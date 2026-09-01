#!/usr/bin/env python3
"""
Plugin de Tema Cyberpunk - Ejemplo de plugin personalizado
Demuestra cómo crear temas personalizados con efectos especiales
"""

def register_theme_plugin():
    """
    Función requerida para registrar el plugin

    Returns:
        Información del plugin
    """

    return {
        "name": "Cyberpunk Theme Plugin",
        "version": "1.0.0",
        "description": "Tema futurista con efectos cyberpunk",
        "author": "Tellectus Team",
        "themes": {
            "cyberpunk": create_cyberpunk_theme(),
            "cyberpunk_blue": create_cyberpunk_blue_theme(),
            "matrix": create_matrix_theme()
        },
        "processors": [cyberpunk_processor]
    }

def create_cyberpunk_theme():
    """Crea el tema cyberpunk principal"""

    return {
        "name": "Cyberpunk 2077",
        "description": "Tema futurista inspirado en Cyberpunk 2077",
        "version": "1.0.0",
        "colors": {
            "primary": "#00ff9f",
            "secondary": "#ff0080", 
            "background": "#0a0a0a",
            "surface": "#1a1a1a",
            "accent": "#ff0080",
            "success": "#00ff9f",
            "warning": "#ffff00",
            "error": "#ff0040",
            "border": "#333333",
            "hover": "#2a2a2a",
            "selected": "#ff008033"
        },
        "fonts": {
            "family": "Consolas, 'Courier New', monospace",
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
            "xl": "16px"
        },
        "borders": {
            "radius": "2px",
            "width": "1px"
        },
        "effects": {
            "glow": True,
            "neon": True,
            "scan_lines": True
        }
    }

def create_cyberpunk_blue_theme():
    """Crea variante azul del tema cyberpunk"""

    theme = create_cyberpunk_theme()
    theme["name"] = "Cyberpunk Blue"
    theme["description"] = "Variante azul del tema cyberpunk"
    theme["colors"]["primary"] = "#00d4ff"
    theme["colors"]["accent"] = "#0080ff"
    theme["colors"]["secondary"] = "#0040ff"
    return theme

def create_matrix_theme():
    """Crea tema inspirado en Matrix"""

    return {
        "name": "Matrix",
        "description": "Tema inspirado en la película Matrix",
        "version": "1.0.0", 
        "colors": {
            "primary": "#00ff00",
            "secondary": "#008000",
            "background": "#000000",
            "surface": "#001100",
            "accent": "#00ff00",
            "success": "#00ff00",
            "warning": "#ffff00",
            "error": "#ff0000",
            "border": "#004400",
            "hover": "#002200",
            "selected": "#00ff0033"
        },
        "fonts": {
            "family": "Consolas, 'Courier New', monospace",
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
            "xl": "16px"
        },
        "borders": {
            "radius": "0px",
            "width": "1px"
        },
        "effects": {
            "matrix_rain": True,
            "terminal": True
        }
    }

def cyberpunk_processor(theme_data: dict) -> str:
    """
    Procesador específico para efectos cyberpunk

    Args:
        theme_data: Datos del tema
    Returns:
        CSS con efectos cyberpunk
    """

    colors = theme_data.get("colors", {})
    effects = theme_data.get("effects", {})

    css = ""

    # Efectos de brillo/glow
    if effects.get("glow"):
        css += f"""
        /* Efectos de brillo cyberpunk */
        QPushButton:hover {{
        }}

        QLineEdit:focus {{
        }}

        QTabBar::tab:selected {{
        }}
        """
    # Efectos neón
    if effects.get("neon"):
        css += f"""
        /* Efectos neón */
        QLabel {{
            text-shadow: 0 0 5px {colors.get('primary', '#00ff9f')};
        }}

        QGroupBox::title {{
            text-shadow: 0 0 8px {colors.get('accent', '#ff0080')};
        }}
        """
    # Líneas de escaneo
    if effects.get("scan_lines"):
        css += f"""
        /* Líneas de escaneo */
        QWidget {{
            background-image: repeating-linear-gradient(
                0deg,
                transparent,
                transparent 2px,
                {colors.get('primary', '#00ff9f')}11 2px,
                {colors.get('primary', '#00ff9f')}11 4px
            );
        }}
        """
    # Efectos Matrix
    if effects.get("matrix_rain"):
        css += f"""
        /* Efectos Matrix */
        QTextEdit {{
            background-image: url('themes/matrix_bg.gif');
            background-repeat: repeat;
        }}
        """
    if effects.get("terminal"):
        css += f"""
        /* Estilo terminal */
        QTextEdit, QLineEdit {{
            font-family: 'Consolas', 'Courier New', monospace;
            background-color: #000000;
            color: {colors.get('primary', '#00ff00')};
            border: 1px solid {colors.get('primary', '#00ff00')};
        }}
        """
    return css
