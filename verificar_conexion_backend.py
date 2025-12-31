#!/usr/bin/env python3
"""
Script para verificar la conexión con el backend de Scrapelio
Verifica que el servidor backend está accesible en la nueva IP
"""

import sys
import requests
from pathlib import Path

# Agregar el directorio actual al path para importar config_manager
sys.path.insert(0, str(Path(__file__).parent))

try:
    from config_manager import get_config
    USE_CONFIG_MANAGER = True
except ImportError:
    USE_CONFIG_MANAGER = False
    print("[WARNING] No se pudo importar config_manager, usando URLs hardcodeadas")

def print_header(title):
    """Imprimir encabezado visual"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def check_endpoint(name, url, timeout=10):
    """
    Verificar si un endpoint está accesible
    
    Args:
        name: Nombre del endpoint
        url: URL a verificar
        timeout: Timeout en segundos
        
    Returns:
        bool: True si está accesible, False si no
    """
    print(f"🔍 Verificando {name}...")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, timeout=timeout)
        
        if response.status_code == 200:
            print(f"   ✅ EXITOSO - Código: {response.status_code}")
            return True
        elif response.status_code == 404:
            # 404 es aceptable, significa que el servidor está corriendo
            print(f"   ✅ SERVIDOR ACTIVO (404 esperado para endpoint raíz) - Código: {response.status_code}")
            return True
        else:
            print(f"   ⚠️  RESPUESTA INESPERADA - Código: {response.status_code}")
            return True  # El servidor responde, aunque no sea 200
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ ERROR DE CONEXIÓN - No se pudo conectar al servidor")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ TIMEOUT - El servidor no respondió en {timeout} segundos")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return False

def check_backend_health(backend_url):
    """
    Verificar el health check del backend
    
    Args:
        backend_url: URL base del backend
        
    Returns:
        bool: True si está saludable, False si no
    """
    health_url = f"{backend_url}/health"
    print(f"🏥 Verificando health check del backend...")
    print(f"   URL: {health_url}")
    
    try:
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ BACKEND SALUDABLE")
            print(f"   📊 Respuesta: {data}")
            return True
        else:
            print(f"   ⚠️  Código: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ ERROR DE CONEXIÓN")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ TIMEOUT")
        return False
    except Exception as e:
        print(f"   ⚠️  Error: {str(e)} (el endpoint /health puede no existir)")
        return False

def main():
    """Verificar conexión con el backend"""
    print_header("🔌 VERIFICACIÓN DE CONEXIÓN CON EL BACKEND")
    
    # Obtener configuración
    if USE_CONFIG_MANAGER:
        config = get_config()
        backend_url = config.get_backend_url()
        frontend_url = config.get_frontend_url()
        registration_url = config.get_registration_url()
        login_url = config.get_login_url()
        # Dashboard URL no tiene getter, construir manualmente
        dashboard_url = f"{frontend_url}/app/dashboard.html"
    else:
        # URLs hardcodeadas (nueva IP)
        backend_url = "http://192.168.1.130:8000"
        frontend_url = "http://192.168.1.130:4321"
        registration_url = f"{frontend_url}/auth/registro.html"
        login_url = f"{frontend_url}/auth/login.html"
        dashboard_url = f"{frontend_url}/app/dashboard.html"
    
    print(f"📋 Configuración detectada:")
    print(f"   Backend API: {backend_url}")
    print(f"   Frontend Web: {frontend_url}")
    print()
    
    # Verificar endpoints
    results = []
    
    # 1. Backend API (raíz)
    results.append(("Backend API (raíz)", check_endpoint("Backend API", backend_url)))
    print()
    
    # 2. Backend Health Check
    results.append(("Backend Health", check_backend_health(backend_url)))
    print()
    
    # 3. Frontend Web
    results.append(("Frontend Web", check_endpoint("Frontend Web", frontend_url)))
    print()
    
    # 4. Página de registro
    results.append(("Página de Registro", check_endpoint("Registro", registration_url)))
    print()
    
    # 5. Página de login
    results.append(("Página de Login", check_endpoint("Login", login_url)))
    print()
    
    # 6. Dashboard
    results.append(("Dashboard", check_endpoint("Dashboard", dashboard_url)))
    print()
    
    # Resumen
    print_header("📊 RESUMEN DE VERIFICACIÓN")
    
    total = len(results)
    exitosos = sum(1 for _, result in results if result)
    fallidos = total - exitosos
    
    print(f"Total de verificaciones: {total}")
    print(f"✅ Exitosas: {exitosos}")
    print(f"❌ Fallidas: {fallidos}")
    print()
    
    # Detalles
    print("Detalles:")
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    print()
    
    # Conclusión
    if exitosos == total:
        print("🎉 ¡PERFECTO! Todos los servicios están accesibles")
        print()
        print("✅ El navegador puede conectarse al backend en la nueva IP: 192.168.1.130")
        print()
        return 0
    elif exitosos >= total // 2:
        print("⚠️  ADVERTENCIA: Algunos servicios no están accesibles")
        print()
        print(f"   {exitosos}/{total} servicios funcionando correctamente")
        print()
        if fallidos > 0:
            print("💡 Sugerencias:")
            print("   1. Verifica que el backend esté ejecutándose")
            print("   2. Verifica que el servidor web (nginx/apache) esté activo")
            print("   3. Verifica que no haya firewall bloqueando las conexiones")
            print()
        return 1
    else:
        print("❌ ERROR: La mayoría de servicios no están accesibles")
        print()
        print(f"   Solo {exitosos}/{total} servicios funcionando")
        print()
        print("💡 Sugerencias:")
        print("   1. Verifica que el servidor backend esté ejecutándose en 192.168.1.130:8000")
        print("   2. Verifica que el servidor web esté ejecutándose en 192.168.1.130:4321")
        print("   3. Verifica la conectividad de red:")
        print(f"      ping 192.168.1.130")
        print("   4. Verifica que los puertos 8000 y 4321 estén abiertos")
        print()
        return 2

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verificación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

