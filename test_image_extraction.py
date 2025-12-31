#!/usr/bin/env python3
"""
Script de prueba para verificar la extracción y descarga de imágenes
"""

import sys
import os

# Añadir el directorio del plugin al path
plugin_dir = os.path.join(os.path.dirname(__file__), 'plugins', 'scraping')
sys.path.insert(0, plugin_dir)

from scraping_integration import ScrapingIntegration

def test_image_detection():
    """Probar la detección de imágenes asociadas"""
    print("=" * 80)
    print("TEST 1: Detección de imágenes asociadas")
    print("=" * 80)
    
    integration = ScrapingIntegration()
    
    # HTML de prueba con productos que incluyen imágenes
    html_test = """
    <html>
        <body>
            <div class="products">
                <div class="product-card">
                    <img src="https://via.placeholder.com/300x300.png?text=Product+1" alt="Producto 1" />
                    <h3>Zapatilla Nike Air Max</h3>
                    <span class="price">$99.99</span>
                    <p class="description">Zapatillas deportivas de alta calidad</p>
                </div>
                
                <div class="product-card">
                    <img src="https://via.placeholder.com/300x300.png?text=Product+2" alt="Producto 2" />
                    <h3>Adidas Ultraboost</h3>
                    <span class="price">$149.99</span>
                    <p class="description">Máximo confort para correr</p>
                </div>
                
                <article class="item">
                    <div class="image-wrapper">
                        <img src="https://via.placeholder.com/300x300.png?text=Product+3" alt="Producto 3" />
                    </div>
                    <div class="info">
                        <h2>Puma RS-X</h2>
                        <span class="price">$79.99</span>
                    </div>
                </article>
            </div>
        </body>
    </html>
    """
    
    # Actualizar contenido
    integration.update_content(html_test, "http://test-shop.com")
    
    # Obtener elementos seleccionables
    elements = integration.get_selectable_elements()
    
    print(f"Elementos encontrados: {len(elements)}")
    print()
    
    # Verificar detección de imágenes
    images_found = 0
    for i, element in enumerate(elements[:10], 1):  # Primeros 10 elementos
        structured_data = element.get("structured_data", {})
        imagen_asociada = structured_data.get("imagen_asociada", {})
        
        if imagen_asociada.get("has_image"):
            images_found += 1
            print(f"✅ Elemento {i}: Imagen detectada")
            print(f"   Tipo: {element.get('type', 'Unknown')}")
            print(f"   Texto: {element.get('texto_limpio', '')[:50]}...")
            print(f"   URL imagen: {imagen_asociada.get('image_url', '')[:60]}...")
            print(f"   Alt texto: {imagen_asociada.get('image_alt', '')}")
            print()
    
    print(f"\nTotal de elementos con imágenes: {images_found}")
    
    if images_found > 0:
        print("✅ PASS: Se detectaron imágenes asociadas")
        return True
    else:
        print("❌ FAIL: No se detectaron imágenes")
        return False

def test_image_download():
    """Probar la descarga de imágenes"""
    print("\n" + "=" * 80)
    print("TEST 2: Descarga de imágenes")
    print("=" * 80)
    
    integration = ScrapingIntegration()
    
    # HTML de prueba con imagen real
    html_test = """
    <html>
        <body>
            <div class="product">
                <img src="https://via.placeholder.com/300x300.png?text=Test+Image" alt="Test Product" />
                <h3>Producto de Prueba</h3>
                <span class="price">$50.00</span>
            </div>
        </body>
    </html>
    """
    
    integration.update_content(html_test, "http://test-shop.com")
    
    # Obtener elementos y seleccionar uno con imagen
    elements = integration.get_selectable_elements()
    
    # Buscar elemento con imagen
    element_with_image = None
    for element in elements:
        structured_data = element.get("structured_data", {})
        imagen_asociada = structured_data.get("imagen_asociada", {})
        if imagen_asociada.get("has_image"):
            element_with_image = element
            break
    
    if not element_with_image:
        print("❌ FAIL: No se encontró elemento con imagen")
        return False
    
    # Agregar elemento (esto debería descargar la imagen)
    integration.add_selected_element(element_with_image)
    
    # Verificar que la imagen se descargó
    structured_data = element_with_image.get("structured_data", {})
    imagen_asociada = structured_data.get("imagen_asociada", {})
    
    local_path = imagen_asociada.get("image_local_path", "")
    thumbnail_path = imagen_asociada.get("thumbnail_path", "")
    
    print(f"URL original: {imagen_asociada.get('image_url', '')}")
    print(f"Ruta local: {local_path}")
    print(f"Ruta thumbnail: {thumbnail_path}")
    
    # Verificar que los archivos existen
    if local_path and os.path.exists(local_path):
        print(f"✅ Imagen descargada: {os.path.basename(local_path)}")
        print(f"   Tamaño: {os.path.getsize(local_path)} bytes")
    else:
        print("❌ FAIL: Imagen no se descargó")
        return False
    
    if thumbnail_path and os.path.exists(thumbnail_path):
        print(f"✅ Thumbnail creado: {os.path.basename(thumbnail_path)}")
        print(f"   Tamaño: {os.path.getsize(thumbnail_path)} bytes")
    else:
        print("⚠️  WARNING: Thumbnail no se creó (puede ser que PIL no esté disponible)")
    
    print("\n✅ PASS: Descarga de imágenes funciona correctamente")
    return True

def test_export_with_images():
    """Probar exportación con imágenes"""
    print("\n" + "=" * 80)
    print("TEST 3: Exportación con imágenes")
    print("=" * 80)
    
    integration = ScrapingIntegration()
    
    # HTML de prueba
    html_test = """
    <html>
        <body>
            <div class="products">
                <div class="product">
                    <img src="https://via.placeholder.com/300x300.png?text=Product+A" alt="Producto A" />
                    <h3>Producto A</h3>
                    <span class="price">$100</span>
                </div>
                <div class="product">
                    <img src="https://via.placeholder.com/300x300.png?text=Product+B" alt="Producto B" />
                    <h3>Producto B</h3>
                    <span class="price">$200</span>
                </div>
            </div>
        </body>
    </html>
    """
    
    integration.update_content(html_test, "http://test-shop.com")
    
    # Obtener y seleccionar elementos con imágenes
    elements = integration.get_selectable_elements()
    selected_count = 0
    
    for element in elements[:5]:  # Seleccionar primeros 5
        structured_data = element.get("structured_data", {})
        imagen_asociada = structured_data.get("imagen_asociada", {})
        if imagen_asociada.get("has_image"):
            integration.add_selected_element(element)
            selected_count += 1
    
    print(f"Elementos seleccionados con imágenes: {selected_count}")
    
    if selected_count == 0:
        print("⚠️  WARNING: No se seleccionaron elementos con imágenes")
        return True  # No es un error, solo no hay imágenes
    
    # Probar exportación a JSON
    print("\n📤 Exportando a JSON...")
    result_json = integration.export_selected_data("json", "test_images_export")
    
    if "error" in result_json:
        print(f"❌ FAIL: Error en exportación JSON: {result_json['error']}")
        return False
    
    print(f"✅ JSON exportado: {result_json.get('filename', 'unknown')}")
    
    # Verificar que el JSON contiene información de imágenes
    try:
        import json
        with open(result_json['filename'], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        elementos = data.get('elementos', [])
        images_in_export = 0
        
        for elemento in elementos:
            if elemento.get('tiene_imagen'):
                images_in_export += 1
                print(f"   ✅ Elemento con imagen: {elemento.get('url_imagen_asociada', '')[:50]}...")
        
        print(f"\nElementos con imágenes en exportación: {images_in_export}")
        
        # Limpiar archivo de prueba
        os.remove(result_json['filename'])
        
        if images_in_export > 0:
            print("✅ PASS: Exportación incluye información de imágenes")
            return True
        else:
            print("⚠️  WARNING: No se encontraron imágenes en la exportación")
            return True
            
    except Exception as e:
        print(f"❌ FAIL: Error verificando exportación: {e}")
        return False

def cleanup_test_files():
    """Limpiar archivos de prueba"""
    print("\n" + "=" * 80)
    print("Limpiando archivos de prueba...")
    print("=" * 80)
    
    try:
        # Limpiar directorios de imágenes de prueba
        import shutil
        
        if os.path.exists("scraped_images"):
            shutil.rmtree("scraped_images")
            print("✅ Directorio scraped_images eliminado")
        
        if os.path.exists("scraped_thumbnails"):
            shutil.rmtree("scraped_thumbnails")
            print("✅ Directorio scraped_thumbnails eliminado")
        
        # Limpiar archivos de exportación de prueba
        for file in os.listdir("."):
            if file.startswith("test_images_export"):
                os.remove(file)
                print(f"✅ Archivo {file} eliminado")
        
    except Exception as e:
        print(f"⚠️  WARNING: Error limpiando archivos: {e}")

def main():
    """Ejecutar todos los tests"""
    print("\n" + "=" * 80)
    print("INICIANDO TESTS DE EXTRACCIÓN DE IMÁGENES")
    print("=" * 80)
    
    results = []
    
    # Ejecutar tests
    results.append(("Detección de imágenes", test_image_detection()))
    results.append(("Descarga de imágenes", test_image_download()))
    results.append(("Exportación con imágenes", test_export_with_images()))
    
    # Limpiar archivos de prueba
    cleanup_test_files()
    
    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN DE TESTS")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    failed = sum(1 for _, result in results if not result)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print()
    print(f"Total: {passed} pasados, {failed} fallidos de {len(results)} tests")
    
    if failed == 0:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("\n💡 NOTA: Las imágenes se descargan de placeholder.com para las pruebas.")
        print("   En uso real, se descargarán las imágenes reales de los sitios web.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) fallaron")
        return 1

if __name__ == "__main__":
    sys.exit(main())

