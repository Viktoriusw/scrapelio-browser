#!/usr/bin/env python3
"""
Theme Editor Panel — editor visual de temas (rediseño minimalista).
"""

import copy

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QColorDialog, QScrollArea, QMessageBox,
    QComboBox, QSpinBox, QTabWidget, QGridLayout, QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QCursor

try:
    from ui.core.theme_engine import get_theme_engine
    _HAS_ENGINE = True
except ImportError:
    _HAS_ENGINE = False
    def get_theme_engine():
        return None


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_colors():
    if _HAS_ENGINE:
        tm = get_theme_engine()
        if tm:
            return tm.get_theme_data().get("colors", {})
    return {}


def _c(colors: dict, *keys, fallback: str = "#888") -> str:
    for k in keys:
        v = colors.get(k)
        if v and str(v).lower() not in ("transparent", "none", ""):
            return v
    return fallback


def _is_dark(hex_color: str) -> bool:
    try:
        c = QColor(hex_color)
        lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255
        return lum < 0.5
    except Exception:
        return True


# ── ColorPickerRow ────────────────────────────────────────────────────────────

class ColorPickerRow(QWidget):
    """
    Fila compacta: [swatch 20×20] [etiqueta expandible] [hex 7ch]
    Al pulsar el swatch o el hex se abre QColorDialog.
    """

    color_changed = Signal(str)

    _SWATCH = 20

    def __init__(self, color_key: str, label: str, initial: str = "#000000", parent=None):
        super().__init__(parent)
        self.color_key   = color_key
        self._label_text = label
        self._color      = initial if initial else "#000000"

        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # Swatch cuadrado
        self._swatch = QLabel()
        self._swatch.setFixedSize(self._SWATCH, self._SWATCH)
        self._swatch.setCursor(QCursor(Qt.PointingHandCursor))
        self._swatch.mousePressEvent = lambda _e: self._pick()
        lay.addWidget(self._swatch, 0)

        # Etiqueta
        lbl = QLabel(label)
        lbl.setFont(QFont("Segoe UI", 8))
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._lbl = lbl
        lay.addWidget(lbl, 1)

        # Hex input
        self._hex = QLineEdit(self._color)
        self._hex.setFont(QFont("Consolas,Courier New", 8))
        self._hex.setFixedWidth(62)
        self._hex.setFixedHeight(20)
        self._hex.editingFinished.connect(self._on_hex_edited)
        lay.addWidget(self._hex, 0)

        self._refresh_swatch()

    def _pick(self):
        c = QColorDialog.getColor(QColor(self._color), self)
        if c.isValid():
            self._color = c.name()
            self._hex.setText(self._color)
            self._refresh_swatch()
            self.color_changed.emit(self._color)

    def _on_hex_edited(self):
        text = self._hex.text().strip()
        if not text.startswith("#"):
            text = "#" + text
        if QColor(text).isValid():
            self._color = text
            self._hex.setText(self._color)
            self._refresh_swatch()
            self.color_changed.emit(self._color)
        else:
            self._hex.setText(self._color)

    def _refresh_swatch(self):
        radius = self._SWATCH // 2
        self._swatch.setStyleSheet(
            f"background:{self._color}; border-radius:{radius}px;"
            f" border:1px solid rgba(128,128,128,0.4);"
        )

    def apply_colors(self, colors: dict):
        bg  = _c(colors, "background", "surface", fallback="#1e1f22")
        txt = _c(colors, "secondary",              fallback="#9aa0a6")
        bdr = _c(colors, "border",                 fallback="#3a3d41")
        self.setStyleSheet(f"background:{bg};")
        self._lbl.setStyleSheet(f"color:{txt}; background:transparent;")
        self._hex.setStyleSheet(
            f"background:{_c(colors,'surface','background',fallback='#2b2d30')};"
            f" color:{_c(colors,'primary',fallback='#e8eaed')};"
            f" border:1px solid {bdr}; border-radius:3px; padding:0 3px;"
        )

    def get_color(self) -> str:
        return self._color

    def set_color(self, color: str):
        if color and str(color).lower() not in ("transparent", "none"):
            self._color = color
        else:
            self._color = "#00000000"
        self._hex.setText(self._color)
        self._refresh_swatch()


# ── Botón de acción pequeño ───────────────────────────────────────────────────

class _Btn(QPushButton):
    def __init__(self, text: str, primary: bool = False, parent=None):
        super().__init__(text, parent)
        self._primary = primary
        self.setFont(QFont("Segoe UI", 8))
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(24)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def apply_colors(self, colors: dict):
        if self._primary:
            bg    = _c(colors, "accent",               fallback="#8ab4f8")
            text  = "#000000" if not _is_dark(bg) else "#ffffff"
            hover = _c(colors, "button_hover", "hover", fallback="#6a94d8")
            self.setStyleSheet(f"""
                QPushButton {{
                    background:{bg}; color:{text};
                    border:none; border-radius:4px; padding:0 10px;
                }}
                QPushButton:hover {{ background:{hover}; }}
                QPushButton:pressed {{ opacity:0.8; }}
            """)
        else:
            bg    = _c(colors, "surface", "background",  fallback="#2b2d30")
            bdr   = _c(colors, "border",                  fallback="#45484a")
            text  = _c(colors, "secondary",               fallback="#9aa0a6")
            hover = _c(colors, "tab_hover", "hover",      fallback="#45484a")
            self.setStyleSheet(f"""
                QPushButton {{
                    background:{bg}; color:{text};
                    border:1px solid {bdr}; border-radius:4px; padding:0 8px;
                }}
                QPushButton:hover {{
                    background:{hover};
                    color:{_c(colors,"primary",fallback="#e8eaed")};
                }}
                QPushButton:pressed {{ background:{bdr}; }}
            """)


# ── Etiqueta de sección ───────────────────────────────────────────────────────

class _SectionLbl(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Segoe UI", 7, QFont.Medium))
        self.setContentsMargins(0, 8, 0, 2)

    def apply_colors(self, colors: dict):
        self.setStyleSheet(
            f"color:{_c(colors,'secondary',fallback='#666')};"
            f" letter-spacing:1px; background:transparent;"
        )


# ── ThemeEditorPanel ──────────────────────────────────────────────────────────

class ThemeEditorPanel(QWidget):
    """Editor visual de temas — minimalista y theme-aware."""

    def __init__(self, theme_engine, browser_instance, parent=None):
        super().__init__(parent)
        self.theme_engine  = theme_engine
        self.browser       = browser_instance
        self.working_theme = None
        self.base_theme    = None
        self._pickers: dict[str, ColorPickerRow] = {}
        self._all_btns: list[_Btn] = []
        self._all_section_lbls: list[_SectionLbl] = []

        self._build()
        self._populate_base_combo()
        self._load_base_theme()

        if self.theme_engine:
            self.theme_engine.theme_changed.connect(self._on_theme_changed)

    # ── construcción ─────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(6)

        # ── Fila 1: base + nombre ────────────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(6)

        base_lbl = QLabel("Base")
        base_lbl.setFont(QFont("Segoe UI", 8))
        self._base_lbl = base_lbl
        top.addWidget(base_lbl)

        self._base_combo = QComboBox()
        self._base_combo.setFont(QFont("Segoe UI", 8))
        self._base_combo.setFixedHeight(22)
        self._base_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._base_combo.currentIndexChanged.connect(self._on_base_changed)
        top.addWidget(self._base_combo, 1)

        name_lbl = QLabel("Nombre")
        name_lbl.setFont(QFont("Segoe UI", 8))
        self._name_lbl_hdr = name_lbl
        top.addWidget(name_lbl)

        self._name_input = QLineEdit()
        self._name_input.setFont(QFont("Segoe UI", 8))
        self._name_input.setFixedHeight(22)
        self._name_input.setPlaceholderText("Mi tema")
        self._name_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top.addWidget(self._name_input, 2)

        root.addLayout(top)

        # Línea divisoria
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        self._divider = line
        root.addWidget(line)

        # ── Tabs ─────────────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setFont(QFont("Segoe UI", 8))
        self._tabs.setDocumentMode(True)
        root.addWidget(self._tabs, 1)

        self._tabs.addTab(self._build_colors_tab(), "Colores")
        self._tabs.addTab(self._build_fonts_tab(),  "Tipografía")
        self._tabs.addTab(self._build_effects_tab(),"Efectos")

        # ── Barra de acciones ─────────────────────────────────────────────────
        bar_line = QFrame()
        bar_line.setFrameShape(QFrame.HLine)
        bar_line.setFixedHeight(1)
        self._bar_divider = bar_line
        root.addWidget(bar_line)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        actions.setContentsMargins(0, 2, 0, 0)

        self._btn_preview = _Btn("Vista previa")
        self._btn_save    = _Btn("Guardar", primary=True)
        self._btn_reset   = _Btn("Restablecer")

        self._btn_preview.clicked.connect(self._preview_theme)
        self._btn_save.clicked.connect(self._save_theme)
        self._btn_reset.clicked.connect(self._reset_to_base)

        actions.addWidget(self._btn_preview)
        actions.addWidget(self._btn_reset)
        actions.addStretch()
        actions.addWidget(self._btn_save)

        self._all_btns = [self._btn_preview, self._btn_save, self._btn_reset]
        root.addLayout(actions)

        self._apply_panel_style()

    # ── tab Colores ───────────────────────────────────────────────────────────

    def _build_colors_tab(self) -> QWidget:
        container = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(2, 4, 2, 8)
        lay.setSpacing(2)

        groups = [
            ("Principales", [
                ("primary",    "Color de texto principal"),
                ("secondary",  "Color de texto secundario"),
                ("background", "Fondo general"),
                ("surface",    "Superficie / widgets"),
            ]),
            ("Acento y estados", [
                ("accent",   "Acento / enlaces"),
                ("success",  "Éxito"),
                ("warning",  "Advertencia"),
                ("error",    "Error"),
            ]),
            ("Pestañas", [
                ("tab_background", "Fondo de pestaña"),
                ("tab_selected",   "Pestaña activa"),
                ("tab_hover",      "Hover de pestaña"),
            ]),
            ("Bordes e interacción", [
                ("border",   "Bordes"),
                ("hover",    "Hover genérico"),
                ("selected", "Seleccionado"),
            ]),
            ("Barra lateral (iconos)", [
                ("icon_color",             "Color de iconos"),
                ("icon_button_background", "Fondo de botón"),
                ("icon_button_hover",      "Hover de botón"),
                ("glow_accent",            "Color de resplandor"),
            ]),
            ("Barra de navegación", [
                ("navbar_button_background", "Fondo de botones"),
                ("navbar_button_hover",      "Hover de botones"),
                ("navbar_button_pressed",    "Pulsado de botones"),
                ("navbar_button_text",       "Color de texto/icono"),
                ("toolbar_background",       "Fondo de barra"),
                ("toolbar_border",           "Borde inferior"),
            ]),
            ("Barra de URL", [
                ("url_bar_background",   "Fondo"),
                ("url_bar_text",         "Color de texto"),
                ("url_bar_border",       "Borde"),
                ("url_bar_placeholder",  "Texto placeholder"),
            ]),
        ]

        for group_name, keys in groups:
            sec = _SectionLbl(group_name.upper())
            self._all_section_lbls.append(sec)
            lay.addWidget(sec)

            for key, label in keys:
                picker = ColorPickerRow(key, label)
                picker.color_changed.connect(
                    lambda color, k=key: self._on_color_changed(k, color)
                )
                self._pickers[key] = picker
                lay.addWidget(picker)

        lay.addStretch()
        scroll.setWidget(inner)

        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return container

    # ── tab Tipografía ────────────────────────────────────────────────────────

    def _build_fonts_tab(self) -> QWidget:
        w = QWidget()
        lay = QGridLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)
        lay.setColumnStretch(1, 1)

        def _row(r, label, attr, default):
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 8))
            inp = QLineEdit(default)
            inp.setFont(QFont("Segoe UI", 8))
            inp.setFixedHeight(22)
            lay.addWidget(lbl, r, 0)
            lay.addWidget(inp, r, 1)
            setattr(self, attr, inp)

        _row(0, "Familia tipográfica", "_font_family", "Segoe UI, Arial, sans-serif")
        _row(1, "Tamaño pequeño",      "_font_sm",      "9pt")
        _row(2, "Tamaño normal",       "_font_md",      "10pt")
        _row(3, "Tamaño grande",       "_font_lg",      "12pt")
        _row(4, "Tamaño título",       "_font_xl",      "14pt")

        lay.setRowStretch(5, 1)
        return w

    # ── tab Efectos ───────────────────────────────────────────────────────────

    def _build_effects_tab(self) -> QWidget:
        w = QWidget()
        lay = QGridLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)
        lay.setColumnStretch(1, 1)

        def _spin_row(r, label, attr, lo, hi, val):
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 8))
            spin = QSpinBox()
            spin.setFont(QFont("Segoe UI", 8))
            spin.setRange(lo, hi)
            spin.setValue(val)
            spin.setFixedHeight(22)
            spin.valueChanged.connect(self._on_effects_changed)
            lay.addWidget(lbl, r, 0)
            lay.addWidget(spin, r, 1)
            setattr(self, attr, spin)

        _spin_row(0, "Resplandor en hover (0 = desactivado, 1–100)", "_spin_glow",  0, 100, 0)
        _spin_row(1, "Brillo extra en hover (0–100)",                 "_spin_light", 0, 100, 0)

        info = QLabel(
            "El resplandor añade un borde de color en botones al pasar el ratón.\n"
            "El brillo mezcla el color de fondo con blanco en estados hover."
        )
        info.setFont(QFont("Segoe UI", 7))
        info.setWordWrap(True)
        self._effects_info = info
        lay.addWidget(info, 2, 0, 1, 2)
        lay.setRowStretch(3, 1)
        return w

    # ── lógica de carga ───────────────────────────────────────────────────────

    def _populate_base_combo(self):
        if not self.theme_engine:
            return
        for t in self.theme_engine.get_available_themes():
            self._base_combo.addItem(t["name"], t["id"])

    def _load_base_theme(self):
        if self._base_combo.count() > 0:
            self._on_base_changed(0)

    def _on_base_changed(self, _index):
        tid = self._base_combo.currentData()
        if not tid or not self.theme_engine:
            return
        tdata = self.theme_engine.get_theme_data(tid)
        self.working_theme = copy.deepcopy(tdata)
        self.base_theme    = tid
        self._fill_inputs(tdata)

    def _fill_inputs(self, tdata: dict):
        colors  = tdata.get("colors", {})
        fonts   = tdata.get("fonts", {})
        effects = tdata.get("effects", {})

        for key, picker in self._pickers.items():
            raw = colors.get(key)
            if raw and str(raw).lower() not in ("transparent", "none"):
                picker.set_color(raw)
            elif key in ("icon_button_background", "navbar_button_background"):
                picker.set_color("#00000000")
            elif key == "icon_button_hover":
                picker.set_color(colors.get("hover", "#e8e8e8"))
            elif key == "navbar_button_hover":
                picker.set_color(colors.get("hover", "#e8e8e8"))
            elif key == "glow_accent":
                picker.set_color(colors.get("accent", "#0078d4"))
            elif key == "toolbar_background":
                picker.set_color(colors.get("background", "#1e1e1e"))
            elif key == "toolbar_border":
                picker.set_color(colors.get("border", "#3a3d41"))

        self._font_family.setText(fonts.get("family", "Segoe UI, Arial, sans-serif"))
        self._font_sm.setText(fonts.get("size_small",  "9pt"))
        self._font_md.setText(fonts.get("size_normal", "10pt"))
        self._font_lg.setText(fonts.get("size_large",  "12pt"))
        self._font_xl.setText(fonts.get("size_title",  "14pt"))
        self._name_input.setText(tdata.get("name", ""))

        if hasattr(self, "_spin_glow"):
            self._spin_glow.setValue(int(effects.get("glow_intensity", 0) or 0))
            self._spin_light.setValue(int(effects.get("hover_brightness", 0) or 0))

    # ── callbacks ─────────────────────────────────────────────────────────────

    def _on_color_changed(self, key: str, color: str):
        if self.working_theme:
            self.working_theme.setdefault("colors", {})[key] = color

    def _on_effects_changed(self, _=None):
        if self.working_theme:
            self.working_theme.setdefault("effects", {}).update({
                "glow_intensity":   self._spin_glow.value(),
                "hover_brightness": self._spin_light.value(),
            })

    def _on_theme_changed(self, _theme_id: str):
        self._apply_panel_style()

    # ── colección de datos ────────────────────────────────────────────────────

    def _collect(self) -> dict | None:
        if not self.working_theme:
            return None
        data = copy.deepcopy(self.working_theme)
        data["colors"] = {k: p.get_color() for k, p in self._pickers.items()}
        data["fonts"]  = {
            "family":      self._font_family.text() or "Segoe UI, Arial, sans-serif",
            "size_small":  self._font_sm.text() or "9pt",
            "size_normal": self._font_md.text() or "10pt",
            "size_large":  self._font_lg.text() or "12pt",
            "size_title":  self._font_xl.text() or "14pt",
        }
        gi = self._spin_glow.value() if hasattr(self, "_spin_glow") else 0
        hb = self._spin_light.value() if hasattr(self, "_spin_light") else 0
        data["effects"] = dict(data.get("effects", {}))
        data["effects"].update({"glow_intensity": gi, "hover_brightness": hb, "glow": gi > 0})

        name = self._name_input.text().strip()
        if name:
            data["name"] = name
        return data

    # ── acciones ──────────────────────────────────────────────────────────────

    def _preview_theme(self):
        if not self.theme_engine:
            return
        data = self._collect()
        if not data:
            return
        try:
            data["id"] = "__preview__"
            self.theme_engine.create_custom_theme("__preview__", data, save_to_file=False)
            self.theme_engine.apply_theme("__preview__")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _save_theme(self):
        if not self.theme_engine:
            return
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Nombre requerido", "Escribe un nombre para el tema.")
            return
        data = self._collect()
        if not data:
            return
        tid = name.lower().replace(" ", "_")
        data.update({"id": tid, "version": "1.0.0", "author": "Custom", "type": "custom"})
        try:
            ok = self.theme_engine.create_custom_theme(tid, data, save_to_file=True)
            if ok:
                self.theme_engine.apply_theme(tid)
                if self.browser and hasattr(self.browser, "statusBar"):
                    self.browser.statusBar().showMessage(f"Tema '{name}' guardado.", 3000)
            else:
                QMessageBox.warning(self, "Error", "No se pudo guardar el tema.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _reset_to_base(self):
        self._on_base_changed(self._base_combo.currentIndex())

    def _close_editor_panel(self):
        if self.browser and hasattr(self.browser, "hide_advanced_panel"):
            self.browser.hide_advanced_panel()
        else:
            self.hide()

    # ── estilo del panel ──────────────────────────────────────────────────────

    def _apply_panel_style(self):
        colors = _get_colors()
        bg      = _c(colors, "background", "surface",   fallback="#1e1f22")
        bg2     = _c(colors, "surface",    "background", fallback="#2b2d30")
        border  = _c(colors, "border",                   fallback="#3a3d41")
        text    = _c(colors, "primary",                  fallback="#e8eaed")
        sec     = _c(colors, "secondary",                fallback="#9aa0a6")
        accent  = _c(colors, "accent",                   fallback="#8ab4f8")

        self.setStyleSheet(f"QWidget {{ background:{bg}; }}")

        # Cabecera
        for w in (self._base_lbl, self._name_lbl_hdr):
            w.setStyleSheet(f"color:{sec}; background:transparent;")
        self._base_combo.setStyleSheet(f"""
            QComboBox {{
                background:{bg2}; color:{text}; border:1px solid {border};
                border-radius:3px; padding:0 4px;
            }}
            QComboBox::drop-down {{ border:none; }}
            QComboBox QAbstractItemView {{
                background:{bg2}; color:{text}; selection-background-color:{accent};
            }}
        """)
        self._name_input.setStyleSheet(f"""
            QLineEdit {{
                background:{bg2}; color:{text}; border:1px solid {border};
                border-radius:3px; padding:0 4px;
            }}
        """)

        # Divisores
        for d in (self._divider, self._bar_divider):
            d.setStyleSheet(f"background:{border};")

        # Tabs
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background:{bg}; border:1px solid {border}; border-radius:4px;
            }}
            QTabBar::tab {{
                background:{bg2}; color:{sec};
                border:none; padding:4px 10px; margin-right:2px;
                border-radius:4px 4px 0 0;
                font-size:8pt;
            }}
            QTabBar::tab:selected {{
                background:{bg}; color:{text}; border-bottom:2px solid {accent};
            }}
            QTabBar::tab:hover:!selected {{ background:{border}; color:{text}; }}
        """)

        # Botones
        for btn in self._all_btns:
            btn.apply_colors(colors)

        # Etiquetas de sección
        for lbl in self._all_section_lbls:
            lbl.apply_colors(colors)

        # Pickers
        for picker in self._pickers.values():
            picker.apply_colors(colors)

        # Efectos info
        if hasattr(self, "_effects_info"):
            self._effects_info.setStyleSheet(f"color:{sec}; background:transparent;")

        # SpinBoxes
        for attr in ("_spin_glow", "_spin_light"):
            if hasattr(self, attr):
                getattr(self, attr).setStyleSheet(f"""
                    QSpinBox {{
                        background:{bg2}; color:{text}; border:1px solid {border};
                        border-radius:3px; padding:0 2px;
                    }}
                """)

        # Font inputs
        for attr in ("_font_family", "_font_sm", "_font_md", "_font_lg", "_font_xl"):
            if hasattr(self, attr):
                getattr(self, attr).setStyleSheet(f"""
                    QLineEdit {{
                        background:{bg2}; color:{text}; border:1px solid {border};
                        border-radius:3px; padding:0 4px;
                    }}
                """)
