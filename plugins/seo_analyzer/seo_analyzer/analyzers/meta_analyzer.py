#!/usr/bin/env python3
"""
Meta Tags Analyzer - Analyzes all meta tags for SEO optimization
"""

import time
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from .base_analyzer import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity


class MetaAnalyzer(BaseAnalyzer):
    """
    Analyzes meta tags:
    - Title tag
    - Meta description  
    - Meta keywords
    - Viewport
    - Robots
    - Canonical
    - Open Graph tags
    - Twitter Cards
    - Language/charset
    """
    
    def __init__(self):
        super().__init__("Meta Tags Analyzer")
        
        # Optimal ranges
        self.TITLE_MIN = 30
        self.TITLE_MAX = 60
        self.TITLE_OPTIMAL = 55
        
        self.DESC_MIN = 120
        self.DESC_MAX = 160
        self.DESC_OPTIMAL = 155
    
    def analyze(self, html: str, url: str, additional_data: Optional[Dict] = None) -> AnalysisResult:
        """Analyze meta tags in HTML"""
        start_time = time.time()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            issues = []
            data = {}
            score = 100.0  # Start with perfect score, deduct points for issues
            
            # Analyze title tag
            title_score, title_data, title_issues = self._analyze_title(soup)
            data['title'] = title_data
            issues.extend(title_issues)
            score -= (100 - title_score) * 0.25  # Title is 25% of meta score
            
            # Analyze meta description
            desc_score, desc_data, desc_issues = self._analyze_description(soup)
            data['description'] = desc_data
            issues.extend(desc_issues)
            score -= (100 - desc_score) * 0.25  # Description is 25% of meta score
            
            # Analyze canonical
            canonical_score, canonical_data, canonical_issues = self._analyze_canonical(soup, url)
            data['canonical'] = canonical_data
            issues.extend(canonical_issues)
            score -= (100 - canonical_score) * 0.10  # Canonical is 10%
            
            # Analyze robots meta
            robots_score, robots_data, robots_issues = self._analyze_robots(soup)
            data['robots'] = robots_data
            issues.extend(robots_issues)
            score -= (100 - robots_score) * 0.10  # Robots is 10%
            
            # Analyze viewport
            viewport_score, viewport_data, viewport_issues = self._analyze_viewport(soup)
            data['viewport'] = viewport_data
            issues.extend(viewport_issues)
            score -= (100 - viewport_score) * 0.10  # Viewport is 10%
            
            # Analyze charset
            charset_score, charset_data, charset_issues = self._analyze_charset(soup)
            data['charset'] = charset_data
            issues.extend(charset_issues)
            score -= (100 - charset_score) * 0.05  # Charset is 5%
            
            # Analyze Open Graph
            og_score, og_data, og_issues = self._analyze_open_graph(soup)
            data['open_graph'] = og_data
            issues.extend(og_issues)
            score -= (100 - og_score) * 0.10  # OG is 10%
            
            # Analyze Twitter Cards
            twitter_score, twitter_data, twitter_issues = self._analyze_twitter_cards(soup)
            data['twitter_cards'] = twitter_data
            issues.extend(twitter_issues)
            score -= (100 - twitter_score) * 0.05  # Twitter is 5%
            
            # Ensure score is in valid range
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
    
    def _analyze_title(self, soup: BeautifulSoup) -> tuple:
        """Analyze title tag"""
        issues = []
        score = 100.0
        
        title_tag = soup.find('title')
        
        if not title_tag:
            self._add_issue(
                issues, IssueSeverity.CRITICAL,
                "Missing Title Tag",
                "The page doesn't have a <title> tag. This is critical for SEO.",
                recommendation="Add a descriptive title tag between 30-60 characters.",
                impact_score=100,
                fix_complexity="easy"
            )
            return 0, {"present": False, "content": None, "length": 0}, issues
        
        title_text = title_tag.get_text().strip()
        title_length = len(title_text)
        
        data = {
            "present": True,
            "content": title_text,
            "length": title_length
        }
        
        # Check if empty
        if not title_text:
            self._add_issue(
                issues, IssueSeverity.CRITICAL,
                "Empty Title Tag",
                "The title tag exists but is empty.",
                recommendation="Add a descriptive title between 30-60 characters.",
                impact_score=95,
                fix_complexity="easy"
            )
            score = 10
        
        # Check length
        elif title_length < self.TITLE_MIN:
            self._add_issue(
                issues, IssueSeverity.ERROR,
                "Title Too Short",
                f"Title is only {title_length} characters. Optimal is {self.TITLE_MIN}-{self.TITLE_MAX}.",
                recommendation=f"Expand your title to at least {self.TITLE_MIN} characters for better visibility in search results.",
                impact_score=60,
                fix_complexity="easy"
            )
            score = 50
        
        elif title_length > self.TITLE_MAX:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "Title Too Long",
                f"Title is {title_length} characters. It may be truncated in search results (optimal: {self.TITLE_MIN}-{self.TITLE_MAX}).",
                recommendation="Shorten your title to improve appearance in search results.",
                impact_score=40,
                fix_complexity="easy"
            )
            score = 70
        
        else:
            # Optimal length
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Title Length Optimal",
                f"Title is {title_length} characters - perfect for search results!",
                impact_score=0
            )
        
        # Check for duplicate words
        words = title_text.lower().split()
        if len(words) != len(set(words)):
            self._add_issue(
                issues, IssueSeverity.INFO,
                "Duplicate Words in Title",
                "Title contains duplicate words which may not be optimal.",
                recommendation="Consider using unique, descriptive words.",
                impact_score=10,
                fix_complexity="easy"
            )
            score -= 5
        
        return score, data, issues
    
    def _analyze_description(self, soup: BeautifulSoup) -> tuple:
        """Analyze meta description"""
        issues = []
        score = 100.0
        
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        
        if not desc_tag or not desc_tag.get('content'):
            self._add_issue(
                issues, IssueSeverity.ERROR,
                "Missing Meta Description",
                "The page doesn't have a meta description. This affects click-through rates.",
                recommendation=f"Add a compelling meta description between {self.DESC_MIN}-{self.DESC_MAX} characters.",
                impact_score=80,
                fix_complexity="easy"
            )
            return 0, {"present": False, "content": None, "length": 0}, issues
        
        desc_text = desc_tag.get('content', '').strip()
        desc_length = len(desc_text)
        
        data = {
            "present": True,
            "content": desc_text,
            "length": desc_length
        }
        
        # Check if empty
        if not desc_text:
            self._add_issue(
                issues, IssueSeverity.ERROR,
                "Empty Meta Description",
                "Meta description tag exists but is empty.",
                recommendation=f"Add a descriptive text between {self.DESC_MIN}-{self.DESC_MAX} characters.",
                impact_score=75,
                fix_complexity="easy"
            )
            score = 10
        
        # Check length
        elif desc_length < self.DESC_MIN:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "Meta Description Too Short",
                f"Description is only {desc_length} characters. Optimal is {self.DESC_MIN}-{self.DESC_MAX}.",
                recommendation="Expand your description to better entice users to click.",
                impact_score=50,
                fix_complexity="easy"
            )
            score = 60
        
        elif desc_length > self.DESC_MAX:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "Meta Description Too Long",
                f"Description is {desc_length} characters and will be truncated in search results.",
                recommendation=f"Shorten to {self.DESC_OPTIMAL} characters for best results.",
                impact_score=40,
                fix_complexity="easy"
            )
            score = 70
        
        else:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Meta Description Optimal",
                f"Description is {desc_length} characters - perfect!",
                impact_score=0
            )
        
        return score, data, issues
    
    def _analyze_canonical(self, soup: BeautifulSoup, url: str) -> tuple:
        """Analyze canonical URL"""
        issues = []
        score = 100.0
        
        canonical_tag = soup.find('link', attrs={'rel': 'canonical'})
        
        if not canonical_tag:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "Missing Canonical Tag",
                "No canonical URL specified. This may cause duplicate content issues.",
                recommendation="Add a <link rel='canonical'> tag to specify the preferred URL.",
                impact_score=50,
                fix_complexity="easy"
            )
            return 70, {"present": False, "href": None}, issues
        
        canonical_href = canonical_tag.get('href', '').strip()
        
        data = {
            "present": True,
            "href": canonical_href
        }
        
        if not canonical_href:
            self._add_issue(
                issues, IssueSeverity.ERROR,
                "Empty Canonical URL",
                "Canonical tag exists but href is empty.",
                recommendation="Specify a valid canonical URL.",
                impact_score=60,
                fix_complexity="easy"
            )
            score = 40
        else:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Canonical Tag Present",
                f"Canonical URL specified: {canonical_href}",
                impact_score=0
            )
        
        return score, data, issues
    
    def _analyze_robots(self, soup: BeautifulSoup) -> tuple:
        """Analyze robots meta tag"""
        issues = []
        score = 100.0
        
        robots_tag = soup.find('meta', attrs={'name': 'robots'})
        
        data = {
            "present": robots_tag is not None,
            "content": None,
            "noindex": False,
            "nofollow": False
        }
        
        if robots_tag:
            content = robots_tag.get('content', '').lower()
            data['content'] = content
            
            if 'noindex' in content:
                data['noindex'] = True
                self._add_issue(
                    issues, IssueSeverity.WARNING,
                    "Page Set to NOINDEX",
                    "This page is blocked from search engine indexing.",
                    recommendation="Remove 'noindex' if you want this page in search results.",
                    impact_score=90,
                    fix_complexity="easy"
                )
                score = 20
            
            if 'nofollow' in content:
                data['nofollow'] = True
                self._add_issue(
                    issues, IssueSeverity.WARNING,
                    "Links Set to NOFOLLOW",
                    "Search engines won't follow links on this page.",
                    recommendation="Remove 'nofollow' if appropriate.",
                    impact_score=40,
                    fix_complexity="easy"
                )
                score -= 20
        else:
            self._add_issue(
                issues, IssueSeverity.INFO,
                "No Robots Meta Tag",
                "No robots directive found (default: index, follow).",
                impact_score=0
            )
        
        return score, data, issues
    
    def _analyze_viewport(self, soup: BeautifulSoup) -> tuple:
        """Analyze viewport meta tag"""
        issues = []
        score = 100.0
        
        viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
        
        if not viewport_tag:
            self._add_issue(
                issues, IssueSeverity.ERROR,
                "Missing Viewport Tag",
                "No viewport meta tag found. Page may not be mobile-friendly.",
                recommendation="Add <meta name='viewport' content='width=device-width, initial-scale=1'>",
                impact_score=70,
                fix_complexity="easy"
            )
            return 30, {"present": False, "content": None}, issues
        
        content = viewport_tag.get('content', '')
        
        data = {
            "present": True,
            "content": content
        }
        
        if not content:
            self._add_issue(
                issues, IssueSeverity.ERROR,
                "Empty Viewport Content",
                "Viewport tag exists but content is empty.",
                recommendation="Add proper viewport configuration.",
                impact_score=65,
                fix_complexity="easy"
            )
            score = 40
        else:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Viewport Configured",
                "Viewport meta tag is present.",
                impact_score=0
            )
        
        return score, data, issues
    
    def _analyze_charset(self, soup: BeautifulSoup) -> tuple:
        """Analyze charset declaration"""
        issues = []
        score = 100.0
        
        charset_tag = soup.find('meta', attrs={'charset': True})
        
        if not charset_tag:
            # Check for http-equiv charset
            charset_tag = soup.find('meta', attrs={'http-equiv': 'Content-Type'})
        
        if not charset_tag:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "Missing Charset Declaration",
                "No character encoding specified.",
                recommendation="Add <meta charset='UTF-8'> at the top of <head>",
                impact_score=30,
                fix_complexity="easy"
            )
            return 60, {"present": False, "charset": None}, issues
        
        charset = charset_tag.get('charset', '').upper()
        if not charset and charset_tag.get('http-equiv'):
            content = charset_tag.get('content', '')
            if 'charset=' in content.lower():
                charset = content.split('charset=')[-1].strip().upper()
        
        data = {
            "present": True,
            "charset": charset
        }
        
        if charset and charset != 'UTF-8':
            self._add_issue(
                issues, IssueSeverity.INFO,
                f"Non-UTF-8 Charset: {charset}",
                "Page uses a character encoding other than UTF-8.",
                recommendation="Consider using UTF-8 for best compatibility.",
                impact_score=10,
                fix_complexity="medium"
            )
            score = 90
        else:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Charset Declared",
                f"Character encoding: {charset or 'specified'}",
                impact_score=0
            )
        
        return score, data, issues
    
    def _analyze_open_graph(self, soup: BeautifulSoup) -> tuple:
        """Analyze Open Graph meta tags"""
        issues = []
        score = 100.0
        
        og_tags = soup.find_all('meta', attrs={'property': lambda x: x and x.startswith('og:')})
        
        og_data = {}
        for tag in og_tags:
            prop = tag.get('property', '').replace('og:', '')
            content = tag.get('content', '')
            og_data[prop] = content
        
        data = {
            "present": len(og_tags) > 0,
            "tags": og_data
        }
        
        if not og_tags:
            self._add_issue(
                issues, IssueSeverity.INFO,
                "No Open Graph Tags",
                "No Open Graph meta tags found. Social sharing may not be optimized.",
                recommendation="Add og:title, og:description, og:image, og:url for better social media sharing.",
                impact_score=30,
                fix_complexity="easy"
            )
            return 60, data, issues
        
        # Check for essential OG tags
        essential = ['title', 'description', 'image', 'url']
        missing = [tag for tag in essential if tag not in og_data or not og_data[tag]]
        
        if missing:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "Incomplete Open Graph Tags",
                f"Missing essential OG tags: {', '.join(missing)}",
                recommendation="Add all essential Open Graph tags for optimal social sharing.",
                impact_score=20,
                fix_complexity="easy"
            )
            score = 70
        else:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Open Graph Tags Complete",
                "All essential Open Graph tags are present.",
                impact_score=0
            )
        
        return score, data, issues
    
    def _analyze_twitter_cards(self, soup: BeautifulSoup) -> tuple:
        """Analyze Twitter Card meta tags"""
        issues = []
        score = 100.0
        
        twitter_tags = soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})
        
        twitter_data = {}
        for tag in twitter_tags:
            name = tag.get('name', '').replace('twitter:', '')
            content = tag.get('content', '')
            twitter_data[name] = content
        
        data = {
            "present": len(twitter_tags) > 0,
            "tags": twitter_data
        }
        
        if not twitter_tags:
            self._add_issue(
                issues, IssueSeverity.INFO,
                "No Twitter Card Tags",
                "No Twitter Card meta tags found. Twitter sharing may not be optimized.",
                recommendation="Add twitter:card, twitter:title, twitter:description for better Twitter visibility.",
                impact_score=20,
                fix_complexity="easy"
            )
            return 70, data, issues
        
        # Check for essential Twitter tags
        if 'card' not in twitter_data:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                "Missing Twitter Card Type",
                "twitter:card meta tag not specified.",
                recommendation="Add twitter:card with value 'summary_large_image' or 'summary'.",
                impact_score=15,
                fix_complexity="easy"
            )
            score = 80
        else:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Twitter Card Configured",
                f"Twitter Card type: {twitter_data['card']}",
                impact_score=0
            )
        
        return score, data, issues

