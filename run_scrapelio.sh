#!/bin/bash

echo "Iniciando Scrapelio Browser..."
echo "=============================="

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "Activando entorno virtual..."
    source venv/bin/activate
    echo "✅ Entorno virtual activado: $(which python3)"
else
    echo "⚠️  No se encontró entorno virtual. Usando Python del sistema."
fi

# Verificar dependencias de Python
echo "Verificando dependencias de Python..."
python3 check_dependencies.py
if [ $? -ne 0 ]; then
    echo "❌ Faltan dependencias de Python. Instalando..."
    if [ -d "venv" ]; then
        pip install -r requirements.txt
    else
        python3 -m pip install --break-system-packages -r requirements.txt
    fi
fi

# Verificar dependencias del sistema
echo "Verificando dependencias del sistema..."

# Verificar si libxcb-cursor0 está instalado
if ! dpkg -l | grep -q libxcb-cursor0; then
    echo "⚠️  Falta libxcb-cursor0. Ejecuta:"
    echo "   sudo apt install libxcb-cursor0"
    echo "   O ejecuta: ./install_dependencies.sh"
    echo ""
    echo "Continuando de todas formas..."
fi

# Intentar ejecutar el programa
echo "Ejecutando Scrapelio Browser..."
echo "Usando Python del sistema: $(which python3)"
python3 main.py

echo "Scrapelio Browser terminado."
