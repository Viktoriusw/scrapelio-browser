import json

import os

from PySide6.QtWidgets import QTabWidget, QMenu

from PySide6.QtWebEngineWidgets import QWebEngineView

from PySide6.QtCore import QUrl, Qt, QSettings

from PySide6.QtGui import QIcon

from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage



class TabManager:

    SESSION_FILE = "tab_session.json"



    def __init__(self, history_manager, parent):

        self.history_manager = history_manager

        self.parent = parent

        self.tabs = QTabWidget()

        self.tabs.setDocumentMode(True)  # Flat tabs style

        self.tabs.setTabsClosable(True)

        self.tabs.tabCloseRequested.connect(self.close_tab)

        self.tabs.currentChanged.connect(self.on_tab_changed)



        # Configure tab context menu

        self.tabs.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)

        self.tabs.tabBar().customContextMenuRequested.connect(self._tab_context_menu)



        # Stack de pestañas cerradas para Ctrl+Shift+T
        self.closed_tabs_stack = []
        self.max_closed_tabs = 10  # Máximo de pestañas cerradas en el historial

        # Pestañas fijadas (pinned tabs)
        self.pinned_tabs = set()  # Conjunto de índices de pestañas fijadas

        # Don't create initial tab here - let ui.py handle it after session restore



    def _inject_dark_scrollbar_css(self, browser):

        """Inyecta CSS de scrollbar oscuro si el tema es dark"""

        try:

            theme = "light"

            if hasattr(self.parent, 'settings'):

                theme = self.parent.settings.value("theme", "light")

            if theme == "dark":

                css = """

                ::-webkit-scrollbar { width: 12px; background: #23272f; }

                ::-webkit-scrollbar-thumb { background: #5a5f6a; border-radius: 6px; }

                ::-webkit-scrollbar-thumb:hover { background: #6c7a89; }

                """

                js = f"""

                (function() {{

                    var style = document.getElementById('scrapelio-scrollbar-style');

                    if (!style) {{

                        style = document.createElement('style');

                        style.id = 'scrapelio-scrollbar-style';

                        style.innerHTML = `{css}`;

                        document.head.appendChild(style);

                    }}

                }})();

                """

                browser.page().runJavaScript(js)

        except Exception as e:

            print(f"Error injecting dark scrollbar CSS: {e}")



    def add_new_tab(self, url="https://duckduckgo.com"):

        """Creates a new tab and returns it"""

        try:

            if not isinstance(url, str) or not url.strip():

                url = "https://duckduckgo.com"



            # Crear el navegador

            browser = QWebEngineView()

            browser.setUrl(QUrl(url))



            # Configurar el perfil con datos aislados por usuario
            profile = browser.page().profile()

            # Si hay un profile_manager disponible, usar rutas específicas del perfil
            if hasattr(self.parent, 'profile_manager') and self.parent.profile_manager:
                profile_path = self.parent.profile_manager.get_profile_path()

                # Configurar rutas de almacenamiento persistente
                cookies_path = self.parent.profile_manager.get_profile_path(subdirectory="cookies")
                cache_path = self.parent.profile_manager.get_profile_path(subdirectory="cache")

                try:
                    profile.setPersistentStoragePath(profile_path)
                    profile.setCachePath(cache_path)
                    print(f"[PROFILE] Using profile-specific paths: {profile_path}")
                except Exception as e:
                    print(f"[WARNING] Could not set profile paths: {e}")

            profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
            profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)

            # Configurar interceptor de red si está disponible
            if hasattr(self.parent, 'network_interceptor') and self.parent.network_interceptor:
                try:
                    profile.setUrlRequestInterceptor(self.parent.network_interceptor)
                    print(f"[NETWORK] Interceptor configured - UA: {self.parent.network_interceptor.user_agent_type}")
                except Exception as e:
                    print(f"[WARNING] Could not set network interceptor: {e}")



            # Conectar señales

            browser.urlChanged.connect(self.on_url_changed)

            browser.urlChanged.connect(self.history_manager.record_history)

            browser.titleChanged.connect(lambda title: self.update_tab_title(title, browser))

            browser.iconChanged.connect(lambda icon: self.update_tab_icon(icon, browser))

            

            # Configurar menú contextual

            browser.setContextMenuPolicy(Qt.CustomContextMenu)

            browser.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, browser))



            # Configurar descargas

            if hasattr(self.parent, 'navigation_manager'):

                self.parent.navigation_manager.setup_downloads(browser)



            # Configurar gestor de contraseñas

            if hasattr(self.parent, 'password_manager'):

                self.parent.password_manager.setup_browser(browser)



            # Configurar inyección de UserScripts

            if hasattr(self.parent, 'userscript_manager'):

                browser.loadFinished.connect(lambda ok: self.inject_userscripts(browser, ok))



            # Añadir la pestaña

            index = self.tabs.addTab(browser, "New Tab")

            self.tabs.setCurrentIndex(index)

            

            # Actualizar la barra de URL si está disponible

            if hasattr(self.parent, 'url_bar'):

                self.parent.url_bar.setText(url)

            

            # TODO V2: Aplicar profile del grupo aquí si la pestaña va a un grupo específico

                

            print(f"Tab created successfully with URL: {url}")

            # Inyectar CSS de scrollbar oscuro si aplica

            self._inject_dark_scrollbar_css(browser)

            return browser

        except Exception as e:

            print(f"Error creating new tab: {str(e)}")

            return None



    def update_tab_icon(self, icon, browser):

        try:

            index = self.tabs.indexOf(browser)

            if index != -1:

                if icon.isNull():

                    icon = QIcon(":/icons/bookmark.png")

                self.tabs.setTabIcon(index, icon)

        except Exception as e:

            print(f"Error al actualizar el icono de la pestaña: {str(e)}")



    def update_tab_title(self, title, browser):

        try:

            index = self.tabs.indexOf(browser)

            if index != -1:

                if not title:

                    url = browser.url().toString()

                    title = url.split('/')[-1] if url else "New Tab"

                if len(title) > 30:

                    title = title[:27] + "..."

                

                self.tabs.setTabText(index, title)

                if self.tabs.currentWidget() == browser:

                    self.parent.setWindowTitle(f"{title} - Scrapelio")

                    

        except Exception as e:

            print(f"Error al actualizar el título de la pestaña: {str(e)}")



    def close_tab(self, index):

        try:

            if self.tabs.count() > 1:

                # Guardar información de la pestaña antes de cerrarla
                tab_widget = self.tabs.widget(index)
                if tab_widget and hasattr(tab_widget, 'url'):
                    tab_data = {
                        'url': tab_widget.url().toString(),
                        'title': self.tabs.tabText(index),
                        'icon': self.tabs.tabIcon(index)
                    }

                    # Agregar al stack de pestañas cerradas
                    self.closed_tabs_stack.append(tab_data)

                    # Limitar el tamaño del stack
                    if len(self.closed_tabs_stack) > self.max_closed_tabs:
                        self.closed_tabs_stack.pop(0)

                # Remover de pestañas fijadas si estaba fijada
                if index in self.pinned_tabs:
                    self.pinned_tabs.discard(index)
                    # Actualizar índices de pestañas fijadas
                    self.pinned_tabs = {i - 1 if i > index else i for i in self.pinned_tabs}

                self.tabs.removeTab(index)

                current_browser = self.tabs.currentWidget()

                if current_browser:

                    self.update_tab_title(current_browser.page().title(), current_browser)

        except Exception as e:

            print(f"Error al cerrar la pestaña: {str(e)}")



    def show_context_menu(self, pos, browser):

        try:

            menu = QMenu(self.parent)

            back_action = menu.addAction("Back")

            forward_action = menu.addAction("Forward")

            reload_action = menu.addAction("Reload")

            menu.addSeparator()

            open_in_new_tab = menu.addAction("Open in New Tab")

            menu.addSeparator()

            save_bookmark = menu.addAction("Save as Bookmark")

            action = menu.exec(browser.mapToGlobal(pos))

            if action == back_action:

                browser.back()

            elif action == forward_action:

                browser.forward()

            elif action == reload_action:

                browser.reload()

            elif action == open_in_new_tab:

                browser.page().runJavaScript(

                    f"var elem = document.elementFromPoint({pos.x()}, {pos.y()}); elem ? elem.href : null;",

                    self.open_link_in_new_tab

                )

            elif action == save_bookmark:

                current_url = browser.url().toString()

                if current_url:

                    self.parent.show_save_favorite_menu()

        except Exception as e:

            print(f"Error al mostrar el menú contextual: {str(e)}")



    def open_link_in_new_tab(self, link):

        try:

            if link:

                self.add_new_tab(link)

        except Exception as e:

            print(f"Error al abrir enlace en nueva pestaña: {str(e)}")



    def on_url_changed(self, url):

        """Maneja el cambio de URL en una pestaña"""

        try:

            # Actualizar la barra de URL si está disponible

            if hasattr(self.parent, 'url_bar'):

                self.parent.url_bar.setText(url.toString())

            if hasattr(self.parent, 'tabs'):

                browser = self.tabs.currentWidget()

                if browser:

                    self._inject_dark_scrollbar_css(browser)

        except Exception as e:

            print(f"Error al actualizar la URL: {str(e)}")



    def on_tab_changed(self, index):

        try:

            current_browser = self.tabs.widget(index)

            if current_browser:

                if hasattr(self.parent, 'devtools_dock'):

                    self.parent.devtools_dock.set_browser(current_browser)

                if hasattr(self.parent, 'url_bar'):

                    self.parent.url_bar.setText(current_browser.url().toString())

                self.update_tab_title(current_browser.page().title(), current_browser)

                

                # Sincronizar con el módulo de scraping si está disponible

                if hasattr(self.parent, 'scraping_integration') and self.parent.scraping_integration:

                    current_url = current_browser.url().toString()

                    # Actualizar el widget del navegador en el scraping integration

                    self.parent.scraping_integration.browser_widget = current_browser

                    

                    # Actualizar browser_tab en el panel de scraping

                    if hasattr(self.parent, 'scraping_panel') and self.parent.scraping_panel:

                        self.parent.scraping_panel.browser_tab = current_browser

                    

                    # Obtener el HTML de la página actual

                    current_browser.page().toHtml(

                        lambda html_content: self.parent.scraping_integration.update_content(html_content, current_url)

                    )

        except Exception as e:

            print(f"Error al cambiar de pestaña: {str(e)}")



    def guardar_sesion(self):

        """Guarda la sesión actual de pestañas (URL) en un archivo JSON"""

        session = []

        for i in range(self.tabs.count()):

            browser = self.tabs.widget(i)

            url = browser.url().toString()

            session.append({"url": url})

        try:

            with open(self.SESSION_FILE, "w", encoding="utf-8") as f:

                json.dump(session, f, ensure_ascii=False, indent=2)

            print(f"Sesión guardada con {len(session)} pestañas.")

        except Exception as e:

            print(f"Error al guardar la sesión: {e}")



    def restaurar_sesion(self):

        """Restore tab session from JSON file"""

        if not os.path.exists(self.SESSION_FILE):

            print("No saved session to restore.")

            return False

        

        try:

            with open(self.SESSION_FILE, "r", encoding="utf-8") as f:

                session = json.load(f)

            

            # Validate session data

            if not session or not isinstance(session, list):

                print("Session file is empty or invalid, no tabs to restore.")

                return False

            

            # Close existing tabs safely if any exist

            tab_count = self.tabs.count()

            if tab_count > 0:

                # Remove tabs from end to beginning to avoid index issues

                for i in range(tab_count - 1, -1, -1):

                    try:

                        self.close_tab(i)

                    except Exception as e:

                        print(f"Error closing tab {i}: {e}")

            

            # Restore session tabs

            for tab_data in session:

                url = tab_data.get("url", "https://duckduckgo.com")

                self.add_new_tab(url)

            

            print(f"Session restored with {len(session)} tabs.")

            return True

            

        except json.JSONDecodeError as e:

            print(f"Error decoding session file: {e}. Starting fresh.")

            return False

        except Exception as e:

            print(f"Error restoring session: {e}")

            import traceback

            traceback.print_exc()

            return False



    def buscar_pestanas(self, query):

        """Filtra las pestañas abiertas por título o URL"""

        query = query.lower().strip()

        for i in range(self.tabs.count()):

            browser = self.tabs.widget(i)

            title = self.tabs.tabText(i).lower()

            url = browser.url().toString().lower()

            visible = query in title or query in url or not query

            self.tabs.setTabVisible(i, visible)







    def close_other_tabs(self, keep_index):

        """Cerrar todas las pestañas excepto la especificada"""

        try:

            # Cerrar desde el final para mantener índices válidos

            for i in range(self.tabs.count() - 1, -1, -1):

                if i != keep_index:

                    self.close_tab(i)

        except Exception as e:

            print(f"Error closing other tabs: {e}")



    def _tab_context_menu(self, pos):

        """Menú contextual por pestaña (MEJORADO)"""

        index = self.tabs.tabBar().tabAt(pos)

        if index < 0:

            return

        menu = QMenu(self.tabs)



        # Recargar pestaña
        reload_action = menu.addAction("🔄 Recargar")

        # Duplicar pestaña
        duplicate_action = menu.addAction("📋 Duplicar pestaña")

        menu.addSeparator()

        # Fijar/Desfijar pestaña
        if index in self.pinned_tabs:
            pin_action = menu.addAction("📌 Desfijar pestaña")
        else:
            pin_action = menu.addAction("📌 Fijar pestaña")

        # Silenciar/Activar audio
        tab_widget = self.tabs.widget(index)
        if tab_widget and hasattr(tab_widget, 'page'):
            if tab_widget.page().isAudioMuted():
                mute_action = menu.addAction("🔊 Activar audio")
            else:
                mute_action = menu.addAction("🔇 Silenciar audio")
        else:
            mute_action = None

        menu.addSeparator()

        # Acciones de cierre

        close_action = menu.addAction("✕ Cerrar pestaña")

        close_others_action = menu.addAction("✕ Cerrar otras pestañas")

        close_right_action = menu.addAction("✕ Cerrar pestañas a la derecha")



        # Ejecutar menú

        action = menu.exec(self.tabs.tabBar().mapToGlobal(pos))



        # Procesar acciones
        if action == reload_action:
            tab_widget = self.tabs.widget(index)
            if tab_widget:
                tab_widget.reload()

        elif action == duplicate_action:
            self.duplicate_tab(index)

        elif action == pin_action:
            self.toggle_pin_tab(index)

        elif action == mute_action and mute_action is not None:
            self.mute_tab(index)

        elif action == close_action:

            self.close_tab(index)

        elif action == close_others_action:

            self.close_other_tabs(index)

        elif action == close_right_action:
            # Cerrar todas las pestañas a la derecha
            for i in range(self.tabs.count() - 1, index, -1):
                self.close_tab(i)



    def limpiar_sesion(self):

        """Limpia la sesión guardada (elimina el archivo de sesión)"""

        try:

            if os.path.exists(self.SESSION_FILE):

                os.remove(self.SESSION_FILE)

                print("Sesión limpiada correctamente.")

            else:

                print("No hay sesión guardada para limpiar.")

        except Exception as e:

            print(f"Error al limpiar la sesión: {e}")



    # ============================================================================
    # NUEVAS FUNCIONALIDADES - Plan de Acción UX/UI
    # ============================================================================

    def reopen_closed_tab(self):
        """Reabrir la última pestaña cerrada (Ctrl+Shift+T)"""
        if not self.closed_tabs_stack:
            print("No hay pestañas cerradas para reabrir")
            return None

        # Obtener última pestaña cerrada
        tab_data = self.closed_tabs_stack.pop()

        # Crear nueva pestaña con la URL guardada
        new_tab = self.add_new_tab(tab_data['url'])

        # Restaurar icono si es posible
        if tab_data.get('icon'):
            current_index = self.tabs.indexOf(new_tab)
            self.tabs.setTabIcon(current_index, tab_data['icon'])

        print(f"Reabierta pestaña: {tab_data['title']}")
        return new_tab

    def duplicate_tab(self, index=None):
        """Duplicar una pestaña existente"""
        if index is None:
            index = self.tabs.currentIndex()

        if index < 0:
            return None

        # Obtener pestaña actual
        current_tab = self.tabs.widget(index)
        if not current_tab or not hasattr(current_tab, 'url'):
            return None

        # Crear nueva pestaña con la misma URL
        url = current_tab.url().toString()
        new_tab = self.add_new_tab(url)

        print(f"Pestaña duplicada: {url}")
        return new_tab

    def pin_tab(self, index=None):
        """Fijar una pestaña (evitar cierre accidental)"""
        if index is None:
            index = self.tabs.currentIndex()

        if index < 0:
            return

        # Agregar a conjunto de pestañas fijadas
        self.pinned_tabs.add(index)

        # Actualizar apariencia
        self._update_pinned_tab_appearance(index, pinned=True)

        # Deshabilitar botón de cerrar
        self.tabs.tabBar().setTabButton(index, self.tabs.tabBar().RightSide, None)

        print(f"Pestaña {index} fijada")

    def unpin_tab(self, index=None):
        """Desfijar una pestaña"""
        if index is None:
            index = self.tabs.currentIndex()

        if index < 0 or index not in self.pinned_tabs:
            return

        # Remover de conjunto de pestañas fijadas
        self.pinned_tabs.discard(index)

        # Actualizar apariencia
        self._update_pinned_tab_appearance(index, pinned=False)

        # Restaurar botón de cerrar
        from PySide6.QtWidgets import QToolButton
        close_button = QToolButton()
        close_button.setText("✕")
        close_button.clicked.connect(lambda: self.close_tab(index))
        self.tabs.tabBar().setTabButton(index, self.tabs.tabBar().RightSide, close_button)

        print(f"Pestaña {index} desfijada")

    def toggle_pin_tab(self, index=None):
        """Alternar fijado de pestaña"""
        if index is None:
            index = self.tabs.currentIndex()

        if index in self.pinned_tabs:
            self.unpin_tab(index)
        else:
            self.pin_tab(index)

    def _update_pinned_tab_appearance(self, index, pinned=True):
        """Actualizar apariencia visual de pestaña fijada"""
        # Reducir ancho de pestaña fijada
        tab_bar = self.tabs.tabBar()

        if pinned:
            # Pestaña fijada: más estrecha, solo icono
            # (Esto requeriría subclase de QTabBar para control completo)
            # Por ahora solo marcamos visualmente
            current_text = self.tabs.tabText(index)
            if not current_text.startswith("📌 "):
                self.tabs.setTabText(index, f"📌 {current_text}")
        else:
            # Restaurar texto normal
            current_text = self.tabs.tabText(index)
            if current_text.startswith("📌 "):
                self.tabs.setTabText(index, current_text[2:])

    def mute_tab(self, index=None):
        """Silenciar audio de una pestaña"""
        if index is None:
            index = self.tabs.currentIndex()

        if index < 0:
            return

        tab_widget = self.tabs.widget(index)
        if tab_widget and hasattr(tab_widget, 'page'):
            page = tab_widget.page()

            # Silenciar audio
            page.setAudioMuted(not page.isAudioMuted())

            # Actualizar indicador visual
            if page.isAudioMuted():
                current_text = self.tabs.tabText(index)
                if not current_text.startswith("🔇 "):
                    self.tabs.setTabText(index, f"🔇 {current_text}")
            else:
                current_text = self.tabs.tabText(index)
                if current_text.startswith("🔇 "):
                    self.tabs.setTabText(index, current_text[2:])

            print(f"Pestaña {index} {'silenciada' if page.isAudioMuted() else 'con audio'}")

    def get_closed_tabs_history(self):
        """Obtener historial de pestañas cerradas"""
        return list(reversed(self.closed_tabs_stack))  # Más reciente primero

    def inject_userscripts(self, browser, ok):
        """Inyectar UserScripts en la página cargada"""
        if not ok or not hasattr(self.parent, 'userscript_manager'):
            return

        url = browser.url().toString()
        if not url or url == 'about:blank':
            return

        # Obtener scripts que coinciden con la URL
        scripts = self.parent.userscript_manager.get_scripts_for_url(url)

        if not scripts:
            return

        print(f"[UserScripts] Injecting {len(scripts)} scripts into {url}")

        for script in scripts:
            try:
                # Preparar código del script
                code = script['code']

                # Crear wrapper con API GM_*
                script_id = script['id']
                wrapped_code = f"""
(function() {{
    // GM API
    var GM_setValue = function(key, value) {{
        console.log('[GM_setValue]', key, value);
        // En un entorno real, esto se comunicaría con Python
    }};

    var GM_getValue = function(key, defaultValue) {{
        console.log('[GM_getValue]', key);
        return defaultValue;
    }};

    var GM_addStyle = function(css) {{
        var style = document.createElement('style');
        style.textContent = css;
        document.head.appendChild(style);
        console.log('[GM_addStyle] CSS injected');
    }};

    var GM_log = function(message) {{
        console.log('[UserScript: {script['name']}]', message);
    }};

    // Ejecutar script de usuario
    try {{
        {code}
    }} catch(e) {{
        console.error('[UserScript Error: {script['name']}]', e);
    }}
}})();
"""

                # Inyectar script
                browser.page().runJavaScript(wrapped_code, lambda result: None)
                print(f"[UserScript] Injected: {script['name']}")

            except Exception as e:
                print(f"[ERROR] Failed to inject script '{script['name']}': {e}")