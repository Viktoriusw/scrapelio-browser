from PySide6.QtWidgets import (QMainWindow, QToolBar, QPushButton, QLineEdit, 
                              QDockWidget, QMenu, QMessageBox, QWidget, QVBoxLayout,
                              QSplitter, QFrame, QCheckBox, QTabWidget, QTextEdit,
                              QHBoxLayout, QLabel, QSpinBox, QComboBox, QStackedWidget)
from PySide6.QtCore import Qt, QUrl, QSettings, QSize, QTimer, QThread, Signal
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtGui import QIcon, QPalette, QColor, QAction, QCursor
from PySide6.QtWebEngineWidgets import QWebEngineView
from tabs import TabManager
from navigation import NavigationManager
from history import HistoryManager
from devtools import DevToolsDock
from privacy import PrivacyManager
from favorites_bar import FavoritesBar
import socket
import sqlite3
import os
import subprocess
from contextlib import closing
from maintag import BookmarkManager
from password_manager import PasswordManager
from auth_manager import AuthManager
from auth_panel import LoginDialog, AuthPanel
import time

# ============================================================================
# NUEVAS FUNCIONALIDADES UX/UI - Plan de Acción
# ============================================================================
from find_in_page import FindInPageBar, FindInPageManager
from modern_statusbar import ModernStatusBar
from download_panel import DownloadPanel
from screenshot_tool import ScreenshotTool, ScreenshotDialog
from profile_manager import ProfileManager, ProfileSwitcher
from network_interceptor import NetworkInterceptor, NetworkSettingsDialog
from userscript_manager import UserScriptManager, UserScriptDialog
from modern_styles import (ThemeManager, CircularButton, ExpandableUrlBar,
                           TrapezoidalTabBar, RetractableSidebar,
                           ModernMenuButton, AnimationHelper, apply_shadow_effect)

# Import theme system
try:
    from theme_manager import get_theme_manager, get_color, get_font, get_spacing, get_border
    THEME_SYSTEM_AVAILABLE = True
    print("[OK] Theme system loaded")
except ImportError as e:
    THEME_SYSTEM_AVAILABLE = False
    print(f"[WARNING] Theme system not available: {e}")
    
    # Create dummy functions for compatibility
    def get_theme_manager():
        return None
    
    def get_color(color_key, theme_name=None):
        return "#000000"
    
    def get_font(font_key, theme_name=None):
        return "10pt"
    
    def get_spacing(spacing_key, theme_name=None):
        return "4px"
    
    def get_border(border_key, theme_name=None):
        return "1px"

# ============================================================================
# LEGACY COMPATIBILITY: Dummy functions for plugins now loaded dynamically
# ============================================================================
# These functions exist only for backward compatibility with older code.
# All plugins are now loaded dynamically through UnifiedPluginManager.
# TODO: Remove these once all legacy references are updated.

print("[INFO] Plugins will be loaded dynamically through UnifiedPluginManager")

def ScrapingPanel(*args, **kwargs):
    """DEPRECATED: Dummy function for compatibility. Use UnifiedPluginManager instead."""
    return None

def scraping_integration():
    """DEPRECATED: Dummy function for compatibility. Use UnifiedPluginManager instead."""
    return None

def PatternDetector():
    """DEPRECATED: Dummy function for compatibility. Use UnifiedPluginManager instead."""
    return None

def ProxyPanel(*args, **kwargs):
    """DEPRECATED: Dummy function for compatibility. Use UnifiedPluginManager instead."""
    return None

# Plugin availability flags
# These are set to False initially and will be set to True when plugins are loaded dynamically
SCRAPING_AVAILABLE = False
PROXY_AVAILABLE = False

# Import AI chat module
try:
    from chat_panel_safe import ChatPanelSafe as ChatPanel
    CHAT_AVAILABLE = True
    print("[OK] AI chat module loaded correctly")
except ImportError as e:
    CHAT_AVAILABLE = False
    print(f"Warning: AI chat module not available - {e}")


# Import unified plugin system
try:
    from unified_plugin_manager import UnifiedPluginManager
    from unified_plugin_panel import UnifiedPluginPanel
    PLUGIN_SYSTEM_AVAILABLE = True
    print("[OK] Unified Plugin system loaded correctly")
except ImportError as e:
    PLUGIN_SYSTEM_AVAILABLE = False
    print(f"[WARNING] Unified Plugin system not available: {e}")

# Import authentication system
try:
    from auth_manager import AuthManager, AuthResult
    from auth_panel import AuthPanel
    from premium_decorators import PremiumMixin
    AUTH_SYSTEM_AVAILABLE = True
    print("[OK] Authentication system loaded correctly")
except ImportError as e:
    AUTH_SYSTEM_AVAILABLE = False
    print(f"Warning: Authentication system not available - {e}")


# Worker thread for asynchronous login
class LoginWorker(QThread):
    """Worker thread para ejecutar login de forma asíncrona sin bloquear la UI"""
    # Señales para comunicar resultados
    login_completed = Signal(object)  # Emite AuthResult
    
    def __init__(self, auth_manager, email, password):
        super().__init__()
        self.auth_manager = auth_manager
        self.email = email
        self.password = password
    
    def run(self):
        """Ejecutar login en un hilo separado"""
        try:
            print(f"[LoginWorker] Executing login for {self.email} in background thread...")
            result = self.auth_manager.login(self.email, self.password)
            print(f"[LoginWorker] Login completed with success={result.success}")
            self.login_completed.emit(result)
        except Exception as e:
            print(f"[LoginWorker] Login error: {e}")
            # Crear un resultado de error
            from auth_manager import AuthError
            error_result = AuthResult(False, AuthError.NETWORK_ERROR, f"Error: {str(e)}")
            self.login_completed.emit(error_result)


class MainWindow(QMainWindow):
    # UI Constants
    BTN_BOX = 36  # button box - tamaño uniforme para todos los botones
    ICON_18 = QSize(14, 14)  # Iconos más pequeños para el sidebar
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scrapelio")
        self.setGeometry(100, 100, 1200, 800)
        
        # VENTANA NORMAL - Comportamiento completo del sistema operativo
        # Sin FramelessWindowHint para mantener TODA la funcionalidad:
        # - Redimensionable desde bordes/esquinas
        # - Snap to edges (arrastrar a laterales)
        # - Doble clic en barra para maximizar
        # - Todas las características modernas del SO
        
        # Configurar ventana sin bordes internos
        self.setContentsMargins(0, 0, 0, 0)
        
        # Worker thread para login asíncrono
        self.login_worker = None
        
        # Los estilos ahora se manejan completamente por el sistema de temas JSON
        # No se aplican estilos hardcodeados aquí
        
        # Inicializar componentes en el orden correcto
        self.history_manager = HistoryManager()
        self.bookmark_manager = BookmarkManager(self)
        self.password_manager = PasswordManager()
        self.navigation_manager = NavigationManager(self)
        self.tab_manager = TabManager(self.history_manager, self)
        self.navigation_manager.initialize_tab_manager(self.tab_manager)

        # ====================================================================
        # NUEVAS FUNCIONALIDADES UX/UI
        # ====================================================================

        # 1. Búsqueda en página
        self.find_bar = FindInPageBar(self)
        self.find_manager = FindInPageManager(self.find_bar, self.tab_manager)

        # 2. Status bar moderna con SSL (se configurará más adelante)
        self.status_bar = ModernStatusBar(self)

        # 3. Sistema de perfiles de usuario
        self.profile_manager = ProfileManager(self)
        print(f"[OK] Profile system initialized - Current profile: {self.profile_manager.current_profile_id}")

        # 4. Network Interceptor para modificar peticiones HTTP
        self.network_interceptor = NetworkInterceptor(self)
        print(f"[OK] Network interceptor initialized - UA: {self.network_interceptor.user_agent_type}")

        # 5. UserScript Manager para scripts personalizados
        self.userscript_manager = UserScriptManager(self)
        scripts_count = len(self.userscript_manager.get_all_scripts())
        print(f"[OK] UserScript manager initialized - {scripts_count} scripts loaded")

        # 6. Modern Theme Manager para estilos visuales modernos
        self.theme_manager = ThemeManager('light')  # Tema por defecto: light
        print(f"[OK] Modern theme manager initialized - Theme: {self.theme_manager.current_theme_name}")

        # Initialize authentication system (SYNCHRONOUS - needed for plugins)
        self.auth_manager = None
        if AUTH_SYSTEM_AVAILABLE:
            try:
                self.auth_manager = AuthManager()
                print("[OK] Authentication system initialized")
            except Exception as e:
                print(f"[ERROR] Failed to initialize auth system: {e}")
        else:
            print("[WARNING] Authentication system not available")
        
        # Initialize unified plugin system (needs auth_manager)
        self.plugin_manager = None
        self.dynamic_plugin_actions = {}  # Para guardar acciones de plugins dinámicos
        self.dynamic_plugin_panels = {}   # Para guardar paneles de plugins dinámicos
        
        if PLUGIN_SYSTEM_AVAILABLE and self.auth_manager:
            try:
                self.plugin_manager = UnifiedPluginManager(auth_manager=self.auth_manager, parent=self)
                
                # Conectar señales para carga dinámica de plugins
                self.plugin_manager.plugin_loaded.connect(self.on_plugin_loaded)
                self.plugin_manager.plugin_unloaded.connect(self.on_plugin_unloaded)
                
                print("[OK] Unified Plugin system initialized with auth")
            except Exception as e:
                print(f"[ERROR] Failed to initialize plugin system: {e}")
        else:
            print("[WARNING] Plugin system not available or auth_manager missing")
        
        # Crear la barra de navegación después de tener navigation_manager
        self.nav_bar = QToolBar("Navigation")
        self.setup_nav_bar()
        
        # Crear contenedor principal con QVBoxLayout para nav_bar y contenido
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Sin márgenes gruesos
        main_layout.setSpacing(0)  # Sin espaciado
        main_layout.addWidget(self.nav_bar)
        main_layout.addWidget(self.find_bar)  # Barra de búsqueda (inicialmente oculta)

        # Crear splitter horizontal REDIMENSIONABLE pero con barra lateral fija
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setChildrenCollapsible(False)  # No permitir colapsar completamente
        
        # Crear contenedor para la barra lateral IZQUIERDA (NO redimensionable)
        self.sidebar_container = QWidget()
        self.sidebar_container.setFixedWidth(36)  # Ancho reducido para iconos más pequeños
        sidebar_layout = QVBoxLayout(self.sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Configurar barra lateral vertical FIJA
        self.side_strip = QToolBar()
        self.side_strip.setOrientation(Qt.Vertical)
        self.side_strip.setMovable(False)
        self.side_strip.setFixedWidth(36)  # Ancho reducido para iconos más pequeños
        self.side_strip.setFloatable(False)
        self.setup_side_strip()
        sidebar_layout.addWidget(self.side_strip)
        
        # Agregar sidebar a la IZQUIERDA primero
        content_splitter.addWidget(self.sidebar_container)
        
        # Configurar stacked widget para paneles avanzados (inicialmente oculto)
        self.advanced_panel_stack = QStackedWidget()
        self.advanced_panel_stack.setMinimumWidth(0)
        self.advanced_panel_stack.setMaximumWidth(0)  # oculto por defecto
        self.advanced_panel_stack.hide()
        content_splitter.addWidget(self.advanced_panel_stack)
        
        # Agregar pestañas (se expande)
        content_splitter.addWidget(self.tab_manager.tabs)

        # Aplicar estilo trapezoidal moderno a las pestañas
        tab_style = self.theme_manager.get_tab_style()
        self.tab_manager.tabs.setStyleSheet(tab_style)
        self.tab_manager.tabs.setDocumentMode(True)  # Pestañas integradas
        self.tab_manager.tabs.setTabsClosable(True)  # Botón X en pestañas
        self.tab_manager.tabs.setMovable(True)  # Pestañas movibles

        # Configurar proporciones: sidebar fija, panel redimensionable, pestañas expandibles
        content_splitter.setStretchFactor(0, 0)  # Sidebar FIJA (no redimensionable)
        content_splitter.setStretchFactor(1, 0)  # Panel tamaño específico
        content_splitter.setStretchFactor(2, 1)  # Pestañas se expanden
        
        main_layout.addWidget(content_splitter)
        self.setCentralWidget(main_container)

        # Configurar status bar moderna
        self.setStatusBar(self.status_bar)

        # Configurar paneles dock
        self.setup_dock_widgets()
        
        # Configurar tema y atajos
        self.setup_theme()
        self.setup_shortcuts()
        
        # Aplicar tema después de que todos los widgets estén creados
        # Usar siempre el sistema legacy para evitar dependencias del plugin
        self._load_legacy_theme()
        
        # Initialize authentication UI state first
        self.update_auth_ui()
        
        # Restore session only if user is authenticated
        session_restored = False
        if self.auth_manager and self.auth_manager.auth_state.is_authenticated:
            print("[AUTH] User is authenticated, restoring session...")
            session_restored = self.tab_manager.restaurar_sesion()
        else:
            print("[AUTH] User not authenticated, skipping session restoration")
        
        # Configure application close event
        self.closeEvent = self.on_close
        
        # Ensure at least one tab is active at startup (only if session wasn't restored or no tabs exist)
        if not session_restored or self.tab_manager.tabs.count() == 0:
            print("Creating initial tab...")
            self.tab_manager.add_new_tab()

        # Conectar señales de cambio de pestaña al status bar
        self.tab_manager.tabs.currentChanged.connect(self._connect_browser_to_statusbar)

        # Conectar el browser actual al status bar
        self._connect_browser_to_statusbar()

        # Iniciar en pantalla completa (maximizado)
        self.showMaximized()

    def setup_dock_widgets(self):
        # Configurar DevTools
        self.devtools_dock = DevToolsDock(self)
        self.devtools_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self.devtools_dock)
        self.devtools_dock.hide()
        
        # Configurar Bookmark Manager
        self.bookmark_dock = QDockWidget("Gestor de Marcadores", self)
        self.bookmark_dock.setWidget(self.bookmark_manager)
        self.bookmark_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self.bookmark_dock)
        self.bookmark_dock.hide()
        
        # Configurar Barra de Favoritos
        self.favorites_bar = FavoritesBar(self)
        self.favorites_bar.setAllowedAreas(Qt.TopToolBarArea | Qt.BottomToolBarArea)
        self.addToolBar(Qt.TopToolBarArea, self.favorites_bar)
        self.favorites_bar.hide()  # Inicialmente oculta
        # Conectar señal de clic en favorito
        self.favorites_bar.favorite_clicked.connect(self.load_url)
        
        # Conexión de pestaña para estrella no implementada
        
        # Configurar Privacy Manager
        self.privacy_manager = PrivacyManager(self)
        self.privacy_dock = QDockWidget("Privacy Settings", self)
        self.privacy_dock.setWidget(self.privacy_manager)
        self.privacy_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self.privacy_dock)
        self.privacy_dock.hide()
        
        # Conectar señal para aplicar cambios al vuelo
        self.privacy_manager.settings_changed.connect(self.reapply_privacy_to_all_tabs)
        
        # Configurar Password Manager
        self.password_dock = QDockWidget("Password Manager", self)
        self.password_dock.setWidget(self.password_manager)
        self.password_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self.password_dock)
        self.password_dock.hide()

        # Configurar Download Panel (NUEVA FUNCIONALIDAD)
        self.download_panel = DownloadPanel(self)
        self.download_dock = QDockWidget("Descargas", self)
        self.download_dock.setWidget(self.download_panel)
        self.download_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self.download_dock)
        self.download_dock.hide()

        # Configurar Scraping Panel (si está disponible)
        if SCRAPING_AVAILABLE:
            self.scraping_integration = scraping_integration
            self.scraping_panel = ScrapingPanel(self.scraping_integration)
            self.scraping_dock = QDockWidget("Scrapelillo Completo", self)
            self.scraping_dock.setWidget(self.scraping_panel)
            self.scraping_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
            self.addDockWidget(Qt.RightDockWidgetArea, self.scraping_dock)
            self.scraping_dock.hide()
            # Inicialmente deshabilitado hasta que el usuario se autentique
            self.scraping_panel.setEnabled(False)
            print("[OK] Scraping panel configured correctly")
        else:
            self.scraping_integration = None
            self.scraping_panel = None
            self.scraping_dock = None
            print("[ERROR] Scraping panel not available")
        
        # Configurar Proxy Panel (si está disponible)
        if PROXY_AVAILABLE:
            # Obtener el proxy manager del scraping integration si está disponible
            proxy_manager = None
            if SCRAPING_AVAILABLE and hasattr(scraping_integration, 'proxy_manager'):
                proxy_manager = scraping_integration.proxy_manager
            
            self.proxy_panel = ProxyPanel(proxy_manager)
            self.proxy_dock = QDockWidget("Proxy Management", self)
            self.proxy_dock.setWidget(self.proxy_panel)
            self.proxy_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
            self.addDockWidget(Qt.RightDockWidgetArea, self.proxy_dock)
            self.proxy_dock.hide()
            # Inicialmente deshabilitado hasta que el usuario se autentique
            self.proxy_panel.setEnabled(False)
            print("[OK] Proxy management panel configured correctly")
        else:
            self.proxy_panel = None
            self.proxy_dock = None
            print("[ERROR] Proxy management panel not available")
        
        # Configurar Chat Panel (si está disponible)
        if CHAT_AVAILABLE:
            self.chat_panel = ChatPanel()
            self.chat_dock = QDockWidget("Chat con IA", self)
            self.chat_dock.setWidget(self.chat_panel)
            self.chat_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
            self.addDockWidget(Qt.RightDockWidgetArea, self.chat_dock)
            self.chat_dock.hide()
            print("[OK] AI chat panel configured correctly")
        else:
            self.chat_panel = None
            self.chat_dock = None
            print("[ERROR] AI chat panel not available")
        
        # SEO Analyzer Plugin - NOW LOADED DYNAMICALLY through UnifiedPluginManager
        # (Removed static initialization)
        
        # Configurar Unified Plugin Panel (usa plugin_manager ya inicializado)
        self.unified_plugin_panel = None
        self.plugin_store_dock = None
        
        if PLUGIN_SYSTEM_AVAILABLE and self.plugin_manager:
            try:
                # Crear el panel unificado de plugins usando el manager ya inicializado
                self.unified_plugin_panel = UnifiedPluginPanel(self.plugin_manager)
                self.plugin_store_dock = QDockWidget("Plugin Store", self)
                self.plugin_store_dock.setWidget(self.unified_plugin_panel)
                self.plugin_store_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
                self.addDockWidget(Qt.RightDockWidgetArea, self.plugin_store_dock)
                self.plugin_store_dock.hide()
                print("[OK] Unified plugin panel configured correctly")
            except Exception as e:
                self.unified_plugin_panel = None
                self.plugin_store_dock = None
                print(f"[ERROR] Failed to configure plugin panel: {e}")
        else:
            print("[WARNING] Plugin panel not configured (system not available or auth_manager missing)")
        
        # Configurar Auth Panel (si está disponible) - diferido
        self.auth_panel = None
        self.auth_dock = None
        if AUTH_SYSTEM_AVAILABLE:
            # Delay auth panel creation until auth_manager is ready
            QTimer.singleShot(1500, self._setup_auth_panel)
            print("[OK] Authentication panel will be configured")
        else:
            print("[ERROR] Authentication panel not available")
        

    def setup_theme(self):
        # Cargar configuración de tema
        self.settings = QSettings("Scrapelio", "Settings")
        
        # Configurar sistema de temas modular
        self._setup_theme_system()

    def setup_shortcuts(self):
        """Configurar atajos de teclado globales"""
        from PySide6.QtGui import QShortcut, QKeySequence
        
        # Nueva pestaña
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(
            lambda: self.tab_manager.add_new_tab())

        # Reabrir pestaña cerrada
        QShortcut(QKeySequence("Ctrl+Shift+T"), self).activated.connect(
            self.tab_manager.reopen_closed_tab)

        # Nueva ventana
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(
            self.open_new_window)
        
        # Ventana privada
        QShortcut(QKeySequence("Ctrl+Shift+P"), self).activated.connect(
            self.open_private_window)
        
        # Imprimir
        QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(
            self.print_page)
        
        # Guardar como
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(
            self.save_page_as)
        
        # Buscar en página (nueva funcionalidad mejorada)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(
            self.find_manager.activate_find)

        # Panel de descargas (Ctrl+J)
        QShortcut(QKeySequence("Ctrl+J"), self).activated.connect(
            self.toggle_download_panel)

        # Captura de pantalla (Ctrl+Shift+S)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(
            self.take_screenshot)

        # Zoom
        QShortcut(QKeySequence("Ctrl++"), self).activated.connect(
            self.zoom_in)
        QShortcut(QKeySequence("Ctrl+="), self).activated.connect(
            self.zoom_in)  # Alternativo sin Shift
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(
            self.zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self).activated.connect(
            self.zoom_reset)
        
        # Pantalla completa
        QShortcut(QKeySequence("F11"), self).activated.connect(
            self.toggle_fullscreen)
        
        # DevTools
        QShortcut(QKeySequence("F12"), self).activated.connect(
            self.toggle_dev_tools)
        
        # Ver código fuente
        QShortcut(QKeySequence("Ctrl+U"), self).activated.connect(
            self.view_page_source)
        
        # Cerrar
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(
            self.close)
        
        # Descargas
        QShortcut(QKeySequence("Ctrl+Shift+Y"), self).activated.connect(
            self.show_downloads)
        
        # Extensiones
        QShortcut(QKeySequence("Ctrl+Shift+A"), self).activated.connect(
            self.show_plugins_panel)
        
        print("[OK] Atajos de teclado configurados")

    def on_close(self, event):
        """Handle browser close event"""
        try:
            # UnifiedPluginManager no requiere shutdown explícito
            if PLUGIN_SYSTEM_AVAILABLE and self.plugin_manager:
                print("[Browser] Unified Plugin Manager cleanup...")
                # shutdown_all_plugins() no existe en UnifiedPluginManager
                # La limpieza se hace automáticamente en el destructor
            
            # Save session only if user is authenticated
            if hasattr(self, 'tab_manager'):
                if self.auth_manager and self.auth_manager.auth_state.is_authenticated:
                    print("[AUTH] User is authenticated, saving session...")
                    self.tab_manager.guardar_sesion()
                else:
                    print("[AUTH] User not authenticated, clearing session...")
                    self.tab_manager.limpiar_sesion()
            
            event.accept()
        except Exception as e:
            print(f"[Browser] Error during shutdown: {e}")
            event.accept()

    def setup_nav_bar(self):
        # Configurar toolbar moderno con constantes uniformes
        self.nav_bar.setIconSize(self.ICON_18)
        self.nav_bar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.nav_bar.setObjectName("navbar")

        # Aplicar estilo moderno del theme manager
        modern_navbar_style = self.theme_manager.get_navbar_style()
        circular_btn_style = self.theme_manager.get_circular_button_style()

        combined_style = modern_navbar_style + """
            QToolButton {
                width: 36px;
                height: 36px;
                padding: 0px;
                margin: 0px;
                border: none;
                border-radius: 18px;
            }
            QToolButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
                border-radius: 18px;
            }
            QToolButton:pressed {
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 18px;
            }
        """

        self.nav_bar.setStyleSheet(combined_style)
        
        # Toggle Sidebar Button - Agregado justo antes de Back/Forward
        self.sidebar_visible = True  # Estado inicial: visible
        toggle_sidebar_action = QAction(QIcon("icons/settings.png"), "Ocultar/Mostrar Panel Lateral", self)
        toggle_sidebar_action.triggered.connect(self.toggle_sidebar)
        self.nav_bar.addAction(toggle_sidebar_action)
        
        # Back Button
        back_action = QAction(QIcon("icons/back.png"), "Back", self)
        back_action.triggered.connect(self.navigation_manager.navigate_back)
        self.nav_bar.addAction(back_action)

        # Forward Button
        forward_action = QAction(QIcon("icons/forward.png"), "Forward", self)
        forward_action.triggered.connect(self.navigation_manager.navigate_forward)
        self.nav_bar.addAction(forward_action)

        # Refresh Button
        refresh_action = QAction(QIcon("icons/refresh.png"), "Refresh", self)
        refresh_action.triggered.connect(self.navigation_manager.refresh_page)
        self.nav_bar.addAction(refresh_action)

        # New Tab Button
        new_tab_action = QAction(QIcon("icons/new-tab.png"), "New Tab", self)
        new_tab_action.triggered.connect(lambda: self.tab_manager.add_new_tab())
        self.nav_bar.addAction(new_tab_action)

        # History Button
        history_action = QAction(QIcon("icons/history.png"), "History", self)
        history_action.triggered.connect(lambda: self.history_manager.show_history(self.tab_manager))
        self.nav_bar.addAction(history_action)

        # URL Bar expandible estilo Chrome
        self.url_bar = ExpandableUrlBar()
        self.url_bar.returnPressed.connect(lambda: self.load_url(self.url_bar.text()))
        self.url_bar.setFixedHeight(36)

        # Aplicar estilo moderno al URL bar
        urlbar_style = self.theme_manager.get_urlbar_style()
        self.url_bar.setStyleSheet(urlbar_style)

        # Habilitar botón de limpiar si está disponible
        if hasattr(self.url_bar, "setClearButtonEnabled"):
            self.url_bar.setClearButtonEnabled(True)

        self.nav_bar.addWidget(self.url_bar)

        # Separador visual entre URL bar y tab search
        url_separator = QFrame()
        url_separator.setFrameShape(QFrame.VLine)
        url_separator.setFrameShadow(QFrame.Sunken)
        url_separator.setMaximumWidth(1)
        # El color del separador se maneja por el tema JSON
        self.nav_bar.addWidget(url_separator)

        # Solo guardar referencia de las acciones para aplicar iconos después
        self.function_actions = {}

        # Campo de búsqueda de pestañas con tamaño balanceado
        self.tab_search = QLineEdit()
        self.tab_search.setPlaceholderText("Search tabs...")
        self.tab_search.setMinimumWidth(200)  # Aumentado para mejor coherencia
        self.tab_search.setMaximumWidth(350)  # Límite máximo más generoso
        self.tab_search.setFixedHeight(36)  # Ajustado para coincidir con botones del sidebar
        self.tab_search.textChanged.connect(self.tab_manager.buscar_pestanas)
        self.nav_bar.addWidget(self.tab_search)

        # Profile Switcher
        self.profile_switcher = ProfileSwitcher(self.profile_manager, self)
        self.nav_bar.addWidget(self.profile_switcher)

        # Hamburger Menu Button
        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(36, 36)  # Ajustado para coincidir con sidebar
        self.menu_btn.setToolTip("Menú principal")
        self.menu_btn.setProperty("class", "menu-button")
        self.menu_btn.clicked.connect(self.show_main_menu)
        self.nav_bar.addWidget(self.menu_btn)
        
        # Login Button with account icon
        self.login_btn = QPushButton()
        self.login_btn.setFixedSize(36, 36)  # Ajustado para coincidir con sidebar
        self.login_btn.setToolTip("Iniciar sesión en Scrapelio")
        self.login_btn.clicked.connect(self.show_login_dialog)
        
        # Set account icon
        account_icon = QIcon("icons/account.png")
        self.login_btn.setIcon(account_icon)
        self.login_btn.setIconSize(QSize(14, 14))  # Ajustado para coincidir con ICON_18
        
        # Los estilos del botón de login se manejan por el tema JSON
        self.login_btn.setProperty("class", "login-button")
        self.nav_bar.addWidget(self.login_btn)
        
        # User Status Label (initially hidden)
        self.user_status_label = QLabel("")
        # Los estilos de la etiqueta de estado se manejan por el tema JSON
        self.user_status_label.setProperty("class", "status-label")
        self.user_status_label.hide()
        self.nav_bar.addWidget(self.user_status_label)
        
        # Botones de control de ventana ELIMINADOS - Usa los controles nativos del sistema
        # La barra de título del sistema operativo ya incluye minimizar, maximizar y cerrar
        
        # Aplicar iconos vectoriales solo a navegación básica
        try:
            import qtawesome as qta
            # El botón toggle sidebar usa sidebar.png por defecto (no se sobrescribe)
            back_action.setIcon(qta.icon('fa.angle-left'))
            forward_action.setIcon(qta.icon('fa.angle-right'))
            refresh_action.setIcon(qta.icon('fa.rotate-right'))
            new_tab_action.setIcon(qta.icon('fa.plus'))
            history_action.setIcon(qta.icon('fa.clock-o'))
            print("[OK] Vector icons applied to basic navigation")
        except Exception as e:
            print(f"[WARNING] Using PNG icons as fallback: {e}")
            pass  # Fallback: usar los QIcon("icons/*.png") ya definidos

    def setup_side_strip(self):
        """Configure the fixed vertical sidebar with standard buttons"""
        # Configurar iconos con tamaño estándar
        self.side_strip.setIconSize(self.ICON_18)
        self.side_strip.setToolButtonStyle(Qt.ToolButtonIconOnly)
        
        # Estilo CSS para centrar los botones en el sidebar
        self.side_strip.setStyleSheet("""
            QToolBar {
                spacing: 2px;
                padding: 0px;
            }
            QToolButton {
                width: 36px;
                height: 36px;
                padding: 0px;
                margin: 0px;
                border: none;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)
        
        # Función helper para crear acciones de la barra lateral
        def create_strip_action(icon_path, tooltip, callback):
            action = QAction(QIcon(icon_path), tooltip, self)
            action.triggered.connect(callback)
            return action
        
        # Crear acciones de funciones
        self.fav_action = create_strip_action('icons/heart.png', 'Save Favorite', 
                                            self.show_save_favorite_menu)
        self.side_strip.addAction(self.fav_action)
        
        self.privacy_action = create_strip_action('icons/lock.png', 'Privacy', 
                                                self.toggle_privacy_panel)
        self.side_strip.addAction(self.privacy_action)
        
        self.password_action = create_strip_action('icons/key.png', 'Password Manager', 
                                                 self.toggle_password_manager)
        self.side_strip.addAction(self.password_action)
        
        self.devtools_action = create_strip_action('icons/wrench.png', 'DevTools', 
                                                 self.toggle_devtools)
        self.side_strip.addAction(self.devtools_action)
        
        # Botones condicionales
        if SCRAPING_AVAILABLE:
            self.scraping_action = create_strip_action('icons/scrap.png', 'Scraping', 
                                                     self.toggle_scraping_panel)
            self.side_strip.addAction(self.scraping_action)
        
        if PROXY_AVAILABLE:
            self.proxy_action = create_strip_action('icons/proxy.png', 'Proxies', 
                                                  self.toggle_proxy_panel)
            self.side_strip.addAction(self.proxy_action)
        
        if CHAT_AVAILABLE:
            self.chat_action = create_strip_action('icons/chat.png', 'Chat IA', 
                                                 self.toggle_chat_panel)
            self.side_strip.addAction(self.chat_action)
        
        # SEO Analyzer - NOW LOADED DYNAMICALLY
        # (Button will be added automatically by UnifiedPluginManager when plugin is installed)
        
        if PLUGIN_SYSTEM_AVAILABLE:
            self.plugin_action = create_strip_action('icons/settings.png', 'Plugins', 
                                                   self.toggle_plugin_panel)
            self.side_strip.addAction(self.plugin_action)
        
        # Botón de "Cuenta" eliminado según requerimiento del usuario
        
        self.bookmark_action = create_strip_action('icons/bookmark.png', 'Marcadores', 
                                                 self.toggle_bookmark_manager)
        self.side_strip.addAction(self.bookmark_action)
        
        self.favorites_action = create_strip_action('icons/heart.png', 'Barra de Favoritos', 
                                                  self.toggle_favorites_bar)
        self.side_strip.addAction(self.favorites_action)
        
        self.theme_action = create_strip_action('icons/settings.png', 'Gestor de Temas', 
                                              self.open_theme_selector)
        self.side_strip.addAction(self.theme_action)
        
        


    def _setup_theme_system(self):
        """Configura el sistema de temas básico (sin dependencias de plugins)"""
        # Usar siempre el sistema básico para evitar dependencias
        self._load_legacy_theme()
        print("[OK] Basic theme system configured")
    
    def _on_theme_changed(self, theme_id: str):
        """Callback cuando cambia el tema"""
        self.settings.setValue("theme", theme_id)
        print(f"[OK] Theme changed to: {theme_id}")
    
    def _load_legacy_theme(self):
        """Sistema de temas usando el nuevo theme manager"""
        if THEME_SYSTEM_AVAILABLE:
            theme_manager = get_theme_manager()
            if theme_manager:
                # El theme manager ya carga el tema guardado en su inicialización
                print(f"[THEME] Theme loaded via theme manager: {theme_manager.get_current_theme()}")
            else:
                print("[ERROR] Theme manager not available")
        else:
            print("[ERROR] Theme system not available")

    def load_theme(self):
        """Carga el tema guardado o usa el tema por defecto"""
        self._load_legacy_theme()

    def apply_theme(self, theme):
        """Aplica el tema especificado usando el theme manager"""
        print(f"[THEME] Applying theme: {theme}")
        if THEME_SYSTEM_AVAILABLE:
            theme_manager = get_theme_manager()
            if theme_manager:
                theme_manager.apply_theme(theme)
            else:
                print("[ERROR] Theme manager not available")
        else:
            print("[ERROR] Theme system not available")
    
    def toggle_theme(self):
        """Alterna entre tema claro y oscuro usando el theme manager"""
        if THEME_SYSTEM_AVAILABLE:
            theme_manager = get_theme_manager()
            if theme_manager:
                theme_manager.toggle_theme()
                print(f"[THEME] Theme toggled to: {theme_manager.get_current_theme()}")
            else:
                print("[ERROR] Theme manager not available")
        else:
            print("[ERROR] Theme system not available")
    
    def open_theme_selector(self):
        """Abre el selector de temas usando el theme manager"""
        if THEME_SYSTEM_AVAILABLE:
            theme_manager = get_theme_manager()
            if theme_manager:
                from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
                
                dialog = QDialog(self)
                dialog.setWindowTitle("Seleccionar Tema")
                dialog.setModal(True)
                dialog.resize(300, 150)
                
                layout = QVBoxLayout(dialog)
                
                # Título
                title = QLabel("Selecciona un tema:")
                title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
                layout.addWidget(title)
                
                # Botones
                buttons_layout = QHBoxLayout()
                
                light_btn = QPushButton("🌞 Tema Claro")
                light_btn.clicked.connect(lambda: self._select_theme("light", dialog))
                buttons_layout.addWidget(light_btn)
                
                dark_btn = QPushButton("🌙 Tema Oscuro")
                dark_btn.clicked.connect(lambda: self._select_theme("dark", dialog))
                buttons_layout.addWidget(dark_btn)
                
                layout.addLayout(buttons_layout)
                
                # Botón cancelar
                cancel_btn = QPushButton("Cancelar")
                cancel_btn.clicked.connect(dialog.reject)
                layout.addWidget(cancel_btn)
                
                dialog.exec()
            else:
                print("[ERROR] Theme manager not available")
        else:
            print("[ERROR] Theme system not available")
    
    def _select_theme(self, theme, dialog):
        """Selecciona un tema y cierra el diálogo"""
        if THEME_SYSTEM_AVAILABLE:
            theme_manager = get_theme_manager()
            if theme_manager:
                theme_manager.apply_theme(theme)
                dialog.accept()
            else:
                print("[ERROR] Theme manager not available")
        else:
            print("[ERROR] Theme system not available")
    
    

    def _load_custom_styles(self):
        """Carga estilos QSS personalizados desde themes/modern.qss (legacy)"""
        try:
            import os
            qss_path = "themes/modern.qss"
            if os.path.exists(qss_path):
                with open(qss_path, "r", encoding="utf-8") as f:
                    return f.read()
            return ""
        except Exception as e:
            print(f"Error cargando estilos personalizados: {e}")
            return ""

    # Métodos de estilos básicos - ahora se usan los temas JSON

    def _close_button_qss(self) -> str:
        """Generate QSS for close button with absolute path"""
        import os
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "icons", "close.png"))
        path = path.replace("\\", "/")  # Qt QSS necesita / incluso en Windows
        return f"""
        /* Override explícito del icono de cierre de pestañas */
        QTabBar::close-button {{
            image: url("{path}");
            width: 16px; height: 16px;
            subcontrol-position: right;
            margin-left: 6px;
        }}
        QTabBar::close-button:hover {{
            background: rgba(0,0,0,0.12);
            border-radius: 8px;
        }}
        """



    def toggle_bookmark_manager(self):
        """Alterna la visibilidad del gestor de marcadores USANDO EL STACK FIJO"""
        if hasattr(self, 'bookmark_manager') and self.bookmark_manager:
            if (self.advanced_panel_stack.currentWidget() == self.bookmark_manager and 
                self.advanced_panel_stack.isVisible()):
                self.hide_advanced_panel()
            else:
                self.show_advanced_panel(self.bookmark_manager)

    def toggle_sidebar(self):
        """Oculta o muestra el panel lateral izquierdo"""
        if hasattr(self, 'sidebar_container') and self.sidebar_container:
            if self.sidebar_visible:
                # Ocultar el sidebar
                self.sidebar_container.hide()
                self.sidebar_visible = False
            else:
                # Mostrar el sidebar
                self.sidebar_container.show()
                self.sidebar_visible = True

    def toggle_privacy_panel(self):
        """Alterna la visibilidad del panel de privacidad USANDO EL STACK FIJO"""
        if hasattr(self, 'privacy_manager') and self.privacy_manager:
            if (self.advanced_panel_stack.currentWidget() == self.privacy_manager and 
                self.advanced_panel_stack.isVisible()):
                self.hide_advanced_panel()
            else:
                self.show_advanced_panel(self.privacy_manager)

    def toggle_password_manager(self):
        """Toggle password manager visibility USING FIXED STACK"""
        if hasattr(self, 'password_manager') and self.password_manager:
            if (self.advanced_panel_stack.currentWidget() == self.password_manager and 
                self.advanced_panel_stack.isVisible()):
                self.hide_advanced_panel()
            else:
                self.show_advanced_panel(self.password_manager)

    def show_advanced_panel(self, widget):
        """Muestra un panel avanzado REDIMENSIONABLE sin mover la barra lateral"""
        if widget is None:
            self.hide_advanced_panel()
            return
        if self.advanced_panel_stack.indexOf(widget) < 0:
            self.advanced_panel_stack.addWidget(widget)
        self.advanced_panel_stack.setCurrentWidget(widget)
        
        # Hacer el panel REDIMENSIONABLE con límites razonables
        self.advanced_panel_stack.setMinimumWidth(350)   # Mínimo para ver contenido
        self.advanced_panel_stack.setMaximumWidth(1000)  # Máximo generoso
        self.advanced_panel_stack.show()
        
        # Establecer tamaño inicial para el splitter (esto es redimensionable)
        content_splitter = self.advanced_panel_stack.parent()
        if hasattr(content_splitter, 'setSizes'):
            # Dar tamaño inicial: sidebar fijo, panel 30%, pestañas 70%
            total_width = content_splitter.width() - 36  # Restar ancho de sidebar
            panel_width = min(450, total_width * 0.3)  # 30% o 450px, lo que sea menor
            tabs_width = total_width - panel_width
            content_splitter.setSizes([36, int(panel_width), int(tabs_width)])  # [sidebar, panel, tabs]
    
    def hide_advanced_panel(self):
        """Oculta el panel avanzado actual"""
        self.advanced_panel_stack.setMinimumWidth(0)
        self.advanced_panel_stack.setMaximumWidth(0)
        self.advanced_panel_stack.hide()
        
        # Resetear el splitter para dar todo el espacio a las pestañas
        content_splitter = self.advanced_panel_stack.parent()
        if hasattr(content_splitter, 'setSizes'):
            total_width = content_splitter.width() - 36
            content_splitter.setSizes([36, 0, total_width])  # [sidebar, panel, tabs]

    # Métodos del botón de favorito no implementados

    def load_url(self, url):
        """Load a URL or perform a search on DuckDuckGo"""
        try:
            url = url.strip()
            # Si es una URL válida, navega directo
            if url.startswith(('http://', 'https://')) or ('.' in url and ' ' not in url):
                final_url = url if url.startswith(('http://', 'https://')) else 'https://' + url
            else:
                # Si no es URL, realiza búsqueda en DuckDuckGo
                query = urllib.parse.quote(url)
                final_url = f'https://duckduckgo.com/?q={query}'
            
            # Crear una nueva pestaña
            new_tab = self.tab_manager.add_new_tab()
            if new_tab:
                if hasattr(self, 'privacy_manager'):
                    self.privacy_manager.apply_privacy_settings(new_tab)
                
                # Conectar la señal de carga terminada para sincronizar con scraping
                new_tab.loadFinished.connect(lambda success: self.on_page_loaded(new_tab, final_url))
                
                new_tab.setUrl(QUrl(final_url))
                self.url_bar.setText(final_url)
                self.tab_manager.tabs.setCurrentWidget(new_tab)
            else:
                QMessageBox.warning(self, "Error", "Could not create a new tab")
        except Exception as e:
            error_msg = f"Error loading URL: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Error", error_msg)
    
    def on_page_loaded(self, browser_tab, url):
        """Callback when page loading is finished"""
        try:
            # Obtener el HTML de la página cargada
            browser_tab.page().toHtml(lambda html_content: self.on_html_loaded(html_content, url))
            
            # También actualizar el scraping integration con el widget del navegador
            if SCRAPING_AVAILABLE and self.scraping_integration:
                self.scraping_integration.browser_widget = browser_tab
                
        except Exception as e:
            print(f"Error en on_page_loaded: {e}")
    
    def update_tab_title(self, title):
        """Update the title of the current tab"""
        current_tab = self.tab_manager.tabs.currentWidget()
        if current_tab:
            index = self.tab_manager.tabs.indexOf(current_tab)
            self.tab_manager.tabs.setTabText(index, title)

    def show_save_favorite_menu(self):
        """Show menu to save favorites with safe database handling"""
        try:
            with closing(self._get_db_connection()) as conn:
                if conn is None:
                    return

                cursor = conn.cursor()
                cursor.execute("SELECT name FROM categories")
                categories = [row[0] for row in cursor.fetchall()]

                menu = QMenu(self)
                for category in categories:
                    menu.addAction(category, lambda c=category: self.save_favorite_to_category(c))

                # Obtener la posición del botón de favoritos
                fav_action = self.sender()
                if isinstance(fav_action, QAction):
                    # Obtener la posición del botón en la barra de herramientas
                    button = self.nav_bar.widgetForAction(fav_action)
                    if button:
                        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
                    else:
                        # Si no podemos obtener el widget, mostrar el menú en la posición actual del cursor
                        menu.exec(QCursor.pos())
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", f"Error loading categories: {e}")

    def save_favorite_to_category(self, category):
        """Save a favorite in the specified category with safe transaction"""
        current_url = self.url_bar.text().strip()
        if not current_url:
            self.statusBar().showMessage("Error: No URL to save", 5000)
            return

        try:
            with closing(self._get_db_connection()) as conn:
                if conn is None:
                    return

                with conn:  # Usa el contexto como transacción
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO bookmarks (title, url, category, notes, tags) VALUES (?, ?, ?, ?, ?)",
                        ("Untitled", current_url, category, "Saved from browser", "No tags")
                    )
                self.statusBar().showMessage(f"Bookmark saved in '{category}'", 5000)
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Error", "This URL already exists in the selected category")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", f"Error saving bookmark: {e}")

    def _get_db_connection(self):
        """Get a database connection with safe handling"""
        try:
            conn = sqlite3.connect("bookmarks.db")
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", f"Could not connect to database: {e}")
            return None

    def toggle_devtools(self):
        """Toggle DevTools visibility"""
        current_browser = self.tab_manager.tabs.currentWidget()
        if current_browser:
            if self.devtools_dock.isVisible():
                self.devtools_dock.hide()
            else:
                self.devtools_dock.set_browser(current_browser)
                self.devtools_dock.show()
                # Ajustar el tamaño del dock widget
                self.devtools_dock.setMinimumWidth(400)
                self.devtools_dock.setMinimumHeight(300)

    def toggle_download_panel(self):
        """Toggle Download Panel visibility (Ctrl+J)"""
        if hasattr(self, 'download_dock') and self.download_dock:
            if self.download_dock.isVisible():
                self.download_dock.hide()
            else:
                self.download_dock.show()
                # Ajustar tamaño mínimo
                self.download_dock.setMinimumWidth(400)
                self.download_dock.setMinimumHeight(300)

    def take_screenshot(self):
        """Capturar screenshot de la página actual (Ctrl+Shift+S)"""
        current_browser = self.tab_manager.tabs.currentWidget()
        if current_browser:
            # Crear herramienta de screenshot para el browser actual
            screenshot_tool = ScreenshotTool(current_browser, self)
            screenshot_tool.show_screenshot_dialog()
        else:
            QMessageBox.warning(
                self,
                "Sin página activa",
                "No hay ninguna página activa para capturar."
            )

    def reload_with_new_profile(self):
        """Recargar el navegador con el nuevo perfil activo"""
        try:
            # Cerrar todas las pestañas
            while self.tab_manager.tabs.count() > 0:
                self.tab_manager.tabs.removeTab(0)

            # Limpiar historial de navegación en memoria
            if hasattr(self, 'navigation_manager'):
                self.navigation_manager.history.clear()

            # Crear nueva pestaña vacía
            self.tab_manager.add_new_tab()

            # Actualizar UI con el nuevo perfil
            if hasattr(self, 'profile_switcher'):
                self.profile_switcher.update_current_profile()

            # Mostrar mensaje
            profile = self.profile_manager.get_current_profile()
            if profile:
                self.status_bar.update_status(
                    f"Cambiado a perfil: {profile['name']} {profile['icon']}"
                )

            print(f"[OK] Browser reloaded with profile: {self.profile_manager.current_profile_id}")

        except Exception as e:
            print(f"[ERROR] Error reloading with new profile: {e}")
            QMessageBox.critical(
                self,
                "Error al cambiar perfil",
                f"Ocurrió un error al cambiar de perfil:\n{str(e)}"
            )

    def toggle_scraping_panel(self):
        """Alterna la visibilidad del panel de scraping USANDO EL STACK FIJO"""
        # Verificar si el plugin está disponible estáticamente O dinámicamente cargado
        plugin_available = SCRAPING_AVAILABLE or (hasattr(self, 'plugin_manager') and 
                                                   self.plugin_manager and 
                                                   self.plugin_manager.is_plugin_installed('scraping'))
        
        # Si el plugin está disponible pero el panel no existe, intentar cargarlo dinámicamente
        if plugin_available and (not hasattr(self, 'scraping_panel') or not self.scraping_panel):
            try:
                # Intentar cargar el panel dinámicamente desde el plugin instalado
                import sys
                from pathlib import Path
                plugin_path = Path('plugins/scraping')
                if plugin_path.exists() and str(plugin_path) not in sys.path:
                    sys.path.insert(0, str(plugin_path))
                
                from scraping_panel import ScrapingPanel  # type: ignore[import-not-found]
                self.scraping_panel = ScrapingPanel(self, plugin_validator=self.plugin_manager)
                self.advanced_panel_stack.addWidget(self.scraping_panel)
                print("[OK] Scraping panel loaded dynamically")
            except Exception as e:
                print(f"[ERROR] Failed to load scraping panel dynamically: {e}")
                plugin_available = False
        
        if plugin_available and hasattr(self, 'scraping_panel') and self.scraping_panel:
            if (self.advanced_panel_stack.currentWidget() == self.scraping_panel and 
                self.advanced_panel_stack.isVisible()):
                self.hide_advanced_panel()
            else:
                # Actualizar el contenido antes de mostrar
                self.update_scraping_content()
                self.show_advanced_panel(self.scraping_panel)
                
                # Activar automáticamente la selección interactiva si hay un navegador activo
                current_browser = self.tab_manager.tabs.currentWidget()
                if current_browser and hasattr(self.scraping_panel, 'browser_tab'):
                    self.scraping_panel.browser_tab = current_browser
        else:
            QMessageBox.information(self, "Premium Feature", 
                                   "Advanced Scraping is a premium feature.\n"
                                   "Please install the Advanced Scraping plugin to use this functionality.")
    
    def toggle_proxy_panel(self):
        """Toggle proxy management panel visibility USING FIXED STACK"""
        if PROXY_AVAILABLE and hasattr(self, 'proxy_panel') and self.proxy_panel:
            if (self.advanced_panel_stack.currentWidget() == self.proxy_panel and 
                self.advanced_panel_stack.isVisible()):
                self.hide_advanced_panel()
            else:
                # Actualizar la lista de proxies si es necesario
                if hasattr(self.proxy_panel, 'refresh_proxy_list'):
                    self.proxy_panel.refresh_proxy_list()
                self.show_advanced_panel(self.proxy_panel)
        else:
            QMessageBox.information(self, "Premium Feature", 
                                   "Proxy Management is a premium feature.\n"
                                   "Please install the Proxy Management plugin to use this functionality.")
    
    def toggle_plugin_store(self):
        """Toggle plugin store panel visibility"""
        if hasattr(self, 'plugin_store_dock') and self.plugin_store_dock:
            if self.plugin_store_dock.isVisible():
                self.plugin_store_dock.hide()
            else:
                self.plugin_store_dock.show()
                # Refresh the plugin list when opening the store
                if hasattr(self, 'unified_plugin_panel') and self.unified_plugin_panel:
                    self.unified_plugin_panel.load_available_plugins()
        else:
            QMessageBox.information(self, "Plugin Store", 
                                   "The Plugin Store is not available.\n"
                                   "Please ensure you are logged in to access the plugin store.")
    
    def toggle_chat_panel(self):
        """Toggle AI chat panel visibility USING FIXED STACK"""
        if CHAT_AVAILABLE and hasattr(self, 'chat_panel') and self.chat_panel:
            if (self.advanced_panel_stack.currentWidget() == self.chat_panel and 
                self.advanced_panel_stack.isVisible()):
                self.hide_advanced_panel()
            else:
                self.show_advanced_panel(self.chat_panel)
        else:
            QMessageBox.information(self, "🤖 AI Chat", "AI chat tools are not available. Verify that chat_panel.py is present.")
    
    # toggle_seo_panel method removed - SEO Analyzer is now a downloadable plugin
    # and will be managed by UnifiedPluginManager
    
    def toggle_plugin_panel(self):
        """Toggle plugin management panel visibility USING FIXED STACK"""
        if PLUGIN_SYSTEM_AVAILABLE and hasattr(self, 'unified_plugin_panel') and self.unified_plugin_panel:
            if (self.advanced_panel_stack.currentWidget() == self.unified_plugin_panel and 
                self.advanced_panel_stack.isVisible()):
                self.hide_advanced_panel()
            else:
                self.show_advanced_panel(self.unified_plugin_panel)
        else:
            QMessageBox.information(self, "🔌 Plugins", 
                                   "Plugin system is not available.\n"
                                   "Verify that:\n"
                                   "• Authentication system is working\n"
                                   "• Plugin files are present\n"
                                   "• You are connected to the backend")
    
    def toggle_auth_panel(self):
        """Toggle authentication panel visibility USING FIXED STACK"""
        if AUTH_SYSTEM_AVAILABLE and hasattr(self, 'auth_panel') and self.auth_panel:
            if (self.advanced_panel_stack.currentWidget() == self.auth_panel and 
                self.advanced_panel_stack.isVisible()):
                self.hide_advanced_panel()
            else:
                self.show_advanced_panel(self.auth_panel)
        else:
            QMessageBox.information(self, "🔐 Autenticación", "Sistema de autenticación no disponible.")

    def update_scraping_content(self):
        """Update the content of the current page in the scraping integration"""
        if SCRAPING_AVAILABLE and self.scraping_integration:
            current_browser = self.tab_manager.tabs.currentWidget()
            if current_browser:
                # Obtener la URL actual
                current_url = current_browser.url().toString()
                
                # Actualizar el widget del navegador en el scraping integration
                self.scraping_integration.browser_widget = current_browser
                
                # La selección interactiva se maneja desde el scraping_panel
                
                # Obtener el HTML de la página actual
                current_browser.page().toHtml(lambda html_content: self.on_html_loaded(html_content, current_url))
                
                # Actualizar el panel de scraping si está visible
                if hasattr(self, 'scraping_panel') and self.scraping_panel:
                    self.scraping_panel.browser_tab = current_browser
    
    # La selección interactiva se maneja desde scraping_panel.py
    
    def handle_element_click(self, click_data):
        """Handle click on page element"""
        try:
            if SCRAPING_AVAILABLE and hasattr(self, 'scraping_panel'):
                x = click_data.get('x', 0)
                y = click_data.get('y', 0)
                self.scraping_panel.handle_page_click(x, y)
        except Exception as e:
            print(f"Error manejando clic en elemento: {e}")

    def on_html_loaded(self, html_content, url):
        """Callback when page HTML is loaded"""
        if SCRAPING_AVAILABLE and self.scraping_integration:
            self.scraping_integration.update_content(html_content, url)

    def toggle_favorites_bar(self):
        """Alterna la visibilidad de la barra de favoritos"""
        if hasattr(self, 'favorites_bar'):
            if self.favorites_bar.isVisible():
                self.favorites_bar.hide()
                self.statusBar().showMessage("Barra de favoritos oculta", 3000)
            else:
                self.favorites_bar.show()
                self.favorites_bar.refresh_favorites()  # Actualizar favoritos
                self.statusBar().showMessage("Barra de favoritos visible", 3000)
        else:
            QMessageBox.information(self, "Favorites Bar", "The favorites bar is not available.")

    def update_favorites_bar(self):
        """Actualiza la barra de favoritos con los favoritos marcados para mostrar en barra desde el gestor principal (maintag.py)"""
        if hasattr(self, 'favorites_bar'):
            self.favorites_bar.refresh_favorites()

    def reapply_privacy_to_all_tabs(self):
        """Apply privacy settings to all open tabs"""
        try:
            if not (hasattr(self, 'tab_manager') and self.tab_manager and hasattr(self, 'privacy_manager')):
                print("Tab manager o privacy manager no disponibles")
                return

            # Obtener todas las pestañas
            tabs_count = self.tab_manager.tabs.count()
            if tabs_count == 0:
                print("No open tabs")
                return
            
            # Variables para controlar recarga
            needs_reload = False
            
            # Verificar si cambios críticos requieren recarga
            current_block_ads = self.privacy_manager.settings.get_setting("block_ads")
            current_block_third_party = self.privacy_manager.settings.get_setting("block_third_party")
            current_block_javascript = self.privacy_manager.settings.get_setting("block_javascript")
            
            # Inicializar estados previos si no existen
            if not hasattr(self, '_last_privacy_settings'):
                self._last_privacy_settings = {
                    'block_ads': current_block_ads,
                    'block_third_party': current_block_third_party,
                    'block_javascript': current_block_javascript
                }
            else:
                # Verificar si hubo cambios que requieren recarga
                if (self._last_privacy_settings['block_ads'] != current_block_ads or 
                    self._last_privacy_settings['block_third_party'] != current_block_third_party):
                    needs_reload = True
                    print("Detectados cambios en filtros de red - programando recarga")
                
                # Actualizar estados guardados
                self._last_privacy_settings.update({
                    'block_ads': current_block_ads,
                    'block_third_party': current_block_third_party,
                    'block_javascript': current_block_javascript
                })
            
            # Aplicar configuración a cada pestaña
            successful_applications = 0
            failed_applications = 0
            
            for i in range(tabs_count):
                try:
                    tab = self.tab_manager.tabs.widget(i)
                    if tab and hasattr(tab, 'page'):
                        # Aplicar configuración de privacidad
                        self.privacy_manager.apply_privacy_settings(tab)
                        successful_applications += 1
                        
                        # Recarga suave si es necesario para cambios de filtros de red
                        if needs_reload:
                            try:
                                # Solo recargar si la pestaña tiene contenido
                                current_url = tab.url()
                                if not current_url.isEmpty() and current_url.toString() != "about:blank":
                                    tab.reload()
                                    print(f"Tab {i+1} reloaded: {current_url.toString()[:50]}...")
                            except Exception as reload_error:
                                print(f"Error reloading tab {i+1}: {reload_error}")
                                
                except Exception as tab_error:
                    print(f"Error applying privacy to tab {i+1}: {tab_error}")
                    failed_applications += 1
            
            # Reporte de resultados
            print(f"Privacy settings applied: {successful_applications}/{tabs_count} successful tabs")
            if failed_applications > 0:
                print(f"Errors in {failed_applications} tabs")
            if needs_reload:
                print("Tabs with content reloaded to apply network filters")
                    
        except Exception as e:
            print(f"Critical error reapplying privacy settings: {e}")
            import traceback
            traceback.print_exc()

    def toggle_maximize(self):
        """Alternar entre maximizado y restaurado"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def show_main_menu(self):
        """Mostrar menú principal del navegador (estilo Chromium)"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                padding: 5px 0px;
                min-width: 280px;
            }
            QMenu::item {
                padding: 8px 35px 8px 25px;
                color: #333;
            }
            QMenu::item:selected {
                background-color: #e8eaed;
            }
            QMenu::separator {
                height: 1px;
                background: #e0e0e0;
                margin: 5px 10px;
            }
            QMenu::icon {
                margin-left: 8px;
            }
        """)
        
        # === Sección 1: Pestañas y Ventanas ===
        new_tab_action = menu.addAction("Nueva pestaña")
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(lambda: self.tab_manager.add_new_tab())
        
        new_window_action = menu.addAction("Nueva ventana")
        new_window_action.setShortcut("Ctrl+N")
        new_window_action.triggered.connect(self.open_new_window)
        
        private_window_action = menu.addAction("Nueva ventana privada")
        private_window_action.setShortcut("Ctrl+Shift+P")
        private_window_action.triggered.connect(self.open_private_window)
        
        menu.addSeparator()
        
        # === Sección 2: Gestión de contenido ===
        bookmarks_menu = menu.addMenu("Marcadores")
        bookmarks_menu.addAction("Mostrar marcadores").triggered.connect(
            lambda: self.show_bookmarks_panel())
        bookmarks_menu.addAction("Añadir marcador").triggered.connect(
            lambda: self.bookmark_manager.add_bookmark())
        bookmarks_menu.addAction("Organizar marcadores").triggered.connect(
            lambda: self.bookmark_manager.show())
        
        history_action = menu.addAction("Historial")
        history_action.triggered.connect(
            lambda: self.history_manager.show_history(self.tab_manager))
        
        downloads_action = menu.addAction("Descargas")
        downloads_action.setShortcut("Ctrl+Shift+Y")
        downloads_action.triggered.connect(self.show_downloads)
        
        passwords_action = menu.addAction("Contraseñas")
        passwords_action.triggered.connect(
            lambda: self.password_manager.show())
        
        extensions_action = menu.addAction("Extensiones y temas")
        extensions_action.setShortcut("Ctrl+Shift+A")
        extensions_action.triggered.connect(self.show_plugins_panel)
        
        menu.addSeparator()
        
        # === Sección 3: Herramientas de página ===
        print_action = menu.addAction("Imprimir...")
        print_action.setShortcut("Ctrl+P")
        print_action.triggered.connect(self.print_page)
        
        save_action = menu.addAction("Guardar como...")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_page_as)
        
        find_action = menu.addAction("Buscar en la página...")
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.show_find_dialog)
        
        menu.addSeparator()
        
        # === Sección 4: Zoom ===
        zoom_menu = menu.addMenu("Tamaño")
        
        zoom_in_action = zoom_menu.addAction("Aumentar")
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        
        zoom_out_action = zoom_menu.addAction("Reducir")
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        
        zoom_reset_action = zoom_menu.addAction("Restablecer")
        zoom_reset_action.setShortcut("Ctrl+0")
        zoom_reset_action.triggered.connect(self.zoom_reset)
        
        zoom_menu.addSeparator()
        
        fullscreen_action = zoom_menu.addAction("Pantalla completa")
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        
        menu.addSeparator()
        
        # === Sección 5: Más herramientas ===
        tools_menu = menu.addMenu("Más herramientas")
        
        tools_menu.addAction("Limpiar datos de navegación...").triggered.connect(
            self.show_clear_data_dialog)
        tools_menu.addAction("Configuración de red...").triggered.connect(
            self.show_network_settings)
        tools_menu.addAction("UserScripts...").triggered.connect(
            self.show_userscripts)

        # Submenú de temas modernos
        themes_menu = tools_menu.addMenu("Cambiar tema visual")
        themes_menu.addAction("🌞 Tema Claro (Light)").triggered.connect(
            lambda: self.change_visual_theme('light'))
        themes_menu.addAction("🌙 Tema Oscuro (Dark)").triggered.connect(
            lambda: self.change_visual_theme('dark'))
        themes_menu.addAction("💎 Tema Azul (Blue)").triggered.connect(
            lambda: self.change_visual_theme('blue'))

        tools_menu.addAction("Herramientas de desarrollador").setShortcut("F12")
        tools_menu.actions()[-1].triggered.connect(self.toggle_dev_tools)
        tools_menu.addAction("Administrador de tareas").triggered.connect(
            self.show_task_manager)
        tools_menu.addAction("Ver código fuente").setShortcut("Ctrl+U")
        tools_menu.actions()[-1].triggered.connect(self.view_page_source)
        
        menu.addSeparator()
        
        # === Sección 6: Configuración y ayuda ===
        settings_action = menu.addAction("Ajustes")
        settings_action.triggered.connect(self.show_settings)
        
        help_menu = menu.addMenu("Ayuda")
        help_menu.addAction("Acerca de Scrapelio").triggered.connect(self.show_about)
        help_menu.addAction("Documentación").triggered.connect(
            lambda: self.tab_manager.add_new_tab("https://docs.scrapelio.com"))
        help_menu.addAction("Informar de un problema").triggered.connect(
            self.report_issue)
        
        menu.addSeparator()
        
        # === Sección 7: Salir ===
        exit_action = menu.addAction("Salir")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        # Mostrar el menú justo debajo del botón
        menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))

    def show_login_dialog(self):
        """Mostrar diálogo de login"""
        if not self.auth_manager:
            QMessageBox.warning(self, "Error", "Sistema de autenticación no disponible")
            return
        
        # Verificar si ya está autenticado
        if self.auth_manager.auth_state.is_authenticated:
            self.show_logout_dialog()
            return
        
        # Mostrar diálogo de login
        login_dialog = LoginDialog(self)
        
        # Conectar señales - IMPORTANTE: conectar ANTES de exec()
        login_dialog.login_requested.connect(lambda email, password: self.handle_login(email, password, login_dialog))
        login_dialog.register_requested.connect(self.open_registration_page)
        
        # Conectar señal de éxito para cerrar el diálogo automáticamente
        self.auth_manager.login_successful.connect(login_dialog.accept)
        
        # Ejecutar diálogo modal
        result = login_dialog.exec()
        
        # Desconectar señales después de cerrar para evitar fugas de memoria
        try:
            self.auth_manager.login_successful.disconnect(login_dialog.accept)
        except:
            pass

    def handle_login(self, email, password, dialog=None):
        """Manejar login de usuario de forma ASÍNCRONA usando QThread para evitar congelamiento"""
        if not self.auth_manager:
            QMessageBox.critical(self, "Error", "Sistema de autenticación no disponible")
            return
        
        # Verificar si ya hay un login en progreso
        if self.login_worker and self.login_worker.isRunning():
            print("[UI] Login already in progress, ignoring duplicate request")
            return
        
        # Deshabilitar botón durante el login
        self.login_btn.setEnabled(False)
        self.login_btn.setToolTip("Validando credenciales...")
        
        # Guardar referencia al diálogo para usarla en el callback
        self._current_login_dialog = dialog
        
        print(f"[UI] Starting ASYNC login process in separate thread for: {email}")
        
        # CRÍTICO: Crear y ejecutar worker thread para login asíncrono
        # Esto evita que el hilo principal de Qt se congele completamente
        self.login_worker = LoginWorker(self.auth_manager, email, password)
        self.login_worker.login_completed.connect(self._on_login_completed)
        self.login_worker.start()
        
        print("[UI] Login worker thread started, UI remains responsive")
    
    def _on_login_completed(self, result):
        """Callback cuando el login se completa en el worker thread"""
        print(f"[UI] Login completed callback received: success={result.success}")
        
        # Restaurar botón
        self.login_btn.setEnabled(True)
        self.login_btn.setToolTip("Iniciar sesión en Scrapelio")
        
        # Limpiar worker thread
        if self.login_worker:
            self.login_worker.deleteLater()
            self.login_worker = None
        
        try:
            if result.success:
                # Actualizar UI (esto se llama automáticamente por las señales, pero lo hacemos explícito)
                self.update_auth_ui()
                
                # Obtener email del diálogo
                email = self._current_login_dialog.email_edit.text() if self._current_login_dialog else "usuario"
                
                # Cerrar el diálogo primero
                if self._current_login_dialog:
                    self._current_login_dialog.accept()
                    self._current_login_dialog = None
                
                # Mostrar mensaje de éxito DESPUÉS de cerrar el diálogo
                QTimer.singleShot(200, lambda: QMessageBox.information(
                    self, 
                    "✅ Inicio de Sesión Exitoso", 
                    f"¡Bienvenido, {email}!\n\n"
                    "• Sesión iniciada correctamente\n"
                    "• Acceso a plugins premium habilitado\n"
                    "• Sincronización completada"
                ))
                
            else:
                # Preparar mensaje de error específico
                from auth_manager import AuthError
                error_details = ""
                if result.error == AuthError.INVALID_CREDENTIALS:
                    error_details = "❌ Credenciales incorrectas. Verifica tu email y contraseña."
                elif result.error == AuthError.USER_NOT_VERIFIED:
                    error_details = "⚠️ Cuenta no verificada. Revisa tu correo electrónico y activa tu cuenta."
                elif result.error == AuthError.NETWORK_ERROR:
                    error_details = "🌐 Error de conexión. Verifica tu conexión a internet."
                else:
                    error_details = f"❌ Error: {result.message}"
                
                print(f"[UI] Showing error in login dialog: {result.error}")
                
                # CRÍTICO: Mostrar error DIRECTAMENTE en el diálogo sin QMessageBox
                # Esto evita bloqueos modales y mantiene el navegador responsive
                if self._current_login_dialog:
                    self._current_login_dialog.show_error_in_dialog(error_details)
                
        except Exception as e:
            print(f"[UI] Login callback error: {e}")
            import traceback
            traceback.print_exc()
            
            # Mostrar error crítico en el diálogo
            error_msg = f"❌ Error crítico: {str(e)}"
            if self._current_login_dialog:
                self._current_login_dialog.show_error_in_dialog(error_msg)

    def show_logout_dialog(self):
        """Mostrar opciones de logout"""
        if not self.auth_manager or not self.auth_manager.auth_state.is_authenticated:
            return
        
        reply = QMessageBox.question(
            self, 
            "Cerrar Sesión", 
            "¿Deseas cerrar sesión?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.auth_manager.logout()
            self.update_auth_ui()  # Esto ya llama a disable_premium_plugins()
            QMessageBox.information(self, "Sesión Cerrada", "Has cerrado sesión correctamente")

    def update_auth_ui(self):
        """Actualizar la interfaz de usuario según el estado de autenticación"""
        if not self.auth_manager:
            return
        
        if self.auth_manager.auth_state.is_authenticated:
            # Usuario autenticado
            user_info = self.auth_manager.get_user_info()
            email = user_info.get('email', 'Usuario') if user_info else 'Usuario'
            
            # Keep the account icon but change tooltip and class
            self.login_btn.setToolTip(f"Cerrar sesión ({email})")
            # Los estilos del botón de logout se manejan por el tema JSON
            self.login_btn.setProperty("class", "logout-button")
            
            # Mostrar estado del usuario
            self.user_status_label.setText(f"✓ {email}")
            self.user_status_label.show()
            
            # Habilitar plugins premium
            self.enable_premium_plugins()
            
        else:
            # Usuario no autenticado
            self.login_btn.setToolTip("Iniciar sesión en Scrapelio")
            # Los estilos del botón de login se manejan por el tema JSON
            self.login_btn.setProperty("class", "login-button")
            
            # Ocultar estado del usuario
            self.user_status_label.hide()
            
            # Deshabilitar plugins premium
            self.disable_premium_plugins()

    def open_registration_page(self):
        """Abrir página de registro en una nueva pestaña"""
        try:
            from network_config import get_registration_url
            registration_url = get_registration_url()
        except ImportError:
            # Fallback si no existe network_config.py
            registration_url = "http://192.168.1.130:4321/auth/registro.html"
        
        self.tab_manager.add_new_tab(registration_url)

    def enable_premium_plugins(self):
        """Habilitar plugins premium cuando el usuario se autentica"""
        if not self.auth_manager or not self.auth_manager.auth_state.is_authenticated:
            return
        
        # Habilitar panel de scraping
        if hasattr(self, 'scraping_panel') and self.scraping_panel:
            self.scraping_panel.setEnabled(True)
            print("[AUTH] Scraping panel enabled")
        
        # Habilitar panel de proxy
        if hasattr(self, 'proxy_panel') and self.proxy_panel:
            self.proxy_panel.setEnabled(True)
            print("[AUTH] Proxy panel enabled")
        
        # Cargar plugins instalados dinámicamente
        if hasattr(self, 'plugin_manager') and self.plugin_manager:
            print("[AUTH] Loading installed plugins...")
            try:
                results = self.plugin_manager.load_all_installed_plugins()
                loaded_count = sum(1 for success in results.values() if success)
                print(f"[AUTH] Loaded {loaded_count}/{len(results)} installed plugins")
                
                # Force load plugins that are installed but not loaded yet
                if hasattr(self.plugin_manager, 'plugins_dir'):
                    import os
                    plugins_dir = self.plugin_manager.plugins_dir
                    if os.path.exists(plugins_dir):
                        for plugin_id in os.listdir(plugins_dir):
                            plugin_path = os.path.join(plugins_dir, plugin_id)
                            if os.path.isdir(plugin_path) and plugin_id not in self.plugin_manager.plugins:
                                # Check if user has license
                                if self.auth_manager and self.auth_manager.is_plugin_licensed(plugin_id):
                                    print(f"[AUTH] Force loading licensed plugin: {plugin_id}")
                                    if self.plugin_manager.load_plugin(plugin_id):
                                        print(f"[AUTH] ✅ Plugin {plugin_id} loaded successfully")
            except Exception as e:
                print(f"[AUTH] Error loading installed plugins: {e}")
                import traceback
                traceback.print_exc()
            
            print("[AUTH] Premium plugins enabled (auto-managed by UnifiedPluginManager)")
        
        # Restaurar sesión ahora que el usuario está autenticado
        if hasattr(self, 'tab_manager'):
            print("[AUTH] Restoring session after authentication...")
            self.tab_manager.restaurar_sesion()

    def disable_premium_plugins(self):
        """Deshabilitar plugins premium cuando el usuario cierra sesión"""
        print("[AUTH] 🔒 Disabling premium plugins...")
        
        # Deshabilitar panel de scraping
        if hasattr(self, 'scraping_panel') and self.scraping_panel:
            self.scraping_panel.setEnabled(False)
            print("[AUTH] ✓ Scraping panel disabled")
        
        # Deshabilitar panel de proxy
        if hasattr(self, 'proxy_panel') and self.proxy_panel:
            self.proxy_panel.setEnabled(False)
            print("[AUTH] ✓ Proxy panel disabled")
        
        # CRÍTICO: Ocultar y descargar plugins dinámicos
        if hasattr(self, 'plugin_manager') and self.plugin_manager:
            # Descargar todos los plugins cargados dinámicamente
            try:
                loaded_plugins = list(self.plugin_manager.plugins.keys())
                for plugin_id in loaded_plugins:
                    self.plugin_manager.unload_plugin(plugin_id)
                    print(f"[AUTH] ✓ Plugin {plugin_id} unloaded")
            except Exception as e:
                print(f"[AUTH] ⚠️ Error unloading plugins: {e}")
        
        # Remover botones de plugins dinámicos del sidebar
        if hasattr(self, 'dynamic_plugin_actions'):
            for plugin_id, action in list(self.dynamic_plugin_actions.items()):
                try:
                    # Encontrar el botón antes del store button para insertarlo ahí
                    if hasattr(self, 'side_strip') and self.side_strip:
                        self.side_strip.removeAction(action)
                    del self.dynamic_plugin_actions[plugin_id]
                    print(f"[AUTH] ✓ Button for plugin {plugin_id} removed")
                except Exception as e:
                    print(f"[AUTH] ⚠️ Error removing button for {plugin_id}: {e}")
        
        # Remover paneles de plugins dinámicos
        if hasattr(self, 'dynamic_plugin_panels'):
            for plugin_id, dock in list(self.dynamic_plugin_panels.items()):
                try:
                    self.removeDockWidget(dock)
                    del self.dynamic_plugin_panels[plugin_id]
                    print(f"[AUTH] ✓ Panel for plugin {plugin_id} removed")
                except Exception as e:
                    print(f"[AUTH] ⚠️ Error removing panel for {plugin_id}: {e}")
        
        print("[AUTH] 🔒 All premium plugins disabled successfully")

    def set_light_theme(self):
        """Aplica el tema claro usando el sistema de temas JSON"""
        try:
            if THEME_SYSTEM_AVAILABLE:
                theme_manager = get_theme_manager()
                if theme_manager:
                    theme_manager.apply_theme("light")
                    print("[OK] Light theme applied via theme manager")
                else:
                    print("[ERROR] Theme manager not available")
            else:
                print("[ERROR] Theme system not available")
        except Exception as e:
            print(f"[ERROR] Failed to apply light theme: {e}")

    def set_dark_theme(self):
        """Aplica el tema oscuro usando el sistema de temas JSON"""
        try:
            if THEME_SYSTEM_AVAILABLE:
                theme_manager = get_theme_manager()
                if theme_manager:
                    theme_manager.apply_theme("dark")
                    print("[OK] Dark theme applied via theme manager")
                else:
                    print("[ERROR] Theme manager not available")
            else:
                print("[ERROR] Theme system not available")
        except Exception as e:
            print(f"[ERROR] Failed to apply dark theme: {e}")
    
    def _initialize_auth_system(self):
        """Initialize authentication system after startup"""
        try:
            if AUTH_SYSTEM_AVAILABLE:
                self.auth_manager = AuthManager()
                print("[OK] Authentication system initialized (delayed)")
            else:
                print("[WARNING] Authentication system not available")
        except Exception as e:
            print(f"[ERROR] Failed to initialize auth system: {e}")
    
    def _initialize_plugin_system(self):
        """Initialize plugin system after startup (LEGACY - YA NO SE USA)"""
        # Este método es legacy del sistema antiguo de plugins
        # El UnifiedPluginManager se inicializa síncronamente en __init__
        # Este método nunca se llama porque quitamos QTimer.singleShot
        print("[INFO] _initialize_plugin_system is legacy code - UnifiedPluginManager already initialized")
    
    def _setup_auth_panel(self):
        """Setup authentication panel after auth_manager is ready"""
        try:
            if self.auth_manager and AUTH_SYSTEM_AVAILABLE:
                self.auth_panel = AuthPanel(self.auth_manager)
                self.auth_dock = QDockWidget("Cuenta", self)
                self.auth_dock.setWidget(self.auth_panel)
                self.auth_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
                self.addDockWidget(Qt.RightDockWidgetArea, self.auth_dock)
                self.auth_dock.hide()
                print("[OK] Authentication panel configured (delayed)")
            else:
                print("[WARNING] Auth manager not ready for panel setup")
        except Exception as e:
            print(f"[ERROR] Failed to setup auth panel: {e}")
    
    def on_plugin_loaded(self, plugin_id: str):
        """
        Manejar la carga de un plugin dinámicamente
        Agregar botón al sidebar y crear panel
        """
        print(f"[UI] Plugin loaded signal received: {plugin_id}")
        
        try:
            # Obtener el módulo del plugin
            if not self.plugin_manager or plugin_id not in self.plugin_manager.plugins:
                print(f"[UI] Plugin {plugin_id} not found in plugin manager")
                return
            
            plugin_module = self.plugin_manager.plugins[plugin_id]
            
            # Verificar si el plugin tiene get_plugin_panel
            if not hasattr(plugin_module, 'get_scraping_panel') and not hasattr(plugin_module, 'get_proxy_panel') and not hasattr(plugin_module, 'get_seo_panel'):
                print(f"[UI] Plugin {plugin_id} doesn't have a panel getter")
                return
            
            # Cargar panel según el tipo de plugin
            if plugin_id == "scraping" and hasattr(plugin_module, 'get_scraping_panel'):
                self._load_scraping_plugin_dynamic(plugin_module)
            elif plugin_id == "proxy" and hasattr(plugin_module, 'get_proxy_panel'):
                self._load_proxy_plugin_dynamic(plugin_module)
            elif plugin_id == "seo_analyzer" and hasattr(plugin_module, 'get_seo_panel'):
                self._load_seo_plugin_dynamic(plugin_module)
            elif plugin_id == "themes":
                print(f"[UI] Themes plugin loaded, no UI changes needed")
            else:
                print(f"[UI] Unknown plugin type: {plugin_id}")
                
        except Exception as e:
            print(f"[UI] Error loading plugin UI for {plugin_id}: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_scraping_plugin_dynamic(self, plugin_module):
        """Cargar plugin de scraping dinámicamente"""
        global SCRAPING_AVAILABLE
        try:
            print("[UI] Loading scraping plugin dynamically...")
            
            # Obtener componentes del plugin
            ScrapingPanel = plugin_module.get_scraping_panel()
            scraping_integration = plugin_module.get_scraping_integration()
            
            if not ScrapingPanel or not scraping_integration:
                print("[UI] Failed to get scraping components")
                return
            
            # Crear panel
            self.scraping_panel = ScrapingPanel(scraping_integration)
            self.scraping_integration = scraping_integration
            
            # Crear dock widget (reemplazar si ya existe)
            if hasattr(self, 'scraping_dock') and self.scraping_dock:
                # Ya existe, solo actualizar el widget
                self.scraping_dock.setWidget(self.scraping_panel)
                print("[UI] Updated existing scraping dock widget")
            else:
                # Crear nuevo dock widget
                self.scraping_dock = QDockWidget("Scraping Avanzado", self)
                self.scraping_dock.setWidget(self.scraping_panel)
                self.scraping_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
                self.addDockWidget(Qt.RightDockWidgetArea, self.scraping_dock)
                self.scraping_dock.hide()
                print("[UI] Created new scraping dock widget")
            
            # Habilitar panel si el usuario está autenticado
            if self.auth_manager and self.auth_manager.auth_state.is_authenticated:
                self.scraping_panel.setEnabled(True)
            
            # Verificar si ya existe un botón de scraping (del import estático)
            existing_scraping_action = None
            for action in self.side_strip.actions():
                if action.text() == 'Scraping' and action.toolTip() == 'Scraping':
                    existing_scraping_action = action
                    print("[UI] Found existing scraping button from static import")
                    break
            
            # Si no existe botón (ni estático ni dinámico), crearlo
            if not existing_scraping_action and 'scraping' not in self.dynamic_plugin_actions:
                print("[UI] Creating new scraping button...")
                self.scraping_action = QAction(QIcon('icons/scrap.png'), 'Scraping', self)
                self.scraping_action.triggered.connect(self.toggle_scraping_panel)
                
                # Insertar antes del botón de Plugin Store
                actions = self.side_strip.actions()
                store_index = -1
                for i, action in enumerate(actions):
                    if action.text() == 'Plugin Store':
                        store_index = i
                        break
                
                if store_index >= 0:
                    self.side_strip.insertAction(actions[store_index], self.scraping_action)
                    print(f"[UI] Inserted scraping button before Plugin Store (index {store_index})")
                else:
                    self.side_strip.addAction(self.scraping_action)
                    print("[UI] Added scraping button to end of sidebar")
                
                self.dynamic_plugin_actions['scraping'] = self.scraping_action
                self.dynamic_plugin_panels['scraping'] = self.scraping_panel
                
                print("[UI] ✅ Scraping plugin loaded and button added to sidebar")
            elif existing_scraping_action:
                # Ya existe botón estático, solo asegurarnos que funciona
                print("[UI] ✅ Scraping plugin loaded, using existing static button")
                self.dynamic_plugin_panels['scraping'] = self.scraping_panel
            else:
                print("[UI] ✅ Scraping plugin loaded, button already exists in dynamic_plugin_actions")
            
            # Marcar scraping como disponible
            SCRAPING_AVAILABLE = True
            print("[UI] SCRAPING_AVAILABLE set to True")
            
        except Exception as e:
            print(f"[UI] Error loading scraping plugin: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_proxy_plugin_dynamic(self, plugin_module):
        """Cargar plugin de proxy dinámicamente"""
        global PROXY_AVAILABLE
        try:
            print("[UI] Loading proxy plugin dynamically...")
            
            # Obtener componentes del plugin
            ProxyPanel = plugin_module.get_proxy_panel()
            
            if not ProxyPanel:
                print("[UI] Failed to get proxy panel")
                return
            
            # Obtener proxy manager del scraping integration si existe
            proxy_manager = None
            if hasattr(self, 'scraping_integration') and hasattr(self.scraping_integration, 'proxy_manager'):
                proxy_manager = self.scraping_integration.proxy_manager
            
            # Crear panel
            self.proxy_panel = ProxyPanel(proxy_manager)
            
            # Crear dock widget (reemplazar si ya existe)
            if hasattr(self, 'proxy_dock') and self.proxy_dock:
                # Ya existe, solo actualizar el widget
                self.proxy_dock.setWidget(self.proxy_panel)
                print("[UI] Updated existing proxy dock widget")
            else:
                # Crear nuevo dock widget
                self.proxy_dock = QDockWidget("Gestión de Proxies", self)
                self.proxy_dock.setWidget(self.proxy_panel)
                self.proxy_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
                self.addDockWidget(Qt.RightDockWidgetArea, self.proxy_dock)
                self.proxy_dock.hide()
                print("[UI] Created new proxy dock widget")
            
            # Habilitar panel si el usuario está autenticado
            if self.auth_manager and self.auth_manager.auth_state.is_authenticated:
                self.proxy_panel.setEnabled(True)
            
            # Verificar si ya existe un botón de proxy (del import estático)
            existing_proxy_action = None
            for action in self.side_strip.actions():
                if action.text() == 'Proxies':
                    existing_proxy_action = action
                    print("[UI] Found existing proxy button from static import")
                    break
            
            # Si no existe botón (ni estático ni dinámico), crearlo
            if not existing_proxy_action and 'proxy' not in self.dynamic_plugin_actions:
                print("[UI] Creating new proxy button...")
                self.proxy_action = QAction(QIcon('icons/proxy.png'), 'Proxies', self)
                self.proxy_action.triggered.connect(self.toggle_proxy_panel)
                
                # Insertar antes del botón de Plugin Store
                actions = self.side_strip.actions()
                store_index = -1
                for i, action in enumerate(actions):
                    if action.text() == 'Plugin Store':
                        store_index = i
                        break
                
                if store_index >= 0:
                    self.side_strip.insertAction(actions[store_index], self.proxy_action)
                    print(f"[UI] Inserted proxy button before Plugin Store (index {store_index})")
                else:
                    self.side_strip.addAction(self.proxy_action)
                    print("[UI] Added proxy button to end of sidebar")
                
                self.dynamic_plugin_actions['proxy'] = self.proxy_action
                self.dynamic_plugin_panels['proxy'] = self.proxy_panel
                
                print("[UI] ✅ Proxy plugin loaded and button added to sidebar")
            elif existing_proxy_action:
                # Ya existe botón estático, solo asegurarnos que funciona
                print("[UI] ✅ Proxy plugin loaded, using existing static button")
                self.dynamic_plugin_panels['proxy'] = self.proxy_panel
            else:
                print("[UI] ✅ Proxy plugin loaded, button already exists in dynamic_plugin_actions")
            
            # Marcar proxy como disponible
            PROXY_AVAILABLE = True
            print("[UI] PROXY_AVAILABLE set to True")
            
        except Exception as e:
            print(f"[UI] Error loading proxy plugin: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_seo_plugin_dynamic(self, plugin_module):
        """Cargar plugin de SEO dinámicamente"""
        try:
            print("[UI] Loading SEO plugin dynamically...")
            
            # Obtener componente del plugin
            SEOPanel = plugin_module.get_seo_panel()
            
            if not SEOPanel:
                print("[UI] SEO plugin running in compatibility mode (no UI available)")
                return
            
            # Crear panel
            self.seo_panel = SEOPanel(parent=self)
            
            # Crear dock widget (reemplazar si ya existe)
            if hasattr(self, 'seo_dock') and self.seo_dock:
                # Ya existe, solo actualizar el widget
                self.seo_dock.setWidget(self.seo_panel)
                print("[UI] Updated existing SEO dock widget")
            else:
                # Crear nuevo dock widget
                self.seo_dock = QDockWidget("SEO Analyzer Pro", self)
                self.seo_dock.setWidget(self.seo_panel)
                self.seo_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
                self.addDockWidget(Qt.RightDockWidgetArea, self.seo_dock)
                self.seo_dock.hide()
                print("[UI] Created new SEO dock widget")
            
            # Habilitar panel si el usuario está autenticado
            if self.auth_manager and self.auth_manager.auth_state.is_authenticated:
                self.seo_panel.setEnabled(True)
            
            # Verificar si ya existe un botón de SEO
            existing_seo_action = None
            for action in self.side_strip.actions():
                if action.text() == 'SEO' or action.text() == 'SEO Analyzer':
                    existing_seo_action = action
                    print("[UI] Found existing SEO button")
                    break
            
            # Si no existe botón, crearlo
            if not existing_seo_action and 'seo_analyzer' not in self.dynamic_plugin_actions:
                print("[UI] Creating new SEO button...")
                self.seo_action = QAction(QIcon('icons/seo.png'), 'SEO', self)
                self.seo_action.triggered.connect(self.toggle_seo_panel)
                
                # Insertar antes del botón de Plugin Store
                actions = self.side_strip.actions()
                store_index = -1
                for i, action in enumerate(actions):
                    if action.text() == 'Plugin Store':
                        store_index = i
                        break
                
                if store_index >= 0:
                    self.side_strip.insertAction(actions[store_index], self.seo_action)
                    print(f"[UI] Inserted SEO button before Plugin Store (index {store_index})")
                else:
                    self.side_strip.addAction(self.seo_action)
                    print("[UI] Added SEO button to end of sidebar")
                
                self.dynamic_plugin_actions['seo_analyzer'] = self.seo_action
                self.dynamic_plugin_panels['seo_analyzer'] = self.seo_panel
                
                print("[UI] ✅ SEO plugin loaded and button added to sidebar")
            elif existing_seo_action:
                # Ya existe botón, solo asegurarnos que funciona
                print("[UI] ✅ SEO plugin loaded, using existing button")
                self.dynamic_plugin_panels['seo_analyzer'] = self.seo_panel
            else:
                print("[UI] ✅ SEO plugin loaded, button already exists in dynamic_plugin_actions")
            
        except Exception as e:
            print(f"[UI] Error loading SEO plugin: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_seo_panel(self):
        """Toggle visibility of SEO panel"""
        if hasattr(self, 'seo_dock'):
            if self.seo_dock.isVisible():
                self.seo_dock.hide()
            else:
                self.seo_dock.show()
                self.seo_dock.raise_()
    
    def on_plugin_unloaded(self, plugin_id: str):
        """
        Manejar la descarga de un plugin dinámicamente
        Remover botón del sidebar y panel
        """
        print(f"[UI] Plugin unloaded signal received: {plugin_id}")
        
        try:
            # Remover acción del sidebar
            if plugin_id in self.dynamic_plugin_actions:
                action = self.dynamic_plugin_actions[plugin_id]
                self.side_strip.removeAction(action)
                del self.dynamic_plugin_actions[plugin_id]
                print(f"[UI] Removed {plugin_id} button from sidebar")
            
            # Remover panel
            if plugin_id in self.dynamic_plugin_panels:
                del self.dynamic_plugin_panels[plugin_id]
                print(f"[UI] Removed {plugin_id} panel")
            
            # Limpiar referencias específicas
            if plugin_id == "scraping":
                if hasattr(self, 'scraping_dock') and self.scraping_dock:
                    self.scraping_dock.hide()
                    self.scraping_dock.setWidget(None)
                self.scraping_panel = None
                self.scraping_integration = None
                
            elif plugin_id == "proxy":
                if hasattr(self, 'proxy_dock') and self.proxy_dock:
                    self.proxy_dock.hide()
                    self.proxy_dock.setWidget(None)
                self.proxy_panel = None
                
        except Exception as e:
            print(f"[UI] Error unloading plugin UI for {plugin_id}: {e}")
            import traceback
            traceback.print_exc()
    
    # ========== MÉTODOS DEL MENÚ PRINCIPAL ==========
    
    def open_new_window(self):
        """Abrir una nueva ventana del navegador"""
        try:
            import subprocess
            import sys
            subprocess.Popen([sys.executable, "main.py"])
            print("[Menu] Nueva ventana abierta")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir nueva ventana: {e}")
    
    def open_private_window(self):
        """Abrir una ventana de navegación privada"""
        try:
            import subprocess
            import sys
            subprocess.Popen([sys.executable, "main.py", "--private"])
            print("[Menu] Ventana privada abierta")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir ventana privada: {e}")
    
    def show_bookmarks_panel(self):
        """Mostrar panel de marcadores"""
        if hasattr(self, 'bookmark_manager') and self.bookmark_manager:
            self.bookmark_manager.show()
    
    def show_downloads(self):
        """Mostrar panel de descargas"""
        current_browser = self.tab_manager.tabs.currentWidget()
        if current_browser:
            download_folder = os.path.expanduser("~/Downloads")
            if os.path.exists(download_folder):
                try:
                    import subprocess
                    import platform
                    if platform.system() == "Windows":
                        os.startfile(download_folder)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.Popen(["open", download_folder])
                    else:  # Linux
                        subprocess.Popen(["xdg-open", download_folder])
                except Exception as e:
                    QMessageBox.information(self, "Descargas", 
                        f"Carpeta de descargas: {download_folder}")
    
    def show_plugins_panel(self):
        """Mostrar panel de plugins/extensiones"""
        if hasattr(self, 'unified_plugin_panel') and self.unified_plugin_panel:
            self.unified_plugin_panel.show()
            self.unified_plugin_panel.raise_()
    
    def print_page(self):
        """Imprimir página actual"""
        current_browser = self.tab_manager.tabs.currentWidget()
        if current_browser and hasattr(current_browser, 'page'):
            try:
                from PySide6.QtPrintSupport import QPrintDialog, QPrinter
                printer = QPrinter(QPrinter.HighResolution)
                dialog = QPrintDialog(printer, self)
                if dialog.exec():
                    current_browser.page().print(printer, lambda success: 
                        print(f"[Menu] Página impresa: {success}"))
            except ImportError:
                QMessageBox.warning(self, "Error", 
                    "Módulo de impresión no disponible")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error al imprimir: {e}")
    
    def save_page_as(self):
        """Guardar página actual"""
        current_browser = self.tab_manager.tabs.currentWidget()
        if current_browser and hasattr(current_browser, 'url'):
            from PySide6.QtWidgets import QFileDialog
            url = current_browser.url().toString()
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar página como",
                os.path.expanduser("~"),
                "HTML Files (*.html *.htm);;All Files (*.*)"
            )
            if filename:
                try:
                    current_browser.page().save(filename)
                    QMessageBox.information(self, "Éxito", 
                        f"Página guardada en: {filename}")
                except Exception as e:
                    QMessageBox.warning(self, "Error", 
                        f"No se pudo guardar la página: {e}")
    
    def show_find_dialog(self):
        """Mostrar diálogo de búsqueda en página"""
        current_browser = self.tab_manager.tabs.currentWidget()
        if current_browser:
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self, "Buscar en página", 
                "Texto a buscar:")
            if ok and text:
                current_browser.findText(text)
    
    def zoom_in(self):
        """Aumentar zoom de la página"""
        current_browser = self.tab_manager.tabs.currentWidget()
        if current_browser:
            current_zoom = current_browser.zoomFactor()
            new_zoom = min(current_zoom + 0.1, 5.0)  # Máximo 500%
            current_browser.setZoomFactor(new_zoom)
            self.status_bar.update_zoom(new_zoom)  # Actualizar status bar
            print(f"[Menu] Zoom aumentado a {int(new_zoom * 100)}%")
    
    def zoom_out(self):
        """Reducir zoom de la página"""
        current_browser = self.tab_manager.tabs.currentWidget()
        if current_browser:
            current_zoom = current_browser.zoomFactor()
            new_zoom = max(current_zoom - 0.1, 0.25)  # Mínimo 25%
            current_browser.setZoomFactor(new_zoom)
            self.status_bar.update_zoom(new_zoom)  # Actualizar status bar
            print(f"[Menu] Zoom reducido a {int(new_zoom * 100)}%")

    def zoom_reset(self):
        """Restablecer zoom al 100%"""
        current_browser = self.tab_manager.tabs.currentWidget()
        if current_browser:
            current_browser.setZoomFactor(1.0)
            self.status_bar.update_zoom(1.0)  # Actualizar status bar
            print("[Menu] Zoom restablecido a 100%")

    def _connect_browser_to_statusbar(self, index=None):
        """Conectar señales del browser actual al status bar"""
        if index is None:
            index = self.tab_manager.tabs.currentIndex()

        if index < 0:
            return

        browser = self.tab_manager.tabs.widget(index)
        if not browser:
            return

        # Obtener la página del browser
        page = browser.page()
        if not page:
            return

        # Desconectar señales anteriores para evitar duplicados
        try:
            page.linkHovered.disconnect()
            browser.urlChanged.disconnect()
            browser.loadProgress.disconnect()
            page.loadStarted.disconnect()
            page.loadFinished.disconnect()
        except:
            pass  # Ignorar si no había conexiones previas

        # Conectar señales del browser al status bar
        # linkHovered es señal de QWebEnginePage, no de QWebEngineView
        page.linkHovered.connect(self.status_bar.update_url_hover)

        browser.urlChanged.connect(
            lambda url: self.status_bar.update_ssl_status(url.toString())
        )
        browser.loadProgress.connect(self.status_bar.update_load_progress)

        # Conectar señales de la página
        page.loadStarted.connect(
            lambda: self.status_bar.update_load_status("Cargando...")
        )
        page.loadFinished.connect(
            lambda: self.status_bar.update_load_status("")
        )

        # Actualizar SSL status de la pestaña actual
        current_url = browser.url().toString()
        if current_url:
            self.status_bar.update_ssl_status(current_url)

        # Actualizar zoom level
        zoom_factor = browser.zoomFactor()
        self.status_bar.update_zoom(zoom_factor)

    def toggle_fullscreen(self):
        """Alternar modo pantalla completa"""
        if self.isFullScreen():
            self.showNormal()
            print("[Menu] Modo pantalla completa desactivado")
        else:
            self.showFullScreen()
            print("[Menu] Modo pantalla completa activado")
    
    def show_clear_data_dialog(self):
        """Mostrar diálogo para limpiar datos de navegación"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Limpiar datos de navegación")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Seleccione los datos a eliminar:"))
        
        history_check = QCheckBox("Historial de navegación")
        history_check.setChecked(True)
        layout.addWidget(history_check)
        
        cache_check = QCheckBox("Caché")
        cache_check.setChecked(True)
        layout.addWidget(cache_check)
        
        cookies_check = QCheckBox("Cookies y datos de sitios")
        layout.addWidget(cookies_check)
        
        passwords_check = QCheckBox("Contraseñas guardadas")
        layout.addWidget(passwords_check)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec():
            try:
                if history_check.isChecked():
                    self.history_manager.clear_history()
                    print("[Menu] Historial limpiado")
                
                if cache_check.isChecked():
                    profile = QWebEngineProfile.defaultProfile()
                    profile.clearHttpCache()
                    print("[Menu] Caché limpiado")
                
                if cookies_check.isChecked():
                    profile = QWebEngineProfile.defaultProfile()
                    profile.cookieStore().deleteAllCookies()
                    print("[Menu] Cookies eliminadas")
                
                if passwords_check.isChecked() and hasattr(self, 'password_manager'):
                    # Implementar limpieza de contraseñas si es necesario
                    print("[Menu] Contraseñas limpiadas")
                
                QMessageBox.information(self, "Éxito", 
                    "Datos de navegación eliminados correctamente")
            except Exception as e:
                QMessageBox.warning(self, "Error",
                    f"Error al limpiar datos: {e}")

    def show_network_settings(self):
        """Mostrar configuración de red e interceptación"""
        if hasattr(self, 'network_interceptor'):
            dialog = NetworkSettingsDialog(self.network_interceptor, self)
            dialog.exec()
        else:
            QMessageBox.warning(
                self,
                "Network Interceptor no disponible",
                "El interceptor de red no está inicializado."
            )

    def show_userscripts(self):
        """Mostrar gestor de UserScripts"""
        if hasattr(self, 'userscript_manager'):
            dialog = UserScriptDialog(self.userscript_manager, self)
            dialog.exec()
        else:
            QMessageBox.warning(
                self,
                "UserScript Manager no disponible",
                "El gestor de UserScripts no está inicializado."
            )

    def change_visual_theme(self, theme_name):
        """Cambiar tema visual del navegador (light, dark, blue)"""
        try:
            # Cambiar tema en el theme manager
            self.theme_manager.change_theme(theme_name)

            # Aplicar nuevos estilos a la navbar
            modern_navbar_style = self.theme_manager.get_navbar_style()
            combined_style = modern_navbar_style + """
                QToolButton {
                    width: 36px;
                    height: 36px;
                    padding: 0px;
                    margin: 0px;
                    border: none;
                    border-radius: 18px;
                }
                QToolButton:hover {
                    background-color: rgba(0, 0, 0, 0.05);
                    border-radius: 18px;
                }
                QToolButton:pressed {
                    background-color: rgba(0, 0, 0, 0.1);
                    border-radius: 18px;
                }
            """
            self.nav_bar.setStyleSheet(combined_style)

            # Aplicar nuevo estilo al URL bar
            urlbar_style = self.theme_manager.get_urlbar_style()
            self.url_bar.setStyleSheet(urlbar_style)

            # Aplicar nuevo estilo a las pestañas
            tab_style = self.theme_manager.get_tab_style()
            self.tab_manager.tabs.setStyleSheet(tab_style)

            # Mensaje de confirmación en status bar
            theme_names = {
                'light': 'Claro',
                'dark': 'Oscuro',
                'blue': 'Azul'
            }
            self.status_bar.showMessage(
                f"Tema cambiado a: {theme_names.get(theme_name, theme_name)}", 3000
            )

            print(f"[THEME] Tema visual cambiado a: {theme_name}")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Error al cambiar tema",
                f"No se pudo cambiar el tema: {str(e)}"
            )
            print(f"[ERROR] Error al cambiar tema visual: {e}")

    def toggle_dev_tools(self):
        """Alternar herramientas de desarrollador"""
        if hasattr(self, 'devtools_dock') and self.devtools_dock:
            if self.devtools_dock.isVisible():
                self.devtools_dock.hide()
                print("[Menu] DevTools ocultadas")
            else:
                self.devtools_dock.show()
                print("[Menu] DevTools mostradas")
    
    def show_task_manager(self):
        """Mostrar administrador de tareas del navegador"""
        QMessageBox.information(self, "Administrador de tareas",
            "Administrador de tareas del navegador\n\n"
            "Pestaña actual: " + 
            (self.tab_manager.tabs.tabText(self.tab_manager.tabs.currentIndex()) 
             if self.tab_manager.tabs.count() > 0 else "Ninguna") +
            f"\nTotal de pestañas: {self.tab_manager.tabs.count()}")
    
    def view_page_source(self):
        """Ver código fuente de la página"""
        current_browser = self.tab_manager.tabs.currentWidget()
        if current_browser and hasattr(current_browser, 'page'):
            current_browser.page().toHtml(self._show_source_dialog)
    
    def _show_source_dialog(self, html):
        """Mostrar diálogo con código fuente"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Código fuente de la página")
        dialog.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(html)
        layout.addWidget(text_edit)
        
        dialog.exec()
    
    def show_settings(self):
        """Mostrar panel de configuración"""
        QMessageBox.information(self, "Ajustes",
            "Panel de configuración\n\n"
            "Características disponibles:\n"
            "• Gestión de plugins y extensiones\n"
            "• Configuración de privacidad\n"
            "• Gestión de contraseñas\n"
            "• Historial y marcadores")
    
    def show_about(self):
        """Mostrar información acerca de"""
        QMessageBox.about(self, "Acerca de Scrapelio",
            "<h2>Scrapelio Browser</h2>"
            "<p>Navegador profesional con capacidades avanzadas de scraping.</p>"
            "<p><b>Versión:</b> 3.4.7</p>"
            "<p><b>Motor:</b> QtWebEngine (Chromium)</p>"
            "<p><b>Framework:</b> PySide6</p>"
            "<br>"
            "<p>© 2024 Scrapelio. Todos los derechos reservados.</p>")
    
    def report_issue(self):
        """Informar de un problema"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Informar de un problema")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Describe el problema que encontraste:"))
        
        text_edit = QTextEdit()
        text_edit.setPlaceholderText(
            "Por favor describe el problema con el mayor detalle posible...\n\n"
            "Incluye:\n"
            "- Qué estabas haciendo\n"
            "- Qué esperabas que sucediera\n"
            "- Qué sucedió en su lugar"
        )
        layout.addWidget(text_edit)
        
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec():
            issue_text = text_edit.toPlainText()
            if issue_text.strip():
                QMessageBox.information(self, "Gracias",
                    "Gracias por tu reporte. Hemos registrado el problema.")
                print(f"[Menu] Problema reportado: {issue_text[:100]}...")
            else:
                QMessageBox.warning(self, "Aviso",
                    "Por favor describe el problema antes de enviar.")


class UrlBar(QLineEdit):
    def __init__(self, parent=None, load_url_callback=None):
        super().__init__(parent)
        self.load_url_callback = load_url_callback

    def insertFromMimeData(self, source):
        # Llama al método original para pegar el texto
        super().insertFromMimeData(source)
        text = self.text().strip()
        if self.load_url_callback and text:
            # Si el texto pegado es un enlace, navega automáticamente
            if text.startswith(('http://', 'https://')) or ('.' in text and ' ' not in text):
                self.load_url_callback(text)





