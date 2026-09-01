#!/usr/bin/env python3
"""
Link Analyzer
Analyzes internal and external links
"""

from bs4 import BeautifulSoup
from typing import Dict, Any, List
from urllib.parse import urlparse
from .base_analyzer import BaseAnalyzer


class LinkAnalyzer(BaseAnalyzer):
    """Analyzer for links"""
    
    def analyze(self, html: str, url: str) -> Dict[str, Any]:
        """Analyze links in HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        issues = []
        score = 100
        
        links = soup.find_all('a', href=True)
        total_links = len(links)
        
        if total_links == 0:
            issues.append({
                "type": "warning",
                "message": "No se encontraron enlaces en la página",
                "element": "a"
            })
            return self.create_result(80, issues, ["Añade enlaces internos y externos relevantes"])
        
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        internal_links = 0
        external_links = 0
        broken_links = 0
        links_without_text = 0
        nofollow_links = 0
        
        for link in links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            rel = link.get('rel', [])
            
            # Check if link has text
            if not link_text and not link.find('img'):
                links_without_text += 1
                issues.append({
                    "type": "warning",
                    "message": "Enlace sin texto descriptivo",
                    "element": "a",
                    "href": href[:50]
                })
            
            # Check if it's internal or external
            if href.startswith('http'):
                link_domain = urlparse(href).netloc
                if link_domain == domain:
                    internal_links += 1
                else:
                    external_links += 1
            elif href.startswith('/') or not href.startswith('#'):
                internal_links += 1
            
            # Check nofollow
            if 'nofollow' in rel:
                nofollow_links += 1
            
            # Check for common broken link patterns
            if href in ['#', '', 'javascript:void(0)', 'javascript:;']:
                broken_links += 1
                issues.append({
                    "type": "error",
                    "message": f"Enlace potencialmente roto: '{href}'",
                    "element": "a",
                    "text": link_text[:30]
                })
        
        # Calculate score
        if links_without_text > 0:
            score -= min(20, links_without_text * 5)
        if broken_links > 0:
            score -= min(30, broken_links * 10)
        if external_links > 0 and internal_links == 0:
            issues.append({
                "type": "warning",
                "message": "Solo hay enlaces externos, considera añadir enlaces internos",
                "element": "a"
            })
            score -= 15
        
        # Add statistics
        issues.append({
            "type": "info",
            "message": f"Estadísticas: {internal_links} internos, {external_links} externos, {nofollow_links} nofollow",
            "element": "summary"
        })
        
        recommendations = []
        if links_without_text > 0:
            recommendations.append("Añade texto descriptivo a todos los enlaces")
        if broken_links > 0:
            recommendations.append("Corrige o elimina los enlaces rotos")
        if internal_links < 3:
            recommendations.append("Añade más enlaces internos para mejorar la navegación")
        if external_links > internal_links * 2:
            recommendations.append("Equilibra el ratio de enlaces internos vs externos")
        
        return self.create_result(max(0, score), issues, recommendations)
