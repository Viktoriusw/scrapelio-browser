#!/usr/bin/env python3
"""
GenTab Panel - Interfaz de Pestañas Generativas para Scrapelio Browser

Panel conversacional AI-First que permite generar aplicaciones web interactivas
a partir del contenido de las pestañas abiertas, inspirado en Google Disco GenTabs.
"""

import html
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QFrame, QGroupBox, QProgressBar,
    QComboBox, QSpinBox, QLineEdit, QSizePolicy, QMessageBox,
    QTabWidget, QListWidget, QListWidgetItem, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, QSettings, QSize, Signal
from PySide6.QtGui import QFont, QColor, QIcon

from base_panel import BasePanel
from llm_client import LLMClient, LLMConfig, PROVIDER_LOCAL, PROVIDER_LLMAPI, LLMAPI_FREE_MODELS
from gentab_engine import GenTabEngine, TabContext, GenTabResult, GenTabStatus


class TabContextCard(QFrame):
    """Tarjeta visual que representa el contexto de una pestaña."""

    toggled = Signal(int, bool)

    def __init__(self, tab_context: TabContext, parent=None):
        super().__init__(parent)
        self.tab_context = tab_context
        self.selected = True
        self.setObjectName("tabContextCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(
            lambda state: self._on_toggle(state == Qt.Checked)
        )
        layout.addWidget(self.checkbox)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        title = self.tab_context.title
        if len(title) > 45:
            title = title[:42] + "..."
        self.title_label = QLabel(f"<b>{html.escape(title)}</b>")
        self.title_label.setObjectName("cardTitle")
        info_layout.addWidget(self.title_label)

        domain = self.tab_context.domain
        self.domain_label = QLabel(f"<span style='opacity:0.7'>{html.escape(domain)}</span>")
        self.domain_label.setObjectName("cardDomain")
        info_layout.addWidget(self.domain_label)

        layout.addLayout(info_layout, 1)

        chars = self.tab_context.content_length
        if chars > 0:
            if chars > 1000:
                label = f"{chars // 1000}k"
            else:
                label = str(chars)
            self.size_label = QLabel(f"{label} chars")
        else:
            self.size_label = QLabel("pendiente")
        self.size_label.setObjectName("cardSize")
        layout.addWidget(self.size_label)

    def _apply_style(self):
        self.setStyleSheet("""
            QFrame#tabContextCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e1b4b, stop:1 #312e81);
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 10px;
                min-height: 48px;
            }
            QFrame#tabContextCard:hover {
                border-color: rgba(99, 102, 241, 0.7);
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #252262, stop:1 #3b3791);
            }
            QLabel#cardTitle { color: #e2e8f0; font-size: 13px; }
            QLabel#cardDomain { color: #94a3b8; font-size: 11px; }
            QLabel#cardSize {
                color: #818cf8; font-size: 11px; font-weight: bold;
                background: rgba(99, 102, 241, 0.15);
                padding: 2px 8px; border-radius: 8px;
            }
            QCheckBox { spacing: 4px; }
            QCheckBox::indicator {
                width: 16px; height: 16px; border-radius: 4px;
                border: 2px solid #6366f1;
            }
            QCheckBox::indicator:checked {
                background: #6366f1;
                image: none;
            }
            QCheckBox::indicator:unchecked {
                background: transparent;
            }
        """)

    def _on_toggle(self, checked):
        self.selected = checked
        self.setProperty("selected", checked)
        opacity = "1.0" if checked else "0.4"
        self.setStyleSheet(self.styleSheet())
        self.toggled.emit(self.tab_context.index, checked)

    def update_content_size(self, size: int):
        self.tab_context.content_length = size
        if size > 1000:
            self.size_label.setText(f"{size // 1000}k chars")
        elif size > 0:
            self.size_label.setText(f"{size} chars")
        else:
            self.size_label.setText("sin datos")


class GenTabPanel(BasePanel):
    """Panel principal de GenTabs: interfaz conversacional para generar apps desde pestañas."""

    gentab_created = Signal(str, str)

    def __init__(self, parent=None):
        self.engine = GenTabEngine()
        self.tab_contexts = []
        self.context_cards = []
        self.server_url = ""
        self.llm_config = LLMConfig.load("GenTabs")
        self._pending_extractions = 0
        self._extracting = False
        self._status_anim_timer = None
        self._status_anim_frames = ["●", "◔", "◑", "◕"]
        self._status_anim_idx = 0
        super().__init__(parent)

        self.engine.gentab_started.connect(self._on_generation_started)
        self.engine.gentab_progress.connect(self._on_progress)
        self.engine.gentab_completed.connect(self._on_generation_complete)
        self.engine.gentab_error.connect(self._on_generation_error)

        self._load_settings()

    def get_tab_definitions(self):
        return [
            (self.create_main_tab, "✨ GenTab"),
            (self.create_settings_tab, "⚙️ Config"),
            (self.create_history_tab, "📜 Historial"),
        ]

    def post_setup_ui(self):
        self.set_object_name("genTabPanel")

    def create_main_tab(self):
        widget = QWidget()
        widget.setObjectName("genTabMain")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Header ---
        header = QFrame()
        header.setObjectName("genTabHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 16, 12)
        header_layout.setSpacing(6)

        title_row = QHBoxLayout()
        logo = QLabel("GenTab")
        logo.setObjectName("genTabLogo")
        title_row.addWidget(logo)
        title_row.addStretch()

        self.status_indicator = QLabel("●")
        self.status_indicator.setObjectName("statusDot")
        title_row.addWidget(self.status_indicator)
        self.status_label = QLabel("Listo")
        self.status_label.setObjectName("statusText")
        title_row.addWidget(self.status_label)
        header_layout.addLayout(title_row)

        subtitle = QLabel("Genera aplicaciones interactivas desde tus pestañas abiertas")
        subtitle.setObjectName("genTabSubtitle")
        header_layout.addWidget(subtitle)

        layout.addWidget(header)

        # --- Tab Context Section ---
        context_section = QFrame()
        context_section.setObjectName("contextSection")
        context_layout = QVBoxLayout(context_section)
        context_layout.setContentsMargins(16, 12, 16, 8)
        context_layout.setSpacing(8)

        ctx_header = QHBoxLayout()
        ctx_title = QLabel("📑 Pestañas abiertas")
        ctx_title.setObjectName("sectionTitle")
        ctx_header.addWidget(ctx_title)
        ctx_header.addStretch()

        self.tab_count_label = QLabel("0 pestañas")
        self.tab_count_label.setObjectName("tabCount")
        ctx_header.addWidget(self.tab_count_label)

        self.refresh_tabs_btn = QPushButton("🔄 Escanear")
        self.refresh_tabs_btn.setObjectName("scanBtn")
        self.refresh_tabs_btn.clicked.connect(self.scan_tabs)
        self.refresh_tabs_btn.setCursor(Qt.PointingHandCursor)
        ctx_header.addWidget(self.refresh_tabs_btn)
        context_layout.addLayout(ctx_header)

        self.tabs_scroll = QScrollArea()
        self.tabs_scroll.setWidgetResizable(True)
        self.tabs_scroll.setMaximumHeight(200)
        self.tabs_scroll.setFrameShape(QFrame.NoFrame)
        self.tabs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tabs_container = QWidget()
        self.tabs_list_layout = QVBoxLayout(self.tabs_container)
        self.tabs_list_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs_list_layout.setSpacing(6)
        self.tabs_list_layout.addStretch()
        self.tabs_scroll.setWidget(self.tabs_container)
        context_layout.addWidget(self.tabs_scroll)

        self.extract_btn = QPushButton("📥 Extraer contenido de pestañas")
        self.extract_btn.setObjectName("extractBtn")
        self.extract_btn.clicked.connect(self.extract_all_content)
        self.extract_btn.setCursor(Qt.PointingHandCursor)
        self.extract_btn.setEnabled(False)
        context_layout.addWidget(self.extract_btn)

        layout.addWidget(context_section)

        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("genTabProgress")
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # --- Messages Area ---
        self.messages_scroll = QScrollArea()
        self.messages_scroll.setWidgetResizable(True)
        self.messages_scroll.setFrameShape(QFrame.NoFrame)
        self.messages_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(16, 8, 16, 8)
        self.messages_layout.setSpacing(10)
        self.messages_layout.setAlignment(Qt.AlignTop)

        welcome = self._create_system_message(
            "Bienvenido a <b>GenTab</b> — el generador de aplicaciones interactivas.",
            "Escanea tus pestañas, extrae su contenido y describe qué aplicación necesitas. "
            "GenTab analizará todas las pestañas y generará una app web personalizada."
        )
        self.messages_layout.addWidget(welcome)
        self.messages_layout.addStretch()

        self.messages_scroll.setWidget(self.messages_container)
        layout.addWidget(self.messages_scroll, 1)

        # --- Input Area ---
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 12, 16, 16)
        input_layout.setSpacing(8)

        self.prompt_input = QTextEdit()
        self.prompt_input.setObjectName("promptInput")
        self.prompt_input.setPlaceholderText(
            "Describe qué aplicación quieres generar...\n"
            "Ej: \"Compara los productos de las pestañas abiertas en una tabla interactiva\""
        )
        self.prompt_input.setMinimumHeight(60)
        self.prompt_input.setMaximumHeight(100)
        self.prompt_input.setAcceptRichText(False)
        input_layout.addWidget(self.prompt_input)

        buttons_row = QHBoxLayout()

        self.generate_btn = QPushButton("✨ Generar GenTab")
        self.generate_btn.setObjectName("generateBtn")
        self.generate_btn.clicked.connect(self.generate_gentab)
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.setEnabled(False)
        buttons_row.addWidget(self.generate_btn)

        self.quick_actions = QComboBox()
        self.quick_actions.setObjectName("quickActions")
        self.quick_actions.addItem("⚡ Acciones rápidas...")
        self.quick_actions.addItem("📊 Comparar contenido de pestañas")
        self.quick_actions.addItem("📋 Resumir todas las pestañas")
        self.quick_actions.addItem("🗺️ Crear mapa de información")
        self.quick_actions.addItem("📚 Generar tarjetas de estudio")
        self.quick_actions.addItem("📈 Dashboard de datos")
        self.quick_actions.addItem("🔗 Mapa de enlaces y relaciones")
        self.quick_actions.currentIndexChanged.connect(self._on_quick_action)
        buttons_row.addWidget(self.quick_actions)

        input_layout.addLayout(buttons_row)
        layout.addWidget(input_frame)

        self._apply_main_styles(widget)
        return widget

    def create_settings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── Proveedor ──────────────────────────────────────────────────────────
        provider_group = QGroupBox("🌐 Proveedor de IA")
        prov_layout = QVBoxLayout()

        prov_row = QHBoxLayout()
        prov_row.addWidget(QLabel("Proveedor:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("🖥️ LM Studio / Local", PROVIDER_LOCAL)
        self.provider_combo.addItem("☁️ llmapi.ai (cloud gratuito)", PROVIDER_LLMAPI)
        prov_row.addWidget(self.provider_combo)
        prov_layout.addLayout(prov_row)

        # LM Studio URL (solo visible en modo local)
        self.local_url_widget = QWidget()
        local_url_layout = QHBoxLayout(self.local_url_widget)
        local_url_layout.setContentsMargins(0, 0, 0, 0)
        local_url_layout.addWidget(QLabel("URL servidor:"))
        self.server_url_input = QLineEdit()
        self.server_url_input.setPlaceholderText("http://localhost:1234")
        self.server_url_input.textChanged.connect(self._on_url_changed)
        local_url_layout.addWidget(self.server_url_input)
        prov_layout.addWidget(self.local_url_widget)

        # llmapi.ai (solo visible en modo cloud)
        self.cloud_widget = QWidget()
        cloud_layout = QVBoxLayout(self.cloud_widget)
        cloud_layout.setContentsMargins(0, 0, 0, 0)

        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API Key:"))
        self.llmapi_key_input = QLineEdit()
        self.llmapi_key_input.setPlaceholderText("lak-...")
        self.llmapi_key_input.setEchoMode(QLineEdit.Password)
        key_row.addWidget(self.llmapi_key_input)
        show_key_btn = QPushButton("👁")
        show_key_btn.setMaximumWidth(32)
        show_key_btn.setCheckable(True)
        show_key_btn.toggled.connect(
            lambda on: self.llmapi_key_input.setEchoMode(
                QLineEdit.Normal if on else QLineEdit.Password
            )
        )
        key_row.addWidget(show_key_btn)
        cloud_layout.addLayout(key_row)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Modelo:"))
        self.llmapi_model_combo = QComboBox()
        for m in LLMAPI_FREE_MODELS:
            self.llmapi_model_combo.addItem(m)
        model_row.addWidget(self.llmapi_model_combo)
        cloud_layout.addLayout(model_row)

        info_cloud = QLabel(
            '🔑 Obtén tu API key gratuita en <a href="https://llmapi.ai" style="color:#818cf8;">llmapi.ai</a>'
        )
        info_cloud.setOpenExternalLinks(True)
        info_cloud.setTextFormat(Qt.RichText)
        info_cloud.setStyleSheet("color: #94a3b8; font-size: 11px;")
        cloud_layout.addWidget(info_cloud)
        prov_layout.addWidget(self.cloud_widget)

        # Estado y botones
        self.server_status = QLabel("Sin configurar")
        self.server_status.setObjectName("serverStatus")
        prov_layout.addWidget(self.server_status)

        btn_row = QHBoxLayout()
        test_btn = QPushButton("🔗 Probar conexión")
        test_btn.clicked.connect(self._test_connection)
        btn_row.addWidget(test_btn)
        save_btn = QPushButton("💾 Guardar")
        save_btn.clicked.connect(self._save_settings)
        btn_row.addWidget(save_btn)
        prov_layout.addLayout(btn_row)

        provider_group.setLayout(prov_layout)
        layout.addWidget(provider_group)

        # ── Generación ─────────────────────────────────────────────────────────
        gen_group = QGroupBox("🎛️ Generación")
        gen_layout = QVBoxLayout()

        temp_row = QHBoxLayout()
        temp_row.addWidget(QLabel("Temperatura (creatividad):"))
        self.temp_spin = QSpinBox()
        self.temp_spin.setRange(1, 15)
        self.temp_spin.setValue(7)
        self.temp_spin.setSuffix(" /10")
        temp_row.addWidget(self.temp_spin)
        gen_layout.addLayout(temp_row)

        tokens_row = QHBoxLayout()
        tokens_row.addWidget(QLabel("Máx tokens:"))
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(1000, 16384)
        self.tokens_spin.setValue(max(4000, int(self.llm_config.max_tokens)))
        self.tokens_spin.setSingleStep(500)
        tokens_row.addWidget(self.tokens_spin)
        gen_layout.addLayout(tokens_row)

        gen_group.setLayout(gen_layout)
        layout.addWidget(gen_group)

        layout.addStretch()

        # Conectar cambio de proveedor para mostrar/ocultar secciones
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        # Inicializar UI con valores guardados
        self._populate_settings_ui()
        return widget

    def _populate_settings_ui(self):
        """Rellena los controles de settings con los valores de llm_config."""
        idx = 0 if self.llm_config.provider == PROVIDER_LOCAL else 1
        if hasattr(self, "provider_combo"):
            self.provider_combo.setCurrentIndex(idx)
        if hasattr(self, "server_url_input"):
            self.server_url_input.setText(self.llm_config.local_url or "")
        if hasattr(self, "llmapi_key_input"):
            self.llmapi_key_input.setText(self.llm_config.llmapi_key or "")
        if hasattr(self, "llmapi_model_combo"):
            mi = self.llmapi_model_combo.findText(self.llm_config.llmapi_model)
            if mi >= 0:
                self.llmapi_model_combo.setCurrentIndex(mi)
        if hasattr(self, "tokens_spin"):
            self.tokens_spin.setValue(max(4000, int(self.llm_config.max_tokens)))
        self._on_provider_changed()

    def _on_provider_changed(self):
        """Muestra/oculta secciones según proveedor seleccionado."""
        if not hasattr(self, "provider_combo"):
            return
        is_local = self.provider_combo.currentData() == PROVIDER_LOCAL
        if hasattr(self, "local_url_widget"):
            self.local_url_widget.setVisible(is_local)
        if hasattr(self, "cloud_widget"):
            self.cloud_widget.setVisible(not is_local)

    def create_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(QLabel("<b>Historial de GenTabs</b>"))
        header.addStretch()
        clear_btn = QPushButton("🗑️ Limpiar")
        clear_btn.clicked.connect(self._clear_history)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        self.history_list.setAlternatingRowColors(True)
        layout.addWidget(self.history_list)

        self._refresh_history()
        return widget

    # ========================================================================
    # Core Actions
    # ========================================================================

    def scan_tabs(self):
        main_window = self.window()
        if not hasattr(main_window, 'tab_manager'):
            self._add_error_message("No se puede acceder al gestor de pestañas.")
            return

        for i in reversed(range(self.tabs_list_layout.count())):
            item = self.tabs_list_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        self.context_cards.clear()
        self.tab_contexts, _ = self.engine.extract_all_tabs_context(main_window.tab_manager)

        for tc in self.tab_contexts:
            card = TabContextCard(tc)
            card.toggled.connect(self._on_tab_toggled)
            self.context_cards.append(card)
            self.tabs_list_layout.insertWidget(self.tabs_list_layout.count() - 1, card)

        count = len(self.tab_contexts)
        self.tab_count_label.setText(f"{count} pestaña{'s' if count != 1 else ''}")
        self.extract_btn.setEnabled(count > 0)

        if count > 0:
            self._add_system_message(
                f"Se detectaron <b>{count}</b> pestañas. "
                "Haz clic en <b>Extraer contenido</b> para analizar su contenido."
            )
        else:
            self._add_system_message("No se encontraron pestañas con contenido web.")

    def extract_all_content(self):
        if self._extracting:
            return

        main_window = self.window()
        if not hasattr(main_window, 'tab_manager'):
            return

        selected = [tc for tc in self.tab_contexts
                    if any(c.tab_context.index == tc.index and c.selected for c in self.context_cards)]

        if not selected:
            self._add_error_message("Selecciona al menos una pestaña para extraer.")
            return

        self._extracting = True
        self._pending_extractions = len(selected)
        self._completed_extractions = 0
        self.extract_btn.setEnabled(False)
        self.extract_btn.setText("⏳ Extrayendo...")
        self.progress_bar.show()
        self._set_status("extracting", "Extrayendo contenido...")
        QTimer.singleShot(15000, self._handle_extraction_timeout)

        for tc in selected:
            browser = main_window.tab_manager.tabs.widget(tc.index)
            if browser:
                self.engine.extract_tab_html(browser, tc, self._on_tab_extracted)
            else:
                self._pending_extractions -= 1

    def _handle_extraction_timeout(self):
        """Evita bloqueo si alguna pestaña no devuelve HTML a tiempo."""
        if not self._extracting:
            return
        self._extracting = False
        self.extract_btn.setEnabled(True)
        self.extract_btn.setText("📥 Extraer contenido de pestañas")
        self.progress_bar.hide()
        self.generate_btn.setEnabled(True)
        self._set_status("ready", "Extracción parcial completada")
        self._add_system_message(
            "⏱️ Algunas pestañas tardaron demasiado. Se continuará con el contenido disponible."
        )

    def _on_tab_extracted(self, tab_context: TabContext):
        self._completed_extractions += 1

        for card in self.context_cards:
            if card.tab_context.index == tab_context.index:
                card.update_content_size(tab_context.content_length)
                break

        if self._completed_extractions >= self._pending_extractions:
            self._extracting = False
            self.extract_btn.setEnabled(True)
            self.extract_btn.setText("📥 Extraer contenido de pestañas")
            self.progress_bar.hide()
            self.generate_btn.setEnabled(True)
            self._set_status("ready", "Contenido extraído")

            total_chars = sum(tc.content_length for tc in self.tab_contexts if tc.content)
            self._add_system_message(
                f"Contenido extraído: <b>{total_chars:,}</b> caracteres de "
                f"<b>{self._completed_extractions}</b> pestañas. "
                "Ahora describe qué aplicación quieres generar."
            )

    def generate_gentab(self):
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "GenTab", "Escribe una descripción de la aplicación que quieres generar.")
            return

        # Asegurar que la config está actualizada antes de generar
        cfg = self.llm_config
        if cfg.provider == PROVIDER_LOCAL and not cfg.local_url:
            QMessageBox.warning(self, "GenTab", "Configura la URL del servidor LLM en la pestaña Config.")
            return
        if cfg.provider == PROVIDER_LLMAPI and not cfg.llmapi_key:
            QMessageBox.warning(self, "GenTab", "Introduce tu API key de llmapi.ai en la pestaña Config.")
            return

        selected = [tc for tc in self.tab_contexts
                    if tc.content and tc.content_length > 0
                    and any(c.tab_context.index == tc.index and c.selected for c in self.context_cards)]

        if not selected:
            QMessageBox.warning(self, "GenTab", "Extrae el contenido de al menos una pestaña primero.")
            return

        self._add_user_message(prompt)
        self.prompt_input.clear()

        temperature = self.temp_spin.value() / 10.0 if hasattr(self, "temp_spin") else 0.7
        max_tokens = self.tokens_spin.value() if hasattr(self, "tokens_spin") else cfg.max_tokens

        cfg.temperature = temperature
        cfg.max_tokens = max_tokens

        self.engine.generate_gentab(
            self.server_url, prompt, selected, temperature, max_tokens, llm_config=cfg
        )

    # ========================================================================
    # Signal Handlers
    # ========================================================================

    def _on_generation_started(self):
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("⏳ Generando...")
        self.progress_bar.show()
        self._set_status("generating", "Generando aplicación...")

    def _on_progress(self, message: str):
        self._add_system_message(message)

    def _on_generation_complete(self, result: GenTabResult):
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("✨ Generar GenTab")
        self.progress_bar.hide()
        self._set_status("ready", "GenTab generada")

        sources = len(result.source_tabs)
        self._add_gentab_message(
            f"<b>{html.escape(result.title)}</b>",
            f"Generada en {result.generation_time}s desde {sources} pestañas. "
            f"Modelo: {result.model_used}",
            result
        )
        self._refresh_history()
        self.gentab_created.emit(result.title, result.html)

    def _on_generation_error(self, error: str):
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("✨ Generar GenTab")
        self.progress_bar.hide()
        self._set_status("error", "Error")
        self._add_error_message(error)

    def _on_tab_toggled(self, index: int, checked: bool):
        pass

    def _on_quick_action(self, idx: int):
        if idx <= 0:
            return
        prompts = {
            1: "Create a sortable comparison TABLE with one row per tab/item. Extract name, key features, pros/cons from each tab. Add column sort buttons and a search filter. Use real source URLs for links.",
            2: "Create expandable SUMMARY CARDS for each tab. Extract: title, 3-5 key points as bullet list, main conclusion. Add expand/collapse toggle per card and a search box. Link each card to its real source URL.",
            3: "Create an interactive MIND MAP showing topics from each tab as connected nodes. Use SVG or CSS positioned elements. Clicking a node shows a detail panel with extracted key info and link to source.",
            4: "Create interactive FLASHCARDS from the tab content. Extract question-answer pairs from the data. Each card has a front (question) and back (answer) with a flip animation on click. Add navigation arrows.",
            5: "Create a DATA DASHBOARD with: item count, domain distribution as horizontal bars, key metrics extracted from content. Use CSS-animated progress bars and counters. Each section links to source tabs.",
            6: "Create a LINK DIRECTORY showing all real destination URLs found in the tabs, grouped by domain. Show link text, URL, and source tab. Add filter by domain and search. Make each link clickable.",
        }
        self.prompt_input.setPlainText(prompts.get(idx, ""))
        self.quick_actions.setCurrentIndex(0)

    def _on_url_changed(self, text):
        self.server_url = text.strip()
        self.llm_config.local_url = self.server_url

    # ========================================================================
    # UI Message Helpers
    # ========================================================================

    def _create_system_message(self, title: str, body: str = "") -> QFrame:
        frame = QFrame()
        frame.setObjectName("systemMsg")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setTextFormat(Qt.RichText)
        title_label.setWordWrap(True)
        title_label.setObjectName("sysMsgTitle")
        layout.addWidget(title_label)

        if body:
            body_label = QLabel(body)
            body_label.setTextFormat(Qt.RichText)
            body_label.setWordWrap(True)
            body_label.setObjectName("sysMsgBody")
            layout.addWidget(body_label)

        frame.setStyleSheet("""
            QFrame#systemMsg {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(99, 102, 241, 0.08), stop:1 rgba(139, 92, 246, 0.08));
                border: 1px solid rgba(99, 102, 241, 0.2);
                border-radius: 12px;
            }
            QLabel#sysMsgTitle { color: #c7d2fe; font-size: 13px; }
            QLabel#sysMsgBody { color: #94a3b8; font-size: 12px; }
        """)
        return frame

    def _add_system_message(self, text: str):
        frame = QFrame()
        frame.setObjectName("sysMsg")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)

        timestamp = datetime.now().strftime("%H:%M")
        label = QLabel(f"<span style='color:#6366f1;font-size:11px'>{timestamp}</span> {text}")
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(label)

        frame.setStyleSheet("""
            QFrame#sysMsg {
                background: rgba(30, 27, 75, 0.5);
                border-radius: 8px;
                border: 1px solid rgba(99, 102, 241, 0.1);
            }
        """)
        idx = self.messages_layout.count() - 1
        self.messages_layout.insertWidget(idx, frame)
        self._scroll_to_bottom()

    def _add_user_message(self, text: str):
        frame = QFrame()
        frame.setObjectName("userMsg")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)

        header = QLabel(f"<b style='color:#818cf8'>Tú</b> "
                        f"<span style='color:#64748b;font-size:11px'>{datetime.now().strftime('%H:%M')}</span>")
        header.setTextFormat(Qt.RichText)
        layout.addWidget(header)

        msg = QLabel(html.escape(text))
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #e2e8f0; font-size: 13px; padding-top: 4px;")
        layout.addWidget(msg)

        frame.setStyleSheet("""
            QFrame#userMsg {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(99, 102, 241, 0.15), stop:1 rgba(99, 102, 241, 0.05));
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 12px;
            }
        """)
        idx = self.messages_layout.count() - 1
        self.messages_layout.insertWidget(idx, frame)
        self._scroll_to_bottom()

    def _add_gentab_message(self, title: str, info: str, result: GenTabResult):
        frame = QFrame()
        frame.setObjectName("gentabMsg")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QLabel(f"<span style='color:#818cf8;font-size:11px'>✨ GenTab creada</span>")
        header.setTextFormat(Qt.RichText)
        layout.addWidget(header)

        title_label = QLabel(title)
        title_label.setTextFormat(Qt.RichText)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("color: #e2e8f0; font-size: 15px;")
        layout.addWidget(title_label)

        info_label = QLabel(info)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(info_label)

        open_btn = QPushButton("🚀 Abrir GenTab en nueva pestaña")
        open_btn.setObjectName("openGenTabBtn")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(lambda: self.gentab_created.emit(result.title, result.html))
        open_btn.setStyleSheet("""
            QPushButton#openGenTabBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #818cf8);
                color: white; border: none; border-radius: 8px;
                padding: 10px 20px; font-weight: bold; font-size: 13px;
            }
            QPushButton#openGenTabBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #818cf8, stop:1 #a5b4fc);
            }
        """)
        layout.addWidget(open_btn)

        sources_text = " · ".join(
            f"<a href='{s['url']}' style='color:#818cf8;text-decoration:none'>{s['domain']}</a>"
            for s in result.source_tabs
        )
        sources = QLabel(f"<span style='color:#64748b;font-size:11px'>Fuentes: {sources_text}</span>")
        sources.setTextFormat(Qt.RichText)
        sources.setWordWrap(True)
        sources.setOpenExternalLinks(True)
        layout.addWidget(sources)

        frame.setStyleSheet("""
            QFrame#gentabMsg {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e1b4b, stop:1 #312e81);
                border: 2px solid rgba(99, 102, 241, 0.4);
                border-radius: 14px;
            }
        """)
        idx = self.messages_layout.count() - 1
        self.messages_layout.insertWidget(idx, frame)
        self._scroll_to_bottom()

    def _add_error_message(self, text: str):
        frame = QFrame()
        frame.setObjectName("errorMsg")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)

        label = QLabel(f"❌ {html.escape(text)}")
        label.setWordWrap(True)
        label.setStyleSheet("color: #fca5a5; font-size: 12px;")
        layout.addWidget(label)

        frame.setStyleSheet("""
            QFrame#errorMsg {
                background: rgba(127, 29, 29, 0.3);
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 8px;
            }
        """)
        idx = self.messages_layout.count() - 1
        self.messages_layout.insertWidget(idx, frame)
        self._scroll_to_bottom()

    def _set_status(self, status: str, text: str):
        colors = {
            "ready": "#22c55e",
            "extracting": "#f59e0b",
            "generating": "#6366f1",
            "error": "#ef4444",
        }
        color = colors.get(status, "#94a3b8")
        self._stop_status_animation()
        self.status_indicator.setText("●")
        self.status_indicator.setStyleSheet(f"color: {color}; font-size: 16px;")
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        if status in ("extracting", "generating"):
            self._start_status_animation(color)

    def _start_status_animation(self, color: str):
        if self._status_anim_timer is None:
            self._status_anim_timer = QTimer(self)
            self._status_anim_timer.timeout.connect(lambda: self._tick_status_animation(color))
        self._status_anim_idx = 0
        self._status_anim_timer.start(180)

    def _tick_status_animation(self, color: str):
        frame = self._status_anim_frames[self._status_anim_idx % len(self._status_anim_frames)]
        self._status_anim_idx += 1
        self.status_indicator.setText(frame)
        self.status_indicator.setStyleSheet(f"color: {color}; font-size: 16px;")

    def _stop_status_animation(self):
        if self._status_anim_timer and self._status_anim_timer.isActive():
            self._status_anim_timer.stop()

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.messages_scroll.verticalScrollBar().setValue(
            self.messages_scroll.verticalScrollBar().maximum()
        ))

    # ========================================================================
    # Settings & History
    # ========================================================================

    def _load_settings(self):
        self.llm_config = LLMConfig.load("GenTabs")
        # Compatibilidad hacia atrás: leer URL antigua si existe
        old_settings = QSettings("Scrapelio", "GenTabs")
        old_url = old_settings.value("server_url", "")
        if old_url and not self.llm_config.local_url:
            self.llm_config.local_url = old_url
        self.server_url = self.llm_config.local_url
        self._populate_settings_ui()

    def _save_settings(self):
        if hasattr(self, "provider_combo"):
            self.llm_config.provider = self.provider_combo.currentData()
        if hasattr(self, "server_url_input"):
            self.llm_config.local_url = self.server_url_input.text().strip()
        if hasattr(self, "llmapi_key_input"):
            self.llm_config.llmapi_key = self.llmapi_key_input.text().strip()
        if hasattr(self, "llmapi_model_combo"):
            self.llm_config.llmapi_model = self.llmapi_model_combo.currentText()
        if hasattr(self, "tokens_spin"):
            self.llm_config.max_tokens = self.tokens_spin.value()
        self.llm_config.save("GenTabs")
        # Mantener server_url para compatibilidad con engine
        self.server_url = self.llm_config.local_url
        self._add_system_message("✅ Configuración guardada.")

    def _test_connection(self):
        self._save_settings()
        client = LLMClient(self.llm_config)
        ok, info = client.test()
        if ok:
            self.server_status.setText(f"✅ {info}")
            self.server_status.setStyleSheet("color: #22c55e;")
        else:
            self.server_status.setText(f"❌ {info[:80]}")
            self.server_status.setStyleSheet("color: #ef4444;")

    def _refresh_history(self):
        if not hasattr(self, 'history_list'):
            return
        self.history_list.clear()
        for result in self.engine.get_history():
            dt = result.created_at[:16].replace('T', ' ') if result.created_at else "?"
            item_text = f"{dt} — {result.title}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, result)
            self.history_list.addItem(item)

    def _clear_history(self):
        self.engine.clear_history()
        self._refresh_history()

    # ========================================================================
    # Theme
    # ========================================================================

    def _apply_main_styles(self, widget):
        theme_name = str(QSettings("Scrapelio", "Settings").value("theme", "light")).lower()
        is_dark = theme_name == "dark"

        if is_dark:
            widget.setStyleSheet("""
                QWidget#genTabMain { background: #0f0f23; }
                QFrame#genTabHeader {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e1b4b, stop:1 #312e81);
                    border-bottom: 1px solid rgba(99, 102, 241, 0.3);
                }
                QLabel#genTabLogo {
                    color: white; font-size: 20px; font-weight: bold;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #a78bfa);
                    padding: 4px 14px; border-radius: 8px;
                }
                QLabel#genTabSubtitle { color: #94a3b8; font-size: 12px; }
                QLabel#statusDot { font-size: 16px; }
                QLabel#statusText { font-size: 12px; }
                QFrame#contextSection {
                    background: rgba(15, 15, 35, 0.8);
                    border-bottom: 1px solid rgba(99, 102, 241, 0.15);
                }
                QLabel#sectionTitle { color: #c7d2fe; font-size: 13px; font-weight: bold; }
                QLabel#tabCount {
                    color: #818cf8; font-size: 12px;
                    background: rgba(99, 102, 241, 0.12);
                    padding: 2px 10px; border-radius: 10px;
                }
                QPushButton#scanBtn, QPushButton#extractBtn {
                    background: rgba(99, 102, 241, 0.15);
                    color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.3);
                    border-radius: 8px; padding: 8px 16px; font-size: 12px;
                }
                QPushButton#scanBtn:hover, QPushButton#extractBtn:hover {
                    background: rgba(99, 102, 241, 0.25);
                    border-color: rgba(99, 102, 241, 0.5);
                }
                QPushButton#generateBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #818cf8);
                    color: white; border: none; border-radius: 10px;
                    padding: 12px 24px; font-weight: bold; font-size: 14px; min-height: 20px;
                }
                QPushButton#generateBtn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #818cf8, stop:1 #a5b4fc);
                }
                QPushButton#generateBtn:disabled { background: #374151; color: #6b7280; }
                QFrame#inputFrame { background: #0f0f23; border-top: 1px solid rgba(99, 102, 241, 0.15); }
                QTextEdit#promptInput {
                    background: #1a1a3e;
                    color: #e2e8f0; border: 1px solid rgba(99, 102, 241, 0.3);
                    border-radius: 10px; padding: 10px; font-size: 13px;
                    selection-background-color: #6366f1;
                }
                QTextEdit#promptInput:focus { border-color: #6366f1; }
                QComboBox#quickActions {
                    background: rgba(99, 102, 241, 0.1);
                    color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.3);
                    border-radius: 8px; padding: 8px 12px; font-size: 12px;
                }
                QProgressBar#genTabProgress { background: #1e1b4b; border: none; }
                QProgressBar#genTabProgress::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #a78bfa);
                }
                QScrollArea { background: transparent; border: none; }
                QScrollBar:vertical { background: #0f0f23; width: 8px; border: none; }
                QScrollBar::handle:vertical { background: #374151; border-radius: 4px; min-height: 30px; }
                QScrollBar::handle:vertical:hover { background: #4b5563; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            """)
        else:
            widget.setStyleSheet("""
                QWidget#genTabMain { background: #f6f8fc; }
                QFrame#genTabHeader {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #eef2ff);
                    border-bottom: 1px solid rgba(79, 70, 229, 0.18);
                }
                QLabel#genTabLogo {
                    color: white; font-size: 20px; font-weight: bold;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #818cf8);
                    padding: 4px 14px; border-radius: 8px;
                }
                QLabel#genTabSubtitle { color: #64748b; font-size: 12px; }
                QLabel#statusDot { font-size: 16px; }
                QLabel#statusText { font-size: 12px; color: #334155; }
                QFrame#contextSection {
                    background: rgba(79, 70, 229, 0.06);
                    border-bottom: 1px solid rgba(79, 70, 229, 0.15);
                }
                QLabel#sectionTitle { color: #1f2937; font-size: 13px; font-weight: bold; }
                QLabel#tabCount {
                    color: #4f46e5; font-size: 12px;
                    background: rgba(79, 70, 229, 0.10);
                    padding: 2px 10px; border-radius: 10px;
                }
                QPushButton#scanBtn, QPushButton#extractBtn {
                    background: rgba(79, 70, 229, 0.10);
                    color: #4338ca; border: 1px solid rgba(79, 70, 229, 0.25);
                    border-radius: 8px; padding: 8px 16px; font-size: 12px;
                }
                QPushButton#scanBtn:hover, QPushButton#extractBtn:hover {
                    background: rgba(79, 70, 229, 0.18);
                    border-color: rgba(79, 70, 229, 0.45);
                }
                QPushButton#generateBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
                    color: white; border: none; border-radius: 10px;
                    padding: 12px 24px; font-weight: bold; font-size: 14px; min-height: 20px;
                }
                QPushButton#generateBtn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #818cf8);
                }
                QPushButton#generateBtn:disabled { background: #e5e7eb; color: #6b7280; }
                QFrame#inputFrame { background: #f6f8fc; border-top: 1px solid rgba(79, 70, 229, 0.12); }
                QTextEdit#promptInput {
                    background: #ffffff;
                    color: #1f2937; border: 1px solid rgba(79, 70, 229, 0.22);
                    border-radius: 10px; padding: 10px; font-size: 13px;
                    selection-background-color: #4f46e5;
                }
                QTextEdit#promptInput:focus { border-color: #4f46e5; }
                QComboBox#quickActions {
                    background: rgba(79, 70, 229, 0.08);
                    color: #1f2937; border: 1px solid rgba(79, 70, 229, 0.2);
                    border-radius: 8px; padding: 8px 12px; font-size: 12px;
                }
                QProgressBar#genTabProgress { background: #e0e7ff; border: none; }
                QProgressBar#genTabProgress::chunk {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #818cf8);
                }
                QScrollArea { background: transparent; border: none; }
                QScrollBar:vertical { background: #eef2f7; width: 8px; border: none; }
                QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 4px; min-height: 30px; }
                QScrollBar::handle:vertical:hover { background: #94a3b8; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            """)

    def _on_theme_changed(self, theme_name):
        """Reaplicar estilos del panel cuando cambia el tema global."""
        super()._on_theme_changed(theme_name)
        if hasattr(self, "tab_widget") and self.tab_widget and self.tab_widget.count() > 0:
            main_widget = self.tab_widget.widget(0)
            if main_widget:
                self._apply_main_styles(main_widget)
