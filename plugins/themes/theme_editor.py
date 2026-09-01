#!/usr/bin/env python3
"""
Professional Theme Editor for Tellectus
Advanced theme customization with real-time preview
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTabWidget, QGroupBox, QFormLayout,
                               QLineEdit, QSpinBox, QComboBox, QColorDialog,
                               QCheckBox, QSlider, QTextEdit, QScrollArea,
                               QSplitter, QFrame, QListWidget, QListWidgetItem,
                               QMessageBox, QFileDialog, QDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QPalette
from theme_manager import theme_manager
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

class ColorPickerWidget(QWidget):
    """Custom color picker widget"""

    color_changed = Signal(str)  # color_hex

    def __init__(self, label: str, initial_color: str = "#000000", parent=None):
        super().__init__(parent)
        self.label = label
        self.current_color = initial_color
        self.setup_ui()
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Label
        label = QLabel(self.label)
        label.setMinimumWidth(120)
        layout.addWidget(label)

        # Color button
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(40, 30)
        self.color_btn.clicked.connect(self.pick_color)
        self.update_color_button()
        layout.addWidget(self.color_btn)

        # Color input
        self.color_input = QLineEdit(self.current_color)
        self.color_input.setMaximumWidth(100)
        self.color_input.textChanged.connect(self.on_color_input_changed)
        layout.addWidget(self.color_input)

        layout.addStretch()
    def update_color_button(self):
        """Update color button appearance"""
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color};
                border: 2px solid #333;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #666;
            }}
        """)
    def pick_color(self):
        """Open color picker dialog"""
        color = QColorDialog.getColor(QColor(self.current_color), self, f"Select {self.label}")
        if color.isValid():
            self.set_color(color.name())
    def set_color(self, color_hex: str):
        """Set color programmatically"""
        self.current_color = color_hex
        self.color_input.setText(color_hex)
        self.update_color_button()
        self.color_changed.emit(color_hex)
    def on_color_input_changed(self, text: str):
        """Handle color input text change"""
        if QColor(text).isValid():
            self.current_color = text
            self.update_color_button()
            self.color_changed.emit(text)

class ThemeEditor(QWidget):
    """
    Professional theme editor with real-time preview
    """

    theme_saved = Signal(str)  # theme_id
    theme_applied = Signal(str)  # theme_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Theme Editor - Tellectus")
        self.setMinimumSize(1000, 700)
        self.current_theme_data = {}
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.apply_preview)

        self.setup_ui()
        self.load_current_theme()

        # Connect theme manager signals
        theme_manager.theme_changed.connect(self.on_theme_changed)
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Theme Editor")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Action buttons
        self.save_btn = QPushButton("💾 Save Theme")
        self.save_btn.clicked.connect(self.save_theme)
        header_layout.addWidget(self.save_btn)

        self.apply_btn = QPushButton("🎨 Apply Theme")
        self.apply_btn.clicked.connect(self.apply_theme)
        header_layout.addWidget(self.apply_btn)

        self.export_btn = QPushButton("📤 Export")
        self.export_btn.clicked.connect(self.export_theme)
        header_layout.addWidget(self.export_btn)

        self.import_btn = QPushButton("📥 Import")
        self.import_btn.clicked.connect(self.import_theme)
        header_layout.addWidget(self.import_btn)

        layout.addLayout(header_layout)

        # Main content with splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left panel - Theme settings
        self.create_settings_panel(splitter)

        # Right panel - Preview
        self.create_preview_panel(splitter)

        # Set splitter proportions
        splitter.setSizes([600, 400])
    def create_settings_panel(self, parent):
        """Create the settings panel"""
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        settings_layout.addWidget(self.tab_widget)

        # Basic info tab
        self.create_basic_info_tab()

        # Colors tab
        self.create_colors_tab()

        # Fonts tab
        self.create_fonts_tab()

        # Spacing tab
        self.create_spacing_tab()

        # Effects tab
        self.create_effects_tab()

        parent.addWidget(settings_widget)
    def create_basic_info_tab(self):
        """Create basic information tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Basic info group
        info_group = QGroupBox("Theme Information")
        info_layout = QFormLayout(info_group)

        self.name_input = QLineEdit()
        self.name_input.textChanged.connect(self.on_basic_info_changed)
        info_layout.addRow("Name:", self.name_input)

        self.description_input = QLineEdit()
        self.description_input.textChanged.connect(self.on_basic_info_changed)
        info_layout.addRow("Description:", self.description_input)

        self.version_input = QLineEdit("1.0.0")
        self.version_input.textChanged.connect(self.on_basic_info_changed)
        info_layout.addRow("Version:", self.version_input)

        self.author_input = QLineEdit("User")
        self.author_input.textChanged.connect(self.on_basic_info_changed)
        info_layout.addRow("Author:", self.author_input)

        layout.addWidget(info_group)

        # Theme selector
        theme_group = QGroupBox("Base Theme")
        theme_layout = QVBoxLayout(theme_group)

        self.base_theme_combo = QComboBox()
        self.base_theme_combo.addItems(["light", "dark"])
        self.base_theme_combo.currentTextChanged.connect(self.load_base_theme)
        theme_layout.addWidget(self.base_theme_combo)

        load_base_btn = QPushButton("Load Base Theme")
        load_base_btn.clicked.connect(self.load_base_theme)
        theme_layout.addWidget(load_base_btn)

        layout.addWidget(theme_group)

        layout.addStretch()

        self.tab_widget.addTab(widget, "Basic Info")
    def create_colors_tab(self):
        """Create colors customization tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Scroll area for color pickers
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Color pickers
        self.color_pickers = {}

        color_groups = [
            ("Primary Colors", [
                ("primary", "Primary Text"),
                ("secondary", "Secondary Text"),
                ("accent", "Accent Color")
            ]),
            ("Background Colors", [
                ("background", "Main Background"),
                ("surface", "Surface"),
                ("border", "Border")
            ]),
            ("Interactive Colors", [
                ("hover", "Hover"),
                ("selected", "Selected"),
                ("disabled", "Disabled")
            ]),
            ("Status Colors", [
                ("success", "Success"),
                ("warning", "Warning"),
                ("error", "Error")
            ])
        ]

        for group_name, colors in color_groups:
            group = QGroupBox(group_name)
            group_layout = QFormLayout(group)

            for color_key, color_label in colors:
                picker = ColorPickerWidget(color_label, "#000000")
                picker.color_changed.connect(lambda color, key=color_key: self.on_color_changed(key, color))
                self.color_pickers[color_key] = picker
                group_layout.addRow(picker)
            scroll_layout.addWidget(group)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        self.tab_widget.addTab(widget, "Colors")
    def create_fonts_tab(self):
        """Create fonts customization tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Font settings group
        font_group = QGroupBox("Font Settings")
        font_layout = QFormLayout(font_group)

        self.font_family_input = QLineEdit("Segoe UI, Arial, sans-serif")
        self.font_family_input.textChanged.connect(self.on_font_changed)
        font_layout.addRow("Font Family:", self.font_family_input)

        # Font sizes
        self.font_size_small = QSpinBox()
        self.font_size_small.setRange(6, 20)
        self.font_size_small.setValue(9)
        self.font_size_small.setSuffix("pt")
        self.font_size_small.valueChanged.connect(self.on_font_changed)
        font_layout.addRow("Small Size:", self.font_size_small)

        self.font_size_normal = QSpinBox()
        self.font_size_normal.setRange(6, 20)
        self.font_size_normal.setValue(10)
        self.font_size_normal.setSuffix("pt")
        self.font_size_normal.valueChanged.connect(self.on_font_changed)
        font_layout.addRow("Normal Size:", self.font_size_normal)

        self.font_size_large = QSpinBox()
        self.font_size_large.setRange(6, 20)
        self.font_size_large.setValue(12)
        self.font_size_large.setSuffix("pt")
        self.font_size_large.valueChanged.connect(self.on_font_changed)
        font_layout.addRow("Large Size:", self.font_size_large)

        self.font_size_title = QSpinBox()
        self.font_size_title.setRange(6, 24)
        self.font_size_title.setValue(14)
        self.font_size_title.setSuffix("pt")
        self.font_size_title.valueChanged.connect(self.on_font_changed)
        font_layout.addRow("Title Size:", self.font_size_title)

        layout.addWidget(font_group)

        # Font weights
        weight_group = QGroupBox("Font Weights")
        weight_layout = QFormLayout(weight_group)

        self.font_weight_normal = QComboBox()
        self.font_weight_normal.addItems(["normal", "bold", "100", "200", "300", "400", "500", "600", "700", "800", "900"])
        self.font_weight_normal.setCurrentText("normal")
        self.font_weight_normal.currentTextChanged.connect(self.on_font_changed)
        weight_layout.addRow("Normal Weight:", self.font_weight_normal)

        self.font_weight_bold = QComboBox()
        self.font_weight_bold.addItems(["normal", "bold", "100", "200", "300", "400", "500", "600", "700", "800", "900"])
        self.font_weight_bold.setCurrentText("bold")
        self.font_weight_bold.currentTextChanged.connect(self.on_font_changed)
        weight_layout.addRow("Bold Weight:", self.font_weight_bold)

        layout.addWidget(weight_group)

        layout.addStretch()

        self.tab_widget.addTab(widget, "Fonts")
    def create_spacing_tab(self):
        """Create spacing customization tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Spacing group
        spacing_group = QGroupBox("Spacing Settings")
        spacing_layout = QFormLayout(spacing_group)

        self.spacing_xs = QSpinBox()
        self.spacing_xs.setRange(0, 20)
        self.spacing_xs.setValue(2)
        self.spacing_xs.setSuffix("px")
        self.spacing_xs.valueChanged.connect(self.on_spacing_changed)
        spacing_layout.addRow("Extra Small:", self.spacing_xs)

        self.spacing_sm = QSpinBox()
        self.spacing_sm.setRange(0, 20)
        self.spacing_sm.setValue(4)
        self.spacing_sm.setSuffix("px")
        self.spacing_sm.valueChanged.connect(self.on_spacing_changed)
        spacing_layout.addRow("Small:", self.spacing_sm)

        self.spacing_md = QSpinBox()
        self.spacing_md.setRange(0, 30)
        self.spacing_md.setValue(8)
        self.spacing_md.setSuffix("px")
        self.spacing_md.valueChanged.connect(self.on_spacing_changed)
        spacing_layout.addRow("Medium:", self.spacing_md)

        self.spacing_lg = QSpinBox()
        self.spacing_lg.setRange(0, 40)
        self.spacing_lg.setValue(12)
        self.spacing_lg.setSuffix("px")
        self.spacing_lg.valueChanged.connect(self.on_spacing_changed)
        spacing_layout.addRow("Large:", self.spacing_lg)

        self.spacing_xl = QSpinBox()
        self.spacing_xl.setRange(0, 50)
        self.spacing_xl.setValue(16)
        self.spacing_xl.setSuffix("px")
        self.spacing_xl.valueChanged.connect(self.on_spacing_changed)
        spacing_layout.addRow("Extra Large:", self.spacing_xl)

        layout.addWidget(spacing_group)

        # Border settings
        border_group = QGroupBox("Border Settings")
        border_layout = QFormLayout(border_group)

        self.border_radius = QSpinBox()
        self.border_radius.setRange(0, 20)
        self.border_radius.setValue(4)
        self.border_radius.setSuffix("px")
        self.border_radius.valueChanged.connect(self.on_border_changed)
        border_layout.addRow("Border Radius:", self.border_radius)

        self.border_width = QSpinBox()
        self.border_width.setRange(0, 5)
        self.border_width.setValue(1)
        self.border_width.setSuffix("px")
        self.border_width.valueChanged.connect(self.on_border_changed)
        border_layout.addRow("Border Width:", self.border_width)

        self.border_style = QComboBox()
        self.border_style.addItems(["solid", "dashed", "dotted", "none"])
        self.border_style.setCurrentText("solid")
        self.border_style.currentTextChanged.connect(self.on_border_changed)
        border_layout.addRow("Border Style:", self.border_style)

        layout.addWidget(border_group)

        layout.addStretch()

        self.tab_widget.addTab(widget, "Spacing")
    def create_effects_tab(self):
        """Create effects customization tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Shadow settings
        shadow_group = QGroupBox("Shadow Effects")
        shadow_layout = QFormLayout(shadow_group)

        self.shadow_enabled = QCheckBox("Enable Shadows")
        self.shadow_enabled.toggled.connect(self.on_shadow_changed)
        shadow_layout.addRow(self.shadow_enabled)

        self.shadow_color_picker = ColorPickerWidget("Shadow Color", "rgba(0,0,0,0.1)")
        self.shadow_color_picker.color_changed.connect(self.on_shadow_changed)
        shadow_layout.addRow(self.shadow_color_picker)

        self.shadow_blur = QSpinBox()
        self.shadow_blur.setRange(0, 20)
        self.shadow_blur.setValue(4)
        self.shadow_blur.setSuffix("px")
        self.shadow_blur.valueChanged.connect(self.on_shadow_changed)
        shadow_layout.addRow("Blur:", self.shadow_blur)

        self.shadow_offset_x = QSpinBox()
        self.shadow_offset_x.setRange(-20, 20)
        self.shadow_offset_x.setValue(0)
        self.shadow_offset_x.setSuffix("px")
        self.shadow_offset_x.valueChanged.connect(self.on_shadow_changed)
        shadow_layout.addRow("Offset X:", self.shadow_offset_x)

        self.shadow_offset_y = QSpinBox()
        self.shadow_offset_y.setRange(-20, 20)
        self.shadow_offset_y.setValue(2)
        self.shadow_offset_y.setSuffix("px")
        self.shadow_offset_y.valueChanged.connect(self.on_shadow_changed)
        shadow_layout.addRow("Offset Y:", self.shadow_offset_y)

        layout.addWidget(shadow_group)

        layout.addStretch()

        self.tab_widget.addTab(widget, "Effects")
    def create_preview_panel(self, parent):
        """Create the preview panel"""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        # Preview title
        preview_title = QLabel("Live Preview")
        preview_title.setFont(QFont("Arial", 14, QFont.Bold))
        preview_layout.addWidget(preview_title)

        # Preview area
        self.preview_area = QScrollArea()
        self.preview_area.setWidgetResizable(True)
        self.preview_area.setMinimumHeight(400)

        # Create preview content
        self.create_preview_content()

        preview_layout.addWidget(self.preview_area)

        parent.addWidget(preview_widget)
    def create_preview_content(self):
        """Create preview content"""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        # Sample buttons
        button_layout = QHBoxLayout()

        sample_btn1 = QPushButton("Sample Button 1")
        sample_btn1.setToolTip("This is a sample button")
        button_layout.addWidget(sample_btn1)

        sample_btn2 = QPushButton("Sample Button 2")
        sample_btn2.setToolTip("Another sample button")
        button_layout.addWidget(sample_btn2)

        preview_layout.addLayout(button_layout)

        # Sample input
        sample_input = QLineEdit("Sample text input")
        sample_input.setPlaceholderText("Enter some text...")
        preview_layout.addWidget(sample_input)

        # Sample group
        sample_group = QGroupBox("Sample Group")
        group_layout = QVBoxLayout(sample_group)

        group_layout.addWidget(QLabel("This is a sample group with some content"))

        sample_checkbox = QCheckBox("Sample checkbox")
        group_layout.addWidget(sample_checkbox)

        sample_combo = QComboBox()
        sample_combo.addItems(["Option 1", "Option 2", "Option 3"])
        group_layout.addWidget(sample_combo)

        preview_layout.addWidget(sample_group)

        # Sample list
        sample_list = QListWidget()
        sample_list.addItems(["Item 1", "Item 2", "Item 3", "Item 4"])
        sample_list.setMaximumHeight(100)
        preview_layout.addWidget(sample_list)

        self.preview_area.setWidget(preview_widget)
    def load_current_theme(self):
        """Load current theme data"""
        self.current_theme_data = theme_manager.get_current_theme_data()
        self.populate_editor()
    def populate_editor(self):
        """Populate editor with current theme data"""
        # Basic info
        self.name_input.setText(self.current_theme_data.get("name", ""))
        self.description_input.setText(self.current_theme_data.get("description", ""))
        self.version_input.setText(self.current_theme_data.get("version", "1.0.0"))
        self.author_input.setText(self.current_theme_data.get("author", ""))

        # Colors
        colors = self.current_theme_data.get("colors", {})
        for color_key, picker in self.color_pickers.items():
            color_value = colors.get(color_key, "#000000")
            picker.set_color(color_value)
        # Fonts
        fonts = self.current_theme_data.get("fonts", {})
        self.font_family_input.setText(fonts.get("family", "Arial, sans-serif"))

        # Parse font sizes
        for size_key, spinbox in [
            ("size_small", self.font_size_small),
            ("size_normal", self.font_size_normal),
            ("size_large", self.font_size_large),
            ("size_title", self.font_size_title)
        ]:
            size_value = fonts.get(size_key, "10pt")
            if size_value.endswith("pt"):
                size_value = int(size_value[:-2])
                spinbox.setValue(size_value)
        # Spacing
        spacing = self.current_theme_data.get("spacing", {})
        for spacing_key, spinbox in [
            ("xs", self.spacing_xs),
            ("sm", self.spacing_sm),
            ("md", self.spacing_md),
            ("lg", self.spacing_lg),
            ("xl", self.spacing_xl)
        ]:
            spacing_value = spacing.get(spacing_key, "4px")
            if spacing_value.endswith("px"):
                spacing_value = int(spacing_value[:-2])
                spinbox.setValue(spacing_value)
        # Borders
        borders = self.current_theme_data.get("borders", {})
        self.border_radius.setValue(int(borders.get("radius", "4px").replace("px", "")))
        self.border_width.setValue(int(borders.get("width", "1px").replace("px", "")))
        self.border_style.setCurrentText(borders.get("style", "solid"))

        # Shadows
        shadows = self.current_theme_data.get("shadows", {})
        self.shadow_enabled.setChecked(shadows.get("enabled", False))
        self.shadow_color_picker.set_color(shadows.get("color", "rgba(0,0,0,0.1)"))
        self.shadow_blur.setValue(int(shadows.get("blur", "4px").replace("px", "")))

        # Parse shadow offset
        offset = shadows.get("offset", "0px 2px").split()
        if len(offset) >= 2:
            self.shadow_offset_x.setValue(int(offset[0].replace("px", "")))
            self.shadow_offset_y.setValue(int(offset[1].replace("px", "")))
    def on_basic_info_changed(self):
        """Handle basic info changes"""
        self.schedule_preview_update()
    def on_color_changed(self, color_key: str, color_value: str):
        """Handle color changes"""
        if "colors" not in self.current_theme_data:
            self.current_theme_data["colors"] = {}
        self.current_theme_data["colors"][color_key] = color_value
        self.schedule_preview_update()
    def on_font_changed(self):
        """Handle font changes"""
        if "fonts" not in self.current_theme_data:
            self.current_theme_data["fonts"] = {}
        self.current_theme_data["fonts"]["family"] = self.font_family_input.text()
        self.current_theme_data["fonts"]["size_small"] = f"{self.font_size_small.value()}pt"
        self.current_theme_data["fonts"]["size_normal"] = f"{self.font_size_normal.value()}pt"
        self.current_theme_data["fonts"]["size_large"] = f"{self.font_size_large.value()}pt"
        self.current_theme_data["fonts"]["size_title"] = f"{self.font_size_title.value()}pt"
        self.current_theme_data["fonts"]["weight_normal"] = self.font_weight_normal.currentText()
        self.current_theme_data["fonts"]["weight_bold"] = self.font_weight_bold.currentText()

        self.schedule_preview_update()
    def on_spacing_changed(self):
        """Handle spacing changes"""
        if "spacing" not in self.current_theme_data:
            self.current_theme_data["spacing"] = {}
        self.current_theme_data["spacing"]["xs"] = f"{self.spacing_xs.value()}px"
        self.current_theme_data["spacing"]["sm"] = f"{self.spacing_sm.value()}px"
        self.current_theme_data["spacing"]["md"] = f"{self.spacing_md.value()}px"
        self.current_theme_data["spacing"]["lg"] = f"{self.spacing_lg.value()}px"
        self.current_theme_data["spacing"]["xl"] = f"{self.spacing_xl.value()}px"

        self.schedule_preview_update()
    def on_border_changed(self):
        """Handle border changes"""
        if "borders" not in self.current_theme_data:
            self.current_theme_data["borders"] = {}
        self.current_theme_data["borders"]["radius"] = f"{self.border_radius.value()}px"
        self.current_theme_data["borders"]["width"] = f"{self.border_width.value()}px"
        self.current_theme_data["borders"]["style"] = self.border_style.currentText()

        self.schedule_preview_update()
    def on_shadow_changed(self):
        """Handle shadow changes"""
        if "shadows" not in self.current_theme_data:
            self.current_theme_data["shadows"] = {}
        self.current_theme_data["shadows"]["enabled"] = self.shadow_enabled.isChecked()
        self.current_theme_data["shadows"]["color"] = self.shadow_color_picker.current_color
        self.current_theme_data["shadows"]["blur"] = f"{self.shadow_blur.value()}px"
        self.current_theme_data["shadows"]["offset"] = f"{self.shadow_offset_x.value()}px {self.shadow_offset_y.value()}px"

        self.schedule_preview_update()
    def schedule_preview_update(self):
        """Schedule a preview update"""
        self.preview_timer.start(100)  # 100ms delay
    def apply_preview(self):
        """Apply current theme as preview"""
        # Create a temporary theme for preview
        preview_theme = self.current_theme_data.copy()
        preview_theme["id"] = "preview"
        preview_theme["name"] = "Preview Theme"

        # Apply to preview area
        self.apply_theme_to_widget(self.preview_area, preview_theme)
    def apply_theme_to_widget(self, widget: QWidget, theme_data: Dict[str, Any]):
        """Apply theme to a specific widget"""
        colors = theme_data.get("colors", {})
        fonts = theme_data.get("fonts", {})
        spacing = theme_data.get("spacing", {})
        borders = theme_data.get("borders", {})
        shadows = theme_data.get("shadows", {})

        # Generate CSS
        shadow_css = ""
        if shadows.get("enabled", False):
            shadow_css = ""  # box-shadow no soportado en Qt QSS
        css = f"""
        QWidget {{
            background-color: {colors.get('background', '#ffffff')};
            color: {colors.get('text_primary', '#000000')};
            font-family: {fonts.get('family', 'Arial, sans-serif')};
            font-size: {fonts.get('size_normal', '10pt')};
        }}

        QPushButton {{
            background-color: {colors.get('surface', '#ffffff')};
            color: {colors.get('text_primary', '#000000')};
            border: {borders.get('width', '1px')} {borders.get('style', 'solid')} {colors.get('border', '#cccccc')};
            border-radius: {borders.get('radius', '4px')};
            padding: {spacing.get('md', '8px')} {spacing.get('lg', '12px')};
            {shadow_css}
        }}

        QPushButton:hover {{
            background-color: {colors.get('hover', '#f0f0f0')};
        }}

        QLineEdit {{
            background-color: {colors.get('surface', '#ffffff')};
            color: {colors.get('text_primary', '#000000')};
            border: {borders.get('width', '1px')} {borders.get('style', 'solid')} {colors.get('border', '#cccccc')};
            border-radius: {borders.get('radius', '4px')};
            padding: {spacing.get('sm', '4px')} {spacing.get('md', '8px')};
        }}

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

        QListWidget {{
            background-color: {colors.get('surface', '#ffffff')};
            color: {colors.get('text_primary', '#000000')};
            border: {borders.get('width', '1px')} {borders.get('style', 'solid')} {colors.get('border', '#cccccc')};
            selection-background-color: {colors.get('selected', '#cce8ff')};
        }}
        """

        widget.setStyleSheet(css)
    def load_base_theme(self):
        """Load base theme"""
        base_theme = self.base_theme_combo.currentText()
        if base_theme in theme_manager.themes:
            self.current_theme_data = theme_manager.themes[base_theme].copy()
            self.populate_editor()
            self.schedule_preview_update()
    def save_theme(self):
        """Save current theme"""
        if not self.current_theme_data.get("name"):
            QMessageBox.warning(self, "Error", "Please enter a theme name")
            return
        # Generate theme ID
        theme_id = self.current_theme_data.get("name", "custom_theme").lower().replace(" ", "_")
        self.current_theme_data["id"] = theme_id

        # Save theme
        if theme_manager.create_custom_theme(self.current_theme_data):
            QMessageBox.information(self, "Success", f"Theme '{theme_id}' saved successfully")
            self.theme_saved.emit(theme_id)
        else:
            QMessageBox.warning(self, "Error", "Failed to save theme")
    def apply_theme(self):
        """Apply current theme"""
        if not self.current_theme_data.get("name"):
            QMessageBox.warning(self, "Error", "Please enter a theme name")
            return
        # Generate theme ID
        theme_id = self.current_theme_data.get("name", "custom_theme").lower().replace(" ", "_")
        self.current_theme_data["id"] = theme_id

        # Save and apply
        if theme_manager.create_custom_theme(self.current_theme_data):
            if theme_manager.set_theme(theme_id):
                QMessageBox.information(self, "Success", f"Theme '{theme_id}' applied successfully")
                self.theme_applied.emit(theme_id)
            else:
                QMessageBox.warning(self, "Error", "Failed to apply theme")
        else:
            QMessageBox.warning(self, "Error", "Failed to save theme")
    def export_theme(self):
        """Export current theme"""
        if not self.current_theme_data.get("name"):
            QMessageBox.warning(self, "Error", "Please enter a theme name")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Theme", f"{self.current_theme_data.get('name', 'theme')}.json",
            "JSON Files (*.json)"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.current_theme_data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "Success", f"Theme exported to {filename}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to export theme: {e}")
    def import_theme(self):
        """Import theme from file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Theme", "", "JSON Files (*.json)"
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    theme_data = json.load(f)
                self.current_theme_data = theme_data
                self.populate_editor()
                self.schedule_preview_update()

                QMessageBox.information(self, "Success", "Theme imported successfully")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to import theme: {e}")
    def on_theme_changed(self, theme_id: str):
        """Handle theme changes from manager"""
        if theme_id != "preview":
            self.load_current_theme()

def open_theme_editor(parent=None):
    """Open the theme editor"""
    editor = ThemeEditor(parent)
    editor.show()
    return editor

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    editor = ThemeEditor()
    editor.show()
    sys.exit(app.exec())
