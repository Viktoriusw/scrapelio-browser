#!/usr/bin/env python3
"""
Premium Scraping Panel with Authentication Integration
Example of how to integrate premium features with the authentication system
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QGroupBox, QMessageBox, QProgressBar, QComboBox,
    QLineEdit, QCheckBox, QSpinBox, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont, QIcon
from premium_decorators import requires_premium, premium_feature, PremiumMixin
import json
import os
import time


class PremiumScrapingPanel(QWidget, PremiumMixin):
    """Premium scraping panel with authentication integration"""
    
    def __init__(self, plugin_validator=None, parent=None):
        super().__init__(parent)
        self.plugin_id = "scraping"
        self.plugin_validator = plugin_validator
        self.setup_ui()
        self.setup_premium_features()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("🕷️ Scraping Avanzado")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Status indicator
        self.status_label = QLabel("🔴 Sin licencia")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        header_layout.addWidget(self.status_label)
        
        layout.addLayout(header_layout)
        
        # Main content area
        content_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Controls
        left_panel = self.create_controls_panel()
        content_splitter.addWidget(left_panel)
        
        # Right panel - Results
        right_panel = self.create_results_panel()
        content_splitter.addWidget(right_panel)
        
        # Set splitter proportions
        content_splitter.setSizes([300, 500])
        
        layout.addWidget(content_splitter)
        
        # Update premium UI
        self.update_premium_ui(self.plugin_id)
    
    def create_controls_panel(self):
        """Create the controls panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # URL Input
        url_group = QGroupBox("URL a Scrapear")
        url_layout = QVBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://ejemplo.com")
        url_layout.addWidget(self.url_input)
        
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)
        
        # Scraping Options
        options_group = QGroupBox("Opciones de Scraping")
        options_layout = QVBoxLayout()
        
        # Basic options (always available)
        self.extract_links_checkbox = QCheckBox("Extraer enlaces")
        self.extract_links_checkbox.setChecked(True)
        options_layout.addWidget(self.extract_links_checkbox)
        
        self.extract_text_checkbox = QCheckBox("Extraer texto")
        self.extract_text_checkbox.setChecked(True)
        options_layout.addWidget(self.extract_text_checkbox)
        
        # Premium options
        self.advanced_scraping_checkbox = QCheckBox("Scraping Avanzado")
        self.advanced_scraping_checkbox.setToolTip("Función premium - Requiere suscripción")
        options_layout.addWidget(self.advanced_scraping_checkbox)
        
        self.javascript_handling_checkbox = QCheckBox("Manejo de JavaScript")
        self.javascript_handling_checkbox.setToolTip("Función premium - Requiere suscripción")
        options_layout.addWidget(self.javascript_handling_checkbox)
        
        self.scheduled_scraping_checkbox = QCheckBox("Scraping Programado")
        self.scheduled_scraping_checkbox.setToolTip("Función premium - Requiere suscripción")
        options_layout.addWidget(self.scheduled_scraping_checkbox)
        
        self.proxy_rotation_checkbox = QCheckBox("Rotación de Proxies")
        self.proxy_rotation_checkbox.setToolTip("Función premium - Requiere suscripción")
        options_layout.addWidget(self.proxy_rotation_checkbox)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Export Options
        export_group = QGroupBox("Opciones de Exportación")
        export_layout = QVBoxLayout()
        
        self.export_format = QComboBox()
        self.export_format.addItems(["JSON", "CSV", "Excel"])
        export_layout.addWidget(QLabel("Formato:"))
        export_layout.addWidget(self.export_format)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        # Action Buttons
        button_layout = QVBoxLayout()
        
        self.start_scraping_button = QPushButton("Iniciar Scraping")
        self.start_scraping_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.start_scraping_button.clicked.connect(self.start_scraping)
        button_layout.addWidget(self.start_scraping_button)
        
        self.export_button = QPushButton("Exportar Datos")
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.export_button.clicked.connect(self.export_data)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        return panel
    
    def create_results_panel(self):
        """Create the results panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Results table
        results_group = QGroupBox("Resultados")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Tipo", "Contenido", "URL"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        results_layout.addWidget(self.results_table)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Log area
        log_group = QGroupBox("Log de Actividad")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        return panel
    
    def setup_premium_features(self):
        """Setup premium feature tracking"""
        self._premium_features = {
            'advanced_scraping_checkbox': self.advanced_scraping_checkbox,
            'javascript_handling_checkbox': self.javascript_handling_checkbox,
            'scheduled_scraping_checkbox': self.scheduled_scraping_checkbox,
            'proxy_rotation_checkbox': self.proxy_rotation_checkbox,
            'export_button': self.export_button
        }
    
    def update_premium_ui(self, plugin_id):
        """Update UI based on premium access"""
        super().update_premium_ui(plugin_id)
        
        if not self.plugin_validator:
            return
        
        access_info = self.plugin_validator.get_plugin_access(plugin_id)
        
        # Update status label
        if access_info.access_level.value == "premium":
            self.status_label.setText("🟢 Premium Activo")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        elif access_info.access_level.value == "trial":
            self.status_label.setText(f"🟡 Prueba ({access_info.trial_remaining}d)")
            self.status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
        else:
            self.status_label.setText("🔴 Sin licencia")
            self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
    
    @requires_premium("scraping", "advanced_scraping")
    def start_advanced_scraping(self):
        """Start advanced scraping (premium feature)"""
        self.log_message("Iniciando scraping avanzado...")
        # Implementation for advanced scraping
        pass
    
    @premium_feature("scraping", "javascript_handling", fallback_func=None)
    def handle_javascript(self):
        """Handle JavaScript rendering (premium feature)"""
        self.log_message("Manejando JavaScript...")
        # Implementation for JavaScript handling
        pass
    
    def start_scraping(self):
        """Start scraping process"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Por favor, introduce una URL válida.")
            return
        
        # Check for premium features
        if self.advanced_scraping_checkbox.isChecked():
            if not self.request_premium_access("scraping", "advanced_scraping"):
                return
        
        if self.javascript_handling_checkbox.isChecked():
            if not self.request_premium_access("scraping", "javascript_handling"):
                return
        
        if self.scheduled_scraping_checkbox.isChecked():
            if not self.request_premium_access("scraping", "scheduled_scraping"):
                return
        
        if self.proxy_rotation_checkbox.isChecked():
            if not self.request_premium_access("scraping", "proxy_rotation"):
                return
        
        # Start scraping
        self.log_message(f"Iniciando scraping de: {url}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Simulate scraping process
        self.simulate_scraping(url)
    
    def simulate_scraping(self, url):
        """Simulate scraping process"""
        # This would be replaced with actual scraping logic
        import random
        
        # Simulate progress
        for i in range(101):
            self.progress_bar.setValue(i)
            QApplication.processEvents()
            time.sleep(0.01)
        
        # Add sample results
        self.add_result("Enlace", "https://ejemplo.com/pagina1", url)
        self.add_result("Texto", "Contenido de ejemplo", url)
        self.add_result("Enlace", "https://ejemplo.com/pagina2", url)
        
        self.progress_bar.setVisible(False)
        self.export_button.setEnabled(True)
        self.log_message("Scraping completado exitosamente")
    
    def add_result(self, result_type, content, source_url):
        """Add result to the table"""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        self.results_table.setItem(row, 0, QTableWidgetItem(result_type))
        self.results_table.setItem(row, 1, QTableWidgetItem(content))
        self.results_table.setItem(row, 2, QTableWidgetItem(source_url))
    
    def export_data(self):
        """Export scraped data"""
        if self.results_table.rowCount() == 0:
            QMessageBox.warning(self, "Error", "No hay datos para exportar.")
            return
        
        # Check premium access for Excel export
        if self.export_format.currentText() == "Excel":
            if not self.request_premium_access("scraping", "excel_export"):
                return
        
        # Get export format
        format_type = self.export_format.currentText().lower()
        
        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            f"Guardar datos como {format_type.upper()}",
            f"scraped_data.{format_type}",
            f"{format_type.upper()} files (*.{format_type})"
        )
        
        if file_path:
            self.export_to_file(file_path, format_type)
    
    def export_to_file(self, file_path, format_type):
        """Export data to file"""
        try:
            if format_type == "json":
                self.export_to_json(file_path)
            elif format_type == "csv":
                self.export_to_csv(file_path)
            elif format_type == "excel":
                self.export_to_excel(file_path)
            
            self.log_message(f"Datos exportados a: {file_path}")
            QMessageBox.information(self, "Éxito", f"Datos exportados exitosamente a {file_path}")
            
        except Exception as e:
            self.log_message(f"Error al exportar: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error al exportar datos: {str(e)}")
    
    def export_to_json(self, file_path):
        """Export to JSON format"""
        data = []
        for row in range(self.results_table.rowCount()):
            item = {
                "tipo": self.results_table.item(row, 0).text(),
                "contenido": self.results_table.item(row, 1).text(),
                "url": self.results_table.item(row, 2).text()
            }
            data.append(item)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def export_to_csv(self, file_path):
        """Export to CSV format"""
        import csv
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Tipo", "Contenido", "URL"])
            
            for row in range(self.results_table.rowCount()):
                writer.writerow([
                    self.results_table.item(row, 0).text(),
                    self.results_table.item(row, 1).text(),
                    self.results_table.item(row, 2).text()
                ])
    
    def export_to_excel(self, file_path):
        """Export to Excel format (premium feature)"""
        try:
            import pandas as pd
            
            data = []
            for row in range(self.results_table.rowCount()):
                data.append([
                    self.results_table.item(row, 0).text(),
                    self.results_table.item(row, 1).text(),
                    self.results_table.item(row, 2).text()
                ])
            
            df = pd.DataFrame(data, columns=["Tipo", "Contenido", "URL"])
            df.to_excel(file_path, index=False)
            
        except ImportError:
            raise Exception("pandas no está instalado. Instala pandas para exportar a Excel.")
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def set_plugin_validator(self, validator):
        """Set the plugin validator"""
        super().set_plugin_validator(validator)
        self.update_premium_ui(self.plugin_id)
