#!/usr/bin/env python3
"""
SEO Analyzer Pro - Main UI Panel
Professional SEO analysis dashboard for the browser
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QColor


class SEOAnalyzerPanel(QWidget):
    """
    Main panel for SEO Analyzer Pro
    Provides UI for analyzing pages and viewing results
    """
    
    analysis_requested = Signal(str)  # url
    
    def __init__(self, parent=None, coordinator=None, tier_manager=None):
        super().__init__(parent)
        self.parent = parent
        self.coordinator = coordinator
        self.tier_manager = tier_manager
        self.browser_tab = None
        self.current_results = {}
        
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
        
        # Dashboard tab
        self.dashboard_tab = self._create_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        
        # Results tab
        self.results_tab = self._create_results_tab()
        self.tabs.addTab(self.results_tab, "📋 Resultados Detallados")
        
        # History tab (PRO+)
        self.history_tab = self._create_history_tab()
        self.tabs.addTab(self.history_tab, "📈 Historial")
        
        # Settings tab
        self.settings_tab = self._create_settings_tab()
        self.tabs.addTab(self.settings_tab, "⚙️ Configuración")
        
        layout.addWidget(self.tabs)
        
        # Status bar
        self.status_label = QLabel("Listo para analizar")
        self.status_label.setStyleSheet("padding: 5px; background-color: #f0f0f0; border-radius: 3px;")
        layout.addWidget(self.status_label)
    
    def _create_header(self):
        """Create header with title and analyze button"""
        header = QFrame()
        header.setStyleSheet("background-color: #2c3e50; border-radius: 5px; padding: 10px;")
        layout = QVBoxLayout(header)
        
        # Title
        title = QLabel("🔍 SEO Analyzer Pro")
        title.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)
        
        # Subtitle with tier info
        tier_name = "FREE"
        if self.tier_manager:
            tier_name = self.tier_manager.current_tier.upper()
        
        subtitle = QLabel(f"Nivel: {tier_name}")
        subtitle.setStyleSheet("color: #95a5a6; font-size: 12px;")
        layout.addWidget(subtitle)
        
        # Analyze button
        button_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("🚀 Analizar Página")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        button_layout.addWidget(self.analyze_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return header
    
    def _create_dashboard_tab(self):
        """Create dashboard tab with score and summary"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Score display
        score_group = QGroupBox("Puntuación SEO General")
        score_layout = QVBoxLayout(score_group)
        
        self.score_label = QLabel("--")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setStyleSheet("""
            font-size: 48px;
            font-weight: bold;
            color: #2c3e50;
            padding: 20px;
        """)
        score_layout.addWidget(self.score_label)
        
        self.grade_label = QLabel("Sin análisis")
        self.grade_label.setAlignment(Qt.AlignCenter)
        self.grade_label.setStyleSheet("font-size: 18px; color: #7f8c8d;")
        score_layout.addWidget(self.grade_label)
        
        layout.addWidget(score_group)
        
        # Issues summary
        issues_group = QGroupBox("Resumen de Problemas")
        issues_layout = QHBoxLayout(issues_group)
        
        self.critical_label = self._create_issue_label("CRÍTICOS", "#e74c3c", "0")
        self.error_label = self._create_issue_label("ERRORES", "#e67e22", "0")
        self.warning_label = self._create_issue_label("ADVERTENCIAS", "#f39c12", "0")
        
        issues_layout.addWidget(self.critical_label)
        issues_layout.addWidget(self.error_label)
        issues_layout.addWidget(self.warning_label)
        
        layout.addWidget(issues_group)
        
        # Export buttons
        export_group = QGroupBox("Exportar Resultados")
        export_layout = QHBoxLayout(export_group)
        
        self.export_json_btn = QPushButton("📄 JSON")
        self.export_csv_btn = QPushButton("📊 CSV")
        self.export_pdf_btn = QPushButton("📑 PDF")
        
        for btn in [self.export_json_btn, self.export_csv_btn, self.export_pdf_btn]:
            btn.setEnabled(False)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 8px 15px;
                    border-radius: 3px;
                    background-color: #34495e;
                    color: white;
                }
                QPushButton:hover:enabled {
                    background-color: #2c3e50;
                }
                QPushButton:disabled {
                    background-color: #95a5a6;
                }
            """)
            export_layout.addWidget(btn)
        
        export_layout.addStretch()
        layout.addWidget(export_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_results_tab(self):
        """Create results tab with detailed analysis"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Analizador", "Puntuación", "Problemas", "Estado"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.results_table)
        
        # Details text area
        details_label = QLabel("Detalles del análisis:")
        layout.addWidget(details_label)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        layout.addWidget(self.details_text)
        
        return tab
    
    def _create_history_tab(self):
        """Create history tab for past analyses"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("📈 Historial de Análisis")
        label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(label)
        
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Fecha", "URL", "Puntuación", "Calificación"])
        layout.addWidget(self.history_table)
        
        # Note for FREE tier
        if self.tier_manager and self.tier_manager.current_tier == "free":
            note = QLabel("💡 El historial está disponible en el plan PROFESSIONAL")
            note.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 10px;")
            layout.addWidget(note)
        
        return tab
    
    def _create_settings_tab(self):
        """Create settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("⚙️ Configuración")
        label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(label)
        
        # Settings will be added here
        settings_text = QLabel("Configuración del plugin SEO Analyzer Pro")
        settings_text.setStyleSheet("padding: 10px;")
        layout.addWidget(settings_text)
        
        layout.addStretch()
        
        return tab
    
    def _create_issue_label(self, title, color, count):
        """Create an issue count label"""
        frame = QFrame()
        frame.setStyleSheet(f"border: 2px solid {color}; border-radius: 5px; padding: 10px;")
        layout = QVBoxLayout(frame)
        
        count_label = QLabel(count)
        count_label.setAlignment(Qt.AlignCenter)
        count_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")
        layout.addWidget(count_label)
        
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(title_label)
        
        return frame
    
    def _connect_signals(self):
        """Connect signals from coordinator"""
        if self.coordinator:
            self.coordinator.analysis_started.connect(self._on_analysis_started)
            self.coordinator.analysis_progress.connect(self._on_analysis_progress)
            self.coordinator.analysis_completed.connect(self._on_analysis_completed)
            self.coordinator.analysis_error.connect(self._on_analysis_error)
    
    @Slot()
    def _on_analyze_clicked(self):
        """Handle analyze button click"""
        # Get current browser tab from parent
        if hasattr(self.parent, 'tab_manager'):
            self.browser_tab = self.parent.tab_manager.tabs.currentWidget()
            if self.browser_tab:
                url = self.browser_tab.url().toString()
                if url and url != "about:blank":
                    self.analyze_btn.setEnabled(False)
                    self.status_label.setText(f"Analizando: {url}")
                    if self.coordinator:
                        self.coordinator.analyze_page(self.browser_tab, url)
                else:
                    self.status_label.setText("⚠️ No hay una página válida para analizar")
            else:
                self.status_label.setText("⚠️ No hay pestaña activa")
        else:
            self.status_label.setText("⚠️ Error: No se puede acceder al tab manager")
    
    @Slot(str)
    def _on_analysis_started(self, url):
        """Handle analysis started signal"""
        self.status_label.setText(f"🔍 Analizando: {url}")
    
    @Slot(int, str)
    def _on_analysis_progress(self, progress, analyzer_name):
        """Handle analysis progress signal"""
        self.status_label.setText(f"🔍 Progreso: {progress}% - {analyzer_name}")
    
    @Slot(dict)
    def _on_analysis_completed(self, results):
        """Handle analysis completed signal"""
        self.current_results = results
        self.analyze_btn.setEnabled(True)
        
        # Update dashboard
        overall_score = results.get('overall_score', 0)
        overall_grade = results.get('overall_grade', 'F')
        
        self.score_label.setText(f"{overall_score:.0f}")
        self.score_label.setStyleSheet(f"""
            font-size: 48px;
            font-weight: bold;
            color: {self._get_score_color(overall_score)};
            padding: 20px;
        """)
        
        self.grade_label.setText(f"Calificación: {overall_grade}")
        
        # Update issues count
        issue_counts = results.get('issue_counts', {})
        self._update_issue_label(self.critical_label, issue_counts.get('critical', 0))
        self._update_issue_label(self.error_label, issue_counts.get('error', 0))
        self._update_issue_label(self.warning_label, issue_counts.get('warning', 0))
        
        # Enable export buttons
        self.export_json_btn.setEnabled(True)
        if self.tier_manager and self.tier_manager.current_tier in ['professional', 'enterprise']:
            self.export_csv_btn.setEnabled(True)
            self.export_pdf_btn.setEnabled(True)
        
        # Update results table
        self._update_results_table(results.get('analyzer_results', {}))
        
        self.status_label.setText(f"✅ Análisis completado - Puntuación: {overall_score:.0f}")
    
    @Slot(str)
    def _on_analysis_error(self, error_message):
        """Handle analysis error signal"""
        self.analyze_btn.setEnabled(True)
        self.status_label.setText(f"❌ Error: {error_message}")
    
    def _update_issue_label(self, label_frame, count):
        """Update issue count in label"""
        # Get the count label (first child)
        count_label = label_frame.layout().itemAt(0).widget()
        count_label.setText(str(count))
    
    def _update_results_table(self, analyzer_results):
        """Update the results table with analyzer results"""
        self.results_table.setRowCount(len(analyzer_results))
        
        for i, (analyzer_name, result) in enumerate(analyzer_results.items()):
            # Analyzer name
            self.results_table.setItem(i, 0, QTableWidgetItem(analyzer_name))
            
            # Score
            score = result.get('score', 0)
            score_item = QTableWidgetItem(f"{score:.1f}")
            score_item.setForeground(QColor(self._get_score_color(score)))
            self.results_table.setItem(i, 1, score_item)
            
            # Issues count
            issues_count = len(result.get('issues', []))
            self.results_table.setItem(i, 2, QTableWidgetItem(str(issues_count)))
            
            # Status
            grade = result.get('grade', 'F')
            status_item = QTableWidgetItem(grade)
            self.results_table.setItem(i, 3, status_item)
    
    def _get_score_color(self, score):
        """Get color based on score"""
        if score >= 90:
            return "#27ae60"  # Green
        elif score >= 75:
            return "#f39c12"  # Orange
        elif score >= 60:
            return "#e67e22"  # Dark orange
        else:
            return "#e74c3c"  # Red
    
    def cleanup(self):
        """Cleanup resources"""
        print("[SEO Analyzer] Cleanup complete")

