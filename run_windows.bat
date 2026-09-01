@echo off
chcp 65001 >nul
echo ================================================
echo   Scrapelio Browser - Lanzador Portable Windows
echo ================================================
echo.

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.11 o 3.12 desde python.org
    echo         Marca "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

python --version

:: Crear entorno virtual si no existe
if not exist "venv_win\Scripts\activate.bat" (
    echo.
    echo [INFO] Creando entorno virtual...
    python -m venv venv_win
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
)

:: Activar entorno virtual
call venv_win\Scripts\activate.bat

:: Instalar/actualizar dependencias (solo la primera vez o si falta algo)
if not exist "venv_win\.deps_installed" (
    echo.
    echo [INFO] Instalando dependencias ^(primera vez, puede tardar 5-10 minutos^)...
    echo.

    pip install --upgrade pip

    :: Core - PySide6 WebEngine (lo mas importante)
    pip install PySide6>=6.5.0
    if errorlevel 1 ( echo [ERROR] Fallo instalando PySide6 & pause & exit /b 1 )

    :: Red y scraping
    pip install requests>=2.28.0
    pip install beautifulsoup4>=4.11.0
    pip install lxml>=4.9.0
    pip install aiohttp>=3.8.0
    pip install aiohttp-socks>=0.7.0

    :: Datos
    pip install pandas>=1.5.0
    pip install numpy>=1.24.0
    pip install openpyxl>=3.0.0
    pip install PyYAML>=6.0
    pip install Pillow>=9.0.0

    :: UI / Temas
    pip install qdarktheme>=2.0
    pip install qtawesome>=1.3

    :: Auth y seguridad
    pip install PyJWT>=2.8.0
    pip install cryptography>=41.0.0

    :: Sistema
    pip install psutil>=5.9.0
    pip install schedule>=1.2.0

    :: Tor
    pip install stem>=1.8.0
    pip install PySocks>=1.7.1

    :: IA (puede tardar mucho, comentar si no se necesita para la prueba)
    pip install sentence-transformers>=2.2.0
    pip install chromadb>=0.4.0

    :: Marcar como instalado
    echo 1 > venv_win\.deps_installed
    echo.
    echo [OK] Dependencias instaladas correctamente.
)

echo.
echo [INFO] Iniciando Scrapelio Browser...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] El navegador cerro con un error. Revisa el log arriba.
    pause
)
