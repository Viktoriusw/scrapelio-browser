#!/usr/bin/env python3
"""
Image Analyzer
Analyzes images for SEO optimization
"""

from bs4 import BeautifulSoup
from typing import Dict, Any, List
from .base_analyzer import BaseAnalyzer
import re


class ImageAnalyzer(BaseAnalyzer):
    """Analyzer for images"""
    
    def analyze(self, html: str, url: str) -> Dict[str, Any]:
        """Analyze images in HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        issues = []
        score = 100
        
        images = soup.find_all('img')
        total_images = len(images)
        
        if total_images == 0:
            return self.create_result(100, [], ["No se encontraron imágenes en la página"])
        
        images_without_alt = 0
        images_with_empty_alt = 0
        images_with_short_alt = 0
        images_without_dimensions = 0
        
        for img in images:
            img_src = img.get('src', '')
            
            # Check alt attribute
            if not img.has_attr('alt'):
                images_without_alt += 1
                issues.append({
                    "type": "error",
                    "message": "Imagen sin atributo alt",
                    "element": "img",
                    "src": img_src[:50]
                })
            elif not img['alt']:
                images_with_empty_alt += 1
                issues.append({
                    "type": "warning",
                    "message": "Imagen con alt vacío",
                    "element": "img",
                    "src": img_src[:50]
                })
            elif len(img['alt']) < 5:
                images_with_short_alt += 1
                issues.append({
                    "type": "info",
                    "message": f"Alt text muy corto: '{img['alt']}'",
                    "element": "img",
                    "src": img_src[:50]
                })
            
            # Check dimensions
            if not img.has_attr('width') or not img.has_attr('height'):
                images_without_dimensions += 1
        
        # Calculate score
        if images_without_alt > 0:
            score -= min(30, images_without_alt * 10)
        if images_with_empty_alt > 0:
            score -= min(20, images_with_empty_alt * 5)
        if images_with_short_alt > 0:
            score -= min(10, images_with_short_alt * 2)
        if images_without_dimensions > total_images * 0.5:
            issues.append({
                "type": "info",
                "message": f"{images_without_dimensions} imágenes sin width/height definidos",
                "element": "img"
            })
            score -= 10
        
        recommendations = []
        if images_without_alt > 0:
            recommendations.append(f"Añade atributo alt descriptivo a {images_without_alt} imagen(es)")
        if images_with_empty_alt > 0:
            recommendations.append(f"Completa el alt text de {images_with_empty_alt} imagen(es)")
        if images_with_short_alt > 0:
            recommendations.append("Usa alt text más descriptivos (mínimo 5 caracteres)")
        if images_without_dimensions > total_images * 0.3:
            recommendations.append("Define width y height en las imágenes para evitar CLS")
        
        return self.create_result(max(0, score), issues, recommendations)
