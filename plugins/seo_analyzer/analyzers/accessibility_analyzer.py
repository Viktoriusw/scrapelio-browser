#!/usr/bin/env python3
"""
Accessibility Analyzer
Analyzes accessibility features
"""

from bs4 import BeautifulSoup
from typing import Dict, Any, List
from .base_analyzer import BaseAnalyzer


class AccessibilityAnalyzer(BaseAnalyzer):
    """Analyzer for accessibility"""
    
    def analyze(self, html: str, url: str) -> Dict[str, Any]:
        """Analyze accessibility features"""
        soup = BeautifulSoup(html, 'html.parser')
        issues = []
        score = 100
        
        # Check lang attribute
        html_tag = soup.find('html')
        if not html_tag or not html_tag.get('lang'):
            issues.append({
                "type": "error",
                "message": "Falta atributo lang en <html>",
                "element": "html"
            })
            score -= 15
        
        # Check for semantic HTML5 elements
        semantic_elements = ['header', 'nav', 'main', 'article', 'section', 'aside', 'footer']
        found_semantic = []
        
        for element in semantic_elements:
            if soup.find(element):
                found_semantic.append(element)
        
        if len(found_semantic) < 3:
            issues.append({
                "type": "warning",
                "message": f"Pocos elementos semánticos HTML5 (encontrados: {len(found_semantic)})",
                "element": "semantic"
            })
            score -= 10
        
        # Check for ARIA labels
        elements_with_aria = soup.find_all(attrs={"aria-label": True})
        buttons = soup.find_all('button')
        links = soup.find_all('a')
        
        # Check buttons without accessible names
        buttons_without_text = 0
        for button in buttons:
            text = button.get_text(strip=True)
            has_aria = button.get('aria-label') or button.get('aria-labelledby')
            if not text and not has_aria and not button.find('img'):
                buttons_without_text += 1
        
        if buttons_without_text > 0:
            issues.append({
                "type": "error",
                "message": f"{buttons_without_text} botones sin texto accesible",
                "element": "button"
            })
            score -= 20
        
        # Check for form labels
        inputs = soup.find_all('input', type=lambda x: x not in ['hidden', 'submit', 'button'])
        inputs_without_label = 0
        
        for input_elem in inputs:
            input_id = input_elem.get('id')
            has_label = False
            
            if input_id:
                has_label = bool(soup.find('label', attrs={'for': input_id}))
            
            has_aria = input_elem.get('aria-label') or input_elem.get('aria-labelledby')
            
            if not has_label and not has_aria:
                inputs_without_label += 1
        
        if inputs_without_label > 0:
            issues.append({
                "type": "error",
                "message": f"{inputs_without_label} campos de formulario sin label",
                "element": "input"
            })
            score -= 20
        
        # Check for skip navigation link
        skip_link = soup.find('a', href='#main') or soup.find('a', href='#content')
        if not skip_link:
            issues.append({
                "type": "info",
                "message": "No se encontró enlace 'skip to main content'",
                "element": "a[href=#main]"
            })
            score -= 5
        
        # Check color contrast (basic check for inline styles)
        elements_with_color = soup.find_all(style=lambda x: x and 'color' in x)
        if len(elements_with_color) > 10:
            issues.append({
                "type": "info",
                "message": "Muchos estilos inline de color (verifica contraste manualmente)",
                "element": "style"
            })
        
        recommendations = []
        if not html_tag or not html_tag.get('lang'):
            recommendations.append("Añade atributo lang al elemento <html>")
        if len(found_semantic) < 3:
            recommendations.append("Usa más elementos semánticos HTML5 (header, nav, main, footer)")
        if buttons_without_text > 0:
            recommendations.append("Añade texto o aria-label a todos los botones")
        if inputs_without_label > 0:
            recommendations.append("Asocia labels a todos los campos de formulario")
        if not skip_link:
            recommendations.append("Añade un enlace 'skip to main content' al inicio")
        
        return self.create_result(max(0, score), issues, recommendations)
