#!/usr/bin/env python3
"""
Base Panel - Base class for reusable tabbed panels.

Provides ScrapelioPanelBase with consistent header, section system
and theme support.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QHBoxLayout,
                               QGroupBox, QPushButton, QLabel, QFrame)
from PySide6.QtCore import Qt, QSettings
from typing import List, Tuple, Callable, Dict, Any

# Import theme system
try:
    from ui.core.theme_engine import get_theme_engine, get_color
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False
    def get_color(key, theme=None):
        return "#000000"
    def get_theme_engine():
        return None

# Design tokens (fallback independiente del motor de temas)
_DARK_TOKENS = {
    "surface_0":      "#1A1A1A",
    "surface_1":      "#222222",
    "surface_hover":  "#303030",
    "border":         "rgba(255,255,255,0.08)",
    "text_primary":   "#F0F0F0",
    "text_secondary": "#A0A0A0",
    "accent":         "#4B9EFF",
    "success":        "#3FB950",
    "error":          "#F85149",
}


class BasePanel(QWidget):
    """

    Base class for tabbed panels that eliminates code duplication

    Usage:
    1. Inherit from BasePanel instead of QWidget

    2. Implement get_tab_definitions() that returns list of (create_tab_method, title)

    3. Optionally override setup_ui() for additional customization

    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tab_widget = None

        # Get current theme
        self.settings = QSettings("Scrapelio", "Settings")
        self.current_theme = self.settings.value("theme", "light")

        self.setup_ui()

        # Apply theme after UI setup
        self._apply_base_theme()

        # Connect to theme changes if available
        if THEME_AVAILABLE:
            theme_engine = get_theme_engine()
            if theme_engine:
                theme_engine.theme_changed.connect(self._on_theme_changed)
    def get_tab_definitions(self) -> List[Tuple[Callable, str]]:
        """

        Must be implemented by child classes

        Returns list of tuples (create_tab_method, tab_title)

        Example:
        return [

            (self.create_main_tab, "📊 Main"),

            (self.create_settings_tab, "⚙️ Settings"),
        ]

        """

        raise NotImplementedError("Child classes must implement get_tab_definitions()")
    def setup_ui(self):
        """

        Standard UI configuration with tabs

        Can be overridden by child classes for additional customization

        """

        layout = QVBoxLayout()

        # Create tab widget for all features

        self.tab_widget = QTabWidget()

        self.tab_widget.setDocumentMode(True)  # Flat tabs modern style

        # Create all tabs using definitions from child class

        try:
            tab_definitions = self.get_tab_definitions()

            for create_method, title in tab_definitions:
                tab_widget = create_method()

                self.tab_widget.addTab(tab_widget, title)
        except NotImplementedError:
            # If child class doesn't implement get_tab_definitions, 

            # allow it to handle setup_ui completely

            pass
        layout.addWidget(self.tab_widget)

        self.setLayout(layout)

        # Allow additional customization

        self.post_setup_ui()
    def post_setup_ui(self):
        """

        Hook for additional customization after basic setup

        Can be overridden by child classes

        """

        pass
    def set_object_name(self, name: str):
        """

        Helper to configure objectName for CSS styles

        """

        self.setObjectName(name)
    # === FACTORY METHODS TO CREATE TABS ===

    def create_basic_tab(self, content_builder: Callable[[QWidget, QVBoxLayout], None], 

                        description: str = "") -> QWidget:
        """

        Factory method to create basic tabs with standard pattern

        Args:
            content_builder: Function that receives (widget, layout) and adds content

            description: Optional description for documentation
        Returns:
            QWidget configured to use as tab
        """

        widget = QWidget()

        layout = QVBoxLayout(widget)

        # Call builder to add specific content

        content_builder(widget, layout)

        return widget
    def create_control_group(self, title: str, controls: List[Tuple[str, str, Callable]]) -> QGroupBox:
        """

        Create a control group with standard buttons

        Args:
            title: Group title

            controls: List of (button_text, tooltip, callback)
        Returns:
            QGroupBox with configured buttons
        """

        group = QGroupBox(title)

        layout = QVBoxLayout()

        # Horizontal layout for buttons

        controls_layout = QHBoxLayout()

        for text, tooltip, callback in controls:
            btn = QPushButton(text)

            if tooltip:
                btn.setToolTip(tooltip)
            if callback:
                btn.clicked.connect(callback)
            controls_layout.addWidget(btn)
        layout.addLayout(controls_layout)

        group.setLayout(layout)

        return group
    def create_button_row(self, buttons: List[Tuple[str, Callable, str]]) -> QHBoxLayout:
        """

        Create a horizontal row of buttons

        Args:
            buttons: List of (text, callback, optional_tooltip)
        Returns:
            QHBoxLayout with configured buttons
        """

        layout = QHBoxLayout()

        for button_data in buttons:
            text = button_data[0]

            callback = button_data[1]

            tooltip = button_data[2] if len(button_data) > 2 else ""

            btn = QPushButton(text)

            if callback:
                btn.clicked.connect(callback)
            if tooltip:
                btn.setToolTip(tooltip)
            layout.addWidget(btn)
        return layout
    # === THEME SUPPORT ===

    def get_theme_colors(self) -> dict:
        """
        Retorna un diccionario de colores desde ThemeEngine para el tema activo.
        Permite a las subclases construir estilos dinámicos que siguen el tema.
        """
        if THEME_AVAILABLE:
            te = get_theme_engine()
            if te:
                c = te.get_theme_data()
                colors = c.get("colors", {})
                bg       = colors.get("background", "#1A1A1A")
                surface  = colors.get("surface", "#222222")
                primary  = colors.get("primary", "#F0F0F0")
                secondary = colors.get("secondary", "#A0A0A0")
                accent   = colors.get("accent", "#4B9EFF")
                border   = colors.get("border", "rgba(255,255,255,0.08)")
                hover    = colors.get("hover", "#303030")
                selected = colors.get("selected", "#41331C")
                success  = colors.get("success", "#3FB950")
                warning  = colors.get("warning", "#D29922")
                error    = colors.get("error", "#F85149")
                input_bg = colors.get("input_background", surface)
                input_border = colors.get("input_border", border)
                input_focus  = colors.get("input_focus", accent)
                panel_bg = colors.get("panel_background", bg)
                card_bg  = colors.get("card_background", surface)

                # Derivados para compatibilidad con paneles que usaban _C
                import re as _re
                def _rgba_alpha(hex_or_rgba: str, alpha: float) -> str:
                    """Crea rgba() con alpha desde un color hex o devuelve fallback."""
                    m = _re.match(r"#([0-9a-fA-F]{6})", hex_or_rgba)
                    if m:
                        r = int(m.group(1)[0:2], 16)
                        g = int(m.group(1)[2:4], 16)
                        b = int(m.group(1)[4:6], 16)
                        return f"rgba({r},{g},{b},{alpha})"
                    return hex_or_rgba
                return {
                    "surface_0":      bg,
                    "surface_1":      surface,
                    "surface_hover":  hover,
                    "border":         border,
                    "text_primary":   primary,
                    "text_secondary": secondary,
                    "text_muted":     colors.get("text_disabled", secondary),
                    "accent":         accent,
                    "accent_subtle":  _rgba_alpha(accent, 0.12),
                    "error":          error,
                    "error_subtle":   _rgba_alpha(error, 0.08),
                    "success":        success,
                    "warning":        warning,
                    "selected":       selected,
                    "input_bg":       input_bg,
                    "input_border":   input_border,
                    "input_focus":    input_focus,
                    "panel_bg":       panel_bg,
                    "card_bg":        card_bg,
                    # scroll handle: blanco/transparente en oscuro, gris en claro
                    "scroll_handle":  _rgba_alpha(primary, 0.15),
                    "scroll_handle_hover": _rgba_alpha(primary, 0.30),
                }
        # Fallback tokens oscuros si ThemeEngine no disponible
        return dict(_DARK_TOKENS, **{
            "text_muted": "#606060",
            "accent_subtle": "rgba(75,158,255,0.12)",
            "error_subtle": "rgba(248,81,73,0.08)",
            "warning": "#D29922",
            "selected": "#303030",
            "input_bg": "#222222",
            "input_border": "rgba(255,255,255,0.08)",
            "input_focus": "#4B9EFF",
            "panel_bg": "#1A1A1A",
            "card_bg": "#222222",
            "scroll_handle": "rgba(255,255,255,0.12)",
            "scroll_handle_hover": "rgba(255,255,255,0.25)",
        })
    def _apply_base_theme(self):
        """
        Apply base theme to the panel using ThemeEngine colors.
        Child classes can override this for custom theming.
        """
        c = self.get_theme_colors()
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {c['surface_0']};
                color: {c['text_primary']};
            }}
            QTabWidget::pane {{
                border: 1px solid {c['border']};
                background-color: {c['surface_0']};
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
            }}
            QPushButton {{
                background: {c['surface_1']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                color: {c['text_secondary']};
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background: {c['surface_hover']};
                color: {c['text_primary']};
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background: {c['input_bg']};
                color: {c['text_primary']};
                border: 1px solid {c['input_border']};
                border-radius: 4px;
                padding: 3px 8px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {c['input_focus']};
            }}
            QListWidget {{
                background: {c['surface_1']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 6px;
            }}
            QListWidget::item:hover {{
                background: {c['surface_hover']};
            }}
            QListWidget::item:selected {{
                background: {c['selected']};
            }}
            QScrollBar:vertical {{
                background: transparent; width: 6px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {c['scroll_handle']};
                border-radius: 3px; min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['scroll_handle_hover']};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{ background: transparent; }}
        """)
    def _on_theme_changed(self, theme_name):
        """Handle theme change signal. Child classes can override."""
        self.current_theme = theme_name
        self._apply_base_theme()
    # ── API pública de estilo ─────────────────────────────────────────────────

    def set_title(self, text: str) -> None:
        """Actualiza el título del panel si existe un QLabel#panelTitle."""
        for label in self.findChildren(QLabel, "panelTitle"):
            label.setText(text.upper())
    def add_section(self, label: str) -> QLabel:
        """Añade un separador de sección con texto a la layout principal."""
        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            "font-size: 10px; font-weight: 600; letter-spacing: 0.8px; "
            "color: #606060; padding: 8px 0px 4px 0px;"
        )
        if self.layout():
            self.layout().addWidget(lbl)
        return lbl
    def apply_panel_style(self, border_side: str = "left") -> None:
        """Aplica el estilo base Arc/Brave al panel usando el ThemeEngine activo."""
        self._apply_base_theme()


# ─── ScrapelioPanelBase ───────────────────────────────────────────────────────

class ScrapelioPanelBase(BasePanel):
    """
    Clase base especializada para paneles de Scrapelio.

    Añade:
    - Header fijo de 40px con título + botón cierre
    - Método `add_section(label)` para separadores
    - Estilos Arc/Brave aplicados por defecto
    - Scrollbar mínima (6px)
    """

    def __init__(self, title: str = "", border_side: str = "left", parent=None):
        self._panel_title    = title
        self._border_side    = border_side
        self._close_callback = None
        super().__init__(parent)
        self.apply_panel_style(border_side)
    def set_close_callback(self, callback) -> None:
        """Registra el callback que se llama al cerrar el panel."""
        self._close_callback = callback
    def _make_header(self) -> QWidget:
        """Header estándar de 40px: título uppercase + botón X."""
        c = self.get_theme_colors()
        header = QWidget()
        header.setObjectName("panelHeader")
        header.setFixedHeight(40)
        header.setStyleSheet(
            f"background: {c['surface_0']}; "
            f"border-bottom: 1px solid {c['border']};"
        )

        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 8, 0)
        h_layout.setSpacing(8)

        title_lbl = QLabel(self._panel_title.upper())
        title_lbl.setObjectName("panelTitle")
        title_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 600; letter-spacing: 0.8px; "
            f"color: {c['text_secondary']}; background: transparent;"
        )
        h_layout.addWidget(title_lbl)
        h_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("panelClose")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; border-radius: 4px;
                color: {c['text_muted']}; font-size: 13px;
            }}
            QPushButton:hover {{
                background: {c['error_subtle']};
                color: {c['error']};
            }}
        """)
        close_btn.clicked.connect(self._on_close)
        h_layout.addWidget(close_btn)

        return header
    def _on_close(self):
        if self._close_callback:
            self._close_callback()
        else:
            self.hide()
    def get_tab_definitions(self):
        return []  # Subclases pueden sobrescribir
