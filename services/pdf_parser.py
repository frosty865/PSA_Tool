"""
PDF parser service
Extracts text from PDF files
"""

import os

# Try importing PDF parsing libraries
pdf_parse = None
try:
    import pdf_parse
    pdf_parse_available = True
except ImportError:
    pdf_parse_available = False

def extract_text(file_path):
    """Extract text from PDF file"""
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        # Try pdf-parse library first (uses pdf_parse function)
        if pdf_parse_available:
            try:
                with open(file_path, 'rb') as f:
                    data = pdf_parse(f.read())
                    return data.get('text', '') if isinstance(data, dict) else str(data)
            except Exception as e:
                # If pdf_parse fails, try other libraries
                pass
        
        # Fallback: Try PyPDF2 or pdfplumber if available
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except ImportError:
            pass
        
        # Last resort: Try pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                return text
        except ImportError:
            raise ImportError("No PDF parsing library available. Install pdf-parse, PyPDF2, or pdfplumber")
            
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

