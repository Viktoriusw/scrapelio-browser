#!/usr/bin/env python3
"""
Schema Markup Analyzer
Analyzes structured data (JSON-LD, Microdata)
"""

from bs4 import BeautifulSoup
from typing import Dict, Any, List
import json
from .base_analyzer import BaseAnalyzer


class SchemaAnalyzer(BaseAnalyzer):
    """Analyzer for schema markup"""
    
    def analyze(self, html: str, url: str) -> Dict[str, Any]:
        """Analyze schema markup"""
        soup = BeautifulSoup(html, 'html.parser')
        issues = []
        score = 100
        
        # Find JSON-LD schemas
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        schemas_found = []
        
        for script in json_ld_scripts:
            try:
                schema_data = json.loads(script.string)
                schema_type = schema_data.get('@type', 'Unknown')
                schemas_found.append(schema_type)
            except (json.JSONDecodeError, AttributeError):
                issues.append({
                    "type": "error",
                    "message": "JSON-LD inválido encontrado",
                    "element": "script[type='application/ld+json']"
                })
                score -= 15
        
        # Check common schema types
        if len(schemas_found) == 0:
            issues.append({
                "type": "warning",
                "message": "No se encontró Schema markup (JSON-LD)",
                "element": "schema"
            })
            score -= 30
        else:
            issues.append({
                "type": "info",
                "message": f"Schemas encontrados: {', '.join(schemas_found)}",
                "element": "schema"
            })
        
        # Check for microdata
        items_with_itemscope = soup.find_all(attrs={"itemscope": True})
        if items_with_itemscope:
            issues.append({
                "type": "info",
                "message": f"Microdata encontrado: {len(items_with_itemscope)} elementos con itemscope",
                "element": "microdata"
            })
        
        # Recommendations based on missing schemas
        recommendations = []
        if len(schemas_found) == 0:
            recommendations.append("Añade Schema markup (JSON-LD) para mejorar rich snippets")
            recommendations.append("Tipos recomendados: Organization, WebSite, Article, BreadcrumbList")
        
        common_schemas = ['Organization', 'WebSite', 'Article', 'BreadcrumbList']
        missing_schemas = [s for s in common_schemas if s not in schemas_found]
        
        if missing_schemas and len(schemas_found) > 0:
            recommendations.append(f"Considera añadir: {', '.join(missing_schemas)}")
        
        return self.create_result(max(0, score), issues, recommendations)
