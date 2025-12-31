#!/usr/bin/env python3
"""
Panel de Plugins Simplificado para SaaS
Sistema claro y funcional para gestión de plugins premium
"""

import logging
import webbrowser
from typing import List, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,  
    QFrame, QScrollArea, QMessageBox, QProgressBar, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor, QPalette

from base_panel import BasePanel

# Configurar logging
logger = logging.getLogger(__name__)


class PluginCard(QFrame):
    """Tarjeta de plugin individual con toda la información y acciones"""
    
    install_clicked = Signal(str)  # plugin_id
    purchase_clicked = Signal(str)  # plugin_id
    
    def __init__(self, plugin_data: dict, license_data: dict = None, is_installed: bool = False, parent=None):
        super().__init__(parent)
        self.plugin_data = plugin_data
        self.license_data = license_data
        self.is_installed = is_installed
        
        self.setObjectName("pluginCard")
        self.setup_ui()
    
    def setup_ui(self):
        """Configurar UI de la tarjeta"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # ========== HEADER: Nombre + Estado ==========
        header_layout = QHBoxLayout()
        
        # Icono y nombre
        name_layout = QVBoxLayout()
        name_layout.setSpacing(4)
        
        name_label = QLabel(self.plugin_data.get("name", "Plugin"))
        name_label.setFont(QFont("Arial", 14, QFont.Bold))
        name_layout.addWidget(name_label)
        
        category_label = QLabel(f"📁 {self.plugin_data.get('category', 'General').title()}")
        category_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        name_layout.addWidget(category_label)
        
        header_layout.addLayout(name_layout)
        header_layout.addStretch()
        
        # Badge de estado
        status_widget = self._create_status_badge()
        header_layout.addWidget(status_widget)
        
        layout.addLayout(header_layout)
        
        # ========== DESCRIPCIÓN ==========
        desc_label = QLabel(self.plugin_data.get("description", ""))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #495057; font-size: 12px; line-height: 1.4;")
        desc_label.setMaximumHeight(60)
        layout.addWidget(desc_label)
        
        # ========== CARACTERÍSTICAS (solo si tiene licencia) ==========
        if self.license_data and self.license_data.get("is_licensed"):
            features = self.plugin_data.get("features", [])
            if features and len(features) > 0:
                features_text = " • ".join(features[:3])  # Mostrar solo 3
                features_label = QLabel(f"✨ {features_text}")
                features_label.setStyleSheet("color: #28a745; font-size: 11px; font-style: italic;")
                features_label.setWordWrap(True)
                layout.addWidget(features_label)
        
        # ========== SEPARADOR ==========
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #dee2e6; margin: 4px 0px;")
        layout.addWidget(separator)
        
        # ========== INFO DE LICENCIA + PRECIO ==========
        info_layout = QHBoxLayout()
        
        # Info de licencia
        if self.license_data and self.license_data.get("is_licensed"):
            expires_at = self.license_data.get("expires_at", "")
            trial_days = self.license_data.get("trial_remaining", 0)
            
            if trial_days > 0:
                license_info = QLabel(f"⏰ Periodo de prueba: {trial_days} días restantes")
                license_info.setStyleSheet("color: #ffc107; font-size: 11px; font-weight: bold;")
            else:
                license_info = QLabel(f"✅ Licencia activa hasta {expires_at[:10]}")
                license_info.setStyleSheet("color: #28a745; font-size: 11px; font-weight: bold;")
            
            info_layout.addWidget(license_info)
        else:
            price = self.plugin_data.get("price", 0)
            billing_cycle = self.plugin_data.get("billing_cycle", "monthly")
            
            cycle_text = "mes" if billing_cycle == "monthly" else "año"
            price_label = QLabel(f"💳 ${price:.2f}/{cycle_text}")
            price_label.setFont(QFont("Arial", 12, QFont.Bold))
            price_label.setStyleSheet("color: #e74c3c;")
            info_layout.addWidget(price_label)
        
        info_layout.addStretch()
        
        # Versión
        version_label = QLabel(f"v{self.plugin_data.get('version', '1.0.0')}")
        version_label.setStyleSheet("color: #6c757d; font-size: 10px;")
        info_layout.addWidget(version_label)
        
        layout.addLayout(info_layout)
        
        # ========== BOTONES DE ACCIÓN ==========
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        # Botón principal (Instalar o Comprar)
        if self.license_data and self.license_data.get("is_licensed"):
            if self.is_installed:
                # Plugin ya instalado
                installed_btn = QPushButton("✅ Instalado")
                installed_btn.setEnabled(False)
                installed_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #28a745;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        font-weight: bold;
                    }
                """)
                buttons_layout.addWidget(installed_btn)
            else:
                # Plugin con licencia pero no instalado
                install_btn = QPushButton("📥 Instalar Plugin")
                install_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #0056b3;
                    }
                """)
                install_btn.clicked.connect(lambda: self.install_clicked.emit(self.plugin_data["id"]))
                buttons_layout.addWidget(install_btn)
        else:
            # Sin licencia - botón de compra
            purchase_btn = QPushButton("🛒 Suscribirse")
            purchase_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1e7e34;
                }
            """)
            purchase_btn.clicked.connect(lambda: self.purchase_clicked.emit(self.plugin_data["id"]))
            buttons_layout.addWidget(purchase_btn)
        
        # Botón de información
        info_btn = QPushButton("ℹ️")
        info_btn.setFixedSize(40, 40)
        info_btn.setToolTip("Ver información detallada")
        info_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        info_btn.clicked.connect(self._show_details)
        buttons_layout.addWidget(info_btn)
        
        layout.addLayout(buttons_layout)
        
        # Estilo de la tarjeta
        if self.license_data and self.license_data.get("is_licensed"):
            # Tarjeta con licencia activa - borde verde
            self.setStyleSheet("""
                QFrame#pluginCard {
                    background-color: #f8f9fa;
                    border: 2px solid #28a745;
                    border-radius: 8px;
                    padding: 0px;
                }
            """)
        else:
            # Tarjeta sin licencia - borde gris
            self.setStyleSheet("""
                QFrame#pluginCard {
                    background-color: white;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 0px;
                }
                QFrame#pluginCard:hover {
                    border-color: #adb5bd;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
            """)
    
    def _create_status_badge(self) -> QLabel:
        """Crear badge de estado"""
        if self.is_installed:
            badge = QLabel("INSTALADO")
            badge.setStyleSheet("""
                background-color: #28a745;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 10px;
                font-weight: bold;
            """)
        elif self.license_data and self.license_data.get("is_licensed"):
            trial_days = self.license_data.get("trial_remaining", 0)
            if trial_days > 0:
                badge = QLabel(f"PRUEBA ({trial_days}d)")
                badge.setStyleSheet("""
                    background-color: #ffc107;
                    color: #000;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 10px;
                    font-weight: bold;
                """)
            else:
                badge = QLabel("PREMIUM")
                badge.setStyleSheet("""
                    background-color: #007bff;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 10px;
                    font-weight: bold;
                """)
        else:
            badge = QLabel("GRATIS")
            badge.setStyleSheet("""
                background-color: #6c757d;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 10px;
                font-weight: bold;
            """)
        
        return badge
    
    def _show_details(self):
        """Mostrar información detallada del plugin"""
        details = f"""
<h2>{self.plugin_data.get('name', 'Plugin')}</h2>
<p><b>Versión:</b> {self.plugin_data.get('version', '1.0.0')}</p>
<p><b>Autor:</b> {self.plugin_data.get('author', 'Scrapelio Team')}</p>

<h3>Descripción:</h3>
<p>{self.plugin_data.get('description', 'No hay descripción disponible')}</p>

<h3>Características:</h3>
<ul>
"""
        for feature in self.plugin_data.get('features', []):
            details += f"<li>{feature}</li>"
        
        details += "</ul>"
        
        if self.license_data and self.license_data.get("is_licensed"):
            details += f"""
<h3>Estado de Licencia:</h3>
<p style="color: #28a745;"><b>✅ Activa</b></p>
<p>Expira: {self.license_data.get('expires_at', 'N/A')}</p>
"""
        else:
            price = self.plugin_data.get('price', 0)
            billing_cycle = self.plugin_data.get('billing_cycle', 'monthly')
            details += f"""
<h3>Precio:</h3>
<p><b>${price:.2f}</b> / {billing_cycle}</p>
<p>Incluye {self.plugin_data.get('trial_days', 7)} días de prueba gratis</p>
"""
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Información del Plugin")
        msg.setTextFormat(Qt.RichText)
        msg.setText(details)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()


class PluginsPanelV2(BasePanel):
    """Panel de plugins simplificado - v2.0"""
    
    plugin_action_requested = Signal(str, str)  # plugin_id, action (install/purchase)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Datos
        self.plugins = []
        self.licenses = {}
        self.installed_plugins = set()
        
        # Conectar con backend
        try:
            from backend_integration import backend_integration
            self.backend = backend_integration
            
            # Conectar señales
            if self.backend:
                self.backend.login_successful.connect(self.on_login)
                self.backend.plugin_downloaded.connect(self.on_plugin_downloaded)
        except ImportError:
            logger.error("No se pudo importar backend_integration")
            self.backend = None
        
        # Cargar datos si ya está autenticado
        if self.backend and self.backend.is_authenticated():
            QTimer.singleShot(500, self.load_data)
    
    def get_tab_definitions(self):
        """Definir pestañas del panel"""
        return [
            (self.create_main_tab, "🛒 Mis Plugins")
        ]
    
    def create_main_tab(self):
        """Crear pestaña principal con todos los plugins"""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== TOOLBAR ==========
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: white; border-bottom: 1px solid #dee2e6; padding: 12px;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 8, 16, 8)
        
        # Título
        title_label = QLabel("Mis Plugins")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        toolbar_layout.addWidget(title_label)
        
        toolbar_layout.addStretch()
        
        # Botones de acción
        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.setToolTip("Refrescar lista de plugins y licencias")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        toolbar_layout.addWidget(refresh_btn)
        
        main_layout.addWidget(toolbar)
        
        # ========== ÁREA DE SCROLL PARA PLUGINS ==========
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #f8f9fa;")
        
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(16, 16, 16, 16)
        self.scroll_layout.setSpacing(12)
        
        scroll.setWidget(self.scroll_widget)
        main_layout.addWidget(scroll)
        
        # ========== BARRA DE ESTADO ==========
        status_bar = QFrame()
        status_bar.setStyleSheet("background-color: white; border-top: 1px solid #dee2e6; padding: 8px;")
        status_bar_layout = QHBoxLayout(status_bar)
        status_bar_layout.setContentsMargins(16, 8, 16, 8)
        
        self.status_label = QLabel("Cargando plugins...")
        self.status_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        status_bar_layout.addWidget(self.status_label)
        
        status_bar_layout.addStretch()
        
        dashboard_btn = QPushButton("🌐 Abrir Dashboard")
        dashboard_btn.setToolTip("Abrir dashboard web para gestionar suscripciones")
        dashboard_btn.clicked.connect(self.open_dashboard)
        dashboard_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        status_bar_layout.addWidget(dashboard_btn)
        
        main_layout.addWidget(status_bar)
        
        return widget
    
    def load_data(self):
        """Cargar datos de plugins y licencias"""
        if not self.backend or not self.backend.is_authenticated():
            self.status_label.setText("🔐 Por favor, inicia sesión para ver tus plugins")
            self._show_login_message()
            return
        
        try:
            self.status_label.setText("🔄 Cargando plugins y licencias...")
            
            # Refrescar licencias
            self.backend.refresh_licenses()
            
            # Obtener datos
            self.plugins = self.backend.get_available_plugins()
            user_licenses = self.backend.get_user_licenses()
            
            # Crear diccionario de licencias por plugin_id
            self.licenses = {lic.plugin_id: lic for lic in user_licenses}
            
            # Obtener plugins instalados
            plugins_dir = Path("plugins")
            if plugins_dir.exists():
                self.installed_plugins = {
                    d.name for d in plugins_dir.iterdir() 
                    if d.is_dir() and (d / "__init__.py").exists()
                }
            
            # Actualizar UI
            self._populate_plugins()
            
            # Actualizar status
            licensed_count = len([l for l in user_licenses if l.is_licensed])
            installed_count = len(self.installed_plugins)
            
            self.status_label.setText(
                f"📦 {len(self.plugins)} plugins disponibles | "
                f"✅ {licensed_count} licencias activas | "
                f"💾 {installed_count} instalados"
            )
            
            logger.info(f"Panel loaded: {len(self.plugins)} plugins, {licensed_count} licenses")
            
        except Exception as e:
            logger.error(f"Error loading plugin data: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"❌ Error al cargar plugins: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error al cargar plugins:\n{str(e)}")
    
    def _populate_plugins(self):
        """Poblar la lista de plugins"""
        # Limpiar layout
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not self.plugins:
            self._show_empty_message()
            return
        
        # Ordenar plugins: Con licencia primero
        sorted_plugins = sorted(
            self.plugins,
            key=lambda p: (
                not self.licenses.get(p.id, None),  # Con licencia primero
                not (p.id in self.installed_plugins),  # Instalados primero
                p.name  # Luego alfabéticamente
            )
        )
        
        # Agregar tarjetas de plugins
        for plugin in sorted_plugins:
            plugin_dict = {
                "id": plugin.id,
                "name": plugin.name,
                "description": plugin.description,
                "version": plugin.version,
                "author": plugin.author,
                "price": plugin.price,
                "currency": plugin.currency,
                "billing_cycle": plugin.billing_cycle,
                "category": plugin.category,
                "features": plugin.features,
                "trial_days": plugin.trial_days
            }
            
            license = self.licenses.get(plugin.id)
            license_dict = None
            if license:
                license_dict = {
                    "plugin_id": license.plugin_id,
                    "plugin_name": license.plugin_name,
                    "is_licensed": license.is_licensed,
                    "expires_at": license.expires_at,
                    "trial_remaining": license.trial_remaining
                }
            
            is_installed = plugin.id in self.installed_plugins
            
            card = PluginCard(plugin_dict, license_dict, is_installed, self)
            card.install_clicked.connect(self.install_plugin)
            card.purchase_clicked.connect(self.purchase_plugin)
            
            self.scroll_layout.addWidget(card)
        
        # Spacer al final
        self.scroll_layout.addStretch()
    
    def _show_login_message(self):
        """Mostrar mensaje de login requerido"""
        # Limpiar layout
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Crear widget de mensaje
        message_widget = QFrame()
        message_widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px dashed #dee2e6;
                border-radius: 8px;
                padding: 40px;
            }
        """)
        message_layout = QVBoxLayout(message_widget)
        message_layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel("🔐")
        icon_label.setFont(QFont("Arial", 48))
        icon_label.setAlignment(Qt.AlignCenter)
        message_layout.addWidget(icon_label)
        
        title_label = QLabel("Inicia Sesión para Ver tus Plugins")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        message_layout.addWidget(title_label)
        
        desc_label = QLabel("Accede a tu cuenta para ver los plugins disponibles y tus suscripciones")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #6c757d;")
        desc_label.setWordWrap(True)
        message_layout.addWidget(desc_label)
        
        self.scroll_layout.addWidget(message_widget)
        self.scroll_layout.addStretch()
    
    def _show_empty_message(self):
        """Mostrar mensaje cuando no hay plugins"""
        message_widget = QFrame()
        message_widget.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 40px;
            }
        """)
        message_layout = QVBoxLayout(message_widget)
        message_layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel("📭")
        icon_label.setFont(QFont("Arial", 48))
        icon_label.setAlignment(Qt.AlignCenter)
        message_layout.addWidget(icon_label)
        
        title_label = QLabel("No Hay Plugins Disponibles")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        message_layout.addWidget(title_label)
        
        self.scroll_layout.addWidget(message_widget)
        self.scroll_layout.addStretch()
    
    def install_plugin(self, plugin_id: str):
        """Instalar un plugin"""
        logger.info(f"Installing plugin: {plugin_id}")
        
        if not self.backend or not self.backend.is_authenticated():
            QMessageBox.warning(self, "No Autenticado", "Debes iniciar sesión para instalar plugins")
            return
        
        # Verificar licencia
        if plugin_id not in self.licenses or not self.licenses[plugin_id].is_licensed:
            QMessageBox.warning(self, "Licencia Requerida", 
                              f"Necesitas una licencia activa para instalar este plugin.\n\n"
                              f"Haz clic en 'Suscribirse' para obtener acceso.")
            return
        
        # Mostrar progreso
        progress = QMessageBox(self)
        progress.setWindowTitle("Instalando Plugin")
        progress.setText(f"Descargando e instalando {plugin_id}...")
        progress.setStandardButtons(QMessageBox.NoButton)
        progress.show()
        
        try:
            # Descargar plugin
            response = self.backend.download_plugin(plugin_id)
            
            progress.close()
            
            if response.success:
                QMessageBox.information(self, "✅ Plugin Instalado", 
                                      f"El plugin se ha instalado correctamente.\n\n"
                                      f"Reinicia el navegador para comenzar a usarlo.")
                
                # Recargar datos
                self.load_data()
            else:
                QMessageBox.critical(self, "❌ Error", 
                                   f"No se pudo instalar el plugin:\n{response.message}")
        
        except Exception as e:
            progress.close()
            logger.error(f"Error installing plugin: {e}")
            QMessageBox.critical(self, "Error", f"Error al instalar:\n{str(e)}")
    
    def purchase_plugin(self, plugin_id: str):
        """Iniciar proceso de compra de plugin"""
        logger.info(f"Purchase requested for: {plugin_id}")
        
        # Obtener info del plugin
        plugin = None
        for p in self.plugins:
            if p.id == plugin_id:
                plugin = p
                break
        
        if not plugin:
            return
        
        # Abrir dashboard web en la página de suscripción
        dashboard_url = "http://localhost:8001/app/dashboard.html"
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Suscripción a Plugin")
        msg.setText(f"<h3>{plugin.name}</h3>")
        msg.setInformativeText(
            f"<p><b>Precio:</b> ${plugin.price:.2f}/{plugin.billing_cycle}</p>"
            f"<p><b>Incluye:</b> {plugin.trial_days} días de prueba gratis</p>"
            f"<p>Para suscribirte, ve al dashboard web y completa el proceso de pago.</p>"
        )
        msg.setTextFormat(Qt.RichText)
        
        open_btn = msg.addButton("Abrir Dashboard", QMessageBox.ActionRole)
        cancel_btn = msg.addButton("Cancelar", QMessageBox.RejectRole)
        
        msg.exec()
        
        if msg.clickedButton() == open_btn:
            webbrowser.open(dashboard_url)
            
            # Mostrar instrucciones adicionales
            QMessageBox.information(self, "Instrucciones", 
                                  f"1. Completa la suscripción en el dashboard web\n"
                                  f"2. Vuelve a este panel\n"
                                  f"3. Haz clic en '🔄 Actualizar' para refrescar tus licencias\n"
                                  f"4. El botón 'Instalar' se habilitará automáticamente")
    
    def open_dashboard(self):
        """Abrir dashboard web"""
        webbrowser.open("http://localhost:8001/app/dashboard.html")
    
    def on_login(self, user):
        """Callback cuando el usuario inicia sesión"""
        logger.info(f"User logged in: {user.email}")
        QTimer.singleShot(1000, self.load_data)
    
    def on_plugin_downloaded(self, plugin_id: str, success: bool):
        """Callback cuando se descarga un plugin"""
        if success:
            logger.info(f"Plugin downloaded successfully: {plugin_id}")
            self.load_data()  # Recargar para actualizar estado

