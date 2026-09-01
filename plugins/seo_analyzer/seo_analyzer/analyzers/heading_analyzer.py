#!/usr/bin/env python3
"""
Heading Structure Analyzer - Analyzes H1-H6 heading hierarchy
"""

import time
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Tag
from .base_analyzer import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity


class HeadingAnalyzer(BaseAnalyzer):
    """
    Analyzes heading structure (H1-H6):
    - Presence and uniqueness of H1
    - Hierarchical structure
    - Keyword usage
    - Length optimization
    - Heading count and distribution
    """
    
    def __init__(self):
        super().__init__("Heading Structure Analyzer")
        
        # Optimal ranges
        self.H1_MIN = 20
        self.H1_MAX = 70
    
    def analyze(self, html: str, url: str, additional_data: Optional[Dict] = None) -> AnalysisResult:
        """Analyze heading structure"""
        start_time = time.time()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            issues = []
            data = {}
            score = 100.0
            
            # Extract all headings
            headings = self._extract_headings(soup)
            data['headings'] = headings
            data['counts'] = self._count_headings(headings)
            
            # Analyze H1
            h1_score, h1_issues = self._analyze_h1(headings)
            issues.extend(h1_issues)
            score -= (100 - h1_score) * 0.40  # H1 is 40% of heading score
            
            # Analyze hierarchy
            hierarchy_score, hierarchy_issues = self._analyze_hierarchy(headings)
            issues.extend(hierarchy_issues)
            score -= (100 - hierarchy_score) * 0.30  # Hierarchy is 30%
            
            # Analyze heading distribution
            distribution_score, distribution_issues = self._analyze_distribution(headings)
            issues.extend(distribution_issues)
            score -= (100 - distribution_score) * 0.20  # Distribution is 20%
            
            # Analyze heading content quality
            content_score, content_issues = self._analyze_content_quality(headings)
            issues.extend(content_issues)
            score -= (100 - content_score) * 0.10  # Content quality is 10%
            
            # Ensure score is valid
            score = max(0, min(100, score))
            grade = self._calculate_grade(score)
            
            execution_time = time.time() - start_time
            
            return AnalysisResult(
                analyzer_name=self.name,
                url=url,
                score=score,
                grade=grade,
                issues=issues,
                data=data,
                execution_time=execution_time,
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return AnalysisResult(
                analyzer_name=self.name,
                url=url,
                score=0,
                grade="F",
                issues=[],
                data={},
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract all headings with their level and text"""
        headings = []
        
        for level in range(1, 7):  # H1 to H6
            tags = soup.find_all(f'h{level}')
            for tag in tags:
                text = tag.get_text().strip()
                if text:  # Only include non-empty headings
                    headings.append({
                        'level': level,
                        'text': text,
                        'length': len(text),
                        'element': f'h{level}'
                    })
        
        return headings
    
    def _count_headings(self, headings: List[Dict]) -> Dict[str, int]:
        """Count headings by level"""
        counts = {f'h{i}': 0 for i in range(1, 7)}
        
        for heading in headings:
            level = heading['level']
            counts[f'h{level}'] += 1
        
        return counts
    
    def _analyze_h1(self, headings: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Analyze H1 tags"""
        issues = []
        score = 100.0
        
        h1_headings = [h for h in headings if h['level'] == 1]
        
        if not h1_headings:
            self._add_issue(
                issues, IssueSeverity.CRITICAL,
                "Missing H1 Tag",
                "No H1 heading found on the page. H1 is crucial for SEO.",
                recommendation="Add one clear, descriptive H1 tag that describes the main topic.",
                impact_score=100,
                fix_complexity="easy"
            )
            return 0, issues
        
        if len(h1_headings) > 1:
            self._add_issue(
                issues, IssueSeverity.ERROR,
                "Multiple H1 Tags",
                f"Found {len(h1_headings)} H1 tags. Having multiple H1s can confuse search engines.",
                recommendation="Use only one H1 tag per page. Convert others to H2 or H3.",
                impact_score=70,
                fix_complexity="easy"
            )
            score = 40
        
        # Analyze the first (or only) H1
        h1 = h1_headings[0]
        h1_text = h1['text']
        h1_length = h1['length']
        
        # Check length
        if h1_length < self.H1_MIN:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "H1 Too Short",
                f"H1 is only {h1_length} characters. Recommended: {self.H1_MIN}-{self.H1_MAX}.",
                element="h1",
                recommendation="Expand H1 to be more descriptive.",
                impact_score=40,
                fix_complexity="easy"
            )
            score -= 20
        
        elif h1_length > self.H1_MAX:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "H1 Too Long",
                f"H1 is {h1_length} characters. Recommended: {self.H1_MIN}-{self.H1_MAX}.",
                element="h1",
                recommendation="Make H1 more concise while keeping it descriptive.",
                impact_score=30,
                fix_complexity="easy"
            )
            score -= 15
        
        else:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "H1 Optimal",
                f"H1 length is {h1_length} characters - perfect!",
                element="h1",
                impact_score=0
            )
        
        # Check if H1 is empty or just whitespace
        if not h1_text or h1_text.isspace():
            self._add_issue(
                issues, IssueSeverity.CRITICAL,
                "Empty H1 Tag",
                "H1 tag exists but contains no text.",
                recommendation="Add meaningful text to your H1.",
                impact_score=95,
                fix_complexity="easy"
            )
            score = 10
        
        return score, issues
    
    def _analyze_hierarchy(self, headings: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Analyze heading hierarchy structure"""
        issues = []
        score = 100.0
        
        if not headings:
            return score, issues
        
        # Check for skipped levels
        levels_present = sorted(set(h['level'] for h in headings))
        
        for i in range(len(levels_present) - 1):
            current_level = levels_present[i]
            next_level = levels_present[i + 1]
            
            if next_level - current_level > 1:
                self._add_issue(
                    issues, IssueSeverity.WARNING,
                    "Skipped Heading Level",
                    f"Heading structure jumps from H{current_level} to H{next_level}, skipping H{current_level + 1}.",
                    recommendation="Use sequential heading levels (H1 → H2 → H3) for proper structure.",
                    impact_score=30,
                    fix_complexity="medium"
                )
                score -= 20
        
        # Check if H1 comes before other headings
        if len(headings) > 1:
            first_heading_level = headings[0]['level']
            if first_heading_level != 1:
                self._add_issue(
                    issues, IssueSeverity.WARNING,
                    "H1 Not First",
                    f"First heading is H{first_heading_level}, not H1.",
                    recommendation="Place H1 at the beginning of your content.",
                    impact_score=25,
                    fix_complexity="easy"
                )
                score -= 15
        
        # Check for proper nesting
        prev_level = 0
        for heading in headings:
            level = heading['level']
            
            # Level shouldn't jump more than 1 from previous
            if level - prev_level > 1 and prev_level > 0:
                self._add_issue(
                    issues, IssueSeverity.INFO,
                    "Heading Level Jump",
                    f"Heading jumps from H{prev_level} to H{level}: '{heading['text'][:50]}'",
                    recommendation="Consider using intermediate heading levels.",
                    impact_score=10,
                    fix_complexity="medium"
                )
                score -= 5
                break  # Only report once
            
            prev_level = level
        
        if score == 100:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Proper Heading Hierarchy",
                "Heading structure follows proper hierarchy.",
                impact_score=0
            )
        
        return score, issues
    
    def _analyze_distribution(self, headings: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Analyze heading distribution"""
        issues = []
        score = 100.0
        
        if not headings:
            self._add_issue(
                issues, IssueSeverity.ERROR,
                "No Headings Found",
                "Page has no heading tags at all.",
                recommendation="Add structured headings to organize your content.",
                impact_score=80,
                fix_complexity="medium"
            )
            return 0, issues
        
        counts = self._count_headings(headings)
        
        # Check for reasonable number of H2s
        h2_count = counts['h2']
        if h2_count == 0:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "No H2 Headings",
                "Page has no H2 headings. H2s help structure content.",
                recommendation="Add H2 headings to break up main sections.",
                impact_score=40,
                fix_complexity="medium"
            )
            score -= 30
        
        elif h2_count > 15:
            self._add_issue(
                issues, IssueSeverity.INFO,
                "Many H2 Headings",
                f"Page has {h2_count} H2 headings. Consider if content could be split.",
                recommendation="Very long pages may benefit from being split into multiple pages.",
                impact_score=15,
                fix_complexity="hard"
            )
            score -= 10
        
        else:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Good H2 Distribution",
                f"Page has {h2_count} H2 headings - good structure.",
                impact_score=0
            )
        
        # Check total heading count
        total = len(headings)
        if total < 3:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "Few Headings",
                f"Only {total} headings found. Content may lack structure.",
                recommendation="Add more headings to organize content better.",
                impact_score=30,
                fix_complexity="medium"
            )
            score -= 20
        
        return score, issues
    
    def _analyze_content_quality(self, headings: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Analyze heading content quality"""
        issues = []
        score = 100.0
        
        # Check for very short headings (may not be descriptive)
        short_headings = [h for h in headings if h['length'] < 10]
        if short_headings:
            self._add_issue(
                issues, IssueSeverity.INFO,
                "Short Headings",
                f"Found {len(short_headings)} heading(s) under 10 characters.",
                recommendation="Ensure headings are descriptive enough to convey meaning.",
                impact_score=15,
                fix_complexity="easy"
            )
            score -= 10
        
        # Check for very long headings (may need splitting)
        long_headings = [h for h in headings if h['length'] > 100]
        if long_headings:
            self._add_issue(
                issues, IssueSeverity.INFO,
                "Very Long Headings",
                f"Found {len(long_headings)} heading(s) over 100 characters.",
                recommendation="Consider making headings more concise.",
                impact_score=10,
                fix_complexity="easy"
            )
            score -= 10
        
        # Check for duplicate headings
        heading_texts = [h['text'].lower() for h in headings]
        duplicates = set([text for text in heading_texts if heading_texts.count(text) > 1])
        
        if duplicates:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "Duplicate Headings",
                f"Found {len(duplicates)} duplicate heading text(s).",
                recommendation="Make each heading unique to improve content clarity.",
                impact_score=20,
                fix_complexity="easy"
            )
            score -= 15
        
        if score == 100:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Good Heading Content",
                "Heading content quality is good.",
                impact_score=0
            )
        
        return score, issues

