"""
OFC Normalizer
Normalizes SAFE/IST format OFC blocks for better extraction.
"""
import re

try:
    from ftfy import fix_text
    FTFY_AVAILABLE = True
except ImportError:
    FTFY_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("ftfy not available - text fixing disabled. Install with: pip install ftfy")


# SAFE bullets: dot, dash, numeric, unicode bullets
SAFE_PREFIX = re.compile(r"^\s*(?:[-•‣▪*]|[0-9]+\.)\s+")

# IST wrapping: lines that continue a sentence
IST_WRAP = re.compile(r"[a-z0-9,;:)]$")


def normalize_safe_ist_ofcs(text: str) -> str:
    """
    Reconstruct OFC blocks in SAFE/IST format:
    - Removes bullets, preserves structure
    - Merges multi-line OFCs
    - Keeps paragraph separation
    - Keeps grouped OFC blocks intact
    
    Args:
        text: Raw text with SAFE/IST formatting
        
    Returns:
        Normalized text with clean OFC blocks
    """
    if not text:
        return text
    
    # Fix text encoding issues if ftfy is available
    if FTFY_AVAILABLE:
        text = fix_text(text).replace("\r", "")
    else:
        text = text.replace("\r", "")
    
    lines = [l.rstrip() for l in text.split("\n")]
    
    blocks = []
    current = []
    
    for line in lines:
        stripped = line.strip()
        
        # EMPTY LINE = PARAGRAPH BREAK
        if not stripped:
            if current:
                blocks.append(" ".join(current))
                current = []
            continue
        
        # SAFE: bullet starts a *new* OFC
        if SAFE_PREFIX.match(stripped):
            # flush previous ofc block
            if current:
                blocks.append(" ".join(current))
                current = []
            
            # remove bullet prefix and start new block
            cleaned = SAFE_PREFIX.sub("", stripped)
            current.append(cleaned)
            continue
        
        # IST-style wrapped continuation line
        if current and IST_WRAP.search(current[-1]):
            # Join continuation lines
            current[-1] = current[-1] + " " + stripped
            continue
        
        # Otherwise, treat as continuation inside the OFC block
        current.append(stripped)
    
    # Flush the last block
    if current:
        blocks.append(" ".join(current))
    
    # final cleanup
    cleaned_blocks = []
    for b in blocks:
        # compress excessive spaces
        b = re.sub(r"\s{2,}", " ", b).strip()
        if b:  # Only add non-empty blocks
            cleaned_blocks.append(b)
    
    # SAFE/IST formatting style: blank line between OFC blocks
    return "\n\n".join(cleaned_blocks)

