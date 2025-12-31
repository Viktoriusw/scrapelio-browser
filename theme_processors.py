#!/usr/bin/env python3
"""
Theme Processors - Procesadores específicos para diferentes componentes
Permite personalización granular de estilos por módulo
"""

import os

def browser_theme_processor(theme_data: dict) -> str:
    """
    Procesador específico para componentes del navegador
    
    Args:
        theme_data: Datos del tema
        
    Returns:
        CSS específico para navegador
    """
    
    colors = theme_data.get("colors", {})
    spacing = theme_data.get("spacing", {})
    borders = theme_data.get("borders", {})
    
    # Generar ruta absoluta para el icono de cierre
    close_icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "icons", "cross.png"))
    close_icon_path = close_icon_path.replace("\\", "/")  # Qt QSS necesita / incluso en Windows
    
    return f"""
    /* === ESTILOS ESPECÍFICOS DEL NAVEGADOR === */
    
    /* Navigation bar */
    #navigationBar {{
        background-color: {colors.get('surface', '#ffffff')};
        border-bottom: {borders.get('width', '1px')} solid {colors.get('border', '#cccccc')};
        padding: {spacing.get('sm', '4px')};
    }}
    
    /* Barra de URL */
    #urlBar {{
        background-color: {colors.get('surface', '#ffffff')};
        border: {borders.get('width', '1px')} solid {colors.get('border', '#cccccc')};
        border-radius: {borders.get('radius', '4px')};
        padding: {spacing.get('md', '8px')};
        font-size: {theme_data.get('fonts', {}).get('size_normal', '10pt')};
    }}
    
    #urlBar:focus {{
        border-color: {colors.get('accent', '#0078d4')};
        box-shadow: 0 0 0 2px {colors.get('accent', '#0078d4')}33;
    }}
    
    /* Tabs del navegador */
    #browserTabs QTabBar::tab {{
        background-color: {colors.get('background', '#f0f0f0')};
        color: {colors.get('secondary', '#666666')};
        padding: {spacing.get('md', '8px')} {spacing.get('lg', '12px')};
        border-top-left-radius: {borders.get('radius', '4px')};
        border-top-right-radius: {borders.get('radius', '4px')};
        margin-right: 2px;
        min-width: 120px;
        max-width: 200px;
    }}
    
    #browserTabs QTabBar::tab:selected {{
        background-color: {colors.get('surface', '#ffffff')};
        color: {colors.get('primary', '#000000')};
        border-bottom: 2px solid {colors.get('accent', '#0078d4')};
    }}
    
    #browserTabs QTabBar::tab:hover:!selected {{
        background-color: {colors.get('hover', '#f0f0f0')};
    }}
    
    /* Botón cerrar tab - con icono personalizado */
    QTabBar::close-button {{
        image: url("{close_icon_path}");
        width: 16px;
        height: 16px;
        background-color: transparent;
        border-radius: 2px;
        margin: 2px;
        subcontrol-position: right;
    }}
    
    QTabBar::close-button:hover {{
        background-color: {colors.get('error', '#d13438')}33;
    }}
    
    #browserTabs QTabBar::close-button {{
        image: url("{close_icon_path}");
        width: 16px;
        height: 16px;
        background-color: transparent;
        border-radius: 2px;
        margin: 2px;
        subcontrol-position: right;
    }}
    
    #browserTabs QTabBar::close-button:hover {{
        background-color: {colors.get('error', '#d13438')}33;
    }}
    """

def scraping_theme_processor(theme_data: dict) -> str:
    """
    Procesador específico para paneles de scraping
    
    Args:
        theme_data: Datos del tema
        
    Returns:
        CSS específico para scraping
    """
    
    colors = theme_data.get("colors", {})
    spacing = theme_data.get("spacing", {})
    borders = theme_data.get("borders", {})
    
    return f"""
    /* === ESTILOS ESPECÍFICOS DE SCRAPING === */
    
    /* Panel de scraping */
    #scrapingPanel {{
        background-color: {colors.get('background', '#ffffff')};
        border: {borders.get('width', '1px')} solid {colors.get('border', '#cccccc')};
    }}
    
    /* Área de resultados */
    #scrapingResults {{
        background-color: {colors.get('surface', '#ffffff')};
        color: {colors.get('primary', '#000000')};
        border: {borders.get('width', '1px')} solid {colors.get('border', '#cccccc')};
        border-radius: {borders.get('radius', '4px')};
        padding: {spacing.get('md', '8px')};
        font-family: 'Consolas', 'Monaco', monospace;
    }}
    
    /* Botones de acción de scraping */
    #scrapingPanel QPushButton {{
        background-color: {colors.get('accent', '#0078d4')};
        color: white;
        border: none;
        border-radius: {borders.get('radius', '4px')};
        padding: {spacing.get('md', '8px')} {spacing.get('lg', '12px')};
        font-weight: bold;
    }}
    
    #scrapingPanel QPushButton:hover {{
        background-color: {colors.get('accent', '#0078d4')}dd;
    }}
    
    #scrapingPanel QPushButton:pressed {{
        background-color: {colors.get('accent', '#0078d4')}bb;
    }}
    
    /* Selectores detectados */
    .selector-item {{
        background-color: {colors.get('surface', '#ffffff')};
        border: {borders.get('width', '1px')} solid {colors.get('border', '#cccccc')};
        border-radius: {borders.get('radius', '4px')};
        padding: {spacing.get('sm', '4px')};
        margin: {spacing.get('xs', '2px')};
    }}
    
    .selector-item:hover {{
        background-color: {colors.get('hover', '#f0f0f0')};
        border-color: {colors.get('accent', '#0078d4')};
    }}
    """

def chat_theme_processor(theme_data: dict) -> str:
    """
    Procesador específico para paneles de chat
    
    Args:
        theme_data: Datos del tema
        
    Returns:
        CSS específico para chat
    """
    
    colors = theme_data.get("colors", {})
    spacing = theme_data.get("spacing", {})
    borders = theme_data.get("borders", {})
    
    return f"""
    /* === ESTILOS ESPECÍFICOS DE CHAT === */
    
    /* Panel de chat */
    #chatPanel {{
        background-color: {colors.get('background', '#ffffff')};
    }}
    
    /* Área de mensajes */
    #chatMessages {{
        background-color: {colors.get('surface', '#ffffff')};
        border: {borders.get('width', '1px')} solid {colors.get('border', '#cccccc')};
        border-radius: {borders.get('radius', '4px')};
        padding: {spacing.get('md', '8px')};
    }}
    
    /* Mensaje del usuario */
    .user-message {{
        background-color: {colors.get('accent', '#0078d4')};
        color: white;
        border-radius: {borders.get('radius', '4px')};
        padding: {spacing.get('md', '8px')};
        margin: {spacing.get('sm', '4px')} 0;
        margin-left: {spacing.get('xl', '16px')};
        text-align: right;
    }}
    
    /* Mensaje del asistente */
    .assistant-message {{
        background-color: {colors.get('surface', '#f8f8f8')};
        color: {colors.get('primary', '#000000')};
        border: {borders.get('width', '1px')} solid {colors.get('border', '#cccccc')};
        border-radius: {borders.get('radius', '4px')};
        padding: {spacing.get('md', '8px')};
        margin: {spacing.get('sm', '4px')} 0;
        margin-right: {spacing.get('xl', '16px')};
    }}
    
    /* Input de chat */
    #chatInput {{
        background-color: {colors.get('surface', '#ffffff')};
        border: {borders.get('width', '1px')} solid {colors.get('border', '#cccccc')};
        border-radius: {borders.get('radius', '4px')};
        padding: {spacing.get('md', '8px')};
        min-height: 60px;
    }}
    
    #chatInput:focus {{
        border-color: {colors.get('accent', '#0078d4')};
    }}
    """

def bookmarks_theme_processor(theme_data: dict) -> str:
    """
    Procesador específico para marcadores
    
    Args:
        theme_data: Datos del tema
        
    Returns:
        CSS específico para marcadores
    """
    
    colors = theme_data.get("colors", {})
    spacing = theme_data.get("spacing", {})
    borders = theme_data.get("borders", {})
    
    return f"""
    /* === ESTILOS ESPECÍFICOS DE MARCADORES === */
    
    /* Panel de marcadores */
    #bookmarksPanel {{
        background-color: {colors.get('background', '#ffffff')};
    }}
    
    /* Árbol de marcadores */
    #bookmarksTree {{
        background-color: {colors.get('surface', '#ffffff')};
        color: {colors.get('primary', '#000000')};
        border: {borders.get('width', '1px')} solid {colors.get('border', '#cccccc')};
        selection-background-color: {colors.get('selected', '#cce8ff')};
    }}
    
    #bookmarksTree::item {{
        padding: {spacing.get('sm', '4px')};
        border-bottom: 1px solid {colors.get('border', '#eeeeee')};
    }}
    
    #bookmarksTree::item:hover {{
        background-color: {colors.get('hover', '#f0f0f0')};
    }}
    
    #bookmarksTree::item:selected {{
        background-color: {colors.get('selected', '#cce8ff')};
        color: {colors.get('primary', '#000000')};
    }}
    
    /* Barra de favoritos */
    #favoritesBar {{
        background-color: {colors.get('surface', '#ffffff')};
        border-bottom: {borders.get('width', '1px')} solid {colors.get('border', '#cccccc')};
        padding: {spacing.get('sm', '4px')};
    }}
    
    .bookmark-button {{
        background-color: transparent;
        color: {colors.get('primary', '#000000')};
        border: none;
        padding: {spacing.get('sm', '4px')} {spacing.get('md', '8px')};
        border-radius: {borders.get('radius', '4px')};
    }}
    
    .bookmark-button:hover {{
        background-color: {colors.get('hover', '#f0f0f0')};
    }}
    """

def privacy_theme_processor(theme_data: dict) -> str:
    """
    Procesador específico para paneles de privacidad
    
    Args:
        theme_data: Datos del tema
        
    Returns:
        CSS específico para privacidad
    """
    
    colors = theme_data.get("colors", {})
    spacing = theme_data.get("spacing", {})
    borders = theme_data.get("borders", {})
    
    return f"""
    /* === ESTILOS ESPECÍFICOS DE PRIVACIDAD === */
    
    /* Panel de privacidad */
    #privacyPanel {{
        background-color: {colors.get('background', '#ffffff')};
    }}
    
    /* Indicadores de estado de privacidad */
    .privacy-status-safe {{
        background-color: {colors.get('success', '#107c10')};
        color: white;
        border-radius: {borders.get('radius', '4px')};
        padding: {spacing.get('xs', '2px')} {spacing.get('sm', '4px')};
        font-size: {theme_data.get('fonts', {}).get('size_small', '9pt')};
        font-weight: bold;
    }}
    
    .privacy-status-warning {{
        background-color: {colors.get('warning', '#ff8c00')};
        color: white;
        border-radius: {borders.get('radius', '4px')};
        padding: {spacing.get('xs', '2px')} {spacing.get('sm', '4px')};
        font-size: {theme_data.get('fonts', {}).get('size_small', '9pt')};
        font-weight: bold;
    }}
    
    .privacy-status-danger {{
        background-color: {colors.get('error', '#d13438')};
        color: white;
        border-radius: {borders.get('radius', '4px')};
        padding: {spacing.get('xs', '2px')} {spacing.get('sm', '4px')};
        font-size: {theme_data.get('fonts', {}).get('size_small', '9pt')};
        font-weight: bold;
    }}
    
    /* Lista de bloqueadores */
    #blockersTable {{
        background-color: {colors.get('surface', '#ffffff')};
        gridline-color: {colors.get('border', '#cccccc')};
    }}
    
    #blockersTable::item:selected {{
        background-color: {colors.get('selected', '#cce8ff')};
    }}
    """
