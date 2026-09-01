#!/usr/bin/env python3
"""
Image Analyzer - Analyzes images for SEO optimization
"""

import time
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .base_analyzer import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity


class ImageAnalyzer(BaseAnalyzer):
    """
    Analyzes images for SEO:
    - Alt text presence and quality
    - Image file names
    - Image formats
    - Broken images
    - Image count
    """
    
    def __init__(self):
        super().__init__("Image Analyzer")
    
    def analyze(self, html: str, url: str, additional_data: Optional[Dict] = None) -> AnalysisResult:
        """Analyze images in HTML"""
        start_time = time.time()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            issues = []
            data = {}
            score = 100.0
            
            # Extract all images
            images = self._extract_images(soup, url)
            data['images'] = images
            data['total_count'] = len(images)
            
            if not images:
                self._add_issue(
                    issues, IssueSeverity.INFO,
                    "No Images Found",
                    "Page has no images. Visual content can improve engagement.",
                    recommendation="Consider adding relevant images to enhance content.",
                    impact_score=20,
                    fix_complexity="medium"
                )
                return AnalysisResult(
                    analyzer_name=self.name,
                    url=url,
                    score=70,
                    grade="C",
                    issues=issues,
                    data=data,
                    execution_time=time.time() - start_time,
                    success=True
                )
            
            # Analyze alt text
            alt_score, alt_issues = self._analyze_alt_text(images)
            issues.extend(alt_issues)
            score -= (100 - alt_score) * 0.50  # Alt text is 50% of image score
            
            # Analyze file names
            filename_score, filename_issues = self._analyze_filenames(images)
            issues.extend(filename_issues)
            score -= (100 - filename_score) * 0.20  # Filenames are 20%
            
            # Analyze formats
            format_score, format_issues = self._analyze_formats(images)
            issues.extend(format_issues)
            score -= (100 - format_score) * 0.20  # Formats are 20%
            
            # Analyze broken images
            broken_score, broken_issues = self._analyze_broken_images(images)
            issues.extend(broken_issues)
            score -= (100 - broken_score) * 0.10  # Broken images are 10%
            
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
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract all images with metadata"""
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            title = img.get('title', '')
            
            # Get filename from src
            filename = ''
            if src:
                parsed = urlparse(src)
                filename = parsed.path.split('/')[-1] if parsed.path else ''
            
            # Detect format from extension
            format = 'unknown'
            if filename:
                ext = filename.split('.')[-1].lower() if '.' in filename else ''
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'ico']:
                    format = ext
            
            images.append({
                'src': src,
                'alt': alt,
                'title': title,
                'filename': filename,
                'format': format,
                'has_alt': bool(alt),
                'alt_length': len(alt) if alt else 0
            })
        
        return images
    
    def _analyze_alt_text(self, images: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Analyze alt text"""
        issues = []
        score = 100.0
        
        total = len(images)
        missing_alt = [img for img in images if not img['has_alt']]
        empty_alt = [img for img in images if img['has_alt'] and img['alt_length'] == 0]
        short_alt = [img for img in images if img['has_alt'] and 0 < img['alt_length'] < 5]
        
        if missing_alt:
            percentage = (len(missing_alt) / total) * 100
            self._add_issue(
                issues, IssueSeverity.ERROR if percentage > 50 else IssueSeverity.WARNING,
                f"Missing Alt Text ({len(missing_alt)} images)",
                f"{len(missing_alt)} out of {total} images ({percentage:.1f}%) don't have alt text.",
                recommendation="Add descriptive alt text to all images for accessibility and SEO.",
                impact_score=80,
                fix_complexity="easy"
            )
            score -= (len(missing_alt) / total) * 50
        
        if empty_alt:
            self._add_issue(
                issues, IssueSeverity.WARNING,
                f"Empty Alt Text ({len(empty_alt)} images)",
                f"{len(empty_alt)} image(s) have alt attribute but it's empty.",
                recommendation="Add descriptive text to empty alt attributes.",
                impact_score=40,
                fix_complexity="easy"
            )
            score -= (len(empty_alt) / total) * 30
        
        if short_alt:
            self._add_issue(
                issues, IssueSeverity.INFO,
                f"Very Short Alt Text ({len(short_alt)} images)",
                f"{len(short_alt)} image(s) have alt text under 5 characters.",
                recommendation="Make alt text more descriptive (aim for 5-125 characters).",
                impact_score=20,
                fix_complexity="easy"
            )
            score -= (len(short_alt) / total) * 10
        
        if not missing_alt and not empty_alt:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "All Images Have Alt Text",
                f"All {total} images have alt text - excellent!",
                impact_score=0
            )
        
        return score, issues
    
    def _analyze_filenames(self, images: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Analyze image filenames"""
        issues = []
        score = 100.0
        
        generic_names = ['image', 'img', 'photo', 'picture', 'untitled', 'screenshot']
        poor_filenames = []
        
        for img in images:
            filename = img['filename'].lower()
            name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
            
            # Check for generic names
            if any(generic in name_without_ext for generic in generic_names):
                poor_filenames.append(img)
            # Check for random/generated names (e.g., IMG_1234.jpg)
            elif name_without_ext.replace('_', '').replace('-', '').isdigit():
                poor_filenames.append(img)
        
        if poor_filenames:
            percentage = (len(poor_filenames) / len(images)) * 100
            self._add_issue(
                issues, IssueSeverity.INFO,
                f"Non-Descriptive Filenames ({len(poor_filenames)} images)",
                f"{len(poor_filenames)} image(s) ({percentage:.1f}%) have generic filenames.",
                recommendation="Use descriptive, keyword-rich filenames (e.g., 'blue-running-shoes.jpg').",
                impact_score=25,
                fix_complexity="medium"
            )
            score -= (len(poor_filenames) / len(images)) * 40
        else:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Descriptive Filenames",
                "Image filenames appear to be descriptive.",
                impact_score=0
            )
        
        return score, issues
    
    def _analyze_formats(self, images: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Analyze image formats"""
        issues = []
        score = 100.0
        
        formats = {}
        for img in images:
            format = img['format']
            formats[format] = formats.get(format, 0) + 1
        
        # Check for modern formats
        total = len(images)
        legacy_formats = formats.get('jpg', 0) + formats.get('jpeg', 0) + formats.get('png', 0)
        modern_formats = formats.get('webp', 0)
        
        if legacy_formats > 0 and modern_formats == 0:
            self._add_issue(
                issues, IssueSeverity.INFO,
                "Consider Modern Formats",
                f"Using traditional formats (JPG/PNG). WebP can reduce file size by 25-35%.",
                recommendation="Consider converting images to WebP format for better performance.",
                impact_score=30,
                fix_complexity="medium"
            )
            score -= 15
        
        if modern_formats > 0:
            self._add_issue(
                issues, IssueSeverity.SUCCESS,
                "Using Modern Formats",
                f"{modern_formats} image(s) use modern WebP format.",
                impact_score=0
            )
        
        return score, issues
    
    def _analyze_broken_images(self, images: List[Dict]) -> Tuple[float, List[SEOIssue]]:
        """Analyze for broken image links"""
        issues = []
        score = 100.0
        
        missing_src = [img for img in images if not img['src'] or img['src'].strip() == '']
        
        if missing_src:
            self._add_issue(
                issues, IssueSeverity.ERROR,
                f"Images with Missing Src ({len(missing_src)})",
                f"{len(missing_src)} image(s) have no src attribute.",
                recommendation="Ensure all <img> tags have a valid src attribute.",
                impact_score=70,
                fix_complexity="easy"
            )
            score -= (len(missing_src) / len(images)) * 80
        
        return score, issues

