#!/usr/bin/env python3
"""
SEO Analyzer Pro - Main UI Panel
Panel completo con 17 tabs funcionales
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QScrollArea, QFrame, QLineEdit,
    QComboBox, QSpinBox, QCheckBox, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QThread
from PySide6.QtGui import QFont, QColor
import sys
import os
from typing import Dict, Any, Optional

# Add parent directory to path
plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from core.analysis_coordinator import AnalysisCoordinator
from core.tier_manager import TierManager
from exporters.json_exporter import JSONExporter
from exporters.csv_exporter import CSVExporter
from exporters.pdf_exporter import PDFExporter


class AnalysisWorker(QThread):
    """Worker thread for running analysis"""
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, coordinator, html, url):
        super().__init__()
        self.coordinator = coordinator
        self.html = html
        self.url = url
    
    def run(self):
        try:
            results = self.coordinator.analyze(self.html, self.url)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class SEOAnalyzerPanel(QWidget):
    """Panel principal de SEO Analyzer Pro con 17 tabs funcionales"""
    
    analysis_requested = Signal(str)
    
    def __init__(self, parent=None, coordinator=None, tier_manager=None):
        super().__init__(parent)
        self.parent = parent
        self.tier_manager = tier_manager or TierManager("free")
        self.coordinator = coordinator or AnalysisCoordinator(tier_manager=self.tier_manager)
        self.current_results = {}
        self.current_url = ""
        self.current_html = ""
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Tab widget for different sections
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        
        # Create all 17 tabs
        self.tabs.addTab(self._create_dashboard_tab(), "📊 Dashboard")
        self.tabs.addTab(self._create_meta_tab(), "🏷️ Meta Tags")
        self.tabs.addTab(self._create_heading_tab(), "📑 Headings")
        self.tabs.addTab(self._create_image_tab(), "🖼️ Imágenes")
        self.tabs.addTab(self._create_link_tab(), "🔗 Enlaces")
        self.tabs.addTab(self._create_performance_tab(), "⚡ Rendimiento")
        self.tabs.addTab(self._create_schema_tab(), "📊 Schema")
        self.tabs.addTab(self._create_accessibility_tab(), "♿ Accesibilidad")
        self.tabs.addTab(self._create_content_tab(), "📝 Contenido")
        self.tabs.addTab(self._create_mobile_tab(), "📱 Mobile")
        self.tabs.addTab(self._create_security_tab(), "🔒 Seguridad")
        self.tabs.addTab(self._create_social_tab(), "📲 Redes Sociales")
        self.tabs.addTab(self._create_technical_tab(), "🔧 Técnico")
        self.tabs.addTab(self._create_recommendations_tab(), "💡 Recomendaciones")
        self.tabs.addTab(self._create_history_tab(), "📈 Historial")
        self.tabs.addTab(self._create_export_tab(), "💾 Exportar")
        self.tabs.addTab(self._create_settings_tab(), "⚙️ Configuración")
        
        layout.addWidget(self.tabs)
        
        # Status bar
        self.status_label = QLabel("✅ Listo para analizar")
        self.status_label.setStyleSheet("padding: 8px; background-color: #e8f5e9; border-radius: 4px; color: #2e7d32;")
        layout.addWidget(self.status_label)
    
    def _create_header(self):
        """Create header with title and analyze button"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e88e5, stop:1 #1565c0);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        layout = QVBoxLayout(header)
        
        # Title row
        title_layout = QHBoxLayout()
        title = QLabel("🔍 SEO Analyzer Pro")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        title_layout.addWidget(title)
        
        tier_badge = QLabel(f"{self.tier_manager.get_tier().upper()}")
        tier_badge.setStyleSheet("""
            background-color: #ffd700;
            color: #000;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 12px;
        """)
        tier_badge.setFixedHeight(24)
        title_layout.addWidget(tier_badge)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # URL input and analyze button
        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Ingresa la URL a analizar o usa la página actual...")
        self.url_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid white;
                border-radius: 6px;
                background-color: rgba(255,255,255,0.9);
                font-size: 14px;
            }
        """)
        input_layout.addWidget(self.url_input, 4)
        
        self.analyze_btn = QPushButton("🚀 Analizar")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #43a047;
                color: white;
                padding: 10px 24px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:pressed {
                background-color: #2e7d32;
            }
            QPushButton:disabled {
                background-color: #9e9e9e;
            }
        """)
        self.analyze_btn.clicked.connect(self.start_analysis)
        input_layout.addWidget(self.analyze_btn, 1)
        
        layout.addLayout(input_layout)
        
        return header
    
    def _create_dashboard_tab(self):
        """Tab 1: Dashboard general"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Score cards
        scores_layout = QHBoxLayout()
        
        self.overall_score_label = QLabel("--")
        self.overall_score_label.setAlignment(Qt.AlignCenter)
        self.overall_score_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #1976d2;")
        
        score_card = self._create_card("Puntuación General", self.overall_score_label)
        scores_layout.addWidget(score_card)
        
        # Issues summary
        self.issues_widget = QWidget()
        issues_layout = QVBoxLayout(self.issues_widget)
        self.critical_label = QLabel("0 Críticos")
        self.critical_label.setStyleSheet("color: #d32f2f; font-size: 16px; font-weight: bold;")
        self.warnings_label = QLabel("0 Advertencias")
        self.warnings_label.setStyleSheet("color: #f57c00; font-size: 16px; font-weight: bold;")
        self.info_label = QLabel("0 Info")
        self.info_label.setStyleSheet("color: #1976d2; font-size: 16px; font-weight: bold;")
        issues_layout.addWidget(self.critical_label)
        issues_layout.addWidget(self.warnings_label)
        issues_layout.addWidget(self.info_label)
        
        issues_card = self._create_card("Issues Detectados", self.issues_widget)
        scores_layout.addWidget(issues_card)
        
        layout.addLayout(scores_layout)
        
        # Analyzer scores table
        self.scores_table = QTableWidget()
        self.scores_table.setColumnCount(3)
        self.scores_table.setHorizontalHeaderLabels(["Analyzer", "Score", "Status"])
        self.scores_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.scores_table)
        
        layout.addStretch()
        return widget
    
    def _create_meta_tab(self):
        """Tab 2: Meta Tags Analysis"""
        return self._create_analyzer_tab("meta", "Meta Tags")
    
    def _create_heading_tab(self):
        """Tab 3: Headings Analysis"""
        return self._create_analyzer_tab("heading", "Headings")
    
    def _create_image_tab(self):
        """Tab 4: Images Analysis"""
        return self._create_analyzer_tab("image", "Imágenes")
    
    def _create_link_tab(self):
        """Tab 5: Links Analysis"""
        return self._create_analyzer_tab("link", "Enlaces")
    
    def _create_performance_tab(self):
        """Tab 6: Performance Analysis"""
        return self._create_analyzer_tab("performance", "Rendimiento")
    
    def _create_schema_tab(self):
        """Tab 7: Schema Markup Analysis"""
        return self._create_analyzer_tab("schema", "Schema Markup")
    
    def _create_accessibility_tab(self):
        """Tab 8: Accessibility Analysis"""
        return self._create_analyzer_tab("accessibility", "Accesibilidad")
    
    def _create_content_tab(self):
        """Tab 9: Content Analysis"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("📝 Análisis de Contenido")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Content metrics
        self.content_metrics = QTextEdit()
        self.content_metrics.setReadOnly(True)
        self.content_metrics.setPlaceholderText("Métricas de contenido aparecerán aquí después del análisis...")
        layout.addWidget(self.content_metrics)
        
        return widget
    
    def _create_mobile_tab(self):
        """Tab 10: Mobile Optimization"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("📱 Optimización Mobile")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.mobile_analysis = QTextEdit()
        self.mobile_analysis.setReadOnly(True)
        self.mobile_analysis.setPlaceholderText("Análisis mobile aparecerá aquí...")
        layout.addWidget(self.mobile_analysis)
        
        return widget
    
    def _create_security_tab(self):
        """Tab 11: Security"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("🔒 Seguridad")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.security_analysis = QTextEdit()
        self.security_analysis.setReadOnly(True)
        self.security_analysis.setPlaceholderText("Análisis de seguridad aparecerá aquí...")
        layout.addWidget(self.security_analysis)
        
        return widget
    
    def _create_social_tab(self):
        """Tab 12: Social Media"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("📲 Redes Sociales")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.social_analysis = QTextEdit()
        self.social_analysis.setReadOnly(True)
        self.social_analysis.setPlaceholderText("Análisis de redes sociales aparecerá aquí...")
        layout.addWidget(self.social_analysis)
        
        return widget
    
    def _create_technical_tab(self):
        """Tab 13: Technical SEO"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("🔧 SEO Técnico")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.technical_analysis = QTextEdit()
        self.technical_analysis.setReadOnly(True)
        self.technical_analysis.setPlaceholderText("Análisis técnico aparecerá aquí...")
        layout.addWidget(self.technical_analysis)
        
        return widget
    
    def _create_recommendations_tab(self):
        """Tab 14: Recommendations"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("💡 Recomendaciones Priorizadas")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.recommendations_list = QTextEdit()
        self.recommendations_list.setReadOnly(True)
        self.recommendations_list.setPlaceholderText("Las recomendaciones aparecerán aquí después del análisis...")
        layout.addWidget(self.recommendations_list)
        
        return widget
    
    def _create_history_tab(self):
        """Tab 15: Analysis History"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("📈 Historial de Análisis")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Fecha", "URL", "Score", "Acciones"])
        layout.addWidget(self.history_table)
        
        return widget
    
    def _create_export_tab(self):
        """Tab 16: Export Results"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("💾 Exportar Resultados")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Export format selection
        format_group = QGroupBox("Formato de Exportación")
        format_layout = QVBoxLayout()
        
        export_btns_layout = QHBoxLayout()
        
        self.export_json_btn = QPushButton("📄 Exportar JSON")
        self.export_json_btn.clicked.connect(lambda: self.export_results("json"))
        export_btns_layout.addWidget(self.export_json_btn)
        
        self.export_csv_btn = QPushButton("📊 Exportar CSV")
        self.export_csv_btn.clicked.connect(lambda: self.export_results("csv"))
        export_btns_layout.addWidget(self.export_csv_btn)
        
        self.export_pdf_btn = QPushButton("📕 Exportar PDF")
        self.export_pdf_btn.clicked.connect(lambda: self.export_results("pdf"))
        export_btns_layout.addWidget(self.export_pdf_btn)
        
        format_layout.addLayout(export_btns_layout)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        self.export_status = QLabel("")
        layout.addWidget(self.export_status)
        
        layout.addStretch()
        return widget
    
    def _create_settings_tab(self):
        """Tab 17: Settings"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        title = QLabel("⚙️ Configuración")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Tier info
        tier_group = QGroupBox("Información de Suscripción")
        tier_layout = QVBoxLayout()
        tier_layout.addWidget(QLabel(f"Tier actual: {self.tier_manager.get_tier().upper()}"))
        tier_layout.addWidget(QLabel(f"Analyzers disponibles: {len(self.coordinator.get_available_analyzers())}"))
        tier_group.setLayout(tier_layout)
        layout.addWidget(tier_group)
        
        layout.addStretch()
        return widget
    
    def _create_analyzer_tab(self, analyzer_name: str, title: str):
        """Create a tab for a specific analyzer"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Title
        title_label = QLabel(f"📊 {title}")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Score display
        score_widget = QWidget()
        score_layout = QHBoxLayout(score_widget)
        score_label = QLabel("Score:")
        score_layout.addWidget(score_label)
        
        score_value = QLabel("--/100")
        score_value.setObjectName(f"{analyzer_name}_score")
        score_value.setStyleSheet("font-size: 24px; font-weight: bold; color: #1976d2;")
        score_layout.addWidget(score_value)
        score_layout.addStretch()
        layout.addWidget(score_widget)
        
        # Issues table
        issues_table = QTableWidget()
        issues_table.setObjectName(f"{analyzer_name}_table")
        issues_table.setColumnCount(3)
        issues_table.setHorizontalHeaderLabels(["Tipo", "Mensaje", "Elemento"])
        issues_table.horizontalHeader().setStretchLastSection(True)
        issues_table.setAlternatingRowColors(True)
        layout.addWidget(issues_table)
        
        # Recommendations
        rec_label = QLabel("💡 Recomendaciones:")
        rec_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(rec_label)
        
        rec_text = QTextEdit()
        rec_text.setObjectName(f"{analyzer_name}_recommendations")
        rec_text.setReadOnly(True)
        rec_text.setMaximumHeight(100)
        layout.addWidget(rec_text)
        
        return widget
    
    def _create_card(self, title: str, content_widget: QWidget):
        """Create a card widget"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; color: #666; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        layout.addWidget(content_widget)
        
        return card
    
    def _connect_signals(self):
        """Connect signals"""
        pass
    
    def start_analysis(self):
        """Start SEO analysis"""
        # Get URL
        url = self.url_input.text().strip()
        if not url and self.parent and hasattr(self.parent, 'tab_widget'):
            # Get current tab URL
            current_tab = self.parent.tab_widget.get_current_tab()
            if current_tab:
                url = current_tab.url().toString()
        
        if not url:
            self.status_label.setText("⚠️ Por favor ingresa una URL")
            self.status_label.setStyleSheet("padding: 8px; background-color: #fff3e0; border-radius: 4px; color: #e65100;")
            return
        
        self.current_url = url
        self.url_input.setText(url)
        
        # Update status
        self.status_label.setText(f"🔄 Obteniendo HTML de {url}...")
        self.status_label.setStyleSheet("padding: 8px; background-color: #e3f2fd; border-radius: 4px; color: #1565c0;")
        self.analyze_btn.setEnabled(False)
        
        # Get REAL HTML content from current tab
        if self.parent and hasattr(self.parent, 'tab_widget'):
            current_tab = self.parent.tab_widget.get_current_tab()
            if current_tab and hasattr(current_tab, 'page'):
                # Get HTML asynchronously
                current_tab.page().toHtml(self._on_html_received)
                return
        
        # Fallback: use requests to fetch HTML
        self._fetch_html_with_requests(url)
    
    def _on_html_received(self, html: str):
        """Callback when HTML is received from browser"""
        self.current_html = html
        self.status_label.setText(f"🔄 Analizando {self.current_url}...")
        
        # Run analysis in thread
        self.worker = AnalysisWorker(self.coordinator, self.current_html, self.current_url)
        self.worker.finished.connect(self.on_analysis_finished)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.start()
    
    def _fetch_html_with_requests(self, url: str):
        """Fetch HTML using requests as fallback"""
        try:
            import requests
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            self.current_html = response.text
            self.status_label.setText(f"🔄 Analizando {url}...")
            
            # Run analysis
            self.worker = AnalysisWorker(self.coordinator, self.current_html, self.current_url)
            self.worker.finished.connect(self.on_analysis_finished)
            self.worker.error.connect(self.on_analysis_error)
            self.worker.start()
        except Exception as e:
            self.analyze_btn.setEnabled(True)
            self.status_label.setText(f"❌ Error obteniendo HTML: {str(e)}")
            self.status_label.setStyleSheet("padding: 8px; background-color: #ffebee; border-radius: 4px; color: #c62828;")
            QMessageBox.critical(self, "Error", f"No se pudo obtener el HTML:\n{str(e)}")
    
    @Slot(dict)
    def on_analysis_finished(self, results: Dict[str, Any]):
        """Handle analysis completion"""
        self.current_results = results
        self.analyze_btn.setEnabled(True)
        
        # Update dashboard
        overall = results.get("overall", {})
        score = overall.get("score", 0)
        self.overall_score_label.setText(f"{score}")
        
        # Update score color
        if score >= 80:
            color = "#4caf50"
        elif score >= 60:
            color = "#ff9800"
        else:
            color = "#f44336"
        self.overall_score_label.setStyleSheet(f"font-size: 48px; font-weight: bold; color: {color};")
        
        # Update issues summary
        summary = self.coordinator.get_summary()
        self.critical_label.setText(f"{summary.get('critical_issues', 0)} Críticos")
        self.warnings_label.setText(f"{summary.get('warnings', 0)} Advertencias")
        self.info_label.setText(f"{summary.get('info', 0)} Info")
        
        # Update scores table
        self.scores_table.setRowCount(0)
        for analyzer_name, analyzer_results in results.items():
            if analyzer_name == "overall":
                continue
            
            row = self.scores_table.rowCount()
            self.scores_table.insertRow(row)
            
            info = self.coordinator.get_analyzer_info(analyzer_name)
            self.scores_table.setItem(row, 0, QTableWidgetItem(f"{info.get('icon', '🔍')} {info.get('name', analyzer_name)}"))
            self.scores_table.setItem(row, 1, QTableWidgetItem(f"{analyzer_results.get('score', 0)}/100"))
            
            severity = analyzer_results.get('severity', 'unknown')
            status_item = QTableWidgetItem(severity.upper())
            if severity == "success":
                status_item.setForeground(QColor("#4caf50"))
            elif severity == "warning":
                status_item.setForeground(QColor("#ff9800"))
            else:
                status_item.setForeground(QColor("#f44336"))
            self.scores_table.setItem(row, 2, status_item)
        
        self.scores_table.resizeColumnsToContents()
        
        # Update analyzer tabs
        for analyzer_name, analyzer_results in results.items():
            if analyzer_name == "overall":
                continue
            self._update_analyzer_tab(analyzer_name, analyzer_results)
        
        # Update recommendations
        recommendations = self.coordinator.get_recommendations()
        if recommendations:
            rec_text = "\n\n".join([f"• {rec}" for rec in recommendations])
            self.recommendations_list.setPlainText(rec_text)
        
        # Update additional tabs with real data
        self._update_additional_tabs(results)
        
        self.status_label.setText(f"✅ Análisis completado - Score: {score}/100")
        self.status_label.setStyleSheet("padding: 8px; background-color: #e8f5e9; border-radius: 4px; color: #2e7d32;")
    
    def _update_analyzer_tab(self, analyzer_name: str, results: Dict[str, Any]):
        """Update a specific analyzer tab with results"""
        # Update score
        score_label = self.findChild(QLabel, f"{analyzer_name}_score")
        if score_label:
            score = results.get("score", 0)
            score_label.setText(f"{score}/100")
            
            if score >= 80:
                color = "#4caf50"
            elif score >= 60:
                color = "#ff9800"
            else:
                color = "#f44336"
            score_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")
        
        # Update issues table
        issues_table = self.findChild(QTableWidget, f"{analyzer_name}_table")
        if issues_table:
            issues_table.setRowCount(0)
            for issue in results.get("issues", []):
                row = issues_table.rowCount()
                issues_table.insertRow(row)
                
                type_item = QTableWidgetItem(issue.get("type", "").upper())
                if issue.get("type") == "error":
                    type_item.setForeground(QColor("#f44336"))
                elif issue.get("type") == "warning":
                    type_item.setForeground(QColor("#ff9800"))
                else:
                    type_item.setForeground(QColor("#2196f3"))
                
                issues_table.setItem(row, 0, type_item)
                issues_table.setItem(row, 1, QTableWidgetItem(issue.get("message", "")))
                issues_table.setItem(row, 2, QTableWidgetItem(issue.get("element", "")))
            
            issues_table.resizeColumnsToContents()
        
        # Update recommendations
        rec_text = self.findChild(QTextEdit, f"{analyzer_name}_recommendations")
        if rec_text:
            recommendations = results.get("recommendations", [])
            if recommendations:
                rec_text.setPlainText("\n".join([f"• {rec}" for rec in recommendations]))
            else:
                rec_text.setPlainText("No hay recomendaciones específicas.")
    
    @Slot(str)
    def on_analysis_error(self, error: str):
        """Handle analysis error"""
        self.analyze_btn.setEnabled(True)
        self.status_label.setText(f"❌ Error: {error}")
        self.status_label.setStyleSheet("padding: 8px; background-color: #ffebee; border-radius: 4px; color: #c62828;")
        
        QMessageBox.critical(self, "Error de Análisis", f"Ocurrió un error durante el análisis:\n\n{error}")
    
    def export_results(self, format_type: str):
        """Export results to file"""
        if not self.current_results:
            QMessageBox.warning(self, "Sin Resultados", "No hay resultados para exportar. Ejecuta un análisis primero.")
            return
        
        # Check if format is available in tier
        if not self.tier_manager.can_export_format(format_type):
            QMessageBox.warning(
                self,
                "Formato No Disponible",
                f"El formato {format_type.upper()} no está disponible en tu tier actual.\n\nActualiza tu suscripción para desbloquear más formatos."
            )
            return
        
        # Get filename
        filters = {
            "json": "JSON Files (*.json)",
            "csv": "CSV Files (*.csv)",
            "pdf": "PDF Files (*.pdf)"
        }
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Análisis",
            f"seo_analysis_{self.current_url.replace('://', '_').replace('/', '_')}.{format_type}",
            filters.get(format_type, "All Files (*.*)")
        )
        
        if not filename:
            return
        
        # Export
        try:
            success = False
            if format_type == "json":
                exporter = JSONExporter()
                success = exporter.export(self.current_results, self.current_url, filename)
            elif format_type == "csv":
                exporter = CSVExporter()
                success = exporter.export(self.current_results, self.current_url, filename)
            elif format_type == "pdf":
                exporter = PDFExporter()
                if exporter.is_available():
                    success = exporter.export(self.current_results, self.current_url, filename)
                else:
                    QMessageBox.warning(self, "PDF No Disponible", "La exportación PDF requiere la librería ReportLab.")
                    return
            
            if success:
                self.export_status.setText(f"✅ Exportado correctamente: {filename}")
                self.export_status.setStyleSheet("color: green; padding: 10px;")
                QMessageBox.information(self, "Éxito", f"Resultados exportados correctamente a:\n{filename}")
            else:
                self.export_status.setText("❌ Error al exportar")
                self.export_status.setStyleSheet("color: red; padding: 10px;")
                QMessageBox.critical(self, "Error", "Ocurrió un error al exportar los resultados.")
        
        except Exception as e:
            self.export_status.setText(f"❌ Error: {str(e)}")
            self.export_status.setStyleSheet("color: red; padding: 10px;")
            QMessageBox.critical(self, "Error", f"Error al exportar:\n{str(e)}")
    
    def _update_additional_tabs(self, results: Dict[str, Any]):
        """Update additional tabs with real analysis data"""
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(self.current_html, 'html.parser')
            
            # Content Analysis
            text_content = soup.get_text()
            word_count = len(text_content.split())
            char_count = len(text_content)
            paragraphs = len(soup.find_all('p'))
            
            content_text = f"""📊 MÉTRICAS DE CONTENIDO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Palabras totales: {word_count}
🔤 Caracteres: {char_count}
📄 Párrafos: {paragraphs}
📏 Promedio palabras/párrafo: {word_count // paragraphs if paragraphs > 0 else 0}

✅ RECOMENDACIONES:
• Contenido óptimo: 1000-2500 palabras
• Usa párrafos cortos (3-5 líneas)
• Incluye listas y subtítulos
"""
            self.content_metrics.setPlainText(content_text)
            
            # Mobile Analysis
            viewport = soup.find('meta', attrs={'name': 'viewport'})
            mobile_text = f"""📱 OPTIMIZACIÓN MOBILE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Viewport tag: {"✅ Presente" if viewport else "❌ Falta"}
"""
            if viewport:
                mobile_text += f"Contenido: {viewport.get('content', 'No especificado')}\n"
            else:
                mobile_text += "\n⚠️ Añade: <meta name='viewport' content='width=device-width, initial-scale=1'>\n"
            
            self.mobile_analysis.setPlainText(mobile_text)
            
            # Security Analysis
            security_text = f"""🔒 ANÁLISIS DE SEGURIDAD:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Protocolo: {"✅ HTTPS" if self.current_url.startswith('https') else "⚠️ HTTP (inseguro)"}
"""
            if not self.current_url.startswith('https'):
                security_text += "\n⚠️ RECOMENDACIÓN: Migra tu sitio a HTTPS para:\n"
                security_text += "  • Mejorar seguridad de usuarios\n"
                security_text += "  • Mejor posicionamiento en Google\n"
                security_text += "  • Aumentar confianza de visitantes\n"
            
            # Check for mixed content
            insecure_resources = []
            for tag in soup.find_all(['img', 'script', 'link']):
                src = tag.get('src') or tag.get('href', '')
                if src.startswith('http://'):
                    insecure_resources.append(src[:80])
            
            if insecure_resources:
                security_text += f"\n⚠️ {len(insecure_resources)} recursos HTTP en página HTTPS (mixed content)\n"
            
            self.security_analysis.setPlainText(security_text)
            
            # Social Media Analysis
            og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
            twitter_tags = soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})
            
            social_text = f"""📲 REDES SOCIALES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OPEN GRAPH TAGS:
{"✅" if og_tags else "❌"} Detectados: {len(og_tags)} tags

"""
            for tag in og_tags[:5]:  # Show first 5
                prop = tag.get('property', '')
                content = tag.get('content', '')[:50]
                social_text += f"  • {prop}: {content}\n"
            
            social_text += f"\nTWITTER CARDS:\n{"✅" if twitter_tags else "❌"} Detectados: {len(twitter_tags)} tags\n"
            
            if not og_tags:
                social_text += "\n💡 Añade Open Graph tags para mejorar compartición en redes\n"
            
            self.social_analysis.setPlainText(social_text)
            
            # Technical SEO
            canonical = soup.find('link', rel='canonical')
            robots_meta = soup.find('meta', attrs={'name': 'robots'})
            
            canonical_status = "✅" if canonical else "⚠️"
            canonical_text = "Presente" if canonical else "Falta"
            robots_status = "✅" if robots_meta else "ℹ️"
            robots_text = "Presente" if robots_meta else "No especificado (por defecto: index, follow)"
            hreflang_status = "✅" if soup.find_all('link', rel='alternate', hreflang=True) else "ℹ️"
            
            technical_text = f"""🔧 SEO TÉCNICO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CANONICALS:
{canonical_status} Canonical tag: {canonical_text}
"""
            if canonical:
                technical_text += f"  URL: {canonical.get('href', '')[:80]}\n"
            
            technical_text += f"""
ROBOTS META:
{robots_status} Robots tag: {robots_text}
"""
            if robots_meta:
                technical_text += f"  Directivas: {robots_meta.get('content', '')}\n"
            
            # Check for hreflang
            hreflang_tags = soup.find_all('link', rel='alternate', hreflang=True)
            technical_text += f"""
HREFLANG:
{hreflang_status} Tags detectados: {len(hreflang_tags)}
"""
            
            self.technical_analysis.setPlainText(technical_text)
            
        except Exception as e:
            print(f"Error updating additional tabs: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()
