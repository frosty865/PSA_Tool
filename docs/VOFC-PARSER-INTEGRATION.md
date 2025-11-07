# VOFC Parser Integration Guide

## Overview

The VOFC Parser Engine is an autonomous parser for extracting vulnerabilities and Options for Consideration (OFCs) from structured federal or DoD guidance documents (e.g., UFC, FEMA, DHS, CISA).

## Files Created

1. **`services/vofc_parser/ruleset_vofc_parser.yaml`** - YAML configuration with extraction patterns
2. **`services/vofc_parser/vofc_parser_engine.py`** - Main parser engine class
3. **`services/vofc_parser/utils.py`** - Utility functions (text cleaning, section detection, etc.)
4. **`services/vofc_parser/__init__.py`** - Package initialization
5. **`services/vofc_parser/integration_example.py`** - Integration examples

## Quick Start

### Basic Usage

```python
from services.vofc_parser.vofc_parser_engine import VOFCParserEngine
import yaml
from services.preprocess import extract_text

# Load ruleset
with open('services/vofc_parser/ruleset_vofc_parser.yaml', 'r') as f:
    rules = yaml.safe_load(f)

# Initialize parser
parser = VOFCParserEngine(rules)

# Extract text from document
text = extract_text('path/to/document.pdf')

# Extract vulnerabilities and OFCs
records = parser.extract(text, source_title="UFC 4-010-01 (2018 C1)")

# Process results
for record in records:
    print(f"Section: {record['section']}")
    print(f"Vulnerability: {record.get('vulnerability')}")
    print(f"OFC: {record.get('option_text')}")
    print(f"Confidence: {record['confidence_score']}")
```

### Integration with Document Extraction Pipeline

The parser can be integrated into the existing `services/document_extractor.py` pipeline:

```python
from services.vofc_parser.integration_example import extract_with_vofc_parser, convert_to_submission_format
from services.submission_saver import save_extraction_to_submission

# Extract using VOFC parser
records = extract_with_vofc_parser(
    file_path='path/to/document.pdf',
    source_title="UFC 4-010-01 (2018 C1)"
)

# Convert to submission format
extraction_results = convert_to_submission_format(
    records,
    submission_id=submission_id,
    source_info={
        'source_title': 'UFC 4-010-01',
        'agency': 'Department of Defense',
        'publication_year': 2018
    }
)

# Save to submission tables
save_extraction_to_submission(submission_id, extraction_results)
```

## Pattern Matching

### Positive Directives (OFCs)

The parser identifies positive directives that indicate requirements or recommendations:
- `shall`, `must`, `is required to`, `will`, `should`
- `provide`, `ensure`, `designed to`, `constructed to`
- `comply with`, `protect against`

### Negative Triggers (Vulnerabilities)

The parser identifies negative statements that indicate vulnerabilities:
- `does not`, `not provided`, `without`
- `lack of`, `absence of`, `failure to`
- `not maintained`, `missing`, `unavailable`

### Section Detection

The parser automatically detects section headings:
- Uppercase headings (e.g., "STANDARD 2-3.2.3 GLAZING")
- Numeric sections (e.g., "2.3.2.3 Windows")
- Explicit "STANDARD" lines
- "Rationale:", "Requirement:", "Design Guidance:" markers

## Configuration

Edit `services/vofc_parser/ruleset_vofc_parser.yaml` to customize:

- **Patterns**: Add or modify regex patterns for directives and triggers
- **Inference Options**: Adjust window size, enable/disable inversion
- **Scoring Weights**: Adjust confidence calculation weights
- **Confidence Threshold**: Set minimum confidence for extraction

## Expected Output

Running the parser on UFC 4-010-01 should produce structured extractions like:

```json
{
  "section": "2-3.2.3 GLAZING",
  "vulnerability": "Failure to comply with this standard may result in: Windows that are not designed to resist blast loads.",
  "option_text": "Windows shall be designed to resist blast loads as specified in UFC 4-010-01.",
  "pattern_matched": "\\bshall\\b",
  "context": "STANDARD 2-3.2.3 ...",
  "source_title": "UFC 4-010-01 (2018 C1)",
  "confidence_score": 0.9
}
```

## Dependencies

The parser requires:
- `nltk` for sentence tokenization (with fallback if not available)
- `yaml` for loading ruleset configuration
- `re` for pattern matching (standard library)

Install dependencies:
```bash
pip install nltk pyyaml
python -m nltk.downloader punkt
```

## Next Steps

1. **Test the parser** on a sample document:
   ```python
   python -c "from services.vofc_parser.integration_example import extract_with_vofc_parser; print(extract_with_vofc_parser('test.pdf', 'Test Document'))"
   ```

2. **Integrate into extraction pipeline** by modifying `services/document_extractor.py` to optionally use the VOFC parser

3. **Re-parse existing documents** to populate submission tables with structured extractions

4. **Tune patterns** in `ruleset_vofc_parser.yaml` based on document types and extraction quality

## Troubleshooting

### NLTK Not Available
The parser includes a fallback sentence tokenizer if NLTK is not installed. For better results, install NLTK:
```bash
pip install nltk
python -m nltk.downloader punkt
```

### No Extractions Found
- Check that the document text is being extracted correctly
- Verify patterns in `ruleset_vofc_parser.yaml` match document style
- Try adjusting `confidence_threshold` in the ruleset

### Integration Issues
- Ensure `services/vofc_parser/` directory is in Python path
- Check that `services/preprocess.py` can extract text from your document format
- Verify submission tables exist and have correct schema

