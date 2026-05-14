#!/usr/bin/env python3
"""
Scrapelio Browser — punto de entrada principal.
"""

import importlib.util
import logging
import os
import socket
import sys
from threading import Thread, Event

from PySide6.QtWidgets import QApplication

# Copia de sys.argv ANTES de cualquier modificación (para reinicio limpio)
sys.argv_original = sys.argv.copy()

import tor_restart
tor_restart.init(sys.argv_original)

from constants import (
    APP_NAME,
    BOOKMARK_SOCKET_HOST,
    BOOKMARK_SOCKET_PORT,
    SOCKET_ACCEPT_TIMEOUT,
)

# ── Logging centralizado ──────────────────────────────────────────────────────
# setup_logging() configura: fichero rotante, colores en consola, buffer en
# memoria, captura de excepciones en hilos y mensajes Qt.
from logger_setup import setup_logging

setup_logging(level="DEBUG")
_logger = logging.getLogger(__name__)


def _configure_tor_proxy_if_needed():
    """
    Inyecta flags de proxy Chromium si Tor está habilitado.
    DEBE llamarse ANTES de cargar ui.py (que importa QtWebEngine).
    Usa --webEngineArgs en sys.argv (QTWEBENGINE_CHROMIUM_FLAGS sobrescribe webEngineArgs).
    """
    try:
        from config_manager import config
        if not config.is_tor_enabled():
            if "proxy-server" in os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", ""):
                os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = ""
            _logger.debug("[TOR] tor.enabled=false, omitiendo proxy")
            return
        from tor_manager import TorManager
        tm = TorManager()
        socks_port = config.get("tor.socks_port", 9150)
        _logger.debug("[TOR] Verificando SOCKS5 en 127.0.0.1:%s...", socks_port)
        if not tm.is_socks5_ready():
            _logger.warning(
                "[TOR] SOCKS5 no disponible en 127.0.0.1:%s. No inyectando flags. "
                "Tor dejó de correr entre sesiones.",
                socks_port,
            )
            config.set_tor_enabled(False)
            config.persist_config()
            return
        # CRÍTICO: NO usar QTWEBENGINE_CHROMIUM_FLAGS — sobrescribe webEngineArgs y
        # host-resolver-rules tiene espacios que se dividen mal. Usar SOLO sys.argv.
        # Formato Chromium: MAP * ^NOTFOUND bloquea DNS local; EXCLUDE 127.0.0.1 permite
        # conectar al proxy. Ver: chromium.org/developers/design-documents/network-stack/socks-proxy
        os.environ.pop("QTWEBENGINE_CHROMIUM_FLAGS", None)
        webengine_args = [
            "--webEngineArgs",
            f"--proxy-server=socks5://127.0.0.1:{socks_port}",
            "--host-resolver-rules=MAP * ^NOTFOUND , EXCLUDE 127.0.0.1",
            "--proxy-bypass-list=<-loopback>",
            "--disable-webrtc",
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
        ]
        for arg in webengine_args:
            if arg not in sys.argv:
                sys.argv.append(arg)
        _logger.info("[TOR] Chromium proxy flags inyectados vía --webEngineArgs (sin QTWEBENGINE_CHROMIUM_FLAGS)")
    except ImportError as e:
        _logger.warning("[TOR] Módulo no disponible: %s", e)


# CRÍTICO: Configurar proxy Tor ANTES de cargar ui (QtWebEngine).
_configure_tor_proxy_if_needed()

# Importar MainWindow desde ui.py (no desde el paquete ui/)
sys.path.insert(0, os.path.dirname(__file__))
spec = importlib.util.spec_from_file_location(
    "ui_module", os.path.join(os.path.dirname(__file__), "ui.py")
)
ui_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_module)
MainWindow = ui_module.MainWindow


class BookmarkListener(Thread):
    """Hilo que escucha URLs entrantes por socket TCP para navegación externa."""

    def __init__(self, navigation_manager):
        super().__init__()
        self.navigation_manager = navigation_manager
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((BOOKMARK_SOCKET_HOST, BOOKMARK_SOCKET_PORT))
        self.server_socket.settimeout(SOCKET_ACCEPT_TIMEOUT)
        self.server_socket.listen(1)
        self._stop_event = Event()
        self.daemon = True
    def run(self):
        while not self._stop_event.is_set():
            try:
                client_socket, _ = self.server_socket.accept()
                with client_socket:
                    url = client_socket.recv(1024).decode("utf-8").strip()
                    if url:
                        _logger.info("URL recibida por socket: %s", url)
                        try:
                            self.navigation_manager.navigate_to_url(url)
                        except Exception as e:
                            _logger.error("Error navegando a URL recibida: %s", e)
            except socket.timeout:
                continue
            except Exception as e:
                if not self._stop_event.is_set():
                    _logger.error("Error en BookmarkListener: %s", e, exc_info=True)
    def stop(self):
        """Detiene el hilo de escucha de forma segura."""
        self._stop_event.set()
        try:
            # Conexión temporal para desbloquear accept()
            temp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            temp.connect((BOOKMARK_SOCKET_HOST, BOOKMARK_SOCKET_PORT))
            temp.close()
        except Exception:
            pass
        if self.is_alive():
            self.join(timeout=2)
        try:
            self.server_socket.close()
        except Exception:
            pass


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)

    window = MainWindow()

    bookmark_listener = None
    if hasattr(window, "navigation_manager") and window.navigation_manager:
        bookmark_listener = BookmarkListener(window.navigation_manager)
        bookmark_listener.start()
    else:
        _logger.warning("NavigationManager no disponible — socket listener desactivado")
    window.show()

    try:
        exit_code = app.exec()
    except Exception as e:
        _logger.error("Error de aplicación: %s", e, exc_info=True)
        exit_code = 1
    finally:
        if bookmark_listener:
            bookmark_listener.stop()
        sys.exit(exit_code)


def restart_with_tor(enabled: bool, window):
    """
    Guarda tor.enabled, URLs de pestañas y reinicia el navegador.

    Args:
        enabled: True para activar Tor, False para desactivar.
        window: MainWindow para obtener URLs de pestañas.
    """
    tor_restart.restart_with_tor(enabled, window)


if __name__ == "__main__":
    main()
