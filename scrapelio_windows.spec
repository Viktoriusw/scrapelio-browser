# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para Scrapelio Browser - Windows
# Requiere: pip install pyinstaller pyinstaller-hooks-contrib
#
# IMPORTANTE: Usar ONE-DIR (no one-file) porque QtWebEngineProcess.exe
# debe existir como ejecutable independiente junto al .exe principal.
#
# Ejecutar: pyinstaller scrapelio_windows.spec

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

# ── Recopilar archivos de PySide6 WebEngine (crítico) ──────────────────────
pyside6_datas = collect_data_files('PySide6')
pyside6_datas += collect_data_files('PySide6.QtWebEngine')

# Binarios de PySide6 (DLLs, QtWebEngineProcess.exe, etc.)
pyside6_binaries = collect_dynamic_libs('PySide6')

# Hidden imports de PySide6
pyside6_hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebChannel',
    'PySide6.QtNetwork',
    'PySide6.QtPrintSupport',
    'PySide6.QtOpenGL',
    'PySide6.QtOpenGLWidgets',
    'PySide6.QtPositioning',
    'PySide6.QtQuick',
    'PySide6.QtWebEngineQuick',
    'PySide6.QtDBus',
    'PySide6.QtSvg',
    'PySide6.QtSvgWidgets',
    'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets',
]

# ── Archivos de datos del proyecto ─────────────────────────────────────────
project_datas = [
    ('icons', 'icons'),
    ('plugins', 'plugins'),
    ('ui', 'ui'),
    ('easylist.txt', '.'),
    ('easyprivacy.txt', '.'),
    ('custom_filters.txt', '.'),
    ('dark_theme.json', '.'),
    ('light_theme.json', '.'),
    ('config.yaml', '.'),
    ('unified_plugin_config.json', '.'),
    ('tab_groups.json', '.'),
    ('logo.png', '.'),
    ('logoscrapelio.png', '.'),
]

# Agregar .db si existen (bases de datos vacías para distribución)
for db in ['bookmarks.db', 'passwords.db', 'downloads_history.db']:
    if os.path.exists(db):
        project_datas.append((db, '.'))

# ── Hidden imports del proyecto ─────────────────────────────────────────────
app_hiddenimports = [
    # Stdlib usados por reflexión
    'importlib.util',
    'importlib.metadata',
    'importlib.resources',
    'email.mime.text',
    'email.mime.multipart',
    'xml.etree.ElementTree',
    'urllib.parse',
    'urllib.request',
    'sqlite3',
    'json',
    'csv',
    'io',
    'base64',
    'hashlib',
    'hmac',
    'secrets',
    'threading',
    'queue',
    'concurrent.futures',
    'asyncio',
    'dataclasses',
    'typing',
    'pathlib',
    're',
    'copy',
    'traceback',
    'weakref',
    # Third-party
    'requests',
    'requests.adapters',
    'requests.auth',
    'urllib3',
    'certifi',
    'charset_normalizer',
    'idna',
    'bs4',
    'bs4.builder',
    'lxml',
    'lxml.etree',
    'lxml.html',
    'aiohttp',
    'aiohttp.connector',
    'aiohttp_socks',
    'pandas',
    'pandas.core.frame',
    'numpy',
    'numpy.core',
    'openpyxl',
    'openpyxl.styles',
    'yaml',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'qdarktheme',
    'qtawesome',
    'jwt',
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.backends',
    'psutil',
    'schedule',
    'stem',
    'stem.control',
    'socks',
    # IA (opcional — comentar si no se usa)
    'sentence_transformers',
    'chromadb',
    'chromadb.api',
    'chromadb.config',
    # PDF export (plugin SEO)
    'reportlab',
    'reportlab.lib',
    'reportlab.platypus',
    # Monaco editor (plugin ai_live_ide) — solo archivos estáticos, no imports adicionales
]

# ── Módulos a excluir (reducen tamaño) ────────────────────────────────────
excludes = [
    'PyQt6',       # No usar PyQt6 — solo PySide6
    'PyQt5',
    'tkinter',
    'wx',
    'matplotlib',  # No usado en el navegador
    'scipy',
    'sklearn',
    'tensorflow',
    'keras',
    'test',
    'unittest',
    'pydoc',
    'doctest',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=pyside6_binaries,
    datas=pyside6_datas + project_datas,
    hiddenimports=pyside6_hiddenimports + app_hiddenimports,
    hookspath=['hooks'],          # carpeta con hooks personalizados (ver abajo)
    hooksconfig={
        'PySide6': {
            'include_qml_files': False,
        },
    },
    runtime_hooks=['runtime_hook_windows.py'],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,        # ONE-DIR mode (obligatorio para WebEngine)
    name='Scrapelio Browser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                    # UPX puede romper WebEngine DLLs en Windows
    console=False,                # Sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icons\\scrapelio.ico',  # Cambia si tienes un .ico; si no, quita esta línea
    version='version_info.txt',   # Opcional: metadata del exe
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Scrapelio Browser',
)
