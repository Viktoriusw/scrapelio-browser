#!/usr/bin/env python3
"""
Unified Plugin Panel - Panel unificado SIMPLIFICADO para gestión de plugins
Versión rediseñada: Solo Tienda y Gestión
"""

from typing import Optional
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QPushButton, QLabel, QHeaderView, QMessageBox, QFrame,
    QListWidget, QListWidgetItem, QScrollArea, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from PySide6.QtGui import QColor, QFont, QDesktopServices
from base_panel import BasePanel
from unified_plugin_manager import UnifiedPluginManager, PluginInfo, PluginAccessInfo, PluginAccessLevel

logger = logging.getLogger(__name__)


class UnifiedPluginPanel(BasePanel):
    """Panel unificado SIMPLIFICADO para gestión de plugins"""
    
    def __init__(self, plugin_manager: UnifiedPluginManager, parent=None):
        # Inicializar elementos UI antes de super().__init__
        self.plugin_list = None
        self.status_label = None
        self.progress_bar = None
        self.management_table = None
        
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.plugins_loaded = False
        
        # Contador para prevenir bucle infinito
        self._ui_init_attempts = 0
        self._max_ui_init_attempts = 3
        
        # Conectar señales del plugin manager
        self.plugin_manager.plugin_installed.connect(self.on_plugin_installed)
        self.plugin_manager.plugin_uninstalled.connect(self.on_plugin_uninstalled)
        self.plugin_manager.plugin_error.connect(self.on_plugin_error)
        self.plugin_manager.access_granted.connect(self.on_access_granted)
        
        # Conectar señales de autenticación
        if self.plugin_manager.auth_manager:
            self.plugin_manager.auth_manager.auth_state_changed.connect(self.on_auth_state_changed)
            self.plugin_manager.auth_manager.login_successful.connect(self.on_login_successful)
            print("[UnifiedPluginPanel] Conectado a señales de autenticación")
        
        # Cargar plugins después de que las pestañas estén listas
        QTimer.singleShot(500, self.initial_load)
    
    def get_tab_definitions(self):
        """Definir SOLO 2 pestañas: Tienda y Gestión"""
        return [
            (self.create_store_tab, "🛒 Tienda"),
            (self.create_management_tab, "⚙️ Gestión"),
        ]
    
    def initial_load(self):
        """Carga inicial de plugins"""
        if not self.plugins_loaded:
            print("[UnifiedPluginPanel] Iniciando carga inicial de plugins...")
            self.plugins_loaded = True
            self.load_available_plugins()
            self.refresh_management_tab()
    
    # ==================== PESTAÑA TIENDA ====================
    
    def create_store_tab(self):
        """Crear pestaña de tienda de plugins"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Encabezado
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🛒 Tienda de Plugins")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        refresh_licenses_btn = QPushButton("🔑 Refrescar Licencias")
        refresh_licenses_btn.setToolTip("Actualizar el estado de tus suscripciones desde el servidor")
        refresh_licenses_btn.clicked.connect(self.refresh_licenses_from_backend)
        header_layout.addWidget(refresh_licenses_btn)
        
        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_available_plugins)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Lista de plugins
        self.plugin_list = QListWidget()
        self.plugin_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                border-bottom: 1px solid #f8f9fa;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        layout.addWidget(self.plugin_list)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Etiqueta de estado
        self.status_label = QLabel("Cargando plugins...")
        self.status_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        return widget
    
    # ==================== PESTAÑA GESTIÓN ====================
    
    def create_management_tab(self):
        """Crear pestaña de gestión de plugins SUSCRITOS"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Encabezado
        header_layout = QHBoxLayout()
        
        title_label = QLabel("⚙️ Mis Plugins Suscritos")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.refresh_management_tab)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Descripción
        desc_label = QLabel(
            "Aquí puedes ver, descargar, instalar y desinstalar los plugins a los que estás suscrito."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #6c757d; padding: 10px; background-color: #f8f9fa; border-radius: 4px;")
        layout.addWidget(desc_label)
        
        # Tabla de plugins suscritos
        self.management_table = QTableWidget()
        self.management_table.setColumnCount(6)
        self.management_table.setHorizontalHeaderLabels([
            "Plugin", "Estado", "Expira", "Instalado", "Acciones", "Info"
        ])
        
        # Configurar tabla
        header = self.management_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.management_table)
        
        return widget
    
    def refresh_management_tab(self):
        """Refrescar tabla de gestión con plugins SUSCRITOS"""
        if not hasattr(self, 'management_table'):
            return
        
        self.management_table.setRowCount(0)
        
        # Verificar autenticación
        if not self.plugin_manager.auth_manager or not self.plugin_manager.auth_manager.auth_state.is_authenticated:
            self._show_auth_required_message()
            return
        
        # Obtener todos los plugins disponibles
        try:
            plugins = self.plugin_manager.load_available_plugins()
            
            if not plugins:
                self._show_no_subscriptions_message()
                return
            
            # Filtrar solo plugins con suscripción activa
            subscribed_plugins = []
            for plugin_info in plugins:
                access_info = self.plugin_manager.get_plugin_access(plugin_info.id)
                if access_info.access_level in [PluginAccessLevel.PREMIUM, PluginAccessLevel.TRIAL]:
                    subscribed_plugins.append((plugin_info, access_info))
            
            if not subscribed_plugins:
                self._show_no_subscriptions_message()
                return
            
            # Agregar cada plugin suscrito a la tabla
            for plugin_info, access_info in subscribed_plugins:
                self._add_plugin_to_management_table(plugin_info, access_info)
                
        except Exception as e:
            print(f"[UnifiedPluginPanel] Error al cargar plugins suscritos: {e}")
            import traceback
            traceback.print_exc()
    
    def _add_plugin_to_management_table(self, plugin_info: PluginInfo, access_info: PluginAccessInfo):
        """Agregar un plugin a la tabla de gestión"""
        row = self.management_table.rowCount()
        self.management_table.insertRow(row)
        
        # Columna 0: Nombre del plugin
        name_item = QTableWidgetItem(plugin_info.name)
        name_item.setFont(QFont("Arial", 10, QFont.Bold))
        self.management_table.setItem(row, 0, name_item)
        
        # Columna 1: Estado (Premium/Trial)
        if access_info.access_level == PluginAccessLevel.PREMIUM:
            status_item = QTableWidgetItem("✅ Premium")
            status_item.setForeground(QColor(40, 167, 69))
        else:
            status_item = QTableWidgetItem(f"⏰ Prueba ({access_info.trial_remaining}d)")
            status_item.setForeground(QColor(255, 193, 7))
        self.management_table.setItem(row, 1, status_item)
        
        # Columna 2: Fecha de expiración
        expires_text = "N/A"
        if access_info.license_info and hasattr(access_info.license_info, 'expires_at'):
            from datetime import datetime
            try:
                if access_info.license_info.expires_at:
                    # Verificar si expires_at es timestamp (float) o string ISO
                    if isinstance(access_info.license_info.expires_at, (int, float)):
                        expires_date = datetime.fromtimestamp(access_info.license_info.expires_at)
                    else:
                        expires_date = datetime.fromisoformat(str(access_info.license_info.expires_at).replace('Z', '+00:00'))
                    expires_text = expires_date.strftime('%Y-%m-%d')
            except Exception as e:
                logger.warning(f"Error parsing expires_at: {e}")
                expires_text = "N/A"
        expires_item = QTableWidgetItem(expires_text)
        expires_item.setForeground(QColor(108, 117, 125))
        self.management_table.setItem(row, 2, expires_item)
        
        # Columna 3: Instalado (Si/No)
        is_installed = self.plugin_manager.is_plugin_installed(plugin_info.id)
        if is_installed:
            installed_item = QTableWidgetItem("✅ Sí")
            installed_item.setForeground(QColor(40, 167, 69))
        else:
            installed_item = QTableWidgetItem("❌ No")
            installed_item.setForeground(QColor(220, 53, 69))
        self.management_table.setItem(row, 3, installed_item)
        
        # Columna 4: Botón de Acción (Instalar/Desinstalar)
        action_btn = QPushButton()
        if is_installed:
            action_btn.setText("🗑️ Desinstalar")
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            action_btn.clicked.connect(lambda checked, pid=plugin_info.id: self.uninstall_plugin(pid))
        else:
            action_btn.setText("📥 Instalar")
            action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            action_btn.clicked.connect(lambda checked, pid=plugin_info.id: self.install_plugin(pid))
        
        self.management_table.setCellWidget(row, 4, action_btn)
        
        # Columna 5: Botón de Información
        info_btn = QPushButton("ℹ️")
        info_btn.setToolTip("Ver información del plugin")
        info_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        info_btn.clicked.connect(lambda checked, pinfo=plugin_info: self.show_plugin_info_simple(pinfo))
        self.management_table.setCellWidget(row, 5, info_btn)
    
    def _show_auth_required_message(self):
        """Mostrar mensaje de que se requiere autenticación"""
        self.management_table.setRowCount(1)
        message_item = QTableWidgetItem("🔐 Por favor, inicia sesión para ver tus plugins suscritos")
        message_item.setForeground(QColor(108, 117, 125))
        message_item.setFont(QFont("Arial", 11, QFont.Bold))
        self.management_table.setItem(0, 0, message_item)
        self.management_table.setSpan(0, 0, 1, 6)
    
    def _show_no_subscriptions_message(self):
        """Mostrar mensaje de que no hay suscripciones"""
        self.management_table.setRowCount(1)
        message_item = QTableWidgetItem(
            "📭 No tienes plugins suscritos. Visita la pestaña Tienda para ver los plugins disponibles."
        )
        message_item.setForeground(QColor(108, 117, 125))
        message_item.setFont(QFont("Arial", 11))
        self.management_table.setItem(0, 0, message_item)
        self.management_table.setSpan(0, 0, 1, 6)
    
    def show_plugin_info_simple(self, plugin_info: PluginInfo):
        """Mostrar información básica del plugin"""
        QMessageBox.information(
            self,
            f"📦 {plugin_info.name}",
            f"<b>Nombre:</b> {plugin_info.name}<br>"
            f"<b>Versión:</b> {plugin_info.version}<br>"
            f"<b>Autor:</b> {plugin_info.author}<br><br>"
            f"<b>Descripción:</b><br>{plugin_info.description}<br><br>"
            f"<b>Características:</b><br>• " + "<br>• ".join(plugin_info.features[:5] if plugin_info.features else ["No disponible"])
        )
    
    # ==================== ACCIONES DE PLUGINS ====================
    
    def install_plugin(self, plugin_id: str):
        """Instalar un plugin"""
        if not self.plugin_manager.auth_manager or not self.plugin_manager.auth_manager.auth_state.is_authenticated:
            QMessageBox.warning(self, "Autenticación Requerida", 
                               "Por favor, inicia sesión para instalar plugins.")
            return
        
        # Verificar si ya está instalado
        if self.plugin_manager.is_plugin_installed(plugin_id):
            QMessageBox.information(self, "Plugin Ya Instalado", 
                                   f"El plugin '{plugin_id}' ya está instalado.")
            return
        
        # Iniciar instalación
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"📥 Descargando {plugin_id}...")
        
        success = self.plugin_manager.install_plugin(
            plugin_id, 
            self.progress_bar.setValue
        )
        
        if not success:
            QMessageBox.warning(self, "Error de Instalación", 
                               "No se pudo iniciar la instalación del plugin.")
            self.progress_bar.setVisible(False)
            self.status_label.setText("❌ Error de instalación")
    
    def uninstall_plugin(self, plugin_id: str):
        """Desinstalar un plugin"""
        reply = QMessageBox.question(
            self, "Confirmar Desinstalación",
            f"¿Estás seguro de que quieres desinstalar el plugin '{plugin_id}'?\n\n"
            f"Esto eliminará todos sus archivos.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.plugin_manager.uninstall_plugin(plugin_id)
            
            if success:
                QMessageBox.information(self, "Desinstalación Exitosa", 
                                       f"Plugin '{plugin_id}' ha sido desinstalado exitosamente.")
                self.refresh_management_tab()
                self.load_available_plugins()
            else:
                QMessageBox.warning(self, "Error", 
                                   f"No se pudo desinstalar el plugin '{plugin_id}'.")
    
    # ==================== CARGA DE PLUGINS PARA TIENDA ====================
    
    def load_available_plugins(self):
        """Cargar plugins disponibles desde el backend"""
        print("[UnifiedPluginPanel] load_available_plugins() called")
        
        if not hasattr(self, 'status_label') or not hasattr(self, 'plugin_list'):
            print("[UnifiedPluginPanel] WARNING: UI elements not ready yet")
            self._ui_init_attempts += 1
            if self._ui_init_attempts < self._max_ui_init_attempts:
                QTimer.singleShot(1000, self.load_available_plugins)
            return
        
        self._ui_init_attempts = 0
        self.status_label.setText("🔄 Cargando plugins desde el servidor...")
        self.plugin_list.clear()
        
        if not self.plugin_manager.auth_manager:
            self.status_label.setText("❌ Error: Sistema de autenticación no disponible")
            return
        
        if not self.plugin_manager.auth_manager.auth_state.is_authenticated:
            print("[UnifiedPluginPanel] User not authenticated")
            self.status_label.setText("🔐 Por favor, inicia sesión para ver los plugins disponibles")
            auth_item = QListWidgetItem()
            auth_widget = self.create_auth_required_widget()
            auth_item.setSizeHint(auth_widget.sizeHint())
            self.plugin_list.addItem(auth_item)
            self.plugin_list.setItemWidget(auth_item, auth_widget)
            return
        
        print("[UnifiedPluginPanel] User authenticated, loading plugins from backend...")
        try:
            plugins = self.plugin_manager.load_available_plugins()
            print(f"[UnifiedPluginPanel] Loaded {len(plugins) if plugins else 0} plugins")
            
            if not plugins or len(plugins) == 0:
                self.status_label.setText("📭 No hay plugins disponibles en el servidor")
                return
            
            for plugin_info in plugins:
                print(f"[UnifiedPluginPanel] Adding plugin: {plugin_info.name}")
                self.add_plugin_to_list(plugin_info)
            
            self.status_label.setText(f"✅ Cargados {len(plugins)} plugins disponibles")
            
        except Exception as e:
            print(f"[UnifiedPluginPanel] ERROR loading plugins: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"❌ Error al cargar plugins: {str(e)}")
    
    def add_plugin_to_list(self, plugin_info: PluginInfo):
        """Agregar un plugin a la lista de la tienda"""
        if not hasattr(self, 'plugin_list'):
            return
            
        item = QListWidgetItem()
        plugin_widget = self.create_plugin_widget(plugin_info)
        item.setSizeHint(plugin_widget.sizeHint())
        self.plugin_list.addItem(item)
        self.plugin_list.setItemWidget(item, plugin_widget)
    
    def create_plugin_widget(self, plugin_info: PluginInfo) -> QWidget:
        """Crear widget para un plugin en la tienda"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        
        access_info = self.plugin_manager.get_plugin_access(plugin_info.id)
        has_subscription = access_info.access_level in [PluginAccessLevel.PREMIUM, PluginAccessLevel.TRIAL]
        is_installed = self.plugin_manager.is_plugin_installed(plugin_info.id)
        
        container = QFrame()
        container.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        
        if has_subscription:
            border_color = "#28a745" if not is_installed else "#17a2b8"
            bg_color = "#f0fff4" if not is_installed else "#e7f5ff"
        else:
            border_color = "#dc3545"
            bg_color = "#fff5f5"
        
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        
        container_layout = QVBoxLayout(container)
        
        # Encabezado
        header_layout = QHBoxLayout()
        
        name_label = QLabel(plugin_info.name)
        name_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        if is_installed:
            status_badge = QLabel("✅ INSTALADO")
            status_badge.setStyleSheet("background-color: #17a2b8; color: white; padding: 4px 12px; border-radius: 12px; font-size: 10px; font-weight: bold;")
        elif has_subscription:
            status_badge = QLabel("🔓 SUSCRITO")
            status_badge.setStyleSheet("background-color: #28a745; color: white; padding: 4px 12px; border-radius: 12px; font-size: 10px; font-weight: bold;")
        else:
            status_badge = QLabel("🔒 PREMIUM")
            status_badge.setStyleSheet("background-color: #dc3545; color: white; padding: 4px 12px; border-radius: 12px; font-size: 10px; font-weight: bold;")
        header_layout.addWidget(status_badge)
        
        container_layout.addLayout(header_layout)
        
        # Descripción
        desc_label = QLabel(plugin_info.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #495057; font-size: 12px; padding: 8px 0;")
        desc_label.setMaximumHeight(50)
        container_layout.addWidget(desc_label)
        
        # Botones
        buttons_layout = QHBoxLayout()
        
        info_btn = QPushButton("ℹ️ Más Info")
        info_btn.setStyleSheet("background-color: #6c757d; color: white; border: none; padding: 6px 12px; border-radius: 4px;")
        info_btn.clicked.connect(lambda: self.show_plugin_info_simple(plugin_info))
        buttons_layout.addWidget(info_btn)
        
        buttons_layout.addStretch()
        
        # Botón de URL del sitio web (se abre en el navegador Scrapelio)
        web_btn = QPushButton("🌐 Ver en Web")
        web_btn.setStyleSheet("background-color: #007bff; color: white; border: none; padding: 6px 12px; border-radius: 4px;")
        web_btn.clicked.connect(lambda: self.open_plugin_in_browser(plugin_info.id))
        buttons_layout.addWidget(web_btn)
        
        container_layout.addLayout(buttons_layout)
        layout.addWidget(container)
        
        return widget
    
    def open_plugin_in_browser(self, plugin_id: str):
        """Abrir URL del plugin en el navegador SCRAPELIO (no externo)"""
        try:
            from network_config import get_website_url
            website_url = get_website_url()
            url = f"{website_url}/app/dashboard.html?plugin={plugin_id}"
            
            # Emitir señal para abrir en el navegador Scrapelio
            # Buscar la ventana principal del navegador
            main_window = self.window()
            if hasattr(main_window, 'browser_widget'):
                # Crear nueva pestaña con la URL
                main_window.browser_widget.tabs_widget.add_tab(url)
                QMessageBox.information(self, "Abriendo en Navegador", 
                                       f"Se ha abierto una nueva pestaña con el plugin '{plugin_id}'.")
            else:
                QMessageBox.warning(self, "Error", 
                                   "No se pudo abrir en el navegador. Abriendo en navegador externo...")
                QDesktopServices.openUrl(QUrl(url))
                
        except Exception as e:
            print(f"[UnifiedPluginPanel] Error opening plugin in browser: {e}")
            QMessageBox.warning(self, "Error", 
                               f"No se pudo abrir la URL del plugin:\n{str(e)}")
    
    def create_auth_required_widget(self) -> QWidget:
        """Widget para mostrar que se requiere autenticación"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        container = QFrame()
        container.setStyleSheet("QFrame { background-color: #f8f9fa; border: 2px solid #dee2e6; border-radius: 8px; padding: 10px; }")
        container_layout = QVBoxLayout(container)
        
        title_label = QLabel("🔐 Autenticación Requerida")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        container_layout.addWidget(title_label)
        
        desc_label = QLabel("Para acceder a los plugins disponibles, necesitas iniciar sesión con tu cuenta de usuario.")
        desc_label.setWordWrap(True)
        container_layout.addWidget(desc_label)
        
        layout.addWidget(container)
        return widget
    
    def refresh_licenses_from_backend(self):
        """Refrescar licencias del usuario desde el backend"""
        print("[UnifiedPluginPanel] Refrescando licencias desde el backend...")
        
        try:
            from backend_integration import backend_integration
            
            if not backend_integration.is_authenticated():
                QMessageBox.warning(self, "No Autenticado", 
                                  "Debes iniciar sesión para refrescar las licencias.")
                return
            
            success = backend_integration.refresh_licenses()
            
            if success:
                self.refresh_all_after_login()
                QMessageBox.information(self, "✅ Licencias Actualizadas", 
                                      f"Las licencias se han actualizado correctamente.\n\n"
                                      f"Licencias activas: {len(backend_integration.user_licenses)}")
                print(f"[UnifiedPluginPanel] Licencias refrescadas: {len(backend_integration.user_licenses)} activas")
            else:
                QMessageBox.warning(self, "❌ Error", 
                                  "No se pudieron refrescar las licencias. Verifica tu conexión.")
                
        except Exception as e:
            print(f"[UnifiedPluginPanel] Error al refrescar licencias: {e}")
            QMessageBox.critical(self, "Error", f"Error al refrescar licencias:\n{str(e)}")
    
    # ==================== MANEJADORES DE SEÑALES ====================
    
    def on_plugin_installed(self, plugin_id: str):
        """Manejar instalación exitosa de plugin"""
        print(f"[UnifiedPluginPanel] Plugin '{plugin_id}' installed successfully")
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"✅ Plugin '{plugin_id}' instalado exitosamente")
        
        QMessageBox.information(self, "Instalación Exitosa", 
                               f"🎉 Plugin '{plugin_id}' ha sido instalado exitosamente!")
        
        self.refresh_management_tab()
        self.load_available_plugins()
    
    def on_plugin_uninstalled(self, plugin_id: str):
        """Manejar desinstalación de plugin"""
        print(f"[UnifiedPluginPanel] Plugin '{plugin_id}' uninstalled")
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"🗑️ Plugin '{plugin_id}' desinstalado")
        
        self.refresh_management_tab()
        self.load_available_plugins()
    
    def on_plugin_error(self, plugin_id: str, error: str):
        """Manejar error de plugin"""
        print(f"[UnifiedPluginPanel] Error en plugin '{plugin_id}': {error}")
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"❌ Error: {error}")
        
        QMessageBox.warning(self, "Error de Plugin", 
                           f"Error en plugin '{plugin_id}':\n\n{error}")
    
    def on_access_granted(self, plugin_id: str):
        """Manejar acceso concedido a plugin"""
        print(f"[UnifiedPluginPanel] Access granted to plugin '{plugin_id}'")
        if hasattr(self, 'status_label'):
            self.status_label.setText(f"✅ Acceso concedido a plugin '{plugin_id}'")
        self.load_available_plugins()
        self.refresh_management_tab()
    
    def on_auth_state_changed(self, is_authenticated: bool):
        """Manejar cambio en el estado de autenticación"""
        print(f"[UnifiedPluginPanel] Estado de autenticación cambió: {is_authenticated}")
        
        if is_authenticated:
            QTimer.singleShot(1000, self.refresh_all_after_login)
        else:
            if hasattr(self, 'plugin_list') and self.plugin_list:
                self.plugin_list.clear()
            if hasattr(self, 'management_table') and self.management_table:
                self._show_auth_required_message()
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText("🔐 Por favor, inicia sesión")
    
    def on_login_successful(self):
        """Manejar login exitoso"""
        print("[UnifiedPluginPanel] Login exitoso detectado - recargando plugins...")
        QTimer.singleShot(1500, self.refresh_all_after_login)
    
    def refresh_all_after_login(self):
        """Refrescar TODO el panel después del login"""
        print("[UnifiedPluginPanel] Refrescando panel completo después del login...")
        
        if hasattr(self, 'load_available_plugins'):
            self.load_available_plugins()
        
        if hasattr(self, 'refresh_management_tab'):
            self.refresh_management_tab()
        
        print("[UnifiedPluginPanel] Panel refrescado completamente")

