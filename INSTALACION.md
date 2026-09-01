# Guía de instalación — Scrapelio Browser v3.4.14

Navegador de escritorio con **PySide6 + Qt WebEngine**. Sin estas librerías el programa **no arranca**.

---

## ⚠️ Requisito crítico: PySide6

Scrapelio Browser **depende al 100 % de PySide6** (bindings de Qt 6 para Python). En concreto necesita:

| Módulo | Función |
|---|---|
| `PySide6.QtWidgets` | Ventanas, botones, paneles |
| `PySide6.QtWebEngineWidgets` | Motor de navegación (renderizado web) |
| `PySide6.QtWebEngineCore` | Perfiles, cookies, interceptor de red |

> **Importante:** el código usa **PySide6 exclusivamente**. Instalar PyQt5 o PyQt6 **no sirve** — el navegador no los reconoce. No instales PySide6 y PyQt a la vez (conflictan).

### Por qué a veces falla `pip install -r requirements.txt`

Al instalar todas las dependencias de golpe, `pip` puede **interrumpirse** antes de completar PySide6 si otro paquete falla (p. ej. `chromadb`, `sentence-transformers`). Resultado: el entorno virtual queda creado pero **sin PySide6**, y `main.py` falla con `ModuleNotFoundError: No module named 'PySide6'`.

**Solución:** instalar PySide6 **primero y de forma explícita**, verificar que funciona, y después el resto.

### Instalación correcta de PySide6 (paso obligatorio)

Con el entorno virtual **activado** (`source venv/bin/activate`):

```bash
# 1. Comprobar que pip apunta al venv (NO al Python del sistema)
which python3          # Linux/macOS — debe mostrar .../venv/bin/python3
where python           # Windows — debe mostrar ...\venv_win\Scripts\python.exe

# 2. Instalar PySide6 ANTES que el resto
pip install --upgrade pip setuptools wheel
pip install --upgrade "PySide6>=6.5.0"

# 3. Verificar que Qt WebEngine carga (si esto falla, el navegador no funciona)
python3 -c "
from PySide6 import __version__
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
print(f'PySide6 {__version__} + Qt WebEngine OK')
"

# 4. Instalar el resto de dependencias
pip install -r requirements.txt
```

En **Linux**, si el paso 3 falla con errores de `xcb`, `GL` o plugins de Qt, instala antes las bibliotecas del sistema (sección siguiente).

### Si PySide6 sigue sin instalarse en el venv

```bash
# Reinstalar forzando descarga limpia
pip uninstall -y PySide6 PySide6-Essentials PySide6-Addons 2>/dev/null
pip install --no-cache-dir --force-reinstall "PySide6>=6.5.0"

# Confirmar que está en el venv correcto
python3 -m pip show PySide6 | grep -E '^(Name|Version|Location)'
```

La línea `Location` debe apuntar a tu carpeta `venv/` o `venv_win/`, no a `/usr/lib/...`.

---

## Requisitos del sistema

| Componente | Mínimo recomendado |
|---|---|
| **SO** | Linux (Ubuntu/Debian/Fedora), Windows 10/11, macOS 12+ |
| **Python** | 3.10 – 3.12 (recomendado **3.11** para máxima compatibilidad con PySide6) |
| **RAM** | 4 GB (8 GB si usas IA local con embeddings) |
| **Disco** | ~2 GB libres (dependencias + modelos de IA opcionales) |
| **Pantalla** | Entorno gráfico (X11 o Wayland con soporte Qt) |

### Dependencias del sistema (Linux)

PySide6 y Qt WebEngine requieren bibliotecas nativas. En **Debian/Ubuntu**:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip \
  libxcb-cursor0 libxcb-xinerama0 libxcb-xtest0 \
  libgl1-mesa-glx libfontconfig1 libssl-dev \
  libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
  libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1
```

En **Fedora/RHEL**:

```bash
sudo dnf install -y python3 python3-pip \
  libxcb xcb-util-cursor mesa-libGL fontconfig openssl-devel
```

### Tor (opcional)

Para usar navegación anónima desde el panel Tor:

```bash
# Debian/Ubuntu
sudo apt install tor

# Fedora
sudo dnf install tor
```

El navegador usa los puertos **9150** (SOCKS5) y **9151** (control) para no chocar con una instancia Tor del sistema (9050/9051).

---

## Instalación desde código fuente

### 1. Obtener el proyecto

```bash
# Clonar o descomprimir el código en una carpeta de tu elección
cd /ruta/a/scrapelio-browser
```

Asegúrate de estar en la carpeta que contiene `main.py`, `requirements.txt` y `config.yaml`.

### 2. Crear entorno virtual (recomendado)

Usar un entorno virtual evita conflictos con el Python del sistema y el error `externally-managed-environment` en distros modernas.

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

**Windows (PowerShell o CMD):**

```cmd
python -m venv venv_win
venv_win\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
```

> En Windows también puedes usar el script incluido `run_windows.bat`, que crea el entorno e instala dependencias automáticamente la primera vez.

### 3. Instalar PySide6 (obligatorio, antes que el resto)

```bash
pip install --upgrade "PySide6>=6.5.0"
python3 -c "from PySide6.QtWebEngineWidgets import QWebEngineView; print('PySide6 OK')"
```

Si este comando falla, **no continúes** — revisa la sección [Requisito crítico: PySide6](#️-requisito-crítico-pyside6) y las dependencias del sistema de Linux.

### 4. Instalar el resto de dependencias de Python

```bash
pip install -r requirements.txt
```

**Dependencias principales** (definidas en `requirements.txt`):

| Paquete | Uso | ¿Obligatorio? |
|---|---|---|
| **`PySide6`** | **Interfaz gráfica y motor web (Qt WebEngine)** | **SÍ — sin esto no funciona** |
| `requests`, `aiohttp` | Red y API | Sí |
| `beautifulsoup4`, `lxml`, `selenium`, `playwright` | Scraping y plugins | Sí (para plugins) |
| `pandas`, `numpy`, `openpyxl` | Exportación de datos | Sí |
| `PyJWT`, `cryptography` | Autenticación y licencias | Sí |
| `stem`, `PySocks`, `aiohttp-socks` | Integración Tor/proxy | Sí |
| `sentence-transformers`, `chromadb` | Contexto semántico de páginas (IA) | No (degradación graceful) |
| `qtawesome`, `qdarktheme` | Iconos y temas | No |
| `psutil` | Monitor de rendimiento | Sí |

**Notas sobre paquetes opcionales:**

- `qdarktheme` puede no estar disponible en algunas versiones de Python; el navegador funciona sin él usando el motor de temas propio.
- `sentence-transformers` y `chromadb` son pesados (~1 GB); sin ellos la IA contextual degrada a búsqueda por palabras clave.
- `chromadb` puede requerir compiladores C++ en Linux: `sudo apt install build-essential`.

### 5. Instalar navegadores de Playwright (opcional)

Necesario solo si usas el plugin **Advanced Scraping** con Playwright:

```bash
playwright install chromium
# Opcional: playwright install firefox webkit
```

### 6. Verificar la instalación

```bash
python3 check_dependencies.py
```

El verificador comprueba **PySide6, QtWebEngineCore y QtWebEngineWidgets** por separado y muestra qué Python estás usando. Si PySide6 falla, verás instrucciones concretas de reinstalación.

Comprobación manual adicional:

```bash
python3 -c "
from PySide6 import __version__
from PySide6.QtWebEngineWidgets import QWebEngineView
print(f'PySide6 {__version__} + Qt WebEngine OK')
"
```

Verificación extendida (dependencias opcionales):

```bash
python3 -c "
import importlib
mods = [
    'PySide6.QtWebEngineWidgets', 'chromadb', 'sentence_transformers',
    'stem', 'qdarktheme', 'psutil'
]
for m in mods:
    try:
        importlib.import_module(m)
        print(f'  OK  {m}')
    except ImportError as e:
        print(f'  --  {m} (opcional): {e}')
"
```

---

## Ejecutar el navegador

### Linux / macOS

```bash
# Con entorno virtual activado
python3 main.py
```

Scripts auxiliares (disponibles en copias del proyecto; puedes recrearlos):

```bash
chmod +x run_scrapelio.sh install_dependencies.sh
./run_scrapelio.sh          # verifica deps e inicia
./install_dependencies.sh   # instala libs del sistema (Linux)
```

### Windows

```cmd
run_windows.bat
```

O manualmente:

```cmd
venv_win\Scripts\activate.bat
python main.py
```

### Comprobar conexión al backend (opcional)

```bash
python3 verificar_conexion_backend.py
```

---

## Configuración post-instalación

### Archivo `config.yaml`

Configuración central del navegador. Valores relevantes:

| Clave | Descripción | Valor por defecto |
|---|---|---|
| `backend.primary_url` | API de licencias y auth | `https://api.scrapelio.com` |
| `frontend.url` | Sitio web Scrapelio | `https://scrapelio.com` |
| `tor.enabled` | Activar Tor al arrancar | `false` |
| `tor.socks_port` | Puerto SOCKS5 | `9150` |
| `logging.level` | Nivel de log | `INFO` |
| `logging.file` | Archivo de log | `scrapelio_browser.log` |

### Variables de entorno (opcional)

Crea un archivo `.env` en la raíz del proyecto o exporta variables en el shell:

```bash
# Backend y red
export SCRAPELIO_BACKEND_URL="http://localhost:8000"
export SCRAPELIO_FRONTEND_URL="https://scrapelio.com"
export SCRAPELIO_NETWORK_MODE="network"   # o "offline"
export SCRAPELIO_LOG_LEVEL="DEBUG"

# Seguridad (solo desarrollo; no commitear)
export JWT_SECRET="tu-clave-secreta-aqui"
```

### Configurar la IA (panel de chat)

El chat IA se configura **desde la interfaz** del navegador (no requiere `.env`):

| Proveedor | Requisito |
|---|---|
| **Local** (LM Studio / Ollama) | Servidor OpenAI-compatible en `http://localhost:1234` — sin API key |
| **llmapi.ai** | API key en ajustes del panel |
| **Anthropic** | API key de Claude |
| **HuggingFace** | Token de Inference API |

Las claves se guardan en `QSettings("Scrapelio", "LLMClient")`, no en archivos de texto.

### Plugins premium

Los plugins de pago (SEO Analyzer, Advanced Scraping, Proxy, AI Live IDE) requieren licencia válida verificada contra el backend. El navegador base y los plugins gratuitos (Custom Themes, Split View) funcionan sin licencia.

---

## Compilar ejecutable (distribución)

### Linux (PyInstaller)

```bash
pip install pyinstaller pyinstaller-hooks-contrib
pyinstaller scrapelio-browser.spec --clean --noconfirm
# Resultado: dist/scrapelio-browser/
```

### Windows

```cmd
build_windows.bat
REM Resultado: dist\Scrapelio Browser\
```

> Distribuye **toda la carpeta** generada, no solo el `.exe`. PySide6 y Qt WebEngine necesitan las DLLs y recursos empaquetados.

---

## Solución de problemas

### `ModuleNotFoundError: No module named 'PySide6'`

PySide6 no está instalado en el entorno que usas para ejecutar el programa.

```bash
# Activar el venv
source venv/bin/activate          # Linux/macOS
venv_win\Scripts\activate.bat     # Windows

# Instalar PySide6 en ESE entorno
pip install --upgrade "PySide6>=6.5.0"

# Confirmar ubicación (debe ser dentro de venv/)
python3 -m pip show PySide6
python3 -c "from PySide6.QtWebEngineWidgets import QWebEngineView; print('OK')"
```

Causas habituales:
- Ejecutaste `pip install` **sin activar** el entorno virtual → PySide6 se instaló en otro Python.
- `pip install -r requirements.txt` **falló a medias** (p. ej. en `chromadb`) y nunca llegó a PySide6 → instálalo aparte primero.
- Instalaste **PyQt6** pensando que es equivalente → no lo es; necesitas **PySide6**.

### `ModuleNotFoundError: No module named 'PySide6.QtWebEngineWidgets'`

PySide6 está instalado pero **sin el componente WebEngine** (instalación incompleta o corrupta):

```bash
pip uninstall -y PySide6 PySide6-Essentials PySide6-Addons
pip install --no-cache-dir --force-reinstall "PySide6>=6.5.0"
python3 -c "from PySide6.QtWebEngineWidgets import QWebEngineView; print('OK')"
```

En Linux, si persiste, instala las bibliotecas del sistema (sección de dependencias del sistema).

### `Could not load the Qt platform plugin "xcb"`

Faltan bibliotecas del sistema:

```bash
sudo apt install libxcb-cursor0 libxcb-xinerama0 libxcb-xtest0
```

### `externally-managed-environment` (pip en Ubuntu 23.04+)

Usa entorno virtual (`python3 -m venv venv`) — **no instales PySide6 en el Python del sistema** salvo que sepas lo que haces:

```bash
python3 -m venv venv && source venv/bin/activate
pip install "PySide6>=6.5.0"
pip install -r requirements.txt
```

### El navegador arranca pero las páginas no cargan

- Revisa `scrapelio_browser.log` en la raíz del proyecto.
- Si Tor está activado sin daemon disponible, desactívalo en `config.yaml` (`tor.enabled: false`) o instala Tor.

### Error al importar `chromadb` o `sentence-transformers`

Son opcionales. Para instalarlos:

```bash
pip install sentence-transformers chromadb
# Linux: puede necesitar build-essential
sudo apt install build-essential
```

### Playwright no encuentra navegador

```bash
playwright install chromium
```

### Puerto en uso al arrancar

El navegador abre un socket local (puerto definido en `constants.py`) para comunicación entre procesos. Cierra instancias previas de Scrapelio Browser.

---

## Comandos de referencia rápida

```bash
# Verificar dependencias
python3 check_dependencies.py

# Arrancar
python3 main.py

# Ver errores recientes
tail -100 scrapelio_browser.log | grep -E "ERROR|Traceback"

# Ejecutar tests
pytest tests/ -v

# Verificar backend
python3 verificar_conexion_backend.py
```

---

## Estructura mínima necesaria

Para que el navegador funcione, la carpeta de instalación debe contener al menos:

```
scrapelio-browser/
├── main.py              ← punto de entrada
├── ui.py                ← ventana principal
├── config.yaml          ← configuración
├── requirements.txt
├── icons/               ← iconos SVG
├── plugins/             ← plugins del navegador
├── ui/                  ← motor de temas
├── easylist.txt         ← filtros de anuncios
├── easyprivacy.txt      ← filtros de trackers
└── *.db                 ← bases SQLite (se crean si no existen)
```

---

## Licencia

Consulta el archivo `LICENSE` para los términos de uso del software.
