# Custom Themes Plugin v2.0.0

## 🎨 Descripción

Plugin avanzado de gestión de temas para Scrapelio Browser. Permite personalizar completamente la apariencia del navegador mediante un selector visual intuitivo y un editor gráfico de temas.

**Versión 2.0.0** - Refactorización completa con integración al ThemeEngine consolidado del navegador.

---

## ✨ Características

### Selector de Temas
- **Interfaz visual** con tarjetas de temas
- **Previsualizaciones de colores** en cada tema
- **Aplicación instantánea** de temas
- Soporte para temas **Light** y **Dark**
- Carga de **temas personalizados** desde archivos

### Editor de Temas
- **Editor visual** con pestañas organizadas:
  - 🎨 **Colores**: Selector de colores para todos los elementos de la UI
  - 📝 **Fuentes**: Configuración de familias y tamaños de fuente
  - 📏 **Espaciado**: Control de márgenes, padding y bordes

- **Vista previa en tiempo real**: Aplica cambios temporalmente para verlos antes de guardar
- **Basado en temas existentes**: Crea temas personalizados partiendo de Light o Dark
- **Guardar temas personalizados**: Almacena tus creaciones para uso futuro

### Importar/Exportar
- **Importar temas** desde archivos JSON
- **Exportar el tema actual** para compartir o respaldar
- Formato JSON estándar y fácil de editar

---

## 🔧 Instalación

1. El plugin viene preinstalado en Scrapelio Browser
2. Actívalo desde el **Panel de Plugins**:
   - Click en el icono de plugins en la barra lateral
   - Busca "Custom Themes"
   - Click en "Instalar" o "Activar"
3. Si es un plugin premium, necesitarás una suscripción activa

---

## 📖 Uso

### Cambiar Tema

1. Abre el selector de temas:
   - Desde el Panel de Plugins → Configuración de "Custom Themes"
   - O mediante el menú del navegador

2. Haz click en cualquier tarjeta de tema para aplicarlo instantáneamente

### Crear Tema Personalizado

1. Abre el **Editor de Temas**:
   - Desde el Selector de Temas → "✏️ Abrir Editor de Temas"

2. Selecciona un **tema base** (Light o Dark) como punto de partida

3. Personaliza los elementos:
   - **Colores**: Click en cada botón de color para abrir el selector
   - **Fuentes**: Modifica familia y tamaños de fuente
   - **Espaciado**: Ajusta márgenes y radios de borde

4. **Vista Previa**: Click en "👁 Vista Previa" para ver los cambios temporalmente

5. **Guardar**:
   - Ingresa un nombre para tu tema
   - Click en "💾 Guardar como Nuevo Tema"
   - Tu tema se guardará en `/ui/themes/custom/`

### Importar Tema

1. Consigue un archivo de tema `.json` (de internet o de un amigo)
2. En el Selector de Temas → "📥 Importar Tema"
3. Selecciona el archivo `.json`
4. El tema se agregará a tu colección

### Exportar Tema

1. Aplica el tema que quieres exportar
2. En el Selector de Temas → "📤 Exportar Tema Actual"
3. Elige dónde guardar el archivo `.json`
4. Comparte el archivo con otros usuarios

---

## 🎯 Integración con ThemeEngine

Este plugin se integra completamente con el **ThemeEngine consolidado** del navegador (`/ui/core/theme_engine.py`), lo que significa:

- ✅ Compatibilidad total con el sistema de temas del navegador
- ✅ Los temas se aplican a TODA la interfaz (no solo partes)
- ✅ Persistencia automática de preferencias
- ✅ Signals Qt para notificar cambios de tema
- ✅ API unificada para otros componentes

---

## 🗂️ Estructura de Archivos

```
plugins/themes/
├── plugin.py                      # Plugin principal (PluginBase)
├── theme_selector_panel.py        # Interfaz del selector
├── theme_editor_panel.py          # Interfaz del editor
├── plugin_info.json               # Metadata del plugin
├── __init__.py                    # Exportaciones del paquete
└── README.md                      # Esta documentación
```

---

## 🔑 Formato de Tema (JSON)

```json
{
  "id": "mi_tema",
  "name": "Mi Tema Personalizado",
  "description": "Un tema increíble",
  "version": "1.0.0",
  "author": "Tu Nombre",
  "colors": {
    "primary": "#2c3e50",
    "background": "#ffffff",
    "accent": "#3498db",
    "success": "#27ae60",
    "warning": "#f39c12",
    "error": "#e74c3c",
    "border": "#dee2e6",
    "hover": "#e9ecef",
    "selected": "#cce8ff",
    "text_primary": "#2c3e50",
    "text_secondary": "#6c757d"
  },
  "fonts": {
    "family": "Segoe UI, Arial, sans-serif",
    "size_small": "9pt",
    "size_normal": "10pt",
    "size_large": "12pt",
    "size_title": "14pt"
  },
  "spacing": {
    "xs": "2px",
    "sm": "4px",
    "md": "8px",
    "lg": "12px",
    "xl": "16px",
    "xxl": "24px"
  },
  "borders": {
    "radius": "4px",
    "width": "1px"
  }
}
```

---

## 🆕 Changelog

### v2.0.0 (Actual)
- ✨ **Refactorización completa** del plugin
- ✅ Implementa `PluginBase` para compatibilidad con `UnifiedPluginManager`
- 🔗 **Integración total** con `ThemeEngine` consolidado
- 🎨 **Nuevo selector visual** con tarjetas de temas
- ✏️ **Editor mejorado** con pestañas y selectores de color gráficos
- 👁️ **Vista previa en tiempo real**
- 📦 Importar/Exportar temas mejorado
- 🎯 Período de prueba extendido a **7 días**

### v1.0.0
- 🎉 Versión inicial
- Temas predefinidos (Light, Dark, Cyberpunk)
- Editor básico

---

## 💰 Licencia y Precio

- **Tipo**: Plugin Premium
- **Precio**: $4.99 USD/mes
- **Período de prueba**: 7 días gratis
- **Ciclo de facturación**: Mensual

---

## 🛠️ Desarrollo

### Dependencias
- `PySide6` (Qt para Python)
- `ui.core.theme_engine` (ThemeEngine del navegador)

### API del Plugin

```python
# Obtener instancia del plugin
from plugins.themes import get_plugin_instance
plugin = get_plugin_instance()

# Abrir selector de temas
from plugins.themes import open_theme_selector
selector = open_theme_selector(parent=self)

# Abrir editor de temas
from plugins.themes import open_theme_editor
editor = open_theme_editor(parent=self)

# Acceder al ThemeEngine
from plugins.themes import get_theme_manager
theme_engine = get_theme_manager()
```

---

## 📞 Soporte

Para reportar bugs o solicitar features:
- GitHub Issues: [scrapelio-browser/issues](https://github.com/scrapelio/browser/issues)
- Email: support@scrapelio.com
- Discord: [Scrapelio Community](https://discord.gg/scrapelio)

---

## 👥 Créditos

**Desarrollado por**: Scrapelio Team
**Versión**: 2.0.0
**Licencia**: Proprietary

---

¡Disfruta personalizando tu navegador! 🎨✨
