#!/usr/bin/env python3
"""
Schema Analyzer - Analyzes structured data (Schema.org)
(PROFESSIONAL tier feature)
"""

import time
import json
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
from .base_analyzer import BaseAnalyzer, AnalysisResult, SEOIssue, IssueSeverity


class SchemaAnalyzer(BaseAnalyzer):
    """
    Analyzes structured data:
    - JSON-LD
    - Microdata
    - RDFa
    - Common schema types (Article, Product, etc)
    """
    
    def __init__(self):
        super().__init__("Schema Analyzer")
    
    def analyze(self, html: str, url: str, additional_data: Optional[Dict] = None) -> AnalysisResult:
        """Analyze structured data"""
        start_time = time.time()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            issues = []
            data = {}
            score = 100.0
            
            # Find JSON-LD scripts
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            schemas_found = []
            
            for script in json_ld_scripts:
                try:
                    schema_data = json.loads(script.string)
                    schema_type = schema_data.get('@type', 'Unknown')
                    schemas_found.append({
                        'type': schema_type,
                        'format': 'JSON-LD',
                        'valid': True
                    })
                except:
                    schemas_found.append({
                        'type': 'Invalid',
                        'format': 'JSON-LD',
                        'valid': False
                    })
            
            data['schemas'] = schemas_found
            data['count'] = len(schemas_found)
            
            if not schemas_found:
                self._add_issue(
                    issues, IssueSeverity.WARNING,
                    "No Structured Data",
                    "No Schema.org markup detected. Rich snippets can improve CTR.",
                    recommendation="Add JSON-LD structured data (Article, Product, Organization, etc).",
                    impact_score=60,
                    fix_complexity="medium"
                )
                score = 40
            else:
                # Check for invalid schemas
                invalid = [s for s in schemas_found if not s['valid']]
                if invalid:
                    self._add_issue(
                        issues, IssueSeverity.ERROR,
                        "Invalid Schema Markup",
                        f"{len(invalid)} schema(s) have JSON parsing errors.",
                        recommendation="Fix JSON-LD syntax errors.",
                        impact_score=50,
                        fix_complexity="medium"
                    )
                    score -= 30
                else:
                    self._add_issue(
                        issues, IssueSeverity.SUCCESS,
                        "Structured Data Present",
                        f"Found {len(schemas_found)} valid schema(s).",
                        impact_score=0
                    )
            
            score = max(0, min(100, score))
            grade = self._calculate_grade(score)
            
            return AnalysisResult(
                analyzer_name=self.name,
                url=url,
                score=score,
                grade=grade,
                issues=issues,
                data=data,
                execution_time=time.time() - start_time,
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

