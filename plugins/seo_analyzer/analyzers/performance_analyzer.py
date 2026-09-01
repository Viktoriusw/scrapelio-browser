#!/usr/bin/env python3
"""
Performance Analyzer
Analyzes page performance metrics
"""

from bs4 import BeautifulSoup
from typing import Dict, Any, List
from .base_analyzer import BaseAnalyzer


class PerformanceAnalyzer(BaseAnalyzer):
    """Analyzer for performance metrics"""
    
    def analyze(self, html: str, url: str) -> Dict[str, Any]:
        """Analyze performance aspects"""
        soup = BeautifulSoup(html, 'html.parser')
        issues = []
        score = 100
        
        # HTML size
        html_size = len(html)
        html_size_kb = html_size / 1024
        
        if html_size_kb > 500:
            issues.append({
                "type": "error",
                "message": f"HTML muy grande: {html_size_kb:.2f} KB (óptimo: < 100 KB)",
                "element": "html"
            })
            score -= 30
        elif html_size_kb > 200:
            issues.append({
                "type": "warning",
                "message": f"HTML grande: {html_size_kb:.2f} KB (óptimo: < 100 KB)",
                "element": "html"
            })
            score -= 15
        
        # Count resources
        scripts = soup.find_all('script', src=True)
        stylesheets = soup.find_all('link', rel='stylesheet')
        images = soup.find_all('img')
        
        total_scripts = len(scripts)
        total_stylesheets = len(stylesheets)
        total_images = len(images)
        
        # Check inline scripts/styles
        inline_scripts = len(soup.find_all('script', src=False))
        inline_styles = len(soup.find_all('style'))
        
        if total_scripts > 15:
            issues.append({
                "type": "warning",
                "message": f"{total_scripts} archivos JavaScript (considera minificar/combinar)",
                "element": "script"
            })
            score -= 10
        
        if total_stylesheets > 10:
            issues.append({
                "type": "warning",
                "message": f"{total_stylesheets} hojas de estilo (considera minificar/combinar)",
                "element": "link[rel=stylesheet]"
            })
            score -= 10
        
        if inline_scripts > 5:
            issues.append({
                "type": "info",
                "message": f"{inline_scripts} scripts inline (considera externalizarlos)",
                "element": "script[inline]"
            })
            score -= 5
        
        if inline_styles > 3:
            issues.append({
                "type": "info",
                "message": f"{inline_styles} estilos inline (considera externalizarlos)",
                "element": "style"
            })
            score -= 5
        
        # Check for render-blocking resources
        render_blocking_scripts = 0
        for script in scripts:
            if not script.get('async') and not script.get('defer'):
                render_blocking_scripts += 1
        
        if render_blocking_scripts > 0:
            issues.append({
                "type": "warning",
                "message": f"{render_blocking_scripts} scripts bloqueantes (usa async/defer)",
                "element": "script"
            })
            score -= 15
        
        # Check for lazy loading
        images_with_loading = sum(1 for img in images if img.get('loading') == 'lazy')
        if total_images > 10 and images_with_loading < total_images * 0.5:
            issues.append({
                "type": "info",
                "message": "Pocas imágenes usan lazy loading",
                "element": "img"
            })
            score -= 5
        
        recommendations = []
        if html_size_kb > 200:
            recommendations.append("Reduce el tamaño del HTML (minifica, elimina código innecesario)")
        if total_scripts > 10:
            recommendations.append("Combina y minifica los archivos JavaScript")
        if total_stylesheets > 5:
            recommendations.append("Combina y minifica las hojas de estilo CSS")
        if render_blocking_scripts > 0:
            recommendations.append("Usa async o defer en scripts no críticos")
        if total_images > 10 and images_with_loading == 0:
            recommendations.append("Implementa lazy loading en las imágenes")
        
        # Add metrics summary
        issues.append({
            "type": "info",
            "message": f"Métricas: HTML {html_size_kb:.1f}KB | {total_scripts} JS | {total_stylesheets} CSS | {total_images} imágenes",
            "element": "summary"
        })
        
        return self.create_result(max(0, score), issues, recommendations)
