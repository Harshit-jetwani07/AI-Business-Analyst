import io
import pandas as pd
import numpy as np
import re
from datetime import datetime

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False


class ReportGenerator:
    def __init__(self, df, ai_agent, analyzer, company_name, analyst_name,
                 report_title, report_date, filename):
        self.df = df
        self.ai_agent = ai_agent
        self.analyzer = analyzer
        self.company_name = company_name
        self.analyst_name = analyst_name
        self.report_title = report_title
        self.report_date = report_date
        self.filename = filename

    def generate(self) -> bytes:
        if not FPDF_AVAILABLE:
            return self._generate_fallback_pdf("FPDF library missing on system.")
        return self._generate_pdf()

    def _generate_pdf(self) -> bytes:
        try:
            # Let FPDF handle the pages naturally based on content size to avoid blank spaces!
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            # Helper to clean characters and strip markdown/layout-breaking text.
            def safe_txt(s):
                if s is None:
                    return ""
                s_str = str(s).strip()
                s_str = s_str.replace("`", "'").replace('"', "'")
                s_str = s_str.replace("$", "USD ").replace("%", " percent")
                s_str = s_str.replace("**", "")
                s_str = s_str.encode("ascii", "ignore").decode("ascii")
                s_str = re.sub(r"[ \t]+", " ", s_str)
                s_str = re.sub(r"\n{3,}", "\n\n", s_str)
                return s_str
            # 
            #  PAGE 1: Corporate Cover Page
            # 
            pdf.add_page()
            pdf.set_fill_color(24, 28, 36)  # Deep Slate Dark Theme
            pdf.rect(0, 0, 210, 297, "F")

            # Solid Top Blue Accent Band
            pdf.set_fill_color(37, 99, 235)
            pdf.rect(0, 0, 210, 8, "F")

            # Main Title Branding
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", "B", 22)
            pdf.set_y(105)
            pdf.cell(0, 12, safe_txt(self.report_title).upper(), ln=True, align="C")
            
            # Subtitle
            pdf.set_font("Arial", "", 12)
            pdf.set_text_color(140, 150, 170)
            pdf.cell(0, 10, "Comprehensive Automated Data Intelligence Report", ln=True, align="C")
            
            pdf.ln(4)
            pdf.set_font("Arial", "I", 10)
            pdf.set_text_color(110, 120, 135)
            pdf.cell(0, 6, f"Data Source Master: {safe_txt(self.filename)}", ln=True, align="C")

            # Lower Metadata Info Block
            pdf.set_y(225)
            pdf.set_text_color(210, 215, 225)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, f"ORGANIZATION: {safe_txt(self.company_name)}", ln=True, align="C")
            pdf.cell(0, 6, f"LEAD ANALYST: {safe_txt(self.analyst_name)}", ln=True, align="C")
            pdf.cell(0, 6, f"GENERATION DATE: {safe_txt(self.report_date)}", ln=True, align="C")


            # 
            #  BODY PAGES (Content flows naturally now without manual add_page blocks)
            # 
            pdf.add_page()
            pdf.set_text_color(30, 41, 59)
            
            # Global Document Section Header Styling Generator
            def add_section_header(title_text):
                if pdf.get_y() > 235:
                    pdf.add_page()
                pdf.ln(3)
                pdf.set_font("Arial", "B", 14)
                pdf.set_text_color(30, 58, 138)  # Deep Navy Blue
                pdf.cell(0, 8, title_text.upper(), ln=1)
                pdf.set_draw_color(37, 99, 235)  # Royal Accent Line
                pdf.set_line_width(0.5)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(3)

            #  SECTION 1: EXECUTIVE SUMMARY
            add_section_header("1. Executive Matrix & Operational Overview")
            pdf.set_font("Arial", "", 10)
            pdf.set_text_color(55, 65, 81)
            exec_text = self.ai_agent.generate_report_text(self.df, "Executive Summary Structure Analysis")
            pdf.multi_cell(0, 5.0, safe_txt(exec_text))

            #  SECTION 2: GRANULAR DATA INSIGHTS
            add_section_header("2. Comprehensive Quantitative Key Insights")
            pdf.set_font("Arial", "", 10)
            pdf.set_text_color(55, 65, 81)
            findings_text = self.ai_agent.generate_report_text(self.df, "Key Business Insights Mathematical Relations")
            pdf.multi_cell(0, 5.0, safe_txt(findings_text))

            #  SECTION 3: DESCRIPTIVE STATISTICAL TABLE
            add_section_header("3. Primary Quantitative Feature Distribution Matrix")
            pdf.set_font("Arial", "", 10)
            pdf.ln(2)
            
            num_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
            if not num_cols:
                pdf.set_font("Arial", "I", 10)
                pdf.cell(0, 6, "No quantitative numeric features detected to calculate metrics.", ln=1)
            else:
                target_cols = num_cols[:3]
                metric_w = 45
                col_w = 48
                
                # Header Format Design
                pdf.set_font("Arial", "B", 9)
                pdf.set_fill_color(30, 58, 138)
                pdf.set_text_color(255, 255, 255)
                
                pdf.cell(metric_w, 7.5, " Statistical Matrix Property", border=1, fill=True)
                for col in target_cols:
                    pdf.cell(col_w, 7.5, safe_txt(str(col)[:20]), border=1, fill=True, align="C")
                pdf.ln()

                # Table Metric Processing Loop
                stats = self.df.describe()
                pdf.set_font("Arial", "", 9.5)
                row_toggle = False
                
                for idx in ["count", "mean", "std", "min", "max"]:
                    if idx in stats.index:
                        pdf.set_fill_color(245, 247, 250) if row_toggle else pdf.set_fill_color(255, 255, 255)
                        pdf.set_text_color(31, 41, 55)
                        
                        pdf.cell(metric_w, 7, f" {idx.title()}", border=1, fill=True)
                        for col in target_cols:
                            val = stats.loc[idx, col]
                            val_str = f"{val:,.2f}" if not np.isnan(val) else "N/A"
                            pdf.cell(col_w, 7, safe_txt(val_str), border=1, fill=True, align="R")
                        pdf.ln()
                        row_toggle = not row_toggle

            #  SECTION 4: QUALITATIVE PATTERNS
            add_section_header("4. Qualitative & Categorical Matrix Patterns")
            pdf.set_font("Arial", "", 10)
            pdf.set_text_color(55, 65, 81)
            
            cat_cols = self.df.select_dtypes(include=['object', 'category']).columns.tolist()
            clean_cat_cols = [c for c in cat_cols if c.lower() not in ['id', 'customer name', 'name', 'unnamed']]
            if not clean_cat_cols:
                clean_cat_cols = cat_cols[:3]

            if not cat_cols:
                profile_summary = "Dataset contains zero qualitative or categorical components to extract metrics."
            else:
                profile_summary = ""
                for c in clean_cat_cols[:3]:
                    if not self.df[c].empty:
                        top_node = self.df[c].mode()[0]
                        percentage = (self.df[c] == top_node).mean() * 100
                        profile_summary += f"Within the vertical categorical tracking domain of '{c}', the dominant recurrent node logs on '{top_node}', accounting for a prominent share of {percentage:.2f}% of all documented process records. This high recurrence indicates centralized clusters within this specific workflow branch.\n\n"
            
            pdf.multi_cell(0, 5.0, safe_txt(profile_summary.strip()))

            #  SECTION 5: STRATEGIC ROADMAP
            add_section_header("5. Data-Driven Strategic Recommendations Roadmap")
            pdf.set_font("Arial", "", 10)
            pdf.set_text_color(30, 41, 59)
            
            rec_text = self.ai_agent.generate_report_text(self.df, "Strategic Recommendations Action Plan Points")
            pdf.multi_cell(0, 5.0, safe_txt(rec_text), border=0)

            # Final standard byte output extraction stream
            try:
                raw_bytes = pdf.output(dest='S')
                if isinstance(raw_bytes, str):
                    return bytes(raw_bytes.encode('latin-1', 'ignore'))
                return bytes(raw_bytes)
            except Exception:
                raw_bytes = pdf.output()
                if isinstance(raw_bytes, str):
                    return bytes(raw_bytes.encode('latin-1', 'ignore'))
                return bytes(raw_bytes)

        except Exception as e:
            return self._generate_fallback_pdf(str(e))

    def _generate_fallback_pdf(self, error: str = "") -> bytes:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "System Compilation Critical Block!", ln=1)
        pdf.ln(5)
        clean_error = str(error).replace("\n", " ").replace("\r", " ")
        pdf.multi_cell(0, 5, f"Tracking Trace Constraint Details: {clean_error}")
        try:
            raw_bytes = pdf.output(dest='S')
            if isinstance(raw_bytes, str):
                return bytes(raw_bytes.encode('latin-1', 'ignore'))
            return bytes(raw_bytes)
        except Exception:
            raw_bytes = pdf.output()
            if isinstance(raw_bytes, str):
                return bytes(raw_bytes.encode('latin-1', 'ignore'))
            return bytes(raw_bytes)
