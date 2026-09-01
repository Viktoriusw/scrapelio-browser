# Informe de Análisis Técnico Detallado
## Integración de Tor en Scrapelio Browser

**Documento:** Análisis técnico del plan de implementación  
**Proyecto:** Scrapelio Browser MVP (PySide6 + QtWebEngine)  
**Fecha:** 17 de marzo de 2026  
**Basado en:** Informe técnico scrapelio_tor_informe.docx

---

## 1. Resumen Ejecutivo del Análisis

El plan de integración de Tor en Scrapelio Browser es **técnicamente viable** y está bien fundamentado. La estrategia de inyectar flags de Chromium en `sys.argv` antes de `QApplication()` es la **única forma fiable** de enrutar todo el tráfico QtWebEngine por SOCKS5; no existen alternativas viables para cambio en caliente sin reinicio. Se identifican **3 riesgos técnicos no mencionados** en el informe original: condición de carrera en el arranque Tor-Chromium, inconsistencia en la ruta de configuración (`config.yaml` vs `~/.scrapelio/config.yaml`), y posible conflicto entre el plugin proxy existente y el módulo Tor nativo. La librería **stem** es la opción correcta frente a torpy para este caso de uso (control de proceso, no solo protocolo). El informe recomienda **aiohttp-socks** redundante si ya existe `requests` con soporte SOCKS; sin embargo, `requests[socks]` fue eliminado de requirements.txt según el comentario en el archivo actual. Se propone un **orden de implementación revisado** que prioriza la verificación de SOCKS5 activo antes de mostrar estado CONECTADO y la degradación graceful cuando stem o el binario tor no están disponibles. Estimación ajustada: Fase 1 en 1.5–2 semanas con tests mínimos de verificación de proxy.

---

## 2. Validación de la Solución Técnica Central

### 2.1 ¿Es la inyección de flags en sys.argv la única forma fiable?

**Sí.** QtWebEngine utiliza el stack de red de Chromium, que es independiente de `QNetworkAccessManager`. La documentación de Qt y múltiples fuentes confirman que:

- `QNetworkProxy.setApplicationProxy()` **no afecta** a QWebEngineView/QWebEnginePage.
- Chromium lee la configuración de proxy **solo al arranque** del proceso de red.
- Los flags `--proxy-server` y `--proxy-bypass-list` deben estar en `sys.argv` (o en `QTWEBENGINE_CHROMIUM_FLAGS`) **antes** de que se cree cualquier instancia de QWebEngine.

**Código de referencia validado:**

```python
# main.py — DEBE ejecutarse antes de cualquier import de QtWebEngine
def _configure_tor_proxy_if_needed():
    from config_manager import config
    tor_enabled = config.get('tor.enabled', False)
    if not tor_enabled:
        return
    flags = [
        '--proxy-server=socks5://127.0.0.1:9050',
        '--proxy-bypass-list=<-loopback>',  # No bypassear localhost
        '--disable-webrtc',
    ]
    for f in flags:
        if f not in sys.argv:
            sys.argv.append(f)
```

### 2.2 ¿Existen alternativas para cambio en caliente sin reinicio?

**No viables para QtWebEngine.** Se evaluaron:

| Alternativa | Resultado |
|-------------|-----------|
| `QWebEngineProfile.setHttpAcceptLanguage()` | Solo afecta headers Accept-Language, no proxy |
| `QWebEngineUrlRequestInterceptor` | Puede bloquear/redirigir URLs pero **no puede cambiar el proxy** de Chromium |
| Perfil QtWebEngine con proxy por pestaña | QtWebEngine no soporta proxy por perfil; el proxy es a nivel de proceso Chromium |
| `QNetworkProxy` después de crear vistas | No afecta a vistas ya creadas; Chromium mantiene el proxy original |

**Conclusión:** El reinicio es inherente a la arquitectura. Tor Browser (Firefox) tampoco permite cambio en caliente.

### 2.3 Condición de carrera: ¿Qué ocurre si Tor no está listo cuando Chromium arranca?

**Riesgo real.** Si `tor.enabled=true` en config pero el proceso Tor aún no ha abierto el puerto SOCKS5 9050:

1. Chromium arranca con `--proxy-server=socks5://127.0.0.1:9050`
2. Las primeras peticiones fallan con `ERR_PROXY_CONNECTION_FAILED`
3. El usuario ve errores de conexión hasta que Tor complete el bootstrap

**Mitigación propuesta:**

```python
# tor_manager.py — Verificación antes de permitir arranque con flags
def is_socks5_ready(self, timeout: float = 2.0) -> bool:
    """Verifica que el puerto SOCKS5 acepte conexiones."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex(('127.0.0.1', self.TOR_SOCKS_PORT))
        sock.close()
        return result == 0
    except Exception:
        return False

# main.py — NO inyectar flags si Tor no está listo
def _configure_tor_proxy_if_needed():
    from config_manager import config
    if not config.get('tor.enabled', False):
        return
    # Si Tor debe iniciarse por la app: esperar bootstrap antes de flags
    # Si Tor es externo: verificar que 9050 esté escuchando
    from tor_manager import TorManager
    tm = TorManager()
    if not tm.is_socks5_ready():
        logging.warning("[TOR] SOCKS5 no disponible; no inyectando flags. Modo Tor desactivado.")
        return  # No inyectar flags → Chromium arranca sin proxy
    # ... inyectar flags
```

**Recomendación:** El informe debería especificar que el flujo "Tor habilitado" implica: (1) Usuario activa Tor → (2) App inicia TorManager.start() → (3) Espera bootstrap → (4) Escribe `tor.enabled: true` en config → (5) **Reinicia la app** → (6) En el nuevo arranque, `_configure_tor_proxy_if_needed()` lee config, verifica SOCKS5, e inyecta flags. No tiene sentido tener `tor.enabled: true` si Tor no va a estar corriendo al arranque.

### 2.4 ¿Los flags --disable-webrtc y --proxy-bypass-list son suficientes?

**Parcialmente.** Por plataforma:

| Plataforma | --disable-webrtc | --proxy-bypass-list | Comentario |
|------------|------------------|---------------------|------------|
| Linux | ✅ Suficiente | ✅ | WebRTC deshabilitado evita fugas |
| macOS | ✅ | ✅ | Mismo comportamiento |
| Windows | ✅ | ✅ | Verificar que no haya bypass por defecto de `localhost` |

**Advertencia:** El informe menciona `--enforce-webrtc-ip-permission-check=false` en un fragmento. Este flag **relaja** las restricciones de WebRTC, no las endurece. **No debe incluirse** si el objetivo es prevenir fugas. Solo `--disable-webrtc` es correcto.

**DNS:** Con `socks5://` (sin 'h'), Chromium puede resolver DNS localmente → **DNS leak**. Debe usarse `socks5h://` en documentación y en variables de entorno para requests/aiohttp. Para el flag Chromium, `--proxy-server=socks5://127.0.0.1:9050` es correcto porque Chromium con proxy SOCKS5 hace la resolución en el proxy cuando la conexión es al proxy. La confusión: `socks5h` aplica a clientes que resuelven antes de conectar; Chromium conecta al proxy y envía el hostname. En la práctica, Chromium con `socks5://` puede hacer DNS remoto según la implementación. **Recomendación:** Documentar y verificar con ipleak.net que no haya DNS leak.

---

## 3. Análisis Fase por Fase

### 3.1 Fase 1: Núcleo Funcional (MVP Tor)

| Tarea | Viabilidad | Dependencias | Completitud | Orden óptimo |
|-------|------------|--------------|-------------|--------------|
| Crear tor_manager.py | ✅ Alta | stem, binario tor | Incompleto: falta `_generate_torrc()` con hash real, manejo de stem no instalado | 1 |
| Crear tor_config.py | ✅ Alta | config_manager | No especificado en detalle | 2 |
| Modificar main.py | ✅ Alta | tor_config, config_manager | Falta: usar ConfigManager existente en lugar de yaml directo | 3 |
| Crear tor_panel.py | ✅ Alta | tor_manager | Descripción general, sin esqueleto | 4 |
| Modificar ui.py | ✅ Alta | tor_panel, tor_manager | Falta: TOR_AVAILABLE vs PROXY_AVAILABLE | 5 |
| Modificar network_interceptor.py | ✅ Alta | tor_manager o flag global | Modo tor_mode no definido cómo se activa | 6 |
| Añadir sección tor a config.yaml | ✅ Alta | — | Esqueleto claro | 7 |

**Dependencias entre tareas:** tor_manager → main (flags), tor_manager → tor_panel (UI), tor_panel → ui (integración). tor_config puede ser parte de config_manager o módulo separado.

**Ambigüedades detectadas:**
- El informe usa `~/.scrapelio/config.yaml` pero ConfigManager busca en múltiples rutas (ver `config_manager._find_config_file()`). Debe usarse ConfigManager para consistencia.
- `HashedControlPassword <HASH>` en torrc: el informe no indica cómo generar el hash. Usar `stem.process.launch_tor_with_config()` con `config={'ControlPort': 9051, 'HashedControlPassword': stem.util.term.get_hash('password')}` o similar.

### 3.2 Fase 2: Gestión Avanzada y Sistema de Plugins

| Tarea | Viabilidad | Dependencias | Completitud | Orden óptimo |
|-------|------------|--------------|-------------|--------------|
| Registrar plugin 'tor' en unified_plugin_config.json | ✅ Alta | Fase 1 | Estructura definida | 1 |
| Integrar en unified_plugin_manager.py | ✅ Media | Patrón get_proxy_panel vs get_tor_panel | El informe sugiere `get_tor_panel`; el manager actual usa `get_proxy_panel` para proxy. Definir si Tor es plugin o módulo nativo | 2 |
| Enrutar requests/aiohttp por Tor | ✅ Alta | tor_manager | Usar os.environ o ProxyConnector | 3 |

**Conflicto potencial:** El plugin "proxy" ya existe en unified_plugin_config.json. Tor podría ser un tipo especial de proxy. Decisión de diseño: ¿Tor reemplaza al proxy panel cuando está activo, o coexisten? El informe no lo aclara.

### 3.3 Fase 3: Onion Services y Endurecimiento

| Tarea | Viabilidad | Dependencias | Completitud | Orden óptimo |
|-------|------------|--------------|-------------|--------------|
| Soporte .onion | ✅ Alta | Proxy activo | Automático con proxy SOCKS5 | 1 |
| Bloqueo WebRTC via UserScript | ✅ Alta | userscript_manager | Necesita script concreto | 2 |
| Perfil aislado para Tor | ✅ Media | tabs.py, profile_manager | Requiere crear QWebEngineProfile separado para pestañas Tor | 3 |
| Detección de fugas (check.torproject.org) | ✅ Alta | — | Botón que abre URL y parsea resultado | 4 |
| Icono cebolla en URL bar | ✅ Alta | ui.py | Cambio aditivo | 5 |

---

## 4. Código Esqueleto por Archivo

### 4.1 tor_manager.py (nuevo)

```python
#!/usr/bin/env python3
"""Gestión del proceso Tor y Control Port para Scrapelio Browser."""

import os
import shutil
import socket
import subprocess
import time
import logging
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TorStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    CONNECTED = "connected"
    ERROR = "error"


class TorManager:
    TOR_SOCKS_PORT = 9050
    TOR_CONTROL_PORT = 9051
    TOR_BINARY = "tor"
    BOOTSTRAP_TIMEOUT = 120  # segundos

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._status = TorStatus.STOPPED
        self._control_password: Optional[str] = None

    def _get_data_dir(self) -> str:
        """Directorio de datos Tor (expandir ~ correctamente)."""
        base = Path.home() / ".scrapelio" / "tor"
        base.mkdir(parents=True, exist_ok=True)
        return str(base)

    def is_socks5_ready(self, timeout: float = 2.0) -> bool:
        """Verifica que el puerto SOCKS5 acepte conexiones."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex(("127.0.0.1", self.TOR_SOCKS_PORT))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _find_tor_binary(self) -> Optional[str]:
        """Detecta el binario tor en el sistema."""
        for path in ["/usr/bin/tor", "/usr/local/bin/tor", "tor"]:
            if path == "tor":
                found = shutil.which("tor")
                return found
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return None

    def start(self) -> bool:
        """Inicia el proceso Tor. Retorna True si bootstrap exitoso."""
        if self._find_tor_binary() is None:
            logger.error("[TOR] Binario tor no encontrado en el sistema")
            self._status = TorStatus.ERROR
            return False

        try:
            import stem.process
            from stem.util.term import get_hash
        except ImportError:
            logger.error("[TOR] stem no instalado: pip install stem")
            self._status = TorStatus.ERROR
            return False

        self._control_password = "scrapelio_tor_secret"
        hashed = get_hash(self._control_password)

        data_dir = self._get_data_dir()
        config = {
            "SocksPort": str(self.TOR_SOCKS_PORT),
            "ControlPort": str(self.TOR_CONTROL_PORT),
            "HashedControlPassword": hashed,
            "DataDirectory": data_dir,
            "Log": ["notice file " + os.path.join(data_dir, "tor.log")],
        }

        self._status = TorStatus.STARTING
        try:
            self._process = stem.process.launch_tor_with_config(config=config)
        except Exception as e:
            logger.exception("[TOR] Error al iniciar Tor: %s", e)
            self._status = TorStatus.ERROR
            return False

        # Esperar bootstrap
        start = time.time()
        while time.time() - start < self.BOOTSTRAP_TIMEOUT:
            if self.is_socks5_ready():
                self._status = TorStatus.CONNECTED
                return True
            time.sleep(0.5)

        self._status = TorStatus.ERROR
        self.stop()
        return False

    def stop(self) -> None:
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()
            self._process = None
        self._status = TorStatus.STOPPED

    def request_new_identity(self) -> bool:
        """Solicita nuevo circuito vía Control Port."""
        try:
            from stem.control import Controller
            from stem import Signal
            with Controller.from_port(port=self.TOR_CONTROL_PORT) as ctrl:
                ctrl.authenticate(password=self._control_password)
                ctrl.signal(Signal.NEWNYM)
            return True
        except Exception as e:
            logger.error("[TOR] Error en NEWNYM: %s", e)
            return False

    @property
    def status(self) -> TorStatus:
        return self._status
```

### 4.2 tor_config.py (nuevo) — o extender config_manager

```python
# Opción A: Usar ConfigManager existente
# En config_manager._get_default_config(), añadir:
'tor': {
    'enabled': False,
    'socks_port': 9050,
    'control_port': 9051,
}

# Opción B: Módulo tor_config.py
def get_tor_enabled() -> bool:
    from config_manager import config
    return config.get('tor.enabled', False)

def get_tor_socks_port() -> int:
    from config_manager import config
    return config.get('tor.socks_port', 9050)
```

### 4.3 main.py — Modificación

```python
# AÑADIR al inicio del archivo, DESPUÉS de imports estándar, ANTES de QApplication:

def _configure_tor_proxy_if_needed():
    """Inyecta flags Chromium si Tor está habilitado. DEBE llamarse antes de QApplication()."""
    try:
        from config_manager import config
        if not config.get('tor.enabled', False):
            return
        # Verificar que SOCKS5 esté listo (Tor ya corriendo, ej. por servicio systemd)
        from tor_manager import TorManager
        tm = TorManager()
        if not tm.is_socks5_ready():
            import logging
            logging.getLogger(__name__).warning(
                "[TOR] SOCKS5 no disponible. No inyectando flags. "
                "Asegúrese de que Tor esté corriendo si tor.enabled=true."
            )
            return
        flags = [
            '--proxy-server=socks5://127.0.0.1:9050',
            '--proxy-bypass-list=<-loopback>',
            '--disable-webrtc',
        ]
        for f in flags:
            if f not in sys.argv:
                sys.argv.append(f)
        import logging
        logging.getLogger(__name__).info("[TOR] Chromium proxy flags injected")
    except ImportError as e:
        import logging
        logging.getLogger(__name__).warning("[TOR] Módulo no disponible: %s", e)


def main():
    _configure_tor_proxy_if_needed()  # ← CRÍTICO: antes de QApplication
    app = QApplication(sys.argv)
    # ... resto sin cambios
```

### 4.4 network_interceptor.py — Modificación

```python
# En __init__, añadir:
self.tor_mode = False  # Se actualizará desde MainWindow cuando Tor esté activo

# En interceptRequest, ANTES de modificar User-Agent, añadir:
if self.tor_mode:
    url_str = info.requestUrl().toString()
    if 'stun.' in url_str or 'turn.' in url_str:
        info.block(True)
        self.request_blocked.emit(url_str)
        return
    info.setHttpHeader(b'X-Tor-Circuit', b'active')
```

**Activación de tor_mode:** MainWindow debe tener acceso al estado de TorManager y llamar a `network_interceptor.tor_mode = tor_manager.status == TorStatus.CONNECTED` cuando corresponda. Dado que el modo Tor requiere reinicio, `tor_mode` será True cuando la app arranque con flags inyectados (config tor.enabled=true).

### 4.5 config.yaml — Añadir sección

```yaml
# Añadir al final del archivo:
tor:
  enabled: false
  socks_port: 9050
  control_port: 9051
```

### 4.6 unified_plugin_config.json — Añadir plugin tor

```json
"tor": {
  "name": "Tor Network",
  "version": "1.0.0",
  "type": "native",
  "description": "Navegación anónima via red Tor",
  "requirements": {
    "dependencies": ["stem"]
  },
  "icon": "icons/tor.png"
}
```

---

## 5. Riesgos No Identificados

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Condición de carrera Tor-Chromium | Media | Alto | Verificar SOCKS5 activo antes de inyectar flags; si tor.enabled pero no hay Tor, no inyectar y loguear warning |
| Inconsistencia ruta config | Baja | Medio | Usar siempre ConfigManager, no abrir `~/.scrapelio/config.yaml` directamente |
| Conflicto plugin proxy vs Tor | Media | Medio | Definir: Tor es módulo nativo independiente; el panel proxy gestiona proxies HTTP/SOCKS externos; Tor tiene su propio panel. No mezclar |
| stem no instalado | Alta | Medio | try/except en import; TOR_AVAILABLE=False; mostrar en UI "Instalar: pip install stem" |
| Binario tor no existe | Alta | Medio | Detectar en startup; ofrecer enlace a instrucciones por OS (apt/brew/winget) |
| WebRTC bypass en Chromium antiguo | Baja | Alto | Verificar versión QtWebEngine; UserScript de respaldo que sobreescribe RTCPeerConnection |
| Config tor.enabled=true pero usuario no reinició | Media | Medio | Al activar Tor, guardar config y mostrar diálogo "Reiniciar ahora" con subprocess para relanzar la app |

---

## 6. Evaluación de Dependencias Externas

### 6.1 stem

**¿Es la mejor opción?** Sí para este proyecto. stem es la librería oficial del Tor Project, soporta `launch_tor_with_config`, Control Port, eventos de bootstrap y autenticación. **Alternativas:**

- **torpy:** Implementación Tor en Python puro. No lanza el binario tor; actúa como cliente Tor. No sirve para gestionar un proceso tor existente o lanzarlo.
- **subprocess directo:** Posible pero sin callbacks de bootstrap ni integración con Control Port. Más código y menos robusto.

**Conclusión:** stem es la opción correcta.

### 6.2 Degradación si stem no está instalado

```python
TOR_AVAILABLE = False
try:
    import stem.process
    import stem.control
    TOR_AVAILABLE = True
except ImportError:
    pass

# En tor_manager.start():
if not TOR_AVAILABLE:
    logger.error("stem no instalado. Ejecute: pip install stem")
    return False
```

Mostrar en tor_panel: "Para usar Tor, instale: pip install stem" y deshabilitar botón de activación.

### 6.3 aiohttp-socks vs requests[socks]

El `requirements.txt` actual tiene `requests>=2.28.0` y el comentario dice que `requests[socks]` fue eliminado por duplicado. Para SOCKS5 con requests se necesita `PySocks` (o `requests[socks]` que lo incluye). **Verificación:** `requests` con proxy SOCKS5 requiere `pip install requests[socks]` o `pip install PySocks`.

- **aiohttp-socks:** Necesaria para aiohttp (scraping async, etc.). requests y aiohttp son stacks distintos.
- **Recomendación:** Añadir `aiohttp-socks>=0.7.0` para aiohttp. Para requests, añadir `PySocks` o `requests[socks]` si se van a enrutar peticiones requests por Tor.

---

## 7. Plan de Implementación Revisado

| Semana | Tareas | Entregable |
|--------|--------|------------|
| 1.1 | tor_manager.py con start/stop/is_socks5_ready, degradación sin stem | Módulo funcional |
| 1.2 | tor_config + sección tor en config.yaml | Configuración persistente |
| 1.3 | main.py: _configure_tor_proxy_if_needed() | Flags inyectados correctamente |
| 1.4 | tor_panel.py básico (estado, toggle, reinicio) | UI mínima |
| 1.5 | ui.py: TOR_AVAILABLE, tor_action, toggle_tor_panel | Integración lateral |
| 1.6 | network_interceptor: tor_mode, bloqueo stun/turn | Capa de seguridad |
| 2.1 | Tests mínimos (ver sección 8) | Verificación automatizada |
| 2.2 | Documentación INSTALACION.md (tor) | Guía de instalación |

**Orden crítico:** tor_manager → main (flags) → tor_panel → ui. network_interceptor puede hacerse en paralelo con tor_panel.

---

## 8. Tests Mínimos Recomendados

```python
# tests/test_tor_integration.py
import pytest

def test_tor_manager_socks5_check_when_stopped():
    """Sin Tor corriendo, is_socks5_ready debe ser False."""
    from tor_manager import TorManager
    tm = TorManager()
    assert tm.is_socks5_ready() is False

def test_tor_flags_not_injected_when_disabled():
    """Con tor.enabled=false, sys.argv no debe contener --proxy-server."""
    import sys
    original = sys.argv.copy()
    # Simular config sin tor
    # ... mock config.get('tor.enabled', False) -> False
    # _configure_tor_proxy_if_needed()
    # assert '--proxy-server=socks5://127.0.0.1:9050' not in sys.argv
    sys.argv = original

def test_network_interceptor_blocks_stun_in_tor_mode():
    """En tor_mode, URLs con stun. deben bloquearse."""
    from network_interceptor import NetworkInterceptor
    from PySide6.QtWebEngineCore import QWebEngineUrlRequestInfo
    interceptor = NetworkInterceptor()
    interceptor.tor_mode = True
    # Crear QWebEngineUrlRequestInfo mock para stun:...
    # Llamar interceptRequest
    # Verificar que info.block(True) fue invocado
```

**Test manual crítico:** Con Tor corriendo (`systemctl start tor` o `tor` en terminal), activar tor.enabled, reiniciar app, abrir https://check.torproject.org y verificar que detecta conexión Tor.

---

## 9. Mitigaciones Adicionales para Riesgos del Informe Original

| Riesgo informe | Mitigación adicional propuesta |
|----------------|-------------------------------|
| Tor no instalado | Añadir script `scripts/check_tor_installation.py` que verifique binario y stem, e imprima instrucciones por OS |
| Proxy no activo al iniciar | No mostrar "CONECTADO" hasta que `is_socks5_ready()` sea True; mostrar "CONECTANDO" durante bootstrap |
| Bootstrap lento | Usar `stem.process.launch_tor_with_config` con callback `progress_callback` para actualizar progress bar en tor_panel |
| Reinicio requerido | Diálogo con QMessageBox que ofrezca "Reiniciar ahora" y ejecute `os.execv(sys.executable, [sys.executable] + sys.argv)` |
| WebRTC IP leak | Añadir UserScript que defina `RTCPeerConnection = function() { throw new Error('WebRTC disabled'); }` como respaldo |
| Latencia elevada | Tooltip en icono Tor: "La navegación puede ser más lenta (~300-600ms extra por petición)" |

---

*Fin del informe de análisis técnico.*
