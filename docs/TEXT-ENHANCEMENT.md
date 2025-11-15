# Text Enhancement Module

## Overview

The text enhancement module (`services/text_enhancer.py`) rewrites and rephrases extracted vulnerabilities and OFCs to be more natural, varied, and contextually rich.

## Features

1. **Natural Rewriting**: Converts extracted text into professional, clear statements
2. **Context Addition**: Incorporates discipline, sector, and source context
3. **Variation Generation**: Creates alternative phrasings for the same content
4. **Batch Processing**: Efficiently processes multiple records

## Usage

### Enable Text Enhancement

Add to your `.env` file:

```bash
ENABLE_TEXT_ENHANCEMENT=true
```

### How It Works

The enhancement runs automatically in the processor pipeline after normalization:

```
Extract → Chunk → Model → Merge → Dedupe → Normalize → **Enhance Text** → Export
```

### Example

**Before Enhancement:**
```json
{
  "vulnerability": "no cameras",
  "options_for_consideration": ["install cameras"]
}
```

**After Enhancement:**
```json
{
  "vulnerability": "Inadequate surveillance coverage due to absence of security cameras",
  "vulnerability_original": "no cameras",
  "vulnerability_variations": [
    "Lack of security camera coverage",
    "Missing surveillance system"
  ],
  "options_for_consideration": [
    "Install comprehensive security camera system with appropriate coverage"
  ],
  "ofc_variations": [
    {
      "original": "install cameras",
      "enhanced": "Install comprehensive security camera system with appropriate coverage",
      "variations": [
        "Deploy surveillance cameras to monitor critical areas",
        "Implement video surveillance system"
      ]
    }
  ]
}
```

## Functions

### `enhance_vulnerability_text()`

Rewrites a vulnerability statement with context.

```python
from services.text_enhancer import enhance_vulnerability_text

result = enhance_vulnerability_text(
    vulnerability="no access control",
    discipline="Physical Security",
    sector="Government Facilities",
    source_context="The facility lacks proper visitor management..."
)

print(result["enhanced_text"])  # Enhanced version
print(result["variations"])     # Alternative phrasings
```

### `enhance_ofc_text()`

Rewrites an OFC statement with context.

```python
from services.text_enhancer import enhance_ofc_text

result = enhance_ofc_text(
    ofc="add bollards",
    vulnerability="Inadequate vehicle barrier protection",
    discipline="Physical Security"
)

print(result["enhanced_text"])
```

### `enhance_record()`

Enhances a complete record (vulnerability + OFCs).

```python
from services.text_enhancer import enhance_record

record = {
    "vulnerability": "no perimeter fence",
    "options_for_consideration": ["install fence"],
    "discipline": "Physical Security"
}

enhanced = enhance_record(record, enable_variations=True)
```

### `enhance_records_batch()`

Processes multiple records efficiently.

```python
from services.text_enhancer import enhance_records_batch

enhanced_records = enhance_records_batch(
    records,
    enable_variations=True,
    max_records=10  # Optional limit for testing
)
```

## Configuration

- **Temperature**: Uses `0.3` for consistent rewrites, `0.5` for variations
- **Model**: Uses `Config.DEFAULT_MODEL` (typically `vofc-unified:latest`)
- **Max Tokens**: 200 for rewrites, 300 for variations

## Integration Points

1. **Processor Pipeline**: Automatically runs if `ENABLE_TEXT_ENHANCEMENT=true`
2. **Post-Processing**: Can be called manually from `services/postprocess.py`
3. **Standalone**: Can be used independently for testing or manual enhancement

## Performance Considerations

- Each enhancement makes 1-2 Ollama API calls
- Batch processing is recommended for large datasets
- Use `max_records` parameter for testing on subsets
- Enhancement failures fall back to original text (non-blocking)

## Error Handling

- If enhancement fails, original text is preserved
- Errors are logged but don't stop processing
- Fallback validation ensures enhanced text is reasonable length

## Future Enhancements

Potential improvements:
- Caching of similar enhancements
- Template-based rewriting for common patterns
- Quality scoring of enhanced text
- A/B testing of different enhancement strategies

