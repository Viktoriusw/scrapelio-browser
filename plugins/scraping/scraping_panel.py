#!/usr/bin/env python3
"""
Panel de Scraping Funcional - Análisis real de HTML y selección de elementos
"""

import sys
import json
import time
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QTextEdit, QPushButton, QLabel, QSpinBox, 
                               QLineEdit, QComboBox, QListWidget, QListWidgetItem,
                               QCheckBox, QGroupBox, QScrollArea, QFrame, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal as pyqtSignal
from PySide6.QtGui import QFont, QColor
from base_panel import BasePanel
from premium_decorators import requires_premium

class ScrapingPanel(BasePanel):
    def __init__(self, scraping_integration, parent=None, plugin_validator=None):
        self.scraping_integration = scraping_integration
        self.browser_tab = None  # Inicializar referencia al navegador
        self.plugin_validator = plugin_validator
        super().__init__(parent)  # Esto llamará a setup_ui() automáticamente
    
    def get_tab_definitions(self):
        """Define los tabs para el panel de scraping"""
        return [
            (self.create_analysis_tab, "📊 Real Analysis"),
            (self.create_selection_tab, "🎯 Element Selection"),
            (self.create_pattern_detection_tab, "🔍 Pattern Detection"),
            (self.create_extraction_tab, "📥 Data Extraction"),
            (self.create_export_tab, "📤 Export Data"),
            (self.create_discovery_tab, "🔍 URL Discovery"),
            (self.create_status_tab, "ℹ️ System Status"),
        ]
    
    def create_analysis_tab(self):
        """Real HTML analysis with full functionality"""
        def build_content(widget, layout):
            # Controls usando factory method
            controls_layout = self.create_button_row([
                ("🔍 Analyze Current Page", self.run_analysis, "Analyze the HTML of the current page"),
                ("🔄 Update HTML", self.refresh_html, "Update HTML content"),
                ("🔄 Refresh All", self.refresh_all_data, "Update all data from browser")
            ])
            layout.addLayout(controls_layout)
            
            # Analysis results
            self.analysis_text = QTextEdit()
            self.analysis_text.setPlaceholderText("Analysis results will appear here...")
            layout.addWidget(self.analysis_text)
        
        return self.create_basic_tab(build_content, "Real HTML analysis with full functionality")
    
    def create_selection_tab(self):
        """Interactive element selection"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        self.load_elements_btn = QPushButton("📋 Cargar Elementos")
        self.load_elements_btn.clicked.connect(self.load_selectable_elements)
        controls_layout.addWidget(self.load_elements_btn)
        
        self.clear_selection_btn = QPushButton("🗑️ Clear Selection")
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        controls_layout.addWidget(self.clear_selection_btn)
        
        self.select_all_btn = QPushButton("✅ Seleccionar Todo")
        self.select_all_btn.clicked.connect(self.select_all_elements)
        controls_layout.addWidget(self.select_all_btn)
        
        # Interactive selection controls
        self.enable_selection_btn = QPushButton("🎯 Activate Interactive Selection")
        self.enable_selection_btn.clicked.connect(self.toggle_interactive_selection)
        controls_layout.addWidget(self.enable_selection_btn)
        
        # Selector input for manual selection
        self.manual_selector_input = QLineEdit()
        self.manual_selector_input.setPlaceholderText("CSS selector (ej: h1, .class, #id)")
        self.manual_selector_input.setFixedHeight(32)  # Altura consistente
        if hasattr(self.manual_selector_input, "setClearButtonEnabled"):
            self.manual_selector_input.setClearButtonEnabled(True)
        controls_layout.addWidget(QLabel("Selector:"))
        controls_layout.addWidget(self.manual_selector_input)
        
        self.add_by_selector_btn = QPushButton("➕ Add by Selector")
        self.add_by_selector_btn.clicked.connect(self.add_elements_by_selector)
        controls_layout.addWidget(self.add_by_selector_btn)
        
        # Sync button for JavaScript selected elements
        self.sync_js_elements_btn = QPushButton("🔄 Sincronizar JS")
        self.sync_js_elements_btn.clicked.connect(self.sync_javascript_elements)
        controls_layout.addWidget(self.sync_js_elements_btn)
        
        # Diagnostic button
        self.diagnostic_btn = QPushButton("🔧 Diagnostics")
        self.diagnostic_btn.clicked.connect(self.run_diagnostics)
        controls_layout.addWidget(self.diagnostic_btn)
        
        # Test extraction button
        self.test_extraction_btn = QPushButton("🧪 Test Extraction")
        self.test_extraction_btn.clicked.connect(self.test_html_extraction)
        controls_layout.addWidget(self.test_extraction_btn)
        
        # Debug JavaScript state button
        self.debug_js_btn = QPushButton("🐛 Debug JS")
        self.debug_js_btn.clicked.connect(self.debug_javascript_state)
        controls_layout.addWidget(self.debug_js_btn)
        
        layout.addLayout(controls_layout)
        
        # Elements list
        elements_group = QGroupBox("Elementos Disponibles")
        elements_layout = QVBoxLayout()
        
        # Filter controls
        filter_layout = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Headers", "Links", "Buttons", "Paragraphs", "Images", "Highlighted Text"])
        self.filter_combo.currentTextChanged.connect(self.filter_elements)
        filter_layout.addWidget(QLabel("Filtrar por tipo:"))
        filter_layout.addWidget(self.filter_combo)
        
        self.refresh_elements_btn = QPushButton("🔄 Actualizar")
        self.refresh_elements_btn.clicked.connect(self.load_selectable_elements)
        filter_layout.addWidget(self.refresh_elements_btn)
        
        elements_layout.addLayout(filter_layout)
        
        self.elements_list = QListWidget()
        self.elements_list.setSelectionMode(QListWidget.MultiSelection)
        self.elements_list.itemDoubleClicked.connect(self.add_single_element)
        elements_layout.addWidget(self.elements_list)
        
        elements_group.setLayout(elements_layout)
        layout.addWidget(elements_group)
        
        # Selected elements
        selected_group = QGroupBox("Elementos Seleccionados")
        selected_layout = QVBoxLayout()
        
        self.selected_list = QListWidget()
        selected_layout.addWidget(self.selected_list)
        
        selected_group.setLayout(selected_layout)
        layout.addWidget(selected_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_extraction_tab(self):
        """Data extraction with custom selectors"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        self.extract_btn = QPushButton("📥 Extraer Datos")
        self.extract_btn.clicked.connect(self.run_extraction)
        controls_layout.addWidget(self.extract_btn)
        
        # Selectors input
        self.selectors_input = QLineEdit()
        self.selectors_input.setPlaceholderText("h1, p, a, table, img (separados por comas)")
        self.selectors_input.setFixedHeight(32)  # Altura consistente
        if hasattr(self.selectors_input, "setClearButtonEnabled"):
            self.selectors_input.setClearButtonEnabled(True)
        controls_layout.addWidget(QLabel("Selectores:"))
        controls_layout.addWidget(self.selectors_input)
        
        layout.addLayout(controls_layout)
        
        # Target attribute selection
        attr_layout = QHBoxLayout()
        self.target_attr_combo = QComboBox()
        self.target_attr_combo.addItems([
            "text", "href", "src", "alt", "title", "data-*", "innerHTML", "outerHTML"
        ])
        self.target_attr_combo.setCurrentText("text")
        attr_layout.addWidget(QLabel("Atributo objetivo:"))
        attr_layout.addWidget(self.target_attr_combo)
        
        # Custom data attribute input
        self.custom_data_attr = QLineEdit()
        self.custom_data_attr.setPlaceholderText("data-custom (para data-*)")
        self.custom_data_attr.setFixedHeight(32)
        self.custom_data_attr.setVisible(False)
        if hasattr(self.custom_data_attr, "setClearButtonEnabled"):
            self.custom_data_attr.setClearButtonEnabled(True)
        attr_layout.addWidget(QLabel("Data attr:"))
        attr_layout.addWidget(self.custom_data_attr)
        
        # Connect signal to show/hide custom data input
        self.target_attr_combo.currentTextChanged.connect(self.on_target_attr_changed)
        
        layout.addLayout(attr_layout)
        
        # Results
        self.extraction_text = QTextEdit()
        self.extraction_text.setPlaceholderText("Extracted data will appear here...")
        layout.addWidget(self.extraction_text)
        
        widget.setLayout(layout)
        return widget
    
    def create_export_tab(self):
        """Export of selected data"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        self.export_btn = QPushButton("📤 Exportar Datos")
        self.export_btn.clicked.connect(self.run_export)
        controls_layout.addWidget(self.export_btn)
        
        # Format selection
        self.export_format = QComboBox()
        self.export_format.addItems(["CSV", "Excel", "JSON", "YAML"])
        controls_layout.addWidget(QLabel("Formato:"))
        controls_layout.addWidget(self.export_format)
        
        # Filename input
        self.export_filename = QLineEdit()
        self.export_filename.setPlaceholderText("nombre_archivo")
        self.export_filename.setFixedHeight(32)  # Altura consistente
        if hasattr(self.export_filename, "setClearButtonEnabled"):
            self.export_filename.setClearButtonEnabled(True)
        controls_layout.addWidget(QLabel("Archivo:"))
        controls_layout.addWidget(self.export_filename)
        
        layout.addLayout(controls_layout)
        
        # Export info
        self.export_text = QTextEdit()
        self.export_text.setPlaceholderText("Export information will appear here...")
        layout.addWidget(self.export_text)
        
        widget.setLayout(layout)
        return widget
    
    def create_discovery_tab(self):
        """Descubrimiento de URLs"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        self.discover_btn = QPushButton("🔍 Descubrir URLs")
        self.discover_btn.clicked.connect(self.run_discovery)
        controls_layout.addWidget(self.discover_btn)
        
        # Parameters
        self.max_urls_spin = QSpinBox()
        self.max_urls_spin.setRange(10, 1000)
        self.max_urls_spin.setValue(100)
        controls_layout.addWidget(QLabel("Max URLs:"))
        controls_layout.addWidget(self.max_urls_spin)
        
        layout.addLayout(controls_layout)
        
        # Export controls
        export_layout = QHBoxLayout()
        export_layout.addWidget(QLabel("📤 Exportar URLs:"))
        
        self.export_csv_btn = QPushButton("📊 CSV")
        self.export_csv_btn.clicked.connect(lambda: self.export_urls('csv'))
        self.export_csv_btn.setEnabled(False)
        export_layout.addWidget(self.export_csv_btn)
        
        self.export_json_btn = QPushButton("📋 JSON")
        self.export_json_btn.clicked.connect(lambda: self.export_urls('json'))
        self.export_json_btn.setEnabled(False)
        export_layout.addWidget(self.export_json_btn)
        
        self.export_txt_btn = QPushButton("📄 TXT")
        self.export_txt_btn.clicked.connect(lambda: self.export_urls('txt'))
        self.export_txt_btn.setEnabled(False)
        export_layout.addWidget(self.export_txt_btn)
        
        self.export_excel_btn = QPushButton("📈 Excel")
        self.export_excel_btn.clicked.connect(lambda: self.export_urls('excel'))
        self.export_excel_btn.setEnabled(False)
        export_layout.addWidget(self.export_excel_btn)
        
        layout.addLayout(export_layout)
        
        # Results
        self.discovery_text = QTextEdit()
        self.discovery_text.setPlaceholderText("Discovered URLs will appear here...")
        layout.addWidget(self.discovery_text)
        
        # Store discovered URLs
        self.discovered_urls = []
        self.fuzzing_results = []
        
        widget.setLayout(layout)
        return widget
    
    def create_pattern_detection_tab(self):
        """Tab for DOM pattern detection"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        self.detect_patterns_btn = QPushButton("🔍 Detectar Patrones")
        self.detect_patterns_btn.clicked.connect(self.run_pattern_detection)
        controls_layout.addWidget(self.detect_patterns_btn)
        
        self.refresh_patterns_btn = QPushButton("🔄 Actualizar Patrones")
        self.refresh_patterns_btn.clicked.connect(self.refresh_pattern_detection)
        controls_layout.addWidget(self.refresh_patterns_btn)
        
        layout.addLayout(controls_layout)
        
        # Results
        self.patterns_text = QTextEdit()
        self.patterns_text.setPlaceholderText("Detected patterns will appear here...")
        layout.addWidget(self.patterns_text)
        
        # Pattern selection list
        patterns_group = QGroupBox("Patrones Detectados")
        patterns_layout = QVBoxLayout()
        
        self.patterns_list = QListWidget()
        self.patterns_list.itemClicked.connect(self.on_pattern_selected)
        patterns_layout.addWidget(self.patterns_list)
        
        # Extract pattern button
        self.extract_pattern_btn = QPushButton("📥 Extract Detected Pattern")
        self.extract_pattern_btn.clicked.connect(self.extract_detected_pattern)
        self.extract_pattern_btn.setEnabled(False)
        patterns_layout.addWidget(self.extract_pattern_btn)
        
        patterns_group.setLayout(patterns_layout)
        layout.addWidget(patterns_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_status_tab(self):
        """Estado del sistema"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        self.status_btn = QPushButton("🔄 Actualizar Estado")
        self.status_btn.clicked.connect(self.refresh_status)
        controls_layout.addWidget(self.status_btn)
        
        layout.addLayout(controls_layout)
        
        # Status display
        self.status_text = QTextEdit()
        self.status_text.setPlaceholderText("System status will appear here...")
        layout.addWidget(self.status_text)
        
        widget.setLayout(layout)
        return widget
    
    # Action methods
    @requires_premium("scraping", "analysis")
    def run_analysis(self):
        """Execute real page analysis"""
        try:
            if not self.scraping_integration.current_html:
                self.analysis_text.setText("❌ Error: No hay contenido HTML para analizar")
                return
            
            result = self.scraping_integration.analyze_page()
            
            if "error" not in result:
                display_text = f"✅ ANÁLISIS COMPLETADO\n"
                display_text += f"📅 Timestamp: {result.get('timestamp', 'N/A')}\n"
                display_text += f"🔗 URL: {result.get('url', 'N/A')}\n\n"
                
                # Display detailed analysis
                if 'analysis' in result:
                    analysis = result['analysis']
                    display_text += "📊 ELEMENTOS DETECTADOS:\n"
                    display_text += f"   • Links: {len(analysis.get('links', []))}\n"
                    display_text += f"   • Images: {len(analysis.get('images', []))}\n"
                    display_text += f"   • Forms: {len(analysis.get('forms', []))}\n"
                    display_text += f"   • Tablas: {len(analysis.get('tables', []))}\n"
                    display_text += f"   • Listas: {len(analysis.get('lists', []))}\n"
                    display_text += f"   • Headers: {len(analysis.get('headings', []))}\n"
                    display_text += f"   • Paragraphs: {len(analysis.get('paragraphs', []))}\n"
                    display_text += f"   • Buttons: {len(analysis.get('buttons', []))}\n"
                    display_text += f"   • Inputs: {len(analysis.get('inputs', []))}\n\n"
                    
                    # Show some examples
                    if analysis.get('links'):
                        display_text += "🔗 EJEMPLOS DE ENLACES:\n"
                        for i, link in enumerate(analysis['links'][:5], 1):
                            display_text += f"   {i}. {link.get('text', 'Sin texto')} -> {link.get('href', 'Sin URL')}\n"
                    
                    if analysis.get('headings'):
                        display_text += "\n📝 EJEMPLOS DE ENCABEZADOS:\n"
                        for i, heading in enumerate(analysis['headings'][:5], 1):
                            display_text += f"   {i}. {heading.get('level', 'h')}: {heading.get('text', 'Sin texto')}\n"
                
                self.analysis_text.setText(display_text)
            else:
                self.analysis_text.setText(f"❌ Error: {result.get('error', 'Desconocido')}")
        except Exception as e:
            self.analysis_text.setText(f"❌ Error: {str(e)}")
    
    def refresh_html(self):
        """Actualizar HTML desde el navegador"""
        try:
            if hasattr(self, 'browser_tab') and self.browser_tab:
                # Get current HTML from the browser
                self.browser_tab.page().toHtml(self.on_html_updated)
                self.analysis_text.setText("🔄 Obteniendo HTML del navegador...")
            else:
                self.analysis_text.setText("❌ No browser tab available")
        except Exception as e:
            self.analysis_text.setText(f"❌ Error actualizando HTML: {str(e)}")
    
    def on_html_updated(self, html_content):
        """Callback cuando se actualiza el HTML desde el navegador"""
        try:
            if html_content and self.scraping_integration:
                # Update the scraping integration with new HTML
                current_url = ""
                if hasattr(self, 'browser_tab') and self.browser_tab:
                    current_url = self.browser_tab.url().toString()
                
                success = self.scraping_integration.update_content(html_content, current_url)
                
                if success:
                    self.analysis_text.setText("✅ HTML actualizado correctamente desde el navegador")
                    print(f"[OK] HTML updated: {len(html_content)} characters from {current_url}")
                else:
                    self.analysis_text.setText("❌ Error actualizando contenido en scraping integration")
            else:
                self.analysis_text.setText("❌ No HTML content received from browser")
        except Exception as e:
            self.analysis_text.setText(f"❌ Error procesando HTML actualizado: {str(e)}")
            print(f"[ERROR] Error processing updated HTML: {e}")
    
    def load_selectable_elements(self):
        """Load selectable elements from the page"""
        try:
            if not self.scraping_integration.current_html:
                QMessageBox.warning(self, "Error", "No hay contenido HTML para analizar")
                return
            
            elements = self.scraping_integration.get_selectable_elements()
            self.all_elements = elements  # Store all elements for filtering
            self.display_elements(elements)
            
            QMessageBox.information(self, "Éxito", f"Se cargaron {len(elements)} elementos")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando elementos: {str(e)}")
    
    def display_elements(self, elements):
        """Display elements in the list with better formatting"""
        self.elements_list.clear()
        
        for element in elements:
            item = QListWidgetItem()
            
            # Create better display text
            element_type = element.get('type', 'Otro')
            importance = element.get('importance', 0)
            text_limpio = element.get('texto_limpio', element.get('text', 'Sin texto'))
            
            # Truncate text for display
            display_text = text_limpio[:60] + "..." if len(text_limpio) > 60 else text_limpio
            
            # Add importance indicator
            if importance > 80:
                display_text = f"⭐ [{element_type}] {display_text}"
            elif importance > 60:
                display_text = f"🔸 [{element_type}] {display_text}"
            else:
                display_text = f"📄 [{element_type}] {display_text}"
            
            item.setText(display_text)
            item.setData(Qt.UserRole, element)
            
            # Set comprehensive tooltip
            tooltip = f"Tipo: {element_type}\n"
            tooltip += f"Importancia: {importance}\n"
            tooltip += f"Selector: {element.get('selector', 'N/A')}\n"
            tooltip += f"Texto limpio: {text_limpio}\n"
            
            # Add structured data info
            if "structured_data" in element:
                structured = element["structured_data"]
                if structured.get("url"):
                    tooltip += f"URL: {structured['url']}\n"
                if structured.get("texto_enlace"):
                    tooltip += f"Texto enlace: {structured['texto_enlace']}\n"
                if structured.get("nivel_encabezado"):
                    tooltip += f"Nivel: {structured['nivel_encabezado']}\n"
            
            item.setToolTip(tooltip)
            
            self.elements_list.addItem(item)
    
    def filter_elements(self):
        """Filter elements by type"""
        if not hasattr(self, 'all_elements'):
            return
        
        filter_type = self.filter_combo.currentText()
        
        if filter_type == "Todos":
            filtered_elements = self.all_elements
        else:
            # Map display names to element types
            type_mapping = {
                "Encabezados": "Encabezado",
                "Links": "Link", 
                "Buttons": "Button",
                "Paragraphs": "Paragraph",
                "Images": "Image",
                "Highlighted Text": "Highlighted Text"
            }
            
            target_type = type_mapping.get(filter_type, filter_type)
            filtered_elements = [e for e in self.all_elements if e.get('type') == target_type]
        
        self.display_elements(filtered_elements)
    
    def add_single_element(self, item):
        """Add a single element when double-clicked"""
        try:
            element_data = item.data(Qt.UserRole)
            self.scraping_integration.add_selected_element(element_data)
            self.update_selected_list()
            
            QMessageBox.information(self, "Element Added", 
                f"✅ Element added:\n{element_data.get('type', 'N/A')}: {element_data.get('text', 'N/A')}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error adding element: {str(e)}")
    
    def clear_selection(self):
        """Clear element selection"""
        try:
            self.scraping_integration.clear_selected_elements()
            self.selected_list.clear()
            QMessageBox.information(self, "Success", "Selection cleared")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error clearing selection: {str(e)}")
    
    def select_all_elements(self):
        """Seleccionar todos los elementos"""
        try:
            self.elements_list.selectAll()
            self.add_selected_elements()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error seleccionando elementos: {str(e)}")
    
    def add_selected_elements(self):
        """Agregar elementos seleccionados a la lista de seleccionados"""
        try:
            selected_items = self.elements_list.selectedItems()
            
            for item in selected_items:
                element_data = item.data(Qt.UserRole)
                self.scraping_integration.add_selected_element(element_data)
            
            self.update_selected_list()
            QMessageBox.information(self, "Éxito", f"Se agregaron {len(selected_items)} elementos")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error agregando elementos: {str(e)}")
    
    def update_selected_list(self):
        """Actualizar lista de elementos seleccionados"""
        try:
            self.selected_list.clear()
            selected_elements = self.scraping_integration.get_selected_elements()
            
            print(f"[DEBUG] Actualizando lista con {len(selected_elements)} elementos")
            
            for element in selected_elements:
                item = QListWidgetItem()
                
                # Obtener información del elemento
                tag = element.get('tag', 'unknown')
                text = element.get('text', element.get('full_text', 'Sin texto'))
                
                # Priorizar información de productos si está disponible
                product_title = element.get('product_title', '')
                product_price = element.get('product_price', '')
                
                # Crear texto de display inteligente
                if product_title and product_price:
                    display_text = f"[{tag}] {product_title} - {product_price}"
                elif product_title:
                    display_text = f"[{tag}] {product_title}"
                elif product_price:
                    display_text = f"[{tag}] {product_price}"
                else:
                    display_text = f"[{tag}] {text}"
                
                # Truncar texto para display
                if len(display_text) > 80:
                    display_text = display_text[:77] + "..."
                
                item.setText(display_text)
                item.setData(Qt.UserRole, element)
                
                # Crear tooltip con información completa
                tooltip = f"Tipo: {tag}\n"
                tooltip += f"Texto: {text[:100]}...\n" if len(text) > 100 else f"Texto: {text}\n"
                tooltip += f"Selector: {element.get('selector', 'N/A')}\n"
                
                if product_title:
                    tooltip += f"Título del producto: {product_title}\n"
                if product_price:
                    tooltip += f"Precio: {product_price}\n"
                if element.get('product_description'):
                    tooltip += f"Descripción: {element.get('product_description')}\n"
                
                item.setToolTip(tooltip)
                self.selected_list.addItem(item)
                
                print(f"[DEBUG] Elemento añadido a la lista: {display_text}")
                
        except Exception as e:
            print(f"Error actualizando lista: {e}")
    
    @requires_premium("scraping", "interactive_selection")
    def toggle_interactive_selection(self):
        """Activate/deactivate interactive selection from the page"""
        try:
            if not hasattr(self, 'interactive_selection_active'):
                self.interactive_selection_active = False
            
            self.interactive_selection_active = not self.interactive_selection_active
            
            # Verificar y establecer conexión con el navegador
            if not self._ensure_browser_connection():
                QMessageBox.critical(self, "Error", 
                    "❌ Could not establish connection with browser.\n\n"
                    "Make sure that:\n"
                    "• There is an open tab in the browser\n"
                    "• The page has finished loading\n"
                    "• You have permissions to execute JavaScript")
                return
            
            # Activar/desactivar en el navegador
            if hasattr(self, 'browser_tab') and self.browser_tab:
                # Primero inyectar el content script si no está presente
                self._inject_content_script()
                
                js_code = f"window.toggleInteractiveSelection({str(self.interactive_selection_active).lower()});"
                self.browser_tab.page().runJavaScript(js_code)
                print(f"🎯 Enviando comando JavaScript: toggleInteractiveSelection({self.interactive_selection_active})")
            else:
                print("❌ No hay pestaña del navegador disponible")
            
            if self.interactive_selection_active:
                self.enable_selection_btn.setText("🎯 Desactivar Selección Interactiva")
                self.enable_selection_btn.setStyleSheet("background-color: #ff6b6b;")
                
                # Iniciar sincronización automática
                self._start_auto_sync()
                QMessageBox.information(self, "Selección Interactiva", 
                    "✅ Selección interactiva ACTIVADA\n\n"
                    "Ahora puedes:\n"
                    "• Hacer clic en elementos de la página para añadirlos\n"
                    "• Usar el selector manual para añadir elementos específicos\n"
                    "• Los elementos seleccionados aparecerán en la lista de abajo\n\n"
                    "�� El cursor cambiará a una cruz cuando pases sobre elementos clickeables\n"
                    "🔍 Usa '🔄 Sincronizar JS' para traer elementos seleccionados")
            else:
                self.enable_selection_btn.setText("🎯 Activar Selección Interactiva")
                self.enable_selection_btn.setStyleSheet("")
                
                # Detener sincronización automática
                self._stop_auto_sync()
                QMessageBox.information(self, "Selección Interactiva", 
                    "❌ Selección interactiva DESACTIVADA")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error activando selección interactiva: {str(e)}")
    
    def add_elements_by_selector(self):
        """Añadir elementos usando un selector CSS"""
        try:
            selector = self.manual_selector_input.text().strip()
            if not selector:
                QMessageBox.warning(self, "Error", "Por favor ingresa un selector CSS")
                return
            
            result = self.scraping_integration.add_element_by_selector(selector)
            
            if "error" not in result:
                QMessageBox.information(self, "Éxito", 
                    f"✅ Se añadieron {result.get('elements_added', 0)} elementos\n"
                    f"Selector: {result.get('selector', 'N/A')}")
                self.update_selected_list()
                self.manual_selector_input.clear()
            else:
                QMessageBox.critical(self, "Error", f"Error añadiendo elementos: {result.get('error', 'Desconocido')}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error añadiendo elementos: {str(e)}")
    
    def add_element_from_page_click(self, x: int, y: int):
        """Añadir elemento desde clic en la página (llamado desde el navegador)"""
        try:
            if not hasattr(self, 'interactive_selection_active') or not self.interactive_selection_active:
                return
            
            result = self.scraping_integration.add_element_by_click(x, y)
            
            if "error" not in result:
                self.update_selected_list()
                print(f"✅ Elemento añadido desde clic en ({x}, {y})")
            else:
                print(f"❌ Error añadiendo elemento desde clic: {result.get('error', 'Desconocido')}")
                
        except Exception as e:
            print(f"Error añadiendo elemento desde clic: {e}")
    
    def handle_page_click(self, x: int, y: int):
        """Manejar clic en la página web"""
        try:
            if hasattr(self, 'interactive_selection_active') and self.interactive_selection_active:
                self.add_element_from_page_click(x, y)
        except Exception as e:
            print(f"Error manejando clic en página: {e}")
    
    @requires_premium("scraping", "javascript_handling")
    def sync_javascript_elements(self):
        """Sincronizar elementos seleccionados desde JavaScript"""
        try:
            if hasattr(self, 'browser_tab') and self.browser_tab:
                print("[DEBUG] Iniciando sincronización de elementos JavaScript...")
                # Get selected elements from JavaScript
                js_code = "window.getSelectedElements ? window.getSelectedElements() : [];"
                self.browser_tab.page().runJavaScript(js_code, self.process_javascript_elements)
                
                # Also check if interactive selection is active
                check_active_js = "window.interactiveSelectionActive || false;"
                self.browser_tab.page().runJavaScript(check_active_js, self.check_selection_status)
            else:
                print("[ERROR] No hay pestaña del navegador disponible para sincronización")
                QMessageBox.warning(self, "Error", "No hay pestaña del navegador disponible")
        except Exception as e:
            print(f"[ERROR] Error sincronizando elementos: {e}")
            QMessageBox.critical(self, "Error", f"Error sincronizando elementos: {str(e)}")
    
    def check_selection_status(self, is_active):
        """Check if interactive selection is active"""
        if is_active:
            print("✅ Selección interactiva está activa en JavaScript")
        else:
            print("❌ Selección interactiva NO está activa en JavaScript")
    
    def process_javascript_elements(self, js_elements):
        """Procesar elementos seleccionados desde JavaScript"""
        try:
            print(f"[DEBUG] process_javascript_elements llamado con: {type(js_elements)}, longitud: {len(js_elements) if js_elements else 0}")
            
            # Si recibimos un string, intentar parsearlo como JSON
            if isinstance(js_elements, str):
                try:
                    js_elements = json.loads(js_elements) if js_elements.strip() else []
                    print(f"[DEBUG] JSON parseado correctamente: {len(js_elements)} elementos")
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Error parseando JSON: {e}, contenido: {js_elements[:100]}")
                    js_elements = []
            
            if js_elements and len(js_elements) > 0:
                added_count = 0
                for js_element in js_elements:
                    # Convert JavaScript element to Python format with complete data
                    element_data = {
                        "tag": js_element.get('tag', 'unknown'),
                        "text": js_element.get('text', ''),
                        "full_text": js_element.get('fullText', js_element.get('text', '')),
                        "html": js_element.get('html', ''),
                        "innerHTML": js_element.get('innerHTML', ''),
                        "selector": js_element.get('selector', ''),
                        "attributes": js_element.get('attributes', {}),
                        "importance": 50,  # Default importance
                        "type": self._get_element_type_from_tag(js_element.get('tag', 'div')),
                        # Datos específicos de productos
                        "product_title": js_element.get('productTitle', ''),
                        "product_price": js_element.get('productPrice', ''),
                        "product_description": js_element.get('productDescription', ''),
                        "product_image": js_element.get('productImage', ''),
                        # Datos estructurados para compatibilidad
                        "structured_data": {
                            "texto_limpio": js_element.get('text', ''),
                            "texto_original": js_element.get('fullText', ''),
                            "tipo_elemento": js_element.get('tag', ''),
                            "selector": js_element.get('selector', ''),
                            "url": js_element.get('href', ''),
                            "texto_enlace": js_element.get('text', '') if js_element.get('href') else '',
                            "url_imagen": js_element.get('src', '') or js_element.get('productImage', ''),
                            "texto_alternativo": js_element.get('alt', ''),
                            "nivel_encabezado": js_element.get('tag', '') if js_element.get('tag', '').startswith('h') else '',
                            "texto_encabezado": js_element.get('text', '') if js_element.get('tag', '').startswith('h') else '',
                            "atributos": js_element.get('attributes', {})
                        }
                    }
                    
                    self.scraping_integration.add_selected_element(element_data)
                    added_count += 1
                
                self.update_selected_list()
                
                # Mostrar notificación solo si no es sincronización automática
                if not hasattr(self, '_auto_sync_active') or not self._auto_sync_active:
                    QMessageBox.information(self, "Sincronización Exitosa", 
                        f"✅ Se sincronizaron {added_count} elementos desde JavaScript")
                else:
                    print(f"✅ Sincronización automática: {added_count} elementos añadidos")
                
                # Clear JavaScript elements after sync
                if hasattr(self, 'browser_tab') and self.browser_tab:
                    self.browser_tab.page().runJavaScript("window.clearSelectedElements();")
            else:
                QMessageBox.information(self, "Sin Elementos", "No hay elementos seleccionados en JavaScript")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error procesando elementos: {str(e)}")
    
    def _get_element_type_from_tag(self, tag: str) -> str:
        """Get element type from tag name"""
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return "Encabezado"
        elif tag == 'a':
            return "Enlace"
        elif tag in ['button', 'input']:
            return "Botón"
        elif tag == 'img':
            return "Imagen"
        elif tag == 'p':
            return "Párrafo"
        elif tag in ['span', 'div']:
            return "Contenedor"
        elif tag in ['li', 'td', 'th']:
            return "Elemento de lista"
        elif tag in ['strong', 'b', 'em', 'i']:
            return "Texto destacado"
        else:
            return "Otro"
    
    def on_target_attr_changed(self, attr_name):
        """Handle target attribute selection change"""
        if attr_name == "data-*":
            self.custom_data_attr.setVisible(True)
        else:
            self.custom_data_attr.setVisible(False)
    
    @requires_premium("scraping", "advanced_scraping")
    def run_extraction(self):
        """Ejecutar extracción de datos con atributo objetivo configurable"""
        try:
            selectors_text = self.selectors_input.text()
            selectors = [s.strip() for s in selectors_text.split(',')] if selectors_text else ['h1', 'p', 'a']
            
            # Get target attribute
            target_attr = self.target_attr_combo.currentText()
            if target_attr == "data-*":
                custom_attr = self.custom_data_attr.text().strip()
                if custom_attr:
                    target_attr = custom_attr
                else:
                    target_attr = "data-value"  # Default data attribute
            
            result = self.scraping_integration.extract_data(selectors, target_attr=target_attr)
            
            if result.get("ok"):
                display_text = f"✅ EXTRACCIÓN COMPLETADA\n"
                display_text += f"🎯 Selectores usados: {len(selectors)}\n"
                display_text += f"📊 Total elementos: {result.get('total_elements', 0)}\n"
                display_text += f"🎯 Atributo objetivo: {target_attr}\n\n"
                
                # Display extracted data
                if result.get('extracted'):
                    display_text += "📥 DATOS EXTRAÍDOS:\n"
                    for selector, data in result['extracted'].items():
                        display_text += f"\n🔍 Selector '{selector}':\n"
                        if isinstance(data, list):
                            for i, item in enumerate(data[:3], 1):
                                # Show the target attribute value
                                target_value = item.get(target_attr, item.get('text', 'Sin valor'))
                                display_text += f"   {i}. {target_value[:50]}...\n"
                            if len(data) > 3:
                                display_text += f"   ... y {len(data) - 3} más\n"
                        else:
                            target_value = data.get(target_attr, data.get('text', 'Sin valor'))
                            display_text += f"   {target_value[:100]}...\n"
                
                self.extraction_text.setText(display_text)
            else:
                self.extraction_text.setText(f"❌ Error: {result.get('error', 'Desconocido')}")
        except Exception as e:
            self.extraction_text.setText(f"❌ Error: {str(e)}")
    
    def run_export(self):
        """Ejecutar exportación de datos"""
        try:
            if not self.scraping_integration.get_selected_elements():
                QMessageBox.warning(self, "Error", "No hay elementos seleccionados para exportar")
                return
            
            format_type = self.export_format.currentText().lower()
            filename = self.export_filename.text() or "scraped_data"
            
            result = self.scraping_integration.export_selected_data(format_type, filename)
            
            if "error" not in result:
                display_text = f"📤 EXPORTACIÓN COMPLETADA\n"
                display_text += f"📄 Formato: {result.get('format', 'N/A')}\n"
                display_text += f"📁 Archivo: {result.get('filename', 'N/A')}\n"
                display_text += f"📊 Elementos exportados: {result.get('elements_exported', 0)}\n"
                display_text += f"📋 Columnas exportadas: {result.get('columns_exported', 0)}\n\n"
                
                # Show sample of exported data
                display_text += "📋 COLUMNAS EXPORTADAS:\n"
                columns_info = [
                    "• tipo_elemento - Tipo de elemento HTML",
                    "• tipo_categoria - Categoría del elemento",
                    "• texto_limpio - Texto limpio sin caracteres especiales",
                    "• texto_original - Texto original extraído",
                    "• selector_css - Selector CSS del elemento",
                    "• importancia - Puntuación de importancia",
                    "• url_enlace - URL del enlace (si aplica)",
                    "• texto_enlace - Texto del enlace",
                    "• url_imagen - URL de la imagen (si aplica)",
                    "• texto_alternativo - Texto alternativo de imagen",
                    "• nivel_encabezado - Nivel H1-H6 (si aplica)",
                    "• texto_encabezado - Texto del encabezado",
                    "• tipo_boton - Tipo de botón (si aplica)",
                    "• valor_boton - Valor del botón",
                    "• atributo_* - Atributos HTML específicos"
                ]
                
                for column_info in columns_info:
                    display_text += f"  {column_info}\n"
                
                display_text += "\n💡 CONSEJOS:\n"
                display_text += "• CSV/Excel: Datos limpios y estructurados para análisis\n"
                display_text += "• JSON/YAML: Datos completos con metadatos\n"
                display_text += "• Los caracteres especiales han sido limpiados\n"
                display_text += "• Los datos están organizados por columnas específicas"
                
                self.export_text.setText(display_text)
                QMessageBox.information(self, "Éxito", 
                    f"✅ Datos exportados exitosamente\n"
                    f"📁 Archivo: {result.get('filename', 'archivo')}\n"
                    f"📊 {result.get('elements_exported', 0)} elementos exportados\n"
                    f"📋 {result.get('columns_exported', 0)} columnas de datos")
            else:
                self.export_text.setText(f"❌ Error: {result.get('error', 'Desconocido')}")
                QMessageBox.critical(self, "Error", f"Error exportando: {result.get('error', 'Desconocido')}")
        except Exception as e:
            self.export_text.setText(f"❌ Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error exportando: {str(e)}")
    
    def run_discovery(self):
        """Ejecutar descubrimiento de URLs"""
        try:
            max_urls = self.max_urls_spin.value()
            
            result = self.scraping_integration.discover_urls(max_urls, 3)
            
            if "error" not in result:
                # Store discovered URLs for export
                self.discovered_urls = result.get('discovered_urls', [])
                self.fuzzing_results = result.get('fuzzing_results', [])
                
                display_text = f"✅ DESCUBRIMIENTO COMPLETADO\n"
                display_text += f"🔍 URLs encontradas: {len(self.discovered_urls)}\n"
                display_text += f"🎯 Resultados de fuzzing: {len(self.fuzzing_results)}\n\n"
                
                # Display discovered URLs
                if self.discovered_urls:
                    display_text += "🔗 URLs DESCUBIERTAS:\n"
                    for i, url in enumerate(self.discovered_urls[:10], 1):
                        display_text += f"   {i}. {url}\n"
                    if len(self.discovered_urls) > 10:
                        display_text += f"   ... y {len(self.discovered_urls) - 10} más\n"
                
                # Enable export buttons if URLs were found
                if self.discovered_urls:
                    self.export_csv_btn.setEnabled(True)
                    self.export_json_btn.setEnabled(True)
                    self.export_txt_btn.setEnabled(True)
                    self.export_excel_btn.setEnabled(True)
                    display_text += "\n📤 Botones de exportación habilitados"
                else:
                    self.export_csv_btn.setEnabled(False)
                    self.export_json_btn.setEnabled(False)
                    self.export_txt_btn.setEnabled(False)
                    self.export_excel_btn.setEnabled(False)
                    display_text += "\n⚠️ No se encontraron URLs para exportar"
                
                self.discovery_text.setText(display_text)
            else:
                self.discovery_text.setText(f"❌ Error: {result.get('error', 'Desconocido')}")
                # Disable export buttons on error
                self.export_csv_btn.setEnabled(False)
                self.export_json_btn.setEnabled(False)
                self.export_txt_btn.setEnabled(False)
                self.export_excel_btn.setEnabled(False)
        except Exception as e:
            self.discovery_text.setText(f"❌ Error: {str(e)}")
            # Disable export buttons on error
            self.export_csv_btn.setEnabled(False)
            self.export_json_btn.setEnabled(False)
            self.export_txt_btn.setEnabled(False)
            self.export_excel_btn.setEnabled(False)
    
    def export_urls(self, format_type: str):
        """Exportar URLs descubiertas a un formato específico"""
        try:
            if not self.discovered_urls:
                QMessageBox.warning(self, "Error", "No hay URLs para exportar.")
                return
            
            filename = f"discovered_urls.{format_type}"
            
            if format_type == 'csv':
                self.scraping_integration.export_urls_to_csv(self.discovered_urls, filename)
            elif format_type == 'json':
                self.scraping_integration.export_urls_to_json(self.discovered_urls, filename)
            elif format_type == 'txt':
                self.scraping_integration.export_urls_to_txt(self.discovered_urls, filename)
            elif format_type == 'excel':
                self.scraping_integration.export_urls_to_excel(self.discovered_urls, filename)
            
            QMessageBox.information(self, "Éxito", f"URLs exportadas exitosamente a {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error exportando URLs: {str(e)}")
    
    def refresh_status(self):
        """Actualizar estado del sistema"""
        try:
            result = self.scraping_integration.get_comprehensive_status()
            
            if "error" not in result:
                display_text = f"ℹ️ ESTADO DEL SISTEMA\n"
                display_text += f"🔧 Sistema de scraping integrado: {'✅ Activo' if result.get('components', {}) else '❌ Inactivo'}\n"
                display_text += f"📦 Componentes: {len(result.get('components', {}))}\n\n"
                
                if result.get('current_state'):
                    state = result['current_state']
                    display_text += "📊 ESTADO ACTUAL:\n"
                    display_text += f"   • HTML cargado: {'✅' if state.get('html_loaded') else '❌'}\n"
                    display_text += f"   • URL cargada: {'✅' if state.get('url_loaded') else '❌'}\n"
                    display_text += f"   • Análisis listo: {'✅' if state.get('analysis_ready') else '❌'}\n"
                    display_text += f"   • Elementos seleccionados: {state.get('elements_selected', 0)}\n"
                    display_text += f"   • Datos extraídos: {'✅' if state.get('data_extracted') else '❌'}\n"
                
                self.status_text.setText(display_text)
            else:
                self.status_text.setText(f"❌ Error: {result.get('error', 'Desconocido')}")
        except Exception as e:
            self.status_text.setText(f"❌ Error: {str(e)}")
    
    # Pattern Detection Methods
    def run_pattern_detection(self):
        """Ejecutar detección de patrones"""
        try:
            if not self.scraping_integration.current_html:
                QMessageBox.warning(self, "Error", "No hay contenido HTML para analizar")
                return
            
            # Verificar si el detector de patrones está disponible
            if not hasattr(self.scraping_integration, 'detect_dom_patterns'):
                QMessageBox.warning(self, "Error", "El detector de patrones no está disponible. Verifica que pattern_detector.py esté presente.")
                return
            
            result = self.scraping_integration.detect_dom_patterns()
            
            if "error" not in result:
                self.detected_patterns = result.get("patterns", [])
                self.display_patterns(self.detected_patterns)
                QMessageBox.information(self, "Éxito", f"✅ Se detectaron {len(self.detected_patterns)} patrones")
            else:
                self.patterns_text.setText(f"❌ Error: {result.get('error', 'Desconocido')}")
                QMessageBox.critical(self, "Error", f"Error detectando patrones: {result.get('error', 'Desconocido')}")
        except Exception as e:
            self.patterns_text.setText(f"❌ Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error detectando patrones: {str(e)}")
    
    def refresh_pattern_detection(self):
        """Actualizar detección de patrones"""
        try:
            # Actualizar HTML desde el navegador si es necesario
            if hasattr(self, 'browser_tab') and self.browser_tab:
                self.browser_tab.page().toHtml(lambda html_content: self.on_html_updated_for_patterns(html_content))
            else:
                self.run_pattern_detection()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error actualizando patrones: {str(e)}")
    
    @requires_premium("scraping", "data_analysis")
    def refresh_all_data(self):
        """Refrescar todos los datos desde el navegador"""
        try:
            if hasattr(self, 'browser_tab') and self.browser_tab:
                self.browser_tab.page().toHtml(lambda html_content: self.on_html_updated_all(html_content))
                QMessageBox.information(self, "Refrescar Datos", "🔄 Actualizando todos los datos desde el navegador...")
            else:
                QMessageBox.warning(self, "Error", "No hay pestaña del navegador disponible")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error refrescando datos: {str(e)}")
    
    def on_html_updated_all(self, html_content):
        """Callback cuando se actualiza el HTML para todos los datos"""
        try:
            if html_content and self.scraping_integration:
                current_url = ""
                if hasattr(self, 'browser_tab') and self.browser_tab:
                    current_url = self.browser_tab.url().toString()
                
                success = self.scraping_integration.update_content(html_content, current_url)
                
                if success:
                    # Refresh all panels
                    self.run_analysis()
                    self.load_selectable_elements()
                    self.run_pattern_detection()
                    QMessageBox.information(self, "Éxito", "✅ Todos los datos actualizados correctamente")
                else:
                    QMessageBox.critical(self, "Error", "Error actualizando contenido")
            else:
                QMessageBox.critical(self, "Error", "No se recibió contenido HTML del navegador")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error procesando HTML actualizado: {str(e)}")
    
    def on_html_updated_for_patterns(self, html_content):
        """Callback cuando se actualiza el HTML para patrones"""
        try:
            if self.scraping_integration:
                self.scraping_integration.update_content(html_content, self.scraping_integration.current_url)
                self.run_pattern_detection()
        except Exception as e:
            print(f"Error actualizando HTML para patrones: {e}")
    
    def display_patterns(self, patterns):
        """Muestra los patrones detectados"""
        self.patterns_list.clear()
        
        if not patterns:
            self.patterns_text.setText("No se detectaron patrones repetitivos en el DOM")
            return
        
        display_text = f"✅ PATRONES DETECTADOS: {len(patterns)}\n\n"
        
        for i, pattern in enumerate(patterns, 1):
            pattern_type = pattern.get('type', 'desconocido').upper()
            elements_count = pattern.get('elements_count', pattern.get('items_count', pattern.get('rows_count', pattern.get('count', 0))))
            similarity_score = pattern.get('similarity_score', 0) * 100
            recommended_selector = pattern.get('selectors', {}).get('recommended', 'N/A')
            
            display_text += f"🔍 Patrón {i}: {pattern_type}\n"
            display_text += f"   • Elementos: {elements_count}\n"
            display_text += f"   • Similitud: {similarity_score:.1f}%\n"
            display_text += f"   • Selector recomendado: {recommended_selector}\n\n"
            
            # Mostrar ejemplos si están disponibles
            if 'sample_items' in pattern:
                display_text += f"   📋 Ejemplos de elementos:\n"
                for j, sample in enumerate(pattern['sample_items'][:2], 1):
                    display_text += f"      {j}. {sample.get('text', 'Sin texto')[:50]}...\n"
            elif 'sample_elements' in pattern:
                display_text += f"   📋 Ejemplos de elementos:\n"
                for j, sample in enumerate(pattern['sample_elements'][:2], 1):
                    display_text += f"      {j}. {sample.get('text', 'Sin texto')[:50]}...\n"
            elif 'sample_rows' in pattern:
                display_text += f"   📋 Ejemplos de filas:\n"
                for j, sample in enumerate(pattern['sample_rows'][:2], 1):
                    display_text += f"      {j}. {sample.get('cells_count', 0)} celdas\n"
            
            display_text += "\n"
        
        self.patterns_text.setText(display_text)
        
        # Añadir patrones a la lista para selección
        for i, pattern in enumerate(patterns, 1):
            pattern_type = pattern.get('type', 'desconocido').upper()
            elements_count = pattern.get('elements_count', pattern.get('items_count', pattern.get('rows_count', pattern.get('count', 0))))
            similarity_score = pattern.get('similarity_score', 0) * 100
            
            item_text = f"Patrón {i}: {pattern_type} ({elements_count} elementos, {similarity_score:.1f}% similitud)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, pattern)
            self.patterns_list.addItem(item)
    
    def on_pattern_selected(self, item):
        """Cuando se selecciona un patrón de la lista"""
        try:
            self.selected_pattern = item.data(Qt.UserRole)
            self.extract_pattern_btn.setEnabled(True)
            
            # Mostrar información detallada del patrón seleccionado
            if self.selected_pattern:
                pattern_info = f"🔍 PATRÓN SELECCIONADO:\n\n"
                pattern_info += f"Tipo: {self.selected_pattern.get('type', 'desconocido').upper()}\n"
                pattern_info += f"Elementos: {self.selected_pattern.get('elements_count', self.selected_pattern.get('items_count', self.selected_pattern.get('rows_count', self.selected_pattern.get('count', 0))))}\n"
                pattern_info += f"Similitud: {self.selected_pattern.get('similarity_score', 0) * 100:.1f}%\n\n"
                
                selectors = self.selected_pattern.get('selectors', {})
                pattern_info += f"SELECTORES DISPONIBLES:\n"
                pattern_info += f"• Recomendado: {selectors.get('recommended', 'N/A')}\n"
                pattern_info += f"• Ancestro común: {selectors.get('common_ancestor', 'N/A')}\n"
                pattern_info += f"• Selector común: {selectors.get('common_selector', 'N/A')}\n"
                
                if selectors.get('index_selectors'):
                    pattern_info += f"• Selectores por índice: {len(selectors['index_selectors'])} disponibles\n"
                
                self.patterns_text.setText(pattern_info)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error seleccionando patrón: {str(e)}")
    
    def extract_detected_pattern(self):
        """Extrae los elementos del patrón detectado"""
        try:
            if not hasattr(self, 'selected_pattern') or not self.selected_pattern:
                QMessageBox.warning(self, "Error", "No hay patrón seleccionado")
                return
            
            # FIX: evitar contenedores genéricos si existen selectores de items
            GENERIC_TAGS = {"div", "section", "main", "article", "ul", "ol", "table", "tbody", "tr"}
            
            def _use_effective_selector(det):
                rec = (det or {}).get("recommended") or ""
                idx = (det or {}).get("index_selectors") or []
                # Si el recomendado es solo un tag genérico (ej: "div" o "div.list"), preferir el item
                tag = rec.split("#")[0].split(".")[0].split(":")[0].strip()
                if tag in GENERIC_TAGS and idx:
                    return idx[0]
                return rec or (idx[0] if idx else "")
            
            selector = _use_effective_selector(self.selected_pattern)
            
            if not selector:
                QMessageBox.warning(self, "Error", "No hay selector disponible para este patrón")
                return
            
            # Usar el selector para extraer elementos
            result = self.scraping_integration.add_element_by_selector(selector)
            
            if "error" not in result:
                elements_added = result.get('elements_added', 0)
                QMessageBox.information(self, "Éxito", 
                    f"✅ Se añadieron {elements_added} elementos del patrón detectado\n"
                    f"Selector usado: {selector}")
                self.update_selected_list()
                
                # Cambiar a la pestaña de selección para ver los elementos
                self.tab_widget.setCurrentIndex(1)  # Pestaña de selección
            else:
                QMessageBox.critical(self, "Error", f"Error extrayendo patrón: {result.get('error', 'Desconocido')}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error extrayendo patrón: {str(e)}")
    
    def _inject_content_script(self):
        """Inyectar el content script para selección interactiva"""
        try:
            if not hasattr(self, 'browser_tab') or not self.browser_tab:
                print("❌ No hay browser_tab disponible para inyectar script")
                return False
            
            print("🔄 Inyectando content script...")
            
            content_script = """
            (function() {
                // Evitar inyección múltiple y limpiar scripts anteriores
                if (window.tellectusScrapingInjected) {
                    console.log('Tellectus Scraping: Script ya inyectado, reinicializando...');
                    // Limpiar eventos anteriores si existen
                    if (window.tellectusCleanupFunction) {
                        window.tellectusCleanupFunction();
                    }
                }
                window.tellectusScrapingInjected = true;
                
                // Estado global
                window.interactiveSelectionActive = false;
                window.selectedElements = [];
                window.tellectusElementSelected = false;
                
                // Estilos para highlight
                const style = document.createElement('style');
                style.textContent = `
                    .tellectus-highlight {
                        outline: 2px solid #ff6b6b !important;
                        outline-offset: 2px !important;
                        background-color: rgba(255, 107, 107, 0.1) !important;
                        cursor: crosshair !important;
                    }
                    .tellectus-selected {
                        outline: 3px solid #4ecdc4 !important;
                        outline-offset: 2px !important;
                        background-color: rgba(78, 205, 196, 0.2) !important;
                    }
                `;
                document.head.appendChild(style);
                
                // Función para generar selector CSS robusto
                function generateSelector(element) {
                    if (!element || element === document) return '';
                    
                    // Si tiene ID, usarlo
                    if (element.id) {
                        return '#' + CSS.escape(element.id);
                    }
                    
                    // Construir ruta desde el elemento
                    const path = [];
                    let current = element;
                    
                    while (current && current !== document && current !== document.documentElement) {
                        let selector = current.tagName.toLowerCase();
                        
                        // Añadir clases si existen
                        if (current.className && typeof current.className === 'string') {
                            const classes = current.className.trim().split(/\\s+/).slice(0, 3);
                            if (classes.length > 0) {
                                selector += '.' + classes.map(cls => CSS.escape(cls)).join('.');
                            }
                        }
                        
                        // Añadir nth-of-type si hay hermanos del mismo tipo
                        const parent = current.parentElement;
                        if (parent) {
                            const siblings = Array.from(parent.children).filter(child => 
                                child.tagName === current.tagName
                            );
                            
                            if (siblings.length > 1) {
                                const index = siblings.indexOf(current) + 1;
                                selector += ':nth-of-type(' + index + ')';
                            }
                        }
                        
                        path.unshift(selector);
                        current = current.parentElement;
                    }
                    
                    return path.join(' > ');
                }
                
                // Función para extraer datos del elemento
                function extractElementData(element) {
                    // Extraer texto limpio (sin HTML)
                    const cleanText = element.textContent.trim();
                    
                    // Extraer HTML completo del elemento
                    const fullHTML = element.outerHTML;
                    
                    // Extraer texto específico para productos (títulos, precios, etc.)
                    const productData = extractProductInfo(element);
                    
                    return {
                        tag: element.tagName.toLowerCase(),
                        text: cleanText.substring(0, 200),
                        fullText: cleanText,
                        html: fullHTML,
                        innerHTML: element.innerHTML,
                        selector: generateSelector(element),
                        href: element.href || '',
                        src: element.src || '',
                        alt: element.alt || '',
                        title: element.title || '',
                        id: element.id || '',
                        className: element.className || '',
                        // Datos específicos de productos
                        productTitle: productData.title,
                        productPrice: productData.price,
                        productDescription: productData.description,
                        productImage: productData.image,
                        // Atributos completos
                        attributes: Array.from(element.attributes).reduce((acc, attr) => {
                            acc[attr.name] = attr.value;
                            return acc;
                        }, {})
                    };
                }
                
                // Función para extraer información específica de productos
                function extractProductInfo(element) {
                    const result = {
                        title: '',
                        price: '',
                        description: '',
                        image: ''
                    };
                    
                    // Buscar título del producto
                    const titleSelectors = ['h1', 'h2', 'h3', '.title', '.name', '.product-name', '.product-title'];
                    for (const selector of titleSelectors) {
                        const titleEl = element.querySelector(selector) || 
                                       (element.matches(selector) ? element : null);
                        if (titleEl && titleEl.textContent.trim()) {
                            result.title = titleEl.textContent.trim();
                            break;
                        }
                    }
                    
                    // Buscar precio
                    const priceSelectors = ['.price', '.precio', '.cost', '.amount', '[class*="price"]', '[class*="precio"]'];
                    for (const selector of priceSelectors) {
                        const priceEl = element.querySelector(selector) || 
                                       (element.matches(selector) ? element : null);
                        if (priceEl && priceEl.textContent.trim()) {
                            result.price = priceEl.textContent.trim();
                            break;
                        }
                    }
                    
                    // Buscar descripción
                    const descSelectors = ['.description', '.desc', '.product-desc', 'p'];
                    for (const selector of descSelectors) {
                        const descEl = element.querySelector(selector);
                        if (descEl && descEl.textContent.trim()) {
                            result.description = descEl.textContent.trim().substring(0, 100);
                            break;
                        }
                    }
                    
                    // Buscar imagen
                    const imgEl = element.querySelector('img');
                    if (imgEl) {
                        result.image = imgEl.src || imgEl.getAttribute('data-src') || '';
                    }
                    
                    return result;
                }
                
                // Función para manejar hover
                function handleMouseOver(event) {
                    if (!window.interactiveSelectionActive) return;
                    
                    // Remover highlight anterior
                    document.querySelectorAll('.tellectus-highlight').forEach(el => {
                        el.classList.remove('tellectus-highlight');
                    });
                    
                    // Añadir highlight al elemento actual
                    event.target.classList.add('tellectus-highlight');
                }
                
                // Función para manejar clic
                function handleClick(event) {
                    if (!window.interactiveSelectionActive) return;
                    
                    event.preventDefault();
                    event.stopPropagation();
                    
                    const element = event.target;
                    const data = extractElementData(element);
                    
                    // Verificar si ya está seleccionado
                    const isAlreadySelected = window.selectedElements.some(selected => 
                        selected.selector === data.selector
                    );
                    
                    if (!isAlreadySelected) {
                        window.selectedElements.push(data);
                        element.classList.add('tellectus-selected');
                        console.log('Tellectus Scraping: Elemento añadido:', data);
                        console.log('Tellectus Scraping: Total elementos seleccionados:', window.selectedElements.length);
                        
                        // Notificar al panel de Python automáticamente
                        window.tellectusElementSelected = true;
                        console.log('Tellectus Scraping: Flag tellectusElementSelected establecida a true');
                    } else {
                        // Remover si ya está seleccionado
                        window.selectedElements = window.selectedElements.filter(selected => 
                            selected.selector !== data.selector
                        );
                        element.classList.remove('tellectus-selected');
                        console.log('Tellectus Scraping: Elemento removido:', data);
                        console.log('Tellectus Scraping: Total elementos seleccionados:', window.selectedElements.length);
                        
                        // Notificar al panel de Python automáticamente
                        window.tellectusElementSelected = true;
                        console.log('Tellectus Scraping: Flag tellectusElementSelected establecida a true');
                    }
                }
                
                // Función para manejar tecla ESPACIO (subir al padre)
                function handleKeyDown(event) {
                    if (!window.interactiveSelectionActive) return;
                    
                    if (event.code === 'Space') {
                        event.preventDefault();
                        
                        // Remover highlight actual
                        document.querySelectorAll('.tellectus-highlight').forEach(el => {
                            el.classList.remove('tellectus-highlight');
                        });
                        
                        // Subir al elemento padre
                        const currentHighlighted = document.querySelector('.tellectus-highlight');
                        if (currentHighlighted && currentHighlighted.parentElement) {
                            currentHighlighted.parentElement.classList.add('tellectus-highlight');
                        }
                    }
                }
                
                // Función de limpieza
                window.tellectusCleanupFunction = function() {
                    console.log('Tellectus Scraping: Limpiando eventos anteriores...');
                    document.removeEventListener('mouseover', handleMouseOver, true);
                    document.removeEventListener('click', handleClick, true);
                    document.removeEventListener('keydown', handleKeyDown, true);
                    document.body.style.cursor = '';
                    
                    // Limpiar highlights
                    document.querySelectorAll('.tellectus-highlight, .tellectus-selected').forEach(el => {
                        el.classList.remove('tellectus-highlight', 'tellectus-selected');
                    });
                };
                
                // API global
                window.toggleInteractiveSelection = function(active) {
                    console.log('Tellectus Scraping: toggleInteractiveSelection called with:', active);
                    window.interactiveSelectionActive = active;
                    
                    // Limpiar eventos anteriores
                    window.tellectusCleanupFunction();
                    
                    if (active) {
                        document.addEventListener('mouseover', handleMouseOver, true);
                        document.addEventListener('click', handleClick, true);
                        document.addEventListener('keydown', handleKeyDown, true);
                        document.body.style.cursor = 'crosshair';
                        console.log('Tellectus Scraping: Selección interactiva ACTIVADA');
                    } else {
                        console.log('Tellectus Scraping: Selección interactiva DESACTIVADA');
                    }
                };
                
                window.getSelectedElements = function() {
                    console.log('Tellectus Scraping: getSelectedElements called, count:', window.selectedElements ? window.selectedElements.length : 0);
                    const elements = window.selectedElements ? window.selectedElements.slice() : [];
                    console.log('Tellectus Scraping: Returning elements:', elements);
                    return JSON.stringify(elements); // Devolver como JSON string para evitar problemas de serialización
                };
                
                window.clearSelectedElements = function() {
                    console.log('Tellectus Scraping: clearSelectedElements called');
                    window.selectedElements = [];
                    document.querySelectorAll('.tellectus-selected').forEach(el => {
                        el.classList.remove('tellectus-selected');
                    });
                    // Resetear flag de elementos seleccionados
                    window.tellectusElementSelected = false;
                };
                
                console.log('Tellectus Scraping Content Script inyectado correctamente');
            })();
            """
            
            # Inyectar el script y verificar que se ejecutó correctamente
            self.browser_tab.page().runJavaScript(content_script, self._on_script_injected)
            return True
            
        except Exception as e:
            print(f"❌ Error inyectando content script: {e}")
            return False
    
    def _on_script_injected(self, result):
        """Callback cuando se inyecta el script"""
        try:
            print("✅ Content script inyectado correctamente")
            
            # Verificar que el script se inyectó correctamente
            verify_js = "window.tellectusScrapingInjected || false;"
            self.browser_tab.page().runJavaScript(verify_js, self._on_script_verified)
            
        except Exception as e:
            print(f"❌ Error en callback de inyección: {e}")
    
    def _on_script_verified(self, is_injected):
        """Verificar que el script se inyectó correctamente"""
        if is_injected:
            print("✅ Content script verificado y funcionando")
        else:
            print("❌ Content script no se inyectó correctamente")
            QMessageBox.warning(self, "Advertencia", 
                "⚠️ El script de selección no se pudo inyectar correctamente.\n\n"
                "Esto puede deberse a:\n"
                "• Políticas de seguridad de la página\n"
                "• Página aún cargando\n"
                "• Problemas de permisos JavaScript\n\n"
                "Intenta recargar la página y volver a activar la selección.")
    
    def _ensure_browser_connection(self):
        """Verificar y establecer conexión con el navegador"""
        try:
            # Si ya tenemos una conexión válida, verificarla
            if hasattr(self, 'browser_tab') and self.browser_tab:
                try:
                    # Probar si podemos ejecutar JavaScript
                    test_js = "true;"
                    self.browser_tab.page().runJavaScript(test_js)
                    print("✅ Conexión con navegador verificada")
                    return True
                except Exception as e:
                    print(f"❌ Conexión con navegador inválida: {e}")
            
            # Intentar obtener la pestaña actual del navegador
            try:
                # Buscar la ventana principal
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
                main_window = None
                
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'tab_manager'):
                        main_window = widget
                        break
                
                if main_window and hasattr(main_window, 'tab_manager'):
                    current_browser = main_window.tab_manager.tabs.currentWidget()
                    if current_browser:
                        self.browser_tab = current_browser
                        print("✅ Conexión con navegador restablecida")
                        return True
                
            except Exception as e:
                print(f"❌ Error obteniendo pestaña del navegador: {e}")
            
            print("❌ No se pudo establecer conexión con el navegador")
            return False
            
        except Exception as e:
            print(f"❌ Error verificando conexión del navegador: {e}")
            return False
    
    def _start_auto_sync(self):
        """Iniciar sincronización automática de elementos seleccionados"""
        try:
            from PySide6.QtCore import QTimer
            
            # Crear timer para verificar elementos seleccionados cada 500ms
            if not hasattr(self, 'auto_sync_timer'):
                self.auto_sync_timer = QTimer()
                self.auto_sync_timer.timeout.connect(self._check_and_sync_elements)
            
            self.auto_sync_timer.start(500)  # Verificar cada 500ms
            print("✅ Sincronización automática iniciada")
            
        except Exception as e:
            print(f"❌ Error iniciando sincronización automática: {e}")
    
    def _stop_auto_sync(self):
        """Detener sincronización automática"""
        try:
            if hasattr(self, 'auto_sync_timer') and self.auto_sync_timer:
                self.auto_sync_timer.stop()
                print("⏹️ Sincronización automática detenida")
        except Exception as e:
            print(f"❌ Error deteniendo sincronización automática: {e}")
    
    def _check_and_sync_elements(self):
        """Verificar si hay elementos seleccionados en JavaScript y sincronizarlos"""
        try:
            if not hasattr(self, 'browser_tab') or not self.browser_tab:
                return
            
            # Verificar si hay elementos seleccionados
            check_js = "window.tellectusElementSelected || false;"
            self.browser_tab.page().runJavaScript(check_js, self._handle_sync_check)
            
        except Exception as e:
            print(f"❌ Error verificando elementos: {e}")
    
    def _handle_sync_check(self, has_new_elements):
        """Manejar el resultado de la verificación de sincronización"""
        try:
            print(f"[DEBUG] _handle_sync_check llamado con: {has_new_elements}")
            if has_new_elements:
                print("[DEBUG] Elementos nuevos detectados, iniciando sincronización...")
                # Resetear la flag
                reset_js = "window.tellectusElementSelected = false;"
                self.browser_tab.page().runJavaScript(reset_js)
                
                # Marcar que es sincronización automática
                self._auto_sync_active = True
                
                # Sincronizar elementos
                self.sync_javascript_elements()
                
                # Resetear flag
                self._auto_sync_active = False
                
                print("🔄 Elementos sincronizados automáticamente")
            else:
                print("[DEBUG] No hay elementos nuevos para sincronizar")
                
        except Exception as e:
            print(f"❌ Error manejando sincronización: {e}")
    
    def run_diagnostics(self):
        """Ejecutar diagnóstico del sistema de selección interactiva"""
        try:
            diagnostic_info = []
            
            # 1. Verificar conexión del navegador
            diagnostic_info.append("🔍 DIAGNÓSTICO DEL SISTEMA DE SELECCIÓN\n")
            
            if hasattr(self, 'browser_tab') and self.browser_tab:
                diagnostic_info.append("✅ Browser tab: Conectado")
                
                # Verificar URL
                try:
                    current_url = self.browser_tab.url().toString()
                    diagnostic_info.append(f"✅ URL actual: {current_url}")
                except:
                    diagnostic_info.append("❌ URL: No se pudo obtener")
                
                # Verificar JavaScript
                try:
                    test_js = "typeof window !== 'undefined';"
                    self.browser_tab.page().runJavaScript(test_js, 
                        lambda result: self._diagnostic_js_test(result, diagnostic_info))
                except Exception as e:
                    diagnostic_info.append(f"❌ JavaScript: Error - {e}")
            else:
                diagnostic_info.append("❌ Browser tab: No conectado")
                diagnostic_info.append("💡 Solución: Abre una pestaña en el navegador")
            
            # 2. Verificar estado del script
            if hasattr(self, 'browser_tab') and self.browser_tab:
                check_script_js = "window.tellectusScrapingInjected || false;"
                self.browser_tab.page().runJavaScript(check_script_js, 
                    lambda result: self._diagnostic_script_test(result, diagnostic_info))
            
            # 3. Verificar estado de selección
            if hasattr(self, 'interactive_selection_active'):
                if self.interactive_selection_active:
                    diagnostic_info.append("✅ Selección interactiva: Activada")
                else:
                    diagnostic_info.append("ℹ️ Selección interactiva: Desactivada")
            else:
                diagnostic_info.append("❌ Selección interactiva: Estado desconocido")
            
            # 4. Verificar elementos seleccionados
            selected_count = len(self.scraping_integration.get_selected_elements())
            diagnostic_info.append(f"ℹ️ Elementos seleccionados: {selected_count}")
            
            # Mostrar diagnóstico inicial
            self._show_diagnostic_results(diagnostic_info)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error ejecutando diagnóstico: {str(e)}")
    
    def _diagnostic_js_test(self, result, diagnostic_info):
        """Callback para test de JavaScript"""
        if result:
            diagnostic_info.append("✅ JavaScript: Funcionando")
        else:
            diagnostic_info.append("❌ JavaScript: No disponible")
        
        self._show_diagnostic_results(diagnostic_info)
    
    def _diagnostic_script_test(self, result, diagnostic_info):
        """Callback para test del script"""
        if result:
            diagnostic_info.append("✅ Content script: Inyectado")
            
            # Verificar funciones específicas
            check_functions_js = """
            (function() {
                return {
                    toggleFunction: typeof window.toggleInteractiveSelection === 'function',
                    getFunction: typeof window.getSelectedElements === 'function',
                    clearFunction: typeof window.clearSelectedElements === 'function'
                };
            })();
            """
            self.browser_tab.page().runJavaScript(check_functions_js, 
                lambda result: self._diagnostic_functions_test(result, diagnostic_info))
        else:
            diagnostic_info.append("❌ Content script: No inyectado")
            diagnostic_info.append("💡 Solución: Activa la selección interactiva para inyectar el script")
        
        self._show_diagnostic_results(diagnostic_info)
    
    def _diagnostic_functions_test(self, result, diagnostic_info):
        """Callback para test de funciones"""
        if result:
            if result.get('toggleFunction'):
                diagnostic_info.append("✅ Función toggle: Disponible")
            else:
                diagnostic_info.append("❌ Función toggle: No disponible")
            
            if result.get('getFunction'):
                diagnostic_info.append("✅ Función get: Disponible")
            else:
                diagnostic_info.append("❌ Función get: No disponible")
            
            if result.get('clearFunction'):
                diagnostic_info.append("✅ Función clear: Disponible")
            else:
                diagnostic_info.append("❌ Función clear: No disponible")
        
        self._show_diagnostic_results(diagnostic_info)
    
    def _show_diagnostic_results(self, diagnostic_info):
        """Mostrar resultados del diagnóstico"""
        diagnostic_text = "\n".join(diagnostic_info)
        diagnostic_text += "\n\n🔧 RECOMENDACIONES:\n"
        diagnostic_text += "• Si hay errores de conexión: Recarga la página\n"
        diagnostic_text += "• Si JavaScript no funciona: Verifica permisos\n"
        diagnostic_text += "• Si el script no se inyecta: Activa/desactiva la selección\n"
        diagnostic_text += "• Si persisten problemas: Reinicia el navegador"
        
        QMessageBox.information(self, "Diagnóstico del Sistema", diagnostic_text)
    
    def test_html_extraction(self):
        """Probar extracción de HTML directamente desde la página"""
        try:
            if not hasattr(self, 'browser_tab') or not self.browser_tab:
                QMessageBox.warning(self, "Error", "No hay conexión con el navegador")
                return
            
            # Test JavaScript para extraer elementos de productos
            test_js = """
            (function() {
                // Buscar elementos que parezcan productos
                const productElements = [];
                
                // Selectores comunes para productos
                const productSelectors = [
                    '[class*="product"]',
                    '[class*="item"]',
                    '[class*="card"]',
                    'article',
                    '.tile',
                    '[data-testid*="product"]'
                ];
                
                for (const selector of productSelectors) {
                    const elements = document.querySelectorAll(selector);
                    for (const element of elements) {
                        // Verificar si contiene información de producto
                        const hasPrice = element.querySelector('[class*="price"], [class*="precio"], [class*="cost"]');
                        const hasTitle = element.querySelector('h1, h2, h3, h4, [class*="title"], [class*="name"]');
                        
                        if (hasPrice || hasTitle) {
                            productElements.push({
                                selector: selector,
                                html: element.outerHTML.substring(0, 500) + '...',
                                text: element.textContent.trim().substring(0, 200),
                                hasPrice: !!hasPrice,
                                hasTitle: !!hasTitle,
                                priceText: hasPrice ? hasPrice.textContent.trim() : '',
                                titleText: hasTitle ? hasTitle.textContent.trim() : ''
                            });
                        }
                    }
                }
                
                return {
                    totalElements: productElements.length,
                    elements: productElements.slice(0, 5), // Solo los primeros 5
                    pageTitle: document.title,
                    url: window.location.href
                };
            })();
            """
            
            self.browser_tab.page().runJavaScript(test_js, self._show_extraction_test_results)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error en test de extracción: {str(e)}")
    
    def _show_extraction_test_results(self, results):
        """Mostrar resultados del test de extracción"""
        try:
            if not results:
                QMessageBox.information(self, "Test de Extracción", 
                    "❌ No se pudieron obtener resultados del test")
                return
            
            result_text = f"🧪 TEST DE EXTRACCIÓN DE HTML\n\n"
            result_text += f"📄 Página: {results.get('pageTitle', 'Sin título')}\n"
            result_text += f"🔗 URL: {results.get('url', 'Sin URL')}\n"
            result_text += f"📦 Elementos encontrados: {results.get('totalElements', 0)}\n\n"
            
            elements = results.get('elements', [])
            if elements:
                result_text += "🎯 ELEMENTOS DE EJEMPLO:\n\n"
                for i, element in enumerate(elements, 1):
                    result_text += f"--- Elemento {i} ---\n"
                    result_text += f"Selector: {element.get('selector', 'N/A')}\n"
                    result_text += f"Tiene precio: {'✅' if element.get('hasPrice') else '❌'}\n"
                    result_text += f"Tiene título: {'✅' if element.get('hasTitle') else '❌'}\n"
                    
                    if element.get('titleText'):
                        result_text += f"Título: {element['titleText'][:50]}...\n"
                    if element.get('priceText'):
                        result_text += f"Precio: {element['priceText']}\n"
                    
                    result_text += f"Texto: {element.get('text', '')[:100]}...\n\n"
            else:
                result_text += "❌ No se encontraron elementos de productos en la página\n"
                result_text += "\n💡 SUGERENCIAS:\n"
                result_text += "• Navega a una página de productos\n"
                result_text += "• Verifica que la página haya cargado completamente\n"
                result_text += "• Intenta con una tienda online diferente"
            
            QMessageBox.information(self, "Resultados del Test", result_text)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error mostrando resultados: {str(e)}")
    
    def debug_javascript_state(self):
        """Método de debug para verificar el estado del JavaScript"""
        try:
            if not hasattr(self, 'browser_tab') or not self.browser_tab:
                print("[DEBUG] No hay browser_tab disponible")
                return
            
            debug_js = """
            (function() {
                return {
                    scriptInjected: !!window.tellectusScrapingInjected,
                    interactiveActive: !!window.interactiveSelectionActive,
                    selectedElementsExists: !!window.selectedElements,
                    selectedElementsLength: window.selectedElements ? window.selectedElements.length : 0,
                    tellectusElementSelectedFlag: !!window.tellectusElementSelected,
                    functionsAvailable: {
                        toggleInteractiveSelection: typeof window.toggleInteractiveSelection === 'function',
                        getSelectedElements: typeof window.getSelectedElements === 'function',
                        clearSelectedElements: typeof window.clearSelectedElements === 'function'
                    }
                };
            })();
            """
            
            self.browser_tab.page().runJavaScript(debug_js, self._show_debug_state)
            
        except Exception as e:
            print(f"[ERROR] Error en debug JavaScript: {e}")
    
    def _show_debug_state(self, debug_info):
        """Mostrar información de debug del estado JavaScript"""
        print(f"[DEBUG] Estado JavaScript: {debug_info}")
        if debug_info:
            print(f"  - Script inyectado: {debug_info.get('scriptInjected', False)}")
            print(f"  - Selección activa: {debug_info.get('interactiveActive', False)}")
            print(f"  - Array selectedElements existe: {debug_info.get('selectedElementsExists', False)}")
            print(f"  - Elementos seleccionados: {debug_info.get('selectedElementsLength', 0)}")
            print(f"  - Flag tellectusElementSelected: {debug_info.get('tellectusElementSelectedFlag', False)}")
            functions = debug_info.get('functionsAvailable', {})
            print(f"  - Funciones disponibles: {functions}")
        else:
            print("  - No se pudo obtener información de debug")

    @requires_premium("scraping", "export")
    def run_export(self):
        """Exportar datos seleccionados"""
        try:
            if not hasattr(self, 'scraping_integration') or not self.scraping_integration:
                QMessageBox.warning(self, "Error", "Sistema de scraping no disponible")
                return
            
            # Obtener formato seleccionado
            format_type = self.export_format.currentText().lower()
            filename = self.export_filename.text().strip()
            
            if not filename:
                filename = f"scraped_data_{int(time.time())}"
            
            # Obtener datos seleccionados
            selected_data = self.scraping_integration.get_selected_elements()
            
            if not selected_data:
                QMessageBox.warning(self, "Error", "No hay datos seleccionados para exportar")
                return
            
            # Exportar según el formato
            if format_type == "csv":
                self.scraping_integration.export_to_csv(selected_data, f"{filename}.csv")
            elif format_type == "excel":
                self.scraping_integration.export_to_excel(selected_data, f"{filename}.xlsx")
            elif format_type == "json":
                self.scraping_integration.export_to_json(selected_data, f"{filename}.json")
            elif format_type == "yaml":
                self.scraping_integration.export_to_yaml(selected_data, f"{filename}.yaml")
            
            QMessageBox.information(self, "Éxito", f"Datos exportados exitosamente a {filename}.{format_type}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error exportando datos: {str(e)}")