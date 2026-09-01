#!/usr/bin/env python3
"""
CSV Exporter - Exports SEO analysis to CSV format (PROFESSIONAL tier)
"""

import csv
from typing import Dict, Any


class CSVExporter:
    """Export SEO analysis results to CSV"""
    
    @staticmethod
    def export(results: Dict[str, Any], filepath: str) -> bool:
        """
        Export results to CSV
        
        Args:
            results: Analysis results dictionary
            filepath: File path to save to
            
        Returns:
            bool: Success status
        """
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(['SEO Analysis Report'])
                writer.writerow(['URL', results.get('url', '')])
                writer.writerow(['Timestamp', results.get('timestamp', '')])
                writer.writerow(['Overall Score', results.get('overall_score', 0)])
                writer.writerow(['Overall Grade', results.get('overall_grade', 'F')])
                writer.writerow([])
                
                # Write analyzer results
                writer.writerow(['Analyzer', 'Score', 'Grade', 'Issues Count'])
                
                for name, result in results.get('analyzers', {}).items():
                    if hasattr(result, 'score'):
                        writer.writerow([
                            name.title(),
                            f"{result.score:.1f}",
                            result.grade,
                            len(result.issues) if hasattr(result, 'issues') else 0
                        ])
                
                writer.writerow([])
                writer.writerow(['Issues Detail'])
                writer.writerow(['Analyzer', 'Severity', 'Title', 'Description', 'Recommendation'])
                
                for name, result in results.get('analyzers', {}).items():
                    if hasattr(result, 'issues'):
                        for issue in result.issues:
                            writer.writerow([
                                name.title(),
                                issue.severity.value,
                                issue.title,
                                issue.description,
                                issue.recommendation or ''
                            ])
            
            return True
            
        except Exception as e:
            print(f"[CSVExporter] Error exporting to CSV: {e}")
            return False

