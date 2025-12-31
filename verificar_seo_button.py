#!/usr/bin/env python3
"""
Script de Verificación Rápida: Botón SEO Analyzer
Verifica que el plugin SEO esté correctamente integrado en ui.py
"""

import sys
import os

def verificar_archivos_plugin():
    """Verificar que existen todos los archivos del plugin"""
    print("=" * 60)
    print("1. Verificando archivos del plugin SEO Analyzer...")
    print("=" * 60)
    
    archivos_requeridos = [
        "plugins/seo_analyzer/__init__.py",
        "plugins/seo_analyzer/plugin.py",
        "plugins/seo_analyzer/core/tier_manager.py",
        "plugins/seo_analyzer/ui/main_panel.py",
    ]
    
    todos_ok = True
    for archivo in archivos_requeridos:
        existe = os.path.exists(archivo)
        status = "✅" if existe else "❌"
        print(f"{status} {archivo}")
        if not existe:
            todos_ok = False
    
    return todos_ok

def verificar_import_en_ui():
    """Verificar que ui.py importa el plugin"""
    print("\n" + "=" * 60)
    print("2. Verificando import en ui.py...")
    print("=" * 60)
    
    try:
        with open("ui.py", "r", encoding="utf-8") as f:
            contenido = f.read()
        
        # Buscar el import del plugin
        if "from plugins.seo_analyzer.plugin import SEOAnalyzerPlugin" in contenido:
            print("✅ Import del plugin SEO encontrado")
            
            if "SEO_ANALYZER_AVAILABLE = True" in contenido:
                print("✅ Variable SEO_ANALYZER_AVAILABLE definida")
            else:
                print("❌ Variable SEO_ANALYZER_AVAILABLE no encontrada")
                return False
            
            return True
        else:
            print("❌ Import del plugin SEO NO encontrado en ui.py")
            return False
            
    except FileNotFoundError:
        print("❌ Archivo ui.py no encontrado")
        return False

def verificar_inicializacion():
    """Verificar que el plugin se inicializa en ui.py"""
    print("\n" + "=" * 60)
    print("3. Verificando inicialización del plugin...")
    print("=" * 60)
    
    try:
        with open("ui.py", "r", encoding="utf-8") as f:
            contenido = f.read()
        
        checks = [
            ("self.seo_plugin = SEOAnalyzerPlugin()", "Instanciación del plugin"),
            ("self.seo_plugin.initialize(self)", "Inicialización con browser"),
            ("SEO Analyzer plugin initialized correctly", "Mensaje de éxito"),
        ]
        
        todos_ok = True
        for texto, descripcion in checks:
            if texto in contenido:
                print(f"✅ {descripcion}")
            else:
                print(f"❌ {descripcion} - NO encontrado")
                todos_ok = False
        
        return todos_ok
        
    except FileNotFoundError:
        print("❌ Archivo ui.py no encontrado")
        return False

def verificar_boton_sidebar():
    """Verificar que el botón se agrega al sidebar"""
    print("\n" + "=" * 60)
    print("4. Verificando botón en sidebar...")
    print("=" * 60)
    
    try:
        with open("ui.py", "r", encoding="utf-8") as f:
            contenido = f.read()
        
        checks = [
            ("self.seo_action = create_strip_action", "Creación de la acción"),
            ("'SEO Analyzer'", "Nombre del botón"),
            ("self.toggle_seo_panel", "Conexión al método toggle"),
            ("self.side_strip.addAction(self.seo_action)", "Agregar al sidebar"),
        ]
        
        todos_ok = True
        for texto, descripcion in checks:
            if texto in contenido:
                print(f"✅ {descripcion}")
            else:
                print(f"❌ {descripcion} - NO encontrado")
                todos_ok = False
        
        return todos_ok
        
    except FileNotFoundError:
        print("❌ Archivo ui.py no encontrado")
        return False

def verificar_metodo_toggle():
    """Verificar que existe el método toggle_seo_panel"""
    print("\n" + "=" * 60)
    print("5. Verificando método toggle_seo_panel()...")
    print("=" * 60)
    
    try:
        with open("ui.py", "r", encoding="utf-8") as f:
            contenido = f.read()
        
        if "def toggle_seo_panel(self):" in contenido:
            print("✅ Método toggle_seo_panel() encontrado")
            
            if "self.seo_plugin.toggle_panel()" in contenido:
                print("✅ Llamada a seo_plugin.toggle_panel()")
                return True
            else:
                print("❌ No llama a seo_plugin.toggle_panel()")
                return False
        else:
            print("❌ Método toggle_seo_panel() NO encontrado")
            return False
            
    except FileNotFoundError:
        print("❌ Archivo ui.py no encontrado")
        return False

def verificar_import_python():
    """Verificar que el plugin se puede importar en Python"""
    print("\n" + "=" * 60)
    print("6. Verificando import de Python...")
    print("=" * 60)
    
    try:
        sys.path.insert(0, os.getcwd())
        from plugins.seo_analyzer.plugin import SEOAnalyzerPlugin
        print("✅ Import exitoso: SEOAnalyzerPlugin")
        
        # Verificar que se puede instanciar
        plugin = SEOAnalyzerPlugin()
        print("✅ Instanciación exitosa")
        
        # Verificar metadata
        metadata = plugin.get_metadata()
        print(f"✅ Metadata: {metadata.name} v{metadata.version}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error de import: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Ejecutar todas las verificaciones"""
    print("\n🔍 VERIFICACIÓN DEL BOTÓN SEO ANALYZER EN LA UI")
    print("=" * 60)
    
    resultados = []
    
    # Ejecutar verificaciones
    resultados.append(("Archivos del plugin", verificar_archivos_plugin()))
    resultados.append(("Import en ui.py", verificar_import_en_ui()))
    resultados.append(("Inicialización", verificar_inicializacion()))
    resultados.append(("Botón en sidebar", verificar_boton_sidebar()))
    resultados.append(("Método toggle", verificar_metodo_toggle()))
    resultados.append(("Import Python", verificar_import_python()))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE VERIFICACIONES")
    print("=" * 60)
    
    total = len(resultados)
    exitosos = sum(1 for _, ok in resultados if ok)
    
    for nombre, ok in resultados:
        status = "✅ PASÓ" if ok else "❌ FALLÓ"
        print(f"{status} - {nombre}")
    
    print("\n" + "=" * 60)
    print(f"RESULTADO: {exitosos}/{total} verificaciones exitosas")
    
    if exitosos == total:
        print("\n🎉 ¡PERFECTO! El botón SEO Analyzer está correctamente integrado.")
        print("\nPróximos pasos:")
        print("1. Iniciar el navegador: python3 main.py")
        print("2. Buscar el botón ⚙️ 'SEO Analyzer' en el panel lateral")
        print("3. Hacer clic para abrir el panel")
        print("\nUbicación del botón: Entre 'Chat IA' y 'Plugins'")
    else:
        print("\n⚠️ Hay algunos problemas. Revisa los errores arriba.")
        print("\nPara más ayuda, lee: BOTON_SEO_IMPLEMENTADO.md")
    
    print("=" * 60)
    
    return exitosos == total

if __name__ == "__main__":
    try:
        exito = main()
        sys.exit(0 if exito else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Verificación interrumpida")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

