#!/usr/bin/env python3
"""
JSON Exporter
Exports SEO analysis results to JSON format
"""

import json
from typing import Dict, Any
from datetime import datetime


class JSONExporter:
    """Exporter for JSON format"""
    
    def export(self, results: Dict[str, Any], url: str, filepath: str) -> bool:
        """
        Export results to JSON file
        
        Args:
            results: Analysis results dictionary
            url: URL that was analyzed
            filepath: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            export_data = {
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "analysis": results
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False
    
    def export_string(self, results: Dict[str, Any], url: str) -> str:
        """Export results to JSON string"""
        export_data = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "analysis": results
        }
        return json.dumps(export_data, indent=2, ensure_ascii=False)
