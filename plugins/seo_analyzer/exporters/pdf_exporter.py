#!/usr/bin/env python3
"""
PDF Exporter
Exports SEO analysis results to PDF format
Note: Requires reportlab library
"""

from typing import Dict, Any
from datetime import datetime


class PDFExporter:
    """Exporter for PDF format"""
    
    def __init__(self):
        self.has_reportlab = False
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib import colors
            self.has_reportlab = True
            print("[OK] ReportLab available for PDF export")
        except ImportError:
            print("[WARNING] ReportLab not available, PDF export disabled")
    
    def export(self, results: Dict[str, Any], url: str, filepath: str) -> bool:
        """
        Export results to PDF file
        
        Args:
            results: Analysis results dictionary
            url: URL that was analyzed
            filepath: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        if not self.has_reportlab:
            print("PDF export requires reportlab library")
            return False
        
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib import colors
            
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            story.append(Paragraph("SEO Analysis Report", styles['Title']))
            story.append(Spacer(1, 12))
            
            # URL and date
            story.append(Paragraph(f"<b>URL:</b> {url}", styles['Normal']))
            story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Results for each analyzer
            for analyzer_name, analyzer_results in results.items():
                # Analyzer header
                story.append(Paragraph(f"<b>{analyzer_name.upper().replace('_', ' ')}</b>", styles['Heading2']))
                story.append(Spacer(1, 6))
                
                # Score
                score = analyzer_results.get('score', 'N/A')
                severity = analyzer_results.get('severity', 'unknown')
                story.append(Paragraph(f"Score: {score}/100 ({severity})", styles['Normal']))
                story.append(Spacer(1, 12))
                
                # Issues
                issues = analyzer_results.get('issues', [])
                if issues:
                    story.append(Paragraph("<b>Issues:</b>", styles['Heading3']))
                    for issue in issues[:10]:  # Limit to 10 issues per analyzer
                        issue_text = f"• [{issue.get('type', '').upper()}] {issue.get('message', '')}"
                        story.append(Paragraph(issue_text, styles['Normal']))
                    story.append(Spacer(1, 12))
                
                # Recommendations
                recommendations = analyzer_results.get('recommendations', [])
                if recommendations:
                    story.append(Paragraph("<b>Recommendations:</b>", styles['Heading3']))
                    for rec in recommendations:
                        story.append(Paragraph(f"• {rec}", styles['Normal']))
                    story.append(Spacer(1, 12))
                
                story.append(Spacer(1, 20))
            
            doc.build(story)
            return True
            
        except Exception as e:
            print(f"Error exporting to PDF: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def is_available(self) -> bool:
        """Check if PDF export is available"""
        return self.has_reportlab
