import os
from typing import Dict, Any
from fpdf import FPDF

class PDFExportEngine:
    """
    Generates enterprise-grade PDF audit reports.
    """
    
    def __init__(self, output_dir: str = "./uploads/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_report(self, report_data: Dict[str, Any]) -> str:
        """
        Creates a PDF report from scan results.
        """
        doc_title = report_data.get("document_title", "Analysis Report")
        job_id = str(report_data.get("job_id", "unknown"))
        filename = f"report_{job_id}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("Arial", 'B', 20)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(190, 15, "PlagX Originality Audit", ln=True, align='C')
        pdf.line(10, 25, 200, 25)
        
        # Overview Section
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(190, 10, "Executive Summary", ln=True)
        
        pdf.set_font("Arial", '', 11)
        pdf.cell(50, 8, "Document Name:")
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(140, 8, doc_title, ln=True)
        
        pdf.set_font("Arial", '', 11)
        pdf.cell(50, 8, "Overall Similarity:")
        pdf.set_font("Arial", 'B', 11)
        score = report_data.get("job", {}).get("overall_score", 0)
        pdf.set_text_color(220, 38, 38) if score > 30 else pdf.set_text_color(0, 0, 0)
        pdf.cell(140, 8, f"{score}%", ln=True)
        pdf.set_text_color(0, 0, 0)
        
        pdf.set_font("Arial", '', 11)
        pdf.cell(50, 8, "AI Probability:")
        pdf.set_font("Arial", 'B', 11)
        ai_prob = report_data.get("job", {}).get("ai_probability", 0)
        pdf.cell(140, 8, f"{ai_prob}%", ln=True)
        
        # Explainability Paragraph
        pdf.ln(5)
        pdf.set_font("Arial", 'I', 10)
        explain = report_data.get("job", {}).get("results", {}).get("explainability", {}).get("summary", "No details available.")
        pdf.multi_cell(190, 6, explain)
        
        # Matches Section
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(190, 10, "Top Matched Sources", ln=True)
        
        matches = report_data.get("job", {}).get("results", {}).get("matches", [])
        for m in matches[:10]:
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(150, 6, f"• {m.get('source', 'Unknown Source')[:60]}...")
            pdf.set_font("Arial", '', 10)
            pdf.cell(40, 6, f"{m.get('similarity', 0):.1f}% Match", ln=True)
            
        pdf.output(filepath)
        return filepath
