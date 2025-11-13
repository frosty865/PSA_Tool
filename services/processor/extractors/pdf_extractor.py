"""
Structured PDF Extraction
Preserves document structure (headings, bullets, page boundaries) for accurate extraction.
"""
import json
import logging
from typing import List, Dict, Any

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logging.error("PyMuPDF (fitz) not available - PDF processing disabled")


def extract_structured_pdf(path: str) -> List[Dict[str, Any]]:
    """
    Extract structured text from PDF preserving page boundaries and formatting.
    
    Args:
        path: Path to PDF file
        
    Returns:
        List of page dictionaries with 'page' number and 'text' content
    """
    if not PYMUPDF_AVAILABLE:
        raise ImportError("PyMuPDF (fitz) is required for PDF extraction")
    
    doc = fitz.open(path)
    pages = []
    
    try:
        for i, page in enumerate(doc):
            # Get structured text with JSON format to preserve layout
            raw = page.get_text("json")
            data = json.loads(raw)
            text_lines = []
            
            # Extract text from blocks, preserving line structure
            for block in data.get("blocks", []):
                if block.get("type") != 0:  # Type 0 = text block
                    continue
                    
                for line in block.get("lines", []):
                    # Combine all spans in a line
                    line_text = " ".join(
                        span.get("text", "") 
                        for span in line.get("spans", [])
                    )
                    if line_text.strip():
                        text_lines.append(line_text)
            
            pages.append({
                "page": i + 1,
                "text": "\n".join(text_lines)
            })
            
    finally:
        doc.close()
    
    logging.info(f"Extracted {len(pages)} pages from {path}")
    return pages

