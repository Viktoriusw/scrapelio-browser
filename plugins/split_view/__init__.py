#!/usr/bin/env python3
"""
Split View Plugin for Scrapelio Browser
Advanced split view functionality with context menu integration
"""

__version__ = "2.1.0"
__author__ = "Scrapelio Team"
__description__ = "Vista dividida que permite mantener una página web visible mientras navegas en otras pestañas"

# Export main plugin components
from .plugin import (
    SplitViewPlugin,
    initialize_plugin,
    get_plugin_instance,
    shutdown_plugin
)

__all__ = [
    'SplitViewPlugin',
    'initialize_plugin',
    'get_plugin_instance',
    'shutdown_plugin'
]
