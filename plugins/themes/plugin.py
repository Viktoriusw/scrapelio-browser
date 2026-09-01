#!/usr/bin/env python3
"""
Advanced Theme System Plugin for Scrapelio Browser
Integrates with the consolidated ThemeEngine in /ui/core/theme_engine.py
"""

import sys
from pathlib import Path

# Add plugin directory to path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

from plugins.plugin_base import PluginBase, PluginMetadata
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QIcon


class ThemePlugin(PluginBase):
    """
    Advanced Theme System Plugin

    Provides a professional theme management interface integrated with
    the browser's consolidated ThemeEngine.

    Features:
    - Theme selector (light, dark, custom themes)
    - Theme editor for creating custom themes
    - Import/Export themes
    - Live preview
    - Integration with ThemeEngine
    """

    def __init__(self):
        super().__init__()
        self.browser = None
        self.theme_engine = None
        self.theme_selector_widget = None
        self.theme_editor_widget = None
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        return PluginMetadata(
            id="themes",
            name="Custom Themes",
            version="2.0.0",
            author="Scrapelio Team",
            description="Gestión avanzada de temas con editor visual, selector intuitivo y soporte para temas personalizados. Integrado con el sistema de temas consolidado del navegador.",
            min_browser_version="1.0.0",
            max_browser_version="999.0.0",
            dependencies=[],
            permissions=["ui_modification"],
            icon="🎨",
            tags=["themes", "customization", "ui", "design"]
        )
    def initialize(self, browser_instance) -> bool:
        """Initialize the plugin"""
        try:
            print("[ThemePlugin] Initializing...")
            self.browser = browser_instance

            # Get the global ThemeEngine instance
            try:
                from ui.core.theme_engine import get_theme_engine
                self.theme_engine = get_theme_engine()
                print("[ThemePlugin] Connected to ThemeEngine successfully")
            except ImportError as e:
                print(f"[ThemePlugin] WARNING: Could not import ThemeEngine: {e}")
                print("[ThemePlugin] Plugin will have limited functionality")
                return False
            # Load theme selector and editor components
            try:
                from theme_selector_panel import ThemeSelectorPanel
                from theme_editor_panel import ThemeEditorPanel

                self.theme_selector_widget = ThemeSelectorPanel(self.theme_engine, self.browser)
                self.theme_editor_widget = ThemeEditorPanel(self.theme_engine, self.browser)
                print("[ThemePlugin] UI components loaded successfully")
            except ImportError as e:
                print(f"[ThemePlugin] WARNING: Could not import UI components: {e}")
                # Create fallback simple widgets
                self._create_fallback_widgets()
            print("[ThemePlugin] Initialized successfully")
            return True
        except Exception as e:
            print(f"[ThemePlugin] Initialization error: {e}")
            import traceback
            traceback.print_exc()
            return False
    def shutdown(self) -> bool:
        """Shutdown the plugin"""
        try:
            print("[ThemePlugin] Shutting down...")

            # Cleanup widgets
            if self.theme_selector_widget:
                self.theme_selector_widget.deleteLater()
                self.theme_selector_widget = None
            if self.theme_editor_widget:
                self.theme_editor_widget.deleteLater()
                self.theme_editor_widget = None
            self.browser = None
            self.theme_engine = None

            print("[ThemePlugin] Shutdown complete")
            return True
        except Exception as e:
            print(f"[ThemePlugin] Shutdown error: {e}")
            return False
    def _create_fallback_widgets(self):
        """Create simple fallback widgets when UI components can't be loaded"""
        self.theme_selector_widget = QWidget()
        layout = QVBoxLayout(self.theme_selector_widget)
        layout.addWidget(QLabel("Theme Selector UI not available"))

        self.theme_editor_widget = QWidget()
        layout = QVBoxLayout(self.theme_editor_widget)
        layout.addWidget(QLabel("Theme Editor UI not available"))
    def get_settings_widget(self):
        """Return the theme selector widget as settings"""
        return self.theme_selector_widget if self.theme_selector_widget else None
    def get_theme_selector(self):
        """Get the theme selector widget"""
        return self.theme_selector_widget
    def get_theme_editor(self):
        """Get the theme editor widget"""
        return self.theme_editor_widget
    def get_toolbar_actions(self) -> list:
        """Return toolbar actions"""
        actions = []

        # Quick theme toggle action (light/dark)
        if self.theme_engine:
            toggle_action = QAction("🎨", self.browser)
            toggle_action.setToolTip("Toggle Light/Dark Theme")
            toggle_action.triggered.connect(self._quick_toggle_theme)
            actions.append(toggle_action)
        return actions
    def _quick_toggle_theme(self):
        """Quick toggle between light and dark theme"""
        if not self.theme_engine:
            return
        try:
            current = self.theme_engine.get_current_theme()
            new_theme = "dark" if current == "light" else "light"
            self.theme_engine.apply_theme(new_theme)
            print(f"[ThemePlugin] Toggled theme to: {new_theme}")
        except Exception as e:
            print(f"[ThemePlugin] Error toggling theme: {e}")
    def on_browser_startup(self):
        """Called when browser starts"""
        print("[ThemePlugin] Browser startup detected")
    def on_browser_shutdown(self):
        """Called when browser shuts down"""
        print("[ThemePlugin] Browser shutdown detected")


# ============================================================================
# Plugin Module Interface - Required by UnifiedPluginManager
# ============================================================================

_plugin_instance = None


def initialize_plugin():
    """
    Initialize the plugin - required by UnifiedPluginManager.
    Creates and returns a plugin instance.
    """
    global _plugin_instance
    try:
        print("[themes] initialize_plugin() called")
        _plugin_instance = ThemePlugin()
        print("[themes] Plugin instance created successfully")
        return True
    except Exception as e:
        print(f"[themes] Error creating plugin instance: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_plugin_instance():
    """Get the plugin instance"""
    return _plugin_instance


def shutdown_plugin():
    """Shutdown the plugin"""
    global _plugin_instance
    if _plugin_instance:
        _plugin_instance.shutdown()
        _plugin_instance = None
    return True


# ============================================================================
# Legacy Compatibility Layer
# For backward compatibility with code that imports theme_manager directly
# ============================================================================

def get_theme_manager():
    """Legacy compatibility - returns ThemeEngine instance"""
    try:
        from ui.core.theme_engine import get_theme_engine
        return get_theme_engine()
    except:
        return None


def open_theme_selector(parent=None):
    """Muestra el selector en el panel lateral del navegador."""
    if _plugin_instance and _plugin_instance.browser:
        br = _plugin_instance.browser
        if hasattr(br, "toggle_themes_panel"):
            br.toggle_themes_panel()
            return _plugin_instance.theme_selector_widget
    if _plugin_instance and _plugin_instance.theme_selector_widget:
        _plugin_instance.theme_selector_widget.show()
        return _plugin_instance.theme_selector_widget
    QMessageBox.information(
        parent,
        "Plugin Not Available",
        "Advanced Theme System plugin is not installed or not active.\n"
        "Please enable the plugin from the Plugins panel.",
    )
    return None


def open_theme_editor(parent=None):
    """Abre el editor en el panel lateral (no como ventana flotante)."""
    if _plugin_instance and _plugin_instance.browser:
        br = _plugin_instance.browser
        if hasattr(br, "open_themes_editor_tab"):
            br.open_themes_editor_tab()
            return getattr(_plugin_instance, "theme_editor_widget", None)
    if _plugin_instance and _plugin_instance.theme_editor_widget:
        _plugin_instance.theme_editor_widget.show()
        return _plugin_instance.theme_editor_widget
    QMessageBox.information(
        parent,
        "Plugin Not Available",
        "Advanced Theme System plugin is not installed or not active.\n"
        "Please enable the plugin from the Plugins panel.",
    )
    return None


# Export compatibility variables
THEME_PLUGIN_AVAILABLE = True
