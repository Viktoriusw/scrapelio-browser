# Crear Icono para SEO Analyzer Plugin

## Especificaciones del Icono

Para que el plugin SEO Analyzer tenga su propio icono distintivo en el panel lateral, necesitas crear el siguiente archivo:

**Ubicación**: `icons/seo.png`

### Requisitos:
- **Formato**: PNG con transparencia
- **Tamaño**: 18x18 píxeles (o múltiplos: 36x36, 54x54)
- **Estilo**: Minimalista, monocromático o con colores corporativos
- **Fondo**: Transparente

### Sugerencias de Diseño:

El icono debería representar SEO/optimización. Algunas ideas:
- 🔍 Lupa con gráfico ascendente
- 📊 Gráfico de barras con una estrella
- 🎯 Diana con flecha en el centro
- 📈 Gráfico de crecimiento
- 🔎 Lupa con símbolo de verificación
- Letras "SEO" estilizadas con efecto de brillo/optimización

### Herramientas Recomendadas:
- **Inkscape** (gratuito) - Para diseño vectorial
- **GIMP** (gratuito) - Para edición de píxeles
- **Figma** (gratuito online) - Para diseño UI
- **Canva** (gratuito) - Plantillas prediseñadas

### Pasos para Crear el Icono:

1. **Diseña el icono** en un tamaño grande (256x256px mínimo)
2. **Exporta** en varios tamaños: 18x18, 36x36, 72x72
3. **Guarda** el archivo de 18x18 como `icons/seo.png`
4. **Verifica** que el fondo sea transparente
5. **Reinicia el navegador** para ver el nuevo icono

### Modificación del Plugin:

Una vez creado el icono, debes actualizar esta línea en `plugins/seo_analyzer/plugin.py`:

```python
# Línea actual (temporal):
icon_path = "icons/settings.png"  # TODO: Create icons/seo.png

# Cambiar a:
icon_path = "icons/seo.png"
```

### Iconos de Referencia:

Puedes inspirarte en los iconos existentes del navegador:
- `icons/settings.png` - Ajustes/configuración
- `icons/scrap.png` - Scraping/extracción
- `icons/wrench.png` - Herramientas
- `icons/bookmark.png` - Marcadores

### Paleta de Colores del Navegador:

Para mantener consistencia visual:
- **Tema Claro**: Íconos oscuros (#333333 o #555555)
- **Tema Oscuro**: Íconos claros (#CCCCCC o #FFFFFF)
- **Acento**: Azul (#007bff) o Verde (#28a745) para SEO

---

**Nota**: Actualmente el plugin usa temporalmente el icono de `settings.png` hasta que crees el icono personalizado `seo.png`.

