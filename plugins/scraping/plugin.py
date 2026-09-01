#!/usr/bin/env python3
"""
Advanced Scraping Plugin for Tellectus
Main plugin file that integrates with the browser
"""

import os
import sys
from pathlib import Path

# Add plugin directory to path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

try:
    from scraping_panel import ScrapingPanel
    from scraping_integration import scraping_integration
    from pattern_detector import PatternDetector
    
    # Plugin is available
    SCRAPING_PLUGIN_AVAILABLE = True
    print("[OK] Advanced Scraping plugin loaded")
    
except ImportError as e:
    # Plugin not available
    SCRAPING_PLUGIN_AVAILABLE = False
    print(f"[WARNING] Advanced Scraping plugin not available: {e}")
    
    # Create dummy functions for compatibility
    def ScrapingPanel(*args, **kwargs):
        return None
    
    def scraping_integration():
        return None
    
    def PatternDetector():
        return None

def get_plugin_info():
    """Return plugin information"""
    return {
        "name": "Advanced Scraping",
        "version": "1.0.0",
        "author": "Tellectus Team",
        "description": "Professional web scraping and data extraction",
        "category": "Data Extraction",
        "dependencies": ["beautifulsoup4", "selenium", "playwright", "pandas"],
        "compatibility": ">=1.0.0",
        "premium": True,
        "available": SCRAPING_PLUGIN_AVAILABLE
    }

def initialize_plugin():
    """Initialize the plugin"""
    if SCRAPING_PLUGIN_AVAILABLE:
        print("[OK] Advanced Scraping plugin initialized")
        return True
    else:
        print("[WARNING] Advanced Scraping plugin not available")
        return False

def get_scraping_panel():
    """Get the scraping panel class"""
    if SCRAPING_PLUGIN_AVAILABLE:
        return ScrapingPanel
    return None

def get_scraping_integration():
    """Get the scraping integration module"""
    if SCRAPING_PLUGIN_AVAILABLE:
        return scraping_integration
    return None

def get_pattern_detector():
    """Get the pattern detector class"""
    if SCRAPING_PLUGIN_AVAILABLE:
        return PatternDetector
    return None
