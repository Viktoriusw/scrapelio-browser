#!/usr/bin/env python3
"""
Script de prueba para verificar que la limpieza de datos funciona correctamente
"""

import sys
import os

# Añadir el directorio del plugin al path
plugin_dir = os.path.join(os.path.dirname(__file__), 'plugins', 'scraping')
sys.path.insert(0, plugin_dir)

from scraping_integration import ScrapingIntegration

def test_clean_text():
    """Probar la función de limpieza de texto"""
    print("=" * 80)
    print("TEST 1: Limpieza de texto con HTML")
    print("=" * 80)
    
    integration = ScrapingIntegration()
    
    # Casos de prueba con HTML
    test_cases = [
        {
            "name": "HTML simple",
            "input": "<p>Este es un <strong>texto</strong> con HTML</p>",
            "expected": "Este es un texto con HTML"
        },
        {
            "name": "HTML complejo",
            "input": "<div class='product'><h2>Título del Producto</h2><span class='price'>$19.99</span></div>",
            "expected": "Título del Producto $19.99"
        },
        {
            "name": "HTML con entidades",
            "input": "Precio: &euro;50 &amp; env&iacute;o gratis",
            "expected": "Precio: €50 & envío gratis"
        },
        {
            "name": "HTML con múltiples espacios",
            "input": "<p>   Texto   con    muchos     espacios   </p>",
            "expected": "Texto con muchos espacios"
        },
        {
            "name": "HTML anidado",
            "input": "<div><span><a href='#'>Link <em>con</em> énfasis</a></span></div>",
            "expected": "Link con énfasis"
        },
        {
            "name": "Texto con scripts",
            "input": "<p>Texto visible</p><script>alert('hack')</script>",
            "expected": "Texto visible"
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = integration._clean_text(test["input"])
        
        # Normalizar espacios para comparación
        result_normalized = ' '.join(result.split())
        expected_normalized = ' '.join(test["expected"].split())
        
        if result_normalized == expected_normalized:
            print(f"✅ PASS: {test['name']}")
            print(f"   Input:    {test['input'][:60]}...")
            print(f"   Output:   {result}")
            print(f"   Expected: {test['expected']}")
            passed += 1
        else:
            print(f"❌ FAIL: {test['name']}")
            print(f"   Input:    {test['input'][:60]}...")
            print(f"   Output:   '{result}'")
            print(f"   Expected: '{test['expected']}'")
            failed += 1
        print()
    
    print(f"\nResultados: {passed} pasados, {failed} fallidos de {len(test_cases)} tests")
    print("=" * 80)
    return failed == 0

def test_format_for_export():
    """Probar la función de formateo para exportación"""
    print("\n" + "=" * 80)
    print("TEST 2: Formateo para exportación")
    print("=" * 80)
    
    integration = ScrapingIntegration()
    
    test_cases = [
        {
            "name": "HTML en texto",
            "input": "<div>Producto: <span class='name'>Laptop</span></div>",
            "should_not_contain": ["<div>", "<span>", "class="]
        },
        {
            "name": "Comillas en texto",
            "input": 'Texto con "comillas" dobles',
            "should_contain": ['""']  # Las comillas deben estar escapadas para CSV
        },
        {
            "name": "Saltos de línea",
            "input": "Línea 1\nLínea 2\rLínea 3",
            "should_not_contain": ["\n", "\r"]
        },
        {
            "name": "Tabs",
            "input": "Columna1\tColumna2\tColumna3",
            "should_not_contain": ["\t"]
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = integration._format_for_export(test["input"])
        
        test_passed = True
        
        # Verificar que NO contenga ciertos caracteres
        if "should_not_contain" in test:
            for char in test["should_not_contain"]:
                if char in result:
                    print(f"❌ FAIL: {test['name']}")
                    print(f"   El resultado contiene '{char}' cuando no debería")
                    print(f"   Input:  {test['input'][:60]}...")
                    print(f"   Output: {result[:60]}...")
                    test_passed = False
                    break
        
        # Verificar que SÍ contenga ciertos caracteres
        if test_passed and "should_contain" in test:
            for char in test["should_contain"]:
                if char not in result:
                    print(f"❌ FAIL: {test['name']}")
                    print(f"   El resultado NO contiene '{char}' cuando debería")
                    print(f"   Input:  {test['input'][:60]}...")
                    print(f"   Output: {result[:60]}...")
                    test_passed = False
                    break
        
        if test_passed:
            print(f"✅ PASS: {test['name']}")
            print(f"   Input:  {test['input'][:60]}...")
            print(f"   Output: {result[:60]}...")
            passed += 1
        else:
            failed += 1
        print()
    
    print(f"\nResultados: {passed} pasados, {failed} fallidos de {len(test_cases)} tests")
    print("=" * 80)
    return failed == 0

def test_structured_data_extraction():
    """Probar la extracción de datos estructurados"""
    print("\n" + "=" * 80)
    print("TEST 3: Extracción de datos estructurados")
    print("=" * 80)
    
    integration = ScrapingIntegration()
    
    # HTML de prueba
    html_test = """
    <html>
        <body>
            <div class="product">
                <h2 class="title">Laptop Gaming <strong>Pro</strong></h2>
                <span class="price">$1,299.99</span>
                <p class="description">
                    La mejor <em>laptop</em> para gamers profesionales.
                    <span>Incluye:</span>
                    <ul>
                        <li>RTX 4090</li>
                        <li>32GB RAM</li>
                    </ul>
                </p>
                <a href="/buy" class="button">Comprar Ahora</a>
            </div>
        </body>
    </html>
    """
    
    # Actualizar contenido
    integration.update_content(html_test, "http://test.com")
    
    # Obtener elementos seleccionables
    elements = integration.get_selectable_elements()
    
    print(f"Elementos encontrados: {len(elements)}")
    print()
    
    # Verificar que no haya HTML en los textos
    html_found = False
    for i, element in enumerate(elements[:5], 1):  # Solo los primeros 5
        texto_limpio = element.get("texto_limpio", "")
        texto_original = element.get("texto_original", "")
        
        print(f"Elemento {i}: {element.get('type', 'Unknown')}")
        print(f"  Tag: {element.get('tag', 'unknown')}")
        print(f"  Texto limpio: {texto_limpio[:80]}...")
        
        # Verificar que no contenga etiquetas HTML
        if '<' in texto_limpio or '>' in texto_limpio:
            print(f"  ❌ CONTIENE HTML en texto_limpio!")
            html_found = True
        else:
            print(f"  ✅ Sin HTML en texto_limpio")
        
        if '<' in texto_original or '>' in texto_original:
            print(f"  ❌ CONTIENE HTML en texto_original!")
            html_found = True
        else:
            print(f"  ✅ Sin HTML en texto_original")
        
        print()
    
    if html_found:
        print("❌ FAIL: Se encontró HTML en los textos extraídos")
        return False
    else:
        print("✅ PASS: No se encontró HTML en los textos extraídos")
        return True

def test_export_data():
    """Probar la exportación de datos"""
    print("\n" + "=" * 80)
    print("TEST 4: Exportación de datos")
    print("=" * 80)
    
    integration = ScrapingIntegration()
    
    # HTML de prueba
    html_test = """
    <div class="products">
        <div class="product">
            <h3>Producto 1</h3>
            <span class="price">$99.99</span>
        </div>
        <div class="product">
            <h3>Producto 2</h3>
            <span class="price">$149.99</span>
        </div>
    </div>
    """
    
    integration.update_content(html_test, "http://test.com")
    
    # Seleccionar elementos
    elements = integration.get_selectable_elements()
    for element in elements[:4]:  # Seleccionar los primeros 4
        integration.add_selected_element(element)
    
    print(f"Elementos seleccionados: {len(integration.get_selected_elements())}")
    
    # Probar exportación a JSON
    result = integration.export_selected_data("json", "test_export")
    
    if "error" in result:
        print(f"❌ FAIL: Error en exportación: {result['error']}")
        return False
    
    print(f"✅ Exportación exitosa a {result.get('filename', 'unknown')}")
    print(f"   Elementos exportados: {result.get('elements_exported', 0)}")
    print(f"   Columnas exportadas: {result.get('columns_exported', 0)}")
    
    # Leer el archivo exportado y verificar que no contenga HTML
    try:
        import json
        with open(result['filename'], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        html_found = False
        for element in data.get('elementos', []):
            texto_limpio = element.get('texto_limpio', '')
            if '<' in texto_limpio or '>' in texto_limpio:
                print(f"❌ FAIL: HTML encontrado en datos exportados: {texto_limpio[:100]}")
                html_found = True
                break
        
        # Limpiar archivo de prueba
        import os
        os.remove(result['filename'])
        
        if html_found:
            return False
        else:
            print("✅ PASS: No se encontró HTML en los datos exportados")
            return True
            
    except Exception as e:
        print(f"❌ FAIL: Error verificando archivo exportado: {e}")
        return False

def main():
    """Ejecutar todos los tests"""
    print("\n" + "=" * 80)
    print("INICIANDO TESTS DE LIMPIEZA DE DATOS")
    print("=" * 80)
    
    results = []
    
    # Ejecutar tests
    results.append(("Limpieza de texto", test_clean_text()))
    results.append(("Formateo para exportación", test_format_for_export()))
    results.append(("Extracción de datos estructurados", test_structured_data_extraction()))
    results.append(("Exportación de datos", test_export_data()))
    
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
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) fallaron")
        return 1

if __name__ == "__main__":
    sys.exit(main())

