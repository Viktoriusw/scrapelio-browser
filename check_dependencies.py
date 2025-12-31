#!/usr/bin/env python3
"""
Script para verificar que todas las dependencias están instaladas correctamente
"""

import sys
import importlib

def check_dependency(module_name, package_name=None):
    """Verifica si una dependencia está instalada"""
    try:
        if package_name:
            importlib.import_module(module_name)
            print(f"✓ {package_name} está instalado")
            return True
        else:
            importlib.import_module(module_name)
            print(f"✓ {module_name} está instalado")
            return True
    except ImportError as e:
        print(f"✗ {package_name or module_name} NO está instalado: {e}")
        return False

def main():
    print("Verificando dependencias de Scrapelio Browser...")
    print("=" * 50)
    
    dependencies = [
        # GUI Framework
        ("PySide6", "PySide6"),
        ("PyQt6", "PyQt6"),
        
        # Web scraping
        ("requests", "requests"),
        ("bs4", "beautifulsoup4"),
        ("lxml", "lxml"),
        ("selenium", "selenium"),
        ("playwright", "playwright"),
        ("aiohttp", "aiohttp"),
        ("readability", "readability"),
        
        # Data analysis
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("openpyxl", "openpyxl"),
        
        # Security
        ("jwt", "PyJWT"),
        ("cryptography", "cryptography"),
        
        # Testing
        ("pytest", "pytest"),
        # ("pytest_qt", "pytest-qt"),  # Opcional, puede no estar disponible
        
        # Scheduling
        ("schedule", "schedule"),
        
        # Icons and themes
        ("qtawesome", "qtawesome"),
    ]
    
    all_ok = True
    
    for module, package in dependencies:
        if not check_dependency(module, package):
            all_ok = False
    
    print("=" * 50)
    
    if all_ok:
        print("🎉 ¡Todas las dependencias están instaladas correctamente!")
        print("Puedes ejecutar el programa con: python3 main.py")
    else:
        print("❌ Algunas dependencias faltan. Ejecuta:")
        print("python3 -m pip install --break-system-packages -r requirements.txt")
    
    return all_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
