# Document Preprocessing Module

## Overview

The `preprocess.py` module provides document preprocessing and chunking functionality for the VOFC-Processor service. It extracts text from PDF, DOCX, and TXT files, normalizes the text, and splits it into logical, sentence-aware chunks ready for model processing.

## Location

**Primary Location:** `services/preprocess.py` (uses `C:\Tools\Ollama\Data` for data directories)

## Features

- **Multi-format Support:** PDF, DOCX, TXT
- **Text Normalization:** Removes headers, footers, extra whitespace, fixes hyphenated line breaks
- **Sentence-Aware Chunking:** Uses NLTK for intelligent sentence boundary detection
- **Configurable Chunk Size:** Default 4000 characters (~800-1200 tokens)
- **Comprehensive Logging:** All actions logged to `logs/preprocess.log`
- **Metadata-Rich Output:** Each chunk includes source file, page range, character count

## Dependencies

```bash
pip install PyMuPDF python-docx nltk
```

Or use the updated `requirements.txt` which includes:
- `PyMuPDF==1.23.8` (fitz) - Best PDF parser with page tracking
- `python-docx==1.1.0` - DOCX parsing
- `nltk==3.8.1` - Sentence tokenization

## Functions

### `extract_text(path: str) -> str`

Extracts text from PDF, DOCX, or TXT files.

**Supported Formats:**
- `.pdf` - Uses PyMuPDF (fitz), falls back to pdfplumber or PyPDF2
- `.docx` - Uses python-docx
- `.txt` - Plain text with encoding detection (UTF-8, Latin-1, CP1252, ISO-8859-1)

**Example:**
```python
from preprocess import extract_text

text = extract_text("document.pdf")
```

### `normalize_text(text: str) -> str`

Cleans and normalizes extracted text:
- Removes excessive whitespace
- Fixes hyphenated line breaks
- Removes common headers/footers (page numbers, "Confidential", etc.)
- Normalizes punctuation

**Example:**
```python
from preprocess import normalize_text

clean_text = normalize_text(raw_text)
```

### `chunk_text(text: str, max_chars=4000) -> list[str]`

Splits text into sentence-aware chunks using NLTK sentence tokenizer.

**Parameters:**
- `text`: Normalized text to chunk
- `max_chars`: Maximum characters per chunk (default: 4000, ~800-1200 tokens)

**Returns:** List of text chunks

**Example:**
```python
from preprocess import chunk_text

chunks = chunk_text(normalized_text, max_chars=4000)
```

### `preprocess_document(path: str, max_chars=4000) -> list[dict]`

Orchestrates the complete preprocessing pipeline: extraction → normalization → chunking.

**Returns:** List of chunk dictionaries with metadata

**Output Structure:**
```json
[
  {
    "chunk_id": "example_001_chunk_01",
    "source_file": "example.pdf",
    "page_range": "1-2",
    "char_count": 3800,
    "content": "Clean normalized text ..."
  },
  {
    "chunk_id": "example_001_chunk_02",
    "source_file": "example.pdf",
    "page_range": "3-4",
    "char_count": 3950,
    "content": "More normalized text ..."
  }
]
```

**Example:**
```python
from preprocess import preprocess_document

chunks = preprocess_document("document.pdf")
for chunk in chunks:
    print(f"Chunk {chunk['chunk_id']}: {chunk['char_count']} chars")
```

## CLI Usage

Run preprocessing from command line:

```bash
python preprocess.py "C:\Tools\Ollama\Data\incoming\sample.pdf"
```

**Output:**
- Console summary with chunk statistics
- JSON file: `<filename>_chunks.json` in the same directory as input file
- Log entries in `logs/preprocess.log`

**Example Output:**
```
============================================================
Preprocessing: C:\Tools\Ollama\Data\incoming\sample.pdf
============================================================

✓ Preprocessing complete!
  File: sample.pdf
  Chunks created: 15
  Total characters: 58,234
  Average chunk size: 3,882 chars

✓ Chunks saved to: C:\Tools\Ollama\Data\incoming\sample_chunks.json

Chunk Summary:
ID                       Page Range  Chars    Preview
--------------------------------------------------------------------------------
sample_001_chunk_01      1-2         3800     Clean normalized text ...
sample_001_chunk_02      3-4         3950     More normalized text ...
...
```

## Integration with process_worker.py

Update your `process_worker.py` to use the preprocessing module:

```python
from preprocess import preprocess_document

def process_file(file_path):
    """Process a file using preprocessing and model pipeline"""
    try:
        # Step 1: Preprocess document into chunks
        chunks = preprocess_document(file_path)
        
        # Step 2: Process each chunk with model
        results = []
        for chunk in chunks:
            result = run_model_on_chunk(chunk)
            results.append({
                'chunk_id': chunk['chunk_id'],
                'result': result
            })
        
        # Step 3: Save results
        save_results(file_path, results)
        
        return results
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise
```

## Logging

All preprocessing actions are logged to `logs/preprocess.log`:

```
2025-11-06 16:30:15 - INFO - Extracting text from sample.pdf (type: .pdf)
2025-11-06 16:30:16 - INFO - Extracted text from PDF using PyMuPDF: 25 pages
2025-11-06 16:30:16 - INFO - Normalizing text: 58234 characters
2025-11-06 16:30:16 - INFO - Normalized text: 57890 characters
2025-11-06 16:30:17 - INFO - Chunking text into chunks of max 4000 characters
2025-11-06 16:30:17 - INFO - Created 15 chunks using NLTK sentence tokenizer
2025-11-06 16:30:17 - INFO - Preprocessing complete: 15 chunks created for sample.pdf
```

## Error Handling

The module includes comprehensive error handling:

- **FileNotFoundError:** File doesn't exist
- **ValueError:** Unsupported file type
- **ImportError:** Missing required libraries
- **Exception:** General processing errors

All errors are logged with full stack traces.

## Configuration

### Chunk Size

Adjust chunk size based on your model's context window:

```python
# For smaller models (e.g., 2K context)
chunks = preprocess_document("file.pdf", max_chars=2000)

# For larger models (e.g., 8K context)
chunks = preprocess_document("file.pdf", max_chars=8000)
```

### Logging Level

Modify logging level in `preprocess.py`:

```python
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,  # Change to DEBUG for more verbose logging
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

## Testing

Test the module with sample files:

```bash
# Test PDF
python preprocess.py "C:\Tools\Ollama\Data\incoming\test.pdf"

# Test DOCX
python preprocess.py "C:\Tools\Ollama\Data\incoming\test.docx"

# Test TXT
python preprocess.py "C:\Tools\Ollama\Data\incoming\test.txt"
```

## Notes

- NLTK punkt tokenizer is automatically downloaded on first use
- Page range estimation is approximate (~2000 chars per page)
- Chunks preserve sentence boundaries for better model understanding
- All text is normalized to UTF-8 encoding

## Troubleshooting

### NLTK Data Not Found

If you see NLTK data errors, manually download:

```python
import nltk
nltk.download('punkt')
```

### PDF Extraction Fails

The module tries multiple PDF libraries in order:
1. PyMuPDF (fitz) - Best for page tracking
2. pdfplumber - Good for complex layouts
3. PyPDF2 - Basic fallback

Install at least one:
```bash
pip install PyMuPDF  # Recommended
# OR
pip install pdfplumber
# OR
pip install PyPDF2
```

### Encoding Issues with TXT Files

The module tries multiple encodings automatically. If issues persist, convert the file to UTF-8 before processing.

---

*Last Updated: 2025-11-06*

