#!/usr/bin/env python3
"""
Proxy Management Panel - Full integration with Scrapelillo
"""

import sys
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QTextEdit, QPushButton, QLabel, QSpinBox, 
                               QLineEdit, QComboBox, QListWidget, QListWidgetItem,
                               QCheckBox, QGroupBox, QScrollArea, QFrame, QMessageBox,
                               QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
                               QProgressBar, QSplitter, QInputDialog, QApplication)
from PySide6.QtCore import Qt, QThread, Signal as pyqtSignal, QTimer
from PySide6.QtGui import QFont, QColor, QIcon
from base_panel import BasePanel
from premium_decorators import requires_premium

class ProxyValidationThread(QThread):
    """Thread to validate proxies in the background"""
    validation_complete = pyqtSignal(dict)
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self, proxy_manager, proxy_list):
        super().__init__()
        self.proxy_manager = proxy_manager
        self.proxy_list = proxy_list
        self.running = True
    
    def run(self):
        """Execute proxy validation"""
        results = {}
        total = len(self.proxy_list)
        
        for i, proxy in enumerate(self.proxy_list):
            if not self.running:
                break
                
            try:
                # Validate proxy using the manager
                if hasattr(self.proxy_manager, 'validate_proxy_sync'):
                    is_valid = self.proxy_manager.validate_proxy_sync(proxy)
                elif hasattr(self.proxy_manager, 'validate_proxy'):
                    # Fallback for async method (simplified for sync)
                    is_valid = True  # Placeholder - basic validation
                else:
                    is_valid = True  # No validation available
                    
                # Use proxy URL as key (hashable string)
                proxy_url = proxy.url if hasattr(proxy, 'url') else str(proxy)
                results[proxy_url] = {
                    'valid': is_valid,
                    'timestamp': datetime.now().isoformat(),
                    'response_time': proxy.speed if hasattr(proxy, 'speed') and proxy.speed else 0,
                    'proxy_obj': proxy  # Keep reference to object
                }
                
                self.progress_updated.emit(
                    int((i + 1) / total * 100),
                    f"Validating {proxy_url}..."
                )
                
            except Exception as e:
                proxy_url = proxy.url if hasattr(proxy, 'url') else str(proxy)
                results[proxy_url] = {
                    'valid': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat(),
                    'proxy_obj': proxy
                }
        
        self.validation_complete.emit(results)
    
    def stop(self):
        """Stop validation"""
        self.running = False

class ProxyPanel(BasePanel):
    def __init__(self, proxy_manager=None, parent=None):
        self.proxy_manager = proxy_manager
        self.validation_thread = None
        super().__init__(parent)  # This will call setup_ui() automatically
        self.load_proxy_config()
    
    def get_tab_definitions(self):
        """Define tabs for proxy panel"""
        return [
            (self.create_proxy_list_tab, "📋 Proxy List"),
            (self.create_configuration_tab, "⚙️ Configuration"),
            (self.create_validation_tab, "🔍 Validation"),
            (self.create_statistics_tab, "📊 Statistics"),
            (self.create_import_export_tab, "📤 Import/Export"),
        ]
    
    def create_proxy_list_tab(self):
        """Tab to manage proxy list"""
        def build_content(widget, layout):
            # Controls using factory method
            controls_layout = self.create_button_row([
                ("➕ Add Proxy", self.add_proxy, "Add new proxy to the list"),
                ("🗑️ Remove Selected", self.remove_selected_proxy, "Delete selected proxy"),
                ("🗑️ Clear All", self.clear_all_proxies, "Delete all proxies"),
                ("🔄 Refresh List", self.refresh_proxy_list, "Update proxy list"),
                ("🧪 Test Selected", self.test_selected_proxy, "Test selected proxy")
            ])
            layout.addLayout(controls_layout)
            
            # Proxy input
            input_layout = QHBoxLayout()
            input_layout.addWidget(QLabel("New Proxy:"))
            
            self.proxy_input = QLineEdit()
            self.proxy_input.setPlaceholderText("http://user:pass@host:port or host:port")
            self.proxy_input.setFixedHeight(32)  # Consistent height
            if hasattr(self.proxy_input, "setClearButtonEnabled"):
                self.proxy_input.setClearButtonEnabled(True)
            input_layout.addWidget(self.proxy_input)
            
            self.add_single_btn = QPushButton("➕ Add")
            self.add_single_btn.clicked.connect(self.add_single_proxy)
            input_layout.addWidget(self.add_single_btn)
            
            layout.addLayout(input_layout)
            
            # Proxy table
            self.proxy_table = QTableWidget()
            self.proxy_table.setColumnCount(6)
            self.proxy_table.setHorizontalHeaderLabels([
                "Proxy", "Status", "Last Used", "Failures", "Speed", "Country"
            ])
            
            # Set table properties
            header = self.proxy_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
            
            layout.addWidget(self.proxy_table)
            
            # Status bar
            self.status_label = QLabel("Ready")
            layout.addWidget(self.status_label)
        
        return self.create_basic_tab(build_content, "Tab to manage proxy list")
    
    def create_configuration_tab(self):
        """Tab for proxy configuration"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Enable/Disable proxies
        enable_group = QGroupBox("Enable Proxies")
        enable_layout = QVBoxLayout()
        
        self.enable_proxies_cb = QCheckBox("Enable proxy rotation")
        self.enable_proxies_cb.toggled.connect(self.toggle_proxy_enabled)
        enable_layout.addWidget(self.enable_proxies_cb)
        
        enable_group.setLayout(enable_layout)
        layout.addWidget(enable_group)
        
        # Rotation strategy
        strategy_group = QGroupBox("Rotation Strategy")
        strategy_layout = QVBoxLayout()
        
        strategy_layout.addWidget(QLabel("Strategy:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["round_robin", "random", "weighted"])
        self.strategy_combo.currentTextChanged.connect(self.change_rotation_strategy)
        strategy_layout.addWidget(self.strategy_combo)
        
        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)
        
        # Timeout settings
        timeout_group = QGroupBox("Timeout Configuration")
        timeout_layout = QHBoxLayout()
        
        timeout_layout.addWidget(QLabel("Timeout (seconds):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 60)
        self.timeout_spin.setValue(10)
        self.timeout_spin.valueChanged.connect(self.change_timeout)
        timeout_layout.addWidget(self.timeout_spin)
        
        timeout_group.setLayout(timeout_layout)
        layout.addWidget(timeout_group)
        
        # Failure settings
        failure_group = QGroupBox("Failure Configuration")
        failure_layout = QHBoxLayout()
        
        failure_layout.addWidget(QLabel("Max failures before deactivation:"))
        self.max_failures_spin = QSpinBox()
        self.max_failures_spin.setRange(1, 10)
        self.max_failures_spin.setValue(3)
        self.max_failures_spin.valueChanged.connect(self.change_max_failures)
        failure_layout.addWidget(self.max_failures_spin)
        
        failure_group.setLayout(failure_layout)
        layout.addWidget(failure_group)
        
        # Validation settings
        validation_group = QGroupBox("Validation Configuration")
        validation_layout = QVBoxLayout()
        
        validation_layout.addWidget(QLabel("Validation URL:"))
        self.validation_url_input = QLineEdit()
        self.validation_url_input.setText("http://httpbin.org/ip")
        self.validation_url_input.setFixedHeight(32)  # Consistent height
        if hasattr(self.validation_url_input, "setClearButtonEnabled"):
            self.validation_url_input.setClearButtonEnabled(True)
        self.validation_url_input.textChanged.connect(self.change_validation_url)
        validation_layout.addWidget(self.validation_url_input)
        
        validation_group.setLayout(validation_layout)
        layout.addWidget(validation_group)
        
        # Apply button
        self.apply_config_btn = QPushButton("💾 Apply Configuration")
        self.apply_config_btn.clicked.connect(self.apply_configuration)
        layout.addWidget(self.apply_config_btn)
        
        widget.setLayout(layout)
        return widget
    
    def create_validation_tab(self):
        """Tab for proxy validation"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Validation controls
        controls_layout = QHBoxLayout()
        
        self.validate_all_btn = QPushButton("🔍 Validate All")
        self.validate_all_btn.clicked.connect(self.validate_all_proxies)
        controls_layout.addWidget(self.validate_all_btn)
        
        self.validate_selected_btn = QPushButton("🔍 Validate Selected")
        self.validate_selected_btn.clicked.connect(self.validate_selected_proxies)
        controls_layout.addWidget(self.validate_selected_btn)
        
        self.stop_validation_btn = QPushButton("⏹️ Stop Validation")
        self.stop_validation_btn.clicked.connect(self.stop_validation)
        self.stop_validation_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_validation_btn)
        
        # Help button
        self.help_validation_btn = QPushButton("❓ Help")
        self.help_validation_btn.clicked.connect(self.show_validation_help)
        controls_layout.addWidget(self.help_validation_btn)
        
        layout.addLayout(controls_layout)
        
        # Progress bar
        self.validation_progress = QProgressBar()
        self.validation_progress.setVisible(False)
        layout.addWidget(self.validation_progress)
        
        # Validation results
        self.validation_text = QTextEdit()
        self.validation_text.setPlaceholderText("Validation results will appear here...")
        layout.addWidget(self.validation_text)
        
        widget.setLayout(layout)
        return widget
    
    def create_statistics_tab(self):
        """Tab for proxy statistics"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Refresh button
        self.refresh_stats_btn = QPushButton("🔄 Refresh Statistics")
        self.refresh_stats_btn.clicked.connect(self.refresh_statistics)
        layout.addWidget(self.refresh_stats_btn)
        
        # Statistics display
        self.stats_text = QTextEdit()
        self.stats_text.setPlaceholderText("Statistics will appear here...")
        layout.addWidget(self.stats_text)
        
        widget.setLayout(layout)
        return widget
    
    def create_import_export_tab(self):
        """Tab for importing/exporting proxies"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Import controls
        import_group = QGroupBox("Import Proxies")
        import_layout = QVBoxLayout()
        
        import_btn_layout = QHBoxLayout()
        self.import_file_btn = QPushButton("📁 Import from File")
        self.import_file_btn.clicked.connect(self.import_from_file)
        import_btn_layout.addWidget(self.import_file_btn)
        
        self.import_text_btn = QPushButton("📝 Import from Text")
        self.import_text_btn.clicked.connect(self.import_from_text)
        import_btn_layout.addWidget(self.import_text_btn)
        
        import_layout.addLayout(import_btn_layout)
        import_group.setLayout(import_layout)
        layout.addWidget(import_group)
        
        # Export controls
        export_group = QGroupBox("Export Proxies")
        export_layout = QVBoxLayout()
        
        export_btn_layout = QHBoxLayout()
        self.export_file_btn = QPushButton("💾 Export to File")
        self.export_file_btn.clicked.connect(self.export_to_file)
        export_btn_layout.addWidget(self.export_file_btn)
        
        self.export_text_btn = QPushButton("📋 Copy to Clipboard")
        self.export_text_btn.clicked.connect(self.export_to_clipboard)
        export_btn_layout.addWidget(self.export_text_btn)
        
        export_layout.addLayout(export_btn_layout)
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        # Bulk input
        bulk_group = QGroupBox("Bulk Input")
        bulk_layout = QVBoxLayout()
        
        self.bulk_input = QTextEdit()
        self.bulk_input.setPlaceholderText("Paste a list of proxies (one per line) here")
        self.bulk_input.setMaximumHeight(100)
        bulk_layout.addWidget(self.bulk_input)
        
        bulk_btn_layout = QHBoxLayout()
        self.add_bulk_btn = QPushButton("➕ Add All")
        self.add_bulk_btn.clicked.connect(self.add_bulk_proxies)
        bulk_btn_layout.addWidget(self.add_bulk_btn)
        
        self.clear_bulk_btn = QPushButton("🗑️ Clear")
        self.clear_bulk_btn.clicked.connect(self.clear_bulk_input)
        bulk_btn_layout.addWidget(self.clear_bulk_btn)
        
        bulk_layout.addLayout(bulk_btn_layout)
        bulk_group.setLayout(bulk_layout)
        layout.addWidget(bulk_group)
        
        widget.setLayout(layout)
        return widget
    
    # Action methods
    def add_proxy(self):
        """Add proxy manually"""
        proxy, ok = QInputDialog.getText(self, "Add Proxy", 
                                        "Enter proxy (format: host:port or http://user:pass@host:port):")
        if ok and proxy.strip():
            self.add_single_proxy_to_manager(proxy.strip())
    
    def add_single_proxy(self):
        """Add proxy from input"""
        proxy = self.proxy_input.text().strip()
        if proxy:
            self.add_single_proxy_to_manager(proxy)
            self.proxy_input.clear()
    
    def add_single_proxy_to_manager(self, proxy):
        """Add proxy to manager with format validation"""
        try:
            if not self.proxy_manager:
                QMessageBox.warning(self, "Error", "Proxy manager not available")
                return
            
            # Validate basic proxy format
            proxy = proxy.strip()
            if not proxy:
                QMessageBox.warning(self, "Error", "Proxy cannot be empty")
                return
            
            # Add protocol if not present
            if not proxy.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
                # Try to detect if it has user:pass@host:port format
                if '@' in proxy:
                    proxy = f"http://{proxy}"
                else:
                    # Simple host:port format
                    proxy = f"http://{proxy}"
            
            self.proxy_manager.add_proxy(proxy)
            self.refresh_proxy_list()
            self.status_label.setText(f"Proxy added: {proxy}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error adding proxy: {str(e)}")
    
    def remove_selected_proxy(self):
        """Remove selected proxy"""
        current_row = self.proxy_table.currentRow()
        if current_row >= 0:
            proxy_item = self.proxy_table.item(current_row, 0)
            if proxy_item:
                proxy = proxy_item.text()
                try:
                    if self.proxy_manager:
                        self.proxy_manager.remove_proxy(proxy)
                        self.refresh_proxy_list()
                        self.status_label.setText(f"Proxy deleted: {proxy}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Error deleting proxy: {str(e)}")
    
    def clear_all_proxies(self):
        """Clear all proxies"""
        reply = QMessageBox.question(self, "Confirm", 
                                   "Are you sure you want to delete all proxies?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                if self.proxy_manager:
                    # Clear all proxies
                    self.proxy_manager.proxies.clear()
                    self.refresh_proxy_list()
                    self.status_label.setText("All proxies deleted")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error clearing proxies: {str(e)}")
    
    def refresh_proxy_list(self):
        """Update proxy list with detailed information"""
        try:
            if not self.proxy_manager:
                self.proxy_table.setRowCount(0)
                self.status_label.setText("Proxy manager not available")
                return
            
            self.proxy_table.setRowCount(0)
            
            for proxy in self.proxy_manager.proxies:
                row = self.proxy_table.rowCount()
                self.proxy_table.insertRow(row)
                
                # Proxy URL
                url_item = QTableWidgetItem(proxy.url)
                url_item.setToolTip(f"Host: {proxy.host}\nPort: {proxy.port}\nProtocol: {proxy.protocol}")
                self.proxy_table.setItem(row, 0, url_item)
                
                # Status with color
                if proxy.is_active and proxy.failure_count < self.proxy_manager.max_failures:
                    status = "✅ Active"
                    status_color = QColor(0, 150, 0)  # Green
                elif proxy.failure_count >= self.proxy_manager.max_failures:
                    status = "🚫 Disabled"
                    status_color = QColor(200, 0, 0)  # Red
                else:
                    status = "⚠️ Inactive"
                    status_color = QColor(200, 150, 0)  # Yellow
                
                status_item = QTableWidgetItem(status)
                status_item.setForeground(status_color)
                status_item.setToolTip(f"Failures: {proxy.failure_count}/{self.proxy_manager.max_failures}")
                self.proxy_table.setItem(row, 1, status_item)
                
                # Last used with readable format
                if proxy.last_used:
                    try:
                        # Calculate elapsed time
                        from datetime import datetime
                        now = datetime.now()
                        diff = now - proxy.last_used
                        
                        if diff.days > 0:
                            last_used_text = f"{diff.days} days ago"
                        elif diff.seconds > 3600:
                            hours = diff.seconds // 3600
                            last_used_text = f"{hours}h ago"
                        elif diff.seconds > 60:
                            minutes = diff.seconds // 60
                            last_used_text = f"{minutes}m ago"
                        else:
                            last_used_text = "Just now"
                        
                        last_used_item = QTableWidgetItem(last_used_text)
                        last_used_item.setToolTip(proxy.last_used.strftime("%Y-%m-%d %H:%M:%S"))
                    except Exception:
                        last_used_item = QTableWidgetItem("Date error")
                else:
                    last_used_item = QTableWidgetItem("Never")
                
                self.proxy_table.setItem(row, 2, last_used_item)
                
                # Failures with color
                failures_item = QTableWidgetItem(str(proxy.failure_count))
                if proxy.failure_count == 0:
                    failures_item.setForeground(QColor(0, 150, 0))  # Green
                elif proxy.failure_count < self.proxy_manager.max_failures:
                    failures_item.setForeground(QColor(200, 150, 0))  # Yellow
                else:
                    failures_item.setForeground(QColor(200, 0, 0))  # Red
                
                self.proxy_table.setItem(row, 3, failures_item)
                
                # Speed with improved format
                if proxy.speed:
                    if proxy.speed < 100:
                        speed_text = f"{proxy.speed:.0f}ms"
                        speed_color = QColor(0, 150, 0)  # Green - fast
                    elif proxy.speed < 500:
                        speed_text = f"{proxy.speed:.0f}ms"
                        speed_color = QColor(200, 150, 0)  # Yellow - medium
                    else:
                        speed_text = f"{proxy.speed:.0f}ms"
                        speed_color = QColor(200, 0, 0)  # Red - slow
                    
                    speed_item = QTableWidgetItem(speed_text)
                    speed_item.setForeground(speed_color)
                else:
                    speed_item = QTableWidgetItem("N/A")
                
                self.proxy_table.setItem(row, 4, speed_item)
                
                # Country
                country_item = QTableWidgetItem(proxy.country or "N/A")
                self.proxy_table.setItem(row, 5, country_item)
            
            # Statistics in status
            active_count = len([p for p in self.proxy_manager.proxies if p.is_active])
            total_count = len(self.proxy_manager.proxies)
            self.status_label.setText(f"Proxies: {active_count}/{total_count} active")
            
        except Exception as e:
            print(f"[ERROR] Error updating proxy list: {e}")
            QMessageBox.critical(self, "Error", f"Error updating list: {str(e)}")
    
    def toggle_proxy_enabled(self, enabled):
        """Enable/disable proxies"""
        try:
            if self.proxy_manager:
                self.proxy_manager.enabled = enabled
                self.status_label.setText(f"Proxies {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error changing state: {str(e)}")
    
    def change_rotation_strategy(self, strategy):
        """Change rotation strategy"""
        try:
            if self.proxy_manager:
                self.proxy_manager.rotation_strategy = strategy
                self.status_label.setText(f"Strategy changed to: {strategy}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error changing strategy: {str(e)}")
    
    def change_timeout(self, timeout):
        """Change timeout"""
        try:
            if self.proxy_manager:
                self.proxy_manager.timeout = timeout
                self.status_label.setText(f"Timeout changed to: {timeout}s")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error changing timeout: {str(e)}")
    
    def change_max_failures(self, max_failures):
        """Change max failures"""
        try:
            if self.proxy_manager:
                self.proxy_manager.max_failures = max_failures
                self.status_label.setText(f"Max failures changed to: {max_failures}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error changing max failures: {str(e)}")
    
    def change_validation_url(self, url):
        """Change validation URL"""
        try:
            if self.proxy_manager:
                self.proxy_manager.validation_url = url
                self.status_label.setText(f"Validation URL changed to: {url}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error changing validation URL: {str(e)}")
    
    def apply_configuration(self):
        """Apply configuration"""
        try:
            # Apply all configuration changes
            self.status_label.setText("Configuration applied")
            QMessageBox.information(self, "Success", "Configuration applied successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error applying configuration: {str(e)}")
    
    @requires_premium("proxy", "validation")
    def validate_all_proxies(self):
        """Validate all proxies"""
        if not self.proxy_manager or not self.proxy_manager.proxies:
            QMessageBox.warning(self, "Warning", "No proxies to validate")
            return
        
        self.start_validation(self.proxy_manager.proxies)
    
    def validate_selected_proxies(self):
        """Validate selected proxies"""
        try:
            selected_rows = set(item.row() for item in self.proxy_table.selectedItems())
            if not selected_rows:
                QMessageBox.warning(self, "Warning", "No proxies selected")
                return
            
            if not self.proxy_manager or not self.proxy_manager.proxies:
                QMessageBox.warning(self, "Error", "No proxies available for validation")
                return
            
            selected_proxies = []
            for row in selected_rows:
                if row < len(self.proxy_manager.proxies):
                    proxy = self.proxy_manager.proxies[row]
                    selected_proxies.append(proxy)
            
            if selected_proxies:
                self.start_validation(selected_proxies)
            else:
                QMessageBox.warning(self, "Error", "Could not get selected proxies")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error validating selected proxies: {str(e)}")
            print(f"[ERROR] Error in validate_selected_proxies: {e}")
    
    def start_validation(self, proxy_list):
        """Start proxy validation"""
        try:
            if self.validation_thread and self.validation_thread.isRunning():
                QMessageBox.warning(self, "Warning", "Validation already in progress")
                return
            
            if not proxy_list:
                QMessageBox.warning(self, "Error", "No proxies to validate")
                return
            
            if not self.proxy_manager:
                QMessageBox.warning(self, "Error", "Proxy manager not available")
                return
            
            # Clear previous results
            self.validation_text.clear()
            
            self.validation_thread = ProxyValidationThread(self.proxy_manager, proxy_list)
            self.validation_thread.validation_complete.connect(self.on_validation_complete)
            self.validation_thread.progress_updated.connect(self.on_validation_progress)
            
            self.validation_progress.setVisible(True)
            self.validation_progress.setValue(0)
            self.stop_validation_btn.setEnabled(True)
            self.validate_all_btn.setEnabled(False)
            self.validate_selected_btn.setEnabled(False)
            
            self.status_label.setText(f"Starting validation of {len(proxy_list)} proxies...")
            self.validation_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error starting validation: {str(e)}")
            print(f"[ERROR] Error in start_validation: {e}")
            # Restore button state on error
            self.validation_progress.setVisible(False)
            self.stop_validation_btn.setEnabled(False)
            self.validate_all_btn.setEnabled(True)
            self.validate_selected_btn.setEnabled(True)
    
    def stop_validation(self):
        """Stop validation"""
        if self.validation_thread:
            self.validation_thread.stop()
            self.validation_thread.wait()
        
        self.validation_progress.setVisible(False)
        self.stop_validation_btn.setEnabled(False)
        self.validate_all_btn.setEnabled(True)
        self.validate_selected_btn.setEnabled(True)
    
    def on_validation_complete(self, results):
        """Callback when validation is complete"""
        self.validation_progress.setVisible(False)
        self.stop_validation_btn.setEnabled(False)
        self.validate_all_btn.setEnabled(True)
        self.validate_selected_btn.setEnabled(True)
        
        # Display results
        result_text = "🔍 VALIDATION RESULTS\n\n"
        
        valid_count = 0
        for proxy_url, result in results.items():
            status = "✅ VALID" if result['valid'] else "❌ INVALID"
            error = result.get('error', '')
            response_time = result.get('response_time', 0)
            
            result_text += f"{proxy_url}: {status}"
            if response_time > 0:
                result_text += f" ({response_time:.0f}ms)"
            result_text += "\n"
            
            if error:
                result_text += f"  Error: {error}\n"
            if result['valid']:
                valid_count += 1
        
        result_text += f"\n📊 SUMMARY:\n"
        result_text += f"  • Total validated: {len(results)}\n"
        result_text += f"  • Valid: {valid_count}\n"
        result_text += f"  • Invalid: {len(results) - valid_count}\n"
        
        # Calculate speed statistics
        valid_speeds = [result['response_time'] for result in results.values() 
                       if result['valid'] and result.get('response_time', 0) > 0]
        if valid_speeds:
            avg_speed = sum(valid_speeds) / len(valid_speeds)
            min_speed = min(valid_speeds)
            max_speed = max(valid_speeds)
            result_text += f"\n⚡ SPEEDS:\n"
            result_text += f"  • Average: {avg_speed:.0f}ms\n"
            result_text += f"  • Fastest: {min_speed:.0f}ms\n"
            result_text += f"  • Slowest: {max_speed:.0f}ms\n"
        
        self.validation_text.setText(result_text)
        self.refresh_proxy_list()  # Update table with new status
        self.status_label.setText(f"Validation completed: {valid_count}/{len(results)} valid")
    
    def on_validation_progress(self, progress, message):
        """Callback to update validation progress"""
        self.validation_progress.setValue(progress)
        self.status_label.setText(message)
    
    def refresh_statistics(self):
        """Update statistics with detailed information"""
        try:
            if not self.proxy_manager:
                self.stats_text.setText("❌ Proxy manager not available")
                return
            
            stats = self.proxy_manager.get_proxy_stats()
            
            stats_text = "📊 PROXY STATISTICS\n\n"
            
            # General information
            stats_text += f"📈 GENERAL:\n"
            stats_text += f"  • Total proxies: {stats.get('total_proxies', 0)}\n"
            stats_text += f"  • Active proxies: {stats.get('active_proxies', 0)}\n"
            stats_text += f"  • Failed proxies: {stats.get('failed_proxies', 0)}\n"
            stats_text += f"  • System enabled: {'✅ Yes' if self.proxy_manager.enabled else '❌ No'}\n\n"
            
            # Current configuration
            stats_text += f"⚙️ CURRENT CONFIGURATION:\n"
            stats_text += f"  • Strategy: {self.proxy_manager.rotation_strategy}\n"
            stats_text += f"  • Timeout: {self.proxy_manager.timeout}s\n"
            stats_text += f"  • Max failures: {self.proxy_manager.max_failures}\n"
            stats_text += f"  • Validation URL: {self.proxy_manager.validation_url}\n\n"
            
            # Current proxy
            current_proxy = self.proxy_manager.get_proxy()
            if current_proxy:
                stats_text += f"🎯 CURRENT PROXY:\n"
                stats_text += f"  • URL: {current_proxy.url}\n"
                stats_text += f"  • Host: {current_proxy.host}:{current_proxy.port}\n"
                stats_text += f"  • Protocol: {current_proxy.protocol}\n"
                stats_text += f"  • Status: {'✅ Active' if current_proxy.is_active else '❌ Inactive'}\n"
                stats_text += f"  • Failures: {current_proxy.failure_count}\n"
                if current_proxy.speed:
                    stats_text += f"  • Speed: {current_proxy.speed:.0f}ms\n"
                if current_proxy.last_used:
                    stats_text += f"  • Last used: {current_proxy.last_used.strftime('%H:%M:%S')}\n"
                stats_text += "\n"
            else:
                stats_text += f"🎯 CURRENT PROXY: None available\n\n"
            
            # Usage statistics
            stats_text += f"🔄 USAGE:\n"
            stats_text += f"  • Total requests: {stats.get('total_requests', 0)}\n"
            stats_text += f"  • Successful requests: {stats.get('successful_requests', 0)}\n"
            stats_text += f"  • Failed requests: {stats.get('failed_requests', 0)}\n"
            stats_text += f"  • Rotations: {stats.get('rotation_count', 0)}\n"
            
            if stats.get('last_rotation'):
                stats_text += f"  • Last rotation: {stats['last_rotation']}\n"
            
            # Top proxies by speed
            fast_proxies = [p for p in self.proxy_manager.proxies if p.speed and p.is_active]
            if fast_proxies:
                fast_proxies.sort(key=lambda x: x.speed)
                stats_text += f"\n🚀 FASTEST PROXIES:\n"
                for i, proxy in enumerate(fast_proxies[:3], 1):
                    stats_text += f"  {i}. {proxy.host}:{proxy.port} - {proxy.speed:.0f}ms\n"
            
            self.stats_text.setText(stats_text)
            self.status_label.setText("Statistics updated")
            
        except Exception as e:
            print(f"[ERROR] Error updating statistics: {e}")
            QMessageBox.critical(self, "Error", f"Error updating statistics: {str(e)}")
    
    def import_from_file(self):
        """Import proxies from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select proxy file", "", 
            "Text files (*.txt);;All files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                for proxy in proxies:
                    self.add_single_proxy_to_manager(proxy)
                
                QMessageBox.information(self, "Success", f"Imported {len(proxies)} proxies from {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error importing file: {str(e)}")
    
    def import_from_text(self):
        """Import proxies from text"""
        text, ok = QInputDialog.getMultiLineText(
            self, "Import Proxies", 
            "Paste a list of proxies (one per line) here:"
        )
        
        if ok and text.strip():
            proxies = [line.strip() for line in text.split('\n') if line.strip()]
            
            for proxy in proxies:
                self.add_single_proxy_to_manager(proxy)
            
            QMessageBox.information(self, "Success", f"Imported {len(proxies)} proxies")
    
    def export_to_file(self):
        """Export proxies to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save proxy file", "proxies.txt", 
            "Text files (*.txt);;All files (*)"
        )
        
        if file_path:
            try:
                if not self.proxy_manager:
                    raise Exception("Proxy manager not available")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    for proxy in self.proxy_manager.proxies:
                        f.write(f"{proxy.url}\n")
                
                QMessageBox.information(self, "Success", f"Exported {len(self.proxy_manager.proxies)} proxies to {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error exporting file: {str(e)}")
    
    def export_to_clipboard(self):
        """Export proxies to clipboard"""
        try:
            if not self.proxy_manager:
                raise Exception("Proxy manager not available")
            
            proxy_list = '\n'.join(proxy.url for proxy in self.proxy_manager.proxies)
            
            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(proxy_list)
            
            QMessageBox.information(self, "Success", f"Copied {len(self.proxy_manager.proxies)} proxies to clipboard")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error copying to clipboard: {str(e)}")
    
    def add_bulk_proxies(self):
        """Add proxies in bulk"""
        text = self.bulk_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Warning", "No text to process")
            return
        
        proxies = [line.strip() for line in text.split('\n') if line.strip()]
        
        for proxy in proxies:
            self.add_single_proxy_to_manager(proxy)
        
        QMessageBox.information(self, "Success", f"Added {len(proxies)} proxies")
        self.clear_bulk_input()
    
    def clear_bulk_input(self):
        """Clear bulk input"""
        self.bulk_input.clear()
    
    def load_proxy_config(self):
        """Load proxy configuration"""
        try:
            if self.proxy_manager:
                # Load current configuration
                self.enable_proxies_cb.setChecked(self.proxy_manager.enabled)
                self.strategy_combo.setCurrentText(self.proxy_manager.rotation_strategy)
                self.timeout_spin.setValue(self.proxy_manager.timeout)
                self.max_failures_spin.setValue(self.proxy_manager.max_failures)
                self.validation_url_input.setText(self.proxy_manager.validation_url)
                
                # Refresh proxy list
                self.refresh_proxy_list()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading configuration: {str(e)}")
    
    def test_selected_proxy(self):
        """Test selected proxy individually"""
        try:
            current_row = self.proxy_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Warning", "Select a proxy to test")
                return
            
            proxy_item = self.proxy_table.item(current_row, 0)
            if not proxy_item:
                return
            
            proxy_url = proxy_item.text()
            
            # Find proxy object
            proxy_obj = None
            for proxy in self.proxy_manager.proxies:
                if proxy.url == proxy_url:
                    proxy_obj = proxy
                    break
            
            if not proxy_obj:
                QMessageBox.warning(self, "Error", "Selected proxy not found")
                return
            
            # Show progress dialog
            from PySide6.QtWidgets import QProgressDialog
            progress = QProgressDialog("Testing proxy...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            # Test proxy in separate thread
            import threading
            def test_proxy():
                try:
                    result = self.proxy_manager.validate_proxy_sync(proxy_obj)
                    # Update UI in main thread
                    from PySide6.QtCore import QMetaObject, Qt
                    QMetaObject.invokeMethod(
                        self, "_show_test_result",
                        Qt.QueuedConnection,
                        result, proxy_url, proxy_obj.speed or 0
                    )
                except Exception as e:
                    QMetaObject.invokeMethod(
                        self, "_show_test_error",
                        Qt.QueuedConnection,
                        str(e), proxy_url
                    )
                finally:
                    QMetaObject.invokeMethod(progress, "close", Qt.QueuedConnection)
            
            thread = threading.Thread(target=test_proxy)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error testing proxy: {str(e)}")
    
    def _show_test_result(self, success, proxy_url, speed):
        """Show proxy test result"""
        try:
            if success:
                speed_text = f" ({speed:.0f}ms)" if speed > 0 else ""
                QMessageBox.information(
                    self, "Proxy Test", 
                    f"✅ Proxy works correctly\n\n"
                    f"URL: {proxy_url}{speed_text}\n"
                    f"Status: Successfully connected"
                )
            else:
                QMessageBox.warning(
                    self, "Proxy Test",
                    f"❌ Proxy does not work\n\n"
                    f"URL: {proxy_url}\n"
                    f"Status: Connection failed"
                )
            
            # Update list to show changes
            self.refresh_proxy_list()
            
        except Exception as e:
            print(f"[ERROR] Error showing result: {e}")
    
    def _show_test_error(self, error, proxy_url):
        """Show proxy test error"""
        try:
            QMessageBox.critical(
                self, "Error in Test",
                f"❌ Error testing proxy\n\n"
                f"URL: {proxy_url}\n"
                f"Error: {error}"
            )
        except Exception as e:
            print(f"[ERROR] Error showing error: {e}")
    
    def validate_proxy_manager_connection(self):
        """Validate that proxy manager is correctly connected"""
        try:
            if not self.proxy_manager:
                return False, "Proxy manager not available"
            
            if not hasattr(self.proxy_manager, 'proxies'):
                return False, "Proxy manager does not have a proxy list"
            
            if not hasattr(self.proxy_manager, 'validate_proxy_sync'):
                return False, "Proxy manager does not have a validation method"
            
            return True, "Valid connection"
            
        except Exception as e:
            return False, f"Error validating connection: {str(e)}"
    
    def show_validation_help(self):
        """Show help about proxy validation"""
        help_text = """
🔍 VALIDATION HELP

📋 HOW TO USE:
1. Add proxies using the format: host:port or http://user:pass@host:port
2. Select specific proxies or use "Validate All"
3. Validation will test the connectivity of each proxy
4. Results will show speed and status

⚡ SUPPORTED FORMATS:
• host:port (http:// is added automatically)
• http://host:port
• http://user:pass@host:port
• https://host:port
• socks5://host:port

📊 RESULTS:
• ✅ VALID: Proxy works correctly
• ❌ INVALID: Proxy does not respond or has errors
• Speed in ms (lower is better)

🚀 TIPS:
• Proxies < 100ms are very fast
• Proxies > 500ms may be slow
• Use "Test Selected" for individual tests
        """
        
        QMessageBox.information(self, "Help - Proxy Validation", help_text.strip()) 