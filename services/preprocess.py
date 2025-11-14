"""
Document Preprocessing and Chunking Module
Extracts text from PDF, DOCX, and TXT files, normalizes it, and splits into chunks.
"""

import os
from config import Config
import re
import json
import logging
from pathlib import Path
from typing import List, Dict

# Try importing required libraries
try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False
    try:
        import PyPDF2
        PYPDF2_AVAILABLE = True
    except ImportError:
        PYPDF2_AVAILABLE = False
        try:
            import pdfplumber
            PDFPLUMBER_AVAILABLE = True
        except ImportError:
            PDFPLUMBER_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import nltk
    NLTK_AVAILABLE = True
    # Download required NLTK data if not already present
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            nltk.download('punkt', quiet=True)
        except:
            pass
except ImportError:
    NLTK_AVAILABLE = False

# Setup logging - Use C:\Tools\Ollama\Data\automation
BASE_DIR = Config.DATA_DIR
LOG_DIR = BASE_DIR / 'automation'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / 'preprocess.log'

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def extract_text(path: str) -> str:
    """
    Extract text from PDF, DOCX, or TXT files.
    
    Args:
        path: Path to the file
        
    Returns:
        Extracted text as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file type is not supported
        Exception: If extraction fails
    """
    file_path = Path(path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    ext = file_path.suffix.lower()
    logger.info(f"Extracting text from {file_path.name} (type: {ext})")
    
    try:
        if ext == '.pdf':
            return _extract_pdf(file_path)
        elif ext == '.docx':
            return _extract_docx(file_path)
        elif ext == '.txt':
            return _extract_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}. Supported: .pdf, .docx, .txt")
    except Exception as e:
        logger.error(f"Failed to extract text from {path}: {str(e)}")
        raise


def _extract_pdf(file_path: Path) -> str:
    """Extract text from PDF file using PyMuPDF (fitz), PyPDF2, or pdfplumber."""
    text = ""
    pages = []
    
    # Try PyMuPDF (fitz) first - best for page tracking
    if FITZ_AVAILABLE:
        try:
            doc = fitz.open(str(file_path))
            for page_num, page in enumerate(doc, start=1):
                page_text = page.get_text()
                text += page_text + "\n"
                pages.append((page_num, page_text))
            doc.close()
            logger.info(f"Extracted text from PDF using PyMuPDF: {len(pages)} pages")
            return text
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {str(e)}, trying fallback")
    
    # Try pdfplumber
    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(str(file_path)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            logger.info(f"Extracted text from PDF using pdfplumber")
            return text
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {str(e)}, trying fallback")
    
    # Fallback to PyPDF2
    if PYPDF2_AVAILABLE:
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            logger.info(f"Extracted text from PDF using PyPDF2")
            return text
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {str(e)}")
            raise Exception(f"All PDF extraction methods failed: {str(e)}")
    
    raise ImportError("No PDF parsing library available. Install PyMuPDF (fitz), pdfplumber, or PyPDF2")


def _extract_docx(file_path: Path) -> str:
    """Extract text from DOCX file."""
    if not DOCX_AVAILABLE:
        raise ImportError("python-docx not available. Install with: pip install python-docx")
    
    try:
        doc = Document(str(file_path))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        logger.info(f"Extracted text from DOCX: {len(text)} characters")
        return text
    except Exception as e:
        logger.error(f"DOCX extraction failed: {str(e)}")
        raise


def _extract_txt(file_path: Path) -> str:
    """Extract text from TXT file."""
    try:
        # Try UTF-8 first, then fallback to other encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    text = f.read()
                logger.info(f"Extracted text from TXT using {encoding}: {len(text)} characters")
                return text
            except UnicodeDecodeError:
                continue
        raise Exception("Could not decode TXT file with any supported encoding")
    except Exception as e:
        logger.error(f"TXT extraction failed: {str(e)}")
        raise


def normalize_text(text: str) -> str:
    """
    Clean and normalize extracted text.
    Removes headers, footers, extra whitespace, and fixes hyphenated line breaks.
    
    Args:
        text: Raw extracted text
        
    Returns:
        Normalized text
    """
    logger.info(f"Normalizing text: {len(text)} characters")
    
    # Remove excessive whitespace (keep single spaces and newlines)
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
    text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines to double newline
    
    # Fix hyphenated line breaks (word-\nword -> word-word)
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    
    # Remove common headers/footers patterns
    # Page numbers
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    # Common footer patterns
    text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Confidential|DRAFT|PROPRIETARY', '', text, flags=re.IGNORECASE)
    
    # Remove excessive punctuation
    text = re.sub(r'[.]{3,}', '...', text)  # Multiple dots to ellipsis
    
    # Clean up whitespace at start/end
    text = text.strip()
    
    logger.info(f"Normalized text: {len(text)} characters")
    return text


def chunk_text(text: str, max_chars: int = 4000) -> List[str]:
    """
    Split text into sentence-aware chunks.
    Uses NLTK sentence tokenizer if available, otherwise falls back to simple splitting.
    
    Args:
        text: Normalized text to chunk
        max_chars: Maximum characters per chunk (default: 4000, ~800-1200 tokens)
        
    Returns:
        List of text chunks
    """
    logger.info(f"Chunking text into chunks of max {max_chars} characters")
    
    if not text.strip():
        logger.warning("Empty text provided for chunking")
        return []
    
    chunks = []
    
    if NLTK_AVAILABLE:
        # Use NLTK sentence tokenizer for better sentence boundaries
        try:
            sentences = nltk.sent_tokenize(text)
            current_chunk = ""
            
            for sentence in sentences:
                # If adding this sentence would exceed max_chars, save current chunk
                if current_chunk and len(current_chunk) + len(sentence) + 1 > max_chars:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Add sentence to current chunk
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
            
            # Add final chunk
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            logger.info(f"Created {len(chunks)} chunks using NLTK sentence tokenizer")
        except Exception as e:
            logger.warning(f"NLTK tokenization failed: {str(e)}, using fallback method")
            chunks = _chunk_text_fallback(text, max_chars)
    else:
        # Fallback: split by sentences using regex
        logger.info("NLTK not available, using regex-based sentence splitting")
        chunks = _chunk_text_fallback(text, max_chars)
    
    return chunks


def _chunk_text_fallback(text: str, max_chars: int) -> List[str]:
    """Fallback chunking method using regex sentence detection."""
    # Split by sentence endings (. ! ? followed by space and capital letter)
    sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
    sentences = re.split(sentence_pattern, text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # If adding this sentence would exceed max_chars, save current chunk
        if current_chunk and len(current_chunk) + len(sentence) + 1 > max_chars:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
    
    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def preprocess_document(path: str, max_chars: int = 4000) -> List[Dict]:
    """
    Orchestrate document preprocessing: extraction → normalization → chunking.
    
    Args:
        path: Path to document file
        max_chars: Maximum characters per chunk (default: 4000)
        
    Returns:
        List of chunk dictionaries with metadata
        
    Example output:
        [
            {
                "chunk_id": "example_001_chunk_01",
                "source_file": "example.pdf",
                "page_range": "1-2",
                "char_count": 3800,
                "content": "Clean normalized text ..."
            },
            ...
        ]
    """
    file_path = Path(path)
    file_name = file_path.stem
    file_ext = file_path.suffix
    
    logger.info(f"Starting preprocessing for {file_path.name}")
    
    try:
        # Step 1: Extract text
        raw_text = extract_text(str(file_path))
        logger.info(f"Extracted {len(raw_text)} characters from {file_path.name}")
        
        # Step 2: Normalize text
        normalized_text = normalize_text(raw_text)
        
        # Step 3: Chunk text
        chunks = chunk_text(normalized_text, max_chars=max_chars)
        logger.info(f"Created {len(chunks)} chunks from {file_path.name}")
        
        # Step 4: Create chunk metadata
        chunk_list = []
        for idx, chunk_content in enumerate(chunks, start=1):
            chunk_id = f"{file_name}_{idx:03d}_chunk_{idx:02d}"
            
            # Estimate page range (rough estimate: ~2000 chars per page)
            chars_per_page = 2000
            start_char = sum(len(chunks[i]) for i in range(idx - 1))
            start_page = max(1, int(start_char / chars_per_page) + 1)
            end_page = max(start_page, int((start_char + len(chunk_content)) / chars_per_page) + 1)
            page_range = f"{start_page}-{end_page}" if start_page != end_page else str(start_page)
            
            chunk_dict = {
                "chunk_id": chunk_id,
                "source_file": file_path.name,
                "page_range": page_range,
                "char_count": len(chunk_content),
                "content": chunk_content
            }
            chunk_list.append(chunk_dict)
        
        logger.info(f"Preprocessing complete: {len(chunk_list)} chunks created for {file_path.name}")
        return chunk_list
        
    except Exception as e:
        logger.error(f"Preprocessing failed for {file_path.name}: {str(e)}")
        raise


if __name__ == "__main__":
    """
    CLI interface for preprocessing documents.
    Usage: python preprocess.py <path-to-file>
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python preprocess.py <path-to-file>")
        print("Example: python preprocess.py C:\\Tools\\Ollama\\Data\\incoming\\sample.pdf")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        print(f"\n{'='*60}")
        print(f"Preprocessing: {file_path}")
        print(f"{'='*60}\n")
        
        # Preprocess document
        chunks = preprocess_document(file_path)
        
        # Print summary
        print(f"✓ Preprocessing complete!")
        print(f"  File: {Path(file_path).name}")
        print(f"  Chunks created: {len(chunks)}")
        print(f"  Total characters: {sum(c['char_count'] for c in chunks):,}")
        print(f"  Average chunk size: {sum(c['char_count'] for c in chunks) // len(chunks) if chunks else 0:,} chars")
        
        # Save chunks to JSON file
        output_file = Path(file_path).parent / f"{Path(file_path).stem}_chunks.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Chunks saved to: {output_file}")
        print(f"\nChunk Summary:")
        print(f"{'ID':<25} {'Page Range':<12} {'Chars':<8} {'Preview'}")
        print(f"{'-'*80}")
        
        for chunk in chunks[:10]:  # Show first 10 chunks
            preview = chunk['content'][:50].replace('\n', ' ') + "..."
            print(f"{chunk['chunk_id']:<25} {chunk['page_range']:<12} {chunk['char_count']:<8} {preview}")
        
        if len(chunks) > 10:
            print(f"... and {len(chunks) - 10} more chunks")
        
        print(f"\n{'='*60}\n")
        
    except FileNotFoundError as e:
        print(f"✗ Error: File not found - {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        logger.exception("CLI preprocessing failed")
        sys.exit(1)

