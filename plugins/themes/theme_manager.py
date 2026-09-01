#!/usr/bin/env python3
"""
Professional Theme Manager for Tellectus
Advanced theme system with real-time customization and JSON configuration
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal, QSettings
from PySide6.QtGui import QColor, QPalette

class ThemeManager(QObject):
    """
    Professional theme manager with real-time customization
    """

    # Signals
    theme_changed = Signal(str)  # theme_id
    theme_updated = Signal(dict)  # theme_data
    customization_changed = Signal(dict)  # customization_data

    def __init__(self):
        super().__init__()
        self.current_theme = "light"
        self.themes = {}
        self.customizations = {}
        self.themes_dir = Path("themes")
        self.custom_dir = Path("themes/custom")

        # Create directories
        self.themes_dir.mkdir(exist_ok=True)
        self.custom_dir.mkdir(parents=True, exist_ok=True)

        # Load settings
        self.settings = QSettings("Tellectus", "ThemeManager")

        # Initialize themes
        self._load_default_themes()
        self._load_custom_themes()
        self._load_user_customizations()
    def _load_default_themes(self):
        """Load default system themes"""

        # Light theme
        self.themes["light"] = {
            "id": "light",
            "name": "Light Theme",
            "description": "Clean and modern light theme",
            "version": "1.0.0",
            "author": "Tellectus Team",
            "colors": {
                "primary": "#2c3e50",
                "secondary": "#7f8c8d",
                "background": "#ffffff",
                "surface": "#f8f9fa",
                "accent": "#3498db",
                "success": "#27ae60",
                "warning": "#f39c12",
                "error": "#e74c3c",
                "border": "#dee2e6",
                "hover": "#e9ecef",
                "selected": "#cce8ff",
                "text_primary": "#2c3e50",
                "text_secondary": "#6c757d",
                "text_disabled": "#adb5bd"
            },
            "fonts": {
                "family": "Segoe UI, Arial, sans-serif",
                "size_small": "9pt",
                "size_normal": "10pt",
                "size_large": "12pt",
                "size_title": "14pt",
                "weight_normal": "normal",
                "weight_bold": "bold"
            },
            "spacing": {
                "xs": "2px",
                "sm": "4px",
                "md": "8px",
                "lg": "12px",
                "xl": "16px",
                "xxl": "24px"
            },
            "borders": {
                "radius": "4px",
                "width": "1px",
                "style": "solid"
            },
            "shadows": {
                "enabled": True,
                "color": "rgba(0,0,0,0.1)",
                "blur": "4px",
                "offset": "0px 2px"
            }
        }

        # Dark theme
        self.themes["dark"] = {
            "id": "dark",
            "name": "Dark Theme",
            "description": "Modern dark theme for comfortable viewing",
            "version": "1.0.0",
            "author": "Tellectus Team",
            "colors": {
                "primary": "#ffffff",
                "secondary": "#b0b3b8",
                "background": "#1a1a1a",
                "surface": "#2d2d30",
                "accent": "#0078d4",
                "success": "#107c10",
                "warning": "#ff8c00",
                "error": "#d13438",
                "border": "#3e3e42",
                "hover": "#404040",
                "selected": "#094771",
                "text_primary": "#ffffff",
                "text_secondary": "#b0b3b8",
                "text_disabled": "#6c757d"
            },
            "fonts": {
                "family": "Segoe UI, Arial, sans-serif",
                "size_small": "9pt",
                "size_normal": "10pt",
                "size_large": "12pt",
                "size_title": "14pt",
                "weight_normal": "normal",
                "weight_bold": "bold"
            },
            "spacing": {
                "xs": "2px",
                "sm": "4px",
                "md": "8px",
                "lg": "12px",
                "xl": "16px",
                "xxl": "24px"
            },
            "borders": {
                "radius": "4px",
                "width": "1px",
                "style": "solid"
            },
            "shadows": {
                "enabled": True,
                "color": "rgba(0,0,0,0.3)",
                "blur": "4px",
                "offset": "0px 2px"
            }
        }
    def _load_custom_themes(self):
        """Load custom themes from themes directory"""
        for theme_file in self.themes_dir.glob("*.json"):
            if theme_file.name not in ["light_theme.json", "dark_theme.json"]:
                try:
                    with open(theme_file, 'r', encoding='utf-8') as f:
                        theme_data = json.load(f)
                        theme_id = theme_file.stem
                        self.themes[theme_id] = theme_data
                        print(f"[ThemeManager] Loaded custom theme: {theme_id}")
                except Exception as e:
                    print(f"[ThemeManager] Error loading theme {theme_file}: {e}")
    def _load_user_customizations(self):
        """Load user customizations"""
        customizations_file = self.custom_dir / "user_customizations.json"
        if customizations_file.exists():
            try:
                with open(customizations_file, 'r', encoding='utf-8') as f:
                    self.customizations = json.load(f)
                    print(f"[ThemeManager] Loaded user customizations")
            except Exception as e:
                print(f"[ThemeManager] Error loading customizations: {e}")
    def get_available_themes(self) -> List[Dict[str, Any]]:
        """Get list of available themes"""
        themes_list = []
        for theme_id, theme_data in self.themes.items():
            themes_list.append({
                "id": theme_id,
                "name": theme_data.get("name", theme_id),
                "description": theme_data.get("description", ""),
                "version": theme_data.get("version", "1.0.0"),
                "author": theme_data.get("author", "Unknown")
            })
        return themes_list
    def get_current_theme_data(self) -> Dict[str, Any]:
        """Get current theme data with customizations applied"""
        if self.current_theme not in self.themes:
            return self.themes.get("light", {})
        theme_data = self.themes[self.current_theme].copy()

        # Apply user customizations
        if self.current_theme in self.customizations:
            customizations = self.customizations[self.current_theme]
            self._apply_customizations(theme_data, customizations)
        return theme_data
    def _apply_customizations(self, theme_data: Dict[str, Any], customizations: Dict[str, Any]):
        """Apply customizations to theme data"""
        for key, value in customizations.items():
            if key in theme_data and isinstance(theme_data[key], dict) and isinstance(value, dict):
                theme_data[key].update(value)
            else:
                theme_data[key] = value
    def set_theme(self, theme_id: str) -> bool:
        """Set current theme"""
        if theme_id not in self.themes:
            print(f"[ThemeManager] Theme not found: {theme_id}")
            return False
        try:
            self.current_theme = theme_id
            self.settings.setValue("current_theme", theme_id)

            # Apply theme to application
            self._apply_theme_to_app()

            # Emit signals
            self.theme_changed.emit(theme_id)
            self.theme_updated.emit(self.get_current_theme_data())

            print(f"[ThemeManager] Theme applied: {theme_id}")
            return True
        except Exception as e:
            print(f"[ThemeManager] Error applying theme: {e}")
            return False
    def _apply_theme_to_app(self):
        """Apply current theme to Qt application"""
        app = QApplication.instance()
        if not app:
            return
        theme_data = self.get_current_theme_data()
        colors = theme_data.get("colors", {})

        # Create palette
        palette = QPalette()

        # Set colors
        palette.setColor(QPalette.Window, QColor(colors.get("background", "#ffffff")))
        palette.setColor(QPalette.WindowText, QColor(colors.get("text_primary", "#000000")))
        palette.setColor(QPalette.Base, QColor(colors.get("surface", "#ffffff")))
        palette.setColor(QPalette.AlternateBase, QColor(colors.get("hover", "#f0f0f0")))
        palette.setColor(QPalette.ToolTipBase, QColor(colors.get("surface", "#ffffff")))
        palette.setColor(QPalette.ToolTipText, QColor(colors.get("text_primary", "#000000")))
        palette.setColor(QPalette.Text, QColor(colors.get("text_primary", "#000000")))
        palette.setColor(QPalette.Button, QColor(colors.get("surface", "#ffffff")))
        palette.setColor(QPalette.ButtonText, QColor(colors.get("text_primary", "#000000")))
        palette.setColor(QPalette.BrightText, QColor(colors.get("accent", "#0078d4")))
        palette.setColor(QPalette.Link, QColor(colors.get("accent", "#0078d4")))
        palette.setColor(QPalette.Highlight, QColor(colors.get("selected", "#cce8ff")))
        palette.setColor(QPalette.HighlightedText, QColor(colors.get("text_primary", "#000000")))

        app.setPalette(palette)

        # Apply CSS stylesheet
        css = self._generate_css(theme_data)
        app.setStyleSheet(css)
    def _generate_css(self, theme_data: Dict[str, Any]) -> str:
        """Generate CSS from theme data"""
        colors = theme_data.get("colors", {})
        fonts = theme_data.get("fonts", {})
        spacing = theme_data.get("spacing", {})
        borders = theme_data.get("borders", {})
        shadows = theme_data.get("shadows", {})

        # Generate shadow CSS
        shadow_css = ""
        if shadows.get("enabled", False):
            shadow_css = ""  # box-shadow no soportado en Qt QSS
        css = f"""
        /* Tellectus Theme: {theme_data.get('name', 'Unknown')} */

        /* Global styles */
        * {{
            color: {colors.get('text_primary', '#000000')};
            font-family: {fonts.get('family', 'Arial, sans-serif')};
            font-size: {fonts.get('size_normal', '10pt')};
        }}

        /* Main window */
        QMainWindow {{
            background-color: {colors.get('background', '#ffffff')};
            color: {colors.get('text_primary', '#000000')};
        }}

        /* Widgets */
        QWidget {{
            background-color: {colors.get('background', '#ffffff')};
            color: {colors.get('text_primary', '#000000')};
        }}

        /* Buttons */
        QPushButton {{
            background-color: {colors.get('surface', '#ffffff')};
            color: {colors.get('text_primary', '#000000')};
            border: {borders.get('width', '1px')} {borders.get('style', 'solid')} {colors.get('border', '#cccccc')};
            border-radius: {borders.get('radius', '4px')};
            padding: {spacing.get('md', '8px')} {spacing.get('lg', '12px')};
            min-height: 20px;
            font-weight: {fonts.get('weight_normal', 'normal')};
        }}

        QPushButton:hover {{
            background-color: {colors.get('hover', '#f0f0f0')};
            {shadow_css}
        }}

        QPushButton:pressed {{
            background-color: {colors.get('selected', '#e0e0e0')};
        }}

        /* Line edits */
        QLineEdit {{
            background-color: {colors.get('surface', '#ffffff')};
            color: {colors.get('text_primary', '#000000')};
            border: {borders.get('width', '1px')} {borders.get('style', 'solid')} {colors.get('border', '#cccccc')};
            border-radius: {borders.get('radius', '4px')};
            padding: {spacing.get('sm', '4px')} {spacing.get('md', '8px')};
        }}

        QLineEdit:hover {{
            background-color: {colors.get('hover', '#f0f0f0')};
        }}

        QLineEdit:focus {{
            border-color: {colors.get('accent', '#0078d4')};
        }}

        /* Tabs */
        QTabWidget::pane {{
            background-color: {colors.get('surface', '#ffffff')};
            border: {borders.get('width', '1px')} {borders.get('style', 'solid')} {colors.get('border', '#cccccc')};
        }}

        QTabBar::tab {{
            background-color: {colors.get('background', '#f0f0f0')};
            color: {colors.get('text_secondary', '#666666')};
            padding: {spacing.get('md', '8px')} {spacing.get('lg', '12px')};
            border: {borders.get('width', '1px')} {borders.get('style', 'solid')} {colors.get('border', '#cccccc')};
            border-bottom: none;
        }}

        QTabBar::tab:selected {{
            background-color: {colors.get('surface', '#ffffff')};
            color: {colors.get('text_primary', '#000000')};
        }}

        QTabBar::tab:hover {{
            background-color: {colors.get('hover', '#f0f0f0')};
        }}

        /* Lists and tables */
        QListWidget, QTreeWidget, QTableWidget {{
            background-color: {colors.get('surface', '#ffffff')};
            color: {colors.get('text_primary', '#000000')};
            border: {borders.get('width', '1px')} {borders.get('style', 'solid')} {colors.get('border', '#cccccc')};
            selection-background-color: {colors.get('selected', '#cce8ff')};
        }}

        /* Groups */
        QGroupBox {{
            color: {colors.get('text_primary', '#000000')};
            border: {borders.get('width', '1px')} {borders.get('style', 'solid')} {colors.get('border', '#cccccc')};
            border-radius: {borders.get('radius', '4px')};
            margin-top: {spacing.get('md', '8px')};
            padding-top: {spacing.get('md', '8px')};
        }}

        QGroupBox::title {{
            color: {colors.get('accent', '#0078d4')};
            font-weight: {fonts.get('weight_bold', 'bold')};
            padding: 0 {spacing.get('sm', '4px')};
        }}

        /* Toolbars */
        QToolBar {{
            background-color: {colors.get('surface', '#ffffff')};
            color: {colors.get('text_primary', '#000000')};
            border: none;
            spacing: {spacing.get('sm', '4px')};
        }}

        /* Menus */
        QMenu {{
            background-color: {colors.get('surface', '#ffffff')};
            color: {colors.get('text_primary', '#000000')};
            border: {borders.get('width', '1px')} {borders.get('style', 'solid')} {colors.get('border', '#cccccc')};
        }}

        QMenu::item:selected {{
            background-color: {colors.get('selected', '#cce8ff')};
        }}

        /* Scrollbars */
        QScrollBar:vertical {{
            background-color: {colors.get('surface', '#ffffff')};
            width: 12px;
            border-radius: 6px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {colors.get('border', '#cccccc')};
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {colors.get('hover', '#f0f0f0')};
        }}
        """

        return css
    def save_customization(self, theme_id: str, customization: Dict[str, Any]):
        """Save customization for a theme"""
        if theme_id not in self.customizations:
            self.customizations[theme_id] = {}
        self.customizations[theme_id].update(customization)

        # Save to file
        customizations_file = self.custom_dir / "user_customizations.json"
        try:
            with open(customizations_file, 'w', encoding='utf-8') as f:
                json.dump(self.customizations, f, indent=2, ensure_ascii=False)
            # Emit signal
            self.customization_changed.emit(customization)

            # Reapply theme if it's current
            if theme_id == self.current_theme:
                self.set_theme(theme_id)
            print(f"[ThemeManager] Customization saved for theme: {theme_id}")
            return True
        except Exception as e:
            print(f"[ThemeManager] Error saving customization: {e}")
            return False
    def create_custom_theme(self, theme_data: Dict[str, Any]) -> bool:
        """Create a new custom theme"""
        theme_id = theme_data.get("id", "custom_theme")

        try:
            # Save theme file
            theme_file = self.custom_dir / f"{theme_id}.json"
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)
            # Add to themes
            self.themes[theme_id] = theme_data

            print(f"[ThemeManager] Custom theme created: {theme_id}")
            return True
        except Exception as e:
            print(f"[ThemeManager] Error creating custom theme: {e}")
            return False
    def export_theme(self, theme_id: str, file_path: str) -> bool:
        """Export theme to file"""
        if theme_id not in self.themes:
            return False
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.themes[theme_id], f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ThemeManager] Error exporting theme: {e}")
            return False
    def import_theme(self, file_path: str) -> bool:
        """Import theme from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            theme_id = theme_data.get("id", Path(file_path).stem)
            self.themes[theme_id] = theme_data

            # Save to custom themes
            theme_file = self.custom_dir / f"{theme_id}.json"
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2, ensure_ascii=False)
            print(f"[ThemeManager] Theme imported: {theme_id}")
            return True
        except Exception as e:
            print(f"[ThemeManager] Error importing theme: {e}")
            return False

# Global instance
theme_manager = ThemeManager()
