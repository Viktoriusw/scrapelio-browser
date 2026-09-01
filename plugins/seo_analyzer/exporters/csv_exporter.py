#!/usr/bin/env python3
"""
CSV Exporter
Exports SEO analysis results to CSV format
"""

import csv
from typing import Dict, Any, List
from datetime import datetime


class CSVExporter:
    """Exporter for CSV format"""
    
    def export(self, results: Dict[str, Any], url: str, filepath: str) -> bool:
        """
        Export results to CSV file
        
        Args:
            results: Analysis results dictionary
            url: URL that was analyzed
            filepath: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            rows = []
            rows.append(['SEO Analysis Report'])
            rows.append(['URL', url])
            rows.append(['Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            rows.append([])
            
            # Add results for each analyzer
            for analyzer_name, analyzer_results in results.items():
                rows.append([f'=== {analyzer_name.upper()} ==='])
                rows.append(['Score', analyzer_results.get('score', 'N/A')])
                rows.append(['Severity', analyzer_results.get('severity', 'N/A')])
                rows.append([])
                
                # Add issues
                issues = analyzer_results.get('issues', [])
                if issues:
                    rows.append(['Type', 'Message', 'Element', 'Details'])
                    for issue in issues:
                        rows.append([
                            issue.get('type', ''),
                            issue.get('message', ''),
                            issue.get('element', ''),
                            str(issue.get('value', issue.get('src', issue.get('href', ''))))[:50]
                        ])
                    rows.append([])
                
                # Add recommendations
                recommendations = analyzer_results.get('recommendations', [])
                if recommendations:
                    rows.append(['Recomendaciones'])
                    for rec in recommendations:
                        rows.append(['', rec])
                    rows.append([])
                
                rows.append([])
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            
            return True
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False
    
    def export_string(self, results: Dict[str, Any], url: str) -> str:
        """Export results to CSV string"""
        import io
        output = io.StringIO()
        
        writer = csv.writer(output)
        writer.writerow(['SEO Analysis Report'])
        writer.writerow(['URL', url])
        writer.writerow(['Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        for analyzer_name, analyzer_results in results.items():
            writer.writerow([f'=== {analyzer_name.upper()} ==='])
            writer.writerow(['Score', analyzer_results.get('score', 'N/A')])
            writer.writerow([])
        
        return output.getvalue()
