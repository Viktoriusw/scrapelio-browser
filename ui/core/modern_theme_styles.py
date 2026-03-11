#!/usr/bin/env python3
"""
Modern Theme Styles - Funciones de generación de estilos modernos

Extrae solo las funciones de generación de CSS de modern_styles.py
sin los componentes (que no se usan)

Origen: modern_styles.py (consolidación de estilos)
"""

def get_circular_button_style(theme_colors):
    """Estilo para botones circulares tipo Chrome - más compactos"""
    return f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            border-radius: 14px;
            min-width: 28px;
            max-width: 28px;
            min-height: 28px;
            max-height: 28px;
            padding: 4px;
            color: {theme_colors['text_primary']};
        }}
        QPushButton:hover {{
            background-color: {theme_colors['bg_hover']};
        }}
        QPushButton:pressed {{
            background-color: {theme_colors['bg_active']};
        }}
        QIcon {{
            width: 16px;
            height: 16px;
        }}
    """

def get_modern_urlbar_style(theme_colors):
    """Estilo para barra de URL expandible tipo Chrome Pill"""
    return f"""
        QLineEdit {{
            background-color: {theme_colors['urlbar_bg']};
            border: 1px solid transparent;
            border-radius: 17px; /* Pill shape fully rounded */
            padding: 6px 16px;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 13px;
            color: {theme_colors['text_primary']};
            selection-background-color: {theme_colors['accent']};
            selection-color: #FFFFFF;
        }}
        QLineEdit:focus {{
            border: 2px solid {theme_colors['accent']};
            background-color: {theme_colors['bg_primary']}; /* Usually white/dark bg on focus */
            padding: 5px 15px; /* Adjust for border width change */
        }}
        QLineEdit:hover {{
             background-color: {theme_colors['bg_hover']}; /* Slight hover effect */
        }}
    """

def get_trapezoidal_tab_style(theme_colors):
    """Estilo para pestañas tipo Chrome Moderno (Isla)"""
    return f"""
        QTabWidget::pane {{
            border-top: 1px solid {theme_colors['border']};
            background-color: {theme_colors['bg_primary']};
            top: -1px; /* Connect with tabs */
        }}
        
        QTabBar {{
            background-color: transparent;
            qproperty-drawBase: 0;
        }}
        
        QTabBar::tab {{
            background-color: transparent;
            color: {theme_colors['text_secondary']};
            border: none;
            padding: 6px 16px;
            margin-right: 2px;
            margin-left: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            min-width: 120px;
            max-width: 240px;
            height: 24px;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 12px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {theme_colors['bg_primary']}; /* Matches toolbar */
            color: {theme_colors['text_primary']};
            font-weight: 500;
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: {theme_colors['bg_hover']};
        }}
        
        QTabBar::close-button {{
            image: url(icons/cross.png);
            subcontrol-position: right;
            margin: 2px;
            border-radius: 8px;
            width: 16px;
            height: 16px;
        }}
        
        QTabBar::close-button:hover {{
            background-color: {theme_colors['bg_active']};
        }}
    """

def get_modern_navbar_style(theme_colors):
    """Estilo para barra de navegación moderna - más compacta tipo Chrome"""
    return f"""
        QWidget#navbar {{
            background-color: {theme_colors['bg_primary']};
            border-bottom: 1px solid {theme_colors['border']};
            padding: 4px 8px;
            min-height: 44px;
        }}
        
        QToolBar {{
            background-color: transparent;
            border: none;
            spacing: 4px;
        }}
        
        QToolButton {{
            background-color: transparent;
            border: none;
            border-radius: 16px;
            min-width: 32px;
            max-width: 32px;
            min-height: 32px;
            max-height: 32px;
            padding: 4px;
            margin: 0px;
        }}
        
        QToolButton:hover {{
            background-color: {theme_colors['bg_hover']};
        }}
        
        QToolButton:pressed {{
            background-color: {theme_colors['bg_active']};
        }}
    """

def get_sidebar_style(theme_colors):
    """Estilo para sidebar retráctil"""
    return f"""
        QFrame#sidebar {{
            background-color: {theme_colors['bg_secondary']};
            border-right: 1px solid {theme_colors['border']};
        }}
        QLabel#sidebar_title {{
            font-size: 14px;
            font-weight: 600;
            color: {theme_colors['text_primary']};
            padding: 16px;
        }}
    """

# Paletas de colores de los temas modernos (Actualizadas a Material Design)
class ModernTheme:
    """Temas modernos con colores predefinidos"""
    
    LIGHT = {
        'bg_primary': '#FFFFFF',
        'bg_secondary': '#F1F3F4', # Chrome Sidebar/Page bg?
        'bg_hover': '#F1F3F4',
        'bg_active': '#E8EAED',
        'text_primary': '#202124',
        'text_secondary': '#5F6368',
        'accent': '#1A73E8',
        'border': '#DADCE0',
        'shadow': 'rgba(0, 0, 0, 0.14)',
        'tab_bg': '#dee1e6',  # Frame color
        'tab_active': '#FFFFFF',
        'urlbar_bg': '#F1F3F4',
        'urlbar_border': 'transparent',
    }
    
    DARK = {
        'bg_primary': '#202124', # Chrome Dark Toolbar
        'bg_secondary': '#292A2D',
        'bg_hover': '#292A2D',
        'bg_active': '#3C4043',
        'text_primary': '#E8EAED',
        'text_secondary': '#9AA0A6',
        'accent': '#8AB4F8',
        'border': '#3C4043',
        'shadow': 'rgba(0, 0, 0, 0.5)',
        'tab_bg': '#202124',
        'tab_active': '#323639',
        'urlbar_bg': '#303134',
        'urlbar_border': 'transparent',
    }
    
    @staticmethod
    def get_theme(name='light'):
        """Obtener tema por nombre"""
        themes = {
            'light': ModernTheme.LIGHT,
            'dark': ModernTheme.DARK,
        }
        return themes.get(name.lower(), ModernTheme.LIGHT)


class ModernStylesAdapter:
    """
    Adaptador para mantener compatibilidad con código que usa
    modern_styles.ThemeManager
    
    Este adaptador simula la API antigua pero usa las nuevas funciones
    """
    
    def __init__(self, theme_name='light'):
        self.current_theme_name = theme_name
        self.current_theme = ModernTheme.get_theme(theme_name)
        self.widgets = []  # Para compatibilidad
    
    def get_tab_style(self):
        """Obtener estilo para pestañas"""
        return get_trapezoidal_tab_style(self.current_theme)
    
    def get_urlbar_style(self):
        """Obtener estilo para URL bar"""
        return get_modern_urlbar_style(self.current_theme)
    
    def get_navbar_style(self):
        """Obtener estilo para navbar"""
        return get_modern_navbar_style(self.current_theme)
    
    def get_sidebar_style(self):
        """Obtener estilo para sidebar"""
        return get_sidebar_style(self.current_theme)
    
    def get_circular_button_style(self):
        """Obtener estilo para botones circulares"""
        return get_circular_button_style(self.current_theme)
    
    def get_current_theme(self):
        """Obtener tema actual"""
        return self.current_theme
    
    def change_theme(self, theme_name):
        """Cambiar tema"""
        self.current_theme_name = theme_name
        self.current_theme = ModernTheme.get_theme(theme_name)


# Alias para compatibilidad con código existente
ThemeManager = ModernStylesAdapter

