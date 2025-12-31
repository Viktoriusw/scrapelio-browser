#!/usr/bin/env python3
"""
Panel de Chat con IA - Versión Segura
"""

import sys
import json
import time
import requests
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QTextEdit, QPushButton, QLabel, QSpinBox, 
                               QLineEdit, QComboBox, QListWidget, QListWidgetItem,
                               QCheckBox, QGroupBox, QScrollArea, QFrame, QMessageBox,
                               QSplitter, QProgressBar, QSizePolicy)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QTextCursor
from base_panel import BasePanel

class ChatPanelSafe(BasePanel):
    def __init__(self, parent=None):
        self.chat_history = []
        self.server_url = ""
        super().__init__(parent)  # Esto llamará a setup_ui() automáticamente
        
    def get_tab_definitions(self):
        """Define los tabs para el panel de chat"""
        return [
            (self.create_chat_tab, "💬 Chat with IA"),
            (self.create_settings_tab, "⚙️ Settings"),
            (self.create_history_tab, "📚 History"),
            (self.create_help_tab, "❓ Help"),
        ]
    
    def post_setup_ui(self):
        """Configuración adicional específica del chat"""
        # Configurar objectName para estilos CSS
        self.set_object_name("chatPanel")
        
    def create_chat_tab(self):
        """Tab principal del chat"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Connection status
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        self.test_connection_btn = QPushButton("🔗 Test Connection")
        self.test_connection_btn.clicked.connect(self.test_connection_safe)
        status_layout.addWidget(self.test_connection_btn)
        status_layout.addStretch(1)
        layout.addLayout(status_layout)

        # Context information display
        context_group = QGroupBox("📄 Page Context Information")
        context_layout = QVBoxLayout()
        self.context_info_label = QLabel("No page context information available")
        self.context_info_label.setObjectName("contextInfo")
        self.context_info_label.setWordWrap(True)
        context_layout.addWidget(self.context_info_label)
        self.refresh_context_btn = QPushButton("🔄 Refresh Context")
        self.refresh_context_btn.clicked.connect(self.update_context_info)
        context_layout.addWidget(self.refresh_context_btn)
        context_group.setLayout(context_layout)
        layout.addWidget(context_group)

        # --- Chat area ---
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setObjectName("chatScroll")
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chat_scroll.setStyleSheet("background: transparent;")

        self.chat_messages_widget = QWidget()
        self.chat_messages_layout = QVBoxLayout(self.chat_messages_widget)
        self.chat_messages_layout.setAlignment(Qt.AlignTop)
        self.chat_messages_layout.setSpacing(12)  # Espaciado entre burbujas
        self.chat_messages_layout.setContentsMargins(8, 8, 8, 8)  # Margen externo
        # Permitir que el widget se expanda según el contenido
        self.chat_messages_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        self.chat_scroll.setWidget(self.chat_messages_widget)
        layout.addWidget(self.chat_scroll, 1)

        # --- Input area: QTextEdit grande encima, botones debajo ---
        self.message_input = QTextEdit()
        self.message_input.setObjectName("chatInput")
        self.message_input.setPlaceholderText("Write your message here...")
        self.message_input.setMinimumHeight(60)
        self.message_input.setMaximumHeight(120)
        self.message_input.setAcceptRichText(False)
        layout.addWidget(self.message_input, 0)

        # Botones debajo del input
        buttons_layout = QHBoxLayout()
        self.send_btn = QPushButton("📤 Send")
        self.send_btn.setObjectName("chatSend")
        self.send_btn.clicked.connect(self.send_message_safe)
        self.send_btn.setEnabled(False)
        buttons_layout.addWidget(self.send_btn)

        self.clear_btn = QPushButton("🗑️ Clear Chat")
        self.clear_btn.clicked.connect(self.clear_chat)
        buttons_layout.addWidget(self.clear_btn)

        self.context_checkbox = QCheckBox("Include current page context")
        self.context_checkbox.setChecked(True)
        self.context_checkbox.toggled.connect(self.on_context_toggled)
        buttons_layout.addWidget(self.context_checkbox)

        buttons_layout.addStretch(1)
        layout.addLayout(buttons_layout)

        widget.setLayout(layout)
        # Habilitar/deshabilitar botón de enviar según input
        self.message_input.textChanged.connect(lambda: self.send_btn.setEnabled(bool(self.message_input.toPlainText().strip())))
        return widget
        
    def create_settings_tab(self):
        """Tab de configuración del servidor"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Server configuration
        server_group = QGroupBox("Server LM Studio Configuration")
        server_layout = QVBoxLayout()
        
        # Server URL input
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Server URL:"))
        self.server_url_input = QLineEdit()
        self.server_url_input.setPlaceholderText("http://localhost:1234")
        self.server_url_input.setFixedHeight(32)  # Altura consistente
        if hasattr(self.server_url_input, "setClearButtonEnabled"):
            self.server_url_input.setClearButtonEnabled(True)
        self.server_url_input.textChanged.connect(self.on_server_url_changed)
        url_layout.addWidget(self.server_url_input)
        
        self.save_url_btn = QPushButton("💾 Save URL")
        self.save_url_btn.clicked.connect(self.save_server_url)
        url_layout.addWidget(self.save_url_btn)
        
        server_layout.addLayout(url_layout)
        
        # Connection test
        test_layout = QHBoxLayout()
        self.test_btn = QPushButton("🔗 Test Connection")
        self.test_btn.clicked.connect(self.test_connection_safe)
        test_layout.addWidget(self.test_btn)
        
        self.connection_status_label = QLabel("Status: Not configured")
        test_layout.addWidget(self.connection_status_label)
        
        server_layout.addLayout(test_layout)
        
        # Advanced settings
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QVBoxLayout()
        
        # Temperature setting
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature (creativity):"))
        self.temperature_spin = QSpinBox()
        self.temperature_spin.setRange(0, 20)
        self.temperature_spin.setValue(7)
        self.temperature_spin.setSuffix(" (0.7)")
        temp_layout.addWidget(self.temperature_spin)
        
        advanced_layout.addLayout(temp_layout)
        
        # Max tokens setting
        tokens_layout = QHBoxLayout()
        tokens_layout.addWidget(QLabel("Max tokens:"))
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 4000)
        self.max_tokens_spin.setValue(1000)
        tokens_layout.addWidget(self.max_tokens_spin)
        
        advanced_layout.addLayout(tokens_layout)
        
        advanced_group.setLayout(advanced_layout)
        server_layout.addWidget(advanced_group)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # Load saved settings
        self.load_settings()
        
        widget.setLayout(layout)
        return widget
        
    def create_history_tab(self):
        """Tab del historial de conversaciones"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.refresh_history_btn = QPushButton("🔄 Refresh History")
        self.refresh_history_btn.clicked.connect(self.refresh_history)
        controls_layout.addWidget(self.refresh_history_btn)
        
        self.clear_history_btn = QPushButton("🗑️ Clear History")
        self.clear_history_btn.clicked.connect(self.clear_history)
        controls_layout.addWidget(self.clear_history_btn)
        
        self.export_history_btn = QPushButton("📤 Export History")
        self.export_history_btn.clicked.connect(self.export_history)
        controls_layout.addWidget(self.export_history_btn)
        
        layout.addLayout(controls_layout)
        
        # History list
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.load_conversation)
        layout.addWidget(self.history_list)
        
        widget.setLayout(layout)
        return widget
        
    def create_help_tab(self):
        """Tab de ayuda y documentación"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h2>🤖 Chat with IA Panel - Help</h2>
        
        <h3>Initial Configuration:</h3>
        <ol>
            <li>Download and install <a href="https://lmstudio.ai/">LM Studio</a></li>
            <li>Open LM Studio and download an AI model</li>
            <li>Start the local server in LM Studio</li>
            <li>Configure the server URL in the "Settings" tab</li>
            <li>Test the connection</li>
        </ol>
        
        <h3>Using the Chat:</h3>
        <ul>
            <li><strong>Send message:</strong> Write in the text area and press "Send"</li>
            <li><strong>Page context:</strong> Check the box to include information about the current page</li>
            <li><strong>Clear chat:</strong> Use the "Clear Chat" button to start a new conversation</li>
        </ul>
        
        <h3>Advanced Settings:</h3>
        <ul>
            <li><strong>Temperature:</strong> Controls the creativity of responses (0.0 = very conservative, 1.0 = very creative)</li>
            <li><strong>Max tokens:</strong> Limits the length of responses</li>
        </ul>
        
        <h3>Typical LM Studio URLs:</h3>
        <ul>
            <li><code>http://localhost:1234</code> - Default port</li>
            <li><code>http://localhost:8080</code> - Alternative port</li>
            <li><code>http://127.0.0.1:1234</code> - Local IP</li>
        </ul>
        
        <h3>Troubleshooting:</h3>
        <ul>
            <li><strong>Connection error:</strong> Ensure LM Studio is running</li>
            <li><strong>Timeout:</strong> The model may take a while to load, wait a few seconds</li>
            <li><strong>Empty response:</strong> Try a simpler message</li>
        </ul>
        """)
        
        layout.addWidget(help_text)
        widget.setLayout(layout)
        return widget
        
    def on_server_url_changed(self):
        """Callback when server URL changes"""
        url = self.server_url_input.text().strip()
        if url:
            self.server_url = url
            self.send_btn.setEnabled(True)
        else:
            self.send_btn.setEnabled(False)
            
    def save_server_url(self):
        """Save server URL"""
        url = self.server_url_input.text().strip()
        if url:
            self.server_url = url
            self.save_settings()
            QMessageBox.information(self, "Settings", "Server URL saved successfully")
        else:
            QMessageBox.warning(self, "Error", "Please enter a valid URL")
            
    def test_connection_safe(self):
        """Test connection safely without threads"""
        if not self.server_url:
            QMessageBox.warning(self, "Error", "Please configure the server URL first")
            return
            
        try:
            self.status_label.setText("Status: Testing connection...")
            self.status_label.setStyleSheet("color: blue; font-weight: bold;")
            
            # Test basic connectivity
            response = requests.get(f"{self.server_url}/v1/models", timeout=10)
            
            if response.status_code != 200:
                self.status_label.setText("Status: Server error")
                self.status_label.setStyleSheet("color: red; font-weight: bold;")
                QMessageBox.warning(self, "Error", f"Server error: {response.status_code}")
                return
                
            # Test chat completions
            test_payload = {
                "messages": [{"role": "user", "content": "Hello"}],
                "temperature": 0.7,
                "max_tokens": 20,
                "stream": False
            }
            
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=test_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    self.status_label.setText("Status: Connected")
                    self.status_label.setStyleSheet("color: green; font-weight: bold;")
                    self.connection_status_label.setText("Status: Connected ✓")
                    QMessageBox.information(self, "Connection Successful", "LM Studio server responds correctly")
                else:
                    self.status_label.setText("Status: Invalid response")
                    self.status_label.setStyleSheet("color: red; font-weight: bold;")
                    QMessageBox.warning(self, "Error", "Invalid server response")
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "")
                
                if "No models loaded" in error_msg:
                    self.status_label.setText("Status: No models loaded")
                    self.status_label.setStyleSheet("color: orange; font-weight: bold;")
                    self.connection_status_label.setText("Status: No model ✗")
                    
                    error_msg = """No models loaded in LM Studio.

To fix this:

1. Open LM Studio
2. Go to the 'Models' tab
3. Select a model (recommended: google/gemma-3-4b)
4. Click 'Load'
5. Wait for it to load (can take 2-5 minutes)
6. Test the connection again

Once the model is loaded, the chat will work correctly."""
                    
                    QMessageBox.information(self, "Information", error_msg)
                else:
                    self.status_label.setText("Status: Connection error")
                    self.status_label.setStyleSheet("color: red; font-weight: bold;")
                    self.connection_status_label.setText("Status: Error ✗")
                    QMessageBox.warning(self, "Error", f"Error: {error_msg}")
                    
        except requests.exceptions.ConnectionError:
            self.status_label.setText("Status: No connection")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.warning(self, "Error", "Could not connect to LM Studio server")
        except requests.exceptions.Timeout:
            self.status_label.setText("Status: Timeout")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.warning(self, "Error", "Timeout: Server took too long to respond")
        except Exception as e:
            self.status_label.setText("Status: Error")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.warning(self, "Error", f"Error: {str(e)}")
            
    def send_message_safe(self):
        """Send message safely without threads"""
        message = self.message_input.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Error", "Please write a message")
            return
            
        if not self.server_url:
            QMessageBox.warning(self, "Error", "Please configure the server URL first")
            return
            
        # Get current page context using the new function
        context = self.get_current_context()
        
        # Add user message to chat
        self.add_message_to_chat("User", message, "user")
        
        # Clear input
        self.message_input.clear()
        
        # Disable send button while processing
        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳ Processing...")
        
        try:
            # Prepare payload
            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a helpful assistant. Additional context: {context}"
                    },
                    {
                        "role": "user", 
                        "content": message
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
                "stream": False
            }
            
            # Perform request
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    self.add_message_to_chat("IA", content, "assistant")
                    self.save_to_history(message, content)
                else:
                    self.add_message_to_chat("System", "Invalid server response", "error")
            else:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                self.add_message_to_chat("System", f"Error: {error_msg}", "error")
                
        except requests.exceptions.ConnectionError:
            self.add_message_to_chat("System", "Could not connect to LM Studio server", "error")
        except requests.exceptions.Timeout:
            self.add_message_to_chat("System", "Timeout: Server took too long to respond", "error")
        except Exception as e:
            self.add_message_to_chat("System", f"Error: {str(e)}", "error")
        finally:
            # Re-enable send button
            self.send_btn.setEnabled(True)
            self.send_btn.setText("📤 Send")
        
    def format_ai_response(self, text):
        """
        Formats text with simple lists/headers to readable HTML.
        Adjusted for dark mode: subtle backgrounds and borders.
        """
        if not text:
            return text
            
        # Convert text to HTML with appropriate formatting
        formatted_text = text
        
        # Format main headings (lines ending with :)
        formatted_text = formatted_text.replace('\n\n', '\n')  # Normalize line breaks
        
        # Detect and format main headings (lines ending with :)
        lines = formatted_text.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Detect main headings (lines ending with :)
            if line.endswith(':') and len(line) < 100:
                formatted_lines.append(f'<h3 style="color: #2E7D32; margin: 15px 0 10px 0; font-size: 16px; font-weight: bold;">{line}</h3>')
                continue
                
            # Detect secondary headings (lines starting with **)
            if line.startswith('**') and line.endswith('**'):
                title = line[2:-2]  # Remove **
                formatted_lines.append(f'<h4 style="color: #388E3C; margin: 12px 0 8px 0; font-size: 14px; font-weight: bold;">{title}</h4>')
                continue
                
            # Detect numbered lists (lines starting with number.)
            if line and line[0].isdigit() and '. ' in line[:5]:
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    number = parts[0]
                    content = parts[1]
                    formatted_lines.append(f'<div style="margin: 5px 0; padding-left: 20px;"><strong>{number}.</strong> {content}</div>')
                    continue
                    
            # Detect list items with *
            if line.startswith('* ') or line.startswith('- '):
                content = line[2:] if line.startswith('* ') else line[2:]
                formatted_lines.append(f'<div style="margin: 3px 0; padding-left: 20px;">• {content}</div>')
                continue
                
            # Detect list items with +
            if line.startswith('+ '):
                content = line[2:]
                formatted_lines.append(f'<div style="margin: 3px 0; padding-left: 20px;">• {content}</div>')
                continue
                
            # Detect bold text (**text**)
            if '**' in line:
                # Replace **text** with <strong>text</strong>
                import re
                line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
                
            # Detect italic text (*text*)
            if '*' in line and '**' not in line:
                # Replace *text* with <em>text</em> (only if not **)
                import re
                line = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', line)
                
            # Normal line
            if line:
                formatted_lines.append(f'<div style="margin: 5px 0; line-height: 1.4;">{line}</div>')
        
        # Join all formatted lines
        formatted_text = '\n'.join(formatted_lines)
        
        # No inline styles - use current theme QSS
        formatted_text = f"""
        <div style="
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.55;
            padding: 12px 14px;
            border-radius: 10px;
            margin: 10px 0;
        ">
            {formatted_text}
        </div>
        """
        
        return formatted_text

    def add_message_to_chat(self, sender, message, message_type):
        """Add message to chat area (as a bubble)"""
        from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget
        import html
        timestamp = datetime.now().strftime("%H:%M:%S")
        # Bubble widget
        bubble = QWidget()
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)  # More generous padding
        bubble_layout.setSpacing(4)
        # Ensure bubble expands to show all content
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        # Title
        if message_type == "user":
            bubble.setObjectName("userBubble")
            title = f'<span style="font-weight:bold;opacity:.8;">{html.escape(sender)} <span style=\"font-size:11px;opacity:.6;\">({timestamp})</span></span>'
        elif message_type == "assistant":
            bubble.setObjectName("assistantBubble")
            title = f'<span style="font-weight:bold;opacity:.8;">{html.escape(sender)} <span style=\"font-size:11px;opacity:.6;\">({timestamp})</span></span>'
        else:
            bubble.setObjectName("errorBubble")
            title = f'<span style="font-weight:bold;opacity:.8;">{html.escape(sender)} <span style=\"font-size:11px;opacity:.6;\">({timestamp})</span></span>'
        title_label = QLabel(title)
        title_label.setTextFormat(Qt.RichText)
        title_label.setObjectName("bubbleTitle")
        bubble_layout.addWidget(title_label)
        # Message
        msg_label = QLabel(self.format_ai_response(message) if message_type=="assistant" else html.escape(message))
        msg_label.setTextFormat(Qt.RichText if message_type=="assistant" else Qt.PlainText)
        msg_label.setWordWrap(True)
        msg_label.setObjectName("bubbleMsg")
        # Ensure message expands completely
        msg_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        msg_label.setMinimumHeight(20)  # Reasonable minimum height
        msg_label.adjustSize()  # Adjust to content
        bubble_layout.addWidget(msg_label)
        self.chat_messages_layout.addWidget(bubble)
        
        # Force layout and scroll update
        self.chat_messages_widget.updateGeometry()
        self.chat_scroll.updateGeometry()
        
        # Auto-scroll to end with a small delay to allow layout to update
        QTimer.singleShot(10, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()))

    def clear_chat(self):
        """Clear chat area"""
        for i in reversed(range(self.chat_messages_layout.count())):
            widget = self.chat_messages_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self.chat_history = []
        
    def save_to_history(self, user_message, ai_response):
        """Save conversation to history"""
        conversation = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "ai_response": ai_response
        }
        self.chat_history.append(conversation)
        self.refresh_history()
        
    def refresh_history(self):
        """Update history list"""
        self.history_list.clear()
        for i, conv in enumerate(self.chat_history):
            timestamp = datetime.fromisoformat(conv["timestamp"]).strftime("%Y-%m-%d %H:%M")
            item_text = f"{timestamp}: {conv['user_message'][:50]}..."
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, i)
            self.history_list.addItem(item)
            
    def load_conversation(self, item):
        """Load conversation from history"""
        index = item.data(Qt.UserRole)
        if 0 <= index < len(self.chat_history):
            conv = self.chat_history[index]
            self.chat_display.clear()
            self.add_message_to_chat("User", conv["user_message"], "user")
            self.add_message_to_chat("IA", conv["ai_response"], "assistant")
            
    def clear_history(self):
        """Clear history"""
        self.chat_history.clear()
        self.history_list.clear()
        
    def export_history(self):
        """Export history to file"""
        if not self.chat_history:
            QMessageBox.information(self, "History", "No conversations to export")
            return
            
        try:
            filename = f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.chat_history, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Export", f"History exported to {filename}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not export history: {e}")
            
    def load_settings(self):
        """Load saved settings"""
        try:
            # Here you could load from a configuration file
            # For now, we use default values
            pass
        except Exception as e:
            print(f"Error loading configuration: {e}")
            
    def save_settings(self):
        """Save settings"""
        try:
            # Here you could save to a configuration file
            pass
        except Exception as e:
            print(f"Error saving configuration: {e}") 

    def update_context_info(self):
        """Updates the current page context information"""
        try:
            main_window = self.window()
            if hasattr(main_window, 'tab_manager'):
                current_tab = main_window.tab_manager.tabs.currentWidget()
                if current_tab:
                    current_url = current_tab.url().toString()
                    current_title = current_tab.page().title()
                    
                    # Format context information
                    context_text = f"""
<b>📄 Current Page:</b>
• <b>Title:</b> {current_title}
• <b>URL:</b> {current_url}
• <b>Status:</b> {'✅ Context active' if self.context_checkbox.isChecked() else '❌ Context inactive'}
                    """
                    
                    self.context_info_label.setText(context_text)
                    # No apply inline styles - use objectName for QSS
                else:
                    self.context_info_label.setText("No active tab")
                    # No apply inline styles - use objectName for QSS
            else:
                self.context_info_label.setText("Cannot access tab manager")
                # No apply inline styles - use objectName for QSS
        except Exception as e:
            self.context_info_label.setText(f"Error getting context: {str(e)}")
            # No apply inline styles - use objectName for QSS
    
    def on_context_toggled(self, checked):
        """Callback when context is toggled"""
        if checked:
            # No apply inline styles - use objectName for QSS
            # Update text to show it's active
            current_text = self.context_info_label.text()
            if "Status:" in current_text:
                current_text = current_text.replace("❌ Context inactive", "✅ Context active")
                self.context_info_label.setText(current_text)
        else:
            # No apply inline styles - use objectName for QSS
            # Update text to show it's inactive
            current_text = self.context_info_label.text()
            if "Status:" in current_text:
                current_text = current_text.replace("✅ Context active", "❌ Context inactive")
                self.context_info_label.setText(current_text)
    
    def get_current_context(self):
        """Gets the current page context"""
        if not self.context_checkbox.isChecked():
            return ""
            
        try:
            main_window = self.window()
            if hasattr(main_window, 'tab_manager'):
                current_tab = main_window.tab_manager.tabs.currentWidget()
                if current_tab:
                    current_url = current_tab.url().toString()
                    current_title = current_tab.page().title()
                    return f"Context: User browsing '{current_title}' ({current_url})"
                else:
                    return "Context: User browsing the web browser"
            else:
                return "Context: User browsing the web browser"
        except Exception as e:
            print(f"Error getting page context: {e}")
            return "Context: User browsing the web browser" 