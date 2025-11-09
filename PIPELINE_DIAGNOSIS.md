# Pipeline Data Flow Diagnosis

## Expected End State

### Phase 1 (Parser)
- **Input**: Document chunks
- **Output**: Array of records, each with:
  ```json
  {
    "vulnerability": "Description of vulnerability",
    "options_for_consideration": ["OFC 1", "OFC 2", ...],  // OR "ofc": "single OFC"
    "category": "...",
    "citations": [...],
    "source_file": "...",
    "source_page": 1,
    "chunk_id": "..."
  }
  ```
- **Status**: ✅ Working correctly (52 records extracted)

### Phase 2 Lite (Taxonomy)
- **Input**: Phase 1 records (52 records)
- **Function**: `classify_phase1_records()` - ONLY adds taxonomy fields
- **Output**: Same structure as Phase 1 + taxonomy fields:
  ```json
  {
    "vulnerability": "...",
    "ofc": "...",  // OR "options_for_consideration": [...]
    "discipline": "Cybersecurity",
    "sector": "Finance",
    "subsector": "Banking",
    "confidence": 0.85,
    "confidence_score": 0.85,
    // ... all Phase 1 fields preserved
  }
  ```
- **Status**: ✅ Function works correctly (52 records in, 52 records out)
- **Problem**: ❌ File on disk has only 1 record with wrong content ("Apache Log4j" instead of "K-12 School Security")

### Sync to Supabase
- **Input**: Phase 2 JSON file with `records` array
- **Function**: `sync_individual_records()` - breaks down into individual submissions
- **Expected Behavior**:
  1. Read Phase 2 JSON file
  2. Extract each record from `records` array
  3. For each record:
     - Extract vulnerabilities (from `vulnerability` field or `vulnerabilities` array)
     - Extract OFCs (from `ofc` field or `options_for_consideration` array)
     - Create 1 submission
     - Insert 1+ vulnerability rows
     - Insert 1+ OFC rows
     - Create links between vulnerabilities and OFCs
- **Status**: ⚠️ Function works, but receives wrong data (1 record instead of 52)

## Root Cause Analysis

### Problem 1: Phase 2 File Corruption
- **Symptom**: Phase 2 file on disk has 1 record, but Phase 2 Lite function correctly processes 52 records
- **Location**: `ollama_auto_processor.py` lines 820-824
- **Possible Causes**:
  1. File is being overwritten by a different document
  2. File write is failing silently
  3. Different process is writing to the same file
  4. File is from a different document entirely

### Problem 2: Sync File Selection
- **Symptom**: Sync uses Phase 2 file (393 bytes, < 2KB) which triggers `sync_processed_result` instead of `sync_individual_records`
- **Location**: `ollama_auto_processor.py` lines 1065-1075
- **Issue**: Small file (< 2KB) uses wrong sync function that expects different format

### Problem 3: Data Structure Mismatch
- **Symptom**: Phase 1 outputs `ofc` (string) but prompt asks for `options_for_consideration` (array)
- **Location**: `ollama_auto_processor.py` lines 309-336
- **Impact**: Sync extraction handles both formats, but inconsistency causes confusion

## Recommended Fixes

### Fix 1: Always Use Individual Sync for Phase 2 Output
```python
# In ollama_auto_processor.py, line ~1067
# Instead of checking file size, check if it's Phase 2 output
if sync_file.name.endswith("_phase2_engine.json"):
    # Always use individual sync for Phase 2 (has records array)
    from services.supabase_sync_individual_v2 import sync_individual_records
    submission_ids = sync_individual_records(str(sync_file), submitter_email="system@psa.local")
else:
    # Use standard sync for other formats
    submission_id = sync_processed_result(str(sync_file), submitter_email="system@psa.local")
```

### Fix 2: Verify Phase 2 File After Writing
```python
# After saving Phase 2 file, verify it was written correctly
with open(temp_file, "r", encoding="utf-8") as f:
    verify_data = json.load(f)
    if len(verify_data.get("records", [])) != len(scored_records):
        logging.error(f"⚠️  Phase 2 file corruption: Expected {len(scored_records)} records, got {len(verify_data.get('records', []))}")
        # Rewrite file
        with open(temp_file, "w", encoding="utf-8") as f2:
            json.dump(engine_output, f2, indent=2, default=str)
```

### Fix 3: Standardize Phase 1 Output Format
- Update Phase 1 prompt to always use `options_for_consideration` array
- Or normalize Phase 1 output to always use `options_for_consideration` array before Phase 2

## Current Data Flow (Broken)

```
Phase 1: 52 records ✅
    ↓
Phase 2 Lite: 52 records processed ✅
    ↓
Phase 2 File: 1 record saved ❌ (WRONG FILE OR CORRUPTION)
    ↓
Sync: Uses wrong file (1 record) ❌
    ↓
Supabase: 1 submission, 1 vulnerability, 0 OFCs ❌
```

## Expected Data Flow (Fixed)

```
Phase 1: 52 records ✅
    ↓
Phase 2 Lite: 52 records processed ✅
    ↓
Phase 2 File: 52 records saved ✅
    ↓
Sync: Uses Phase 2 file (52 records) ✅
    ↓
Supabase: 52 submissions, 52+ vulnerabilities, 52+ OFCs ✅
```

