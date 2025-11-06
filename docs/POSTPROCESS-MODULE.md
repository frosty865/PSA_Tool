# Document Post-Processing Module

## Overview

The `postprocess.py` module provides post-processing functionality for model results, including text normalization, deduplication, and Supabase taxonomy resolution. It ensures that parsed model outputs are cleaned, validated, and properly mapped to Supabase database IDs before insertion.

## Location

**File:** `services/postprocess.py`

## Features

- **Text Normalization:** Standardizes text for comparison (lowercase, strip, collapse whitespace)
- **Deduplication:** Removes duplicate vulnerabilities based on normalized text
- **Taxonomy Resolution:** Maps discipline, sector, and subsector names to Supabase IDs
- **Fuzzy Matching:** Falls back to fuzzy matching for disciplines if exact match not found
- **Category Extraction:** Automatically attaches category from discipline record
- **Data Validation:** Filters out incomplete or invalid records

## Functions

### `normalize_text(s: str) -> str`

Normalizes text for comparison by:
- Converting to lowercase
- Stripping whitespace
- Collapsing multiple spaces to single space

**Example:**
```python
from services.postprocess import normalize_text

normalized = normalize_text("  Physical Security  ")  # Returns: "physical security"
```

### `dedupe_results(results) -> list`

Removes duplicate results based on normalized vulnerability text.

**Example:**
```python
from services.postprocess import dedupe_results

unique = dedupe_results(model_results)
```

### `resolve_discipline(name: str) -> tuple`

Resolves discipline name to `(discipline_id, category)` using Supabase lookup.

**Features:**
- Exact match lookup (case-insensitive)
- Fuzzy matching fallback (70% similarity threshold)
- Returns `(None, None)` if not found

**Example:**
```python
from services.postprocess import resolve_discipline

disc_id, category = resolve_discipline("Physical Security")
# Returns: (uuid, "Physical") or (None, None)
```

### `postprocess_results(model_results) -> list`

Main post-processing function that orchestrates the full pipeline.

**Process:**
1. Extracts and validates vulnerability and OFC data
2. Resolves discipline, sector, and subsector to IDs
3. Attaches category from discipline record
4. Deduplicates results
5. Returns cleaned, validated records

**Input Format:**
```python
[
  {
    "vulnerability": "Text...",
    "options_for_consideration": ["OFC1", "OFC2"],
    "discipline": "Physical Security",
    "sector": "Energy",
    "subsector": "Power Grid",
    "source": "document.pdf",
    "page_range": "1-2"
  }
]
```

**Output Format:**
```python
[
  {
    "vulnerability": "Text...",
    "options_for_consideration": ["OFC1", "OFC2"],
    "discipline_id": "uuid-here",
    "category": "Physical",
    "sector_id": "uuid-here",
    "subsector_id": "uuid-here",
    "source": "document.pdf",
    "page_ref": "1-2",
    "chunk_id": "doc_001_chunk_01"
  }
]
```

**Example:**
```python
from services.postprocess import postprocess_results

cleaned = postprocess_results(model_results)
```

## Supabase Helper Functions

### `get_discipline_record(name=None, all=False)`

Get discipline record(s) from Supabase.

**Parameters:**
- `name`: Discipline name to search (case-insensitive)
- `all`: If True, return all active disciplines

**Returns:**
- Single record dict, list of records, or None

**Example:**
```python
from services.supabase_client import get_discipline_record

# Get specific discipline
record = get_discipline_record("Physical Security")

# Get all disciplines
all_discs = get_discipline_record(all=True)
```

### `get_sector_id(name)`

Get sector ID by name from Supabase.

**Parameters:**
- `name`: Sector name (case-insensitive)

**Returns:**
- Sector ID (UUID) or None

**Example:**
```python
from services.supabase_client import get_sector_id

sector_id = get_sector_id("Energy")
```

### `get_subsector_id(name)`

Get subsector ID by name from Supabase.

**Parameters:**
- `name`: Subsector name (case-insensitive)

**Returns:**
- Subsector ID (UUID) or None

**Example:**
```python
from services.supabase_client import get_subsector_id

subsector_id = get_subsector_id("Power Grid")
```

## Integration

### In Flask API (`routes/process.py`)

The post-processing is automatically integrated into the `/api/process` endpoint:

```python
# Step 4: Model inference
model_results = run_model_on_chunks(chunks)

# Step 5: Post-process results
final_results = postprocess_results(model_results)

# Step 6: Save to Supabase
save_results(final_results, source_file=filename)
```

### In process_worker.py

```python
from services.postprocess import postprocess_results
from services.supabase_client import save_results

# After model inference
final_records = postprocess_results(model_results)
save_results(final_records)
```

## CLI Usage

Test post-processing standalone:

```bash
python services/postprocess.py results.json
```

**Output:**
- Console summary with statistics
- Cleaned JSON file: `results_cleaned.json`
- Sample records display

## Processing Pipeline

```
Model Results
    ↓
Extract & Validate
    ↓
Resolve Taxonomy (Discipline, Sector, Subsector)
    ↓
Attach Category from Discipline
    ↓
Deduplicate
    ↓
Validated Records (Ready for Supabase)
```

## Error Handling

- **Missing Fields:** Records without vulnerability or OFCs are skipped
- **Unknown Taxonomy:** Missing discipline/sector/subsector IDs are set to None
- **Fuzzy Match Failures:** Logged as warnings, record continues with None IDs
- **Invalid Data:** Malformed records are logged and skipped

## Logging

All post-processing actions are logged:

```
INFO - Starting post-processing for 15 model results
INFO - No exact match for discipline 'Physical Security', trying fuzzy match...
INFO - Fuzzy match found: 'Physical Security' -> 'Physical Security' (score: 1.00)
WARNING - Sector not found: Unknown Sector
INFO - Deduplication: 15 -> 12 unique records
INFO - Post-processing complete: 12 unique records (skipped: 3)
```

## Fuzzy Matching

The discipline resolver uses `difflib.SequenceMatcher` for fuzzy matching:

- **Threshold:** 70% similarity required
- **Fallback:** If exact match fails, searches all active disciplines
- **Best Match:** Returns discipline with highest similarity score

**Example:**
- Input: "Physical Securty" (typo)
- Fuzzy match: "Physical Security" (score: 0.95) ✓
- Returns discipline ID and category

## Data Validation

Records are validated before inclusion:

**Required Fields:**
- `vulnerability` - Must be non-empty string
- `options_for_consideration` - Must be non-empty list

**Optional Fields:**
- `discipline_id` - Resolved from discipline name
- `category` - Extracted from discipline record
- `sector_id` - Resolved from sector name
- `subsector_id` - Resolved from subsector name
- `source` - Source file or chunk ID
- `page_ref` - Page range reference

## Performance Considerations

- **Taxonomy Lookups:** Cached at Supabase client level
- **Fuzzy Matching:** Only used when exact match fails
- **Batch Processing:** Processes all results in single pass
- **Deduplication:** Uses set-based lookup for O(1) performance

## Testing

### Test with sample data:

```python
import json
from services.postprocess import postprocess_results

# Load model results
with open('model_results.json', 'r') as f:
    results = json.load(f)

# Post-process
cleaned = postprocess_results(results)

# Save cleaned results
with open('cleaned_results.json', 'w') as f:
    json.dump(cleaned, f, indent=2)
```

## Troubleshooting

### Discipline Not Found

If disciplines aren't resolving:
1. Check Supabase `disciplines` table has active records
2. Verify discipline names match exactly (case-insensitive)
3. Check fuzzy match threshold (default 0.7)
4. Review logs for fuzzy match scores

### Sector/Subsector Not Found

If sectors/subsectors aren't resolving:
1. Check Supabase `sectors` and `subsectors` tables
2. Verify field names (`sector_name` vs `name`)
3. Check case sensitivity (uses `ilike` for case-insensitive)

### High Deduplication Rate

If many records are being deduplicated:
1. Check model output format
2. Verify vulnerability text extraction
3. Review normalization logic
4. Check for model generating identical outputs

---

*Last Updated: 2025-11-06*

