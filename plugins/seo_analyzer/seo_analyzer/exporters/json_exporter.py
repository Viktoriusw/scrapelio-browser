#!/usr/bin/env python3
"""
JSON Exporter - Exports SEO analysis to JSON format
"""

import json
from datetime import datetime
from typing import Dict, Any


class JSONExporter:
    """Export SEO analysis results to JSON"""
    
    @staticmethod
    def export(results: Dict[str, Any], filepath: str = None) -> str:
        """
        Export results to JSON
        
        Args:
            results: Analysis results dictionary
            filepath: Optional file path to save to
            
        Returns:
            str: JSON string
        """
        # Convert AnalysisResult objects to dicts
        export_data = JSONExporter._prepare_data(results)
        
        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)
        
        return json_str
    
    @staticmethod
    def _prepare_data(results: Dict[str, Any]) -> Dict:
        """Prepare data for JSON serialization"""
        export_data = {
            'url': results.get('url', ''),
            'timestamp': results.get('timestamp', datetime.now().isoformat()),
            'overall_score': results.get('overall_score', 0),
            'overall_grade': results.get('overall_grade', 'F'),
            'total_issues': results.get('total_issues', 0),
            'critical_issues': results.get('critical_issues', 0),
            'execution_time': results.get('execution_time', 0),
            'analyzers': {}
        }
        
        # Convert analyzer results
        for name, result in results.get('analyzers', {}).items():
            if hasattr(result, 'to_dict'):
                export_data['analyzers'][name] = result.to_dict()
            else:
                export_data['analyzers'][name] = str(result)
        
        return export_data

