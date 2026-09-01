#!/usr/bin/env python3
"""
Accessibility Analyzer - Analyzes accessibility features
(PROFESSIONAL tier feature)
"""

import time
from typing import Dict, Optional
from bs4 import BeautifulSoup
from .base_analyzer import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity


class AccessibilityAnalyzer(BaseAnalyzer):
    """
    Analyzes accessibility:
    - ARIA labels
    - Form labels
    - Link text
    - Language attribute
    - Semantic HTML
    """
    
    def __init__(self):
        super().__init__("Accessibility Analyzer")
    
    def analyze(self, html: str, url: str, additional_data: Optional[Dict] = None) -> AnalysisResult:
        """Analyze accessibility"""
        start_time = time.time()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            issues = []
            data = {}
            score = 100.0
            
            # Check lang attribute on html
            html_tag = soup.find('html')
            has_lang = html_tag and html_tag.get('lang')
            
            if not has_lang:
                self._add_issue(
                    issues, IssueSeverity.WARNING,
                    "Missing Language Attribute",
                    "No lang attribute on <html> tag.",
                    recommendation="Add lang='en' (or appropriate language) to <html> tag.",
                    impact_score=40,
                    fix_complexity="easy"
                )
                score -= 20
            
            # Check for form labels
            forms = soup.find_all('form')
            inputs = soup.find_all('input', type=lambda x: x not in ['hidden', 'submit', 'button'])
            labels = soup.find_all('label')
            
            data['forms'] = len(forms)
            data['inputs'] = len(inputs)
            data['labels'] = len(labels)
            
            if inputs and len(labels) < len(inputs):
                self._add_issue(
                    issues, IssueSeverity.WARNING,
                    "Missing Form Labels",
                    f"{len(inputs)} input(s) but only {len(labels)} label(s).",
                    recommendation="Add <label> tags for all form inputs for accessibility.",
                    impact_score=50,
                    fix_complexity="easy"
                )
                score -= 25
            
            # Check for ARIA landmarks
            aria_landmarks = soup.find_all(attrs={'role': True})
            data['aria_landmarks'] = len(aria_landmarks)
            
            if not aria_landmarks and len(soup.find_all(['header', 'nav', 'main', 'footer'])) == 0:
                self._add_issue(
                    issues, IssueSeverity.INFO,
                    "No ARIA Landmarks",
                    "No ARIA landmarks or semantic HTML5 elements found.",
                    recommendation="Use semantic HTML5 tags (header, nav, main, footer) or ARIA roles.",
                    impact_score=30,
                    fix_complexity="medium"
                )
                score -= 15
            
            # Check for buttons without text
            buttons = soup.find_all('button')
            empty_buttons = [b for b in buttons if not b.get_text().strip() and not b.get('aria-label')]
            
            if empty_buttons:
                self._add_issue(
                    issues, IssueSeverity.WARNING,
                    "Buttons Without Text",
                    f"{len(empty_buttons)} button(s) have no text or aria-label.",
                    recommendation="Add text or aria-label to all buttons.",
                    impact_score=35,
                    fix_complexity="easy"
                )
                score -= 20
            
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

