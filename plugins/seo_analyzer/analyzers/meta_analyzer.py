#!/usr/bin/env python3
"""
Meta Tags Analyzer
Analyzes meta tags for SEO optimization
"""

from bs4 import BeautifulSoup
from typing import Dict, Any, List
from .base_analyzer import BaseAnalyzer


class MetaAnalyzer(BaseAnalyzer):
    """Analyzer for meta tags"""
    
    def analyze(self, html: str, url: str) -> Dict[str, Any]:
        """Analyze meta tags in HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        issues = []
        score = 100
        
        # Check title tag
        title = soup.find('title')
        if not title or not title.string:
            issues.append({
                "type": "error",
                "message": "Falta el tag <title>",
                "element": "title"
            })
            score -= 20
        elif len(title.string) < 30 or len(title.string) > 60:
            issues.append({
                "type": "warning",
                "message": f"El título tiene {len(title.string)} caracteres (óptimo: 30-60)",
                "element": "title",
                "value": title.string
            })
            score -= 10
        
        # Check meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc or not meta_desc.get('content'):
            issues.append({
                "type": "error",
                "message": "Falta meta description",
                "element": "meta[name=description]"
            })
            score -= 20
        elif len(meta_desc.get('content', '')) < 120 or len(meta_desc.get('content', '')) > 160:
            issues.append({
                "type": "warning",
                "message": f"Meta description tiene {len(meta_desc.get('content', ''))} caracteres (óptimo: 120-160)",
                "element": "meta[name=description]",
                "value": meta_desc.get('content', '')[:100]
            })
            score -= 10
        
        # Check meta robots
        meta_robots = soup.find('meta', attrs={'name': 'robots'})
        robots_content = meta_robots.get('content', '') if meta_robots else ''
        
        if 'noindex' in robots_content:
            issues.append({
                "type": "warning",
                "message": "La página tiene noindex (no será indexada)",
                "element": "meta[name=robots]",
                "value": robots_content
            })
        
        # Check Open Graph tags
        og_title = soup.find('meta', property='og:title')
        og_description = soup.find('meta', property='og:description')
        og_image = soup.find('meta', property='og:image')
        
        if not og_title:
            issues.append({
                "type": "info",
                "message": "Falta Open Graph title (og:title)",
                "element": "meta[property=og:title]"
            })
            score -= 5
        
        if not og_description:
            issues.append({
                "type": "info",
                "message": "Falta Open Graph description (og:description)",
                "element": "meta[property=og:description]"
            })
            score -= 5
            
        if not og_image:
            issues.append({
                "type": "info",
                "message": "Falta Open Graph image (og:image)",
                "element": "meta[property=og:image]"
            })
            score -= 5
        
        # Check Twitter Card
        twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
        if not twitter_card:
            issues.append({
                "type": "info",
                "message": "Falta Twitter Card meta tag",
                "element": "meta[name=twitter:card]"
            })
            score -= 5
        
        recommendations = []
        if score < 100:
            if not title or not title.string:
                recommendations.append("Añade un tag <title> descriptivo y único")
            if not meta_desc:
                recommendations.append("Añade una meta description atractiva")
            if not og_title or not og_description or not og_image:
                recommendations.append("Completa los Open Graph tags para mejorar compartición en redes sociales")
            if not twitter_card:
                recommendations.append("Añade Twitter Card meta tags")
        
        return self.create_result(max(0, score), issues, recommendations)
