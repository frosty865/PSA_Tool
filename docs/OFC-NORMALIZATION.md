# OFC Normalization Module

## Overview

The OFC (Options for Consideration) normalizer (`services/ingestion/ofc_normalizer.py`) handles SAFE/IST format documents by reconstructing OFC blocks, merging multi-line OFCs, and preserving paragraph structure.

## Features

1. **SAFE Format Support**: Handles bulleted lists (•, -, *, numeric)
2. **IST Format Support**: Merges wrapped continuation lines
3. **Structure Preservation**: Maintains paragraph separation and OFC block grouping
4. **Text Fixing**: Uses `ftfy` to fix encoding issues

## Integration

The normalizer is automatically integrated into the processor pipeline:

```
Extract PDF → Normalize OFCs → Chunk → Model → Merge → Dedupe → Normalize → Export
```

It runs **after** text extraction but **before** chunking, ensuring:
- Multi-line OFCs are properly merged
- Bullets are removed but structure is preserved
- Better chunk cohesion
- Improved model accuracy

## How It Works

### SAFE Format Example

**Input:**
```
- Install security cameras
- Add perimeter fencing
- Implement access control
```

**Output:**
```
Install security cameras

Add perimeter fencing

Implement access control
```

### IST Format Example (Wrapped Lines)

**Input:**
```
- Install comprehensive security camera
  system with appropriate coverage
- Add perimeter fencing with proper
  height and material specifications
```

**Output:**
```
Install comprehensive security camera system with appropriate coverage

Add perimeter fencing with proper height and material specifications
```

### Mixed Format

**Input:**
```
1. Install security cameras
2. Add perimeter fencing
   with proper specifications
3. Implement access control
```

**Output:**
```
Install security cameras

Add perimeter fencing with proper specifications

Implement access control
```

## Pattern Matching

### SAFE Prefix Pattern
Matches bullets at start of line:
- `-` (dash)
- `•` (bullet)
- `‣` (triangular bullet)
- `▪` (square bullet)
- `*` (asterisk)
- `1.`, `2.`, etc. (numeric)

### IST Wrap Pattern
Detects continuation lines:
- Lines ending with lowercase letters
- Lines ending with numbers
- Lines ending with punctuation: `,`, `;`, `:`, `)`

## Usage

### Automatic (Recommended)

The normalizer runs automatically in the processor pipeline. No configuration needed.

### Manual Usage

```python
from services.ingestion.ofc_normalizer import normalize_safe_ist_ofcs

raw_text = """
- Install security cameras
- Add perimeter fencing
   with proper height
- Implement access control
"""

normalized = normalize_safe_ist_ofcs(raw_text)
print(normalized)
```

## Dependencies

- `ftfy==6.1.1` - Text fixing library (optional but recommended)
  - If not installed, normalization still works but encoding fixes are skipped
  - Install with: `pip install ftfy`

## Error Handling

- If `ftfy` is not available, normalization continues without encoding fixes
- Errors are logged but don't stop processing
- Falls back gracefully if normalization fails

## Benefits

1. **Better Extraction**: Properly structured OFC blocks improve model understanding
2. **Cleaner Output**: Removes formatting artifacts while preserving meaning
3. **Improved Chunking**: Better chunk cohesion when OFCs are properly merged
4. **Future-Ready**: Structure preserved for future enhancements (tables, page refs, disciplines)

## Technical Details

### Algorithm

1. **Split by lines**: Process text line by line
2. **Detect bullets**: Identify SAFE-style bullet prefixes
3. **Merge continuations**: Join IST-style wrapped lines
4. **Preserve breaks**: Empty lines create paragraph breaks
5. **Clean whitespace**: Compress excessive spaces
6. **Format output**: Join blocks with double newlines

### Performance

- Linear time complexity: O(n) where n is number of lines
- Minimal memory overhead
- Fast processing even for large documents

## Future Enhancements

Potential improvements:
- Table detection and preservation
- Page reference extraction
- Discipline-specific normalization
- Custom formatting rules per document type

