# Current Parsing System - VOFC Unified Processor

## Overview

The current parsing system is a **unified, service-ready pipeline** that processes entire documents at once (no chunking). It replaces the old 3-phase chunking system and uses Supabase as the deduplication authority.

## Architecture

### Service: VOFC-Processor

**Location:** `C:\Tools\py_scripts\vofc_processor\vofc_processor.py`  
**Service Name:** `VOFC-Processor` (Windows Service via NSSM)  
**Status:** Active and running continuously

### Key Characteristics

- ✅ **No Chunking** - Processes entire documents at once
- ✅ **Unified Pipeline** - Single pass through the model
- ✅ **Supabase Deduplication** - Uses `dedupe_key` for duplicate detection
- ✅ **Automatic Processing** - Monitors `incoming/` directory every 30 seconds
- ✅ **Service-Based** - Runs as Windows service, independent of Flask

---

## Processing Flow

### 1. File Detection

**Directory:** `C:\Tools\Ollama\Data\incoming\`  
**Supported Formats:** PDF files (`.pdf`)

The service runs a continuous loop that checks for new PDF files every 30 seconds:

```python
def run_service_loop():
    while True:
        process_all_pdfs()  # Check incoming/ directory
        time.sleep(30)      # Wait 30 seconds
```

### 2. Text Extraction

**Method:** PyMuPDF (fitz)  
**Output:** Full document text as a single string

```python
def extract_text_from_pdf(pdf_path: str) -> str:
    # Uses PyMuPDF to extract all text from PDF
    # Returns complete document text (no chunking)
```

### 3. Reference Data Loading

**Source:** Supabase production database  
**Tables:**
- `vulnerabilities` - Existing vulnerability records
- `options_for_consideration` - Existing OFC records
- `vulnerability_ofc_links` - Links between vulnerabilities and OFCs
- `disciplines`, `sectors`, `subsectors` - Taxonomy data

**Purpose:** Provides context to the model for:
- Alignment with existing records
- Duplicate detection
- Taxonomy normalization

**Limit:** Up to 2000 reference records loaded per processing cycle

### 4. Model Processing

**Model:** `vofc-unified:latest` (configurable via `OLLAMA_MODEL` env var)  
**Server:** Ollama HTTP API (treats Ollama as separate server entity)  
**Endpoint:** `http://127.0.0.1:11434/api/generate` (configurable via `OLLAMA_BASE_URL`)

**Prompt Structure:**
```
Extract physical security vulnerabilities and OFCs from this document.

Reference Context:
[2000 reference records from Supabase]

Document:
[Full document text - no chunking]

Output format - JSON object:
{
  "records": [
    {
      "vulnerability": "...",
      "options_for_consideration": ["...", "..."],
      "discipline": "...",
      "sector": "...",
      "subsector": "...",
      "confidence": "High|Medium|Low",
      "impact_level": "High|Moderate|Low",
      "follow_up": false,
      "standard_reference": "..."
    }
  ],
  "links": [
    {
      "ofc": "...",
      "linked_vulnerabilities": ["...", "..."]
    }
  ]
}
```

**Key Features:**
- Sends entire document to model (no chunking)
- Includes reference context for alignment
- Explicitly prevents cyber/CVE hallucinations
- Requests structured JSON output

### 5. JSON Parsing & Normalization

**Input:** Model response (may be wrapped in markdown or have extra text)  
**Processing:**
1. Extract JSON object using balanced brace matching
2. Parse `records` and `links` arrays
3. Calculate `dedupe_key` for each record: `SHA1(vulnerability + first_ofc)`
4. Filter out hallucinations (cyber/CVE content)
5. Normalize fields (strip whitespace, handle empty values)

**Output Schema:**
```json
{
  "records": [
    {
      "vulnerability": "Unsecured Perimeter",
      "options_for_consideration": ["Fencing", "Lighting", "Access Control"],
      "discipline": "Physical Security",
      "sector": "Government",
      "subsector": "Federal",
      "confidence": "High",
      "impact_level": "High",
      "follow_up": false,
      "dedupe_key": "a1b2c3d4e5f6...",
      "standard_reference": ""
    }
  ],
  "links": [
    {
      "ofc": "Install perimeter fencing",
      "linked_vulnerabilities": ["Unsecured Perimeter", "Inadequate Access Control"]
    }
  ]
}
```

### 6. Supabase Deduplication & Insertion

**Deduplication Authority:** Supabase (not the model)

**Process:**
1. For each record, check if vulnerability exists using `dedupe_key`:
   ```sql
   SELECT id FROM vulnerabilities WHERE dedupe_key = :dedupe_key
   ```

2. **If exists:**
   - Link to existing vulnerability (no duplicate insert)
   - Create/update `vulnerability_ofc_links` for OFCs
   - Increment `linked_count`

3. **If not exists:**
   - Insert new vulnerability record
   - Insert new OFC records (if not already exist)
   - Create `vulnerability_ofc_links`
   - Increment `inserted_count`

**Tables Used:**
- `vulnerabilities` - Main vulnerability records
- `options_for_consideration` - OFC records
- `vulnerability_ofc_links` - Links between vulnerabilities and OFCs
- `submissions` - Processing metadata and tracking

**Schema Compatibility:**
- Handles both `vulnerability_name` and `description` columns
- Skips `confidence` and `impact_level` (columns don't exist in current schema)
- Stores `dedupe_key` for future deduplication queries

### 7. File Archival

**Processed Files:** Moved to `C:\Tools\Ollama\Data\library\`  
**JSON Output:** Saved to `C:\Tools\Ollama\Data\processed\{filename}_vofc.json`  
**Error Files:** Saved to `C:\Tools\Ollama\Data\processed\{filename}_error.txt` (if processing fails)

---

## Configuration

### Environment Variables

Set via NSSM for the `VOFC-Processor` service:

```powershell
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# Ollama Configuration
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=vofc-unified:latest

# Data Directories
VOFC_DATA_DIR=C:\Tools\Ollama\Data
```

### Directory Structure

```
C:\Tools\Ollama\Data\
├── incoming\          # Place PDFs here for processing
├── processed\         # JSON output files
├── library\           # Processed PDFs (archived)
├── errors\            # Failed processing files
└── logs\              # Service logs
```

---

## Output Format

### Successful Processing

**JSON File:** `{filename}_vofc.json`

```json
{
  "records": [
    {
      "vulnerability": "Inadequate Perimeter Security",
      "options_for_consideration": ["Install fencing", "Add lighting"],
      "discipline": "Physical Security",
      "sector": "Government",
      "subsector": "Federal",
      "confidence": "High",
      "impact_level": "High",
      "follow_up": false,
      "dedupe_key": "sha1_hash_here",
      "standard_reference": "DHS Security Guidelines"
    }
  ],
  "links": [
    {
      "ofc": "Install perimeter fencing",
      "linked_vulnerabilities": ["Inadequate Perimeter Security"]
    }
  ]
}
```

### Supabase Submission Record

**Table:** `submissions`

```json
{
  "id": "uuid",
  "type": "document",
  "status": "pending_review",
  "source": "vofc_processor",
  "document_name": "filename.pdf",
  "data": {
    "source_file": "filename.pdf",
    "processed_at": "2025-11-12T10:55:15.901050",
    "records": [...],
    "links": [...],
    "model_version": "vofc-unified:latest",
    "inserted_count": 5,
    "linked_count": 2
  }
}
```

---

## Differences from Old System

### Old System (Deprecated)

- ❌ **Chunking:** Split documents into 246 chunks
- ❌ **3-Phase Pipeline:** Phase 1 (Parser) → Phase 2 (Engine) → Phase 3 (Auditor)
- ❌ **Flask-Based:** Processed via Flask endpoints
- ❌ **Panda Signature:** Used model-calculated signatures for deduplication
- ❌ **Excel Reference:** Loaded reference data from Excel file

### Current System (Active)

- ✅ **No Chunking:** Processes entire documents
- ✅ **Unified Pipeline:** Single pass through model
- ✅ **Service-Based:** Runs as Windows service
- ✅ **Dedupe Key:** SHA1 hash for Supabase deduplication
- ✅ **Supabase Reference:** Loads live production data

---

## Monitoring & Logs

### Log Location

**File:** `C:\Tools\Ollama\Data\logs\vofc_processor*.log`

### Key Log Messages

```
[+] Processing: filename.pdf
  [1/5] Extracting text from PDF...
  ✓ Extracted 50000 characters
  [2/5] Sending to vofc-unified:latest...
  ✓ Received response (15000 chars)
  [3/5] Saving and validating JSON output...
  ✓ Saved 10 records to output.json
  [4/5] Uploading to Supabase...
  ✓ Uploaded to Supabase (5 inserted, 2 linked)
  [5/5] Archiving file...
  ✓ Processing complete
```

### Service Status

```powershell
# Check service status
nssm status VOFC-Processor

# View logs
Get-Content C:\Tools\Ollama\Data\logs\vofc_processor*.log -Tail 50
```

---

## Error Handling

### Common Issues

1. **Model Not Found:**
   - Logs warning, continues (allows service to start)
   - Check `OLLAMA_MODEL` environment variable

2. **Ollama Server Unavailable:**
   - Logs error, retries in next cycle
   - Check Ollama service is running

3. **Supabase Connection Failed:**
   - Logs warning, skips upload
   - Saves JSON locally for manual upload

4. **JSON Parse Error:**
   - Saves error file with full response
   - Logs detailed error information

5. **Schema Mismatch:**
   - Handles missing columns gracefully
   - Falls back to available columns

---

## Performance Characteristics

- **Processing Time:** ~30-60 seconds per document (depends on size)
- **Check Interval:** 30 seconds between file checks
- **Concurrent Processing:** One file at a time (sequential)
- **Memory Usage:** Loads entire document into memory (no streaming)
- **Reference Data:** Cached per processing cycle (2000 records max)

---

## Integration Points

### Frontend

- **Status Display:** Shows VOFC-Processor service status
- **File Upload:** Places files in `incoming/` directory
- **Results View:** Displays submissions from Supabase

### Flask API

- **Status Endpoint:** `/api/system/progress` - Shows service status
- **Control Endpoint:** `/api/system/control` - Service control (deprecated processing actions)
- **No Processing Endpoints:** All file processing handled by VOFC-Processor service

### Supabase

- **Production Tables:** `vulnerabilities`, `options_for_consideration`, `vulnerability_ofc_links`
- **Submission Tracking:** `submissions` table
- **Deduplication:** Uses `dedupe_key` column (if exists) or text matching

---

## Future Enhancements

1. **Dedupe Key Column:** Add `dedupe_key` column to `vulnerabilities` table for faster lookups
2. **Confidence/Impact Columns:** Add these columns if needed for metadata
3. **Streaming Processing:** For very large documents (>100MB)
4. **Parallel Processing:** Process multiple files concurrently
5. **Retry Logic:** Automatic retry for failed model calls

---

## Core Principles

### Database Schema Design Philosophy

**Rule: Form the SQL tables to the project, not the other way around.**

- **Table edits are encouraged** to maintain scalability and reliability
- The database schema should be designed to support the application's needs
- Don't constrain the application to match existing table structures
- Update tables as needed to accommodate new features and requirements
- Schema evolution is expected and should be embraced

---

### Schema-First-for-Function Approach

This approach prioritizes adding database columns to support application functionality, rather than working around missing columns in code.

#### 1. When the App Needs New Metadata

**Example:** Model outputs `confidence` and `impact_level`

```sql
ALTER TABLE vulnerabilities ADD COLUMN confidence TEXT;
ALTER TABLE vulnerabilities ADD COLUMN impact_level TEXT;
```

**Result:** No workaround in Python needed — the data is first-class in the database.

#### 2. When You Need Faster Deduplication

```sql
ALTER TABLE vulnerabilities ADD COLUMN dedupe_key TEXT UNIQUE;
CREATE INDEX idx_vulnerabilities_dedupe_key ON vulnerabilities(dedupe_key);
```

**Result:** Instant O(1) lookups for deduplication instead of text matching.

#### 3. When Linking Across Data Sources

Add a stable foreign-key link for traceability:

```sql
ALTER TABLE vulnerability_ofc_links
ADD COLUMN source_document TEXT;
```

**Result:** Every link can trace back to its origin (SAFE, FEMA, UFC, etc.).

#### 4. When You Evolve the Model Output

If you add new fields (like `impact_level`, `standard_reference`, `sector_match_level`), don't trim them in post-processing — add them to Supabase and keep them in the unified record format.

**Result:** Keeps your model, database, and interface in sync.

---

### Operational Rule-of-Thumb

| When... | Then... |
|---------|---------|
| Model adds a new JSON field | Add the column in Supabase |
| Processor warns "column does not exist" | Fix schema, not Python |
| Schema causes performance issues | Add an index |
| You refactor naming conventions | Propagate to all systems (Ollama, Flask, Supabase) |

**Key Principle:** Always fix the schema to match the application's needs, never constrain the application to match the schema.

---

## Summary

The current parsing system is a **unified, service-based pipeline** that:

- Processes entire documents without chunking
- Uses Supabase as the deduplication authority
- Runs continuously as a Windows service
- Provides structured JSON output with dedupe keys
- Integrates seamlessly with the production database

This replaces the old 3-phase chunking system and provides a more efficient, maintainable solution for document processing.

