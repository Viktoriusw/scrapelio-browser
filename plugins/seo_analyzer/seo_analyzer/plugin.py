#!/usr/bin/env python3
"""
SEO Analyzer Pro Plugin for Tellectus
Main plugin file that integrates with the browser
"""

import os
import sys
from pathlib import Path

# Add plugin directory to path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

try:
    from core.analysis_coordinator import AnalysisCoordinator
    from core.tier_manager import TierManager
    from ui.seo_panel import SEOAnalyzerPanel
    
    # Plugin is available
    SEO_PLUGIN_AVAILABLE = True
    print("[OK] SEO Analyzer Pro plugin loaded")
    
except ImportError as e:
    # Plugin not available
    SEO_PLUGIN_AVAILABLE = False
    print(f"[WARNING] SEO Analyzer Pro plugin not available: {e}")
    
    # Create dummy classes for compatibility
    class SEOAnalyzerPanel:
        def __init__(self, *args, **kwargs):
            pass
    
    class AnalysisCoordinator:
        def __init__(self, *args, **kwargs):
            pass
    
    class TierManager:
        def __init__(self, *args, **kwargs):
            pass


def get_plugin_info():
    """Return plugin information"""
    return {
        "id": "seo_analyzer",
        "name": "SEO Analyzer Pro",
        "version": "1.0.0",
        "author": "Scrapelio Team",
        "description": "Professional-grade SEO auditing tool with tiered features",
        "category": "SEO & Marketing",
        "dependencies": [
            "beautifulsoup4>=4.11.0",
            "lxml>=4.9.0",
            "requests>=2.28.0",
            "pandas>=1.5.0",
            "numpy>=1.24.0"
        ],
        "compatibility": ">=1.0.0",
        "premium": True,
        "available": SEO_PLUGIN_AVAILABLE
    }


def initialize_plugin():
    """Initialize the plugin"""
    if SEO_PLUGIN_AVAILABLE:
        print("[OK] SEO Analyzer Pro plugin initialized")
        return True
    else:
        print("[WARNING] SEO Analyzer Pro plugin not available")
        return False


def get_seo_panel():
    """Get the SEO analyzer panel class"""
    if SEO_PLUGIN_AVAILABLE:
        return SEOAnalyzerPanel
    return None


def get_analysis_coordinator():
    """Get the analysis coordinator class"""
    if SEO_PLUGIN_AVAILABLE:
        return AnalysisCoordinator
    return None


def get_tier_manager():
    """Get the tier manager class"""
    if SEO_PLUGIN_AVAILABLE:
        return TierManager
    return None


# Main plugin class for UnifiedPluginManager compatibility
class SEOAnalyzerPlugin:
    """Main plugin class for SEO Analyzer Pro"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.panel = None
        self.coordinator = None
        self.tier_manager = None
        
        if SEO_PLUGIN_AVAILABLE:
            self._initialize_components()
    
    def _initialize_components(self):
        """Initialize plugin components"""
        try:
            # Create tier manager
            self.tier_manager = TierManager()
            
            # Create analysis coordinator
            self.coordinator = AnalysisCoordinator(tier_manager=self.tier_manager)
            
            # Create UI panel
            self.panel = SEOAnalyzerPanel(
                parent=self.parent,
                coordinator=self.coordinator,
                tier_manager=self.tier_manager
            )
            
            print("[OK] SEO Analyzer Pro components initialized")
        except Exception as e:
            print(f"[ERROR] Failed to initialize SEO Analyzer Pro: {e}")
    
    def get_panel(self):
        """Get the plugin panel widget"""
        return self.panel
    
    def cleanup(self):
        """Cleanup plugin resources"""
        if self.panel:
            self.panel.cleanup()
        print("[OK] SEO Analyzer Pro cleanup complete")

