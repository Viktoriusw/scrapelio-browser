#!/usr/bin/env python3
"""
Base Analyzer - Foundation for all SEO analyzers
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class IssueSeverity(Enum):
    """Severity levels for SEO issues"""
    CRITICAL = "critical"  # Must fix immediately
    ERROR = "error"        # Important issue
    WARNING = "warning"    # Should improve
    INFO = "info"          # Informational
    SUCCESS = "success"    # Doing great


@dataclass
class SEOIssue:
    """Represents a single SEO issue or recommendation"""
    severity: IssueSeverity
    title: str
    description: str
    element: Optional[str] = None  # CSS selector or element description
    recommendation: Optional[str] = None
    impact_score: int = 0  # 0-100, how much this affects SEO
    fix_complexity: str = "easy"  # easy, medium, hard
    learn_more_url: Optional[str] = None


@dataclass
class AnalysisResult:
    """
    Standard result structure for all analyzers
    """
    analyzer_name: str
    url: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Main metrics
    score: float = 0.0  # 0-100
    grade: str = "F"  # A+ to F
    
    # Issues found
    issues: List[SEOIssue] = field(default_factory=list)
    
    # Raw data extracted
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    execution_time: float = 0.0  # seconds
    success: bool = True
    error_message: Optional[str] = None
    
    def get_issues_by_severity(self, severity: IssueSeverity) -> List[SEOIssue]:
        """Filter issues by severity"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_critical_count(self) -> int:
        """Count critical issues"""
        return len(self.get_issues_by_severity(IssueSeverity.CRITICAL))
    
    def get_error_count(self) -> int:
        """Count errors"""
        return len(self.get_issues_by_severity(IssueSeverity.ERROR))
    
    def get_warning_count(self) -> int:
        """Count warnings"""
        return len(self.get_issues_by_severity(IssueSeverity.WARNING))
    
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues"""
        return self.get_critical_count() > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "analyzer": self.analyzer_name,
            "url": self.url,
            "timestamp": self.timestamp.isoformat(),
            "score": self.score,
            "grade": self.grade,
            "issues_count": {
                "critical": self.get_critical_count(),
                "errors": self.get_error_count(),
                "warnings": self.get_warning_count(),
                "total": len(self.issues)
            },
            "issues": [
                {
                    "severity": issue.severity.value,
                    "title": issue.title,
                    "description": issue.description,
                    "element": issue.element,
                    "recommendation": issue.recommendation,
                    "impact_score": issue.impact_score
                }
                for issue in self.issues
            ],
            "data": self.data,
            "execution_time": self.execution_time,
            "success": self.success
        }


class BaseAnalyzer(ABC):
    """
    Base class for all SEO analyzers
    
    Each analyzer should:
    1. Extract relevant data from HTML/page
    2. Analyze data against SEO best practices
    3. Generate scored result with issues and recommendations
    """
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
    
    @abstractmethod
    def analyze(self, html: str, url: str, additional_data: Optional[Dict] = None) -> AnalysisResult:
        """
        Analyze HTML content and return results
        
        Args:
            html: Page HTML content
            url: Page URL
            additional_data: Optional additional data (JS metrics, etc)
            
        Returns:
            AnalysisResult: Structured analysis results
        """
        pass
    
    def _calculate_grade(self, score: float) -> str:
        """Convert numeric score to letter grade"""
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
            return "D+"
        elif score >= 45:
            return "D"
        elif score >= 40:
            return "D-"
        else:
            return "F"
    
    def _add_issue(self, issues: List[SEOIssue], severity: IssueSeverity, 
                   title: str, description: str, **kwargs):
        """Helper to add an issue to the list"""
        issue = SEOIssue(
            severity=severity,
            title=title,
            description=description,
            **kwargs
        )
        issues.append(issue)
    
    def is_enabled(self) -> bool:
        """Check if analyzer is enabled"""
        return self.enabled
    
    def enable(self):
        """Enable analyzer"""
        self.enabled = True
    
    def disable(self):
        """Disable analyzer"""
        self.enabled = False

