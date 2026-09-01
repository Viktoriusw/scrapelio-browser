#!/usr/bin/env python3
"""
Proxy Management Plugin for Tellectus
Main plugin file that integrates with the browser
"""

import os
import sys
from pathlib import Path

# Add plugin directory to path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

try:
    from proxy_panel import ProxyPanel
    
    # Plugin is available
    PROXY_PLUGIN_AVAILABLE = True
    print("[OK] Proxy Management plugin loaded")
    
except ImportError as e:
    # Plugin not available
    PROXY_PLUGIN_AVAILABLE = False
    print(f"[WARNING] Proxy Management plugin not available: {e}")
    
    # Create dummy functions for compatibility
    def ProxyPanel(*args, **kwargs):
        return None

def get_plugin_info():
    """Return plugin information"""
    return {
        "name": "Proxy Management",
        "version": "1.0.0",
        "author": "Tellectus Team",
        "description": "Advanced proxy management and configuration",
        "category": "Network",
        "dependencies": ["requests"],
        "compatibility": ">=1.0.0",
        "premium": True,
        "available": PROXY_PLUGIN_AVAILABLE
    }

def initialize_plugin():
    """Initialize the plugin"""
    if PROXY_PLUGIN_AVAILABLE:
        print("[OK] Proxy Management plugin initialized")
        return True
    else:
        print("[WARNING] Proxy Management plugin not available")
        return False

def get_proxy_panel():
    """Get the proxy panel class"""
    if PROXY_PLUGIN_AVAILABLE:
        return ProxyPanel
    return None
