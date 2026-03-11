#!/usr/bin/env python3

"""

Base Panel - Base class for reusable tabbed panels

Eliminates code duplication in setup_ui of different panels

"""



from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QHBoxLayout, 

                               QGroupBox, QPushButton, QLabel)

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
    
    def _apply_base_theme(self):
        """
        Apply base theme to the panel
        Child classes can override this for custom theming
        """
        if not THEME_AVAILABLE:
            return
        
        theme = self.current_theme
        
        # Get theme colors
        bg = get_color("background", theme)
        surface = get_color("surface", theme)
        primary = get_color("primary", theme)
        border = get_color("border", theme)
        
        # Apply basic theme to panel
        if theme == "dark":
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {bg};
                    color: {primary};
                }}
                QTabWidget::pane {{
                    border: 1px solid {border};
                    background-color: {bg};
                }}
                QGroupBox {{
                    background-color: {surface};
                    border: 1px solid {border};
                    border-radius: 4px;
                    margin-top: 8px;
                    padding-top: 8px;
                }}
                QGroupBox::title {{
                    color: {primary};
                }}
            """)
    
    def _on_theme_changed(self, theme_name):
        """
        Handle theme change signal
        Child classes can override for additional theming
        """
        self.current_theme = theme_name
        self._apply_base_theme()

