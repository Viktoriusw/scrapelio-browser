#!/usr/bin/env python3
"""
Theme Selector Panel — panel de selección de temas (rediseño minimalista).
"""

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFileDialog, QFrame, QSizePolicy, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QFont, QCursor

try:
    from ui.core.theme_engine import get_theme_engine
    _HAS_ENGINE = True
except ImportError:
    _HAS_ENGINE = False
    def get_theme_engine():
        return None


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_colors():
    """Devuelve el dict de colores del tema activo, con fallbacks seguros."""
    if _HAS_ENGINE:
        tm = get_theme_engine()
        if tm:
            return tm.get_theme_data().get("colors", {})
    return {}


def _c(colors: dict, *keys, fallback: str = "#888888") -> str:
    for k in keys:
        v = colors.get(k)
        if v and str(v).lower() not in ("transparent", "none", ""):
            return v
    return fallback


# ── ThemeRow ─────────────────────────────────────────────────────────────────

class ThemeRow(QWidget):
    """Fila compacta que representa un tema disponible."""

    selected = Signal(str)   # theme_id

    _DOT_SIZE = 12

    def __init__(self, theme_id: str, theme_data: dict, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.theme_id = theme_id
        self.theme_data = theme_data
        self.is_active = is_active
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(36)
        self._build()
        self._refresh_style()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(8)

        # Indicador activo (punto o hueco)
        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)
        lay.addWidget(self._dot, 0)

        # Nombre
        name = self.theme_data.get("name", self.theme_id)
        self._name_lbl = QLabel(name)
        self._name_lbl.setFont(QFont("Segoe UI", 9))
        lay.addWidget(self._name_lbl, 1)

        # Paleta de colores (4 puntos pequeños)
        colors = self.theme_data.get("colors", {})
        for key in ("background", "accent", "surface", "primary"):
            if key in colors:
                dot = QLabel()
                dot.setFixedSize(self._DOT_SIZE, self._DOT_SIZE)
                dot.setStyleSheet(
                    f"background:{colors[key]}; border-radius:{self._DOT_SIZE//2}px;"
                    f" border:1px solid rgba(128,128,128,0.3);"
                )
                lay.addWidget(dot, 0)

        # Badge "activo"
        self._badge = QLabel("activo")
        self._badge.setFont(QFont("Segoe UI", 8))
        self._badge.setFixedWidth(38)
        self._badge.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._badge.setVisible(self.is_active)
        lay.addWidget(self._badge, 0)

    def _refresh_style(self):
        colors = _get_colors()
        bg      = _c(colors, "surface", "background", fallback="#2b2d30")
        bg_sel  = _c(colors, "tab_selected", "accent",  fallback="#3c3f41")
        hover   = _c(colors, "tab_hover", "hover",      fallback="#45484a")
        primary = _c(colors, "primary",                  fallback="#e8eaed")
        accent  = _c(colors, "accent",                   fallback="#8ab4f8")
        secondary = _c(colors, "secondary",              fallback="#9aa0a6")

        if self.is_active:
            row_bg  = bg_sel
            name_color = primary
            dot_bg  = accent
            badge_color = accent
        else:
            row_bg  = "transparent"
            name_color = secondary
            dot_bg  = "transparent"
            badge_color = secondary

        self.setStyleSheet(f"""
            ThemeRow {{
                background: {row_bg};
                border-radius: 6px;
            }}
            ThemeRow:hover {{
                background: {hover};
            }}
        """)
        self._dot.setStyleSheet(
            f"background:{dot_bg}; border-radius:4px;"
            f" border:{'none' if self.is_active else f'1px solid {secondary}'};"
        )
        self._name_lbl.setStyleSheet(
            f"color:{name_color}; font-weight:{'600' if self.is_active else '400'}; background:transparent;"
        )
        self._badge.setStyleSheet(f"color:{badge_color}; background:transparent;")

    def set_active(self, active: bool):
        self.is_active = active
        self._badge.setVisible(active)
        self._refresh_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.theme_id)
        super().mousePressEvent(event)


# ── Separador de sección ──────────────────────────────────────────────────────

class _SectionLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setFont(QFont("Segoe UI", 7, QFont.Medium))
        self.setContentsMargins(8, 8, 0, 2)

    def apply_colors(self, colors: dict):
        color = _c(colors, "secondary", fallback="#666")
        self.setStyleSheet(f"color:{color}; letter-spacing:1px; background:transparent;")


# ── Botón de acción pequeño ───────────────────────────────────────────────────

class _ActionBtn(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Segoe UI", 8))
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(24)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def apply_colors(self, colors: dict):
        bg     = _c(colors, "surface", "background",   fallback="#2b2d30")
        border = _c(colors, "border",                   fallback="#45484a")
        text   = _c(colors, "secondary", "primary",     fallback="#9aa0a6")
        hover  = _c(colors, "tab_hover", "hover",       fallback="#45484a")
        self.setStyleSheet(f"""
            QPushButton {{
                background:{bg};
                border:1px solid {border};
                border-radius:4px;
                color:{text};
                padding:0 8px;
            }}
            QPushButton:hover {{
                background:{hover};
                color:{_c(colors, "primary", fallback="#e8eaed")};
            }}
            QPushButton:pressed {{
                background:{border};
            }}
        """)


# ── ThemeSelectorPanel ────────────────────────────────────────────────────────

class ThemeSelectorPanel(QWidget):
    """Panel minimalista de selección de temas."""

    def __init__(self, theme_engine, browser_instance, parent=None):
        super().__init__(parent)
        self.theme_engine   = theme_engine
        self.browser        = browser_instance
        self._rows: dict[str, ThemeRow] = {}
        self._section_labels: list[_SectionLabel] = []
        self._action_btns: list[_ActionBtn] = []

        self._build()
        self._load_themes()

        if self.theme_engine:
            self.theme_engine.theme_changed.connect(self._on_theme_changed)

    # ── construcción ─────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(0)

        # Cabecera: tema activo
        self._active_label = QLabel()
        self._active_label.setFont(QFont("Segoe UI", 8))
        self._active_label.setContentsMargins(12, 6, 12, 6)
        root.addWidget(self._active_label)

        # Línea divisoria
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        self._divider = line
        root.addWidget(line)

        # Lista scrollable de temas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(6, 4, 6, 4)
        self._list_layout.setSpacing(1)

        scroll.setWidget(self._list_widget)
        root.addWidget(scroll, 1)

        # Barra inferior de acciones
        bar_frame = QFrame()
        self._bar_frame = bar_frame
        bar_lay = QHBoxLayout(bar_frame)
        bar_lay.setContentsMargins(8, 6, 8, 6)
        bar_lay.setSpacing(6)

        self._btn_import  = _ActionBtn("Importar")
        self._btn_export  = _ActionBtn("Exportar")
        self._btn_refresh = _ActionBtn("Actualizar")

        self._btn_import.clicked.connect(self._import_theme)
        self._btn_export.clicked.connect(self._export_current_theme)
        self._btn_refresh.clicked.connect(self._load_themes)

        bar_lay.addWidget(self._btn_import)
        bar_lay.addWidget(self._btn_export)
        bar_lay.addStretch()
        bar_lay.addWidget(self._btn_refresh)

        self._action_btns = [self._btn_import, self._btn_export, self._btn_refresh]
        root.addWidget(bar_frame)

    # ── carga de temas ────────────────────────────────────────────────────────

    def _load_themes(self):
        # Limpiar lista
        for row in self._rows.values():
            row.deleteLater()
        self._rows.clear()
        for lbl in self._section_labels:
            lbl.deleteLater()
        self._section_labels.clear()

        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.theme_engine:
            return

        available = self.theme_engine.get_available_themes()
        current_id = self.theme_engine.get_current_theme()

        # Separar incorporados de personalizados
        builtin  = [t for t in available if t.get("type") != "custom"]
        custom   = [t for t in available if t.get("type") == "custom"]

        def _add_section(label_text: str, themes: list):
            if not themes:
                return
            lbl = _SectionLabel(label_text)
            self._section_labels.append(lbl)
            self._list_layout.addWidget(lbl)
            for t in themes:
                tid   = t["id"]
                tdata = self.theme_engine.get_theme_data(tid)
                row   = ThemeRow(tid, tdata, is_active=(tid == current_id))
                row.selected.connect(self._apply_theme)
                self._rows[tid] = row
                self._list_layout.addWidget(row)

        _add_section("Incorporados", builtin)
        _add_section("Personalizados", custom)
        self._list_layout.addStretch()

        # Actualizar cabecera
        self._update_active_label(current_id)
        self._apply_panel_style()

    # ── aplicación de tema ────────────────────────────────────────────────────

    def _apply_theme(self, theme_id: str):
        if not self.theme_engine:
            return
        try:
            self.theme_engine.apply_theme(theme_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo aplicar el tema:\n{e}")

    # ── señal de cambio de tema ───────────────────────────────────────────────

    def _on_theme_changed(self, theme_id: str):
        for tid, row in self._rows.items():
            row.set_active(tid == theme_id)
        self._update_active_label(theme_id)
        self._apply_panel_style()

    # ── estilo del panel ──────────────────────────────────────────────────────

    def _apply_panel_style(self):
        colors = _get_colors()
        bg       = _c(colors, "background", "surface",  fallback="#1e1f22")
        border   = _c(colors, "border",                  fallback="#3a3d41")
        secondary = _c(colors, "secondary",              fallback="#9aa0a6")
        primary  = _c(colors, "primary",                 fallback="#e8eaed")

        self.setStyleSheet(f"QWidget {{ background:{bg}; }}")
        self._active_label.setStyleSheet(
            f"color:{secondary}; background:{bg}; font-size:8pt;"
        )
        self._divider.setStyleSheet(f"color:{border}; background:{border};")
        self._divider.setFixedHeight(1)
        self._bar_frame.setStyleSheet(
            f"QFrame {{ background:{bg}; border-top:1px solid {border}; }}"
        )
        for btn in self._action_btns:
            btn.apply_colors(colors)
        for lbl in self._section_labels:
            lbl.apply_colors(colors)
        for row in self._rows.values():
            row._refresh_style()

    def _update_active_label(self, theme_id: str):
        if not self.theme_engine:
            return
        tdata = self.theme_engine.get_theme_data(theme_id)
        name  = tdata.get("name", theme_id) if tdata else theme_id
        self._active_label.setText(f"Tema activo  ·  {name}")

    # ── importar / exportar ───────────────────────────────────────────────────

    def _import_theme(self):
        if not self.theme_engine:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Importar tema", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            tid = data.get("id", Path(path).stem)
            if self.theme_engine.create_custom_theme(tid, data, save_to_file=True):
                self._load_themes()
            else:
                QMessageBox.warning(self, "Error", "Archivo de tema no válido.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _export_current_theme(self):
        if not self.theme_engine:
            return
        tid   = self.theme_engine.get_current_theme()
        tdata = self.theme_engine.get_theme_data(tid)
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar tema", f"{tid}_theme.json", "JSON (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(tdata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _open_theme_editor(self):
        if self.browser and hasattr(self.browser, "open_themes_editor_tab"):
            self.browser.open_themes_editor_tab()
