#!/usr/bin/env python3
"""
Advanced Theme System Plugin Package
Integrated with Scrapelio Browser's ThemeEngine
"""

# Export main plugin components
from .plugin import (
    ThemePlugin,
    initialize_plugin,
    get_plugin_instance,
    shutdown_plugin,
    get_theme_manager,
    open_theme_selector,
    open_theme_editor,
    THEME_PLUGIN_AVAILABLE
)

__all__ = [
    'ThemePlugin',
    'initialize_plugin',
    'get_plugin_instance',
    'shutdown_plugin',
    'get_theme_manager',
    'open_theme_selector',
    'open_theme_editor',
    'THEME_PLUGIN_AVAILABLE'
]

__version__ = '2.0.0'
__author__ = 'Scrapelio Team'
