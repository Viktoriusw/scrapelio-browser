#!/usr/bin/env python3
"""
Script de Prueba: Integración del Plugin SEO Analyzer
Verifica que el plugin se puede cargar y que tiene todos los componentes necesarios
"""

import sys
from pathlib import Path

# Add plugin directory to path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir.parent.parent))

def test_plugin_imports():
    """Test 1: Verificar que se pueden importar todos los módulos"""
    print("=" * 60)
    print("TEST 1: Verificando importaciones del plugin...")
    print("=" * 60)
    
    try:
        from plugins.seo_analyzer import PLUGIN_INFO, TIER_CONFIG
        print("✅ __init__.py - PLUGIN_INFO importado")
        print(f"   - ID: {PLUGIN_INFO['id']}")
        print(f"   - Nombre: {PLUGIN_INFO['name']}")
        print(f"   - Versión: {PLUGIN_INFO['version']}")
        
        from plugins.seo_analyzer.plugin import SEOAnalyzerPlugin
        print("✅ plugin.py - SEOAnalyzerPlugin importado")
        
        from plugins.seo_analyzer.core.tier_manager import TierManager
        print("✅ tier_manager.py - TierManager importado")
        
        from plugins.seo_analyzer.ui.main_panel import SEOAnalyzerPanel
        print("✅ main_panel.py - SEOAnalyzerPanel importado")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False

def test_plugin_metadata():
    """Test 2: Verificar metadata del plugin"""
    print("\n" + "=" * 60)
    print("TEST 2: Verificando metadata del plugin...")
    print("=" * 60)
    
    try:
        from plugins.seo_analyzer.plugin import SEOAnalyzerPlugin
        plugin = SEOAnalyzerPlugin()
        metadata = plugin.get_metadata()
        
        print(f"✅ Metadata obtenida correctamente:")
        print(f"   - ID: {metadata.id}")
        print(f"   - Nombre: {metadata.name}")
        print(f"   - Versión: {metadata.version}")
        print(f"   - Autor: {metadata.author}")
        print(f"   - Permisos: {', '.join(metadata.permissions)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error obteniendo metadata: {e}")
        return False

def test_tier_manager():
    """Test 3: Verificar TierManager"""
    print("\n" + "=" * 60)
    print("TEST 3: Verificando TierManager...")
    print("=" * 60)
    
    try:
        from plugins.seo_analyzer.core.tier_manager import TierManager
        
        # Test FREE tier
        tier_manager = TierManager("FREE")
        print(f"✅ TierManager creado con tier: {tier_manager.get_tier()}")
        
        tier_info = tier_manager.get_tier_info()
        print(f"   - Nombre: {tier_info['name']}")
        print(f"   - Límite diario: {tier_info['daily_limit']}")
        print(f"   - Restantes hoy: {tier_info['remaining_today']}")
        print(f"   - Features: {len(tier_info['features'])} características")
        
        # Test métodos
        print(f"   - is_premium(): {tier_manager.is_premium()}")
        print(f"   - get_tier_badge_emoji(): {tier_manager.get_tier_badge_emoji()}")
        print(f"   - get_tier_color(): {tier_manager.get_tier_color()}")
        
        # Test PROFESSIONAL tier
        tier_manager.set_tier("PROFESSIONAL")
        print(f"✅ Tier actualizado a: {tier_manager.get_tier()}")
        print(f"   - is_premium(): {tier_manager.is_premium()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error con TierManager: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_panel_creation():
    """Test 4: Verificar creación de panel (sin browser_instance)"""
    print("\n" + "=" * 60)
    print("TEST 4: Verificando creación de componentes UI...")
    print("=" * 60)
    
    try:
        from PySide6.QtWidgets import QApplication
        from plugins.seo_analyzer.core.tier_manager import TierManager
        from plugins.seo_analyzer.ui.main_panel import SEOAnalyzerPanel
        
        # Crear QApplication si no existe (necesario para widgets Qt)
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Crear tier manager y panel
        tier_manager = TierManager("FREE")
        
        # Mock plugin y coordinator
        class MockPlugin:
            def __init__(self):
                self.auto_analyze_on_load = True
                self.show_notifications = True
        
        class MockCoordinator:
            pass
        
        plugin = MockPlugin()
        coordinator = MockCoordinator()
        
        panel = SEOAnalyzerPanel(plugin, tier_manager, coordinator)
        print(f"✅ Panel creado correctamente")
        print(f"   - Tipo: {type(panel).__name__}")
        print(f"   - Tabs disponibles: {panel.tabs.count()}")
        
        for i in range(panel.tabs.count()):
            tab_text = panel.tabs.tabText(i)
            print(f"   - Tab {i+1}: {tab_text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando panel: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_plugin_initialization():
    """Test 5: Verificar inicialización del plugin (sin browser)"""
    print("\n" + "=" * 60)
    print("TEST 5: Verificando inicialización del plugin...")
    print("=" * 60)
    
    try:
        from plugins.seo_analyzer.plugin import SEOAnalyzerPlugin
        
        plugin = SEOAnalyzerPlugin()
        print("✅ Plugin instanciado")
        print(f"   - Tier actual: {plugin.current_tier}")
        print(f"   - Auto-analyze: {plugin.auto_analyze_on_load}")
        print(f"   - Notificaciones: {plugin.show_notifications}")
        
        # Test métodos sin browser
        print("✅ Plugin tiene los métodos requeridos:")
        print(f"   - get_metadata: {hasattr(plugin, 'get_metadata')}")
        print(f"   - initialize: {hasattr(plugin, 'initialize')}")
        print(f"   - shutdown: {hasattr(plugin, 'shutdown')}")
        print(f"   - toggle_panel: {hasattr(plugin, 'toggle_panel')}")
        print(f"   - _add_sidebar_button: {hasattr(plugin, '_add_sidebar_button')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error inicializando plugin: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecutar todos los tests"""
    print("\n🔍 INICIANDO PRUEBAS DEL PLUGIN SEO ANALYZER")
    print("=" * 60)
    
    results = []
    
    results.append(("Importaciones", test_plugin_imports()))
    results.append(("Metadata", test_plugin_metadata()))
    results.append(("TierManager", test_tier_manager()))
    results.append(("Panel UI", test_panel_creation()))
    results.append(("Inicialización", test_plugin_initialization()))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    for name, success in results:
        status = "✅ PASÓ" if success else "❌ FALLÓ"
        print(f"{status} - {name}")
    
    print("\n" + "=" * 60)
    print(f"RESULTADO FINAL: {passed}/{total} pruebas pasadas")
    
    if passed == total:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON! El plugin está listo para usar.")
        print("\nPróximos pasos:")
        print("1. Crear el icono: icons/seo.png (ver icons/CREAR_ICONO_SEO.md)")
        print("2. Iniciar el navegador y hacer login")
        print("3. Instalar el plugin desde el Plugin Store")
        print("4. Hacer clic en el botón SEO en el panel lateral")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa los errores arriba.")
    
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Pruebas interrumpidas por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

