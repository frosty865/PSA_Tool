# Ollama Auto Processor

## Overview

The `ollama_auto_processor.py` script is an automated document processing system that monitors the incoming directory, processes documents through the full pipeline, and manages file lifecycle according to the new directory structure.

## Directory Structure

All operations occur within `C:\Tools\Ollama\Data` (configurable via `VOFC_BASE_DIR` environment variable):

```
C:\Tools\Ollama\Data\
├── incoming/      → New documents from website
├── processed/     → JSON outputs from successful runs
├── library/       → Archive of original documents (moved after processing)
├── errors/        → Failed documents + .txt error logs
├── review/        → Temporary admin review copies of parsed JSON
└── automation/    → progress.json + vofc_auto_processor.log
```

## Processing Pipeline

Each document goes through three stages:

1. **Preprocessing** (`services/preprocess.py`)
   - Extract text from PDF, DOCX, TXT files
   - Normalize and clean text
   - Chunk into sentence-aware segments

2. **Model Inference** (`services/ollama_client.py`)
   - Run Ollama model on each chunk
   - Extract vulnerabilities and OFCs
   - Parse JSON responses

3. **Post-processing** (`services/postprocess.py`)
   - Clean and normalize results
   - Deduplicate vulnerabilities
   - Resolve taxonomy (Discipline, Sector, Subsector) to Supabase IDs
   - Map to production-ready format

## File Lifecycle

### Successful Processing

1. Document placed in `incoming/`
2. Processing runs (preprocess → model → postprocess)
3. JSON output saved to `processed/{filename}_vofc.json`
4. Original document moved to `library/{filename}`
5. JSON copied to `review/{filename}_vofc.json` for admin validation

### Failed Processing

1. Document placed in `incoming/`
2. Processing fails at any stage
3. Error log written to `errors/{filename}_error.txt` with full traceback
4. Original document moved to `errors/{filename}`

## Progress Tracking

The `automation/progress.json` file tracks file counts across all directories:

```json
{
  "timestamp": "2024-01-15 14:30:00",
  "incoming": 5,
  "processed": 42,
  "library": 38,
  "errors": 3,
  "review": 40,
  "status": "running"
}
```

## Logging

All operations are logged to `automation/vofc_auto_processor.log` with timestamps and log levels:

```
2024-01-15 14:30:00 | INFO | Starting document processing cycle
2024-01-15 14:30:01 | INFO | Processing: document.pdf
2024-01-15 14:30:05 | INFO | Extracted 12 chunks from document.pdf
2024-01-15 14:30:15 | INFO | Model returned 12 results
2024-01-15 14:30:16 | INFO | Post-processing complete: 8 unique records
2024-01-15 14:30:17 | INFO | ✅ Successfully processed document.pdf
```

## Usage

### Run as Background Service

The script runs continuously as a background service with two main components:

1. **Folder Watcher** - Monitors `incoming/` for new files in real-time
2. **Supabase Sync** - Periodically syncs approved review files to production tables

```bash
python ollama_auto_processor.py
```

The script will:
- Process any existing files in `incoming/` on startup
- Start the folder watcher to monitor for new files
- Run Supabase sync every 10 minutes
- Continue running until interrupted (Ctrl+C)

### Run as Windows Service (NSSM)

For production, run as a Windows service using NSSM:

```powershell
# Install as service
nssm install VOFC-AutoProcessor "C:\Python\python.exe" "C:\path\to\ollama_auto_processor.py"

# Set working directory
nssm set VOFC-AutoProcessor AppDirectory "C:\path\to\PSA_Tool"

# Start service
nssm start VOFC-AutoProcessor
```

### Environment Variables

- `VOFC_BASE_DIR` - Base directory for all operations (default: `C:\Tools\Ollama\Data`)

## Integration with Review System

1. Processed JSON files are copied to `review/` for admin validation
2. Admins review files in `/admin/review` page and approve/reject submissions
3. **Automatic Sync**: The auto-processor checks for approved submissions every 10 minutes
4. Approved review files are automatically synced to Supabase production tables
5. Synced files are moved from `review/` to `processed/` after successful sync

### Supabase Sync Process

- Every 10 minutes, the script checks all JSON files in `review/`
- For each file, it queries Supabase `submissions` table for matching approved records
- If approved, the vulnerabilities and OFCs are inserted into production tables
- The review file is moved to `processed/` after successful sync

## Error Handling

- All errors are logged with full tracebacks
- Failed documents are moved to `errors/` with error logs
- Processing continues even if individual files fail
- Progress is updated after each file

## Supported File Types

- `.pdf` - PDF documents (via PyMuPDF)
- `.docx` - Word documents (via python-docx)
- `.txt` - Plain text files
- `.xlsx` - Excel files (via openpyxl)

## Dependencies

- `services/preprocess.py` - Document preprocessing
- `services/ollama_client.py` - Ollama model interaction
- `services/postprocess.py` - Result post-processing
- `services/supabase_client.py` - Taxonomy resolution and Supabase sync
- `watchdog` - File system monitoring (install with: `pip install watchdog`)

## Features

### Real-Time Folder Monitoring

- Uses `watchdog` library to monitor `incoming/` directory
- Automatically processes new files as soon as they appear
- Prevents duplicate processing with file tracking
- Waits for file write completion before processing

### Automatic Supabase Sync

- Checks for approved review files every 10 minutes
- Queries Supabase `submissions` table for approval status
- Inserts approved records into production `vulnerabilities` and `options_for_consideration` tables
- Moves synced files to `processed/` after successful sync

### Error Handling

- All errors are logged with full tracebacks
- Failed documents are moved to `errors/` with error logs
- Processing continues even if individual files fail
- Supabase sync errors don't stop the main loop

## Future Enhancements

- Email notifications on processing failures
- Retry logic for transient failures
- Batch processing optimization
- Configurable sync interval
- Webhook notifications for processing completion

