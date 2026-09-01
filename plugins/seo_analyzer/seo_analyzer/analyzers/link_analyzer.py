#!/usr/bin/env python3
"""
Link Analyzer - Analyzes internal and external links
"""

import time
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from .base_analyzer import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity


class LinkAnalyzer(BaseAnalyzer):
    """
    Analyzes links for SEO:
    - Internal vs external links
    - Nofollow attributes
    - Broken links (basic detection)
    - Anchor text quality
    - Link count and distribution
    """
    
    def __init__(self):
        super().__init__("Link Analyzer")
    
    def analyze(self, html: str, url: str, additional_data: Optional[Dict] = None) -> AnalysisResult:
        """Analyze links in HTML"""
        start_time = time.time()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            issues = []
            data = {}
            score = 100.0
            
            # Extract all links
            links = self._extract_links(soup, url)
            data['links'] = links
            data['total_count'] = len(links)
            
            # Categorize links
            internal = [l for l in links if l['type'] == 'internal']
            external = [l for l in links if l['type'] == 'external']
            
            data['internal_count'] = len(internal)
            data['external_count'] = len(external)
            
            if not links:
                self._add_issue(
                    issues, IssueSeverity.WARNING,
                    "No Links Found",
                    "Page has no links. Internal linking helps SEO and user navigation.",
                    recommendation="Add relevant internal and external links.",
                    impact_score=50,
                    fix_complexity="medium"
                )
                return AnalysisResult(
                    analyzer_name=self.name,
                    url=url,
                    score=50,
                    grade="F",
                    issues=issues,
                    data=data,
                    execution_time=time.time() - start_time,
                    success=True
                )
            
            # Analyze internal links
            internal_score, internal_issues = self._analyze_internal_links(internal)
            issues.extend(internal_issues)
            score -= (100 - internal_score) * 0.30  # Internal links are 30%
            
            # Analyze external links
            external_score, external_issues = self._analyze_external_links(external)
            issues.extend(external_issues)
            score -= (100 - external_score) * 0.20  # External links are 20%
            
            # Analyze anchor text
            anchor_score, anchor_issues = self._analyze_anchor_text(links)
            issues.extend(anchor_issues)
            score -= (100 - anchor_score) * 0.25  # Anchor text is 25%
            
            # Analyze nofollow usage
            nofollow_score, nofollow_issues = self._analyze_nofollow(links)
            issues.extend(nofollow_issues)
            score -= (100 - nofollow_score) * 0.15  # Nofollow is 15%
            
            # Analyze broken links (basic)
            broken_score, broken_issues = self._analyze_broken_links(links)
            issues.extend(broken_issues)
            score -= (100 - broken_score) * 0.10  # Broken links are 10%
            
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
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract all links with metadata"""
        links = []
        base_domain = urlparse(base_url).netloc
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').strip()
            
            if not href or href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:') or href.startswith('tel:'):
                continue
            
            # Get anchor text
            anchor_text = a_tag.get_text().strip()
            
            # Determine if internal or external
            link_domain = urlparse(urljoin(base_url, href)).netloc
            link_type = 'internal' if link_domain == base_domain or not link_domain else 'external'
            
            # Check for nofollow
            rel = a_tag.get('rel', [])
            if isinstance(rel, str):
                rel = [rel]
            nofollow = 'nofollow' in rel
            
            # Check for target blank
            target_blank = a_tag.get('target') == '_blank'
            
            links.append({
                'href': href,
                'anchor_text': anchor_text,
                'anchor_length': len(anchor_text),
                'type': link_type,
                'nofollow': nofollow,
                'target_blank': target_blank,
                'domain': link_domain
            })
        
        return links
    
    def _analyze_internal_links(self, internal_links: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Analyze internal links"""
        issues = []
        score = 100.0
        
        count = len(internal_links)
        
        if count == 0:
            self._add_issue(
                issues, IssueSeverity.ERROR,
                "No Internal Links",
                "Page has no internal links. Internal linking is important for SEO.",
                recommendation="Add links to other relevant pages on your site.",
                impact_score=70,
                fix_complexity="medium"
            )
            return 30, issues
        
        elif count < 3:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "Few Internal Links",
                f"Only {count} internal link(s) found. More internal links improve site structure.",
                recommendation="Add more links to related content on your site.",
                impact_score=40,
                fix_complexity="easy"
            )
            score = 60
        
        elif count > 100:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "Excessive Internal Links",
                f"{count} internal links found. Too many links can dilute link value.",
                recommendation="Consider reducing to focus on most important links.",
                impact_score=30,
                fix_complexity="medium"
            )
            score = 70
        
        else:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Good Internal Linking",
                f"{count} internal links - good for site structure.",
                impact_score=0
            )
        
        return score, issues
    
    def _analyze_external_links(self, external_links: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Analyze external links"""
        issues = []
        score = 100.0
        
        count = len(external_links)
        
        if count == 0:
            self._add_issue(
                issues, IssueSeverity.INFO,
                "No External Links",
                "Page has no external links. Linking to quality sources can add value.",
                recommendation="Consider linking to authoritative external sources when relevant.",
                impact_score=20,
                fix_complexity="easy"
            )
            score = 80
        
        elif count > 50:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "Many External Links",
                f"{count} external links found. Excessive external links may look spammy.",
                recommendation="Reduce external links to most relevant/authoritative sources.",
                impact_score=40,
                fix_complexity="medium"
            )
            score = 60
        
        else:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Balanced External Linking",
                f"{count} external link(s) - good balance.",
                impact_score=0
            )
        
        # Check for target="_blank" without rel="noopener"
        target_blank_count = len([l for l in external_links if l['target_blank']])
        if target_blank_count > 0:
            self._add_issue(
                issues, IssueSeverity.INFO,
                "External Links Open in New Tab",
                f"{target_blank_count} external link(s) open in new tab. Consider adding rel='noopener' for security.",
                recommendation="Add rel='noopener noreferrer' to target='_blank' links.",
                impact_score=10,
                fix_complexity="easy"
            )
            score -= 5
        
        return score, issues
    
    def _analyze_anchor_text(self, links: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Analyze anchor text quality"""
        issues = []
        score = 100.0
        
        # Check for empty anchor text
        empty_anchors = [l for l in links if not l['anchor_text']]
        if empty_anchors:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                f"Empty Anchor Text ({len(empty_anchors)} links)",
                f"{len(empty_anchors)} link(s) have no anchor text.",
                recommendation="Add descriptive anchor text to all links.",
                impact_score=50,
                fix_complexity="easy"
            )
            score -= (len(empty_anchors) / len(links)) * 40
        
        # Check for generic anchor text
        generic_texts = ['click here', 'read more', 'here', 'this', 'link', 'more']
        generic_anchors = [l for l in links if l['anchor_text'].lower() in generic_texts]
        
        if generic_anchors:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                f"Generic Anchor Text ({len(generic_anchors)} links)",
                f"{len(generic_anchors)} link(s) use generic anchor text like 'click here'.",
                recommendation="Use descriptive, keyword-rich anchor text that describes the destination.",
                impact_score=40,
                fix_complexity="easy"
            )
            score -= (len(generic_anchors) / len(links)) * 30
        
        # Check for very long anchor text
        long_anchors = [l for l in links if l['anchor_length'] > 100]
        if long_anchors:
            self._add_issue(
                issues, IssueSeverity.INFO,
                f"Long Anchor Text ({len(long_anchors)} links)",
                f"{len(long_anchors)} link(s) have anchor text over 100 characters.",
                recommendation="Keep anchor text concise while remaining descriptive.",
                impact_score=15,
                fix_complexity="easy"
            )
            score -= (len(long_anchors) / len(links)) * 10
        
        if not empty_anchors and not generic_anchors:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Quality Anchor Text",
                "Anchor text appears to be descriptive.",
                impact_score=0
            )
        
        return score, issues
    
    def _analyze_nofollow(self, links: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Analyze nofollow usage"""
        issues = []
        score = 100.0
        
        internal_nofollow = [l for l in links if l['type'] == 'internal' and l['nofollow']]
        external_nofollow = [l for l in links if l['type'] == 'external' and l['nofollow']]
        
        if internal_nofollow:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                f"Internal Links with Nofollow ({len(internal_nofollow)})",
                f"{len(internal_nofollow)} internal link(s) have nofollow attribute.",
                recommendation="Remove nofollow from internal links to pass PageRank within your site.",
                impact_score=45,
                fix_complexity="easy"
            )
            score -= 20
        
        external_total = len([l for l in links if l['type'] == 'external'])
        if external_total > 0:
            nofollow_percentage = (len(external_nofollow) / external_total) * 100
            
            if nofollow_percentage > 80:
                self._add_issue(
                    issues, IssueSeverity.INFO,
                    "Most External Links are Nofollow",
                    f"{nofollow_percentage:.0f}% of external links have nofollow.",
                    recommendation="Consider which external links should pass PageRank.",
                    impact_score=20,
                    fix_complexity="easy"
                )
                score -= 10
        
        return score, issues
    
    def _analyze_broken_links(self, links: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Basic broken link detection"""
        issues = []
        score = 100.0
        
        # Check for obviously broken patterns
        suspicious = [l for l in links if 
                     l['href'].startswith('#') or 
                     l['href'] == '' or
                     l['href'] in ['#', 'javascript:void(0)']]
        
        if suspicious:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                f"Suspicious Links ({len(suspicious)})",
                f"{len(suspicious)} link(s) may be broken or non-functional.",
                recommendation="Review and fix broken or placeholder links.",
                impact_score=60,
                fix_complexity="easy"
            )
            score -= (len(suspicious) / len(links)) * 50
        
        return score, issues

