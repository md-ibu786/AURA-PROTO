"""PDF generation helpers

Clean implementation using FPDF/fpdf2.
Provides:
- preprocess_text_for_pdf(text)
- create_pdf(summary_text, title, output_filename)
- create_pdf_bytes(summary_text, title)
"""

from typing import Optional

try:
    from fpdf import FPDF
    FPDF_LIBRARY = 'fpdf'
except ImportError:
    try:
        from fpdf2 import FPDF
        FPDF_LIBRARY = 'fpdf2'
    except ImportError:
        raise ImportError("Neither fpdf nor fpdf2 libraries are available. Please install one of them.")


def preprocess_text_for_pdf(text: str) -> str:
    """Normalize and replace Unicode characters that may not be supported by older FPDF implementations."""
    if not text:
        return text

    replacements = {
        '\u2014': '--', '\u2013': '-', '\u2018': "'", '\u2019': "'",
        '\u201C': '"', '\u201D': '"', '\u2192': '->', '\u2026': '...',
        '\u00A0': ' ', '\u00AD': '', '\u200B': '',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    if FPDF_LIBRARY == 'fpdf2':
        return text

    try:
        text.encode('latin-1')
        return text
    except UnicodeEncodeError:
        return text.encode('latin-1', 'replace').decode('latin-1')


class LectureNotesPDF(FPDF):
    def __init__(self, title_text: Optional[str] = None):
        super().__init__()
        self.title_text = title_text or ""

    def header(self):
        self.set_font('Helvetica', 'B', 15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')


def _build_pdf(summary_text: str, title: str) -> FPDF:
    summary_text = preprocess_text_for_pdf(summary_text)
    title = preprocess_text_for_pdf(title)

    pdf = LectureNotesPDF(title_text=title)
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font('Helvetica', 'B', 15)
    pdf.cell(0, 10, title, align='C')
    pdf.ln(20)

    pdf.set_font('Times', '', 12)

    def write_formatted_text(pdf_obj, text_line, line_height=6):
        parts = text_line.split('**')
        for i, part in enumerate(parts):
            if i % 2 == 1:
                pdf_obj.set_font('Times', 'B', 12)
                pdf_obj.write(line_height, part)
            else:
                pdf_obj.set_font('Times', '', 12)
                pdf_obj.write(line_height, part)

    for line in summary_text.split('\n'):
        line = line.strip()
        if not line:
            pdf.ln(4)
            continue

        if line.startswith('# '):
            pdf.set_font('Helvetica', 'B', 16)
            pdf.multi_cell(0, 8, line[2:], align='L')
            pdf.set_font('Times', '', 12)
        elif line.startswith('## '):
            pdf.set_font('Helvetica', 'B', 14)
            pdf.multi_cell(0, 7, line[3:], align='L')
            pdf.set_font('Times', '', 12)
        elif line.startswith('### '):
            pdf.set_font('Helvetica', 'B', 13)
            pdf.multi_cell(0, 6, line[4:], align='L')
            pdf.set_font('Times', '', 12)
        elif line.startswith('- ') or line.startswith('* '):
            bullet_marker = line[0] + ' '
            content = line[2:]
            original_margin = pdf.l_margin
            pdf.cell(5, 6, bullet_marker)
            pdf.set_left_margin(original_margin + 5)
            write_formatted_text(pdf, content)
            pdf.set_left_margin(original_margin)
            pdf.ln()
        else:
            write_formatted_text(pdf, line)
            pdf.ln()

    return pdf


def create_pdf(summary_text: str, title: str, output_filename: str = "lecture_notes.pdf") -> str:
    pdf = _build_pdf(summary_text, title)
    pdf.output(output_filename)
    return output_filename


def create_pdf_bytes(summary_text: str, title: str) -> bytes:
    pdf = _build_pdf(summary_text, title)
    s = pdf.output(dest='S')
    if isinstance(s, str):
        return s.encode('latin-1')
    return s


__all__ = ['preprocess_text_for_pdf', '_build_pdf', 'create_pdf', 'create_pdf_bytes']

