#!/usr/bin/env python3

"""

Theme Engine - Motor unificado de gestión de temas

Unifica theme_manager.py y theme_loader.py eliminando duplicación.
Compatible con código existente mediante API retrocompatible.

Migración UI - Consolidación de Sistemas de Temas
Fecha: 2025-01-27

"""



import json

import os

from pathlib import Path

from typing import Dict, Optional, List

from PySide6.QtWidgets import QApplication

from PySide6.QtCore import QObject, Signal, QSettings


# Import constants
try:
    from ui.core.constants import ThemeDefaults
except ImportError:
    # Fallback si constants.py no está disponible
    class ThemeDefaults:
        DEFAULT_THEME = "light"
        THEME_DIRECTORY = "ui/themes"
        CUSTOM_THEME_DIRECTORY = "ui/themes/custom"
        BASE_THEMES = ["light", "dark"]


class ThemeEngine(QObject):

    """

    Motor unificado de gestión de temas
    
    Combina funcionalidades de theme_manager.py y theme_loader.py
    Mantiene compatibilidad con código existente

    """

    

    # Señales para notificar cambios de tema

    theme_changed = Signal(str)  # nombre del tema

    theme_loaded = Signal(dict)  # datos del tema

    

    def __init__(self):

        super().__init__()

        self.current_theme = ThemeDefaults.DEFAULT_THEME

        self.themes = {}

        self.settings = QSettings("Scrapelio", "Settings")

        
        # Directorios de temas
        self.theme_dir = Path(ThemeDefaults.THEME_DIRECTORY)
        self.custom_theme_dir = Path(ThemeDefaults.CUSTOM_THEME_DIRECTORY)
        
        # Crear directorios si no existen
        self.theme_dir.mkdir(parents=True, exist_ok=True)
        self.custom_theme_dir.mkdir(parents=True, exist_ok=True)

        

        # Cargar todos los temas disponibles

        self._load_theme_files()

        

        # Aplicar tema guardado o por defecto

        saved_theme = self.settings.value("theme", ThemeDefaults.DEFAULT_THEME)

        self.apply_theme(saved_theme)

    

    def _load_theme_files(self):

        """Carga todos los archivos de tema disponibles desde múltiples ubicaciones"""

        # Cargar temas base (obligatorios)

        base_theme_files = [

            "light_theme.json",

            "dark_theme.json"

        ]

        

        # Cargar temas base - buscar en múltiples ubicaciones
        for theme_file in base_theme_files:
            # 1. Buscar en ui/themes/ (nueva ubicación)
            theme_path = self.theme_dir / theme_file
            
            # 2. Fallback a raíz del proyecto (compatibilidad)
            if not theme_path.exists():
                theme_path = Path(theme_file)
            
            if theme_path.exists():
                try:
                    with open(theme_path, 'r', encoding='utf-8') as f:
                        theme_data = json.load(f)
                        theme_id = theme_data.get("id") or theme_path.stem.replace("_theme", "")
                        theme_name_key = theme_data.get("name", theme_id).lower()
                        
                        # Guardar con ambas claves (por ID y por nombre) para flexibilidad
                        self.themes[theme_id.lower()] = theme_data
                        self.themes[theme_name_key] = theme_data
                        
                        print(f"[ThemeEngine] Loaded base theme: {theme_data.get('name', theme_id)}")
                except Exception as e:
                    print(f"[ThemeEngine] Failed to load theme {theme_file}: {e}")
        
        # Cargar temas personalizados desde ui/themes/custom/
        if self.custom_theme_dir.exists():
            for theme_file in self.custom_theme_dir.glob("*.json"):
                try:
                    with open(theme_file, 'r', encoding='utf-8') as f:
                        theme_data = json.load(f)
                        theme_id = theme_data.get("id") or theme_file.stem
                        theme_name_key = theme_data.get("name", theme_id).lower()
                        
                        self.themes[theme_id.lower()] = theme_data
                        self.themes[theme_name_key] = theme_data
                        
                        print(f"[ThemeEngine] Loaded custom theme: {theme_data.get('name', theme_id)}")
                except Exception as e:
                    print(f"[ThemeEngine] Failed to load custom theme {theme_file}: {e}")

    

    def get_theme_data(self, theme_name: str = None) -> Dict:

        """Obtiene los datos del tema actual o especificado"""

        if theme_name is None:

            theme_name = self.current_theme

        

        return self.themes.get(theme_name.lower(), {})

    

    def get_color(self, color_key: str, theme_name: str = None) -> str:

        """Obtiene un color específico del tema actual o especificado"""

        theme_data = self.get_theme_data(theme_name)

        colors = theme_data.get("colors", {})

        return colors.get(color_key, "#000000")  # Fallback a negro

    

    def get_font(self, font_key: str, theme_name: str = None) -> str:

        """Obtiene una configuración de fuente del tema actual o especificado"""

        theme_data = self.get_theme_data(theme_name)

        fonts = theme_data.get("fonts", {})

        return fonts.get(font_key, "10pt")

    

    def get_spacing(self, spacing_key: str, theme_name: str = None) -> str:

        """Obtiene un espaciado del tema actual o especificado"""

        theme_data = self.get_theme_data(theme_name)

        spacing = theme_data.get("spacing", {})

        return spacing.get(spacing_key, "4px")

    

    def get_border(self, border_key: str, theme_name: str = None) -> str:

        """Obtiene una configuración de borde del tema actual o especificado"""

        theme_data = self.get_theme_data(theme_name)

        borders = theme_data.get("borders", {})

        return borders.get(border_key, "1px")

    

    def apply_theme(self, theme_name: str) -> bool:

        """Aplica un tema específico"""

        key = theme_name.lower().strip()

        theme_data = self.themes.get(key)

        

        if not theme_data:

            print(f"[ERROR] Theme '{theme_name}' not found")

            return False

        

        try:

            # Generar CSS basado en el tema

            css = self._generate_complete_css(theme_data)

            

            # Aplicar a la aplicación

            app = QApplication.instance()

            if app:

                app.setStyleSheet(css)

                print(f"[OK] Applied theme: {theme_data.get('name', key)}")

            

            # Guardar tema actual

            self.current_theme = key

            self.settings.setValue("theme", key)

            

            # Emitir señales

            self.theme_changed.emit(key)

            self.theme_loaded.emit(theme_data)

            

            return True

            

        except Exception as e:

            print(f"[ERROR] Failed to apply theme {theme_name}: {e}")

            return False

    

    def _generate_complete_css(self, theme_data: Dict) -> str:

        """Genera CSS completo basado en los datos del tema"""

        colors = theme_data.get("colors", {})

        fonts = theme_data.get("fonts", {})

        spacing = theme_data.get("spacing", {})

        borders = theme_data.get("borders", {})

        

        return f"""

        /* === TEMA: {theme_data.get('name', 'Unknown')} === */

        

        /* Estilos base */

        * {{

            color: {colors.get('primary', '#000000')} !important;

            font-family: {fonts.get('family', 'Segoe UI, Arial, sans-serif')} !important;

        }}

        

        QMainWindow {{

            background-color: {colors.get('background', '#f5f5f5')} !important;

            color: {colors.get('primary', '#000000')} !important;

        }}

        

        QWidget {{

            background-color: {colors.get('background', '#f5f5f5')} !important;

            color: {colors.get('primary', '#000000')} !important;

        }}

        

        /* Toolbar */

        QToolBar {{

            background-color: {colors.get('toolbar_background', colors.get('surface', '#ffffff'))} !important;

            border: {borders.get('width', '1px')} solid {colors.get('toolbar_border', colors.get('border', '#e0e0e0'))} !important;

            border-radius: {borders.get('radius', '4px')} !important;

            padding: {spacing.get('md', '8px')} !important;

            spacing: {spacing.get('sm', '4px')} !important;

        }}

        

        /* Botones de toolbar (compactos tipo Chrome) */

        QToolBar QToolButton {{

            background-color: transparent !important;

            color: {colors.get('primary', '#000000')} !important;

            border: none !important;

            border-radius: 16px !important;

            padding: 4px !important;

            margin: 0px !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

            min-width: 32px !important;

            min-height: 32px !important;

            max-width: 32px !important;

            max-height: 32px !important;

        }}

        

        QToolBar QToolButton:hover {{

            background-color: {colors.get('button_hover', colors.get('hover', '#e8e8e8'))} !important;

        }}

        

        QToolBar QToolButton:pressed {{

            background-color: {colors.get('button_pressed', colors.get('selected', '#cce8ff'))} !important;

        }}

        

        /* Botones generales */

        QPushButton {{

            background-color: {colors.get('button_background', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('primary', '#000000')} !important;

            border: none !important;

            border-radius: {borders.get('radius', '4px')} !important;

            padding: 4px 8px !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

            font-weight: bold !important;

            min-height: 24px !important;

        }}

        

        QPushButton:hover {{

            background-color: {colors.get('button_hover', colors.get('hover', '#e8e8e8'))} !important;

        }}

        

        QPushButton:pressed {{

            background-color: {colors.get('button_pressed', colors.get('selected', '#cce8ff'))} !important;

        }}

        

        /* Botones de control de ventana */

        QToolBar QPushButton {{

            background-color: {colors.get('button_background', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('primary', '#000000')} !important;

            border: none !important;

            border-radius: {borders.get('radius', '4px')} !important;

            padding: 2px 4px !important;

            font-size: 12px !important;

            font-weight: bold !important;

            min-width: 24px !important;

            min-height: 24px !important;

            max-width: 24px !important;

            max-height: 24px !important;

        }}

        

        QToolBar QPushButton:hover {{

            background-color: {colors.get('button_hover', colors.get('hover', '#e8e8e8'))} !important;

        }}

        

        QToolBar QPushButton:pressed {{

            background-color: {colors.get('button_pressed', colors.get('selected', '#cce8ff'))} !important;

        }}

        

        /* Campos de entrada */

        QLineEdit {{

            background-color: {colors.get('input_background', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('primary', '#000000')} !important;

            border: {borders.get('width', '1px')} solid {colors.get('input_border', colors.get('border', '#e0e0e0'))} !important;

            border-radius: {borders.get('radius', '4px')} !important;

            padding: {spacing.get('sm', '4px')} {spacing.get('md', '8px')} !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

        }}

        

        QLineEdit:focus {{

            border-color: {colors.get('input_focus', colors.get('accent', '#0078d4'))} !important;

            box-shadow: 0 0 0 2px {colors.get('input_focus', colors.get('accent', '#0078d4'))}33 !important;

        }}

        

        QLineEdit:hover {{

            border-color: {colors.get('accent', '#0078d4')} !important;

        }}

        

        /* Pestañas */

        QTabWidget::pane {{

            background-color: {colors.get('background', '#f5f5f5')} !important;

            border: {borders.get('width', '1px')} solid {colors.get('border', '#e0e0e0')} !important;

        }}

        

        /* Pestañas (estilo Chrome - compacto con efecto isla) */

        QTabBar {{

            background-color: transparent !important;

        }}

        

        QTabBar::tab {{

            background-color: {colors.get('tab_background', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('secondary', '#666666')} !important;

            border: none !important;

            padding: 5px 12px !important;

            margin-right: 4px !important;

            margin-top: 4px !important;

            border-radius: 8px !important;

            min-width: 100px !important;

            max-width: 200px !important;

            height: 26px !important;

            font-size: 12px !important;

        }}

        

        QTabBar::tab:selected {{

            background-color: {colors.get('tab_selected', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('primary', '#000000')} !important;

            margin-top: 2px !important;

            height: 28px !important;

        }}

        

        QTabBar::tab:hover {{

            background-color: {colors.get('tab_hover', colors.get('hover', '#e8e8e8'))} !important;

        }}

        

        /* Dock widgets */

        QDockWidget::title {{

            background-color: {colors.get('surface', '#ffffff')} !important;

            color: {colors.get('primary', '#000000')} !important;

            padding: {spacing.get('sm', '4px')} {spacing.get('md', '8px')} !important;

        }}

        

        /* Scrollbars */

        QScrollBar:vertical, QScrollBar:horizontal {{

            background-color: {colors.get('background', '#f5f5f5')} !important;

            border: none !important;

            width: 12px !important;

        }}

        

        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{

            background-color: {colors.get('border', '#e0e0e0')} !important;

            border-radius: 6px !important;

            min-height: 20px !important;

        }}

        

        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{

            background-color: {colors.get('accent', '#0078d4')} !important;

        }}

        

        /* Separadores */

        QFrame {{

            color: {colors.get('border', '#e0e0e0')} !important;

        }}

        

        /* Widgets de texto - CRÍTICO para visibilidad */

        QTextEdit {{

            background-color: {colors.get('input_background', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('primary', '#000000')} !important;

            border: {borders.get('width', '1px')} solid {colors.get('input_border', colors.get('border', '#e0e0e0'))} !important;

            border-radius: {borders.get('radius', '4px')} !important;

            padding: {spacing.get('sm', '4px')} !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

            selection-background-color: {colors.get('selected', '#cce8ff')} !important;

            selection-color: {colors.get('primary', '#000000')} !important;

        }}

        

        QPlainTextEdit {{

            background-color: {colors.get('input_background', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('primary', '#000000')} !important;

            border: {borders.get('width', '1px')} solid {colors.get('input_border', colors.get('border', '#e0e0e0'))} !important;

            border-radius: {borders.get('radius', '4px')} !important;

            padding: {spacing.get('sm', '4px')} !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

            selection-background-color: {colors.get('selected', '#cce8ff')} !important;

            selection-color: {colors.get('primary', '#000000')} !important;

        }}

        

        /* Tablas - CRÍTICO para visibilidad */

        QTableWidget {{

            background-color: {colors.get('input_background', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('primary', '#000000')} !important;

            border: {borders.get('width', '1px')} solid {colors.get('input_border', colors.get('border', '#e0e0e0'))} !important;

            border-radius: {borders.get('radius', '4px')} !important;

            gridline-color: {colors.get('border', '#e0e0e0')} !important;

            selection-background-color: {colors.get('selected', '#cce8ff')} !important;

            selection-color: {colors.get('primary', '#000000')} !important;

        }}

        

        QTableWidget::item {{

            color: {colors.get('primary', '#000000')} !important;

            padding: 4px !important;

        }}

        

        QTableWidget::item:selected {{

            background-color: {colors.get('selected', '#cce8ff')} !important;

            color: {colors.get('primary', '#000000')} !important;

        }}

        

        QHeaderView::section {{

            background-color: {colors.get('tab_background', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('primary', '#000000')} !important;

            border: {borders.get('width', '1px')} solid {colors.get('border', '#e0e0e0')} !important;

            padding: 4px !important;

            font-weight: bold !important;

        }}

        

        /* ComboBox */

        QComboBox {{

            background-color: {colors.get('input_background', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('primary', '#000000')} !important;

            border: {borders.get('width', '1px')} solid {colors.get('input_border', colors.get('border', '#e0e0e0'))} !important;

            border-radius: {borders.get('radius', '4px')} !important;

            padding: {spacing.get('sm', '4px')} {spacing.get('md', '8px')} !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

        }}

        

        QComboBox:hover {{

            border-color: {colors.get('accent', '#0078d4')} !important;

        }}

        

        QComboBox::drop-down {{

            border: none !important;

            background-color: transparent !important;

        }}

        

        QComboBox QAbstractItemView {{

            background-color: {colors.get('input_background', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('primary', '#000000')} !important;

            border: {borders.get('width', '1px')} solid {colors.get('border', '#e0e0e0')} !important;

            selection-background-color: {colors.get('selected', '#cce8ff')} !important;

            selection-color: {colors.get('primary', '#000000')} !important;

        }}

        

        /* SpinBox */

        QSpinBox, QDoubleSpinBox {{

            background-color: {colors.get('input_background', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('primary', '#000000')} !important;

            border: {borders.get('width', '1px')} solid {colors.get('input_border', colors.get('border', '#e0e0e0'))} !important;

            border-radius: {borders.get('radius', '4px')} !important;

            padding: {spacing.get('sm', '4px')} !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

        }}

        

        /* CheckBox y RadioButton */

        QCheckBox, QRadioButton {{

            color: {colors.get('primary', '#000000')} !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

            spacing: 5px !important;

        }}

        

        /* GroupBox */

        QGroupBox {{

            color: {colors.get('primary', '#000000')} !important;

            border: {borders.get('width', '1px')} solid {colors.get('border', '#e0e0e0')} !important;

            border-radius: {borders.get('radius', '4px')} !important;

            margin-top: 10px !important;

            font-weight: bold !important;

            padding-top: 10px !important;

        }}

        

        QGroupBox::title {{

            color: {colors.get('primary', '#000000')} !important;

            subcontrol-origin: margin !important;

            subcontrol-position: top left !important;

            padding: 0 5px !important;

            background-color: {colors.get('background', '#f5f5f5')} !important;

        }}

        

        /* Labels generales */

        QLabel {{

            color: {colors.get('primary', '#000000')} !important;

            background-color: transparent !important;

        }}

        

        /* ListWidget - CRÍTICO para visibilidad */

        QListWidget {{

            background-color: {colors.get('input_background', colors.get('surface', '#ffffff'))} !important;

            color: {colors.get('primary', '#000000')} !important;

            border: {borders.get('width', '1px')} solid {colors.get('input_border', colors.get('border', '#e0e0e0'))} !important;

            border-radius: {borders.get('radius', '4px')} !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

            selection-background-color: {colors.get('selected', '#cce8ff')} !important;

            selection-color: {colors.get('primary', '#000000')} !important;

        }}

        

        QListWidget::item {{

            color: {colors.get('primary', '#000000')} !important;

            padding: 4px !important;

        }}

        

        QListWidget::item:selected {{

            background-color: {colors.get('selected', '#cce8ff')} !important;

            color: {colors.get('primary', '#000000')} !important;

        }}

        

        QListWidget::item:hover {{

            background-color: {colors.get('hover', '#e8e8e8')} !important;

        }}

        

        /* Estilos específicos para botones de login/logout */

        QPushButton[class="login-button"] {{

            background-color: {colors.get('login_button', colors.get('accent', '#0078d4'))} !important;

            color: white !important;

            border: none !important;

            border-radius: {borders.get('radius', '4px')} !important;

            font-weight: bold !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

        }}

        

        QPushButton[class="login-button"]:hover {{

            background-color: {colors.get('login_button_hover', colors.get('accent', '#0078d4'))} !important;

        }}

        

        QPushButton[class="login-button"]:pressed {{

            background-color: {colors.get('login_button_pressed', colors.get('accent', '#0078d4'))} !important;

        }}

        

        QPushButton[class="logout-button"] {{

            background-color: {colors.get('logout_button', colors.get('error', '#d13438'))} !important;

            color: white !important;

            border: none !important;

            border-radius: {borders.get('radius', '4px')} !important;

            font-weight: bold !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

        }}

        

        QPushButton[class="logout-button"]:hover {{

            background-color: {colors.get('logout_button_hover', colors.get('error', '#d13438'))} !important;

        }}

        

        QPushButton[class="logout-button"]:pressed {{

            background-color: {colors.get('logout_button_pressed', colors.get('error', '#d13438'))} !important;

        }}

        

        /* Estilos para etiquetas de estado */

        QLabel[class="status-label"] {{

            color: {colors.get('status_success', colors.get('success', '#107c10'))} !important;

            font-weight: bold !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

            padding: 0 8px !important;

        }}

        

        /* Estilos específicos del Plugin Store */

        QFrame[class="plugin-item-container"] {{

            background-color: {colors.get('surface', '#ffffff')} !important;

            border: {borders.get('width', '1px')} solid {colors.get('border', '#e0e0e0')} !important;

            border-radius: 8px !important;

            padding: 10px !important;

        }}

        

        QFrame[class="plugin-item-container"]:hover {{

            background-color: {colors.get('hover', '#e8e8e8')} !important;

            border-color: {colors.get('accent', '#0078d4')} !important;

        }}

        

        QLabel[class="plugin-name"] {{

            color: {colors.get('primary', '#000000')} !important;

            font-weight: bold !important;

            font-size: {fonts.get('size_large', '12pt')} !important;

        }}

        

        QLabel[class="plugin-price"] {{

            color: {colors.get('success', '#107c10')} !important;

            background-color: {colors.get('success', '#107c10')}22 !important;

            padding: 4px 8px !important;

            border-radius: 4px !important;

            font-weight: bold !important;

            font-size: {fonts.get('size_normal', '10pt')} !important;

        }}

        

        QLabel[class="plugin-description"] {{

            color: {colors.get('secondary', '#333333')} !important;

            font-size: {fonts.get('size_small', '9pt')} !important;

        }}

        

        QLabel[class="plugin-features"] {{

            color: {colors.get('secondary', '#333333')} !important;

            font-size: {fonts.get('size_small', '9pt')} !important;

            font-style: italic !important;

        }}
        """ + self._apply_theme_processors(theme_data)

    
    def _apply_theme_processors(self, theme_data: Dict) -> str:
        """Aplica procesadores de temas específicos para componentes"""
        css_parts = []
        try:
            from theme_processors import (
                browser_theme_processor,
                scraping_theme_processor,
                chat_theme_processor,
                bookmarks_theme_processor,
                privacy_theme_processor
            )
            for processor in (
                browser_theme_processor,
                scraping_theme_processor,
                chat_theme_processor,
                bookmarks_theme_processor,
                privacy_theme_processor
            ):
                try:
                    css_parts.append(processor(theme_data))
                except Exception as e:
                    print(f"[WARNING] Theme processor failed: {e}")
        except Exception as e:
            print(f"[WARNING] Error applying theme processors: {e}")
        return "".join(css_parts)

    def get_current_theme(self) -> str:

        """Retorna el tema actual"""

        return self.current_theme

    

    def toggle_theme(self):

        """Alterna entre tema claro y oscuro"""

        new_theme = "dark" if self.current_theme == "light" else "light"

        self.apply_theme(new_theme)

    

    def get_available_themes(self) -> List[Dict[str, str]]:
        """
        Retorna lista de temas disponibles con metadatos
        
        NUEVO: Funcionalidad de theme_loader.py
        """
        themes_list = []
        seen_ids = set()
        
        for theme_id, theme_data in self.themes.items():
            # Evitar duplicados (temas guardados por ID y por nombre)
            if " " in theme_id or theme_id in seen_ids:
                continue
            
            seen_ids.add(theme_id)
            try:
                from ui.core.constants import ThemeDefaults
                base_themes = ThemeDefaults.BASE_THEMES
            except:
                base_themes = ["light", "dark"]
                
            themes_list.append({
                "id": theme_id,
                "name": theme_data.get("name", theme_id),
                "description": theme_data.get("description", ""),
                "version": theme_data.get("version", "1.0.0"),
                "type": "base" if theme_id in base_themes else "custom"
            })
        
        return sorted(themes_list, key=lambda x: (x["type"] != "base", x["name"]))
    
    def create_custom_theme(self, theme_id: str, theme_data: Dict, save_to_file: bool = True) -> bool:
        """
        Crea un tema personalizado
        
        NUEVO: Funcionalidad de theme_loader.py
        """
        try:
            # Validar datos del tema
            if not self._validate_theme_data(theme_data):
                print(f"[ThemeEngine] Invalid theme data for {theme_id}")
                return False
            
            # Agregar metadatos
            theme_data["id"] = theme_id
            theme_data["version"] = theme_data.get("version", "1.0.0")
            theme_data["type"] = "custom"
            
            # Guardar en memoria
            self.themes[theme_id.lower()] = theme_data
            self.themes[theme_data.get("name", theme_id).lower()] = theme_data
            
            # Guardar en archivo si se solicita
            if save_to_file:
                theme_file = self.custom_theme_dir / f"{theme_id}.json"
                with open(theme_file, 'w', encoding='utf-8') as f:
                    json.dump(theme_data, f, indent=2, ensure_ascii=False)
                print(f"[ThemeEngine] Custom theme created: {theme_id}")
            
            return True
            
        except Exception as e:
            print(f"[ThemeEngine] Failed to create custom theme {theme_id}: {e}")
            return False
    
    def delete_custom_theme(self, theme_id: str) -> bool:
        """
        Elimina un tema personalizado
        
        NUEVO: Funcionalidad de theme_loader.py
        """
        try:
            try:
                from ui.core.constants import ThemeDefaults
                base_themes = ThemeDefaults.BASE_THEMES
            except:
                base_themes = ["light", "dark"]
                
            if theme_id in base_themes:
                print(f"[ThemeEngine] Cannot delete base theme: {theme_id}")
                return False
            
            # Eliminar de memoria
            if theme_id.lower() in self.themes:
                del self.themes[theme_id.lower()]
            
            # Eliminar archivo
            theme_file = self.custom_theme_dir / f"{theme_id}.json"
            if theme_file.exists():
                theme_file.unlink()
            
            print(f"[ThemeEngine] Custom theme deleted: {theme_id}")
            return True
            
        except Exception as e:
            print(f"[ThemeEngine] Failed to delete custom theme {theme_id}: {e}")
            return False
    
    def _validate_theme_data(self, theme_data: Dict) -> bool:
        """
        Valida que los datos del tema sean correctos
        
        NUEVO: Funcionalidad de theme_loader.py
        """
        required_keys = ["name", "colors"]
        for key in required_keys:
            if key not in theme_data:
                return False
        
        # Validar colores requeridos
        required_colors = ["primary", "background", "surface"]
        colors = theme_data.get("colors", {})
        for color in required_colors:
            if color not in colors:
                return False
        
        return True
    
    def reload_themes(self):
        """
        Recarga todos los temas desde archivos
        
        NUEVO: Funcionalidad de theme_loader.py
        """
        self.themes.clear()
        self._load_theme_files()
        print("[ThemeEngine] Themes reloaded")



# Instancia global del theme engine

_theme_engine = None



def get_theme_engine() -> ThemeEngine:

    """Obtiene la instancia global del theme engine"""

    global _theme_engine

    if _theme_engine is None:

        _theme_engine = ThemeEngine()

    return _theme_engine


# Alias para retrocompatibilidad con theme_manager.py
get_theme_manager = get_theme_engine

# Alias para retrocompatibilidad (ThemeManager -> ThemeEngine)
ThemeManager = ThemeEngine


def get_color(color_key: str, theme_name: str = None) -> str:

    """Función de conveniencia para obtener un color"""

    return get_theme_engine().get_color(color_key, theme_name)



def get_font(font_key: str, theme_name: str = None) -> str:

    """Función de conveniencia para obtener una fuente"""

    return get_theme_engine().get_font(font_key, theme_name)



def get_spacing(spacing_key: str, theme_name: str = None) -> str:

    """Función de conveniencia para obtener un espaciado"""

    return get_theme_engine().get_spacing(spacing_key, theme_name)



def get_border(border_key: str, theme_name: str = None) -> str:

    """Función de conveniencia para obtener un borde"""

    return get_theme_engine().get_border(border_key, theme_name)

