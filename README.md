<p align="center">
  <img src="logoscrapelio.jpg" alt="Scrapelio Browser" width="220" />
</p>

## Scrapelio Browser

Navegador web ligero con sistema de plugins, IA integrada y foco en privacidad.

### Instalación

**Linux / macOS**
cd /ruta/a/scrapelio-browser

### 1. Dependencias del sistema
sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
  libxcb-cursor0 libxcb-xinerama0 libxcb-xtest0 \
  libgl1-mesa-glx libfontconfig1 libssl-dev
  
### 2. Entorno virtual
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

### 3. Dependencias Python
pip install -r requirements.txt

### 4. Verificar
python3 check_dependencies.py
python3 -c "from PySide6.QtWebEngineWidgets import QWebEngineView; print('OK')"

### 5. Ejecutar
python3 main.py



### Características principales

- **Plugins de la comunidad**: sistema de plugins extensible, con plugins oficiales y desarrollados por la comunidad.
- **Chat IA integrado**: panel de chat con IA y asistencia contextual dentro del navegador.
- **IA en la navegación**: extracción de contexto de páginas, ayuda para búsquedas y tareas directamente sobre los sitios que visitas.
- **Privacidad y seguridad**: gestor de contraseñas, controles avanzados de privacidad y utilidades de seguridad integradas.
- **Navegador muy ligero**: interfaz en PySide6 optimizada, consumo reducido de recursos y tiempos de arranque rápidos.


### Licencia

Consulta el archivo `LICENSE` para los términos completos de uso.
