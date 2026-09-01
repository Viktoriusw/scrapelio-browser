#!/usr/bin/env python3
"""
Analysis Coordinator
Coordinates all SEO analyzers and manages analysis workflow
"""

from typing import Dict, Any, List, Optional
import sys
import os

# Add parent directory to path for imports
plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from analyzers.meta_analyzer import MetaAnalyzer
from analyzers.heading_analyzer import HeadingAnalyzer
from analyzers.image_analyzer import ImageAnalyzer
from analyzers.link_analyzer import LinkAnalyzer
from analyzers.performance_analyzer import PerformanceAnalyzer
from analyzers.schema_analyzer import SchemaAnalyzer
from analyzers.accessibility_analyzer import AccessibilityAnalyzer
from core.tier_manager import TierManager


class AnalysisCoordinator:
    """Coordinates SEO analysis workflow"""
    
    def __init__(self, tier_manager: Optional[TierManager] = None):
        """
        Initialize Analysis Coordinator
        
        Args:
            tier_manager: TierManager instance for feature access control
        """
        self.tier_manager = tier_manager or TierManager("free")
        self.analyzers = self._initialize_analyzers()
        self.last_results = {}
    
    def _initialize_analyzers(self) -> Dict[str, Any]:
        """Initialize all analyzers based on available tier"""
        analyzers = {}
        current_tier = self.tier_manager.get_tier()
        
        # Map analyzer names to classes
        analyzer_classes = {
            "meta": MetaAnalyzer,
            "heading": HeadingAnalyzer,
            "image": ImageAnalyzer,
            "link": LinkAnalyzer,
            "performance": PerformanceAnalyzer,
            "schema": SchemaAnalyzer,
            "accessibility": AccessibilityAnalyzer
        }
        
        # Initialize only available analyzers
        for name, analyzer_class in analyzer_classes.items():
            if self.tier_manager.can_use_analyzer(name):
                analyzers[name] = analyzer_class(tier=current_tier)
        
        return analyzers
    
    def analyze(self, html: str, url: str, analyzers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run SEO analysis
        
        Args:
            html: HTML content to analyze
            url: URL being analyzed
            analyzers: List of specific analyzers to run (None = all available)
            
        Returns:
            Dictionary with analysis results
        """
        results = {}
        
        # Determine which analyzers to run
        if analyzers is None:
            analyzers_to_run = list(self.analyzers.keys())
        else:
            # Filter requested analyzers by available ones
            analyzers_to_run = [a for a in analyzers if a in self.analyzers]
        
        # Run each analyzer
        for analyzer_name in analyzers_to_run:
            try:
                analyzer = self.analyzers[analyzer_name]
                results[analyzer_name] = analyzer.analyze(html, url)
            except Exception as e:
                print(f"Error running {analyzer_name} analyzer: {e}")
                import traceback
                traceback.print_exc()
                results[analyzer_name] = {
                    "score": 0,
                    "issues": [{
                        "type": "error",
                        "message": f"Error durante el análisis: {str(e)}"
                    }],
                    "recommendations": ["Contacta con soporte técnico"],
                    "severity": "error"
                }
        
        # Calculate overall score
        if results:
            total_score = sum(r.get("score", 0) for r in results.values())
            results["overall"] = {
                "score": total_score // len(results),
                "total_analyzers": len(results),
                "tier": self.tier_manager.get_tier()
            }
        
        self.last_results = results
        return results
    
    def get_available_analyzers(self) -> List[str]:
        """Get list of available analyzer names"""
        return list(self.analyzers.keys())
    
    def get_analyzer_info(self, analyzer_name: str) -> Dict[str, Any]:
        """Get information about a specific analyzer"""
        if analyzer_name not in self.analyzers:
            return {"available": False, "reason": "Not available in current tier"}
        
        analyzer_info = {
            "meta": {
                "name": "Meta Tags",
                "description": "Analiza meta tags, title, description, Open Graph, Twitter Cards",
                "icon": "🏷️"
            },
            "heading": {
                "name": "Estructura de Headings",
                "description": "Analiza H1-H6 y jerarquía de encabezados",
                "icon": "📑"
            },
            "image": {
                "name": "Optimización de Imágenes",
                "description": "Analiza alt text, dimensiones y optimización de imágenes",
                "icon": "🖼️"
            },
            "link": {
                "name": "Enlaces",
                "description": "Analiza enlaces internos, externos y estructura de links",
                "icon": "🔗"
            },
            "performance": {
                "name": "Rendimiento",
                "description": "Analiza tamaño HTML, scripts, estilos y recursos",
                "icon": "⚡"
            },
            "schema": {
                "name": "Schema Markup",
                "description": "Analiza datos estructurados JSON-LD y microdata",
                "icon": "📊"
            },
            "accessibility": {
                "name": "Accesibilidad",
                "description": "Analiza características de accesibilidad (ARIA, semántica)",
                "icon": "♿"
            }
        }
        
        return analyzer_info.get(analyzer_name, {"name": analyzer_name, "description": "Analyzer", "icon": "🔍"})
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of last analysis"""
        if not self.last_results:
            return {"status": "no_analysis"}
        
        summary = {
            "overall_score": self.last_results.get("overall", {}).get("score", 0),
            "tier": self.tier_manager.get_tier(),
            "analyzers_run": len(self.last_results) - 1,  # -1 for 'overall' key
            "total_issues": 0,
            "critical_issues": 0,
            "warnings": 0,
            "info": 0
        }
        
        for analyzer_name, results in self.last_results.items():
            if analyzer_name == "overall":
                continue
            
            issues = results.get("issues", [])
            summary["total_issues"] += len(issues)
            
            for issue in issues:
                issue_type = issue.get("type", "info")
                if issue_type == "error":
                    summary["critical_issues"] += 1
                elif issue_type == "warning":
                    summary["warnings"] += 1
                else:
                    summary["info"] += 1
        
        return summary
    
    def get_recommendations(self) -> List[str]:
        """Get all recommendations from last analysis"""
        if not self.last_results:
            return []
        
        all_recommendations = []
        for analyzer_name, results in self.last_results.items():
            if analyzer_name == "overall":
                continue
            recommendations = results.get("recommendations", [])
            all_recommendations.extend(recommendations)
        
        return all_recommendations
