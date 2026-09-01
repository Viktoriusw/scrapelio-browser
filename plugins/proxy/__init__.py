#!/usr/bin/env python3
"""
Proxy Management Plugin for Tellectus
Advanced proxy configuration and management
"""

__version__ = "1.0.0"
__author__ = "Tellectus Team"
__description__ = "Advanced proxy management and configuration"

# Plugin metadata
PLUGIN_INFO = {
    "name": "Proxy Management",
    "version": "1.0.0",
    "author": "Tellectus Team",
    "description": "Advanced proxy management and configuration",
    "category": "Network",
    "dependencies": ["requests"],
    "compatibility": ">=1.0.0",
    "premium": True
}

def get_plugin_info():
    """Return plugin information"""
    return PLUGIN_INFO

def initialize_plugin():
    """Initialize the plugin"""
    try:
        # Import the actual plugin module
        from . import plugin
        return plugin.initialize_plugin()
    except ImportError:
        print("[WARNING] Proxy Management plugin not available")
        return False
