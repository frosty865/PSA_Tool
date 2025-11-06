"""
Text parser service
Extracts text from plain text files
"""

def extract_text(path):
    """Extract text from plain text file"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

