#!/bin/bash

echo "Instalando dependencias del sistema para Scrapelio Browser..."

# Instalar dependencias de Qt y X11
echo "Instalando dependencias de Qt y X11..."
sudo apt update
sudo apt install -y libxcb-cursor0 libxcb-cursor-dev

# Instalar dependencias adicionales para Qt
sudo apt install -y libxcb-xinerama0 libxcb-xinerama-dev

# Instalar dependencias para multimedia
sudo apt install -y libxcb-xtest0 libxcb-xtest-dev

# Instalar dependencias para OpenGL
sudo apt install -y libgl1-mesa-dev libglu1-mesa-dev

# Instalar dependencias para fuentes
sudo apt install -y libfontconfig1-dev

# Instalar dependencias para SSL
sudo apt install -y libssl-dev

echo "Dependencias del sistema instaladas correctamente."
echo "Ahora puedes ejecutar el programa con: python3 main.py"
