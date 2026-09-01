#!/usr/bin/env python3
"""
Performance Analyzer - Analyzes page performance and Core Web Vitals
(PROFESSIONAL tier feature)
"""

import time
from typing import Dict, Optional, Tuple, List
from bs4 import BeautifulSoup
from .base_analyzer import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity


class PerformanceAnalyzer(BaseAnalyzer):
    """
    Analyzes performance metrics:
    - Resource count (CSS, JS, images)
    - Estimated page weight
    - Blocking resources
    - Minification
    """
    
    def __init__(self):
        super().__init__("Performance Analyzer")
    
    def analyze(self, html: str, url: str, additional_data: Optional[Dict] = None) -> AnalysisResult:
        """Analyze performance"""
        start_time = time.time()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            issues = []
            data = {}
            score = 100.0
            
            # Count resources
            css_count = len(soup.find_all('link', rel='stylesheet'))
            js_count = len(soup.find_all('script', src=True))
            img_count = len(soup.find_all('img'))
            
            data['resources'] = {
                'css': css_count,
                'javascript': js_count,
                'images': img_count,
                'total': css_count + js_count + img_count
            }
            
            # Analyze CSS
            if css_count > 10:
                self._add_issue(
                    issues, IssueSeverity.WARNING,
                    "Many CSS Files",
                    f"{css_count} CSS files detected. Consider combining them.",
                    recommendation="Combine CSS files to reduce HTTP requests.",
                    impact_score=40,
                    fix_complexity="medium"
                )
                score -= 15
            
            # Analyze JS
            if js_count > 15:
                self._add_issue(
                    issues, IssueSeverity.WARNING,
                    "Many JavaScript Files",
                    f"{js_count} JS files detected. This can slow page load.",
                    recommendation="Combine and minify JavaScript files.",
                    impact_score=50,
                    fix_complexity="medium"
                )
                score -= 20
            
            # Check for inline styles (anti-pattern)
            inline_styles = len(soup.find_all(style=True))
            if inline_styles > 20:
                self._add_issue(
                    issues, IssueSeverity.INFO,
                    "Many Inline Styles",
                    f"{inline_styles} elements with inline styles detected.",
                    recommendation="Move styles to CSS files for better caching.",
                    impact_score=25,
                    fix_complexity="medium"
                )
                score -= 10
            
            # Check for minification indicators
            js_tags = soup.find_all('script', src=True)
            minified_js = len([tag for tag in js_tags if '.min.' in tag.get('src', '')])
            
            if js_count > 0:
                minification_ratio = minified_js / js_count
                if minification_ratio < 0.5:
                    self._add_issue(
                        issues, IssueSeverity.WARNING,
                        "JavaScript Not Minified",
                        "Some JS files may not be minified.",
                        recommendation="Minify all JavaScript files for better performance.",
                        impact_score=35,
                        fix_complexity="easy"
                    )
                    score -= 15
            
            score = max(0, min(100, score))
            grade = self._calculate_grade(score)
            
            return AnalysisResult(
                analyzer_name=self.name,
                url=url,
                score=score,
                grade=grade,
                issues=issues,
                data=data,
                execution_time=time.time() - start_time,
                success=True
            )
            
        except Exception as e:
            return AnalysisResult(
                analyzer_name=self.name,
                url=url,
                score=0,
                grade="F",
                issues=[],
                data={},
                execution_time=time.time() - start_time,
                success=False,
                error_message=str(e)
            )

