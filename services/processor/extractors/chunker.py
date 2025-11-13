"""
Document Chunker
Splits pages into manageable chunks while preserving page boundaries.
"""
import logging
from typing import List, Dict, Any


def chunk_pages(pages: List[Dict[str, Any]], max_chars: int = 5000) -> List[str]:
    """
    Chunk pages into manageable sizes without losing page boundaries.
    
    Each chunk is ~800-1200 tokens, perfect for extraction.
    Page markers are preserved to maintain context.
    
    Args:
        pages: List of page dictionaries with 'page' and 'text' keys
        max_chars: Maximum characters per chunk (default: 5000)
        
    Returns:
        List of chunk strings with page markers
    """
    chunks = []
    current = []
    length = 0
    
    for p in pages:
        page_text = p.get("text", "")
        page_num = p.get("page", 0)
        
        # If adding this page would exceed max_chars, finalize current chunk
        if length + len(page_text) > max_chars and current:
            chunks.append("\n".join(current))
            current = []
            length = 0
        
        # Add page marker and text
        page_marker = f"[PAGE {page_num}]\n{page_text}\n"
        current.append(page_marker)
        length += len(page_text)
    
    # Add final chunk if any remaining pages
    if current:
        chunks.append("\n".join(current))
    
    logging.info(f"Created {len(chunks)} chunks from {len(pages)} pages")
    return chunks

