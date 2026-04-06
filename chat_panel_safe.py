#!/usr/bin/env python3
"""
Panel de Chat con IA — Copiloto del navegador con Navegación Aumentada por IA.

Integra el chat conversacional con el sistema de análisis de sesión,
sugerencias proactivas y generación de GenTabs.
"""

import json
import re
import time
import requests
from urllib.parse import quote_plus, urlparse, parse_qs, unquote
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTextEdit, QPushButton, QLabel, QSpinBox,
    QLineEdit, QComboBox, QListWidget, QListWidgetItem,
    QCheckBox, QGroupBox, QScrollArea, QFrame, QMessageBox,
    QSplitter, QProgressBar, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QEventLoop, Signal, QThread
from PySide6.QtGui import QFont, QColor, QTextCursor

from base_panel import BasePanel
from llm_client import (
    LLMClient, LLMConfig, LLMError,
    PROVIDER_LOCAL, PROVIDER_LLMAPI, PROVIDER_ANTHROPIC,
    LLMAPI_FREE_MODELS, ANTHROPIC_MODELS, ANTHROPIC_DEFAULT_MODEL,
)

# Importación opcional del sistema de navegación IA
try:
    from session_intent_detector import SessionContextAnalyzer, SessionIntent
    from proactive_suggestion_engine import ProactiveSuggestionEngine, SuggestionType
    _AI_NAV_OK = True
except ImportError:
    _AI_NAV_OK = False

SYSTEM_PROMPT_BROWSER = """You are the AI copilot of a modern web browser. You help the user navigate, search and discover content.

When you recommend websites, tools, articles or resources, ALWAYS provide recommendations as SEARCH-READY items, not fragile deep links.

- Use markdown links with clear labels: [What to search](https://example.com) as reference if needed
- Suggest 2-5 concrete options
- Prefer robust recommendations that can be searched in Google/Bing/DuckDuckGo
- The browser will convert your recommendations into search result tabs."""

SYSTEM_PROMPT_NAV_ANALYST = """You are an expert web navigation analyst. Analyze the browser session described by the user.
Respond in Spanish. Be concise and actionable:
- Summarize what the user is researching/doing
- Identify 3-5 key insights from the open tabs
- Suggest 2-3 next steps or related resources
- Format with headers and bullet points."""

import logging as _log_module
_chat_log = _log_module.getLogger(__name__)


class ChatWorker(QThread):
    """Ejecuta la llamada al LLM en un hilo separado para no bloquear el UI."""

    chunk_received = Signal(str)   # fragmento de texto (streaming)
    finished = Signal(str)         # respuesta completa
    error = Signal(str)            # mensaje de error

    def __init__(self, llm_config: "LLMConfig", messages: list,
                 max_tokens: int = 4096, temperature: float = 0.7):
        super().__init__()
        self._llm_config = llm_config
        self._messages = messages
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            client = LLMClient(self._llm_config)
            full_text = ""

            # Intentar streaming primero
            try:
                for chunk in client.chat_stream(
                    self._messages,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                ):
                    if self._cancelled:
                        return
                    full_text += chunk
                    self.chunk_received.emit(chunk)
                self.finished.emit(full_text)
            except AttributeError:
                # Fallback sin streaming si el método no existe
                content = client.chat(
                    self._messages,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                )
                if not self._cancelled:
                    self.finished.emit(content)
        except LLMError as e:
            _chat_log.error("ChatWorker LLMError: %s", e, exc_info=True)
            if not self._cancelled:
                self.error.emit(str(e))
        except Exception as e:
            _chat_log.error("ChatWorker error: %s", e, exc_info=True)
            if not self._cancelled:
                self.error.emit(f"Error inesperado: {e}")


class ChatPanelSafe(BasePanel):

    # Señal para solicitar apertura de GenTab desde dentro del panel
    gentab_requested = Signal(str)

    # Paleta de colores del panel
    _C = {
        "surface_0":      "#1A1A1A",
        "surface_1":      "#222222",
        "surface_hover":  "#303030",
        "border":         "rgba(255,255,255,0.08)",
        "text_primary":   "#F0F0F0",
        "text_secondary": "#A0A0A0",
        "text_muted":     "#606060",
        "accent":         "#4B9EFF",
        "accent_subtle":  "rgba(75,158,255,0.12)",
        "error":          "#F85149",
        "error_subtle":   "rgba(248,81,73,0.08)",
        "success":        "#3FB950",
    }

    def __init__(self, parent=None):
        self.chat_history = []
        self.session_messages = []
        self.llm_config = LLMConfig.load("ChatPanel")
        self.server_url = self.llm_config.local_url
        self.activity_timer = None
        self._activity_frames = ["⏳", "⌛", "◜", "◝", "◞", "◟"]
        self._activity_idx = 0
        self._last_session_analysis = {}
        self._chat_worker: "ChatWorker | None" = None
        self._streaming_placeholder_added = False
        super().__init__(parent)

    def get_tab_definitions(self):
        return [
            (self.create_chat_tab,       "💬 Chat"),
            (self.create_nav_tab,        "🧭 Navegación"),
            (self.create_settings_tab,   "⚙️ Config"),
            (self.create_history_tab,    "📚 Historial"),
            (self.create_help_tab,       "❓ Ayuda"),
        ]

    def post_setup_ui(self):
        self.set_object_name("chatPanel")
        self._apply_chat_style()

    def _apply_chat_style(self):
        """Aplica el sistema de diseño Arc/Linear al panel de chat."""
        c = self._C
        self.setStyleSheet(f"""
            QWidget#chatPanel, QWidget {{
                background: {c['surface_0']};
                color: {c['text_primary']};
            }}
            QTabWidget::pane {{
                border: none;
                background: {c['surface_0']};
            }}
            QTabBar {{
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {c['text_secondary']};
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                min-height: 26px;
            }}
            QTabBar::tab:selected {{
                background: {c['surface_1']};
                color: {c['text_primary']};
            }}
            QTabBar::tab:hover:!selected {{
                background: {c['surface_hover']};
            }}
            /* Mensajes usuario — borde izquierdo acento */
            QWidget#userBubble {{
                background: {c['accent_subtle']};
                border-left: 2px solid {c['accent']};
                border-radius: 0px 6px 6px 0px;
            }}
            QWidget#assistantBubble {{
                background: transparent;
            }}
            QWidget#errorBubble {{
                background: {c['error_subtle']};
                border-left: 2px solid {c['error']};
                border-radius: 0px 6px 6px 0px;
            }}
            QLabel#bubbleTitle {{
                font-size: 11px;
                color: {c['text_muted']};
                font-weight: 600;
                background: transparent;
            }}
            QLabel#bubbleMsg {{
                font-size: 13px;
                color: {c['text_primary']};
                background: transparent;
            }}
            /* Input area */
            QTextEdit#chatInput {{
                background: transparent;
                border: none;
                font-size: 13px;
                color: {c['text_primary']};
            }}
            /* Scrollbar mínima */
            QScrollBar:vertical {{
                background: transparent; width: 6px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.12);
                border-radius: 3px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255,255,255,0.25);
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{ background: transparent; }}
            /* Botones */
            QPushButton {{
                background: transparent;
                border: 1px solid {c['border']};
                border-radius: 4px;
                color: {c['text_secondary']};
                font-size: 12px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background: {c['surface_hover']};
                color: {c['text_primary']};
            }}
            QPushButton#chatSend {{
                background: {c['accent_subtle']};
                border-color: {c['accent']};
                color: {c['accent']};
                font-weight: 600;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                border-radius: 6px;
                padding: 0px;
                font-size: 16px;
            }}
            QPushButton#chatSend:hover {{
                background: {c['accent']};
                color: #FFFFFF;
            }}
            /* Grupos */
            QGroupBox {{
                background: transparent;
                border: 1px solid {c['border']};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 11px;
                color: {c['text_secondary']};
            }}
            QGroupBox::title {{
                color: {c['text_secondary']};
                subcontrol-origin: margin;
                left: 8px; padding: 0 4px;
            }}
            /* ComboBox, Spin */
            QComboBox, QSpinBox {{
                background: {c['surface_1']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                color: {c['text_primary']};
                padding: 3px 6px;
                font-size: 12px;
            }}
            QComboBox::drop-down {{
                border: none; width: 16px;
            }}
            /* Status */
            QLabel#statusBadge {{
                font-size: 11px;
                padding: 2px 6px;
                border-radius: 3px;
            }}
        """)

    # ── Métodos públicos para integración externa ────────────────────────────

    def set_input_text(self, text: str) -> None:
        """Establece el texto del input de chat y cambia al tab Chat."""
        if hasattr(self, "message_input"):
            self.message_input.setPlainText(text)
            self.message_input.setFocus()
        if hasattr(self, "tab_widget") and self.tab_widget:
            self.tab_widget.setCurrentIndex(0)

    def set_prompt(self, prompt: str) -> None:
        """Recibe un prompt de GenTab, lo muestra y activa el modo GenTab."""
        if hasattr(self, "message_input"):
            self.message_input.setPlainText(prompt)
        if hasattr(self, "assistant_mode"):
            idx = self.assistant_mode.findText("✨ Crear GenTab")
            if idx >= 0:
                self.assistant_mode.setCurrentIndex(idx)
        if hasattr(self, "tab_widget") and self.tab_widget:
            self.tab_widget.setCurrentIndex(0)

    def show_navigation_tab(self) -> None:
        """Cambia al tab de Navegación IA."""
        if hasattr(self, "tab_widget") and self.tab_widget:
            self.tab_widget.setCurrentIndex(1)
        
    def create_chat_tab(self):
        """Tab principal del chat — estilo documento, no burbujas."""
        c = self._C
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Mini header de estado ──────────────────────────────────────────────
        status_bar = QWidget()
        status_bar.setFixedHeight(32)
        status_bar.setStyleSheet(
            f"background: {c['surface_1']}; border-bottom: 1px solid {c['border']};"
        )
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(12, 0, 8, 0)
        sb_layout.setSpacing(6)

        self.status_label = QLabel("● Desconectado")
        self.status_label.setStyleSheet(f"color: {c['error']}; font-size: 11px; background: transparent;")
        sb_layout.addWidget(self.status_label)
        sb_layout.addStretch()

        self.test_connection_btn = QPushButton("Conectar")
        self.test_connection_btn.setFixedHeight(22)
        self.test_connection_btn.clicked.connect(self.test_connection_safe)
        self.test_connection_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1px solid {c['border']};
                border-radius: 3px; color: {c['text_secondary']};
                font-size: 11px; padding: 0px 8px;
            }}
            QPushButton:hover {{
                border-color: {c['accent']}; color: {c['accent']};
            }}
        """)
        sb_layout.addWidget(self.test_connection_btn)
        layout.addWidget(status_bar)

        # ── Contexto de página (colapsable visualmente) ────────────────────────
        ctx_bar = QWidget()
        ctx_bar.setStyleSheet(f"background: {c['surface_1']}; border-bottom: 1px solid {c['border']};")
        ctx_l = QHBoxLayout(ctx_bar)
        ctx_l.setContentsMargins(12, 4, 8, 4)
        ctx_l.setSpacing(6)

        self.context_display = QTextEdit()
        self.context_display.setReadOnly(True)
        self.context_display.setPlaceholderText("Sin contexto de página")
        self.context_display.setMaximumHeight(70)
        self.context_display.setStyleSheet(
            f"background: transparent; border: none; font-size: 11px; "
            f"color: {c['text_secondary']};"
        )
        ctx_l.addWidget(self.context_display, 1)

        ctx_btns = QVBoxLayout()
        ctx_btns.setSpacing(3)
        self.extract_context_btn = QPushButton("↻")
        self.extract_context_btn.setFixedSize(24, 24)
        self.extract_context_btn.setToolTip("Extraer contenido de la página actual")
        self.extract_context_btn.setCursor(Qt.PointingHandCursor)
        self.extract_context_btn.clicked.connect(self.extract_page_content_now)
        self.extract_context_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; border-radius: 3px; "
            f"color: {c['text_muted']}; font-size: 14px; }}"
            f"QPushButton:hover {{ background: {c['surface_hover']}; color: {c['accent']}; }}"
        )
        ctx_btns.addWidget(self.extract_context_btn)

        self.clear_context_btn = QPushButton("✕")
        self.clear_context_btn.setFixedSize(24, 24)
        self.clear_context_btn.setToolTip("Limpiar contexto")
        self.clear_context_btn.setCursor(Qt.PointingHandCursor)
        self.clear_context_btn.clicked.connect(lambda: self.context_display.clear())
        self.clear_context_btn.setStyleSheet(self.extract_context_btn.styleSheet())
        ctx_btns.addWidget(self.clear_context_btn)
        ctx_l.addLayout(ctx_btns)
        layout.addWidget(ctx_bar)

        # ── Área de mensajes ───────────────────────────────────────────────────
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setObjectName("chatScroll")
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chat_scroll.setStyleSheet(f"background: {c['surface_0']}; border: none;")

        self.chat_messages_widget = QWidget()
        self.chat_messages_widget.setStyleSheet(f"background: {c['surface_0']};")
        self.chat_messages_layout = QVBoxLayout(self.chat_messages_widget)
        self.chat_messages_layout.setAlignment(Qt.AlignTop)
        self.chat_messages_layout.setSpacing(2)
        self.chat_messages_layout.setContentsMargins(0, 8, 0, 8)
        self.chat_messages_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        self.chat_scroll.setWidget(self.chat_messages_widget)
        layout.addWidget(self.chat_scroll, 1)

        # ── Área de input (fija en la parte inferior) ──────────────────────────
        input_area = QWidget()
        input_area.setObjectName("chatInputArea")
        input_area.setStyleSheet(
            f"background: {c['surface_1']}; border-top: 1px solid {c['border']};"
        )
        ia_layout = QVBoxLayout(input_area)
        ia_layout.setContentsMargins(12, 8, 12, 8)
        ia_layout.setSpacing(6)

        # Fila de modo + controles
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)

        self.assistant_mode = QComboBox()
        self.assistant_mode.addItem("💬 Chat")
        self.assistant_mode.addItem("📄 Resumen pestaña")
        self.assistant_mode.addItem("📚 Multi-pestaña")
        self.assistant_mode.addItem("🧭 Sesión")
        self.assistant_mode.addItem("✨ GenTab")
        self.assistant_mode.addItem("🔎 Búsqueda")
        self.assistant_mode.addItem("📂 Abrir")
        self.assistant_mode.setToolTip("Modo del asistente")
        self.assistant_mode.setFixedHeight(24)
        self.assistant_mode.setStyleSheet(f"""
            QComboBox {{
                background: transparent; border: 1px solid {c['border']};
                border-radius: 3px; color: {c['text_secondary']};
                font-size: 11px; padding: 0px 4px;
            }}
            QComboBox::drop-down {{ border: none; width: 14px; }}
            QComboBox QAbstractItemView {{
                background: {c['surface_2'] if 'surface_2' in c else c['surface_1']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                selection-background-color: {c['surface_hover']};
            }}
        """)
        mode_row.addWidget(self.assistant_mode)

        self.context_checkbox = QCheckBox("Contexto")
        self.context_checkbox.setChecked(True)
        self.context_checkbox.toggled.connect(self.on_context_toggled)
        self.context_checkbox.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: 11px; background: transparent;"
        )
        mode_row.addWidget(self.context_checkbox)
        mode_row.addStretch()

        self.clear_btn = QPushButton("Limpiar")
        self.clear_btn.setFixedHeight(22)
        self.clear_btn.clicked.connect(self.clear_chat)
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {c['text_muted']}; font-size: 11px;
            }}
            QPushButton:hover {{ color: {c['text_secondary']}; }}
        """)
        mode_row.addWidget(self.clear_btn)
        ia_layout.addLayout(mode_row)

        # Input + botón enviar
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.message_input = QTextEdit()
        self.message_input.setObjectName("chatInput")
        self.message_input.setPlaceholderText("Ask about this page...")
        self.message_input.setMinimumHeight(36)
        self.message_input.setMaximumHeight(100)
        self.message_input.setAcceptRichText(False)
        self.message_input.setStyleSheet(
            f"background: transparent; border: none; font-size: 13px; "
            f"color: {c['text_primary']}; padding: 4px 0px;"
        )
        input_row.addWidget(self.message_input, 1)

        self.send_btn = QPushButton("↑")
        self.send_btn.setObjectName("chatSend")
        self.send_btn.setFixedSize(28, 28)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self.send_message_safe)
        self.send_btn.setEnabled(False)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {c['accent_subtle']}; color: {c['accent']};
                border: 1px solid {c['accent']}; border-radius: 6px;
                font-size: 16px; font-weight: bold;
            }}
            QPushButton:hover {{
                background: {c['accent']}; color: #FFFFFF;
            }}
            QPushButton:disabled {{
                background: transparent;
                border-color: {c['border']};
                color: {c['text_muted']};
            }}
        """)
        input_row.addWidget(self.send_btn)
        ia_layout.addLayout(input_row)
        layout.addWidget(input_area)

        widget.setLayout(layout)
        self.message_input.textChanged.connect(
            lambda: self.send_btn.setEnabled(bool(self.message_input.toPlainText().strip()))
        )
        return widget
        
    # ── Tab Navegación IA ────────────────────────────────────────────────────

    def create_nav_tab(self):
        """Tab de Navegación Aumentada con IA: análisis de sesión + GenTab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ── Análisis de sesión ────────────────────────────────────────────────
        session_group = QGroupBox("🧭 Análisis de Sesión")
        session_group.setStyleSheet("""
            QGroupBox { color: #e2e8f0; border: 1px solid rgba(99,102,241,0.35);
                        border-radius: 10px; margin-top: 8px; font-size: 13px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
        """)
        sg_layout = QVBoxLayout(session_group)
        sg_layout.setSpacing(8)

        # Badge de intención
        self._intent_badge = QLabel("— Sin analizar —")
        self._intent_badge.setAlignment(Qt.AlignCenter)
        self._intent_badge.setStyleSheet("""
            background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.4);
            border-radius: 8px; padding: 6px 12px; color: #c7d2fe; font-size: 13px;
        """)
        sg_layout.addWidget(self._intent_badge)

        # Barra de confianza
        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("Confianza:"))
        self._conf_bar = QProgressBar()
        self._conf_bar.setRange(0, 100)
        self._conf_bar.setValue(0)
        self._conf_bar.setFixedHeight(10)
        self._conf_bar.setTextVisible(False)
        self._conf_bar.setStyleSheet("""
            QProgressBar { background: #1a1a3e; border-radius: 5px; border: none; }
            QProgressBar::chunk { background: #6366f1; border-radius: 5px; }
        """)
        conf_row.addWidget(self._conf_bar, 1)
        self._conf_pct_label = QLabel("0%")
        self._conf_pct_label.setFixedWidth(36)
        self._conf_pct_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        conf_row.addWidget(self._conf_pct_label)
        sg_layout.addLayout(conf_row)

        # Acción sugerida
        self._suggested_action_label = QLabel("")
        self._suggested_action_label.setWordWrap(True)
        self._suggested_action_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-style: italic;")
        sg_layout.addWidget(self._suggested_action_label)

        # Botón de análisis
        analyze_btn = QPushButton("🔍 Analizar sesión actual")
        analyze_btn.setStyleSheet("""
            QPushButton { background: rgba(99,102,241,0.2); color: #c7d2fe;
                          border: 1px solid rgba(99,102,241,0.5); border-radius: 8px;
                          padding: 7px 14px; font-size: 13px; }
            QPushButton:hover { background: rgba(99,102,241,0.4); }
        """)
        analyze_btn.setCursor(Qt.PointingHandCursor)
        analyze_btn.clicked.connect(self._run_session_analysis)
        sg_layout.addWidget(analyze_btn)

        layout.addWidget(session_group)

        # ── Pestañas abiertas ─────────────────────────────────────────────────
        tabs_group = QGroupBox("📑 Pestañas abiertas")
        tabs_group.setStyleSheet(session_group.styleSheet())
        tg_layout = QVBoxLayout(tabs_group)
        tg_layout.setSpacing(6)

        tabs_header = QHBoxLayout()
        self._tabs_count_label = QLabel("0 pestañas")
        self._tabs_count_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        tabs_header.addWidget(self._tabs_count_label)
        tabs_header.addStretch()
        refresh_tabs_btn = QPushButton("🔄")
        refresh_tabs_btn.setFixedSize(28, 28)
        refresh_tabs_btn.setToolTip("Actualizar lista de pestañas")
        refresh_tabs_btn.setStyleSheet("""
            QPushButton { background: rgba(99,102,241,0.15); color: #c7d2fe;
                          border: 1px solid rgba(99,102,241,0.3); border-radius: 6px; }
            QPushButton:hover { background: rgba(99,102,241,0.35); }
        """)
        refresh_tabs_btn.clicked.connect(self._refresh_open_tabs_list)
        tabs_header.addWidget(refresh_tabs_btn)
        tg_layout.addLayout(tabs_header)

        self._open_tabs_list = QListWidget()
        self._open_tabs_list.setMaximumHeight(130)
        self._open_tabs_list.setStyleSheet("""
            QListWidget { background: #1a1a3e; border: 1px solid rgba(99,102,241,0.25);
                          border-radius: 8px; color: #e2e8f0; font-size: 12px; outline: none; }
            QListWidget::item { padding: 5px 8px; border-radius: 4px; }
            QListWidget::item:hover { background: rgba(99,102,241,0.15); }
        """)
        self._open_tabs_list.itemDoubleClicked.connect(self._on_tab_item_double_click)
        tg_layout.addWidget(self._open_tabs_list)

        layout.addWidget(tabs_group)

        # ── Acciones rápidas de navegación ───────────────────────────────────
        actions_group = QGroupBox("⚡ Acciones rápidas")
        actions_group.setStyleSheet(session_group.styleSheet())
        ag_layout = QVBoxLayout(actions_group)
        ag_layout.setSpacing(6)

        quick_actions = [
            ("🧭 Analizar y resumir sesión con IA",
             "Analiza todas mis pestañas abiertas, identifica qué estoy investigando y dame un resumen con insights clave.",
             "🧭 Analizar sesión"),
            ("📊 Comparar contenido de pestañas",
             "Compara el contenido de todas las pestañas abiertas en una tabla interactiva con los puntos clave de cada una.",
             "✨ Crear GenTab"),
            ("📋 Resumen ejecutivo multi-pestaña",
             "Resume todas las pestañas abiertas en un briefing ejecutivo con los puntos más importantes.",
             "📚 Resumen pestañas abiertas"),
            ("🔗 Mapa de enlaces y relaciones",
             "Genera un mapa de enlaces que muestre todos los links encontrados en las pestañas, agrupados por dominio.",
             "✨ Crear GenTab"),
            ("📚 Flashcards de estudio",
             "Genera flashcards interactivas con preguntas y respuestas extraídas del contenido de mis pestañas.",
             "✨ Crear GenTab"),
            ("📈 Dashboard de datos",
             "Crea un dashboard con métricas y KPIs extraídos de los datos de las pestañas. Usa gráficos y contadores.",
             "✨ Crear GenTab"),
        ]

        for label, prompt, mode_text in quick_actions:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton { background: rgba(26,26,62,0.8); color: #c7d2fe;
                              border: 1px solid rgba(99,102,241,0.25); border-radius: 8px;
                              padding: 7px 12px; font-size: 12px; text-align: left; }
                QPushButton:hover { background: rgba(99,102,241,0.25);
                                    border-color: rgba(99,102,241,0.6); }
            """)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, p=prompt, m=mode_text: self._apply_quick_action(p, m)
            )
            ag_layout.addWidget(btn)

        layout.addWidget(actions_group)

        # ── GenTab directo ───────────────────────────────────────────────────
        gentab_group = QGroupBox("✨ GenTab — Generador de aplicaciones")
        gentab_group.setStyleSheet(session_group.styleSheet())
        gg_layout = QVBoxLayout(gentab_group)
        gg_layout.setSpacing(6)

        gentab_info = QLabel(
            "Genera una aplicación web interactiva desde el contenido de tus pestañas."
        )
        gentab_info.setWordWrap(True)
        gentab_info.setStyleSheet("color: #94a3b8; font-size: 12px;")
        gg_layout.addWidget(gentab_info)

        self._gentab_prompt_input = QTextEdit()
        self._gentab_prompt_input.setPlaceholderText(
            "Describe la aplicación a generar...\n"
            "Ej: «Compara los precios de las pestañas en una tabla ordenable»"
        )
        self._gentab_prompt_input.setMaximumHeight(70)
        self._gentab_prompt_input.setAcceptRichText(False)
        self._gentab_prompt_input.setStyleSheet("""
            QTextEdit { background: #1a1a3e; color: #e2e8f0;
                        border: 1px solid rgba(99,102,241,0.3); border-radius: 8px;
                        padding: 6px; font-size: 12px; }
            QTextEdit:focus { border-color: #6366f1; }
        """)
        gg_layout.addWidget(self._gentab_prompt_input)

        open_gentab_btn = QPushButton("✨ Abrir panel GenTab")
        open_gentab_btn.setStyleSheet("""
            QPushButton { background: #6366f1; color: white; border: none;
                          border-radius: 8px; padding: 8px 16px;
                          font-size: 13px; font-weight: bold; }
            QPushButton:hover { background: #4f46e5; }
        """)
        open_gentab_btn.setCursor(Qt.PointingHandCursor)
        open_gentab_btn.clicked.connect(self._open_gentab_panel)
        gg_layout.addWidget(open_gentab_btn)

        layout.addWidget(gentab_group)
        layout.addStretch()

        # Cargar pestañas al crear el tab
        QTimer.singleShot(500, self._refresh_open_tabs_list)
        return widget

    # ── Métodos de Navegación IA ─────────────────────────────────────────────

    def _run_session_analysis(self) -> None:
        """Ejecuta el análisis de sesión y muestra resultado en el tab chat."""
        main = self.window()
        if not hasattr(main, "tab_manager"):
            self.add_message_to_chat("System", "No se puede acceder al gestor de pestañas.", "error")
            return

        self._refresh_open_tabs_list()

        # Actualizar badge a "analizando"
        self._intent_badge.setText("🔄 Analizando...")

        if _AI_NAV_OK:
            try:
                analyzer = SessionContextAnalyzer()
                analysis = analyzer.analyze_current_session(main.tab_manager)
                self._last_session_analysis = analysis
                self._update_session_ui(analysis)

                # Lanzar análisis IA en el chat
                intent_name = analysis["intent"].value if analysis.get("intent") else "general"
                conf = int(analysis.get("confidence", 0) * 100)
                tab_count = analysis.get("tab_count", 0)
                domains = ", ".join(analysis.get("domains", [])[:5])
                action = analysis.get("suggested_action", "")

                analysis_summary = (
                    f"Analiza mi sesión de navegación actual:\n"
                    f"- Intención detectada: {intent_name} (confianza: {conf}%)\n"
                    f"- Pestañas abiertas: {tab_count}\n"
                    f"- Dominios: {domains or 'varios'}\n"
                    f"- Acción sugerida: {action}\n\n"
                    f"Dame un análisis detallado con insights y próximos pasos."
                )

                if hasattr(self, "message_input"):
                    self.message_input.setPlainText(analysis_summary)
                if hasattr(self, "assistant_mode"):
                    idx = self.assistant_mode.findText("🧭 Analizar sesión")
                    if idx >= 0:
                        self.assistant_mode.setCurrentIndex(idx)
                if hasattr(self, "tab_widget"):
                    self.tab_widget.setCurrentIndex(0)
                return
            except Exception as e:
                pass

        # Fallback sin módulo AI
        tabs_context = self._extract_all_open_tabs_context(limit_tabs=6)
        prompt = (
            "Analiza estas pestañas que tengo abiertas y dime:\n"
            "1. ¿Qué estoy investigando/haciendo?\n"
            "2. Insights clave de cada pestaña\n"
            "3. Próximos pasos recomendados\n\n"
            f"{tabs_context}"
        )
        if hasattr(self, "message_input"):
            self.message_input.setPlainText(prompt)
        if hasattr(self, "tab_widget"):
            self.tab_widget.setCurrentIndex(0)
        self._intent_badge.setText("🧭 Análisis manual solicitado")

    def _update_session_ui(self, analysis: dict) -> None:
        """Actualiza los widgets del tab Navegación con los datos del análisis."""
        intent = analysis.get("intent")
        confidence = analysis.get("confidence", 0.0)
        action = analysis.get("suggested_action", "")

        _INTENT_LABELS = {
            "research":      "🔬 Investigación",
            "shopping":      "🛒 Compras",
            "news":          "📰 Noticias",
            "travel":        "✈️ Viajes",
            "coding":        "💻 Programación",
            "entertainment": "🎬 Entretenimiento",
            "general":       "🌐 General",
        }
        label = _INTENT_LABELS.get(intent.value if intent else "general", "🌐 General")
        pct = int(confidence * 100)

        self._intent_badge.setText(label)
        self._conf_bar.setValue(pct)
        self._conf_pct_label.setText(f"{pct}%")
        if action:
            self._suggested_action_label.setText(f"💡 {action}")

    def _refresh_open_tabs_list(self) -> None:
        """Actualiza la lista de pestañas abiertas en el tab Navegación."""
        if not hasattr(self, "_open_tabs_list"):
            return
        self._open_tabs_list.clear()
        main = self.window()
        if not hasattr(main, "tab_manager"):
            return
        tabs = main.tab_manager.tabs
        count = 0
        for i in range(tabs.count()):
            widget = tabs.widget(i)
            if widget is None:
                continue
            url = widget.url().toString() if hasattr(widget, "url") else ""
            if not url or url.startswith("about:"):
                continue
            title = tabs.tabText(i) or url
            item = QListWidgetItem(f"  {i+1}. {title[:55]}")
            item.setToolTip(url)
            item.setData(Qt.UserRole, url)
            self._open_tabs_list.addItem(item)
            count += 1
        self._tabs_count_label.setText(f"{count} pestaña{'s' if count != 1 else ''}")

    def _on_tab_item_double_click(self, item: QListWidgetItem) -> None:
        """Al hacer doble clic en una pestaña, activa ese tab en el navegador."""
        url = item.data(Qt.UserRole)
        if not url:
            return
        main = self.window()
        if not hasattr(main, "tab_manager"):
            return
        tabs = main.tab_manager.tabs
        for i in range(tabs.count()):
            w = tabs.widget(i)
            if w and hasattr(w, "url") and w.url().toString() == url:
                tabs.setCurrentIndex(i)
                break

    def _apply_quick_action(self, prompt: str, mode_text: str) -> None:
        """Aplica una acción rápida: pone el prompt en el input y activa el modo."""
        if hasattr(self, "message_input"):
            self.message_input.setPlainText(prompt)
        if hasattr(self, "assistant_mode"):
            idx = self.assistant_mode.findText(mode_text)
            if idx >= 0:
                self.assistant_mode.setCurrentIndex(idx)
        if hasattr(self, "tab_widget"):
            self.tab_widget.setCurrentIndex(0)

    def _open_gentab_panel(self) -> None:
        """Abre el panel GenTab desde el botón del tab Navegación."""
        prompt = ""
        if hasattr(self, "_gentab_prompt_input"):
            prompt = self._gentab_prompt_input.toPlainText().strip()

        main = self.window()
        if hasattr(main, "gentab_panel") and main.gentab_panel:
            if hasattr(main, "show_advanced_panel"):
                main.show_advanced_panel(main.gentab_panel)
            if prompt and hasattr(main.gentab_panel, "prompt_input"):
                main.gentab_panel.prompt_input.setPlainText(prompt)
        else:
            # Emitir señal para que la MainWindow lo maneje
            self.gentab_requested.emit(prompt)

    def create_settings_tab(self):
        """Tab de configuración del servidor LLM"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # ── Proveedor ──────────────────────────────────────────────────────────
        prov_group = QGroupBox("🌐 Proveedor de IA")
        prov_layout = QVBoxLayout()

        prov_row = QHBoxLayout()
        prov_row.addWidget(QLabel("Proveedor:"))
        self.chat_provider_combo = QComboBox()
        self.chat_provider_combo.addItem("🖥️ LM Studio / Local", PROVIDER_LOCAL)
        self.chat_provider_combo.addItem("☁️ llmapi.ai (cloud gratuito)", PROVIDER_LLMAPI)
        self.chat_provider_combo.addItem("🤖 Anthropic (Claude)", PROVIDER_ANTHROPIC)
        prov_row.addWidget(self.chat_provider_combo)
        prov_layout.addLayout(prov_row)

        # Local URL
        self.chat_local_widget = QWidget()
        local_layout = QHBoxLayout(self.chat_local_widget)
        local_layout.setContentsMargins(0, 0, 0, 0)
        local_layout.addWidget(QLabel("URL servidor:"))
        self.server_url_input = QLineEdit()
        self.server_url_input.setPlaceholderText("http://localhost:1234")
        if hasattr(self.server_url_input, "setClearButtonEnabled"):
            self.server_url_input.setClearButtonEnabled(True)
        self.server_url_input.textChanged.connect(self.on_server_url_changed)
        local_layout.addWidget(self.server_url_input)
        prov_layout.addWidget(self.chat_local_widget)

        # Cloud (llmapi.ai)
        self.chat_cloud_widget = QWidget()
        cloud_layout = QVBoxLayout(self.chat_cloud_widget)
        cloud_layout.setContentsMargins(0, 0, 0, 0)

        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API Key:"))
        self.chat_api_key_input = QLineEdit()
        self.chat_api_key_input.setPlaceholderText("lak-...")
        self.chat_api_key_input.setEchoMode(QLineEdit.Password)
        key_row.addWidget(self.chat_api_key_input)
        show_btn = QPushButton("👁")
        show_btn.setMaximumWidth(32)
        show_btn.setCheckable(True)
        show_btn.toggled.connect(
            lambda on: self.chat_api_key_input.setEchoMode(
                QLineEdit.Normal if on else QLineEdit.Password
            )
        )
        key_row.addWidget(show_btn)
        cloud_layout.addLayout(key_row)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Modelo:"))
        self.chat_model_combo = QComboBox()
        for m in LLMAPI_FREE_MODELS:
            self.chat_model_combo.addItem(m)
        model_row.addWidget(self.chat_model_combo)
        cloud_layout.addLayout(model_row)

        info_cloud = QLabel(
            '🔑 API key gratuita en <a href="https://llmapi.ai" style="color:#4f8ef7;">llmapi.ai</a>'
        )
        info_cloud.setOpenExternalLinks(True)
        info_cloud.setTextFormat(Qt.RichText)
        info_cloud.setStyleSheet("color: #94a3b8; font-size: 11px;")
        cloud_layout.addWidget(info_cloud)
        prov_layout.addWidget(self.chat_cloud_widget)

        # ── Panel Anthropic ──────────────────────────────────────────────────
        self.chat_anthropic_widget = QWidget()
        ant_layout = QVBoxLayout(self.chat_anthropic_widget)
        ant_layout.setContentsMargins(0, 0, 0, 0)
        ant_layout.setSpacing(6)

        # API Key
        ant_key_row = QHBoxLayout()
        ant_key_lbl = QLabel("API Key:")
        ant_key_lbl.setFixedWidth(72)
        ant_key_row.addWidget(ant_key_lbl)
        self.chat_anthropic_key_input = QLineEdit()
        self.chat_anthropic_key_input.setPlaceholderText("sk-ant-api03-...")
        self.chat_anthropic_key_input.setEchoMode(QLineEdit.Password)
        ant_key_row.addWidget(self.chat_anthropic_key_input)
        ant_show_btn = QPushButton("👁")
        ant_show_btn.setMaximumWidth(32)
        ant_show_btn.setCheckable(True)
        ant_show_btn.toggled.connect(
            lambda on: self.chat_anthropic_key_input.setEchoMode(
                QLineEdit.Normal if on else QLineEdit.Password
            )
        )
        ant_key_row.addWidget(ant_show_btn)
        ant_layout.addLayout(ant_key_row)

        # Selector de modelo
        ant_model_row = QHBoxLayout()
        ant_model_lbl = QLabel("Modelo:")
        ant_model_lbl.setFixedWidth(72)
        ant_model_row.addWidget(ant_model_lbl)
        self.chat_anthropic_model_combo = QComboBox()
        model_groups = [
            ("── Claude 4 ──", []),
            (None, ["claude-opus-4-5", "claude-sonnet-4-5"]),
            ("── Claude 3.7 ──", []),
            (None, ["claude-sonnet-3-7"]),
            ("── Claude 3.5 ──", []),
            (None, ["claude-sonnet-3-5", "claude-haiku-3-5"]),
            ("── Claude 3 (legacy) ──", []),
            (None, ["claude-opus-3", "claude-sonnet-3", "claude-haiku-3"]),
        ]
        for header, models_in_group in model_groups:
            if header is not None:
                self.chat_anthropic_model_combo.addItem(header)
                idx = self.chat_anthropic_model_combo.count() - 1
                item = self.chat_anthropic_model_combo.model().item(idx)
                if item:
                    item.setEnabled(False)
                    item.setForeground(QColor("#606060"))
            else:
                for model in models_in_group:
                    self.chat_anthropic_model_combo.addItem(model)
        ant_model_row.addWidget(self.chat_anthropic_model_combo)
        ant_layout.addLayout(ant_model_row)

        # Descripción del modelo seleccionado
        self.chat_anthropic_model_desc = QLabel("")
        self.chat_anthropic_model_desc.setWordWrap(True)
        self.chat_anthropic_model_desc.setStyleSheet(
            f"color: {self._C['text_secondary']}; font-size: 11px;"
        )
        ant_layout.addWidget(self.chat_anthropic_model_desc)
        self.chat_anthropic_model_combo.currentTextChanged.connect(
            self._update_anthropic_model_desc
        )

        # Link a consola Anthropic
        ant_info = QLabel(
            '🔑 Obtén tu API key en '
            '<a href="https://console.anthropic.com/settings/keys" '
            'style="color:#4B9EFF;">console.anthropic.com</a>'
        )
        ant_info.setOpenExternalLinks(True)
        ant_info.setTextFormat(Qt.RichText)
        ant_info.setStyleSheet(f"color: {self._C['text_secondary']}; font-size: 11px;")
        ant_layout.addWidget(ant_info)

        prov_layout.addWidget(self.chat_anthropic_widget)
        # ── fin panel Anthropic ──────────────────────────────────────────────

        # Estado + botones
        conn_row = QHBoxLayout()
        self.test_btn = QPushButton("🔗 Probar conexión")
        self.test_btn.clicked.connect(self.test_connection_safe)
        conn_row.addWidget(self.test_btn)
        save_btn = QPushButton("💾 Guardar")
        save_btn.clicked.connect(self.save_server_url)
        conn_row.addWidget(save_btn)
        prov_layout.addLayout(conn_row)

        self.connection_status_label = QLabel("Estado: sin configurar")
        prov_layout.addWidget(self.connection_status_label)

        prov_group.setLayout(prov_layout)
        layout.addWidget(prov_group)

        # ── Avanzado ───────────────────────────────────────────────────────────
        adv_group = QGroupBox("⚙️ Avanzado")
        adv_layout = QVBoxLayout()

        temp_row = QHBoxLayout()
        temp_row.addWidget(QLabel("Temperatura:"))
        self.temperature_spin = QSpinBox()
        self.temperature_spin.setRange(0, 20)
        self.temperature_spin.setValue(7)
        self.temperature_spin.setSuffix(" /10")
        temp_row.addWidget(self.temperature_spin)
        adv_layout.addLayout(temp_row)

        tokens_row = QHBoxLayout()
        tokens_row.addWidget(QLabel("Máx tokens:"))
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 8192)
        self.max_tokens_spin.setValue(int(self.llm_config.max_tokens))
        tokens_row.addWidget(self.max_tokens_spin)
        adv_layout.addLayout(tokens_row)

        adv_group.setLayout(adv_layout)
        layout.addWidget(adv_group)

        layout.addStretch()

        # Conectar cambio de proveedor
        self.chat_provider_combo.currentIndexChanged.connect(self._on_chat_provider_changed)

        # Poblar con valores guardados
        self._populate_chat_settings_ui()

        widget.setLayout(layout)
        return widget

    def _populate_chat_settings_ui(self):
        provider_index_map = {
            PROVIDER_LOCAL: 0,
            PROVIDER_LLMAPI: 1,
            PROVIDER_ANTHROPIC: 2,
        }
        idx = provider_index_map.get(self.llm_config.provider, 0)
        if hasattr(self, "chat_provider_combo"):
            self.chat_provider_combo.setCurrentIndex(idx)
        if hasattr(self, "server_url_input"):
            self.server_url_input.setText(self.llm_config.local_url or "")
        if hasattr(self, "chat_api_key_input"):
            self.chat_api_key_input.setText(self.llm_config.llmapi_key or "")
        if hasattr(self, "chat_model_combo"):
            mi = self.chat_model_combo.findText(self.llm_config.llmapi_model)
            if mi >= 0:
                self.chat_model_combo.setCurrentIndex(mi)
        # Poblar campos Anthropic
        if hasattr(self, "chat_anthropic_key_input"):
            self.chat_anthropic_key_input.setText(self.llm_config.anthropic_key or "")
        if hasattr(self, "chat_anthropic_model_combo"):
            target = self.llm_config.anthropic_model or ANTHROPIC_DEFAULT_MODEL
            for i in range(self.chat_anthropic_model_combo.count()):
                item = self.chat_anthropic_model_combo.model().item(i)
                if item and item.isEnabled() and self.chat_anthropic_model_combo.itemText(i) == target:
                    self.chat_anthropic_model_combo.setCurrentIndex(i)
                    break
            self._update_anthropic_model_desc(self.chat_anthropic_model_combo.currentText())
        if hasattr(self, "max_tokens_spin"):
            self.max_tokens_spin.setValue(int(self.llm_config.max_tokens))
        self._on_chat_provider_changed()

    _ANTHROPIC_MODEL_DESCRIPTIONS = {
        "claude-opus-4-5":    "Opus 4.5 — el más potente, razonamiento avanzado, 200k ctx",
        "claude-sonnet-4-5":  "Sonnet 4.5 — balance óptimo inteligencia/velocidad (recomendado)",
        "claude-sonnet-3-7":  "Sonnet 3.7 — razonamiento híbrido, pensamiento extendido",
        "claude-sonnet-3-5":  "Sonnet 3.5 — excelente para código y análisis, 200k ctx",
        "claude-haiku-3-5":   "Haiku 3.5 — el más rápido y económico, ideal para tareas cortas",
        "claude-opus-3":      "Opus 3 — legacy, máxima inteligencia generación anterior",
        "claude-sonnet-3":    "Sonnet 3 — legacy, balance generación anterior",
        "claude-haiku-3":     "Haiku 3 — legacy, el más rápido generación anterior",
    }

    def _update_anthropic_model_desc(self, model_text: str) -> None:
        """Actualiza la descripción del modelo Anthropic seleccionado."""
        if not hasattr(self, "chat_anthropic_model_desc"):
            return
        desc = self._ANTHROPIC_MODEL_DESCRIPTIONS.get(model_text, "")
        self.chat_anthropic_model_desc.setText(desc)

    def _on_chat_provider_changed(self):
        if not hasattr(self, "chat_provider_combo"):
            return
        provider = self.chat_provider_combo.currentData()
        if hasattr(self, "chat_local_widget"):
            self.chat_local_widget.setVisible(provider == PROVIDER_LOCAL)
        if hasattr(self, "chat_cloud_widget"):
            self.chat_cloud_widget.setVisible(provider == PROVIDER_LLMAPI)
        if hasattr(self, "chat_anthropic_widget"):
            self.chat_anthropic_widget.setVisible(provider == PROVIDER_ANTHROPIC)
        
    def create_history_tab(self):
        """Tab del historial de conversaciones"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.refresh_history_btn = QPushButton("🔄 Refresh History")
        self.refresh_history_btn.clicked.connect(self.refresh_history)
        controls_layout.addWidget(self.refresh_history_btn)
        
        self.clear_history_btn = QPushButton("🗑️ Clear History")
        self.clear_history_btn.clicked.connect(self.clear_history)
        controls_layout.addWidget(self.clear_history_btn)
        
        self.export_history_btn = QPushButton("📤 Export History")
        self.export_history_btn.clicked.connect(self.export_history)
        controls_layout.addWidget(self.export_history_btn)
        
        layout.addLayout(controls_layout)
        
        # History list
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.load_conversation)
        layout.addWidget(self.history_list)
        
        widget.setLayout(layout)
        return widget
        
    def create_help_tab(self):
        """Tab de ayuda y documentación"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h2>🤖 Chat with IA Panel - Help</h2>
        
        <h3>Initial Configuration:</h3>
        <ol>
            <li>Download and install <a href="https://lmstudio.ai/">LM Studio</a></li>
            <li>Open LM Studio and download an AI model</li>
            <li>Start the local server in LM Studio</li>
            <li>Configure the server URL in the "Settings" tab</li>
            <li>Test the connection</li>
        </ol>
        
        <h3>Using the Chat:</h3>
        <ul>
            <li><strong>Send message:</strong> Write in the text area and press "Send"</li>
            <li><strong>Page context:</strong> Check the box to include information about the current page</li>
            <li><strong>Clear chat:</strong> Use the "Clear Chat" button to start a new conversation</li>
        </ul>
        
        <h3>Advanced Settings:</h3>
        <ul>
            <li><strong>Temperature:</strong> Controls the creativity of responses (0.0 = very conservative, 1.0 = very creative)</li>
            <li><strong>Max tokens:</strong> Limits the length of responses</li>
        </ul>
        
        <h3>Typical LM Studio URLs:</h3>
        <ul>
            <li><code>http://localhost:1234</code> - Default port</li>
            <li><code>http://localhost:8080</code> - Alternative port</li>
            <li><code>http://127.0.0.1:1234</code> - Local IP</li>
        </ul>
        
        <h3>Troubleshooting:</h3>
        <ul>
            <li><strong>Connection error:</strong> Ensure LM Studio is running</li>
            <li><strong>Timeout:</strong> The model may take a while to load, wait a few seconds</li>
            <li><strong>Empty response:</strong> Try a simpler message</li>
        </ul>
        """)
        
        layout.addWidget(help_text)
        widget.setLayout(layout)
        return widget
        
    def on_server_url_changed(self):
        url = self.server_url_input.text().strip()
        self.server_url = url
        self.llm_config.local_url = url
        self.send_btn.setEnabled(bool(url) or self.llm_config.provider in (PROVIDER_LLMAPI, PROVIDER_ANTHROPIC))

    def save_server_url(self):
        """Guarda configuración del proveedor LLM."""
        if hasattr(self, "chat_provider_combo"):
            self.llm_config.provider = self.chat_provider_combo.currentData()
        if hasattr(self, "server_url_input"):
            self.llm_config.local_url = self.server_url_input.text().strip()
            self.server_url = self.llm_config.local_url
        if hasattr(self, "chat_api_key_input"):
            self.llm_config.llmapi_key = self.chat_api_key_input.text().strip()
        if hasattr(self, "chat_model_combo"):
            self.llm_config.llmapi_model = self.chat_model_combo.currentText()
        # Guardar configuración Anthropic
        if hasattr(self, "chat_anthropic_key_input"):
            self.llm_config.anthropic_key = self.chat_anthropic_key_input.text().strip()
        if hasattr(self, "chat_anthropic_model_combo"):
            item = self.chat_anthropic_model_combo.model().item(
                self.chat_anthropic_model_combo.currentIndex()
            )
            if item and item.isEnabled():
                self.llm_config.anthropic_model = self.chat_anthropic_model_combo.currentText()
        if hasattr(self, "max_tokens_spin"):
            self.llm_config.max_tokens = self.max_tokens_spin.value()
        self.llm_config.save("ChatPanel")
        if hasattr(self, "connection_status_label"):
            self.connection_status_label.setText("✅ Guardado")

    def test_connection_safe(self):
        """Prueba la conexión con el proveedor configurado."""
        c = self._C
        self.save_server_url()
        if hasattr(self, "status_label"):
            self.status_label.setText("● Probando...")
            self.status_label.setStyleSheet(
                f"color: {c['accent']}; font-size: 11px; background: transparent;"
            )
        try:
            client = LLMClient(self.llm_config)
            ok, info = client.test()
            if hasattr(self, "status_label"):
                if ok:
                    self.status_label.setText("● Conectado")
                    self.status_label.setStyleSheet(
                        f"color: {c['success']}; font-size: 11px; background: transparent;"
                    )
                else:
                    self.status_label.setText("● Error")
                    self.status_label.setStyleSheet(
                        f"color: {c['error']}; font-size: 11px; background: transparent;"
                    )
            if hasattr(self, "connection_status_label"):
                self.connection_status_label.setText(
                    f"{'✓' if ok else '✗'} {info[:80]}"
                )
            if not ok:
                QMessageBox.warning(self, "Error de conexión", info)
        except Exception as e:
            if hasattr(self, "status_label"):
                self.status_label.setText("● Error")
                self.status_label.setStyleSheet(
                    f"color: {c['error']}; font-size: 11px; background: transparent;"
                )
            QMessageBox.warning(self, "Error", str(e))
            
    def send_message_safe(self):
        """Send message safely without threads"""
        message = self.message_input.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Error", "Please write a message")
            return

        # Get context from the visible display (what user extracted)
        context = ""
        if self.context_checkbox.isChecked():
            context = self.context_display.toPlainText()
            if not context or context.startswith("❌") or context.startswith("⏳"):
                # No valid context extracted
                self.add_message_to_chat("System", "⚠️ Warning: Context checkbox is enabled but no page content extracted. Click 'Extract Page Content' first.", "error")
                context = ""

        # Add user message to chat
        self.add_message_to_chat("User", message, "user")

        mode = self.assistant_mode.currentText() if hasattr(self, "assistant_mode") else "💬 Conversación"

        # Comandos interactivos del navegador (funcionan incluso sin servidor LLM)
        if mode.startswith("🔎"):
            if self._try_handle_browser_command(f"busca {message}"):
                self.message_input.clear()
                return
        if mode.startswith("📂"):
            if self._try_handle_browser_command(f"abre {message}"):
                self.message_input.clear()
                return
        if self._try_handle_browser_command(message):
            self.message_input.clear()
            return

        if self.llm_config.provider == PROVIDER_LOCAL and not self.llm_config.local_url:
            QMessageBox.warning(self, "Error", "Configura la URL del servidor en la pestaña Settings")
            return
        if self.llm_config.provider == PROVIDER_LLMAPI and not self.llm_config.llmapi_key:
            QMessageBox.warning(self, "Error", "Introduce tu API key de llmapi.ai en la pestaña Settings")
            return
        if self.llm_config.provider == PROVIDER_ANTHROPIC and not self.llm_config.anthropic_key:
            QMessageBox.warning(self, "Error", "Introduce tu API key de Anthropic en la pestaña Settings (sk-ant-...)")
            return

        # Clear input
        self.message_input.clear()

        # Disable send button while processing
        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳ Processing...")
        self._start_activity("Procesando...")

        try:
            # Construir prompt según modo
            if mode.startswith("📄"):  # resumen pestaña actual
                if not context:
                    self.extract_page_content_now()
                    context = self.context_display.toPlainText()
                user_content = (
                    "Resume de forma clara y estructurada el siguiente contenido de la pestaña actual. "
                    "Incluye puntos clave, hallazgos y próximos pasos.\n\n"
                    f"{context}\n\nSolicitud del usuario: {message}"
                )

            elif mode.startswith("📚"):  # resumen multi-pestaña
                all_tabs_context = self._extract_all_open_tabs_context(limit_tabs=8)
                user_content = (
                    "Resume y compara el contenido de TODAS estas pestañas abiertas. "
                    "Devuelve: resumen ejecutivo, diferencias clave y recomendaciones accionables.\n\n"
                    f"{all_tabs_context}\n\nSolicitud del usuario: {message}"
                )
                self.add_message_to_chat("System", "📚 Contexto multi-pestaña extraído.", "assistant")

            elif mode.startswith("🧭"):  # analizar sesión
                all_tabs_context = self._extract_all_open_tabs_context(limit_tabs=10)
                intent_info = ""
                if _AI_NAV_OK and self._last_session_analysis:
                    intent = self._last_session_analysis.get("intent")
                    conf = int(self._last_session_analysis.get("confidence", 0) * 100)
                    intent_info = f"\nIntención detectada automáticamente: {intent.value if intent else 'general'} ({conf}% confianza)\n"
                user_content = (
                    f"Analiza la sesión de navegación del usuario.{intent_info}\n"
                    f"Pestañas abiertas:\n{all_tabs_context}\n\n"
                    f"Solicitud: {message}"
                )
                self.add_message_to_chat("System", "🧭 Contexto de sesión capturado para análisis.", "assistant")

            elif mode.startswith("✨"):  # Crear GenTab
                # Despachar al panel GenTab en vez de al chat
                self._create_gentab_from_chat(message)
                self.message_input.clear()
                self.send_btn.setEnabled(True)
                self.send_btn.setText("📤 Enviar")
                self._stop_activity()
                return

            else:
                if context:
                    user_content = f"""Estoy viendo una página web. Contenido:\n\n{context}\n\n---\n\nBasándote en este contenido, {message}"""
                    self.add_message_to_chat("System", f"📄 Contexto enviado ({len(context)} chars)", "assistant")
                else:
                    user_content = message

            # Seleccionar prompt de sistema según modo
            system_prompt = SYSTEM_PROMPT_BROWSER
            if mode.startswith("📄") or mode.startswith("📚"):
                system_prompt = (
                    "You are an expert assistant that creates high-quality summaries in Spanish. "
                    "Be clear, structured and practical. Use headings and bullet points."
                )
            elif mode.startswith("🧭"):
                system_prompt = SYSTEM_PROMPT_NAV_ANALYST

            # Conversación persistente: incluir últimos turnos
            history_window = self.session_messages[-10:] if self.session_messages else []
            messages = [{"role": "system", "content": system_prompt}] + history_window + [
                {"role": "user", "content": user_content}
            ]

            temperature = getattr(self.llm_config, "temperature", 0.7)
            # Límite razonable: evita respuestas interminables y timeouts
            max_tokens = max(1024, min(8192, getattr(self.llm_config, "max_tokens", 4096)))

            # Guardar el mensaje del usuario en historial antes de lanzar el worker
            self.session_messages.append({"role": "user", "content": user_content})

            # Lanzar worker asíncrono para no bloquear el UI
            self._launch_chat_worker(messages, message, max_tokens, temperature)
            return  # el resto lo gestionan los slots del worker

        except Exception as e:
            _chat_log.critical("Error preparando mensaje: %s", e, exc_info=True)
            self.add_message_to_chat("System", f"Error al preparar mensaje: {e}", "error")
            self.send_btn.setEnabled(True)
            self.send_btn.setText("📤 Enviar")
            self._stop_activity()

    # ── Worker asíncrono para chat ────────────────────────────────────────────

    def _launch_chat_worker(self, messages: list, original_message: str,
                            max_tokens: int, temperature: float):
        """Lanza ChatWorker en segundo plano. NO bloquea el hilo principal."""
        # Cancelar worker anterior si sigue activo
        if self._chat_worker and self._chat_worker.isRunning():
            self._chat_worker.cancel()
            self._chat_worker.wait(2000)

        self._streaming_placeholder_added = False
        self._streaming_original_message = original_message

        self._chat_worker = ChatWorker(
            self.llm_config, messages, max_tokens, temperature
        )
        self._chat_worker.chunk_received.connect(self._on_chat_chunk)
        self._chat_worker.finished.connect(self._on_chat_finished)
        self._chat_worker.error.connect(self._on_chat_error)

        # Botón cambia a "Cancelar"
        self.send_btn.setEnabled(True)
        self.send_btn.setText("⏹ Cancelar")
        try:
            self.send_btn.clicked.disconnect()
        except Exception:
            pass
        self.send_btn.clicked.connect(self._cancel_chat_worker)

        self._chat_worker.start()

    def _cancel_chat_worker(self):
        """Cancela el worker en curso y restaura el botón de envío."""
        if self._chat_worker and self._chat_worker.isRunning():
            self._chat_worker.cancel()
            self._chat_worker.wait(2000)
        self.add_message_to_chat("System", "⏹ Generación cancelada.", "assistant")
        self._restore_send_button()
        self._stop_activity()

    def _on_chat_chunk(self, chunk: str):
        """Añade fragmento de streaming al último mensaje IA."""
        if not self._streaming_placeholder_added:
            self.add_message_to_chat("IA", "", "assistant")
            self._streaming_placeholder_added = True
            self._streaming_text = ""

        self._streaming_text = getattr(self, "_streaming_text", "") + chunk

        # Actualizar el QLabel del último mensaje de IA (objectName "bubbleMsg")
        last_labels = self.chat_messages_widget.findChildren(
            QLabel, "bubbleMsg"
        )
        if last_labels:
            last_labels[-1].setText(self._streaming_text)
            last_labels[-1].adjustSize()

        # Auto-scroll
        QTimer.singleShot(0, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def _on_chat_finished(self, full_content: str):
        """Llamado cuando el worker termina correctamente."""
        if not self._streaming_placeholder_added:
            # Sin streaming: mostrar de una vez
            self.add_message_to_chat("IA", full_content, "assistant")
        # Registrar en historial
        self.session_messages.append({"role": "assistant", "content": full_content})
        original = getattr(self, "_streaming_original_message", "")
        self.save_to_history(original, full_content)
        self._restore_send_button()
        self._stop_activity()

    def _on_chat_error(self, error_msg: str):
        """Llamado cuando el worker devuelve un error."""
        self.add_message_to_chat("System", f"⚠️ {error_msg}", "error")
        self._restore_send_button()
        self._stop_activity()

    def _restore_send_button(self):
        """Restaura el botón de envío a su estado normal."""
        try:
            self.send_btn.clicked.disconnect()
        except Exception:
            pass
        self.send_btn.clicked.connect(self.send_message_safe)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("📤 Enviar")

    def _try_handle_browser_command(self, message):
        """
        Ejecuta acciones directas del navegador desde lenguaje natural:
        - "busca ...": abre búsqueda en nueva pestaña
        - "abre ...": abre URL(s)/dominios o una búsqueda si no hay URL
        """
        text = (message or "").strip()
        lower = text.lower().strip()

        # Normalizar acentos para detectar comandos robustamente (busca/busqueda/abrir/etc.)
        normalized = (
            lower.replace("á", "a")
                 .replace("é", "e")
                 .replace("í", "i")
                 .replace("ó", "o")
                 .replace("ú", "u")
        )

        # Buscar en la web (acepta frases como "por favor buscame X")
        search_match = re.search(
            r"\b(?:busca(?:me|r)?|search|find)\b\s+(.+)$",
            normalized,
            flags=re.IGNORECASE
        )
        if search_match:
            start_idx = search_match.start(1)
            query = text[start_idx:].strip(" .,:;!?")
            if not query:
                self.add_message_to_chat("System", "Escribe qué quieres buscar. Ejemplo: \"busca vuelos baratos a Tokio\"", "error")
                return True
            opened_url = self._open_best_result_from_query(query)
            if opened_url:
                self.add_message_to_chat("IA", f"🚀 He abierto el mejor resultado web para: **{query}**\n\n[{opened_url}]({opened_url})", "assistant")
            else:
                search_url = self._build_search_url(query)
                self._open_url_in_browser(search_url)
                self.add_message_to_chat("IA", f"🔎 No pude resolver resultado directo. Abrí la búsqueda para: **{query}**\n\n[{search_url}]({search_url})", "assistant")
            return True

        # Abrir web(s) (acepta "abre", "abrir", "open", incluso dentro de frase)
        open_match = re.search(
            r"\b(?:abre|abrir|open)\b\s+(.+)$",
            normalized,
            flags=re.IGNORECASE
        )
        if open_match:
            start_idx = open_match.start(1)
            target = text[start_idx:].strip(" .,:;!?")
            if not target:
                self.add_message_to_chat("System", "Indica qué quieres abrir. Ejemplo: \"abre github.com\"", "error")
                return True

            links = self._extract_urls_from_message(target)
            urls = [u[0] for u in links]

            # Si no hay URL explícita, intentar detectar dominios sueltos
            if not urls:
                domains = re.findall(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b', target)
                for d in domains:
                    urls.append(f"https://{d}")

            # Si sigue sin haber URLs, abrir una búsqueda con el texto objetivo
            if not urls:
                opened_url = self._open_best_result_from_query(target)
                if opened_url:
                    self.add_message_to_chat("IA", f"🚀 No detecté URL exacta, abrí el mejor resultado para: **{target}**\n\n[{opened_url}]({opened_url})", "assistant")
                else:
                    search_url = self._build_search_url(target)
                    self._open_url_in_browser(search_url)
                    self.add_message_to_chat("IA", f"📂 No detecté una URL exacta, así que abrí una búsqueda para: **{target}**\n\n[{search_url}]({search_url})", "assistant")
                return True

            self._open_urls_in_browser(urls)
            self.add_message_to_chat("IA", f"🚀 He abierto {len(urls)} pestaña(s) en el navegador.", "assistant")
            return True

        return False

    def _create_gentab_from_chat(self, prompt: str) -> None:
        """Abre el panel GenTab con el prompt indicado desde el chat."""
        self.add_message_to_chat(
            "System",
            f"✨ Abriendo GenTab con el prompt: «{prompt[:80]}{'...' if len(prompt) > 80 else ''}»",
            "assistant",
        )
        main = self.window()
        if hasattr(main, "gentab_panel") and main.gentab_panel:
            if hasattr(main, "show_advanced_panel"):
                main.show_advanced_panel(main.gentab_panel)
            if prompt and hasattr(main.gentab_panel, "prompt_input"):
                main.gentab_panel.prompt_input.setPlainText(prompt)
        else:
            self.gentab_requested.emit(prompt)

    def _build_search_url(self, query):
        """Construye URL de búsqueda usando el motor predeterminado si existe."""
        q = quote_plus(query)
        main = self.window()
        try:
            if hasattr(main, 'search_engine_manager') and main.search_engine_manager:
                default_engine = main.search_engine_manager.get_default_engine()
                engine_id = getattr(default_engine, "id", "duckduckgo")
                if engine_id == "google":
                    return f"https://www.google.com/search?q={q}"
                if engine_id == "bing":
                    return f"https://www.bing.com/search?q={q}"
                return f"https://duckduckgo.com/?q={q}"
        except Exception:
            pass
        return f"https://duckduckgo.com/?q={q}"

    def _get_search_engine_name(self):
        """Obtiene nombre legible del buscador activo."""
        main = self.window()
        try:
            if hasattr(main, 'search_engine_manager') and main.search_engine_manager:
                default_engine = main.search_engine_manager.get_default_engine()
                engine_id = getattr(default_engine, "id", "duckduckgo")
                if engine_id == "google":
                    return "Google"
                if engine_id == "bing":
                    return "Bing"
                return "DuckDuckGo"
        except Exception:
            pass
        return "DuckDuckGo"

    def _extract_all_open_tabs_context(self, limit_tabs=8):
        """Extrae contexto de múltiples pestañas abiertas de forma síncrona (con timeout por pestaña)."""
        import logging as _logging
        _log = _logging.getLogger(__name__)

        main = self.window()
        if not hasattr(main, 'tab_manager') or not main.tab_manager:
            _log.warning("_extract_all_open_tabs_context: tab_manager no disponible")
            return "No se pudo acceder a las pestañas."

        contexts = []
        tabs = main.tab_manager.tabs
        total = min(tabs.count(), limit_tabs)
        _log.debug("Extrayendo contexto de %d/%d pestañas", total, tabs.count())

        for i in range(total):
            browser = tabs.widget(i)
            if not browser or not hasattr(browser, "page"):
                _log.debug("Pestaña %d: sin widget o sin page, omitida", i)
                continue
            try:
                url = browser.url().toString()
            except Exception as e:
                _log.warning("Pestaña %d: error obteniendo URL: %s", i, e)
                continue

            if not url or url.startswith("about:"):
                continue

            holder = {"html": None}
            loop = QEventLoop()

            def on_html(html_content, l=loop, h=holder):
                h["html"] = html_content
                if l.isRunning():
                    l.quit()

            _log.debug("Pestaña %d (%s): solicitando HTML…", i, url[:60])
            QTimer.singleShot(3000, loop.quit)
            try:
                browser.page().toHtml(on_html)
                loop.exec()
            except Exception as e:
                _log.error("Pestaña %d: error en toHtml/loop.exec: %s", i, e, exc_info=True)
                continue

            html_content = holder.get("html") or ""
            if not html_content:
                _log.warning("Pestaña %d (%s): HTML vacío tras timeout", i, url[:60])
                continue

            try:
                title = browser.page().title() or f"Tab {i+1}"
                extracted = self._simple_extract_text(html_content, url, title)
                contexts.append(f"=== TAB {i+1} ===\n{extracted[:2500]}")
                _log.debug("Pestaña %d: extraídos %d chars", i, len(extracted))
            except Exception as e:
                _log.error("Pestaña %d: error extrayendo texto: %s", i, e, exc_info=True)

        if not contexts:
            _log.warning("No se pudo extraer contexto de ninguna pestaña")
            return "No se pudo extraer contenido de pestañas abiertas."

        _log.info("Contexto multi-pestaña extraído: %d pestañas", len(contexts))
        return "\n\n".join(contexts)

    def _start_activity(self, base_text="Procesando..."):
        """Inicia animación suave en la etiqueta de estado."""
        c = self._C
        self._activity_idx = 0
        if not self.activity_timer:
            self.activity_timer = QTimer(self)
            self.activity_timer.timeout.connect(lambda: self._tick_activity(base_text))
        if hasattr(self, "status_label"):
            self.status_label.setStyleSheet(
                f"color: {c['warning'] if 'warning' in c else '#D29922'}; "
                "font-size: 11px; background: transparent;"
            )
        self.activity_timer.start(200)

    def _tick_activity(self, base_text):
        frame = self._activity_frames[self._activity_idx % len(self._activity_frames)]
        self._activity_idx += 1
        if hasattr(self, "status_label"):
            self.status_label.setText(f"{frame} {base_text}")

    def _stop_activity(self):
        """Detiene animación de actividad y actualiza indicador."""
        c = self._C
        if self.activity_timer and self.activity_timer.isActive():
            self.activity_timer.stop()
        if hasattr(self, "status_label"):
            if self.server_url:
                self.status_label.setText("● Conectado")
                self.status_label.setStyleSheet(
                    f"color: {c['success']}; font-size: 11px; background: transparent;"
                )
            else:
                self.status_label.setText("● Desconectado")
                self.status_label.setStyleSheet(
                    f"color: {c['error']}; font-size: 11px; background: transparent;"
                )

    def _get_search_engine_id(self):
        """Obtiene id interno del buscador activo."""
        main = self.window()
        try:
            if hasattr(main, 'search_engine_manager') and main.search_engine_manager:
                default_engine = main.search_engine_manager.get_default_engine()
                return getattr(default_engine, "id", "duckduckgo")
        except Exception:
            pass
        return "duckduckgo"

    def _open_best_result_from_query(self, query):
        """
        Resuelve una consulta al primer resultado web y lo abre automáticamente.
        Devuelve la URL abierta o None.
        """
        direct_url = self._resolve_first_result_url(query)
        if direct_url:
            self._open_url_in_browser(direct_url)
            return direct_url
        return None

    def _resolve_first_result_url(self, query):
        """
        Intenta resolver la consulta a la primera URL real del buscador seleccionado.
        Fallback: None.
        """
        search_url = self._build_search_url(query)
        engine_id = self._get_search_engine_id()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
        }

        try:
            resp = requests.get(search_url, headers=headers, timeout=10)
            if resp.status_code != 200 or not resp.text:
                return None
            html = resp.text

            # Bing parser
            if engine_id == "bing":
                m = re.search(r'<li class="b_algo".*?<h2><a href="(https?://[^"]+)"', html, re.DOTALL)
                if m:
                    return m.group(1)

            # Google parser (frágil por cambios, pero útil como intento)
            if engine_id == "google":
                m = re.search(r'/url\\?q=(https?[^&"]+)&', html)
                if m:
                    return unquote(m.group(1))

            # DuckDuckGo parser
            m = re.search(r'class="result__a"[^>]*href="([^"]+)"', html)
            if m:
                href = m.group(1)
                # Puede venir redirect /l/?uddg=...
                if "duckduckgo.com/l/?" in href or href.startswith("/l/?"):
                    parsed = urlparse(href if href.startswith("http") else f"https://duckduckgo.com{href}")
                    uddg = parse_qs(parsed.query).get("uddg", [])
                    if uddg:
                        return unquote(uddg[0])
                if href.startswith("http"):
                    return href

        except Exception:
            return None

        return None
        
    def format_ai_response(self, text):
        """
        Formats text with simple lists/headers to readable HTML.
        Adjusted for dark mode: subtle backgrounds and borders.
        """
        if not text:
            return text
            
        # Convert text to HTML with appropriate formatting
        formatted_text = text
        
        # Format main headings (lines ending with :)
        formatted_text = formatted_text.replace('\n\n', '\n')  # Normalize line breaks
        
        # Detect and format main headings (lines ending with :)
        lines = formatted_text.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Detect main headings (lines ending with :)
            if line.endswith(':') and len(line) < 100:
                formatted_lines.append(f'<h3 style="margin: 15px 0 10px 0; font-size: 16px; font-weight: bold;">{line}</h3>')
                continue
                
            # Detect secondary headings (lines starting with **)
            if line.startswith('**') and line.endswith('**'):
                title = line[2:-2]  # Remove **
                formatted_lines.append(f'<h4 style="margin: 12px 0 8px 0; font-size: 14px; font-weight: bold;">{title}</h4>')
                continue
                
            # Detect numbered lists (lines starting with number.)
            if line and line[0].isdigit() and '. ' in line[:5]:
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    number = parts[0]
                    content = parts[1]
                    formatted_lines.append(f'<div style="margin: 5px 0; padding-left: 20px;"><strong>{number}.</strong> {content}</div>')
                    continue
                    
            # Detect list items with *
            if line.startswith('* ') or line.startswith('- '):
                content = line[2:] if line.startswith('* ') else line[2:]
                formatted_lines.append(f'<div style="margin: 3px 0; padding-left: 20px;">• {content}</div>')
                continue
                
            # Detect list items with +
            if line.startswith('+ '):
                content = line[2:]
                formatted_lines.append(f'<div style="margin: 3px 0; padding-left: 20px;">• {content}</div>')
                continue
                
            # Detect bold text (**text**)
            if '**' in line:
                # Replace **text** with <strong>text</strong>
                import re
                line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
                
            # Detect italic text (*text*)
            if '*' in line and '**' not in line:
                # Replace *text* with <em>text</em> (only if not **)
                import re
                line = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', line)
                
            # Normal line
            if line:
                formatted_lines.append(f'<div style="margin: 5px 0; line-height: 1.4;">{line}</div>')
        
        # Join all formatted lines
        formatted_text = '\n'.join(formatted_lines)
        
        # No inline styles - use current theme QSS
        formatted_text = f"""
        <div style="
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.55;
            padding: 12px 14px;
            border-radius: 10px;
            margin: 10px 0;
        ">
            {formatted_text}
        </div>
        """
        
        return formatted_text

    def add_message_to_chat(self, sender, message, message_type):
        """
        Añade un mensaje al chat — estilo documento (no burbujas).

        Usuario: borde izquierdo accent, fondo sutil.
        IA: sin fondo, solo texto.
        Error/Sistema: borde izquierdo rojo, fondo sutil.
        """
        import html as _html

        c = self._C
        timestamp = datetime.now().strftime("%H:%M")

        # Contenedor del mensaje
        msg_widget = QWidget()
        msg_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

        if message_type == "user":
            msg_widget.setObjectName("userBubble")
            margin_left = 16
        elif message_type == "assistant":
            msg_widget.setObjectName("assistantBubble")
            margin_left = 0
        else:
            msg_widget.setObjectName("errorBubble")
            margin_left = 0

        msg_layout = QVBoxLayout(msg_widget)
        msg_layout.setSpacing(2)

        if message_type == "user":
            msg_layout.setContentsMargins(12, 8, 10, 8)
        else:
            msg_layout.setContentsMargins(12, 6, 10, 6)

        # Fila meta: remitente + hora
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)

        sender_map = {"user": "Tú", "assistant": sender, "error": "Sistema"}
        sender_text = sender_map.get(message_type, sender)

        meta_lbl = QLabel(f"{sender_text}")
        meta_lbl.setObjectName("bubbleTitle")
        meta_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; "
            f"color: {c['accent'] if message_type == 'user' else c['text_muted']}; "
            "background: transparent;"
        )
        meta_row.addWidget(meta_lbl)

        time_lbl = QLabel(timestamp)
        time_lbl.setStyleSheet(f"font-size: 10px; color: {c['text_muted']}; background: transparent;")
        meta_row.addWidget(time_lbl)
        meta_row.addStretch()
        msg_layout.addLayout(meta_row)

        # Contenido del mensaje
        if message_type == "assistant" and sender == "IA":
            content_html = self.format_ai_response(message)
            msg_lbl = QLabel(content_html)
            msg_lbl.setTextFormat(Qt.RichText)
        else:
            msg_lbl = QLabel(_html.escape(message) if message_type != "assistant" else message)
            msg_lbl.setTextFormat(Qt.PlainText if message_type != "assistant" else Qt.RichText)

        msg_lbl.setObjectName("bubbleMsg")
        msg_lbl.setWordWrap(True)
        msg_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        msg_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        msg_lbl.setOpenExternalLinks(True)
        msg_layout.addWidget(msg_lbl)

        # Tarjetas de recomendación solo para IA real
        if message_type == "assistant" and sender == "IA":
            search_links = self._extract_search_links_from_message(message)
            if search_links:
                self._add_recommendation_cards(msg_layout, search_links)

        # Añadir a la lista con margen izquierdo para mensajes de usuario
        if margin_left:
            row = QHBoxLayout()
            row.setContentsMargins(margin_left, 0, 0, 0)
            row.addWidget(msg_widget)
            row_widget = QWidget()
            row_widget.setLayout(row)
            row_widget.setStyleSheet("background: transparent;")
            self.chat_messages_layout.addWidget(row_widget)
        else:
            self.chat_messages_layout.addWidget(msg_widget)

        # Forzar actualización de layout
        self.chat_messages_widget.updateGeometry()
        self.chat_scroll.updateGeometry()

        # Auto-scroll al final
        QTimer.singleShot(10, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    def _extract_urls_from_message(self, text):
        """Extrae URLs de la respuesta de la IA: markdown [texto](url) y URLs planas."""
        if not text:
            return []
        urls = []
        # Enlaces markdown [texto](url)
        for m in re.finditer(r'\[([^\]]*)\]\((https?://[^\)\s]+)\)', text):
            url = m.group(2).rstrip('.,;:!?)')
            title = (m.group(1).strip() or None)
            if url and url not in [u[0] for u in urls]:
                urls.append((url, title))
        # URLs planas no capturadas ya
        for m in re.finditer(r'https?://[^\s\)\]\>\"]+', text):
            url = m.group(0).rstrip('.,;:!?)')
            if not any(u[0] == url for u in urls):
                urls.append((url, None))
        return urls[:10]  # Máximo 10 para no saturar la UI

    def _extract_search_links_from_message(self, text):
        """
        Convierte recomendaciones de la IA en enlaces de búsqueda robustos.
        Devuelve lista de tuplas: (search_url, label)
        """
        raw_links = self._extract_urls_from_message(text)
        search_links = []
        seen = set()

        for url, title in raw_links:
            query = self._build_search_query_from_recommendation(url, title)
            if not query:
                continue
            search_url = self._build_search_url(query)
            if search_url in seen:
                continue
            seen.add(search_url)
            label = title or query
            search_links.append((search_url, label))

        # Fallback: sólo extraer bullets que parezcan nombres de sitios/herramientas,
        # NUNCA cabeceras markdown, frases largas de análisis ni mensajes del sistema.
        if not search_links and text:
            for line in text.splitlines():
                stripped = line.strip()
                # Ignorar cabeceras markdown (# ## ###)
                if stripped.startswith("#"):
                    continue
                # Ignorar líneas que son claramente frases normales de análisis
                if stripped.startswith(("✅", "⏳", "❌", "🧭", "📄", "📚", "🔄")):
                    continue
                # Ignorar líneas demasiado cortas o demasiado largas
                clean = stripped.strip(" -•*\t")
                if len(clean) < 8 or len(clean) > 60:
                    continue
                # Solo aceptar si parece un nombre de herramienta/sitio:
                # debe contener al menos un punto o ser una palabra compuesta
                # Requisito mínimo: no ser una frase con verbo
                words = clean.split()
                if len(words) > 6:
                    continue  # Frases largas no son recomendaciones de sitios
                query = clean
                search_url = self._build_search_url(query)
                if search_url in seen:
                    continue
                seen.add(search_url)
                search_links.append((search_url, query))
                if len(search_links) >= 5:
                    break

        return search_links[:10]

    def _build_search_query_from_recommendation(self, url, title=None):
        """Construye una query estable para buscador desde URL/título sugerido por IA."""
        if title and title.strip():
            return title.strip()

        clean = re.sub(r'^https?://', '', (url or '').strip(), flags=re.IGNORECASE)
        clean = clean.split('#')[0].split('?')[0]
        parts = [p for p in clean.split('/') if p]
        if not parts:
            return ""
        domain = parts[0].replace("www.", "")
        path = " ".join(parts[1:3]) if len(parts) > 1 else ""
        path = path.replace('-', ' ').replace('_', ' ')
        query = f"{domain} {path}".strip()
        return query[:120]

    def _add_recommendation_cards(self, parent_layout, urls):
        """Añade tarjetas para abrir resultados de búsqueda en pestañas."""
        rec_frame = QFrame()
        rec_frame.setObjectName("recommendationCards")
        rec_layout = QVBoxLayout(rec_frame)
        rec_layout.setContentsMargins(8, 10, 8, 4)
        rec_layout.setSpacing(8)

        rec_label = QLabel(f"🔎 <b>Abrir búsqueda en {self._get_search_engine_name()}</b>")
        rec_label.setStyleSheet("color: #1a73e8; font-size: 12px;")
        rec_label.setTextFormat(Qt.RichText)
        rec_layout.addWidget(rec_label)

        # Fila de botones por enlace
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(6)
        for url, title in urls:
            label = (title or url)
            if len(label) > 45:
                label = label[:42] + "..."
            btn = QPushButton(f"🔎 {label}")
            btn.setToolTip(url)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(26, 115, 232, 0.12);
                    color: #1a73e8; border: 1px solid rgba(26, 115, 232, 0.4);
                    border-radius: 6px; padding: 6px 12px; font-size: 12px;
                    text-align: left; max-width: 220px;
                }
                QPushButton:hover {
                    background: rgba(26, 115, 232, 0.25);
                    border-color: #1a73e8;
                }
            """)
            btn.clicked.connect(lambda checked, u=url: self._open_url_in_browser(u))
            buttons_row.addWidget(btn)
        buttons_row.addStretch(1)
        rec_layout.addLayout(buttons_row)

        if len(urls) > 1:
            open_all_btn = QPushButton(f"🔎 Abrir todas en {self._get_search_engine_name()}")
            open_all_btn.setCursor(Qt.PointingHandCursor)
            open_all_btn.setStyleSheet("""
                QPushButton {
                    background: #1a73e8; color: white; border: none;
                    border-radius: 6px; padding: 8px 14px; font-size: 12px; font-weight: bold;
                }
                QPushButton:hover { background: #1557b0; }
            """)
            open_all_btn.clicked.connect(lambda: self._open_urls_in_browser([u[0] for u in urls]))
            rec_layout.addWidget(open_all_btn)

        rec_frame.setStyleSheet("""
            QFrame#recommendationCards {
                background: rgba(26, 115, 232, 0.06);
                border: 1px solid rgba(26, 115, 232, 0.2);
                border-radius: 8px;
            }
        """)
        parent_layout.addWidget(rec_frame)

    def _auto_open_recommendations(self, search_links, max_auto_open=3):
        """
        Abre automáticamente resultados web reales desde recomendaciones de búsqueda.
        search_links: [(search_url, label), ...]
        """
        opened = 0
        for search_url, label in search_links:
            if opened >= max_auto_open:
                break
            query = (label or "").strip()
            if not query:
                # fallback: usar q de la URL
                try:
                    parsed = urlparse(search_url)
                    q = parse_qs(parsed.query).get("q", [""])[0]
                    query = unquote(q)
                except Exception:
                    query = ""
            if not query:
                continue
            direct = self._resolve_first_result_url(query)
            if direct:
                self._open_url_in_browser(direct)
                opened += 1

    def _open_url_in_browser(self, url):
        """Abre una URL en una nueva pestaña del navegador."""
        main = self.window()
        if hasattr(main, 'tab_manager') and main.tab_manager:
            main.tab_manager.add_new_tab(url)

    def _open_urls_in_browser(self, urls):
        """Abre varias URLs en pestañas nuevas."""
        for url in urls:
            self._open_url_in_browser(url)

    def clear_chat(self):
        """Clear chat area"""
        for i in reversed(range(self.chat_messages_layout.count())):
            widget = self.chat_messages_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self.chat_history = []
        self.session_messages = []
        self._stop_activity()
        
    def save_to_history(self, user_message, ai_response):
        """Save conversation to history"""
        conversation = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "ai_response": ai_response
        }
        self.chat_history.append(conversation)
        self.refresh_history()
        
    def refresh_history(self):
        """Update history list"""
        self.history_list.clear()
        for i, conv in enumerate(self.chat_history):
            timestamp = datetime.fromisoformat(conv["timestamp"]).strftime("%Y-%m-%d %H:%M")
            item_text = f"{timestamp}: {conv['user_message'][:50]}..."
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, i)
            self.history_list.addItem(item)
            
    def load_conversation(self, item):
        """Load conversation from history"""
        index = item.data(Qt.UserRole)
        if 0 <= index < len(self.chat_history):
            conv = self.chat_history[index]
            self.clear_chat()
            self.add_message_to_chat("User", conv["user_message"], "user")
            self.add_message_to_chat("IA", conv["ai_response"], "assistant")
            
    def clear_history(self):
        """Clear history"""
        self.chat_history.clear()
        self.history_list.clear()
        
    def export_history(self):
        """Export history to file"""
        if not self.chat_history:
            QMessageBox.information(self, "History", "No conversations to export")
            return
            
        try:
            filename = f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.chat_history, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Export", f"History exported to {filename}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not export history: {e}")
            
    def load_settings(self):
        """Load saved settings"""
        try:
            # Here you could load from a configuration file
            # For now, we use default values
            pass
        except Exception as e:
            print(f"Error loading configuration: {e}")
            
    def save_settings(self):
        """Save settings"""
        try:
            # Here you could save to a configuration file
            pass
        except Exception as e:
            print(f"Error saving configuration: {e}") 

    def update_context_info(self):
        """DEPRECATED - Trigger extraction instead"""
        # Now we just trigger the extraction
        self.extract_page_content_now()
    
    def on_context_toggled(self, checked):
        """Callback when context is toggled"""
        if checked:
            # Show message suggesting to extract content
            if not self.context_display.toPlainText() or self.context_display.toPlainText().startswith("Page content"):
                self.add_message_to_chat("System", "💡 Tip: Click 'Extract Page Content' to load the current page's content", "assistant")
        else:
            self.add_message_to_chat("System", "ℹ️ Page context disabled - AI will not receive page content", "assistant")
    
    def extract_page_content_now(self):
        """Extract page content and display it - SIMPLE VERSION"""
        try:
            # Show loading message
            self.context_display.setPlainText("⏳ Extracting page content...")
            self.extract_context_btn.setEnabled(False)

            # Get current tab
            main_window = self.window()
            if not hasattr(main_window, 'tab_manager'):
                self.context_display.setPlainText("❌ Error: Cannot access tab manager")
                self.extract_context_btn.setEnabled(True)
                return

            current_tab = main_window.tab_manager.tabs.currentWidget()
            if not current_tab or not hasattr(current_tab, 'page'):
                self.context_display.setPlainText("❌ Error: No active tab")
                self.extract_context_btn.setEnabled(True)
                return

            # Get URL and title
            current_url = current_tab.url().toString()
            current_title = current_tab.page().title()

            # Request HTML
            def on_html_received(html):
                try:
                    # Extract text content
                    extracted_text = self._simple_extract_text(html, current_url, current_title)

                    # Display in text edit
                    self.context_display.setPlainText(extracted_text)

                    # Add success message to chat
                    self.add_message_to_chat("System", f"✅ Page content extracted: {len(extracted_text)} characters", "assistant")

                except Exception as e:
                    error_msg = f"❌ Error extracting content: {str(e)}"
                    self.context_display.setPlainText(error_msg)
                    print(error_msg)
                    import traceback
                    traceback.print_exc()
                finally:
                    self.extract_context_btn.setEnabled(True)

            # Request HTML asynchronously
            current_tab.page().toHtml(on_html_received)

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            self.context_display.setPlainText(error_msg)
            print(error_msg)
            import traceback
            traceback.print_exc()
            self.extract_context_btn.setEnabled(True)

    def _simple_extract_text(self, html, url, title):
        """Simple and effective text extraction"""
        try:
            from bs4 import BeautifulSoup

            # Parse HTML
            soup = BeautifulSoup(html, 'lxml')

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript', 'form']):
                element.decompose()

            # Get all text
            text = soup.get_text(separator='\n', strip=True)

            # Clean up
            lines = []
            for line in text.split('\n'):
                line = line.strip()
                if line and len(line) > 2:  # Skip very short lines
                    lines.append(line)

            clean_text = '\n'.join(lines)

            # Build context
            context = f"""PAGE: {title}
URL: {url}

CONTENT:
{clean_text[:3000]}

{'[Content truncated - showing first 3000 characters]' if len(clean_text) > 3000 else '[End of content]'}"""

            return context

        except ImportError:
            # Fallback without BeautifulSoup
            import re
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'\s+', ' ', text).strip()

            return f"""PAGE: {title}
URL: {url}

CONTENT:
{text[:3000]}

{'[Content truncated]' if len(text) > 3000 else '[End]'}"""
        except Exception as e:
            return f"Error extracting text: {str(e)}"

    def get_current_context(self):
        """DEPRECATED - Now using context_display directly"""
        # This function is kept for compatibility but no longer used
        return self.context_display.toPlainText() if hasattr(self, 'context_display') else "" 