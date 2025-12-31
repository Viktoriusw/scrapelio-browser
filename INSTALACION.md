# Guía de Instalación - Scrapelio Browser

## Dependencias Instaladas ✅

Todas las dependencias de Python han sido instaladas correctamente:

### GUI Framework
- ✅ PySide6 6.10.0
- ✅ PyQt6 6.10.0

### Web Scraping
- ✅ requests 2.31.0
- ✅ beautifulsoup4 4.14.2
- ✅ lxml 6.0.2
- ✅ selenium 4.37.0
- ✅ playwright 1.55.0
- ✅ aiohttp 3.13.1
- ✅ readability 0.3.2

### Data Analysis
- ✅ pandas 2.3.3
- ✅ numpy 2.3.4
- ✅ openpyxl 3.1.5

### Security
- ✅ PyJWT 2.7.0
- ✅ cryptography 41.0.7

### Testing
- ✅ pytest 8.4.2

### Scheduling
- ✅ schedule 1.2.2

### Icons and Themes
- ✅ qtawesome 1.4.0

## Cómo Ejecutar el Programa

### ✅ Opción 1: Script Automático (Recomendado)
```bash
./run_scrapelio.sh
```

### ✅ Opción 2: Ejecución Directa
```bash
python3 main.py
```

### ✅ Opción 3: Verificar Dependencias Primero
```bash
python3 check_dependencies.py
python3 main.py
```

### 🔧 Configuración del IDE
Si tu IDE no encuentra PySide6, configura el intérprete:
```bash
python3 setup_ide.py
```
Luego usa el intérprete: `/usr/bin/python3`

## Dependencias del Sistema

Si encuentras errores relacionados con Qt o X11, ejecuta:

```bash
./install_dependencies.sh
```

O manualmente:
```bash
sudo apt install libxcb-cursor0 libxcb-xinerama0 libxcb-xtest0
```

## Solución de Problemas

### Error: "Could not load the Qt platform plugin"
```bash
sudo apt install libxcb-cursor0 libxcb-xinerama0
```

### Error: "externally-managed-environment"
Ya está solucionado usando `--break-system-packages`

### Error: "No module named 'X'"
```bash
python3 -m pip install --break-system-packages X
```

## Navegadores de Playwright

Los navegadores de Playwright ya están instalados:
- ✅ Chromium 140.0.7339.16
- ✅ Firefox 141.0
- ✅ Webkit 26.0

## Archivos de Configuración

- `requirements.txt` - Dependencias de Python
- `check_dependencies.py` - Verificador de dependencias
- `run_scrapelio.sh` - Script de inicio
- `install_dependencies.sh` - Instalador de dependencias del sistema

## Notas Importantes

1. **qdarktheme** no está disponible para Python 3.12, pero el programa puede funcionar sin él
2. **pytest-qt** puede no estar disponible, pero no es crítico para el funcionamiento
3. Todas las dependencias principales están instaladas y funcionando

¡El programa está listo para usar! 🚀
