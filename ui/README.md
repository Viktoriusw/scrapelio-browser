# UI Package - Sistema UI Consolidado

Este paquete contiene el sistema de interfaz de usuario consolidado de Scrapelio Browser.

## 📁 Estructura

```
ui/
├── core/               # Motor central del sistema UI
│   ├── constants.py           # Constantes centralizadas (tamaños, espaciados, etc.)
│   ├── theme_engine.py        # Motor unificado de gestión de temas
│   └── modern_theme_styles.py # Generadores de estilos modernos
│
├── components/         # Componentes reutilizables
│   └── widgets.py             # Widgets modernos (ExpandableUrlBar, CircularButton)
│
├── themes/            # Temas en formato JSON
│   ├── light_theme.json       # Tema claro (base)
│   ├── dark_theme.json        # Tema oscuro (base)
│   └── custom/                # Temas personalizados del usuario
│
├── managers/          # Managers de UI (futuro)
│   └── (vacío)
│
└── windows/           # Ventanas principales (futuro)
    └── (vacío)
```

## 🎯 Propósito

Este paquete centraliza y organiza todo el código relacionado con la interfaz visual, reemplazando el sistema anterior fragmentado:

**ANTES (Sistema Antiguo):**
- ❌ `theme_manager.py` - Gestión de temas (raíz)
- ❌ `theme_loader.py` - Carga de temas (duplicado)
- ❌ `modern_styles.py` - Estilos y widgets mezclados (raíz)
- ❌ Código duplicado y difícil de mantener

**AHORA (Sistema Nuevo):**
- ✅ `ui/core/theme_engine.py` - Gestión unificada de temas
- ✅ `ui/core/modern_theme_styles.py` - Solo generación de estilos
- ✅ `ui/components/widgets.py` - Solo widgets
- ✅ `ui/core/constants.py` - Constantes centralizadas
- ✅ Separación clara de responsabilidades

## 📦 Componentes Principales

### 1. Theme Engine (`core/theme_engine.py`)

Motor unificado de gestión de temas que consolida funcionalidades de:
- `theme_manager.py` (antiguo)
- `theme_loader.py` (antiguo)

**Funcionalidades:**
- Carga de temas base (light, dark)
- Carga de temas personalizados
- Generación de CSS completo
- API retrocompatible
- Signals: `theme_changed`, `theme_loaded`

**Uso:**
```python
from ui.core.theme_engine import get_theme_engine, get_color

engine = get_theme_engine()
engine.apply_theme('dark')
color = get_color('accent')
```

### 2. Modern Theme Styles (`core/modern_theme_styles.py`)

Funciones de generación de estilos CSS modernos.

**Funcionalidades:**
- Paletas de colores predefinidas (LIGHT, DARK)
- Funciones de generación de estilos para componentes específicos
- Adaptador retrocompatible con código antiguo

**Uso:**
```python
from ui.core.modern_theme_styles import ModernStylesAdapter

adapter = ModernStylesAdapter('light')
tab_style = adapter.get_tab_style()
urlbar_style = adapter.get_urlbar_style()
```

### 3. Constants (`core/constants.py`)

Constantes centralizadas para toda la interfaz.

**Categorías:**
- `ComponentSize` - Tamaños de botones, iconos, barras
- `Spacing` - Espaciados (XS, SM, MD, LG, XL, XXL)
- `Animation` - Duraciones de animaciones
- `ThemeDefaults` - Configuración de temas
- `Navigation`, `Plugins`, `Security` - Otras constantes

**Uso:**
```python
from ui.core.constants import ComponentSize, Spacing

button.setFixedSize(ComponentSize.BUTTON_MEDIUM)  # 36x36
layout.setSpacing(Spacing.MD)  # 8px
```

### 4. Widgets (`components/widgets.py`)

Componentes visuales modernos reutilizables.

**Componentes:**
- `ExpandableUrlBar` - Barra de URL expandible tipo Chrome
- `CircularButton` - Botones circulares con animaciones

**Uso:**
```python
from ui.components.widgets import ExpandableUrlBar, CircularButton

url_bar = ExpandableUrlBar()
back_btn = CircularButton(icon_path='icons/back.png')
```

## 🔄 Retrocompatibilidad

El paquete mantiene **retrocompatibilidad total** con código existente:

```python
# Código antiguo - SIGUE FUNCIONANDO
from theme_manager import get_theme_manager, get_color

manager = get_theme_manager()  # Funciona (importa desde theme_engine)
color = get_color('accent')     # Funciona
```

**Razón:** Aliases en `theme_engine.py`:
```python
get_theme_manager = get_theme_engine
ThemeManager = ThemeEngine
```

## 🎨 Crear Temas Personalizados

Los temas personalizados se colocan en `ui/themes/custom/`:

```json
// ui/themes/custom/mi_tema.json
{
  "id": "mi_tema",
  "name": "Mi Tema Personalizado",
  "description": "Un tema hermoso",
  "colors": {
    "primary": "#FF5722",
    "background": "#FAFAFA",
    "accent": "#00BCD4",
    ...
  },
  "fonts": {...},
  "spacing": {...},
  "borders": {...}
}
```

O crear programáticamente:
```python
from ui.core.theme_engine import get_theme_engine

engine = get_theme_engine()
custom_theme = {...}
engine.create_custom_theme('mi_tema', custom_theme, save_to_file=True)
engine.apply_theme('mi_tema')
```

## 🧪 Testing

### Script de validación completo:
```bash
python3 scripts/validate_migration.py
```

### Herramienta de gestión:
```bash
# Ver temas disponibles
python3 scripts/migration_manager.py info

# Ver paleta de colores
python3 scripts/migration_manager.py colors

# Ver constantes
python3 scripts/migration_manager.py constants
```

## 📚 Documentación

- **RESUMEN_MIGRACION.md** - Resumen ejecutivo de la migración
- **MIGRACION_UI_COMPLETADA.md** - Informe completo
- **GUIA_USO_SISTEMA_UI.md** - Guía detallada de uso
- **CHECKLIST_VALIDACION.md** - Lista de verificación

## 🔌 Compatibilidad con Plugins

Los plugins existentes funcionan sin cambios:

```python
# En tu plugin - NO requiere cambios
from theme_manager import get_color  # ✅ Funciona
from base_panel import BasePanel

class MyPluginPanel(BasePanel):
    def setup_ui(self):
        color = get_color('accent')  # ✅ Funciona
```

## 🚀 Futuras Expansiones

Esta estructura está preparada para:

1. **`ui/managers/`** - Managers adicionales de UI
   - Layout managers
   - Style managers
   - Animation managers

2. **`ui/windows/`** - Ventanas principales
   - Main window (cuando se migre desde ui.py)
   - Preferences window
   - About window

3. **`ui/components/`** - Más componentes
   - StatusBar moderno
   - Sidebar mejorado
   - Menús contextuales
   - Diálogos estándar

## 📊 Métricas

- **Archivos Python:** 10
- **Temas base:** 2 (light, dark)
- **Constantes definidas:** 30+
- **Componentes reutilizables:** 2 (expandible)
- **Líneas de código:** ~1,600
- **Duplicación eliminada:** ~60%

## 🏆 Beneficios

1. ✅ **Organización clara** - Estructura lógica por función
2. ✅ **Mantenibilidad** - Cambios centralizados
3. ✅ **Reutilización** - Componentes modulares
4. ✅ **Extensibilidad** - Fácil agregar temas y componentes
5. ✅ **Retrocompatibilidad** - Código existente sigue funcionando
6. ✅ **Documentación completa** - Guías y ejemplos

## 🔗 Links Relacionados

- [Documentación Principal](../README.md)
- [Guía de Migración](../MIGRACION_UI_COMPLETADA.md)
- [Guía de Uso](../GUIA_USO_SISTEMA_UI.md)
- [Scripts de Validación](../scripts/validate_migration.py)

---

**Versión:** 1.0.0  
**Fecha:** 2026-01-01  
**Estado:** ✅ Producción

