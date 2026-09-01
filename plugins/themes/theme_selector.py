#!/usr/bin/env python3
"""
Simple Theme Selector for Tellectus
Quick theme selection and management
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QListWidget, QListWidgetItem,
                               QGroupBox, QMessageBox, QDialog, QDialogButtonBox,
                               QComboBox, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from theme_manager import theme_manager
from theme_editor import open_theme_editor

class ThemeSelector(QDialog):
    """
    Simple theme selector dialog
    """

    theme_selected = Signal(str)  # theme_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Theme - Tellectus")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        self.setup_ui()
        self.load_themes()

        # Connect theme manager
        theme_manager.theme_changed.connect(self.on_theme_changed)
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("Theme Selector")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Advanced editor button
        editor_btn = QPushButton("🎨 Advanced Editor")
        editor_btn.clicked.connect(self.open_advanced_editor)
        header_layout.addWidget(editor_btn)

        layout.addLayout(header_layout)

        # Current theme info
        current_group = QGroupBox("Current Theme")
        current_layout = QVBoxLayout(current_group)

        self.current_theme_label = QLabel("Loading...")
        self.current_theme_label.setFont(QFont("Arial", 12, QFont.Bold))
        current_layout.addWidget(self.current_theme_label)

        layout.addWidget(current_group)

        # Available themes
        themes_group = QGroupBox("Available Themes")
        themes_layout = QVBoxLayout(themes_group)

        self.themes_list = QListWidget()
        self.themes_list.itemDoubleClicked.connect(self.apply_selected_theme)
        self.themes_list.itemClicked.connect(self.show_theme_info)
        themes_layout.addWidget(self.themes_list)

        # Theme actions
        actions_layout = QHBoxLayout()

        self.apply_btn = QPushButton("Apply Theme")
        self.apply_btn.clicked.connect(self.apply_selected_theme)
        actions_layout.addWidget(self.apply_btn)

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self.preview_theme)
        actions_layout.addWidget(self.preview_btn)

        actions_layout.addStretch()

        themes_layout.addLayout(actions_layout)
        layout.addWidget(themes_group)

        # Theme info
        info_group = QGroupBox("Theme Information")
        info_layout = QVBoxLayout(info_group)

        self.theme_info = QLabel("Select a theme to view information")
        self.theme_info.setWordWrap(True)
        self.theme_info.setMinimumHeight(80)
        info_layout.addWidget(self.theme_info)

        layout.addWidget(info_group)

        # Import/Export buttons
        import_export_layout = QHBoxLayout()

        import_btn = QPushButton("📥 Import Theme")
        import_btn.clicked.connect(self.import_theme)
        import_export_layout.addWidget(import_btn)

        export_btn = QPushButton("📤 Export Theme")
        export_btn.clicked.connect(self.export_theme)
        import_export_layout.addWidget(export_btn)

        import_export_layout.addStretch()

        layout.addLayout(import_export_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    def load_themes(self):
        """Load available themes"""
        self.themes_list.clear()

        themes = theme_manager.get_available_themes()
        current_theme = theme_manager.current_theme

        for theme in themes:
            item = QListWidgetItem()
            item.setText(f"{theme['name']} ({theme['id']})")
            item.setData(Qt.UserRole, theme['id'])

            # Highlight current theme
            if theme['id'] == current_theme:
                item.setBackground(QColor(200, 255, 200))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.themes_list.addItem(item)
        # Update current theme label
        current_theme_data = next((t for t in themes if t['id'] == current_theme), None)
        if current_theme_data:
            self.current_theme_label.setText(f"{current_theme_data['name']} ({current_theme})")
        # Select first item if available
        if self.themes_list.count() > 0:
            self.themes_list.setCurrentRow(0)
            self.show_theme_info()
    def show_theme_info(self):
        """Show information about selected theme"""
        current_item = self.themes_list.currentItem()
        if not current_item:
            return
        theme_id = current_item.data(Qt.UserRole)
        if theme_id not in theme_manager.themes:
            return
        theme_data = theme_manager.themes[theme_id]

        info_text = f"""
<b>Name:</b> {theme_data.get('name', theme_id)}<br>
<b>Description:</b> {theme_data.get('description', 'No description')}<br>
<b>Version:</b> {theme_data.get('version', '1.0.0')}<br>
<b>Author:</b> {theme_data.get('author', 'Unknown')}<br>
<br>
<b>Colors:</b> {len(theme_data.get('colors', {}))} defined<br>
<b>Fonts:</b> {len(theme_data.get('fonts', {}))} configured<br>
<b>Effects:</b> {'Yes' if theme_data.get('shadows', {}).get('enabled', False) else 'No'}
        """

        self.theme_info.setText(info_text.strip())
    def apply_selected_theme(self):
        """Apply selected theme"""
        current_item = self.themes_list.currentItem()
        if not current_item:
            return
        theme_id = current_item.data(Qt.UserRole)
        if theme_manager.set_theme(theme_id):
            QMessageBox.information(self, "Success", f"Theme '{theme_id}' applied successfully")
            self.theme_selected.emit(theme_id)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", f"Could not apply theme '{theme_id}'")
    def preview_theme(self):
        """Preview selected theme"""
        current_item = self.themes_list.currentItem()
        if not current_item:
            return
        theme_id = current_item.data(Qt.UserRole)

        # Apply theme temporarily
        if theme_manager.set_theme(theme_id):
            QMessageBox.information(self, "Preview", f"Previewing theme '{theme_id}'. Click 'Apply Theme' to make it permanent.")
        else:
            QMessageBox.warning(self, "Error", f"Could not preview theme '{theme_id}'")
    def open_advanced_editor(self):
        """Open advanced theme editor"""
        try:
            editor = open_theme_editor(self)
            editor.theme_applied.connect(self.on_theme_applied)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open theme editor: {e}")
    def on_theme_applied(self, theme_id: str):
        """Handle theme applied from editor"""
        self.load_themes()
        QMessageBox.information(self, "Success", f"Theme '{theme_id}' applied successfully")
        self.theme_selected.emit(theme_id)
    def import_theme(self):
        """Import theme from file"""
        from PySide6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Theme", "", "JSON Files (*.json)"
        )

        if filename:
            if theme_manager.import_theme(filename):
                QMessageBox.information(self, "Success", "Theme imported successfully")
                self.load_themes()
            else:
                QMessageBox.warning(self, "Error", "Could not import theme")
    def export_theme(self):
        """Export selected theme"""
        current_item = self.themes_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a theme to export")
            return
        theme_id = current_item.data(Qt.UserRole)
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Theme", f"{theme_id}.json", "JSON Files (*.json)"
        )

        if filename:
            if theme_manager.export_theme(theme_id, filename):
                QMessageBox.information(self, "Success", f"Theme exported to {filename}")
            else:
                QMessageBox.warning(self, "Error", "Could not export theme")
    def on_theme_changed(self, theme_id: str):
        """Handle theme changes from manager"""
        self.load_themes()

def open_theme_selector(parent=None):
    """Open the theme selector"""
    selector = ThemeSelector(parent)
    return selector

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    selector = ThemeSelector()
    selector.show()
    sys.exit(app.exec())
