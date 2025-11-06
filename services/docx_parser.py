"""
DOCX parser service
Extracts text from DOCX files
"""

from docx import Document

def extract_text(path):
    """Extract text from DOCX file"""
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

