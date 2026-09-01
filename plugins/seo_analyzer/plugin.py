#!/usr/bin/env python3
"""
SEO Analyzer Pro Plugin for Scrapelio Browser
Professional-grade SEO analysis with tiered features
"""

import os
import sys
from pathlib import Path

# Add plugin directory to path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

# Ensure subdirectories are importable
for subdir in ['core', 'ui', 'analyzers', 'exporters', 'enterprise']:
    subdir_path = os.path.join(plugin_dir, subdir)
    if os.path.exists(subdir_path) and str(subdir_path) not in sys.path:
        sys.path.insert(0, str(subdir_path))

# Check PySide6 availability
try:
    from PySide6.QtWidgets import QWidget  # pyright: ignore[reportMissingImports]
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    print("[WARNING] PySide6 not available for SEO plugin")
    # Create minimal Qt stubs
    class QWidget:
        def __init__(self, *args, **kwargs):
            pass

# Plugin metadata
PLUGIN_ID = "seo_analyzer"
PLUGIN_NAME = "SEO Analyzer Pro"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Comprehensive SEO analysis tool with 17 functional tabs"
PLUGIN_AUTHOR = "Scrapelio Team"
PLUGIN_REQUIRES_LICENSE = True

# Plugin availability flag
SEO_PLUGIN_AVAILABLE = False
SEOAnalyzerPanel: any = None  # type: ignore
AnalysisCoordinator: any = None  # type: ignore
TierManager: any = None  # type: ignore

# Try to load the full plugin
try:
    # Import core components
    from core.analysis_coordinator import AnalysisCoordinator as AnalysisCoordinatorClass  # type: ignore
    from core.tier_manager import TierManager as TierManagerClass  # type: ignore
    
    AnalysisCoordinator = AnalysisCoordinatorClass  # type: ignore
    TierManager = TierManagerClass  # type: ignore
    
    if PYSIDE6_AVAILABLE:
        # Import UI panel using absolute path
        import importlib.util
        
        seo_panel_path = os.path.join(plugin_dir, 'ui', 'seo_panel.py')
        if not os.path.exists(seo_panel_path):
            raise ImportError(f"seo_panel.py not found at {seo_panel_path}")
        
        spec = importlib.util.spec_from_file_location("seo_analyzer_ui_panel", seo_panel_path)
        if spec and spec.loader:
            seo_panel_module = importlib.util.module_from_spec(spec)
            sys.modules["seo_analyzer_ui_panel"] = seo_panel_module
            spec.loader.exec_module(seo_panel_module)
            SEOAnalyzerPanel = seo_panel_module.SEOAnalyzerPanel
            print("[OK] SEO Analyzer Pro UI panel loaded successfully")
        else:
            raise ImportError("Could not load seo_panel module spec")
    else:
        raise ImportError("PySide6 not available")
    
    # Plugin is available
    SEO_PLUGIN_AVAILABLE = True
    print("[OK] SEO Analyzer Pro plugin loaded successfully")
    print(f"[INFO] Available analyzers: meta, heading, image, link, performance, schema, accessibility")
    print(f"[INFO] Export formats: JSON, CSV, PDF")
    print(f"[INFO] UI: 17 functional tabs")
    
except Exception as e:
    # Plugin not available - create dummy classes
    SEO_PLUGIN_AVAILABLE = False
    print(f"[WARNING] SEO Analyzer Pro plugin not available: {e}")
    import traceback
    traceback.print_exc()
    
    # Create dummy SEOAnalyzerPanel that shows a message
    if PYSIDE6_AVAILABLE:
        from PySide6.QtWidgets import QWidget as RealQWidget, QVBoxLayout, QLabel  # type: ignore
        
        class SEOAnalyzerPanel(RealQWidget):  # type: ignore
            def __init__(self, parent=None, *args, **kwargs):
                super().__init__(parent)
                layout = QVBoxLayout(self)
                label = QLabel("SEO Analyzer Pro requiere instalación completa.\nContacta con soporte.")
                layout.addWidget(label)
                print("[OK] SEO Analyzer Panel created in compatibility mode")
    else:
        class SEOAnalyzerPanel:  # type: ignore
            def __init__(self, parent=None, *args, **kwargs):
                print("[OK] SEO Analyzer Panel created in minimal mode")
    
    # Dummy core classes
    if not AnalysisCoordinator:
        class AnalysisCoordinator:  # type: ignore
            def __init__(self, *args, **kwargs):
                pass
    
    if not TierManager:
        class TierManager:  # type: ignore
            def __init__(self, *args, **kwargs):
                pass


def get_plugin_info():
    """Return plugin information"""
    return {
        "id": PLUGIN_ID,
        "name": PLUGIN_NAME,
        "version": PLUGIN_VERSION,
        "author": PLUGIN_AUTHOR,
        "description": PLUGIN_DESCRIPTION,
        "category": "SEO & Marketing",
        "dependencies": [
            "beautifulsoup4>=4.11.0",
            "lxml>=4.9.0"
        ],
        "compatibility": ">=1.0.0",
        "premium": True,
        "available": SEO_PLUGIN_AVAILABLE,
        "features": [
            "17 tabs funcionales",
            "7 analyzers profesionales",
            "Exportación JSON/CSV/PDF",
            "Tier management",
            "Análisis en tiempo real"
        ]
    }


def initialize_plugin():
    """Initialize the plugin"""
    if SEO_PLUGIN_AVAILABLE:
        print("[OK] SEO Analyzer Pro plugin initialized successfully")
        return True
    else:
        print("[WARNING] SEO Analyzer Pro plugin running in compatibility mode")
        return True  # Still return True to allow loading


def get_seo_panel():
    """Get the SEO analyzer panel class"""
    return SEOAnalyzerPanel


def get_analysis_coordinator():
    """Get the analysis coordinator class"""
    return AnalysisCoordinator if AnalysisCoordinator else None


def get_tier_manager():
    """Get the tier manager class"""
    return TierManager if TierManager else None


def cleanup_plugin():
    """Cleanup plugin resources"""
    print("[OK] SEO Analyzer Pro plugin cleanup")
    pass


# Main plugin class for UnifiedPluginManager compatibility
class SEOAnalyzerPlugin:
    """Main plugin class for SEO Analyzer Pro"""
    
    def __init__(self, parent=None, tier="free"):
        self.parent = parent
        self.panel = None
        self.coordinator = None
        self.tier_manager = None
        self.tier = tier
        
        if SEO_PLUGIN_AVAILABLE:
            self._initialize_components()
    
    def _initialize_components(self):
        """Initialize plugin components"""
        try:
            # Create tier manager
            if TierManager:
                self.tier_manager = TierManager(self.tier)
            
            # Create analysis coordinator
            if AnalysisCoordinator:
                self.coordinator = AnalysisCoordinator(tier_manager=self.tier_manager)
            
            # Create UI panel
            if SEOAnalyzerPanel:
                self.panel = SEOAnalyzerPanel(
                    parent=self.parent,
                    coordinator=self.coordinator,
                    tier_manager=self.tier_manager
                )
            
            print("[OK] SEO Analyzer Pro components initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize SEO Analyzer Pro: {e}")
            import traceback
            traceback.print_exc()
    
    def get_panel(self):
        """Get the plugin panel widget"""
        return self.panel
    
    def cleanup(self):
        """Cleanup plugin resources"""
        if self.panel and hasattr(self.panel, 'cleanup'):
            self.panel.cleanup()  # type: ignore
        print("[OK] SEO Analyzer Pro cleanup complete")


# Export main functions and classes
__all__ = [
    'get_plugin_info',
    'initialize_plugin', 
    'get_seo_panel',
    'get_analysis_coordinator',
    'get_tier_manager',
    'cleanup_plugin',
    'SEOAnalyzerPlugin',
    'PLUGIN_ID',
    'PLUGIN_NAME',
    'PLUGIN_VERSION',
    'SEO_PLUGIN_AVAILABLE'
]
