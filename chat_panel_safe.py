#!/usr/bin/env python3
"""
Panel de Chat con IA - Versión Segura
"""

import sys
import json
import re
import time
import requests
from urllib.parse import quote_plus
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QTextEdit, QPushButton, QLabel, QSpinBox, 
                               QLineEdit, QComboBox, QListWidget, QListWidgetItem,
                               QCheckBox, QGroupBox, QScrollArea, QFrame, QMessageBox,
                               QSplitter, QProgressBar, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, QEventLoop
from PySide6.QtGui import QFont, QColor, QTextCursor
from base_panel import BasePanel

# System prompt: la IA es el copiloto del navegador y debe priorizar consultas buscables
SYSTEM_PROMPT_BROWSER = """You are the AI copilot of a modern web browser. You help the user navigate, search and discover content.

When you recommend websites, tools, articles or resources, ALWAYS provide recommendations as SEARCH-READY items, not fragile deep links.

- Use markdown links with clear labels: [What to search](https://example.com) as reference if needed
- Suggest 2-5 concrete options
- Prefer robust recommendations that can be searched in Google/Bing/DuckDuckGo
- The browser will convert your recommendations into search result tabs."""

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

        # Context information display - NUEVO: Ahora con QTextEdit para ver el contenido
        context_group = QGroupBox("📄 Page Context (This will be sent to AI)")
        context_layout = QVBoxLayout()

        # Text edit to show extracted content
        self.context_display = QTextEdit()
        self.context_display.setReadOnly(True)
        self.context_display.setPlaceholderText("Page content will appear here when you click 'Extract Page Content'...")
        self.context_display.setMaximumHeight(150)
        context_layout.addWidget(self.context_display)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.extract_context_btn = QPushButton("🔄 Extract Page Content")
        self.extract_context_btn.clicked.connect(self.extract_page_content_now)
        buttons_layout.addWidget(self.extract_context_btn)

        self.clear_context_btn = QPushButton("🗑️ Clear Context")
        self.clear_context_btn.clicked.connect(lambda: self.context_display.clear())
        buttons_layout.addWidget(self.clear_context_btn)

        context_layout.addLayout(buttons_layout)
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
        self.message_input.setPlaceholderText(
            "Pregunta lo que quieras, pide recomendaciones o di «ábreme Skyscanner» o «busca vuelos a Barcelona»… "
            "La IA te responderá y podrás abrir sus enlaces en pestañas con un clic."
        )
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

        # Get context from the visible display (what user extracted)
        context = ""
        if self.context_checkbox.isChecked():
            context = self.context_display.toPlainText()
            if not context or context.startswith("❌") or context.startswith("⏳"):
                # No valid context extracted
                self.add_message_to_chat("System", "⚠️ Warning: Context checkbox is enabled but no page content extracted. Click 'Extract Page Content' first.", "error")
                context = ""

        # Add user message to chat
        self.add_message_to_chat("User", message, "user")

        # Comandos interactivos del navegador (funcionan incluso sin servidor LLM)
        if self._try_handle_browser_command(message):
            self.message_input.clear()
            return

        if not self.server_url:
            QMessageBox.warning(self, "Error", "Please configure the server URL first")
            return

        # Clear input
        self.message_input.clear()

        # Disable send button while processing
        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳ Processing...")

        try:
            # Build messages array
            messages = []

            # If we have context, include it EXPLICITLY in user message
            if context:
                user_content = f"""I'm viewing a web page. Here's the page content:

{context}

---

Based on this page content, {message}"""

                self.add_message_to_chat("System", f"📄 Sending page context ({len(context)} chars) to AI", "assistant")
            else:
                user_content = message

            # Mensajes con system prompt: la IA actúa como copiloto del navegador y recomienda enlaces
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_BROWSER},
                {"role": "user", "content": user_content}
            ]

            # Prepare payload
            payload = {
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000,
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

    def _try_handle_browser_command(self, message):
        """
        Ejecuta acciones directas del navegador desde lenguaje natural:
        - "busca ...": abre búsqueda en nueva pestaña
        - "abre ...": abre URL(s)/dominios o una búsqueda si no hay URL
        """
        text = (message or "").strip()
        lower = text.lower().strip()

        # Normalizar acentos para detectar comandos robustamente (busca/busqueda/abrir/etc.)
        normalized = (
            lower.replace("á", "a")
                 .replace("é", "e")
                 .replace("í", "i")
                 .replace("ó", "o")
                 .replace("ú", "u")
        )

        # Buscar en la web (acepta frases como "por favor buscame X")
        search_match = re.search(
            r"\b(?:busca(?:me|r)?|search|find)\b\s+(.+)$",
            normalized,
            flags=re.IGNORECASE
        )
        if search_match:
            start_idx = search_match.start(1)
            query = text[start_idx:].strip(" .,:;!?")
            if not query:
                self.add_message_to_chat("System", "Escribe qué quieres buscar. Ejemplo: \"busca vuelos baratos a Tokio\"", "error")
                return True
            opened_url = self._open_best_result_from_query(query)
            if opened_url:
                self.add_message_to_chat("IA", f"🚀 He abierto el mejor resultado web para: **{query}**\n\n[{opened_url}]({opened_url})", "assistant")
            else:
                search_url = self._build_search_url(query)
                self._open_url_in_browser(search_url)
                self.add_message_to_chat("IA", f"🔎 No pude resolver resultado directo. Abrí la búsqueda para: **{query}**\n\n[{search_url}]({search_url})", "assistant")
            return True

        # Abrir web(s) (acepta "abre", "abrir", "open", incluso dentro de frase)
        open_match = re.search(
            r"\b(?:abre|abrir|open)\b\s+(.+)$",
            normalized,
            flags=re.IGNORECASE
        )
        if open_match:
            start_idx = open_match.start(1)
            target = text[start_idx:].strip(" .,:;!?")
            if not target:
                self.add_message_to_chat("System", "Indica qué quieres abrir. Ejemplo: \"abre github.com\"", "error")
                return True

            links = self._extract_urls_from_message(target)
            urls = [u[0] for u in links]

            # Si no hay URL explícita, intentar detectar dominios sueltos
            if not urls:
                domains = re.findall(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b', target)
                for d in domains:
                    urls.append(f"https://{d}")

            # Si sigue sin haber URLs, abrir una búsqueda con el texto objetivo
            if not urls:
                opened_url = self._open_best_result_from_query(target)
                if opened_url:
                    self.add_message_to_chat("IA", f"🚀 No detecté URL exacta, abrí el mejor resultado para: **{target}**\n\n[{opened_url}]({opened_url})", "assistant")
                else:
                    search_url = self._build_search_url(target)
                    self._open_url_in_browser(search_url)
                    self.add_message_to_chat("IA", f"📂 No detecté una URL exacta, así que abrí una búsqueda para: **{target}**\n\n[{search_url}]({search_url})", "assistant")
                return True

            self._open_urls_in_browser(urls)
            self.add_message_to_chat("IA", f"🚀 He abierto {len(urls)} pestaña(s) en el navegador.", "assistant")
            return True

        return False

    def _build_search_url(self, query):
        """Construye URL de búsqueda usando el motor predeterminado si existe."""
        q = quote_plus(query)
        main = self.window()
        try:
            if hasattr(main, 'search_engine_manager') and main.search_engine_manager:
                default_engine = main.search_engine_manager.get_default_engine()
                engine_id = getattr(default_engine, "id", "duckduckgo")
                if engine_id == "google":
                    return f"https://www.google.com/search?q={q}"
                if engine_id == "bing":
                    return f"https://www.bing.com/search?q={q}"
                return f"https://duckduckgo.com/?q={q}"
        except Exception:
            pass
        return f"https://duckduckgo.com/?q={q}"

    def _get_search_engine_name(self):
        """Obtiene nombre legible del buscador activo."""
        main = self.window()
        try:
            if hasattr(main, 'search_engine_manager') and main.search_engine_manager:
                default_engine = main.search_engine_manager.get_default_engine()
                engine_id = getattr(default_engine, "id", "duckduckgo")
                if engine_id == "google":
                    return "Google"
                if engine_id == "bing":
                    return "Bing"
                return "DuckDuckGo"
        except Exception:
            pass
        return "DuckDuckGo"

    def _get_search_engine_id(self):
        """Obtiene id interno del buscador activo."""
        main = self.window()
        try:
            if hasattr(main, 'search_engine_manager') and main.search_engine_manager:
                default_engine = main.search_engine_manager.get_default_engine()
                return getattr(default_engine, "id", "duckduckgo")
        except Exception:
            pass
        return "duckduckgo"

    def _open_best_result_from_query(self, query):
        """
        Resuelve una consulta al primer resultado web y lo abre automáticamente.
        Devuelve la URL abierta o None.
        """
        direct_url = self._resolve_first_result_url(query)
        if direct_url:
            self._open_url_in_browser(direct_url)
            return direct_url
        return None

    def _resolve_first_result_url(self, query):
        """
        Intenta resolver la consulta a la primera URL real del buscador seleccionado.
        Fallback: None.
        """
        search_url = self._build_search_url(query)
        engine_id = self._get_search_engine_id()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
        }

        try:
            resp = requests.get(search_url, headers=headers, timeout=10)
            if resp.status_code != 200 or not resp.text:
                return None
            html = resp.text

            # Bing parser
            if engine_id == "bing":
                m = re.search(r'<li class="b_algo".*?<h2><a href="(https?://[^"]+)"', html, re.DOTALL)
                if m:
                    return m.group(1)

            # Google parser (frágil por cambios, pero útil como intento)
            if engine_id == "google":
                m = re.search(r'/url\\?q=(https?[^&"]+)&', html)
                if m:
                    return unquote(m.group(1))

            # DuckDuckGo parser
            m = re.search(r'class="result__a"[^>]*href="([^"]+)"', html)
            if m:
                href = m.group(1)
                # Puede venir redirect /l/?uddg=...
                if "duckduckgo.com/l/?" in href or href.startswith("/l/?"):
                    parsed = urlparse(href if href.startswith("http") else f"https://duckduckgo.com{href}")
                    uddg = parse_qs(parsed.query).get("uddg", [])
                    if uddg:
                        return unquote(uddg[0])
                if href.startswith("http"):
                    return href

        except Exception:
            return None

        return None
        
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

        # Si la IA devuelve recomendaciones, abrirlas como búsquedas en el motor elegido
        if message_type == "assistant":
            search_links = self._extract_search_links_from_message(message)
            if search_links:
                # Abrir automáticamente páginas web reales (no solo SERP) con límite para evitar spam
                self._auto_open_recommendations(search_links, max_auto_open=3)
                self._add_recommendation_cards(bubble_layout, search_links)

        self.chat_messages_layout.addWidget(bubble)
        
        # Force layout and scroll update
        self.chat_messages_widget.updateGeometry()
        self.chat_scroll.updateGeometry()
        
        # Auto-scroll to end with a small delay to allow layout to update
        QTimer.singleShot(10, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()))

    def _extract_urls_from_message(self, text):
        """Extrae URLs de la respuesta de la IA: markdown [texto](url) y URLs planas."""
        if not text:
            return []
        urls = []
        # Enlaces markdown [texto](url)
        for m in re.finditer(r'\[([^\]]*)\]\((https?://[^\)\s]+)\)', text):
            url = m.group(2).rstrip('.,;:!?)')
            title = (m.group(1).strip() or None)
            if url and url not in [u[0] for u in urls]:
                urls.append((url, title))
        # URLs planas no capturadas ya
        for m in re.finditer(r'https?://[^\s\)\]\>\"]+', text):
            url = m.group(0).rstrip('.,;:!?)')
            if not any(u[0] == url for u in urls):
                urls.append((url, None))
        return urls[:10]  # Máximo 10 para no saturar la UI

    def _extract_search_links_from_message(self, text):
        """
        Convierte recomendaciones de la IA en enlaces de búsqueda robustos.
        Devuelve lista de tuplas: (search_url, label)
        """
        raw_links = self._extract_urls_from_message(text)
        search_links = []
        seen = set()

        for url, title in raw_links:
            query = self._build_search_query_from_recommendation(url, title)
            if not query:
                continue
            search_url = self._build_search_url(query)
            if search_url in seen:
                continue
            seen.add(search_url)
            label = title or query
            search_links.append((search_url, label))

        # Si no hay URLs en la respuesta, intentar extraer bullets/textos como consultas
        if not search_links and text:
            for line in text.splitlines():
                line = line.strip(" -•\t")
                if len(line) < 6:
                    continue
                # Evitar párrafos largos
                if len(line) > 90:
                    continue
                query = line
                search_url = self._build_search_url(query)
                if search_url in seen:
                    continue
                seen.add(search_url)
                search_links.append((search_url, query))
                if len(search_links) >= 5:
                    break

        return search_links[:10]

    def _build_search_query_from_recommendation(self, url, title=None):
        """Construye una query estable para buscador desde URL/título sugerido por IA."""
        if title and title.strip():
            return title.strip()

        clean = re.sub(r'^https?://', '', (url or '').strip(), flags=re.IGNORECASE)
        clean = clean.split('#')[0].split('?')[0]
        parts = [p for p in clean.split('/') if p]
        if not parts:
            return ""
        domain = parts[0].replace("www.", "")
        path = " ".join(parts[1:3]) if len(parts) > 1 else ""
        path = path.replace('-', ' ').replace('_', ' ')
        query = f"{domain} {path}".strip()
        return query[:120]

    def _add_recommendation_cards(self, parent_layout, urls):
        """Añade tarjetas para abrir resultados de búsqueda en pestañas."""
        rec_frame = QFrame()
        rec_frame.setObjectName("recommendationCards")
        rec_layout = QVBoxLayout(rec_frame)
        rec_layout.setContentsMargins(8, 10, 8, 4)
        rec_layout.setSpacing(8)

        rec_label = QLabel(f"🔎 <b>Abrir búsqueda en {self._get_search_engine_name()}</b>")
        rec_label.setStyleSheet("color: #1a73e8; font-size: 12px;")
        rec_label.setTextFormat(Qt.RichText)
        rec_layout.addWidget(rec_label)

        # Fila de botones por enlace
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(6)
        for url, title in urls:
            label = (title or url)
            if len(label) > 45:
                label = label[:42] + "..."
            btn = QPushButton(f"🔎 {label}")
            btn.setToolTip(url)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(26, 115, 232, 0.12);
                    color: #1a73e8; border: 1px solid rgba(26, 115, 232, 0.4);
                    border-radius: 6px; padding: 6px 12px; font-size: 12px;
                    text-align: left; max-width: 220px;
                }
                QPushButton:hover {
                    background: rgba(26, 115, 232, 0.25);
                    border-color: #1a73e8;
                }
            """)
            btn.clicked.connect(lambda checked, u=url: self._open_url_in_browser(u))
            buttons_row.addWidget(btn)
        buttons_row.addStretch(1)
        rec_layout.addLayout(buttons_row)

        if len(urls) > 1:
            open_all_btn = QPushButton(f"🔎 Abrir todas en {self._get_search_engine_name()}")
            open_all_btn.setCursor(Qt.PointingHandCursor)
            open_all_btn.setStyleSheet("""
                QPushButton {
                    background: #1a73e8; color: white; border: none;
                    border-radius: 6px; padding: 8px 14px; font-size: 12px; font-weight: bold;
                }
                QPushButton:hover { background: #1557b0; }
            """)
            open_all_btn.clicked.connect(lambda: self._open_urls_in_browser([u[0] for u in urls]))
            rec_layout.addWidget(open_all_btn)

        rec_frame.setStyleSheet("""
            QFrame#recommendationCards {
                background: rgba(26, 115, 232, 0.06);
                border: 1px solid rgba(26, 115, 232, 0.2);
                border-radius: 8px;
            }
        """)
        parent_layout.addWidget(rec_frame)

    def _auto_open_recommendations(self, search_links, max_auto_open=3):
        """
        Abre automáticamente resultados web reales desde recomendaciones de búsqueda.
        search_links: [(search_url, label), ...]
        """
        opened = 0
        for search_url, label in search_links:
            if opened >= max_auto_open:
                break
            query = (label or "").strip()
            if not query:
                # fallback: usar q de la URL
                try:
                    parsed = urlparse(search_url)
                    q = parse_qs(parsed.query).get("q", [""])[0]
                    query = unquote(q)
                except Exception:
                    query = ""
            if not query:
                continue
            direct = self._resolve_first_result_url(query)
            if direct:
                self._open_url_in_browser(direct)
                opened += 1

    def _open_url_in_browser(self, url):
        """Abre una URL en una nueva pestaña del navegador."""
        main = self.window()
        if hasattr(main, 'tab_manager') and main.tab_manager:
            main.tab_manager.add_new_tab(url)

    def _open_urls_in_browser(self, urls):
        """Abre varias URLs en pestañas nuevas."""
        for url in urls:
            self._open_url_in_browser(url)

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
        """DEPRECATED - Trigger extraction instead"""
        # Now we just trigger the extraction
        self.extract_page_content_now()
    
    def on_context_toggled(self, checked):
        """Callback when context is toggled"""
        if checked:
            # Show message suggesting to extract content
            if not self.context_display.toPlainText() or self.context_display.toPlainText().startswith("Page content"):
                self.add_message_to_chat("System", "💡 Tip: Click 'Extract Page Content' to load the current page's content", "assistant")
        else:
            self.add_message_to_chat("System", "ℹ️ Page context disabled - AI will not receive page content", "assistant")
    
    def extract_page_content_now(self):
        """Extract page content and display it - SIMPLE VERSION"""
        try:
            # Show loading message
            self.context_display.setPlainText("⏳ Extracting page content...")
            self.extract_context_btn.setEnabled(False)

            # Get current tab
            main_window = self.window()
            if not hasattr(main_window, 'tab_manager'):
                self.context_display.setPlainText("❌ Error: Cannot access tab manager")
                self.extract_context_btn.setEnabled(True)
                return

            current_tab = main_window.tab_manager.tabs.currentWidget()
            if not current_tab or not hasattr(current_tab, 'page'):
                self.context_display.setPlainText("❌ Error: No active tab")
                self.extract_context_btn.setEnabled(True)
                return

            # Get URL and title
            current_url = current_tab.url().toString()
            current_title = current_tab.page().title()

            # Request HTML
            def on_html_received(html):
                try:
                    # Extract text content
                    extracted_text = self._simple_extract_text(html, current_url, current_title)

                    # Display in text edit
                    self.context_display.setPlainText(extracted_text)

                    # Add success message to chat
                    self.add_message_to_chat("System", f"✅ Page content extracted: {len(extracted_text)} characters", "assistant")

                except Exception as e:
                    error_msg = f"❌ Error extracting content: {str(e)}"
                    self.context_display.setPlainText(error_msg)
                    print(error_msg)
                    import traceback
                    traceback.print_exc()
                finally:
                    self.extract_context_btn.setEnabled(True)

            # Request HTML asynchronously
            current_tab.page().toHtml(on_html_received)

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            self.context_display.setPlainText(error_msg)
            print(error_msg)
            import traceback
            traceback.print_exc()
            self.extract_context_btn.setEnabled(True)

    def _simple_extract_text(self, html, url, title):
        """Simple and effective text extraction"""
        try:
            from bs4 import BeautifulSoup

            # Parse HTML
            soup = BeautifulSoup(html, 'lxml')

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript', 'form']):
                element.decompose()

            # Get all text
            text = soup.get_text(separator='\n', strip=True)

            # Clean up
            lines = []
            for line in text.split('\n'):
                line = line.strip()
                if line and len(line) > 2:  # Skip very short lines
                    lines.append(line)

            clean_text = '\n'.join(lines)

            # Build context
            context = f"""PAGE: {title}
URL: {url}

CONTENT:
{clean_text[:3000]}

{'[Content truncated - showing first 3000 characters]' if len(clean_text) > 3000 else '[End of content]'}"""

            return context

        except ImportError:
            # Fallback without BeautifulSoup
            import re
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'\s+', ' ', text).strip()

            return f"""PAGE: {title}
URL: {url}

CONTENT:
{text[:3000]}

{'[Content truncated]' if len(text) > 3000 else '[End]'}"""
        except Exception as e:
            return f"Error extracting text: {str(e)}"

    def get_current_context(self):
        """DEPRECATED - Now using context_display directly"""
        # This function is kept for compatibility but no longer used
        return self.context_display.toPlainText() if hasattr(self, 'context_display') else "" 