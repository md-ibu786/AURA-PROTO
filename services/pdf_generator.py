from fpdf import FPDF

class LectureNotesPDF(FPDF):
    def __init__(self, title_text):
        super().__init__()
        # Store the title passed during initialization
        self.title_text = title_text

    def header(self):
        """Standard header for every page"""
        # Set font: Helvetica bold 15
        self.set_font('Helvetica', 'B', 15)
        
        # Title is now handled in the body of the first page only
        pass

    def footer(self):
        """Standard footer for every page"""
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

def create_pdf(summary_text, title, output_filename="lecture_notes.pdf"):
    """
    Converts a summary string into a PDF with a dynamic header title.
    
    Args:
        summary_text (str): The summarized lecture text.
        title (str): The specific title of the lecture provided by the user.
        output_filename (str): The desired path/name for the PDF.
    """
    
    # Initialize PDF with the specific title
    pdf = LectureNotesPDF(title_text=title)
    
    pdf.alias_nb_pages() 
    pdf.add_page()
    
    # Add Title to the first page
    pdf.set_font('Helvetica', 'B', 15)
    pdf.cell(0, 10, title, align='C')
    pdf.ln(20)
    
    pdf.set_font('Times', '', 12)
    
    def write_formatted_text(pdf_obj, text_line, line_height=6):
        """
        Parses text for **bold** markers and writes it to the PDF.
        """
        parts = text_line.split('**')
        for i, part in enumerate(parts):
            if i % 2 == 1:  # Odd indices are between ** and ** -> Bold
                pdf_obj.set_font('Times', 'B', 12)
                pdf_obj.write(line_height, part)
            else:           # Even indices are normal text
                pdf_obj.set_font('Times', '', 12)
                pdf_obj.write(line_height, part)
    
    # Parse and write content line by line
    lines = summary_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            pdf.ln(4) # Small space for empty lines
            continue
            
        if line.startswith('# '):
            # Level 1 Header (Bold, Large)
            pdf.set_font('Helvetica', 'B', 16)
            pdf.multi_cell(0, 8, line[2:], align='L')
            pdf.set_font('Times', '', 12) # Reset to body font
        elif line.startswith('## '):
            # Level 2 Header (Bold, Medium)
            pdf.set_font('Helvetica', 'B', 14)
            pdf.multi_cell(0, 7, line[3:], align='L')
            pdf.set_font('Times', '', 12) # Reset to body font
        elif line.startswith('### '):
            # Level 3 Header (Bold, Small)
            pdf.set_font('Helvetica', 'B', 13)
            pdf.multi_cell(0, 6, line[4:], align='L')
            pdf.set_font('Times', '', 12) # Reset to body font
        else:
            # Body Text
            # Check for bullet points for indentation
            if line.startswith('- ') or line.startswith('* '):
                # Handle bullet point
                bullet_marker = line[0] + ' '
                content = line[2:]
                
                # Save current position
                original_x = pdf.get_x()
                original_margin = pdf.l_margin
                
                # Write bullet
                pdf.cell(5, 6, bullet_marker)
                
                # Indent for the content
                pdf.set_left_margin(original_margin + 5)
                
                # Write content with bold parsing
                write_formatted_text(pdf, content)
                
                # Restore margin and move to next line
                pdf.set_left_margin(original_margin)
                pdf.ln()
            else:
                # Normal paragraph
                write_formatted_text(pdf, line)
                pdf.ln()
    
    pdf.output(output_filename)
    return output_filename