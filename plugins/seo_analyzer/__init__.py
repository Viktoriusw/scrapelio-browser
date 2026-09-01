#!/usr/bin/env python3
"""
SEO Analyzer Pro Plugin
Professional-grade SEO auditing tool for Scrapelio Browser
"""

__version__ = "1.0.0"
__author__ = "Scrapelio Team"
__all__ = ['SEOAnalyzerPlugin', 'get_seo_panel', 'initialize_plugin']

# Plugin metadata
PLUGIN_ID = "seo_analyzer"
PLUGIN_NAME = "SEO Analyzer Pro"
PLUGIN_AVAILABLE = False

# Try to import plugin components
try:
    from .core.analysis_coordinator import AnalysisCoordinator
    from .core.tier_manager import TierManager
    PLUGIN_AVAILABLE = True
    print(f"[OK] {PLUGIN_NAME} components loaded")
except ImportError as e:
    print(f"[WARNING] {PLUGIN_NAME} not available: {e}")
    AnalysisCoordinator = None
    TierManager = None

