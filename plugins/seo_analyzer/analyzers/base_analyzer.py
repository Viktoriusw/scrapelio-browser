#!/usr/bin/env python3
"""
Base Analyzer Class
All specific analyzers inherit from this
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseAnalyzer(ABC):
    """Base class for all SEO analyzers"""
    
    def __init__(self, tier: str = "free"):
        self.tier = tier
        self.results = {}
        
    @abstractmethod
    def analyze(self, html: str, url: str) -> Dict[str, Any]:
        """
        Analyze HTML content and return results
        
        Args:
            html: HTML content to analyze
            url: URL being analyzed
            
        Returns:
            Dictionary with analysis results
        """
        pass
    
    def get_severity(self, issues_count: int) -> str:
        """Get severity level based on issues count"""
        if issues_count == 0:
            return "success"
        elif issues_count <= 3:
            return "warning"
        else:
            return "error"
    
    def create_result(self, score: int, issues: List[Dict], recommendations: List[str]) -> Dict[str, Any]:
        """Create standardized result dictionary"""
        return {
            "score": score,
            "issues": issues,
            "recommendations": recommendations,
            "severity": self.get_severity(len(issues))
        }
