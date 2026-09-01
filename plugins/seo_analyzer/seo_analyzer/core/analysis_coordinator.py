#!/usr/bin/env python3
"""
Analysis Coordinator - Orchestrates all SEO analyzers
"""

import time
from typing import Dict, List, Optional, Any
from PySide6.QtCore import QObject, Signal, QThread
from datetime import datetime

# Import analyzers
try:
    from ..analyzers import (
        BaseAnalyzer, AnalysisResult,
        MetaAnalyzer, HeadingAnalyzer, ImageAnalyzer, LinkAnalyzer
    )
except ImportError:
    # Fallback for relative imports
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from analyzers import (
        BaseAnalyzer, AnalysisResult,
        MetaAnalyzer, HeadingAnalyzer, ImageAnalyzer, LinkAnalyzer
    )


class AnalysisCoordinator(QObject):
    """
    Coordinates all SEO analyzers and aggregates results
    
    Manages:
    - Running analyzers based on tier
    - Collecting and aggregating results
    - Calculating overall SEO score
    - Emitting progress signals
    """
    
    # Signals
    analysis_started = Signal(str)  # url
    analysis_progress = Signal(int, str)  # progress (0-100), current_analyzer
    analysis_completed = Signal(dict)  # results
    analysis_error = Signal(str)  # error_message
    
    def __init__(self, tier_manager=None):
        super().__init__()
        self.tier_manager = tier_manager
        
        # Initialize basic analyzers (available in FREE tier)
        self.basic_analyzers = {
            'meta': MetaAnalyzer(),
            'headings': HeadingAnalyzer(),
            'images': ImageAnalyzer(),
            'links': LinkAnalyzer()
        }
        
        # Advanced analyzers (PROFESSIONAL+)
        self.advanced_analyzers = {}
        
        # Enterprise analyzers
        self.enterprise_analyzers = {}
        
        # Current analysis state
        self.current_url = None
        self.current_results = {}
        self.is_analyzing = False
    
    def analyze_page(self, browser_tab, url: str):
        """
        Start analysis of a page
        
        Args:
            browser_tab: QWebEngineView instance
            url: Page URL
        """
        if self.is_analyzing:
            print("[AnalysisCoordinator] Analysis already in progress")
            return
        
        # Check tier limits
        if self.tier_manager:
            if not self.tier_manager.can_analyze_today():
                print("[AnalysisCoordinator] Daily analysis limit reached")
                self.analysis_error.emit("Daily analysis limit reached. Upgrade for unlimited analyses.")
                return
        
        self.is_analyzing = True
        self.current_url = url
        self.current_results = {}
        
        print(f"[AnalysisCoordinator] Starting analysis of: {url}")
        self.analysis_started.emit(url)
        
        # Extract HTML from page
        browser_tab.page().toHtml(lambda html: self._run_analysis(html, url))
    
    def _run_analysis(self, html: str, url: str):
        """Run all enabled analyzers"""
        try:
            start_time = time.time()
            results = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'analyzers': {},
                'overall_score': 0,
                'overall_grade': 'F',
                'total_issues': 0,
                'critical_issues': 0,
                'execution_time': 0
            }
            
            # Determine which analyzers to run based on tier
            analyzers_to_run = self._get_enabled_analyzers()
            total_analyzers = len(analyzers_to_run)
            
            # Run each analyzer
            for idx, (name, analyzer) in enumerate(analyzers_to_run.items()):
                progress = int((idx / total_analyzers) * 100)
                self.analysis_progress.emit(progress, name)
                
                print(f"[AnalysisCoordinator] Running {name} analyzer...")
                
                try:
                    result = analyzer.analyze(html, url)
                    results['analyzers'][name] = result
                    
                    print(f"[AnalysisCoordinator] {name}: Score={result.score:.1f}, Issues={len(result.issues)}")
                    
                except Exception as e:
                    print(f"[AnalysisCoordinator] Error in {name} analyzer: {e}")
            
            # Calculate overall scores
            self._calculate_overall_scores(results)
            
            # Increment usage counter
            if self.tier_manager:
                self.tier_manager.increment_analysis_count()
            
            # Calculate execution time
            results['execution_time'] = time.time() - start_time
            
            # Store results
            self.current_results = results
            
            # Emit completion
            self.analysis_progress.emit(100, "Complete")
            self.analysis_completed.emit(results)
            
            print(f"[AnalysisCoordinator] Analysis complete: Overall Score={results['overall_score']:.1f}")
            
        except Exception as e:
            print(f"[AnalysisCoordinator] Analysis error: {e}")
            import traceback
            traceback.print_exc()
            self.analysis_error.emit(str(e))
        
        finally:
            self.is_analyzing = False
    
    def _get_enabled_analyzers(self) -> Dict[str, BaseAnalyzer]:
        """Get analyzers enabled for current tier"""
        enabled = {}
        
        # Basic analyzers (always available)
        enabled.update(self.basic_analyzers)
        
        # Advanced analyzers (PROFESSIONAL+)
        if self.tier_manager and self.tier_manager.is_premium():
            enabled.update(self.advanced_analyzers)
        
        # Enterprise analyzers (ENTERPRISE only)
        if self.tier_manager and self.tier_manager.is_enterprise():
            enabled.update(self.enterprise_analyzers)
        
        return enabled
    
    def _calculate_overall_scores(self, results: Dict[str, Any]):
        """Calculate overall SEO score from analyzer results"""
        analyzer_results = results['analyzers']
        
        if not analyzer_results:
            return
        
        # Calculate weighted average
        total_score = 0
        total_weight = 0
        total_issues = 0
        critical_issues = 0
        
        # Weights for different analyzers
        weights = {
            'meta': 0.30,  # Meta tags are very important (30%)
            'headings': 0.25,  # Heading structure is important (25%)
            'images': 0.20,  # Images matter (20%)
            'links': 0.25,  # Links are crucial (25%)
            # Advanced analyzers would have lower weights
            'performance': 0.15,
            'schema': 0.10,
            'accessibility': 0.15
        }
        
        for name, result in analyzer_results.items():
            if isinstance(result, AnalysisResult) and result.success:
                weight = weights.get(name, 0.10)  # Default 10% weight
                total_score += result.score * weight
                total_weight += weight
                total_issues += len(result.issues)
                critical_issues += result.get_critical_count()
        
        # Calculate average score
        if total_weight > 0:
            overall_score = total_score / total_weight
        else:
            overall_score = 0
        
        # Determine grade
        overall_grade = self._calculate_grade(overall_score)
        
        results['overall_score'] = overall_score
        results['overall_grade'] = overall_grade
        results['total_issues'] = total_issues
        results['critical_issues'] = critical_issues
    
    def _calculate_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "A-"
        elif score >= 80:
            return "B+"
        elif score >= 75:
            return "B"
        elif score >= 70:
            return "B-"
        elif score >= 65:
            return "C+"
        elif score >= 60:
            return "C"
        elif score >= 55:
            return "C-"
        elif score >= 50:
            return "D"
        else:
            return "F"
    
    def get_current_results(self) -> Dict[str, Any]:
        """Get results from last analysis"""
        return self.current_results
    
    def export_results_json(self) -> str:
        """Export results as JSON"""
        import json
        
        # Convert AnalysisResult objects to dictionaries
        export_data = self.current_results.copy()
        
        if 'analyzers' in export_data:
            analyzers_dict = {}
            for name, result in export_data['analyzers'].items():
                if isinstance(result, AnalysisResult):
                    analyzers_dict[name] = result.to_dict()
                else:
                    analyzers_dict[name] = result
            export_data['analyzers'] = analyzers_dict
        
        return json.dumps(export_data, indent=2)

