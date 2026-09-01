#!/usr/bin/env python3
"""
Heading Structure Analyzer
Analyzes H1-H6 heading structure
"""

from bs4 import BeautifulSoup
from typing import Dict, Any, List
from .base_analyzer import BaseAnalyzer


class HeadingAnalyzer(BaseAnalyzer):
    """Analyzer for heading structure"""
    
    def analyze(self, html: str, url: str) -> Dict[str, Any]:
        """Analyze heading structure"""
        soup = BeautifulSoup(html, 'html.parser')
        issues = []
        score = 100
        
        # Count headings
        h1_tags = soup.find_all('h1')
        h2_tags = soup.find_all('h2')
        h3_tags = soup.find_all('h3')
        h4_tags = soup.find_all('h4')
        h5_tags = soup.find_all('h5')
        h6_tags = soup.find_all('h6')
        
        # Check H1
        if len(h1_tags) == 0:
            issues.append({
                "type": "error",
                "message": "No se encontró ningún H1",
                "element": "h1"
            })
            score -= 30
        elif len(h1_tags) > 1:
            issues.append({
                "type": "warning",
                "message": f"Se encontraron {len(h1_tags)} H1 (recomendado: 1)",
                "element": "h1",
                "count": len(h1_tags)
            })
            score -= 15
        else:
            # Check H1 length
            h1_text = h1_tags[0].get_text(strip=True)
            if len(h1_text) < 20 or len(h1_text) > 70:
                issues.append({
                    "type": "info",
                    "message": f"H1 tiene {len(h1_text)} caracteres (óptimo: 20-70)",
                    "element": "h1",
                    "value": h1_text
                })
                score -= 5
        
        # Check heading hierarchy
        all_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        prev_level = 0
        
        for heading in all_headings:
            current_level = int(heading.name[1])
            
            if current_level > prev_level + 1 and prev_level > 0:
                issues.append({
                    "type": "warning",
                    "message": f"Salto en jerarquía: de H{prev_level} a H{current_level}",
                    "element": heading.name,
                    "value": heading.get_text(strip=True)[:50]
                })
                score -= 5
            
            prev_level = current_level
        
        # Check empty headings
        for heading in all_headings:
            text = heading.get_text(strip=True)
            if not text:
                issues.append({
                    "type": "error",
                    "message": f"{heading.name.upper()} vacío",
                    "element": heading.name
                })
                score -= 10
        
        recommendations = []
        if len(h1_tags) == 0:
            recommendations.append("Añade un H1 descriptivo que resuma el contenido principal")
        elif len(h1_tags) > 1:
            recommendations.append("Usa solo un H1 por página")
        
        if len(h2_tags) == 0 and len(all_headings) > 1:
            recommendations.append("Considera añadir H2 para estructurar mejor el contenido")
        
        # Check if there were any hierarchy jumps detected
        hierarchy_issues = [issue for issue in issues if "Salto en jerarquía" in issue.get("message", "")]
        if hierarchy_issues:
            recommendations.append("Mantén una jerarquía lógica en los headings (H1 > H2 > H3...)")
        
        return self.create_result(max(0, score), issues, recommendations)
