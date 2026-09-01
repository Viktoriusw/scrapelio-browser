#!/usr/bin/env python3
"""
Split View Plugin - Fixed side panel with custom web page
Allows users to keep a webpage visible while browsing in other tabs
"""

from plugins.plugin_base import PluginBase, PluginMetadata
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QLineEdit, QSplitter, QFrame,
                               QMessageBox, QGroupBox, QMenu)
from PySide6.QtGui import QAction
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtCore import Qt, QUrl, QSettings, Signal, QPoint


class SplitViewWidget(QWidget):
    """Enhanced widget for split view - includes independent navigation"""

    close_requested = Signal()       # Signal to request closing the split view
    open_in_new_tab = Signal(str)    # URL to open in main browser tab

    def __init__(self, browser_instance, parent=None):
        super().__init__(parent)
        self.browser = browser_instance
        self.is_focused = False
        self._hovered_link_url = ""  # tracks last hovered link for context menu

        # Load saved URL
        self.settings = QSettings("Tellectus", "SplitViewPlugin")
        self.saved_url = self.settings.value("last_url", "https://duckduckgo.com")

        self.init_ui()

        # Load the saved URL
        self.web_view.setUrl(QUrl(self.saved_url))

        # Install event filter to detect focus
        self.web_view.installEventFilter(self)
    def init_ui(self):
        """Initialize UI with toolbar and web view"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Toolbar ---
        toolbar = QFrame()
        toolbar.setObjectName("splitViewToolbar")
        toolbar.setFixedHeight(44)  # Force compact height

        # Use theme-neutral colors or inherit from global theme if possible
        # For now, hardcoding a clean look that works in both modes (standard Qt styling)
        toolbar.setStyleSheet("""
            QFrame#splitViewToolbar {
                background-color: #f0f0f0; 
                border-bottom: 1px solid #d0d0d0;
            }
        """) 
        # Attempt to use ThemeEngine if available (best effort)
        try:
            from ui.core.theme_engine import get_color
            bg = get_color("toolbar_background")
            border = get_color("border")
            toolbar.setStyleSheet(f"""
                QFrame#splitViewToolbar {{
                    background-color: {bg}; 
                    border-bottom: 1px solid {border};
                }}
            """)
        except ImportError:
            pass
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        toolbar_layout.setSpacing(4)

        # Navigation Buttons
        self.btn_back = QPushButton("◀")
        self.btn_back.setFixedSize(24, 24)
        self.btn_back.setToolTip("Back")
        self.btn_back.clicked.connect(lambda: self.web_view.back())

        self.btn_forward = QPushButton("▶")
        self.btn_forward.setFixedSize(24, 24)
        self.btn_forward.setToolTip("Forward")
        self.btn_forward.clicked.connect(lambda: self.web_view.forward())

        self.btn_reload = QPushButton("↻")
        self.btn_reload.setFixedSize(24, 24)
        self.btn_reload.setToolTip("Reload")
        self.btn_reload.clicked.connect(lambda: self.web_view.reload())

        toolbar_layout.addWidget(self.btn_back)
        toolbar_layout.addWidget(self.btn_forward)
        toolbar_layout.addWidget(self.btn_reload)

        # Address Bar
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL...")
        self.url_input.returnPressed.connect(self._on_url_input_return)
        # Style it like a pill
        self.url_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 12px;
                padding: 2px 8px;
                background: white;
            }
        """)
        try:
            from ui.core.theme_engine import get_color
            bg_input = get_color("input_background")
            text_input = get_color("text_primary")
            border_input = get_color("input_border")
            self.url_input.setStyleSheet(f"""
                QLineEdit {{
                    border: 1px solid {border_input};
                    border-radius: 12px;
                    padding: 4px 10px;
                    background: {bg_input};
                    color: {text_input};
                }}
            """)
        except:
            pass
        toolbar_layout.addWidget(self.url_input)

        # Close Button
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setToolTip("Close Split View")
        self.btn_close.clicked.connect(self.close_requested.emit)
        # Make it red on hover
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #ffcccc;
                color: #d00000;
            }
        """)

        toolbar_layout.addWidget(self.btn_close)

        layout.addWidget(toolbar)

        # --- Web View ---
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # Connect signals
        self.web_view.urlChanged.connect(self.on_url_changed)
        self.web_view.loadStarted.connect(self.on_load_started)
        self.web_view.loadFinished.connect(self.on_load_finished)
        self.web_view.titleChanged.connect(self.on_title_changed)

        # Rastrear el último link bajo el cursor para el menú contextual
        self.web_view.page().linkHovered.connect(self._on_link_hovered)

        # Menú contextual personalizado
        self.web_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.web_view.customContextMenuRequested.connect(self._show_context_menu)
    def eventFilter(self, obj, event):
        """Filter events - Split View is now passive, no focus changes"""
        return super().eventFilter(obj, event)
    def _on_url_input_return(self):
        """Handle URL input return pressed"""
        url = self.url_input.text().strip()
        self.load_url(url)
    def load_url(self, url):
        """Load a URL programmatically"""
        if isinstance(url, str):
            if not url.startswith(('http://', 'https://', 'file://', 'about:')):
                url = 'https://' + url
            self.web_view.setUrl(QUrl(url))
        elif isinstance(url, QUrl):
            self.web_view.setUrl(url)
    def on_url_changed(self, url):
        """Handle URL changed - update local address bar"""
        url_str = url.toString()
        self.url_input.setText(url_str)

        # Save persistence
        self.settings.setValue("last_url", url_str)
    def on_load_started(self):
        """Handle load started"""
        self.btn_reload.setText("×") # Stop icon
        self.btn_reload.clicked.disconnect()
        self.btn_reload.clicked.connect(lambda: self.web_view.stop())
    def on_load_finished(self, success):
        """Handle load finished"""
        self.btn_reload.setText("↻")
        try:
            self.btn_reload.clicked.disconnect()
        except:
            pass
        self.btn_reload.clicked.connect(lambda: self.web_view.reload())

        # Update styling based on success/fail?
    def on_title_changed(self, title):
        """Handle title changed"""
        # Could show tooltip or update something else
        pass
    def _on_link_hovered(self, url: str):
        """Guarda la URL del enlace sobre el que está el cursor."""
        self._hovered_link_url = url
    def _show_context_menu(self, pos: QPoint):
        """Muestra menú contextual personalizado con opción de abrir en nueva pestaña."""
        menu = QMenu(self)

        link_url = self._hovered_link_url.strip()
        current_url = self.web_view.url().toString()

        if link_url and link_url not in ("", "about:blank"):
            open_tab_action = QAction("🗗 Abrir enlace en nueva pestaña", self)
            open_tab_action.triggered.connect(lambda: self.open_in_new_tab.emit(link_url))
            menu.addAction(open_tab_action)
            menu.addSeparator()
        open_current_action = QAction("🗗 Abrir página actual en nueva pestaña", self)
        open_current_action.triggered.connect(lambda: self.open_in_new_tab.emit(current_url))
        menu.addAction(open_current_action)

        menu.addSeparator()

        back_action = QAction("◀ Atrás", self)
        back_action.setEnabled(self.web_view.history().canGoBack())
        back_action.triggered.connect(self.web_view.back)
        menu.addAction(back_action)

        forward_action = QAction("▶ Adelante", self)
        forward_action.setEnabled(self.web_view.history().canGoForward())
        forward_action.triggered.connect(self.web_view.forward)
        menu.addAction(forward_action)

        reload_action = QAction("↻ Recargar", self)
        reload_action.triggered.connect(self.web_view.reload)
        menu.addAction(reload_action)

        menu.exec(self.web_view.mapToGlobal(pos))
    def get_current_url(self):
        """Get current URL"""
        return self.web_view.url().toString()


class SplitViewSettingsWidget(QWidget):
    """Settings widget for Split View plugin"""

    def __init__(self, plugin_instance):
        super().__init__()
        self.plugin = plugin_instance
        self.init_ui()
    def init_ui(self):
        """Initialize settings UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("<h2>Split View Settings</h2>")
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "The Split View plugin allows you to keep a webpage visible "
            "while browsing in other tabs. It appears as a clean, borderless "
            "browser tab alongside your main tabs."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Status
        status_group = QGroupBox("Plugin Status")
        status_layout = QVBoxLayout()

        status_info = QLabel(
            f"<b>Status:</b> {'Enabled' if self.plugin.is_active() else 'Disabled'}"
        )
        status_layout.addWidget(status_info)

        if self.plugin.is_active():
            active_info = QLabel(
                f"<b>Split View Visible:</b> {'Yes' if self.plugin.split_view_visible else 'No'}"
            )
            status_layout.addWidget(active_info)

            if self.plugin.split_view_widget:
                current_url = self.plugin.split_view_widget.get_current_url()
                url_info = QLabel(f"<b>Current URL:</b> {current_url}")
                url_info.setWordWrap(True)
                status_layout.addWidget(url_info)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # URL Management
        url_group = QGroupBox("Change Split View URL")
        url_layout = QVBoxLayout()

        url_layout.addWidget(QLabel("Enter a new URL to load in the split view:"))

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")

        # Load current URL if split view is active
        if self.plugin.split_view_widget:
            current_url = self.plugin.split_view_widget.get_current_url()
            self.url_input.setText(current_url)
        url_layout.addWidget(self.url_input)

        button_layout = QHBoxLayout()

        load_url_btn = QPushButton("Load URL")
        load_url_btn.clicked.connect(self.load_url_in_split_view)
        button_layout.addWidget(load_url_btn)

        save_default_btn = QPushButton("Save as Default")
        save_default_btn.clicked.connect(self.save_as_default)
        button_layout.addWidget(save_default_btn)

        url_layout.addLayout(button_layout)

        url_group.setLayout(url_layout)
        layout.addWidget(url_group)

        # Usage instructions
        usage_group = QGroupBox("How to Use")
        usage_layout = QVBoxLayout()

        instructions = QLabel(
            "1. Click the split button in the right sidebar to toggle split view<br>"
            "2. The page will appear as a clean, borderless tab<br>"
            "3. Navigate normally in your other tabs<br>"
            "4. The split view stays visible and synchronized<br>"
            "5. Click the split button again to hide it"
        )
        instructions.setWordWrap(True)
        usage_layout.addWidget(instructions)

        usage_group.setLayout(usage_layout)
        layout.addWidget(usage_group)

        layout.addStretch()
    def load_url_in_split_view(self):
        """Load URL in split view"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "No URL", "Please enter a URL")
            return
        if self.plugin.split_view_widget:
            self.plugin.split_view_widget.load_url(url)
            QMessageBox.information(self, "Success", f"Loading: {url}")
        else:
            QMessageBox.warning(self, "Split View Not Active", 
                              "Please enable split view first by clicking the sidebar button")
    def save_as_default(self):
        """Save current URL as default"""
        url = self.url_input.text().strip()
        if url:
            settings = QSettings("Tellectus", "SplitViewPlugin")
            settings.setValue("last_url", url)
            QMessageBox.information(
                self,
                "Success",
                f"Default URL saved: {url}"
            )


class SplitViewPlugin(PluginBase):
    """
    Split View Plugin - Allows keeping a fixed webpage visible while browsing.

    Features:
    - Fixed side panel with web view
    - Customizable URL
    - Toggle visibility with sidebar button
    - Persistent settings
    """

    def __init__(self):
        super().__init__()
        self.browser = None
        self.split_view_widget = None
        self.sidebar_action = None
        self.main_splitter = None
        self.split_view_visible = False
    def get_metadata(self) -> PluginMetadata:
        """Define plugin metadata"""
        return PluginMetadata(
            id="split_view",
            name="Split View",
            version="2.1.0",
            author="Tellectus Team",
            description="Keep a webpage visible as a clean, borderless tab with full navigation integration. "
                       "Click the split view to control it with browser's back/forward buttons and URL bar.",
            min_browser_version="1.0.0",
            max_browser_version="999.0.0",
            dependencies=[],
            permissions=["toolbar", "ui_modification"]
        )
    def initialize(self, browser_instance) -> bool:
        """Initialize the plugin"""
        try:
            print("[SplitViewPlugin] Initializing...")
            self.browser = browser_instance

            # Create split view widget with browser instance
            self.split_view_widget = SplitViewWidget(self.browser)
            self.split_view_widget.setMinimumWidth(300)
            self.split_view_widget.setMaximumWidth(800)
            self.split_view_widget.hide()  # Hidden by default

            # Connect close signal from widget
            self.split_view_widget.close_requested.connect(self.hide_split_view)

            # Conectar "Abrir en nueva pestaña" al método del navegador principal
            self.split_view_widget.open_in_new_tab.connect(self._open_url_in_main_tab)

            # Find the main content splitter
            if hasattr(self.browser, 'centralWidget'):
                central = self.browser.centralWidget()
                if central:
                    # Find the splitter in the layout
                    for child in central.findChildren(QSplitter):
                        if child.orientation() == Qt.Horizontal:
                            self.main_splitter = child
                            break
                    if self.main_splitter:
                        # Insert split view widget into splitter
                        # Order: [sidebar, advanced_panel, tabs, split_view]
                        self.main_splitter.insertWidget(3, self.split_view_widget)
                        print("[SplitViewPlugin] Split view widget added to main splitter")
            # NO agregar botón al sidebar - se accede desde menú contextual de pestañas
            # El menú contextual se maneja en tabs.py

            # Connect to tab change events to lose focus when switching tabs
            if hasattr(self.browser, 'tab_manager') and hasattr(self.browser.tab_manager, 'tabs'):
                self.browser.tab_manager.tabs.currentChanged.connect(self._on_tab_changed)
                print("[SplitViewPlugin] Connected to tab change events")
            print("[SplitViewPlugin] Initialized successfully")
            return True
        except Exception as e:
            print(f"[SplitViewPlugin] Initialization error: {e}")
            import traceback
            traceback.print_exc()
            return False
    def _open_url_in_main_tab(self, url: str):
        """Abre la URL recibida en una nueva pestaña del navegador principal (fuera de Split View)."""
        if not url or not self.browser:
            return
        try:
            url = (url or "").strip()
            if not url:
                return
            # API real del navegador: tab_manager.add_new_tab(url)
            if hasattr(self.browser, "tab_manager") and hasattr(self.browser.tab_manager, "add_new_tab"):
                self.browser.tab_manager.add_new_tab(url)
                return
            if hasattr(self.browser, "open_new_tab"):
                self.browser.open_new_tab(url)
                return
            if hasattr(self.browser, "add_new_tab"):
                self.browser.add_new_tab(url)
                return
            print(f"[SplitView] No se encontró método para abrir nueva pestaña. URL: {url}")
        except Exception as e:
            print(f"[SplitView] Error al abrir en nueva pestaña: {e}")
    def shutdown(self) -> bool:
        """Shutdown the plugin"""
        try:
            print("[SplitViewPlugin] Shutting down...")

            # Hide split view
            if self.split_view_widget:
                self.split_view_widget.hide()
            # Remove split view widget from splitter
            if self.split_view_widget and self.main_splitter:
                self.main_splitter.widget(self.main_splitter.indexOf(self.split_view_widget)).deleteLater()
                self.split_view_widget = None
            self.browser = None
            self.split_view_visible = False

            print("[SplitViewPlugin] Shutdown complete")
            return True
        except Exception as e:
            print(f"[SplitViewPlugin] Shutdown error: {e}")
            return False
    def _on_tab_changed(self, index):
        """Called when user switches to a different tab"""
        print(f"[SplitViewPlugin] Tab changed to index {index}")

        # Force update URL bar with the new tab's URL
        if hasattr(self.browser, 'tab_manager') and hasattr(self.browser.tab_manager, 'tabs'):
            current_browser = self.browser.tab_manager.tabs.widget(index)
            if current_browser and hasattr(self.browser, 'url_bar'):
                self.browser.url_bar.setText(current_browser.url().toString())
                print(f"[SplitViewPlugin] Updated URL bar after tab change: {current_browser.url().toString()}")
    def get_settings_widget(self):
        """Return settings widget"""
        return SplitViewSettingsWidget(self)
    def open_tab_in_split_view(self, tab_index):
        """Open the specified tab URL in split view"""
        try:
            if not hasattr(self.browser, 'tab_manager'):
                return
            # Get the tab widget
            tab_widget = self.browser.tab_manager.tabs.widget(tab_index)
            if not tab_widget:
                return
            # Get the URL from the tab
            url = tab_widget.url().toString()

            # Load in split view
            if self.split_view_widget:
                self.split_view_widget.load_url(url)
            # Show split view if hidden
            if not self.split_view_visible:
                self.show_split_view()
            print(f"[SplitViewPlugin] Opened tab {tab_index} in split view: {url}")
        except Exception as e:
            print(f"[SplitViewPlugin] Error opening tab in split view: {e}")
            import traceback
            traceback.print_exc()
    def show_split_view(self):
        """Show split view"""
        try:
            if not self.split_view_widget:
                return
            # Show split view
            self.split_view_widget.show()
            self.split_view_visible = True

            # Adjust splitter sizes
            if self.main_splitter:
                total_width = self.main_splitter.width()
                split_view_width = 450  # Default width (slightly wider for better usability)

                sizes = self.main_splitter.sizes()
                if len(sizes) >= 4:
                    # Index 0: Sidebar (preserved)
                    # Index 1: Advanced Panel (preserved)
                    # Index 2: Tabs (Main Content)
                    # Index 3: Split View

                    # Calculate available space for content (excluding sidebar/advanced)
                    sidebar_width = sizes[0] + sizes[1]
                    available_width = total_width - sidebar_width

                    sizes[2] = available_width - split_view_width
                    sizes[3] = split_view_width

                    self.main_splitter.setSizes(sizes)
            print("[SplitViewPlugin] Split view shown")
        except Exception as e:
            print(f"[SplitViewPlugin] Error showing split view: {e}")
            import traceback
            traceback.print_exc()
    def hide_split_view(self):
        """Hide split view"""
        try:
            if not self.split_view_widget:
                return
            # Hide split view
            self.split_view_widget.hide()
            self.split_view_visible = False

            # Adjust splitter sizes
            if self.main_splitter:
                sizes = self.main_splitter.sizes()
                if len(sizes) >= 4:
                    # Give split view space back to tabs
                    sizes[2] = sizes[2] + sizes[3]
                    sizes[3] = 0
                    self.main_splitter.setSizes(sizes)
            print("[SplitViewPlugin] Split view hidden")
        except Exception as e:
            print(f"[SplitViewPlugin] Error hiding split view: {e}")
            import traceback
            traceback.print_exc()
    def toggle_split_view(self):
        """Toggle split view visibility"""
        if self.split_view_visible:
            self.hide_split_view()
        else:
            self.show_split_view()
    def on_browser_startup(self):
        """Called when browser starts"""
        print("[SplitViewPlugin] Browser startup detected")
    def on_browser_shutdown(self):
        """Called when browser shuts down"""
        print("[SplitViewPlugin] Browser shutdown detected")
        # Save state
        if self.split_view_widget:
            settings = QSettings("Tellectus", "SplitViewPlugin")
            settings.setValue("last_visible", self.split_view_visible)


# ============================================================================
# Plugin Module Interface - Required by UnifiedPluginManager
# ============================================================================

_plugin_instance = None


def initialize_plugin():
    """
    Initialize the plugin - required by UnifiedPluginManager.
    Creates and returns a plugin instance.
    """
    global _plugin_instance
    try:
        print("[split_view] initialize_plugin() called")
        _plugin_instance = SplitViewPlugin()
        print("[split_view] Plugin instance created successfully")
        return True
    except Exception as e:
        print(f"[split_view] Error creating plugin instance: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_plugin_instance():
    """Get the plugin instance"""
    return _plugin_instance


def shutdown_plugin():
    """Shutdown the plugin"""
    global _plugin_instance
    if _plugin_instance:
        _plugin_instance.shutdown()
        _plugin_instance = None
    return True
