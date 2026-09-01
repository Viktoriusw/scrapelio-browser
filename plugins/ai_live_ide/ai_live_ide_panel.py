#!/usr/bin/env python3
"""
AI Live IDE — Panel principal del plugin premium estrella de Scrapelio Browser.

Características:
  - Editor Monaco embebido (QWebEngineView) con detección de lenguaje
  - Live Preview HTML/CSS/JS en tiempo real (QWebEngineView vía file://)
  - Asistente IA vía Hugging Face Inference Router (modelo Qwen2.5-Coder)
  - Auto-reload con QFileSystemWatcher
  - Tema oscuro alineado con el motor de temas del navegador
  - Acceso protegido por suscripción premium (@requires_premium)

Esta clase hereda de `BasePanel` (de `base_panel.py`) y de `PremiumMixin`
(de `premium_decorators.py`) tal y como hacen el resto de plugins premium
del proyecto (ej. `PremiumScrapingPanel`).
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Dict

from PySide6.QtCore import (
    QFileSystemWatcher,
    QObject,
    QSize,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QDesktopServices,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFileSystemModel,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QToolBar,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineSettings
    _WEBENGINE_AVAILABLE = True
except ImportError:  # pragma: no cover - PySide6 sin QtWebEngine
    _WEBENGINE_AVAILABLE = False

from base_panel import BasePanel
from premium_decorators import PremiumMixin, requires_premium

# Chat IA — workers, parser y catálogo de modelos viven en ai_chat.py
# para mantener este archivo enfocado en UI y orquestación.
try:
    from ai_chat import (  # type: ignore[import]
        AIChatMessage,
        AIChatWorker,
        AIFileChange,
        CodeBlockParser,
        HF_CHAT_MAX_TOKENS,
        HF_CODE_MODELS,
        HF_DEFAULT_MODEL_SLUG,
        MAX_HISTORY_MESSAGES,
        ProjectContextBuilder,
        build_system_prompt,
    )
    _AI_CHAT_AVAILABLE = True
except ImportError:
    try:
        # Carga relativa cuando se importa como paquete (plugins.ai_live_ide.*)
        from .ai_chat import (
            AIChatMessage,
            AIChatWorker,
            AIFileChange,
            CodeBlockParser,
            HF_CHAT_MAX_TOKENS,
            HF_CODE_MODELS,
            HF_DEFAULT_MODEL_SLUG,
            MAX_HISTORY_MESSAGES,
            ProjectContextBuilder,
            build_system_prompt,
        )
        _AI_CHAT_AVAILABLE = True
    except ImportError as _exc:
        _AI_CHAT_AVAILABLE = False
        HF_CHAT_MAX_TOKENS = 8192  # referencia segura si falta el módulo
        print(f"[WARNING] ai_chat module not available: {_exc}")

logger = logging.getLogger(__name__)

# Iconos de toolbar (lógicos × lógicos, coincide con strip_icons / navbar)
IDE_TOOLBAR_ICON_SIZE = QSize(20, 20)
IDE_CHAT_CHROME_ICON_SIZE = QSize(16, 16)

# ────────────────────────────────────────────────────────────────────────────
# Constantes del plugin
# ────────────────────────────────────────────────────────────────────────────

PLUGIN_ID = "ai_live_ide"
FEATURE_AI_EDIT = "ai_code_edit"
FEATURE_AI_CHAT = "ai_chat"
FEATURE_PROJECT_OPEN = "project_open"

HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
HF_DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
HF_REQUEST_TIMEOUT = 90

PREVIEWABLE_EXTENSIONS = {".html", ".htm", ".css", ".js", ".svg"}

AUTOSAVE_INTERVAL_MS = 1500  # debounce del autoguardado

# Qt WebEngine a veces no emite titleChanged cuando JS asigna document.title;
# sondeamos editorAPI tras cargar monaco.html hasta que exista (o timeout).
EDITOR_JS_READY_POLL_MS = 150
EDITOR_JS_READY_MAX_ATTEMPTS = 120  # ~18 s (CDN Monaco)


# ────────────────────────────────────────────────────────────────────────────
# Worker IA — llamada a Hugging Face Inference Router en hilo separado
# ────────────────────────────────────────────────────────────────────────────

class _AICodeEditWorker(QThread):
    """Hilo que envía el código actual a Hugging Face y devuelve el código editado."""

    finished_ok = Signal(str)        # código editado
    finished_error = Signal(str)     # mensaje de error
    progress = Signal(str)           # mensaje informativo

    def __init__(
        self,
        api_token: str,
        model: str,
        language: str,
        instruction: str,
        code: str,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._token = api_token
        self._model = model or HF_DEFAULT_MODEL
        self._language = language or "plaintext"
        self._instruction = (instruction or "").strip()
        self._code = code or ""

    def run(self) -> None:
        try:
            import requests  # local import: evita coste si el plugin no se usa
        except ImportError:
            self.finished_error.emit("La librería 'requests' no está instalada.")
            return
        if not self._token:
            self.finished_error.emit(
                "Falta el token de Hugging Face. Configúralo en el panel de "
                "Chat IA (proveedor 'huggingface') o en variable de entorno "
                "HUGGINGFACE_TOKEN."
            )
            return
        instruction = self._instruction or "Mejora, refactoriza y corrige errores"

        system_prompt = (
            "Eres un asistente de programación experto integrado en el IDE de "
            "Scrapelio Browser. Recibes el código fuente actual y una "
            "instrucción del usuario. Responde EXCLUSIVAMENTE con el código "
            "fuente editado completo, sin explicaciones, sin comentarios "
            "introductorios y sin envolverlo en bloques markdown. "
            "Mantén la indentación, el estilo y el lenguaje originales."
        )
        user_prompt = (
            f"Lenguaje: {self._language}\n"
            f"Instrucción: {instruction}\n\n"
            f"--- CÓDIGO ACTUAL ---\n{self._code}\n--- FIN ---\n\n"
            "Devuelve únicamente el código editado."
        )

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 4000,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        try:
            self.progress.emit("Contactando Hugging Face Inference Router…")
            resp = requests.post(
                HF_ROUTER_URL,
                json=payload,
                headers=headers,
                timeout=HF_REQUEST_TIMEOUT,
            )
        except requests.exceptions.Timeout:
            self.finished_error.emit(
                f"Hugging Face no respondió en {HF_REQUEST_TIMEOUT}s "
                "(modelo frío). Inténtalo de nuevo en unos segundos."
            )
            return
        except requests.exceptions.ConnectionError as exc:
            self.finished_error.emit(f"Sin conexión a Hugging Face: {exc}")
            return
        except Exception as exc:  # noqa: BLE001
            self.finished_error.emit(f"Error de red: {exc}")
            return
        if resp.status_code != 200:
            preview = resp.text[:300].replace("\n", " ")
            self.finished_error.emit(
                f"HTTP {resp.status_code} desde Hugging Face: {preview}"
            )
            return
        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            self.finished_error.emit(f"Respuesta inválida del modelo: {exc}")
            return
        cleaned = self._strip_markdown_fences(content)
        self.finished_ok.emit(cleaned)

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Si el modelo devuelve ```lang ... ``` lo limpiamos."""
        if not text:
            return ""
        stripped = text.strip()
        if stripped.startswith("```"):
            first_nl = stripped.find("\n")
            if first_nl != -1:
                stripped = stripped[first_nl + 1:]
            if stripped.rstrip().endswith("```"):
                stripped = stripped.rstrip()[:-3]
        return stripped.rstrip() + "\n"

# ────────────────────────────────────────────────────────────────────────────
# Panel principal del plugin
# ────────────────────────────────────────────────────────────────────────────

class AILiveIDEPanel(BasePanel, PremiumMixin):
    """Panel del plugin AI Live IDE.

    Hereda de `BasePanel` para reutilizar el motor de temas y de
    `PremiumMixin` para integrarse con el validador del UnifiedPluginManager.

    Sobrescribe `setup_ui()` (permitido por el contrato de BasePanel) para
    ofrecer una composición libre con QSplitter en lugar de pestañas.
    """

    code_changed = Signal()  # se emite cuando el contenido del editor cambia
    # Solicita al host (MainWindow) ocultar/mostrar las pestañas del navegador.
    # Útil cuando el IDE ocupa el área central y queremos liberar/recuperar
    # espacio del QTabWidget de páginas web. El host es quien decide qué hacer.
    toggle_browser_tabs_requested = Signal()
    # Solicita cerrar completamente el modo IDE y devolver el navegador a su
    # estado normal de navegación web.
    close_ide_requested = Signal()

    def __init__(self, plugin_validator=None, parent: Optional[QWidget] = None):
        # Atributos primitivos requeridos por setup_ui() — DEBEN existir
        # antes de llamar a super().__init__() porque BasePanel.__init__
        # invoca self.setup_ui() de forma síncrona.
        self.plugin_id = PLUGIN_ID
        self.plugin_validator = plugin_validator
        self._premium_features: Dict[str, QWidget] = {}
        self._project_root: Optional[Path] = None
        self._current_file: Optional[Path] = None
        self._dirty = False
        self._ai_worker: Optional[_AICodeEditWorker] = None
        self._editor_ready = False
        self._pending_initial_doc: Optional[Dict[str, str]] = None

        # Estado del chat IA
        self._chat_worker: Optional["AIChatWorker"] = None
        self._chat_history: List["AIChatMessage"] = []
        self._chat_streaming_buffer: str = ""
        self._chat_assistant_anchor: Optional[int] = None  # offset en QTextBrowser
        self._pending_file_changes: List["AIFileChange"] = []

        # NO crear QObjects con parent=self antes de super().__init__():
        # shiboken aborta con "base class __init__ not called". Los creamos
        # sin parent ahora y se reparentan tras super().__init__() si hace falta.
        self._file_watcher = QFileSystemWatcher()
        self._autosave_timer = QTimer()
        self._autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self._autosave_timer.setSingleShot(True)

        # super().__init__ llama internamente a self.setup_ui() y aplica tema
        super().__init__(parent)

        # Importante: PremiumMixin.__init__ (alcanzable vía MRO) resetea
        # `self.plugin_validator = None`. Lo reasignamos aquí explícitamente
        # para que conserve el validador inyectado.
        self.plugin_validator = plugin_validator

        # Reparentar los QObject auxiliares ahora que QObject está inicializado,
        # y conectar señales (que necesitan que self sea un QObject completo).
        self._file_watcher.setParent(self)
        self._file_watcher.fileChanged.connect(self._on_watched_file_changed)
        self._file_watcher.directoryChanged.connect(self._on_watched_dir_changed)
        self._autosave_timer.setParent(self)
        self._autosave_timer.timeout.connect(self._autosave_current_file)

        self._editor_ready_timer = QTimer(self)
        self._editor_ready_timer.setInterval(EDITOR_JS_READY_POLL_MS)
        self._editor_ready_timer.timeout.connect(self._poll_editor_js_api)
        self._editor_ready_poll_attempts = 0

        self.setObjectName("AILiveIDEPanel")
        self.setWindowTitle("AI Live IDE")
        self.setMinimumSize(900, 600)
        self.update_premium_ui(self.plugin_id)

    # ── Contrato BasePanel ───────────────────────────────────────────────

    def get_tab_definitions(self):
        # Sobrescribimos setup_ui() entero, así que esta lista queda vacía.
        return []

    def setup_ui(self):  # noqa: D401 - override BasePanel
        """Construye la UI completa del IDE."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Barra superior con título y estado
        header = self._build_header()
        root_layout.addWidget(header)

        # Toolbar de acciones
        self._toolbar = self._build_toolbar()
        root_layout.addWidget(self._toolbar)

        # Cuerpo principal: árbol | editor | preview | chat IA
        body_splitter = QSplitter(Qt.Horizontal, self)
        body_splitter.setChildrenCollapsible(True)  # permite colapsar chat
        body_splitter.setHandleWidth(2)

        body_splitter.addWidget(self._build_file_tree())
        body_splitter.addWidget(self._build_editor_view())
        body_splitter.addWidget(self._build_preview_view())
        self._chat_panel_widget = self._build_chat_panel()
        body_splitter.addWidget(self._chat_panel_widget)
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 3)
        body_splitter.setStretchFactor(2, 2)
        body_splitter.setStretchFactor(3, 2)
        body_splitter.setSizes([200, 520, 420, 420])
        self._body_splitter = body_splitter
        root_layout.addWidget(body_splitter, stretch=1)

        # Barra de estado inferior
        root_layout.addWidget(self._build_status_bar())

    def post_setup_ui(self):  # noqa: D401 - override BasePanel
        """Hook tras setup_ui() — no usado, pero requerido por contrato."""
        return None

    # ── Construcción UI ──────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        colors = self.get_theme_colors()
        header = QWidget()
        header.setObjectName("aiIdeHeader")
        self._header_widget = header
        header.setFixedHeight(42)
        header.setStyleSheet(
            f"background: {colors['surface_1']}; "
            f"border-bottom: 1px solid {colors['border']};"
        )
        layout = QHBoxLayout(header)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        self._hdr_title = QLabel("AI Live IDE")
        self._hdr_title.setObjectName("aiIdeTitle")
        self._hdr_title.setStyleSheet(
            f"color: {colors['text_primary']}; "
            "font-size: 13px; font-weight: 600; letter-spacing: 0.3px;"
        )
        layout.addWidget(self._hdr_title)

        self._hdr_subtitle = QLabel("Premium · Hugging Face + Monaco")
        self._hdr_subtitle.setObjectName("aiIdeSubtitle")
        self._hdr_subtitle.setStyleSheet(
            f"color: {colors['text_secondary']}; "
            "font-size: 10px; letter-spacing: 0.5px;"
        )
        layout.addWidget(self._hdr_subtitle)

        layout.addStretch()

        self._status_badge = QLabel("Sin licencia")
        self._status_badge.setObjectName("aiIdeStatusBadge")
        self._status_badge.setStyleSheet(
            f"color: {colors['error']}; font-weight: 600; font-size: 11px;"
        )
        layout.addWidget(self._status_badge)
        return header

    def _build_toolbar(self) -> QToolBar:
        self._toolbar_theme_actions: List[QAction] = []
        toolbar = QToolBar("AI Live IDE Toolbar", self)
        self._toolbar = toolbar
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(IDE_TOOLBAR_ICON_SIZE)
        toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self._act_open_folder = self._make_ide_toolbar_action(
            toolbar,
            "ide_folder_open",
            "Abrir carpeta del proyecto",
            "Ctrl+O",
            self.open_project_folder,
            application_shortcut=True,
        )
        self._act_new_file = self._make_ide_toolbar_action(
            toolbar,
            "ide_file_new",
            "Nuevo archivo sin título",
            "Ctrl+N",
            self._new_untitled_file,
            application_shortcut=True,
        )
        self._act_save = self._make_ide_toolbar_action(
            toolbar,
            "ide_save",
            "Guardar archivo actual",
            "Ctrl+S",
            self.save_current_file,
            application_shortcut=True,
        )
        toolbar.addSeparator()

        self._act_ai_edit = self._make_ide_toolbar_action(
            toolbar,
            "ide_ai_sparkles",
            "IA: editar o mejorar el código del archivo actual",
            "Ctrl+Shift+I",
            self._on_ai_edit_clicked,
            application_shortcut=True,
        )
        toolbar.addSeparator()

        self._act_reload_preview = self._make_ide_toolbar_action(
            toolbar,
            "refresh",
            "Recargar vista previa",
            "F5",
            self.reload_preview,
        )
        toolbar.addSeparator()

        self._act_open_external = self._make_ide_toolbar_action(
            toolbar,
            "ide_external_link",
            "Abrir vista previa en el navegador",
            None,
            self._open_preview_external,
        )
        toolbar.addSeparator()

        self._act_toggle_chat = self._make_ide_toolbar_action(
            toolbar,
            "chat",
            "Mostrar u ocultar el panel de chat IA",
            "Ctrl+L",
            self._on_toggle_chat_panel,
            checkable=True,
            checked=True,
        )
        self._act_toggle_browser_tabs = self._make_ide_toolbar_action(
            toolbar,
            "splitview",
            "Mostrar u ocultar las pestañas web del navegador (división horizontal)",
            "Ctrl+Shift+T",
            lambda _checked=False: self.toggle_browser_tabs_requested.emit(),
            checkable=True,
            checked=False,
        )
        toolbar.addSeparator()
        self._act_close_ide = self._make_ide_toolbar_action(
            toolbar,
            "ide_close",
            "Cerrar el modo IDE y volver al navegador",
            "Ctrl+Shift+Q",
            lambda: self.close_ide_requested.emit(),
        )

        self._premium_features = {
            "_act_ai_edit": self._act_ai_edit,
            "_act_open_folder": self._act_open_folder,
            "_act_save": self._act_save,
        }
        self._premium_action_tooltips = {
            k: v.toolTip() for k, v in self._premium_features.items()
        }
        self._apply_toolbar_chrome()
        return toolbar

    def _make_ide_toolbar_action(
        self,
        toolbar: QToolBar,
        icon_name: str,
        tooltip: str,
        shortcut: Optional[str],
        slot,
        *,
        checkable: bool = False,
        checked: bool = False,
        application_shortcut: bool = False,
    ) -> QAction:
        """Crea un QAction solo-icono con SVG temático (mismo pipeline que navbar)."""
        try:
            from ui.core import strip_icons
        except Exception:  # noqa: BLE001
            strip_icons = None
        colors = self.get_theme_colors()
        color = colors.get("text_secondary", "#808080")
        path = ""
        icon = QIcon()
        if strip_icons:
            path = strip_icons.resolve_icon_path(icon_name) or ""
            if path:
                icon = strip_icons.build_strip_icon(
                    path, color, IDE_TOOLBAR_ICON_SIZE
                )
        act = QAction(icon, "", self)
        if path:
            act.setProperty("strip_icon_path", path)
        act.setProperty("strip_icon_name", icon_name)
        tip = tooltip
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
            tip = (
                f"{tooltip} · "
                f"{QKeySequence(shortcut).toString(QKeySequence.NativeText)}"
            )
        act.setToolTip(tip)
        if checkable:
            act.setCheckable(True)
            act.setChecked(checked)
        if application_shortcut:
            act.setShortcutContext(Qt.ApplicationShortcut)
        # triggered(bool): intentar con el bool (toggles); si el slot no lo acepta
        # (p. ej. métodos decorados) reintentar sin argumentos. Capturar fallos para
        # no tumbar el proceso ante excepciones no controladas.

        def _dispatch_toolbar_action(checked: bool = False) -> None:
            try:
                try:
                    slot(checked)
                except TypeError:
                    slot()
            except Exception as exc:
                logger.exception(
                    "Error en acción de la barra del AI Live IDE: %s", exc
                )

        act.triggered.connect(_dispatch_toolbar_action)
        toolbar.addAction(act)
        self._toolbar_theme_actions.append(act)
        return act

    def _themed_toolbar_icon(
        self, icon_name: str, size: Optional[QSize] = None
    ) -> QIcon:
        """Icono SVG tiñido con `text_secondary` del tema activo."""
        try:
            from ui.core import strip_icons
            colors = self.get_theme_colors()
            color = colors.get("text_secondary", "#808080")
            sz = size or IDE_CHAT_CHROME_ICON_SIZE
            path = strip_icons.resolve_icon_path(icon_name)
            if path:
                ic = strip_icons.build_strip_icon(path, color, sz)
                if not ic.isNull():
                    return ic
        except Exception:  # noqa: BLE001
            pass
        return QIcon()

    def _apply_toolbar_chrome(self):
        """Estilos + iconos del toolbar según ThemeEngine."""
        if not hasattr(self, "_toolbar") or self._toolbar is None:
            return
        colors = self.get_theme_colors()
        self._toolbar.setIconSize(IDE_TOOLBAR_ICON_SIZE)
        self._toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        acc = colors.get("accent", "#4B9EFF")
        acc_subtle = colors.get("accent_subtle", "rgba(75,158,255,0.12)")
        self._toolbar.setStyleSheet(
            f"QToolBar {{ background: {colors['surface_0']}; "
            f"border: none; border-bottom: 1px solid {colors['border']}; "
            "padding: 3px 6px; spacing: 2px; }} "
            f"QToolBar::separator {{ background: {colors['border']}; width: 1px; "
            "margin: 5px 6px; }} "
            f"QToolBar QToolButton {{ background: transparent; color: {colors['text_primary']}; "
            "border: 1px solid transparent; border-radius: 5px; "
            "padding: 4px; min-width: 28px; min-height: 28px; }} "
            f"QToolBar QToolButton:hover {{ background: {colors['surface_hover']}; "
            f"border-color: {colors['border']}; }} "
            f"QToolBar QToolButton:pressed {{ background: {colors['surface_1']}; }} "
            f"QToolBar QToolButton:checked {{ background: {acc_subtle}; "
            f"border: 1px solid {acc}; }} "
            f"QToolBar QToolButton:disabled {{ color: {colors['text_muted']}; }}"
        )
        self._refresh_toolbar_icons()

    def _refresh_toolbar_icons(self):
        """Re-tiñe los SVG del toolbar (p. ej. tras cambiar tema)."""
        try:
            from ui.core import strip_icons
        except Exception:  # noqa: BLE001
            return
        colors = self.get_theme_colors()
        sec = colors.get("text_secondary", "#808080")
        for act in getattr(self, "_toolbar_theme_actions", []):
            path = act.property("strip_icon_path")
            if not path:
                continue
            ic = strip_icons.build_strip_icon(path, sec, IDE_TOOLBAR_ICON_SIZE)
            if not ic.isNull():
                act.setIcon(ic)

    def _apply_ide_chrome_theme(self):
        """Cabecera + toolbar alineados con el tema del navegador."""
        if not hasattr(self, "_header_widget"):
            return
        colors = self.get_theme_colors()
        hw = self._header_widget
        hw.setStyleSheet(
            f"background: {colors['surface_1']}; "
            f"border-bottom: 1px solid {colors['border']};"
        )
        if hasattr(self, "_hdr_title"):
            self._hdr_title.setStyleSheet(
                f"color: {colors['text_primary']}; "
                "font-size: 13px; font-weight: 600; letter-spacing: 0.3px;"
            )
        if hasattr(self, "_hdr_subtitle"):
            self._hdr_subtitle.setStyleSheet(
                f"color: {colors['text_secondary']}; "
                "font-size: 10px; letter-spacing: 0.5px;"
            )
        self._apply_toolbar_chrome()
        self.update_premium_ui(self.plugin_id)
        if hasattr(self, "_refresh_token_status_label"):
            self._refresh_token_status_label()

    def _on_theme_changed(self, theme_name: str):  # noqa: D401
        super()._on_theme_changed(theme_name)
        self._apply_ide_chrome_theme()
        try:
            if hasattr(self, "_chat_settings_btn"):
                self._chat_settings_btn.setIcon(
                    self._themed_toolbar_icon("ide_gear")
                )
            if hasattr(self, "_chat_clear_btn"):
                self._chat_clear_btn.setIcon(
                    self._themed_toolbar_icon("ide_trash")
                )
        except Exception as exc:  # noqa: BLE001
            logger.debug("AI IDE chat chrome refresh: %s", exc)

    def _build_file_tree(self) -> QWidget:
        colors = self.get_theme_colors()
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("EXPLORADOR")
        header.setStyleSheet(
            f"color: {colors['text_secondary']}; "
            "font-size: 10px; font-weight: 600; letter-spacing: 0.8px; "
            f"padding: 8px 12px; background: {colors['surface_1']}; "
            f"border-bottom: 1px solid {colors['border']};"
        )
        layout.addWidget(header)

        self._fs_model = QFileSystemModel(self)
        self._fs_model.setReadOnly(False)
        self._tree = QTreeView(container)
        self._tree.setModel(self._fs_model)
        self._tree.setHeaderHidden(True)
        for col in range(1, 4):
            self._tree.setColumnHidden(col, True)
        self._tree.setStyleSheet(
            f"QTreeView {{ background: {colors['surface_0']}; "
            f"color: {colors['text_primary']}; border: none; "
            "font-size: 12px; padding: 4px; }} "
            f"QTreeView::item:hover {{ background: {colors['surface_hover']}; }} "
            f"QTreeView::item:selected {{ background: {colors['selected']}; "
            f"color: {colors['text_primary']}; }} "
            f"QTreeView::branch {{ background: transparent; }}"
        )
        self._tree.activated.connect(self._on_tree_activated)
        self._tree.doubleClicked.connect(self._on_tree_activated)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(
            self._on_file_tree_context_menu
        )
        layout.addWidget(self._tree, stretch=1)

        empty_label = QLabel(
            "Sin proyecto abierto.\n"
            "Usa el botón de carpeta en la barra de herramientas (tooltip «Abrir carpeta del proyecto»)."
        )
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet(
            f"color: {colors['text_muted']}; padding: 24px 12px; font-size: 11px;"
        )
        empty_label.setWordWrap(True)
        layout.addWidget(empty_label)
        self._tree_empty_label = empty_label
        return container

    def _build_editor_view(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not _WEBENGINE_AVAILABLE:
            label = QLabel(
                "QtWebEngine no está disponible.\n"
                "Instala PySide6 con soporte WebEngine para usar el editor Monaco."
            )
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            label.setStyleSheet("color: #F85149; padding: 24px;")
            layout.addWidget(label)
            self._editor_view = None
            return container
        self._editor_view = QWebEngineView(container)
        settings = self._editor_view.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self._editor_view.loadFinished.connect(self._on_editor_load_finished)

        monaco_path = Path(__file__).parent / "monaco.html"
        self._editor_view.setUrl(QUrl.fromLocalFile(str(monaco_path)))
        layout.addWidget(self._editor_view, stretch=1)
        return container

    def _build_preview_view(self) -> QWidget:
        colors = self.get_theme_colors()
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("LIVE PREVIEW")
        header.setStyleSheet(
            f"color: {colors['text_secondary']}; "
            "font-size: 10px; font-weight: 600; letter-spacing: 0.8px; "
            f"padding: 8px 12px; background: {colors['surface_1']}; "
            f"border-bottom: 1px solid {colors['border']};"
        )
        layout.addWidget(header)

        if not _WEBENGINE_AVAILABLE:
            label = QLabel("QtWebEngine no disponible — sin preview.")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #F85149; padding: 24px;")
            layout.addWidget(label)
            self._preview_view = None
            self._preview_lazy_placeholder = None
            return container
        # Diferir el segundo QWebEngineView hasta que haga falta preview: dos
        # instancias Chromium + pestañas del navegador agotan RAM y el kernel
        # mata el proceso («Terminado (killed)») en equipos con poca memoria.
        self._preview_view = None
        self._preview_body_layout = layout
        self._preview_lazy_placeholder = QLabel(
            "La vista previa se cargará al abrir un archivo compatible\n"
            "(p. ej. HTML/CSS) o al activar el servidor HTTP local.\n"
            "Así se retrasa un segundo motor Chromium y se reduce el uso de memoria."
        )
        self._preview_lazy_placeholder.setWordWrap(True)
        self._preview_lazy_placeholder.setAlignment(Qt.AlignCenter)
        self._preview_lazy_placeholder.setStyleSheet(
            f"color: {colors['text_muted']}; padding: 20px 16px; font-size: 11px;"
        )
        layout.addWidget(self._preview_lazy_placeholder, stretch=1)
        return container

    def _ensure_preview_webview(self) -> None:
        """Crea el QWebEngineView de la vista previa solo cuando hace falta (ahorra RAM)."""
        if self._preview_view is not None or not _WEBENGINE_AVAILABLE:
            return
        lay = getattr(self, "_preview_body_layout", None)
        ph = getattr(self, "_preview_lazy_placeholder", None)
        if lay is None or ph is None:
            return
        parent_w = lay.parentWidget()
        if parent_w is None:
            return
        self._preview_view = QWebEngineView(parent_w)
        self._preview_view.setUrl(QUrl("about:blank"))
        if lay.replaceWidget(ph, self._preview_view):
            ph.deleteLater()
        else:
            lay.removeWidget(ph)
            ph.deleteLater()
            lay.addWidget(self._preview_view, stretch=1)
        self._preview_lazy_placeholder = None

    def _build_status_bar(self) -> QWidget:
        colors = self.get_theme_colors()
        bar = QWidget()
        bar.setFixedHeight(26)
        bar.setStyleSheet(
            f"background: {colors['surface_1']}; "
            f"border-top: 1px solid {colors['border']};"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(14)

        self._status_file_label = QLabel("Sin archivo")
        self._status_file_label.setStyleSheet(
            f"color: {colors['text_secondary']}; font-size: 11px;"
        )
        layout.addWidget(self._status_file_label)

        layout.addStretch()

        self._status_lang_label = QLabel("plaintext")
        self._status_lang_label.setStyleSheet(
            f"color: {colors['text_muted']}; font-size: 11px;"
        )
        layout.addWidget(self._status_lang_label)

        self._status_msg_label = QLabel("")
        self._status_msg_label.setStyleSheet(
            f"color: {colors['accent']}; font-size: 11px;"
        )
        layout.addWidget(self._status_msg_label)
        return bar

    # ── Construcción del Chat IA (panel derecho) ─────────────────────────

    def _build_chat_panel(self) -> QWidget:
        """Construye el panel de chat IA (estilo Cursor/Copilot)."""
        colors = self.get_theme_colors()
        container = QWidget()
        container.setObjectName("aiChatPanel")
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1) Cabecera del panel de chat
        header = QLabel("CHAT IA")
        header.setStyleSheet(
            f"color: {colors['text_secondary']}; "
            "font-size: 10px; font-weight: 600; letter-spacing: 0.8px; "
            f"padding: 8px 12px; background: {colors['surface_1']}; "
            f"border-bottom: 1px solid {colors['border']};"
        )
        layout.addWidget(header)

        # 2) Barra de modelo + contexto
        controls = QWidget()
        controls.setStyleSheet(f"background: {colors['surface_1']};")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(8, 6, 8, 6)
        controls_layout.setSpacing(4)

        # Fila 1: selector de modelo HF
        model_row = QHBoxLayout()
        model_row.setSpacing(6)
        model_lbl = QLabel("Modelo:")
        model_lbl.setStyleSheet(
            f"color: {colors['text_secondary']}; font-size: 11px;"
        )
        model_row.addWidget(model_lbl)

        self._chat_model_combo = QComboBox()
        self._chat_model_combo.setStyleSheet(self._build_combo_style(colors))
        if _AI_CHAT_AVAILABLE:
            for m in HF_CODE_MODELS:
                self._chat_model_combo.addItem(m["label"], userData=m["slug"])
                idx = self._chat_model_combo.count() - 1
                self._chat_model_combo.setItemData(
                    idx, m.get("notes", ""), Qt.ToolTipRole
                )
            # Restaurar último modelo elegido
            default_slug = self._load_chosen_model_slug()
            for i in range(self._chat_model_combo.count()):
                if self._chat_model_combo.itemData(i) == default_slug:
                    self._chat_model_combo.setCurrentIndex(i)
                    break
            self._chat_model_combo.currentIndexChanged.connect(
                self._on_chat_model_changed
            )
        else:
            self._chat_model_combo.addItem("ai_chat module no disponible")
            self._chat_model_combo.setEnabled(False)
        model_row.addWidget(self._chat_model_combo, stretch=1)
        controls_layout.addLayout(model_row)

        # Fila 2: opciones de contexto
        ctx_row = QHBoxLayout()
        ctx_row.setSpacing(4)
        self._chat_include_file = QCheckBox("Archivo actual")
        self._chat_include_file.setChecked(True)
        self._chat_include_file.setToolTip(
            "Incluir el contenido del archivo abierto en el editor "
            "como contexto del mensaje."
        )
        self._chat_include_file.setStyleSheet(
            f"color: {colors['text_secondary']}; font-size: 11px;"
        )
        ctx_row.addWidget(self._chat_include_file)

        self._chat_include_project = QCheckBox("Proyecto completo")
        self._chat_include_project.setChecked(False)
        self._chat_include_project.setToolTip(
            "Incluir el árbol y los ficheros del proyecto (limitado por "
            "tamaño). Útil para preguntas que abarcan varios módulos."
        )
        self._chat_include_project.setStyleSheet(
            f"color: {colors['text_secondary']}; font-size: 11px;"
        )
        ctx_row.addWidget(self._chat_include_project)

        ctx_row.addStretch()

        icon_btn_ss = (
            f"QPushButton {{ background: transparent; border: 1px solid transparent; "
            f"border-radius: 4px; padding: 2px; min-width: 28px; min-height: 24px; }}"
            f"QPushButton:hover {{ background: {colors['surface_hover']}; "
            f"border-color: {colors['border']}; }}"
        )
        self._chat_settings_btn = QPushButton()
        self._chat_settings_btn.setIcon(self._themed_toolbar_icon("ide_gear"))
        self._chat_settings_btn.setIconSize(IDE_CHAT_CHROME_ICON_SIZE)
        self._chat_settings_btn.setFixedSize(28, 26)
        self._chat_settings_btn.setToolTip(
            "Configurar token de Hugging Face y opciones del chat"
        )
        self._chat_settings_btn.setStyleSheet(icon_btn_ss)
        self._chat_settings_btn.clicked.connect(self._on_open_settings)
        ctx_row.addWidget(self._chat_settings_btn)

        self._chat_clear_btn = QPushButton()
        self._chat_clear_btn.setIcon(self._themed_toolbar_icon("ide_trash"))
        self._chat_clear_btn.setIconSize(IDE_CHAT_CHROME_ICON_SIZE)
        self._chat_clear_btn.setFixedSize(28, 26)
        self._chat_clear_btn.setToolTip("Limpiar conversación")
        self._chat_clear_btn.setStyleSheet(icon_btn_ss)
        self._chat_clear_btn.clicked.connect(self._on_clear_chat)
        ctx_row.addWidget(self._chat_clear_btn)
        controls_layout.addLayout(ctx_row)

        # Indicador de estado del token (visible si NO hay token)
        self._chat_token_warning = QLabel("")
        self._chat_token_warning.setTextFormat(Qt.RichText)
        self._chat_token_warning.setOpenExternalLinks(False)
        self._chat_token_warning.setWordWrap(True)
        self._chat_token_warning.setStyleSheet(
            f"color: {colors['warning']}; font-size: 11px; "
            "padding: 4px 0;"
        )
        self._chat_token_warning.linkActivated.connect(
            lambda _href: self._on_open_settings()
        )
        controls_layout.addWidget(self._chat_token_warning)
        self._refresh_token_status_label()

        layout.addWidget(controls)

        # 3) Historial / transcript
        self._chat_view = QTextBrowser()
        self._chat_view.setOpenExternalLinks(True)
        self._chat_view.setStyleSheet(
            f"QTextBrowser {{ background: {colors['surface_0']}; "
            f"color: {colors['text_primary']}; border: none; "
            f"padding: 8px 10px; font-size: 12px; }}"
        )
        layout.addWidget(self._chat_view, stretch=1)
        self._render_chat_greeting()

        # 4) Panel inferior: propuestas de cambios (oculto cuando no hay)
        self._chat_changes_box = QWidget()
        self._chat_changes_box.setStyleSheet(
            f"background: {colors['surface_1']}; "
            f"border-top: 1px solid {colors['border']};"
        )
        changes_layout = QVBoxLayout(self._chat_changes_box)
        changes_layout.setContentsMargins(8, 6, 8, 6)
        changes_layout.setSpacing(4)
        changes_header = QHBoxLayout()
        changes_lbl = QLabel("CAMBIOS PROPUESTOS")
        changes_lbl.setStyleSheet(
            f"color: {colors['accent']}; font-size: 10px; "
            "font-weight: 700; letter-spacing: 0.6px;"
        )
        changes_header.addWidget(changes_lbl)
        changes_header.addStretch()
        self._chat_changes_count_lbl = QLabel("")
        self._chat_changes_count_lbl.setStyleSheet(
            f"color: {colors['text_secondary']}; font-size: 10px;"
        )
        changes_header.addWidget(self._chat_changes_count_lbl)
        changes_layout.addLayout(changes_header)

        self._chat_changes_list = QListWidget()
        self._chat_changes_list.setMaximumHeight(120)
        self._chat_changes_list.setStyleSheet(
            f"QListWidget {{ background: {colors['surface_0']}; "
            f"color: {colors['text_primary']}; "
            f"border: 1px solid {colors['border']}; "
            "border-radius: 4px; font-size: 11px; padding: 2px; }} "
            f"QListWidget::item {{ padding: 3px 5px; }} "
            f"QListWidget::item:hover {{ background: {colors['surface_hover']}; }} "
            f"QListWidget::item:selected {{ background: {colors['selected']}; }}"
        )
        self._chat_changes_list.itemDoubleClicked.connect(self._on_change_double_clicked)
        changes_layout.addWidget(self._chat_changes_list)

        changes_buttons = QHBoxLayout()
        changes_buttons.setSpacing(4)
        self._chat_review_btn = QPushButton("Revisar")
        self._chat_review_btn.setStyleSheet(self._build_action_btn_style(colors, "accent"))
        self._chat_review_btn.clicked.connect(self._on_review_changes)
        changes_buttons.addWidget(self._chat_review_btn)

        self._chat_apply_all_btn = QPushButton("Aplicar todos")
        self._chat_apply_all_btn.setStyleSheet(self._build_action_btn_style(colors, "success"))
        self._chat_apply_all_btn.clicked.connect(self._on_apply_all_changes)
        changes_buttons.addWidget(self._chat_apply_all_btn)

        self._chat_discard_btn = QPushButton("Descartar")
        self._chat_discard_btn.setStyleSheet(self._build_action_btn_style(colors, "error"))
        self._chat_discard_btn.clicked.connect(self._on_discard_changes)
        changes_buttons.addWidget(self._chat_discard_btn)

        changes_layout.addLayout(changes_buttons)
        layout.addWidget(self._chat_changes_box)
        self._chat_changes_box.hide()  # solo visible cuando hay cambios pendientes

        # 5) Input multilínea + botón enviar
        input_box = QWidget()
        input_box.setStyleSheet(
            f"background: {colors['surface_1']}; "
            f"border-top: 1px solid {colors['border']};"
        )
        input_layout = QVBoxLayout(input_box)
        input_layout.setContentsMargins(8, 6, 8, 8)
        input_layout.setSpacing(4)

        self._chat_input = QPlainTextEdit()
        self._chat_input.setPlaceholderText(
            "Pregunta a la IA o pide cambios (Ctrl+Enter para enviar)…"
        )
        self._chat_input.setStyleSheet(
            f"QPlainTextEdit {{ background: {colors['surface_0']}; "
            f"color: {colors['text_primary']}; "
            f"border: 1px solid {colors['border']}; "
            "border-radius: 5px; padding: 6px 8px; font-size: 12px; "
            "font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; }} "
            f"QPlainTextEdit:focus {{ border-color: {colors['accent']}; }}"
        )
        self._chat_input.setMaximumHeight(120)
        self._chat_input.setMinimumHeight(48)
        # Atajo Ctrl+Enter para enviar
        self._chat_input.installEventFilter(self)
        input_layout.addWidget(self._chat_input)

        bottom_row = QHBoxLayout()
        self._chat_status_label = QLabel("")
        self._chat_status_label.setStyleSheet(
            f"color: {colors['text_muted']}; font-size: 10px;"
        )
        bottom_row.addWidget(self._chat_status_label)
        bottom_row.addStretch()

        self._chat_stop_btn = QPushButton("Detener")
        self._chat_stop_btn.setStyleSheet(self._build_action_btn_style(colors, "error"))
        self._chat_stop_btn.clicked.connect(self._on_stop_chat)
        self._chat_stop_btn.hide()
        bottom_row.addWidget(self._chat_stop_btn)

        self._chat_send_btn = QPushButton("Enviar")
        self._chat_send_btn.setShortcut(QKeySequence("Ctrl+Return"))
        self._chat_send_btn.setStyleSheet(self._build_action_btn_style(colors, "accent"))
        self._chat_send_btn.clicked.connect(self._on_send_chat)
        bottom_row.addWidget(self._chat_send_btn)
        input_layout.addLayout(bottom_row)
        layout.addWidget(input_box)

        # El chat es feature premium también
        self._premium_features.setdefault("_chat_send_btn", self._chat_send_btn)
        self._premium_features.setdefault("_chat_input", self._chat_input)
        return container

    # ── Estilos comunes ──────────────────────────────────────────────────

    @staticmethod
    def _build_combo_style(colors: dict) -> str:
        return (
            f"QComboBox {{ background: {colors['surface_0']}; "
            f"color: {colors['text_primary']}; "
            f"border: 1px solid {colors['border']}; "
            "border-radius: 4px; padding: 3px 6px; font-size: 11px; }} "
            f"QComboBox:hover {{ border-color: {colors['accent']}; }} "
            f"QComboBox QAbstractItemView {{ "
            f"background: {colors['surface_0']}; "
            f"color: {colors['text_primary']}; "
            f"selection-background-color: {colors['selected']}; "
            f"border: 1px solid {colors['border']}; }}"
        )

    @staticmethod
    def _build_minibtn_style(colors: dict) -> str:
        return (
            f"QPushButton {{ background: {colors['surface_0']}; "
            f"color: {colors['text_secondary']}; "
            f"border: 1px solid {colors['border']}; "
            "border-radius: 4px; padding: 1px 6px; font-size: 12px; }} "
            f"QPushButton:hover {{ background: {colors['surface_hover']}; "
            f"color: {colors['text_primary']}; }}"
        )

    @staticmethod
    def _build_action_btn_style(colors: dict, variant: str) -> str:
        bg = colors.get("accent", "#4B9EFF")
        hover_bg = "#5DA8FF"
        fg = "#FFFFFF"
        if variant == "success":
            bg = colors.get("success", "#3FB950")
            hover_bg = "#52C962"
        elif variant == "error":
            bg = colors.get("error", "#F85149")
            hover_bg = "#FF6B63"
        return (
            f"QPushButton {{ background: {bg}; color: {fg}; "
            "border: none; border-radius: 4px; padding: 5px 12px; "
            "font-size: 11px; font-weight: 600; } "
            f"QPushButton:hover {{ background: {hover_bg}; }} "
            "QPushButton:disabled { background: #555; color: #999; }"
        )

    # ── Integración con PremiumMixin ─────────────────────────────────────

    def set_plugin_validator(self, validator):
        super().set_plugin_validator(validator)
        self.update_premium_ui(self.plugin_id)

    def update_premium_ui(self, plugin_id: str):
        """Refleja el nivel de acceso del usuario en la cabecera y toolbar.

        Si no hay validator (modo desarrollo / instalación local), tratamos
        al usuario como premium para que todo funcione end-to-end durante
        el QA. La conexión con licencias reales se restablece automáticamente
        en cuanto el plugin_manager esté disponible.
        """
        if not self.plugin_validator:
            self._status_badge.setText("Dev mode · acceso total")
            self._status_badge.setStyleSheet(
                f"color: {self.get_theme_colors()['success']}; "
                "font-weight: 600; font-size: 11px;"
            )
            self._set_premium_widgets_enabled(True)
            return
        try:
            access = self.plugin_validator.get_plugin_access(plugin_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("update_premium_ui: validador falló: %s", exc)
            return
        c = self.get_theme_colors()
        level = access.access_level.value
        if level == "premium":
            self._status_badge.setText("Premium activo")
            self._status_badge.setStyleSheet(
                f"color: {c['success']}; font-weight: 600; font-size: 11px;"
            )
            self._set_premium_widgets_enabled(True)
        elif level == "trial":
            self._status_badge.setText(
                f"Trial · {access.trial_remaining} días restantes"
            )
            self._status_badge.setStyleSheet(
                f"color: {c['warning']}; font-weight: 600; font-size: 11px;"
            )
            self._set_premium_widgets_enabled(True)
        else:
            self._status_badge.setText("Sin licencia")
            self._status_badge.setStyleSheet(
                f"color: {c['error']}; font-weight: 600; font-size: 11px;"
            )
            self._set_premium_widgets_enabled(False)

    def _set_premium_widgets_enabled(self, enabled: bool):
        for key, action in self._premium_features.items():
            action.setEnabled(enabled)
            base = self._premium_action_tooltips.get(key, action.toolTip())
            if enabled:
                action.setToolTip(base)
            else:
                action.setToolTip(
                    f"{base}\n\n— Requiere suscripción AI Live IDE"
                    if base
                    else "Requiere suscripción AI Live IDE"
                )
        if enabled:
            self._refresh_toolbar_icons()

    # ── Apertura de proyectos y ficheros ─────────────────────────────────

    @requires_premium(plugin_id=PLUGIN_ID, feature=FEATURE_PROJECT_OPEN)
    def open_project_folder(self):
        """Abre una carpeta como raíz del proyecto en el árbol de ficheros."""
        start_dir = str(self._project_root) if self._project_root else str(Path.home())
        folder = QFileDialog.getExistingDirectory(
            self, "Selecciona la carpeta del proyecto", start_dir
        )
        if not folder:
            return
        self._set_project_root(Path(folder))
        self._set_status_msg(f"Proyecto abierto: {Path(folder).name}", timeout_ms=4000)

    def _set_project_root(self, root: Path):
        self._project_root = root
        self._fs_model.setRootPath(str(root))
        self._tree.setRootIndex(self._fs_model.index(str(root)))
        self._tree_empty_label.hide()
        # Refrescar watcher (solo el directorio raíz; QFileSystemModel ya
        # observa recursivamente para refresco del árbol)
        if self._file_watcher.directories():
            self._file_watcher.removePaths(self._file_watcher.directories())
        self._file_watcher.addPath(str(root))

    def _on_tree_activated(self, index):
        path_str = self._fs_model.filePath(index)
        if not path_str:
            return
        path = Path(path_str)
        if path.is_file():
            self.load_file(path)

    def _path_within_project(self, path: Path) -> bool:
        """True si la ruta no sale del proyecto abierto."""
        if self._project_root is None:
            return False
        if not isinstance(path, Path):
            logger.warning(
                "_path_within_project: se esperaba Path, se recibió %s",
                type(path).__name__,
            )
            return False
        try:
            path.resolve().relative_to(self._project_root.resolve())
            return True
        except ValueError:
            return False

    def _refresh_file_tree(self) -> None:
        """Refresca el QFileSystemModel (tras crear/renombrar/borrar fuera del modelo)."""
        if not self._project_root:
            return
        r = str(self._project_root)
        self._fs_model.setRootPath(r)
        self._tree.setRootIndex(self._fs_model.index(r))

    def _ensure_save_allowed(self) -> bool:
        """Misma política que Guardar en la toolbar (premium)."""
        if not self.plugin_validator:
            return True
        try:
            if self.plugin_validator.can_access_feature(PLUGIN_ID, "save_file"):
                return True
        except Exception:  # noqa: BLE001
            return True
        self.request_premium_access(PLUGIN_ID, "save_file")
        return False

    def _on_file_tree_context_menu(self, pos) -> None:
        """Menú contextual del explorador (clic derecho), estilo IDE."""
        if self._project_root is None:
            QMessageBox.information(
                self,
                "Explorador",
                "Abre primero una carpeta de proyecto (barra de herramientas · "
                "Abrir carpeta o Ctrl+O).",
            )
            return
        idx = self._tree.indexAt(pos)
        path: Optional[Path] = None
        if idx.isValid():
            path = Path(self._fs_model.filePath(idx))
            if not self._path_within_project(path):
                path = None

        root_resolved = self._project_root.resolve()
        menu = QMenu(self._tree)

        def new_file_in(target_dir: Path) -> None:
            name, ok = QInputDialog.getText(
                self,
                "Nuevo archivo",
                "Nombre del archivo (p. ej. componente.js):",
                text="nuevo.txt",
            )
            if not ok or not name.strip():
                return
            name = name.strip().replace("\\", "/").split("/")[-1]
            dest = (target_dir / name).resolve()
            if not self._path_within_project(dest):
                QMessageBox.warning(self, "Explorador", "Ruta fuera del proyecto.")
                return
            if dest.exists():
                QMessageBox.warning(
                    self, "Explorador", "Ya existe un elemento con ese nombre."
                )
                return
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text("", encoding="utf-8")
            except OSError as exc:
                QMessageBox.critical(self, "Error creando archivo", str(exc))
                return
            self._refresh_file_tree()
            self.load_file(dest)

        def new_folder_in(target_dir: Path) -> None:
            name, ok = QInputDialog.getText(
                self,
                "Nueva carpeta",
                "Nombre de la carpeta:",
                text="nueva_carpeta",
            )
            if not ok or not name.strip():
                return
            name = name.strip().replace("\\", "/").split("/")[-1]
            dest = (target_dir / name).resolve()
            if not self._path_within_project(dest):
                QMessageBox.warning(self, "Explorador", "Ruta fuera del proyecto.")
                return
            if dest.exists():
                QMessageBox.warning(self, "Explorador", "Ya existe esa ruta.")
                return
            try:
                dest.mkdir(parents=False)
            except OSError as exc:
                QMessageBox.critical(self, "Error creando carpeta", str(exc))
                return
            self._refresh_file_tree()

        # Clic en área vacía: acciones sobre la raíz del proyecto
        if path is None:
            a = menu.addAction("Nuevo archivo…")
            a.triggered.connect(
                lambda _checked=False: new_file_in(self._project_root)
            )
            b = menu.addAction("Nueva carpeta…")
            b.triggered.connect(
                lambda _checked=False: new_folder_in(self._project_root)
            )
            menu.addSeparator()
            c = menu.addAction("Actualizar explorador")
            c.triggered.connect(
                lambda _checked=False: self._refresh_file_tree()
            )
            menu.exec(self._tree.mapToGlobal(pos))
            return

        is_project_root = path.resolve() == root_resolved

        if path.is_dir():
            a = menu.addAction("Nuevo archivo…")
            a.triggered.connect(
                lambda _checked=False, d=path: new_file_in(d)
            )
            b = menu.addAction("Nueva carpeta…")
            b.triggered.connect(
                lambda _checked=False, d=path: new_folder_in(d)
            )
            menu.addSeparator()
            ar = menu.addAction("Renombrar…")
            ar.setEnabled(not is_project_root)
            ar.triggered.connect(
                lambda _checked=False, p=path: self._explorer_rename(p)
            )
            ad = menu.addAction("Eliminar")
            ad.setEnabled(not is_project_root)
            ad.triggered.connect(
                lambda _checked=False, p=path: self._explorer_delete(p)
            )
            menu.addSeparator()
            menu.addAction("Copiar ruta absoluta").triggered.connect(
                lambda _checked=False, p=path: self._explorer_copy_path(
                    p, relative=False
                )
            )
            menu.addAction("Copiar ruta relativa").triggered.connect(
                lambda _checked=False, p=path: self._explorer_copy_path(
                    p, relative=True
                )
            )
            menu.addSeparator()
            menu.addAction("Actualizar explorador").triggered.connect(
                lambda _checked=False: self._refresh_file_tree()
            )
            menu.addSeparator()
            menu.addAction("Abrir en el gestor de archivos").triggered.connect(
                lambda _checked=False, p=path: self._explorer_open_in_file_manager(
                    p
                )
            )
            menu.exec(self._tree.mapToGlobal(pos))
            return

        if path.is_file():
            menu.addAction("Abrir").triggered.connect(
                lambda _checked=False, p=path: self.load_file(p)
            )
            menu.addAction("Recargar desde disco").triggered.connect(
                lambda _checked=False, p=path: self._explorer_reload_file(p)
            )
            menu.addSeparator()
            is_current = (
                self._current_file is not None
                and path.resolve() == self._current_file.resolve()
            )
            act_save = menu.addAction("Guardar")
            act_save.setEnabled(
                bool(is_current and self._editor_view and self._editor_ready)
            )
            act_save.triggered.connect(
                lambda _checked=False: self.save_current_file()
            )
            act_sa = menu.addAction("Guardar como…")
            act_sa.setEnabled(bool(self._editor_view and self._editor_ready))
            act_sa.triggered.connect(
                lambda _checked=False, p=path: self._explorer_save_as(
                    p.parent
                )
            )
            menu.addSeparator()
            menu.addAction("Renombrar…").triggered.connect(
                lambda _checked=False, p=path: self._explorer_rename(p)
            )
            menu.addAction("Eliminar").triggered.connect(
                lambda _checked=False, p=path: self._explorer_delete(p)
            )
            menu.addSeparator()
            menu.addAction("Copiar ruta absoluta").triggered.connect(
                lambda _checked=False, p=path: self._explorer_copy_path(
                    p, relative=False
                )
            )
            menu.addAction("Copiar ruta relativa").triggered.connect(
                lambda _checked=False, p=path: self._explorer_copy_path(
                    p, relative=True
                )
            )
            menu.addSeparator()
            menu.addAction("Actualizar explorador").triggered.connect(
                lambda _checked=False: self._refresh_file_tree()
            )
            menu.addSeparator()
            menu.addAction(
                "Abrir ubicación en el gestor de archivos"
            ).triggered.connect(
                lambda _checked=False, p=path: self._explorer_open_in_file_manager(
                    p
                )
            )
            menu.exec(self._tree.mapToGlobal(pos))

    def _explorer_reload_file(self, path: Path) -> None:
        """Vuelve a cargar el fichero desde disco en el editor."""
        if not path.is_file():
            return
        if (
            self._current_file
            and path.resolve() == self._current_file.resolve()
            and self._dirty
        ):
            r = QMessageBox.question(
                self,
                "Recargar archivo",
                "Hay cambios sin guardar. ¿Descartarlos y recargar desde disco?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if r != QMessageBox.Yes:
                return
        self.load_file(path)

    def _explorer_rename(self, path: Path) -> None:
        if (
            not self._path_within_project(path)
            or path.resolve() == self._project_root.resolve()
        ):
            return
        new_name, ok = QInputDialog.getText(
            self, "Renombrar", "Nuevo nombre:", text=path.name
        )
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip().replace("\\", "/").split("/")[-1]
        if new_name == path.name:
            return
        dest = path.parent / new_name
        if dest.exists():
            QMessageBox.warning(self, "Renombrar", "Ya existe un elemento con ese nombre.")
            return
        try:
            path.rename(dest)
        except OSError as exc:
            QMessageBox.critical(self, "Error al renombrar", str(exc))
            return
        if self._current_file:
            cur = self._current_file.resolve()
            old_p = path.resolve()
            new_dest = dest.resolve()
            try:
                if path.is_file() and cur == old_p:
                    self._current_file = new_dest
                elif path.is_dir():
                    rel = cur.relative_to(old_p)
                    self._current_file = (new_dest / rel).resolve()
            except ValueError:
                pass
            self._status_file_label.setText(str(self._current_file))
        # Quitar entradas del watcher que apuntan al nodo renombrado o descendientes
        prefix = str(path.resolve())
        sep = os.sep
        for f in list(self._file_watcher.files()):
            if f == prefix or f.startswith(prefix + sep):
                self._file_watcher.removePath(f)
        if self._current_file and self._current_file.is_file():
            self._file_watcher.addPath(str(self._current_file.resolve()))
        self._refresh_file_tree()

    def _explorer_delete(self, path: Path) -> None:
        if not self._path_within_project(path):
            return
        if path.resolve() == self._project_root.resolve():
            QMessageBox.warning(
                self, "Explorador", "No se puede eliminar la raíz del proyecto."
            )
            return
        typ = "carpeta" if path.is_dir() else "archivo"
        r = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar {typ} «{path.name}»? Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if r != QMessageBox.Yes:
            return
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as exc:
            QMessageBox.critical(self, "Error al eliminar", str(exc))
            return
        if (
            self._current_file
            and path.resolve() == self._current_file.resolve()
        ):
            if self._file_watcher.files() and str(path) in self._file_watcher.files():
                self._file_watcher.removePath(str(path))
            self._new_untitled_file()
        self._refresh_file_tree()

    def _explorer_copy_path(self, path: Path, *, relative: bool) -> None:
        clip = QGuiApplication.clipboard()
        if relative and self._project_root is not None:
            try:
                rel = path.relative_to(self._project_root).as_posix()
                clip.setText(rel)
            except ValueError:
                clip.setText(str(path.resolve()))
        else:
            clip.setText(str(path.resolve()))
        self._set_status_msg("Ruta copiada al portapapeles", timeout_ms=1800)

    def _explorer_open_in_file_manager(self, path: Path) -> None:
        target = path if path.is_dir() else path.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.resolve())))

    def _explorer_save_as(self, initial_dir: Path) -> None:
        """Guardar contenido actual del editor en otra ruta (dentro del proyecto)."""
        if not self._editor_view or not self._editor_ready:
            QMessageBox.information(
                self,
                "Guardar como",
                "El editor aún no está listo. Espera un momento e inténtalo de nuevo.",
            )
            return
        if not self._ensure_save_allowed():
            return
        base = initial_dir if initial_dir.is_dir() else initial_dir.parent
        suggested = (
            self._current_file.name if self._current_file else "nuevo.txt"
        )
        fp, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar como",
            str(Path(base) / suggested),
            "Todos los archivos (*)",
        )
        if not fp:
            return
        dest = Path(fp)
        self._editor_view.page().runJavaScript(
            "window.editorAPI ? window.editorAPI.getValue() : '';",
            lambda c, d=dest: self._explorer_write_buffer_to_path(d, c),
        )

    def _explorer_write_buffer_to_path(self, dest: Path, content: object) -> None:
        if not self._path_within_project(dest.resolve()):
            QMessageBox.warning(
                self,
                "Guardar como",
                "El destino debe estar dentro de la carpeta del proyecto abierto.",
            )
            return
        raw = content if isinstance(content, str) else ""
        old = self._current_file
        try:
            if old and self._file_watcher.files() and str(old) in self._file_watcher.files():
                self._file_watcher.removePath(str(old))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(raw, encoding="utf-8")
            self._current_file = dest.resolve()
            self._dirty = False
            self._status_file_label.setText(str(self._current_file))
            ext = self._current_file.suffix.lower().lstrip(".")
            lang = self._language_from_extension(ext)
            self._status_lang_label.setText(lang)
            self._send_set_language_to_editor(lang)
            self._file_watcher.addPath(str(self._current_file))
            self._set_status_msg(f"Guardado: {self._current_file.name}", timeout_ms=2500)
            self.reload_preview()
            self._refresh_file_tree()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error guardando", str(exc))

    def _new_untitled_file(self):
        """Crea un buffer en memoria sin tocar disco (untitled)."""
        self._current_file = None
        self._dirty = False
        self._status_file_label.setText("untitled.txt (sin guardar)")
        self._status_lang_label.setText("plaintext")
        self._set_editor_value("", language="plaintext")

    def load_file(self, path: Path):
        """Carga un fichero del disco en el editor."""
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            QMessageBox.warning(
                self, "Archivo binario",
                f"No se puede abrir «{path.name}»: no es UTF-8 legible."
            )
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error abriendo archivo", str(exc))
            return
        # Quitar watcher anterior
        if self._current_file and str(self._current_file) in self._file_watcher.files():
            self._file_watcher.removePath(str(self._current_file))
        self._current_file = path
        self._dirty = False
        self._status_file_label.setText(str(path))
        ext = path.suffix.lower().lstrip(".")
        language = self._language_from_extension(ext)
        self._status_lang_label.setText(language)
        self._set_editor_value(text, language=language)
        # Watch para detectar cambios externos
        self._file_watcher.addPath(str(path))
        # Recargar preview si aplica
        self.reload_preview()

    @staticmethod
    def _language_from_extension(ext: str) -> str:
        """Espejo Python del mapping JS de monaco.html."""
        mapping = {
            "html": "html", "htm": "html",
            "css": "css", "scss": "scss", "less": "less",
            "js": "javascript", "mjs": "javascript", "cjs": "javascript",
            "jsx": "javascript",
            "ts": "typescript", "tsx": "typescript",
            "json": "json",
            "py": "python", "pyw": "python",
            "md": "markdown",
            "yml": "yaml", "yaml": "yaml",
            "xml": "xml", "svg": "xml",
            "sql": "sql",
            "sh": "shell", "bash": "shell",
            "go": "go", "rs": "rust", "java": "java",
            "c": "c", "h": "c",
            "cpp": "cpp", "cxx": "cpp", "cc": "cpp", "hpp": "cpp",
            "cs": "csharp", "rb": "ruby", "php": "php",
            "kt": "kotlin", "swift": "swift",
            "vue": "html", "txt": "plaintext",
        }
        return mapping.get(ext, "plaintext")

    # ── Guardado ─────────────────────────────────────────────────────────

    @requires_premium(plugin_id=PLUGIN_ID, feature="save_file")
    def save_current_file(self):
        """Guarda el contenido actual del editor en disco."""
        if not self._editor_view:
            return
        self._editor_view.page().runJavaScript(
            "window.editorAPI ? window.editorAPI.getValue() : '';",
            self._do_save_with_content,
        )

    def _do_save_with_content(self, content):
        if self._current_file is None:
            # Pedir destino
            start_dir = (str(self._project_root) if self._project_root
                         else str(Path.home()))
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Guardar archivo como", start_dir,
                "Todos los archivos (*)"
            )
            if not file_path:
                return
            self._current_file = Path(file_path)
            self._status_file_label.setText(str(self._current_file))
            ext = self._current_file.suffix.lower().lstrip(".")
            language = self._language_from_extension(ext)
            self._status_lang_label.setText(language)
            self._send_set_language_to_editor(language)
        try:
            # Quitamos el watcher mientras escribimos para evitar reentradas
            if str(self._current_file) in self._file_watcher.files():
                self._file_watcher.removePath(str(self._current_file))
            self._current_file.parent.mkdir(parents=True, exist_ok=True)
            self._current_file.write_text(content or "", encoding="utf-8")
            self._file_watcher.addPath(str(self._current_file))
            self._dirty = False
            self._set_status_msg(
                f"Guardado: {self._current_file.name}", timeout_ms=2500
            )
            self.reload_preview()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error guardando archivo", str(exc))

    def _autosave_current_file(self):
        """Autoguardado silencioso (solo si ya hay fichero asociado)."""
        if not self._current_file:
            return
        if not self._editor_view:
            return
        self._editor_view.page().runJavaScript(
            "window.editorAPI ? window.editorAPI.getValue() : '';",
            self._do_autosave_with_content,
        )

    def _do_autosave_with_content(self, content):
        if not self._current_file:
            return
        try:
            if str(self._current_file) in self._file_watcher.files():
                self._file_watcher.removePath(str(self._current_file))
            self._current_file.write_text(content or "", encoding="utf-8")
            self._file_watcher.addPath(str(self._current_file))
            self._dirty = False
            self.reload_preview()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Autosave falló: %s", exc)

    # ── Puente con el editor Monaco ──────────────────────────────────────

    def _on_editor_load_finished(self, ok: bool):
        """Cuando monaco.html termina de cargar, registramos el callback JS."""
        self._editor_ready_timer.stop()
        if not ok or not self._editor_view:
            self._editor_ready = False
            return
        # loadFinished ocurre al cargar el HTML; Monaco (CDN) crea editorAPI
        # después. Listo solo tras __SCRAPELIO_EDITOR_READY__ (monaco.html)
        # o cuando el sondeo detecta window.editorAPI (titleChanged no siempre
        # se emite en Qt WebEngine al mutar document.title desde JS).
        self._editor_ready = False
        self._editor_ready_poll_attempts = 0
        # Definimos en JS una función que reenviará los cambios a Python a través
        # de title-bridge (más portable que QWebChannel sin dependencias extras).
        bridge_js = """
        window.scrapelioOnChange = function(value) {
            // Codificamos el evento en el title — Python lo monitorea con
            // titleChanged y descodifica. Es robusto, sin QWebChannel, y
            // funciona en todas las versiones de PySide6.
            document.title = '__SCRAPELIO_CHANGE__' + (Date.now());
        };
        """
        self._editor_view.page().runJavaScript(bridge_js)
        # Conectar titleChanged una sola vez
        try:
            self._editor_view.page().titleChanged.disconnect()
        except (RuntimeError, TypeError):
            pass
        self._editor_view.page().titleChanged.connect(self._on_editor_title_changed)
        self._editor_ready_timer.start()

    def _poll_editor_js_api(self) -> None:
        """Detecta cuando existe window.editorAPI (Monaco o fallback)."""
        if not self._editor_view or self._editor_ready:
            self._editor_ready_timer.stop()
            return
        self._editor_ready_poll_attempts += 1
        if self._editor_ready_poll_attempts > EDITOR_JS_READY_MAX_ATTEMPTS:
            self._editor_ready_timer.stop()
            logger.warning(
                "AI Live IDE: editorAPI no disponible tras %s intentos; "
                "revisa la conexión o el CDN de Monaco.",
                EDITOR_JS_READY_MAX_ATTEMPTS,
            )
            return
        self._editor_view.page().runJavaScript(
            "Boolean(window.editorAPI && window.editorAPI.setValue);",
            self._on_editor_js_poll_callback,
        )

    def _on_editor_js_poll_callback(self, result: object) -> None:
        if self._editor_ready:
            return
        if result is True:
            self._mark_editor_js_ready()

    def _mark_editor_js_ready(self) -> None:
        """Una sola vez: editor utilizable en JS; vuelca cola o archivo actual."""
        if self._editor_ready:
            return
        self._editor_ready = True
        self._editor_ready_timer.stop()
        if self._pending_initial_doc is not None:
            doc = self._pending_initial_doc
            self._pending_initial_doc = None
            self._set_editor_value(
                doc.get("text", ""), language=doc.get("lang")
            )
        elif self._current_file is not None:
            try:
                text = self._current_file.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                return
            ext = self._current_file.suffix.lower().lstrip(".")
            self._set_editor_value(
                text, language=self._language_from_extension(ext)
            )

    def _on_editor_title_changed(self, title: str):
        if title.startswith("__SCRAPELIO_EDITOR_READY__"):
            self._mark_editor_js_ready()
            return
        if title.startswith("__SCRAPELIO_CHANGE__"):
            self._dirty = True
            self.code_changed.emit()
            self._autosave_timer.start()  # debounce

    def _set_editor_value(self, text: str, language: Optional[str] = None):
        if not self._editor_view:
            return
        if not self._editor_ready:
            self._pending_initial_doc = {"text": text, "lang": language or "plaintext"}
            return
        payload = json.dumps({"text": text, "lang": language or "plaintext"})
        js = (
            f"(function(){{ var p = {payload}; "
            "if (window.editorAPI) { "
            "window.editorAPI.setValue(p.text); "
            "window.editorAPI.setLanguage(p.lang); "
            "}})();"
        )
        self._editor_view.page().runJavaScript(js)

    def _send_set_language_to_editor(self, language: str):
        if not self._editor_view or not self._editor_ready:
            return
        js = (
            f"if (window.editorAPI) window.editorAPI.setLanguage("
            f"{json.dumps(language)});"
        )
        self._editor_view.page().runJavaScript(js)

    # ── Edición IA (Hugging Face) ────────────────────────────────────────

    def _on_ai_edit_clicked(self):
        """Slot: pide la edición IA del código actual."""
        if not self._editor_view:
            return
        # Gate premium explícito SOLO si hay validador. Sin validador
        # (modo dev / arranque temprano) confiamos en el decorador
        # @requires_premium del worker (que también hace bypass sin validator).
        if self.plugin_validator is not None:
            if not self.request_premium_access(PLUGIN_ID, FEATURE_AI_EDIT):
                return
        instruction = self._ask_instruction()
        if instruction is None:
            return
        self._editor_view.page().runJavaScript(
            "JSON.stringify({ "
            "code: window.editorAPI ? window.editorAPI.getValue() : '', "
            "lang: window.editorAPI ? window.editorAPI.getLanguage() : 'plaintext'"
            "});",
            lambda raw: self._launch_ai_worker(raw, instruction),
        )

    def _ask_instruction(self) -> Optional[str]:
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getMultiLineText(
            self,
            "AI Live IDE — Instrucción para la IA",
            "Describe los cambios que quieres aplicar al código actual.\n"
            "Ejemplos:\n"
            "  • Añade manejo de errores con try/except\n"
            "  • Convierte estas funciones a async/await\n"
            "  • Refactoriza para usar list comprehensions\n",
            "",
        )
        if not ok:
            return None
        return text.strip() or "Mejora, refactoriza y corrige errores"

    @requires_premium(plugin_id=PLUGIN_ID, feature=FEATURE_AI_EDIT)
    def _launch_ai_worker(self, raw_payload, instruction: str):
        try:
            payload = json.loads(raw_payload) if raw_payload else {}
        except (TypeError, ValueError):
            payload = {}
        code = payload.get("code") or ""
        lang = payload.get("lang") or "plaintext"
        token = self._resolve_huggingface_token()
        model = self._resolve_huggingface_model()
        if not token:
            QMessageBox.warning(
                self,
                "Token de Hugging Face no configurado",
                "Para usar el asistente IA debes configurar tu token de "
                "Hugging Face en el panel de Chat IA del navegador "
                "(proveedor 'huggingface'), o establecer la variable de "
                "entorno HUGGINGFACE_TOKEN.",
            )
            return
        if self._ai_worker and self._ai_worker.isRunning():
            QMessageBox.information(
                self, "AI Live IDE",
                "Ya hay una edición IA en curso. Espera a que termine."
            )
            return
        self._act_ai_edit.setEnabled(False)
        self._set_status_msg("Llamando al asistente IA…")

        self._ai_worker = _AICodeEditWorker(
            api_token=token,
            model=model,
            language=lang,
            instruction=instruction,
            code=code,
            parent=self,
        )
        self._ai_worker.progress.connect(
            lambda msg: self._set_status_msg(msg)
        )
        self._ai_worker.finished_ok.connect(self._on_ai_finished_ok)
        self._ai_worker.finished_error.connect(self._on_ai_finished_error)
        self._ai_worker.finished.connect(self._on_ai_thread_finished)
        self._ai_worker.start()

    def _on_ai_finished_ok(self, edited_code: str):
        self._set_editor_value(edited_code)
        self._dirty = True
        self._set_status_msg("IA: cambios aplicados", timeout_ms=3500)

    def _on_ai_finished_error(self, error: str):
        self._set_status_msg("IA: error", timeout_ms=4000)
        QMessageBox.warning(self, "AI Live IDE — error", error)

    def _on_ai_thread_finished(self):
        self._act_ai_edit.setEnabled(True)

    def _resolve_huggingface_token(self) -> str:
        """Busca el token HF en (orden):
            1. QSettings('Scrapelio', 'LLMClient').huggingface_key
            2. ConfigManager → config.yaml: ai.huggingface_token / hf_token
            3. Variables de entorno HUGGINGFACE_TOKEN / HF_TOKEN
        """
        # 1) QSettings — donde lo guarda el chat IA del navegador
        try:
            from PySide6.QtCore import QSettings
            s = QSettings("Scrapelio", "LLMClient")
            key = str(s.value("huggingface_key", "") or "")
            if key:
                return key
        except Exception as exc:  # noqa: BLE001
            logger.debug("HF token QSettings fail: %s", exc)
        # 2) ConfigManager
        try:
            from config_manager import get_config
            cfg = get_config()
            for k in ("ai.huggingface_token", "ai.hf_token",
                      "huggingface.token", "ai_live_ide.huggingface_token"):
                val = cfg.get(k)
                if val:
                    return str(val)
        except Exception as exc:  # noqa: BLE001
            logger.debug("HF token ConfigManager fail: %s", exc)
        # 3) Variables de entorno
        for env_name in ("HUGGINGFACE_TOKEN", "HF_TOKEN",
                         "HUGGINGFACEHUB_API_TOKEN"):
            val = os.environ.get(env_name)
            if val:
                return val
        return ""

    def _resolve_huggingface_model(self) -> str:
        """Permite que el usuario sobrescriba el modelo desde QSettings.

        Por defecto usa Qwen2.5-Coder-7B-Instruct.
        """
        try:
            from PySide6.QtCore import QSettings
            s = QSettings("Scrapelio", "AILiveIDE")
            override = str(s.value("hf_model", "") or "")
            if override:
                return override
        except Exception as exc:  # noqa: BLE001
            logger.debug("HF model QSettings fail: %s", exc)
        return HF_DEFAULT_MODEL

    # ── Live Preview ─────────────────────────────────────────────────────

    def reload_preview(self):
        """Recarga la preview en función del fichero actualmente abierto."""
        self._ensure_preview_webview()
        if not self._preview_view:
            return
        if not self._current_file:
            self._preview_view.setUrl(QUrl("about:blank"))
            return
        ext = self._current_file.suffix.lower()
        if ext in PREVIEWABLE_EXTENSIONS:
            self._preview_view.setUrl(QUrl.fromLocalFile(str(self._current_file)))
        else:
            # Para lenguajes no previsualizables, mostrar mensaje contextual
            html = self._build_unsupported_preview_html(ext)
            self._preview_view.setHtml(html, QUrl("about:blank"))

    def _build_unsupported_preview_html(self, ext: str) -> str:
        c = self.get_theme_colors()
        bg = c.get("surface_0", "#1A1A1A")
        fg = c.get("text_secondary", "#A0A0A0")
        hi = c.get("text_primary", "#F0F0F0")
        code_bg = c.get("surface_1", "#222222")
        acc = c.get("accent", "#4B9EFF")
        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            f"<style>body{{margin:0;padding:24px;background:{bg};color:{fg};"
            "font-family:-apple-system,Segoe UI,sans-serif;font-size:13px;}}"
            f"h1{{font-size:14px;color:{hi};font-weight:600;margin:0 0 8px;}}"
            f"code{{background:{code_bg};padding:2px 6px;border-radius:3px;"
            f"color:{acc};font-family:Menlo,Consolas,monospace;}}</style></head>"
            "<body><h1>Vista previa</h1>"
            f"<p>El tipo de archivo <code>{ext or '(sin extensión)'}</code> no "
            "admite vista previa directa en el panel.</p>"
            "<p>Abre un archivo <code>.html</code> (o otro tipo previsualizable) "
            "desde el árbol para cargar la vista previa.</p>"
            "</body></html>"
        )

    def _open_preview_external(self):
        """Abre la preview actual en una pestaña del navegador Scrapelio."""
        target_url: Optional[QUrl] = None
        if self._current_file and self._current_file.suffix.lower() in PREVIEWABLE_EXTENSIONS:
            target_url = QUrl.fromLocalFile(str(self._current_file))
        if not target_url:
            self._set_status_msg(
                "Nada que abrir externamente todavía", timeout_ms=2500
            )
            return
        # Intentamos delegar al navegador padre. Si no existe, fallback
        # al QDesktopServices del sistema.
        try:
            main_window = self.window()
            if hasattr(main_window, "browser_widget") and hasattr(
                main_window.browser_widget, "tabs_widget"
            ):
                main_window.browser_widget.tabs_widget.add_new_tab(target_url.toString())
                return
        except Exception as exc:  # noqa: BLE001
            logger.debug("No se pudo abrir en pestaña del navegador: %s", exc)
        QDesktopServices.openUrl(target_url)

    # ── File watcher ─────────────────────────────────────────────────────

    def _on_watched_file_changed(self, path: str):
        """Si el archivo cambia desde fuera y no estamos modificando, recarga."""
        try:
            p = Path(path)
        except Exception:  # noqa: BLE001
            return
        if self._current_file and p == self._current_file and not self._dirty:
            # Recarga silenciosa
            try:
                text = p.read_text(encoding="utf-8")
                ext = p.suffix.lower().lstrip(".")
                self._set_editor_value(text, language=self._language_from_extension(ext))
                self._set_status_msg("Archivo recargado desde disco", timeout_ms=2500)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Reload externo falló: %s", exc)
        # Recargar preview si la preview lo apunta
        self.reload_preview()

    def _on_watched_dir_changed(self, _path: str):
        self.reload_preview()

    # ── Utilidades UI ────────────────────────────────────────────────────

    def _set_status_msg(self, text: str, timeout_ms: int = 0):
        if hasattr(self, "_status_msg_label"):
            self._status_msg_label.setText(text)
            if timeout_ms > 0:
                QTimer.singleShot(
                    timeout_ms,
                    lambda: (
                        self._status_msg_label.setText("")
                        if self._status_msg_label else None
                    ),
                )

    # ── Chat IA — lógica completa ────────────────────────────────────────

    def _on_toggle_chat_panel(self, checked: bool):
        """Muestra/oculta el panel de chat en el splitter."""
        if not hasattr(self, "_body_splitter") or not hasattr(self, "_chat_panel_widget"):
            return
        sizes = self._body_splitter.sizes()
        if checked:
            if len(sizes) >= 4 and sizes[3] == 0:
                sizes[3] = 380
                self._body_splitter.setSizes(sizes)
            self._chat_panel_widget.show()
        else:
            if len(sizes) >= 4:
                sizes[3] = 0
                self._body_splitter.setSizes(sizes)

    def _on_clear_chat(self):
        """Limpia historial conversacional y cambios pendientes."""
        self._chat_history.clear()
        self._pending_file_changes.clear()
        self._chat_changes_box.hide()
        self._chat_changes_list.clear()
        self._chat_view.clear()
        self._render_chat_greeting()
        self._chat_set_status("Conversación limpiada")

    # ── Configuración del chat (token HF + opciones) ─────────────────────

    def _on_open_settings(self):
        """Abre el diálogo de configuración (token HF, temperatura, etc.)."""
        current_token = self._resolve_huggingface_token()
        dlg = _HFTokenDialog(
            current_token=current_token,
            current_model=self._current_model_slug(),
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            new_token = dlg.get_token().strip()
            # Persistir el token de forma centralizada (compatible con el
            # chat IA global de Scrapelio). QSettings es la fuente de verdad.
            try:
                from PySide6.QtCore import QSettings
                s = QSettings("Scrapelio", "LLMClient")
                if new_token:
                    s.setValue("huggingface_key", new_token)
                else:
                    s.remove("huggingface_key")
                s.sync()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to persist HF token: %s", exc)
                QMessageBox.warning(
                    self, "AI Live IDE",
                    f"No se pudo guardar el token: {exc}"
                )
                return
            self._refresh_token_status_label()
            if new_token:
                self._chat_set_status(
                    "Token de Hugging Face guardado", timeout_ms=3000
                )
            else:
                self._chat_set_status(
                    "Token de Hugging Face borrado", timeout_ms=3000
                )

    def _refresh_token_status_label(self):
        """Muestra/oculta el aviso de token según haya o no token configurado."""
        if not hasattr(self, "_chat_token_warning"):
            return
        token = self._resolve_huggingface_token()
        if token:
            # Token presente — sin aviso (lo dejamos vacío)
            self._chat_token_warning.setText("")
            self._chat_token_warning.hide()
        else:
            acc = self.get_theme_colors().get("accent", "#4B9EFF")
            self._chat_token_warning.setText(
                "Aviso: token de Hugging Face no configurado. "
                f"<a href='#config' style='color:{acc};'>Configurar ahora</a>"
            )
            self._chat_token_warning.show()

    def _on_chat_model_changed(self, index: int):
        slug = self._chat_model_combo.itemData(index)
        if not slug:
            return
        try:
            from PySide6.QtCore import QSettings
            QSettings("Scrapelio", "AILiveIDE").setValue("chat_model", slug)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to persist chat model: %s", exc)
        self._chat_set_status(f"Modelo: {slug}", timeout_ms=2500)

    def _load_chosen_model_slug(self) -> str:
        try:
            from PySide6.QtCore import QSettings
            slug = str(
                QSettings("Scrapelio", "AILiveIDE")
                .value("chat_model", "") or ""
            )
            if slug:
                return slug
        except Exception:  # noqa: BLE001
            pass
        return HF_DEFAULT_MODEL_SLUG if _AI_CHAT_AVAILABLE else ""

    def _render_chat_greeting(self):
        """Mensaje inicial del asistente."""
        greeting_html = """
        <div style='color:#A0A0A0; font-size:11px; padding:6px 0;'>
          <b style='color:#F0F0F0'>AI Live IDE Chat</b><br>
          Asistente integrado al estilo Cursor/Copilot. Puedo:
          <ul style='margin:4px 0 0 14px; padding:0;'>
            <li>Explicar y depurar tu código actual</li>
            <li>Refactorizar el archivo abierto en el editor</li>
            <li>Generar archivos nuevos del proyecto</li>
            <li>Modificar varios archivos a la vez con un solo prompt</li>
          </ul>
          <div style='margin-top:8px;'>
            Modelo HF actual: <code>{model}</code><br>
            Atajo: <code>Ctrl+L</code> para mostrar/ocultar este panel ·
            <code>Ctrl+Enter</code> para enviar.
          </div>
        </div>
        <hr style='border:none; border-top:1px solid #2A2A2A; margin:8px 0;'/>
        """
        slug = self._current_model_slug() or "(módulo ai_chat no disponible)"
        self._chat_view.setHtml(greeting_html.format(model=slug))

    def _current_model_slug(self) -> str:
        if not _AI_CHAT_AVAILABLE:
            return ""
        idx = self._chat_model_combo.currentIndex()
        if idx < 0:
            return HF_DEFAULT_MODEL_SLUG
        return str(self._chat_model_combo.itemData(idx) or HF_DEFAULT_MODEL_SLUG)

    # ── Filtro de eventos para Ctrl+Enter ────────────────────────────────

    def eventFilter(self, obj, event):  # noqa: D401 - Qt override
        from PySide6.QtCore import QEvent
        if obj is getattr(self, "_chat_input", None) and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & (Qt.ControlModifier | Qt.MetaModifier):
                    self._on_send_chat()
                    return True
        return super().eventFilter(obj, event)

    # ── Envío del mensaje ────────────────────────────────────────────────

    def _collect_editor_json_for_chat(self, callback) -> None:
        """Obtiene código del archivo actual (Monaco o disco) para el prompt."""
        if not self._chat_include_file.isChecked():
            callback("")
            return
        if self._editor_view and self._editor_ready:
            self._editor_view.page().runJavaScript(
                "JSON.stringify({ "
                "code: window.editorAPI ? window.editorAPI.getValue() : '', "
                "lang: window.editorAPI ? window.editorAPI.getLanguage() : 'plaintext'"
                "});",
                callback,
            )
            return
        if self._current_file and self._current_file.is_file():
            try:
                code = self._current_file.read_text(encoding="utf-8")
                ext = self._current_file.suffix.lower().lstrip(".")
                lang = self._language_from_extension(ext)
                callback(json.dumps({"code": code, "lang": lang}))
            except (OSError, UnicodeError) as exc:
                logger.warning(
                    "Contexto chat: no se pudo leer %s: %s",
                    self._current_file,
                    exc,
                )
                callback("")
            return
        self._chat_set_status(
            "«Archivo actual» activo: selecciona un archivo en el explorador",
            timeout_ms=4000,
        )
        callback("")

    def _on_send_chat(self):
        if not _AI_CHAT_AVAILABLE:
            QMessageBox.warning(
                self, "Chat IA no disponible",
                "El módulo ai_chat.py no se pudo cargar."
            )
            return
        text = self._chat_input.toPlainText().strip()
        if not text:
            return
        # Gate premium solo si hay validator
        if self.plugin_validator is not None:
            if not self.request_premium_access(PLUGIN_ID, FEATURE_AI_CHAT):
                return
        # Token HF
        token = self._resolve_huggingface_token()
        if not token:
            # En vez de un mensaje abrupto, abrimos directamente el diálogo
            # de configuración. Si el usuario lo cierra sin guardar nada,
            # cancelamos el envío.
            resp = QMessageBox.question(
                self, "Token de Hugging Face no configurado",
                "Para enviar mensajes al chat IA necesitas un token de "
                "Hugging Face (gratis en huggingface.co/settings/tokens).\n\n"
                "¿Quieres configurarlo ahora?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if resp != QMessageBox.Yes:
                return
            self._on_open_settings()
            token = self._resolve_huggingface_token()
            if not token:
                return
        if self._chat_worker and self._chat_worker.isRunning():
            QMessageBox.information(
                self, "Chat IA",
                "Ya hay una generación en curso. Espera a que termine "
                "o pulsa 'Detener'."
            )
            return
        self._collect_editor_json_for_chat(
            lambda raw: self._launch_chat_with_context(text, raw, token)
        )

    def _launch_chat_with_context(self, user_text: str, raw_editor: str, token: str):
        # Parse del contenido del editor
        editor_code = ""
        editor_lang = "plaintext"
        if raw_editor:
            try:
                obj = json.loads(raw_editor)
                editor_code = obj.get("code", "") or ""
                editor_lang = obj.get("lang", "plaintext") or "plaintext"
            except (TypeError, ValueError):
                pass
        # Construir contexto adicional
        context_chunks: List[str] = []
        focus_path = None
        if self._chat_include_file.isChecked() and editor_code:
            file_label = (
                str(self._current_file.relative_to(self._project_root).as_posix())
                if (self._current_file and self._project_root)
                else (self._current_file.name if self._current_file else "current_buffer")
            )
            context_chunks.append(
                f"=== CURRENT EDITOR ({editor_lang}, file: {file_label}) ===\n"
                f"{editor_code}"
            )
            if self._current_file:
                focus_path = self._current_file
        # Contexto de proyecto
        if self._chat_include_project.isChecked():
            if not self._project_root:
                self._chat_set_status(
                    "«Proyecto completo» requiere carpeta abierta · Ctrl+O",
                    timeout_ms=5000,
                )
            else:
                try:
                    builder = ProjectContextBuilder(self._project_root)
                    ctx_text, stats = builder.build_context(
                        focus_paths=[focus_path] if focus_path else None
                    )
                    context_chunks.append(ctx_text)
                    note = (
                        f"📁 Contexto: {stats['files']} archivos, "
                        f"{stats['bytes'] // 1024} KB"
                        + (" (truncado)" if stats.get("truncated") else "")
                    )
                    self._chat_set_status(note, timeout_ms=4000)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Project context build failed: %s", exc)
        # Sistema + historial + nuevo turno
        system = build_system_prompt("\n\n".join(context_chunks))
        messages: List[AIChatMessage] = [AIChatMessage(role="system", content=system)]
        # Solo los últimos N turnos del historial
        history = self._chat_history[-MAX_HISTORY_MESSAGES:]
        messages.extend(history)
        messages.append(AIChatMessage(role="user", content=user_text))

        # Pintar mensaje del usuario en el transcript
        self._chat_history.append(AIChatMessage(role="user", content=user_text))
        self._chat_append_user_message(user_text)
        self._chat_input.clear()

        # Lanzar worker
        model_slug = self._current_model_slug()
        self._chat_worker = AIChatWorker(
            api_token=token,
            model=model_slug,
            messages=messages,
            max_tokens=HF_CHAT_MAX_TOKENS,
            parent=self,
        )
        self._chat_streaming_buffer = ""
        self._chat_begin_assistant_message(model_slug)
        self._chat_worker.chunk_received.connect(self._on_chat_chunk)
        self._chat_worker.finished_ok.connect(self._on_chat_finished_ok)
        self._chat_worker.finished_error.connect(self._on_chat_finished_error)
        self._chat_worker.finished.connect(self._on_chat_thread_done)
        self._chat_worker.start()
        self._chat_send_btn.setEnabled(False)
        self._chat_send_btn.setText("Generando…")
        self._chat_stop_btn.show()
        self._chat_set_status(f"Llamando a {model_slug}…")

    def _on_stop_chat(self):
        if self._chat_worker and self._chat_worker.isRunning():
            self._chat_worker.request_stop()
            self._chat_set_status("Deteniendo…")

    def _on_chat_chunk(self, chunk: str):
        self._chat_streaming_buffer += chunk
        self._chat_update_assistant_message(self._chat_streaming_buffer)

    def _on_chat_finished_ok(self, full: str):
        # Persistir respuesta completa
        self._chat_history.append(AIChatMessage(role="assistant", content=full))
        self._chat_streaming_buffer = full
        self._chat_update_assistant_message(full)
        self._chat_set_status("Respuesta completada", timeout_ms=2500)
        # Detectar cambios de archivo en la respuesta
        self._extract_and_show_changes(full)

    def _on_chat_finished_error(self, err: str):
        self._chat_update_assistant_message(
            self._chat_streaming_buffer
            + f"\n\n[ERROR] {err}"
        )
        self._chat_set_status("Error", timeout_ms=4000)

    def _on_chat_thread_done(self):
        self._chat_send_btn.setEnabled(True)
        self._chat_send_btn.setText("Enviar")
        self._chat_stop_btn.hide()
        self._chat_worker = None

    # ── Renderizado del transcript ──────────────────────────────────────

    def _chat_append_user_message(self, text: str):
        html = (
            "<div style='margin:8px 0; padding:6px 10px; "
            "background:rgba(75,158,255,0.08); border-left:2px solid #4B9EFF; "
            "border-radius:3px;'>"
            "<div style='color:#4B9EFF; font-size:10px; font-weight:600; "
            "letter-spacing:0.5px; margin-bottom:3px;'>TÚ</div>"
            f"<div style='color:#F0F0F0; font-size:12px; white-space:pre-wrap;'>"
            f"{self._html_escape(text)}</div></div>"
        )
        self._chat_view.append(html)
        self._chat_scroll_to_bottom()

    def _chat_begin_assistant_message(self, model_slug: str):
        """Crea el contenedor del mensaje del asistente para streaming."""
        slug_short = model_slug.split("/")[-1]
        html = (
            "<div style='margin:8px 0; padding:6px 10px; "
            "background:rgba(63,185,80,0.06); border-left:2px solid #3FB950; "
            "border-radius:3px;'>"
            "<div style='color:#3FB950; font-size:10px; font-weight:600; "
            f"letter-spacing:0.5px; margin-bottom:3px;'>IA · {self._html_escape(slug_short)}</div>"
            "<div id='asst-current' style='color:#F0F0F0; font-size:12px; "
            "white-space:pre-wrap; font-family: -apple-system, monospace;'>"
            "<span style='color:#888'>▎</span></div></div>"
        )
        self._chat_view.append(html)
        self._chat_scroll_to_bottom()

    def _chat_update_assistant_message(self, text: str):
        """Reescribe SIEMPRE el HTML completo del último mensaje asistente.

        Estrategia: como QTextBrowser no permite editar el HTML in-place
        de un fragmento concreto sin coste alto, regeneramos el cuerpo
        completo: historial + buffer streaming. Es coste lineal en nº
        mensajes — aceptable para chats típicos.
        """
        parts: List[str] = []
        # 1) Greeting reducido (sin el HR)
        slug = self._current_model_slug() or ""
        parts.append(
            "<div style='color:#A0A0A0; font-size:11px; padding:4px 0;'>"
            "<b style='color:#F0F0F0'>AI Live IDE Chat</b> · "
            f"<code>{self._html_escape(slug)}</code></div>"
            "<hr style='border:none; border-top:1px solid #2A2A2A; margin:6px 0;'/>"
        )
        # 2) Historial confirmado (sin el último asistente en streaming)
        history = self._chat_history
        for i, msg in enumerate(history):
            if msg.role == "user":
                parts.append(self._render_user_html(msg.content))
            elif msg.role == "assistant":
                # Si el último es assistant Y estamos en streaming, sustituimos por buffer
                is_last = (i == len(history) - 1)
                if is_last and self._chat_worker and self._chat_worker.isRunning():
                    parts.append(self._render_assistant_html(text, streaming=True))
                else:
                    parts.append(self._render_assistant_html(msg.content, streaming=False))
        # Si todavía no hay asistente en historial pero estamos streaming, añadirlo
        if (
            self._chat_worker and self._chat_worker.isRunning()
            and (not history or history[-1].role != "assistant")
        ):
            parts.append(self._render_assistant_html(text, streaming=True))
        self._chat_view.setHtml("".join(parts))
        self._chat_scroll_to_bottom()

    def _render_user_html(self, text: str) -> str:
        return (
            "<div style='margin:8px 0; padding:6px 10px; "
            "background:rgba(75,158,255,0.08); border-left:2px solid #4B9EFF; "
            "border-radius:3px;'>"
            "<div style='color:#4B9EFF; font-size:10px; font-weight:600; "
            "letter-spacing:0.5px; margin-bottom:3px;'>TÚ</div>"
            f"<div style='color:#F0F0F0; font-size:12px; white-space:pre-wrap;'>"
            f"{self._html_escape(text)}</div></div>"
        )

    def _render_assistant_html(self, text: str, streaming: bool) -> str:
        slug_short = (self._current_model_slug() or "").split("/")[-1]
        cursor = "<span style='color:#888'>▎</span>" if streaming else ""
        # Renderizado simple: respetamos saltos + resaltamos fences
        rendered = self._render_markdown_lite(text) + cursor
        return (
            "<div style='margin:8px 0; padding:6px 10px; "
            "background:rgba(63,185,80,0.06); border-left:2px solid #3FB950; "
            "border-radius:3px;'>"
            "<div style='color:#3FB950; font-size:10px; font-weight:600; "
            f"letter-spacing:0.5px; margin-bottom:3px;'>IA · {self._html_escape(slug_short)}</div>"
            f"<div style='color:#F0F0F0; font-size:12px; "
            "font-family: -apple-system, sans-serif;'>"
            f"{rendered}</div></div>"
        )

    def _render_markdown_lite(self, text: str) -> str:
        """Markdown ultra-ligero: fences ``` y `inline`, escapando el resto."""
        if not text:
            return ""
        # Trocear por triple-backtick
        out: List[str] = []
        in_code = False
        buffer_code_header = ""
        # Split conservando los fences
        chunks = text.split("```")
        for i, chunk in enumerate(chunks):
            if i % 2 == 0:
                # Texto fuera de fence: escape + inline-code + saltos
                escaped = self._html_escape(chunk)
                # `inline`
                escaped = re.sub(
                    r"`([^`\n]+)`",
                    r"<code style='background:#2A2A2A;color:#4B9EFF;"
                    r"padding:1px 4px;border-radius:3px;font-size:11px;"
                    r"font-family:Menlo,Consolas,monospace;'>\1</code>",
                    escaped,
                )
                # saltos de línea
                escaped = escaped.replace("\n", "<br>")
                out.append(escaped)
            else:
                # Dentro de fence: primera línea = header (lang[:path])
                lines = chunk.split("\n", 1)
                header = lines[0] if lines else ""
                body = lines[1] if len(lines) > 1 else ""
                lang_label = header.strip() or "code"
                out.append(
                    "<pre style='background:#1A1A1A;border:1px solid #2A2A2A;"
                    "border-left:3px solid #4B9EFF;border-radius:4px;"
                    "padding:8px 10px;margin:6px 0;overflow-x:auto;'>"
                    "<div style='color:#888;font-size:10px;font-family:Menlo,"
                    "Consolas,monospace;margin-bottom:4px;'>"
                    f"{self._html_escape(lang_label)}</div>"
                    "<code style='color:#E0E0E0;font-size:11px;"
                    "font-family:Menlo,Consolas,monospace;white-space:pre;'>"
                    f"{self._html_escape(body)}</code></pre>"
                )
        return "".join(out)

    @staticmethod
    def _html_escape(text: str) -> str:
        return (
            (text or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def _chat_scroll_to_bottom(self):
        sb = self._chat_view.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _chat_set_status(self, text: str, timeout_ms: int = 0):
        if hasattr(self, "_chat_status_label"):
            self._chat_status_label.setText(text)
            if timeout_ms > 0:
                QTimer.singleShot(
                    timeout_ms,
                    lambda: (
                        self._chat_status_label.setText("")
                        if self._chat_status_label else None
                    ),
                )

    # ── Detección y aplicación de cambios de archivo ────────────────────

    def _extract_and_show_changes(self, response: str):
        """Si la respuesta contiene bloques con ruta de fichero, los listamos."""
        if not _AI_CHAT_AVAILABLE or not response:
            return
        tuples = CodeBlockParser.extract_file_changes(response)
        if not tuples:
            self._pending_file_changes.clear()
            self._chat_changes_box.hide()
            return
        # Convertir a AIFileChange
        changes: List[AIFileChange] = []
        for path, lang, content in tuples:
            change = AIFileChange(
                path=path, language=lang, new_content=content,
                is_new=False, old_content=None,
            )
            if self._project_root:
                abs_p = change.absolute_path(self._project_root)
                if abs_p.exists() and abs_p.is_file():
                    try:
                        change.old_content = abs_p.read_text(encoding="utf-8")
                    except Exception:  # noqa: BLE001
                        change.old_content = None
                else:
                    change.is_new = True
            else:
                # Sin proyecto abierto, todos serían "nuevos" (sin destino claro)
                change.is_new = True
            changes.append(change)
        self._pending_file_changes = changes
        # Pintar lista
        self._chat_changes_list.clear()
        for ch in changes:
            tag = "[nuevo]" if ch.is_new else "[editar]"
            item = QListWidgetItem(f"{tag}  {ch.path}  ({ch.language})")
            item.setData(Qt.UserRole, ch)
            self._chat_changes_list.addItem(item)
        self._chat_changes_count_lbl.setText(f"{len(changes)} archivo(s)")
        self._chat_changes_box.show()

    def _on_change_double_clicked(self, item: QListWidgetItem):
        change: AIFileChange = item.data(Qt.UserRole)
        if change:
            self._show_diff_dialog(change)

    def _on_review_changes(self):
        if not self._pending_file_changes:
            return
        # Diálogo con todos los cambios encolados
        dlg = _ChangesReviewDialog(
            self._pending_file_changes, self._project_root, parent=self
        )
        if dlg.exec() == QDialog.Accepted:
            selected = dlg.get_selected_changes()
            self._apply_changes(selected)

    def _on_apply_all_changes(self):
        if not self._pending_file_changes:
            return
        if self._project_root is None:
            # Pedimos al usuario un destino
            folder = QFileDialog.getExistingDirectory(
                self, "Selecciona el destino del proyecto", str(Path.home())
            )
            if not folder:
                return
            self._set_project_root(Path(folder))
        msg = (
            f"Se van a aplicar {len(self._pending_file_changes)} "
            "cambio(s) sobre el proyecto. ¿Continuar?"
        )
        if QMessageBox.question(
            self, "Aplicar cambios", msg,
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self._apply_changes(self._pending_file_changes)

    def _on_discard_changes(self):
        self._pending_file_changes.clear()
        self._chat_changes_list.clear()
        self._chat_changes_box.hide()
        self._chat_set_status("Cambios descartados", timeout_ms=2000)

    def _apply_changes(self, changes: List[AIFileChange]):
        if not changes:
            return
        if self._project_root is None:
            QMessageBox.warning(
                self, "Aplicar cambios",
                "Necesitas abrir una carpeta de proyecto para aplicar cambios."
            )
            return
        applied_count = 0
        errors: List[str] = []
        last_applied: Optional[Path] = None
        for ch in changes:
            try:
                abs_p = ch.absolute_path(self._project_root)
                # Evitamos escribir fuera del proyecto por seguridad
                try:
                    abs_p.resolve().relative_to(self._project_root.resolve())
                except ValueError:
                    errors.append(
                        f"{ch.path}: ruta fuera del proyecto, omitida"
                    )
                    continue
                abs_p.parent.mkdir(parents=True, exist_ok=True)
                # Quitamos watcher mientras escribimos
                if str(abs_p) in self._file_watcher.files():
                    self._file_watcher.removePath(str(abs_p))
                abs_p.write_text(ch.new_content, encoding="utf-8")
                self._file_watcher.addPath(str(abs_p))
                ch.applied = True
                applied_count += 1
                last_applied = abs_p
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{ch.path}: {exc}")
        # Refrescar el árbol y la preview
        if self._project_root:
            self._fs_model.setRootPath(str(self._project_root))
        if applied_count > 0 and last_applied is not None:
            self.load_file(last_applied)
            idx = self._fs_model.index(str(last_applied))
            if idx.isValid():
                self._tree.setCurrentIndex(idx)
                self._tree.scrollTo(
                    idx, QAbstractItemView.ScrollHint.PositionAtCenter
                )
        self.reload_preview()
        # Limpiar UI de cambios aplicados
        self._chat_changes_list.clear()
        remaining = [c for c in self._pending_file_changes if not c.applied]
        self._pending_file_changes = remaining
        if remaining:
            for ch in remaining:
                tag = "[nuevo]" if ch.is_new else "[editar]"
                item = QListWidgetItem(f"{tag}  {ch.path}  ({ch.language})")
                item.setData(Qt.UserRole, ch)
                self._chat_changes_list.addItem(item)
            self._chat_changes_count_lbl.setText(f"{len(remaining)} archivo(s)")
        else:
            self._chat_changes_box.hide()
            self._chat_changes_count_lbl.setText("")
        msg_parts = [f"{applied_count} cambios aplicados"]
        if errors:
            msg_parts.append(f"{len(errors)} errores")
        self._chat_set_status(" · ".join(msg_parts), timeout_ms=4000)
        if errors:
            QMessageBox.warning(
                self, "Errores aplicando cambios",
                "\n".join(errors[:10])
                + (f"\n…+{len(errors)-10} más" if len(errors) > 10 else "")
            )

    def _show_diff_dialog(self, change: AIFileChange):
        """Diálogo con diff simple del cambio."""
        dlg = _SingleChangeDialog(change, self._project_root, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._apply_changes([change])

    # ── Ciclo de vida ────────────────────────────────────────────────────

    def closeEvent(self, event):  # noqa: D401 - Qt override
        if self._ai_worker and self._ai_worker.isRunning():
            self._ai_worker.requestInterruption()
            self._ai_worker.wait(1500)
        super().closeEvent(event)

    def shutdown(self):
        """Llamado por UnifiedPluginManager.unload_plugin si está disponible."""
        try:
            if self._chat_worker and self._chat_worker.isRunning():
                self._chat_worker.request_stop()
                self._chat_worker.wait(1500)
        except Exception:  # noqa: BLE001
            pass


# ────────────────────────────────────────────────────────────────────────────
# Diálogos auxiliares — revisión de cambios y diff de un solo archivo
# ────────────────────────────────────────────────────────────────────────────

class _SingleChangeDialog(QDialog):
    """Muestra el cambio propuesto sobre un único archivo (con diff básico)."""

    def __init__(self, change, project_root, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Cambio propuesto — {change.path}")
        self.resize(900, 600)
        layout = QVBoxLayout(self)

        # Header
        info = QLabel(
            f"<b>{change.path}</b>  ·  "
            f"<span style='color:#4B9EFF'>{change.language}</span>  ·  "
            f"{'[nuevo]' if change.is_new else '[editar]'}"
        )
        info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        # Splitter: izquierdo = actual, derecho = propuesto
        splitter = QSplitter(Qt.Horizontal, self)

        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Actual:"))
        left_view = QPlainTextEdit()
        left_view.setReadOnly(True)
        left_view.setPlainText(change.old_content or "(archivo no existe)")
        left_view.setStyleSheet(
            "QPlainTextEdit { background:#1A1A1A; color:#F0F0F0; "
            "font-family: Menlo, Consolas, monospace; font-size: 12px; }"
        )
        left_layout.addWidget(left_view)
        splitter.addWidget(left_box)

        right_box = QWidget()
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("Propuesto:"))
        right_view = QPlainTextEdit()
        right_view.setReadOnly(True)
        right_view.setPlainText(change.new_content or "")
        right_view.setStyleSheet(
            "QPlainTextEdit { background:#1A2218; color:#E0F0E0; "
            "font-family: Menlo, Consolas, monospace; font-size: 12px; }"
        )
        right_layout.addWidget(right_view)
        splitter.addWidget(right_box)
        splitter.setSizes([450, 450])
        layout.addWidget(splitter, stretch=1)

        # Botones
        bb = QDialogButtonBox(
            QDialogButtonBox.Apply | QDialogButtonBox.Cancel, self
        )
        apply_btn = bb.button(QDialogButtonBox.Apply)
        apply_btn.setText("Aplicar cambio")
        apply_btn.clicked.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)


class _ChangesReviewDialog(QDialog):
    """Lista cada cambio con checkbox; permite seleccionar cuáles aplicar."""

    def __init__(self, changes, project_root, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Revisar {len(changes)} cambio(s) propuestos")
        self.resize(900, 600)
        self._changes = list(changes)
        self._checkboxes = []
        self._project_root = project_root

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Marca los cambios que quieres aplicar. Doble-click sobre uno "
            "para ver su contenido completo."
        ))

        # Lista con checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setSpacing(4)
        for ch in self._changes:
            row = QHBoxLayout()
            cb = QCheckBox()
            cb.setChecked(True)
            self._checkboxes.append(cb)
            row.addWidget(cb)
            tag = "[nuevo] " if ch.is_new else "[editar] "
            lbl = QLabel(
                f"<b>{tag}</b>  {ch.path}  "
                f"<span style='color:#888'>({ch.language})</span>"
            )
            lbl.setTextFormat(Qt.RichText)
            row.addWidget(lbl, stretch=1)
            view_btn = QPushButton("👁 Ver")
            row.addWidget(view_btn)
            inner_layout.addLayout(row)

            def _make_view_cb(change=ch):
                return lambda: _SingleChangeDialog(
                    change, self._project_root, parent=self
                ).exec()
            view_btn.clicked.connect(_make_view_cb())
        inner_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        bb = QDialogButtonBox(
            QDialogButtonBox.Apply | QDialogButtonBox.Cancel, self
        )
        apply_btn = bb.button(QDialogButtonBox.Apply)
        apply_btn.setText("Aplicar seleccionados")
        apply_btn.clicked.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def get_selected_changes(self):
        return [
            ch for ch, cb in zip(self._changes, self._checkboxes)
            if cb.isChecked()
        ]


class _HFTokenDialog(QDialog):
    """Diálogo para configurar el token de Hugging Face.

    Lo guardamos en `QSettings("Scrapelio", "LLMClient").huggingface_key`
    (la misma clave que usa el chat IA global del navegador), por lo que el
    token queda compartido entre ambos sistemas.
    """

    HF_TOKENS_URL = "https://huggingface.co/settings/tokens"

    def __init__(self, current_token: str = "", current_model: str = "",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Chat IA — Token de Hugging Face")
        self.resize(560, 380)
        self._current_token = current_token or ""

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Cabecera explicativa
        header = QLabel(
            "<b>Token de Hugging Face</b><br>"
            "<span style='color:#A0A0A0; font-size:11px;'>"
            "Necesario para llamar a los modelos de IA. Es gratuito: "
            "crea uno en "
            f"<a href='{self.HF_TOKENS_URL}' "
            "style='color:#4B9EFF; text-decoration:none;'>"
            "huggingface.co/settings/tokens</a> "
            "(elige el tipo <code>Read</code> o <code>Fine-grained</code> con "
            "permiso para 'Inference Providers')."
            "</span>"
        )
        header.setTextFormat(Qt.RichText)
        header.setOpenExternalLinks(True)
        header.setWordWrap(True)
        layout.addWidget(header)

        # Estado actual
        if self._current_token:
            masked = self._mask_token(self._current_token)
            state_lbl = QLabel(
                f"<span style='color:#3FB950;'>Token actual detectado:</span> "
                f"<code style='color:#A0A0A0; font-size:11px;'>{masked}</code>"
            )
        else:
            state_lbl = QLabel(
                "<span style='color:#D29922;'>No hay token configurado.</span>"
            )
        state_lbl.setTextFormat(Qt.RichText)
        state_lbl.setWordWrap(True)
        layout.addWidget(state_lbl)

        # Campo de entrada del token
        layout.addSpacing(4)
        layout.addWidget(QLabel("Token (hf_...):"))
        self._token_edit = QTextEdit()
        self._token_edit.setPlaceholderText(
            "Pega aquí tu token de Hugging Face (empieza por 'hf_')…"
        )
        self._token_edit.setAcceptRichText(False)
        self._token_edit.setFixedHeight(60)
        self._token_edit.setStyleSheet(
            "QTextEdit { background:#1A1A1A; color:#F0F0F0; "
            "border:1px solid #3A3A3A; border-radius:5px; "
            "padding:6px 8px; font-family: Menlo, Consolas, monospace; "
            "font-size:12px; } "
            "QTextEdit:focus { border-color:#4B9EFF; }"
        )
        # Pre-rellenar si ya hay token (texto plano, no ocultado para que el
        # usuario pueda inspeccionar/copiar)
        if self._current_token:
            self._token_edit.setPlainText(self._current_token)
        layout.addWidget(self._token_edit)

        # Información del modelo seleccionado
        if current_model:
            model_lbl = QLabel(
                f"<span style='color:#A0A0A0; font-size:11px;'>"
                f"Modelo activo: <code>{current_model}</code></span>"
            )
            model_lbl.setTextFormat(Qt.RichText)
            layout.addWidget(model_lbl)

        # Nota sobre alcance del token
        scope_lbl = QLabel(
            "<span style='color:#808080; font-size:10px;'>"
            "Se guardará en <code>QSettings('Scrapelio','LLMClient')</code> "
            "y se compartirá con el chat IA principal del navegador. No se "
            "envía a ningún servidor de Scrapelio."
            "</span>"
        )
        scope_lbl.setTextFormat(Qt.RichText)
        scope_lbl.setWordWrap(True)
        layout.addWidget(scope_lbl)

        layout.addStretch()

        # Botones: Cancelar / Borrar / Guardar
        bb = QDialogButtonBox(self)
        save_btn = bb.addButton("Guardar", QDialogButtonBox.AcceptRole)
        save_btn.setStyleSheet(
            "QPushButton { background:#4B9EFF; color:#FFF; "
            "border:none; border-radius:4px; padding:6px 14px; "
            "font-weight:600; }"
            " QPushButton:hover { background:#5DA8FF; }"
        )
        save_btn.clicked.connect(self.accept)

        clear_btn = bb.addButton("Borrar token", QDialogButtonBox.DestructiveRole)
        clear_btn.setStyleSheet(
            "QPushButton { background:transparent; color:#F85149; "
            "border:1px solid #F85149; border-radius:4px; padding:6px 14px; }"
            " QPushButton:hover { background:rgba(248,81,73,0.15); }"
        )
        clear_btn.clicked.connect(self._on_clear_clicked)

        cancel_btn = bb.addButton(QDialogButtonBox.Cancel)
        cancel_btn.setStyleSheet(
            "QPushButton { background:transparent; color:#A0A0A0; "
            "border:1px solid #3A3A3A; border-radius:4px; padding:6px 14px; }"
            " QPushButton:hover { background:#2A2A2A; color:#F0F0F0; }"
        )
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(bb)

        # Estilo general del diálogo
        self.setStyleSheet(
            "QDialog { background:#1A1A1A; color:#F0F0F0; } "
            "QLabel { color:#F0F0F0; }"
        )

    def _on_clear_clicked(self):
        self._token_edit.setPlainText("")
        # Aceptamos el diálogo para que el panel persista el token vacío
        self.accept()

    def get_token(self) -> str:
        return self._token_edit.toPlainText().strip()

    @staticmethod
    def _mask_token(token: str) -> str:
        if not token or len(token) <= 8:
            return "•" * len(token or "")
        return f"{token[:4]}…{token[-4:]}"
