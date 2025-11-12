# VOFC Processor Architecture

## Overview

The VOFC Processor is a unified, service-ready pipeline that replaces all previous phase-based processors. It uses a single cognitive layer (`vofc-engine:latest`) to extract vulnerabilities and options for consideration from PDF documents.

## Architecture

```
PDF → Text Extraction → (Optional Reference Subset) → vofc-engine:latest → JSON Validation → Supabase Upload → Archive
```

## Components

### 1. Text Extraction
- **Tool**: PyMuPDF (fitz)
- **Process**: Extracts all text from PDF pages
- **Output**: Plain text string

### 2. Reference Context (Optional)
- **Source**: `VOFC_Library.xlsx` in `/library` directory
- **Purpose**: Provides canonical vulnerabilities and OFCs for alignment
- **Limit**: 2000 records (configurable)
- **Format**: JSON array with vulnerability, OFC, discipline, sector, subsector

### 3. Model Processing
- **Model**: `vofc-engine:latest` (Ollama)
- **Input**: Document text + reference context
- **Output**: JSON array of vulnerability/OFC records
- **Temperature**: 0.1 (low for consistency)

### 4. JSON Validation
- **Process**: Parses and validates model response
- **Error Handling**: Saves malformed JSON to `*_error.txt` for debugging
- **Output**: Validated JSON array

### 5. Supabase Upload
- **Table**: `submissions`
- **Status**: `pending_review`
- **Source**: `vofc_processor`
- **Data**: Full JSON payload with metadata

### 6. Archive
- **Destination**: `/library` directory
- **Process**: Moves processed PDF from `/incoming` to `/library`
- **Naming**: Adds timestamp if file already exists

## Directory Structure

```
C:\Tools\Ollama\Data\
├── incoming\          # Drop PDFs here for processing
├── processed\         # JSON output files
├── library\           # Archived PDFs + VOFC_Library.xlsx
├── temp\              # Failed files for manual review
└── logs\              # Service logs
```

## Service Installation

### Prerequisites
- Python 3.11+
- **Ollama server** (separate service) with `vofc-engine:latest` model
  - Default: `http://localhost:11434`
  - Configurable via `OLLAMA_BASE_URL` environment variable
- Supabase credentials (SUPABASE_URL, SUPABASE_KEY)
- NSSM (Non-Sucking Service Manager)

### Installation Steps

1. **Install Dependencies**
   ```powershell
   cd tools\vofc_processor
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```powershell
   $env:SUPABASE_URL = "https://your-project.supabase.co"
   $env:SUPABASE_KEY = "your-service-role-key"
   ```

3. **Verify Model**
   ```powershell
   ollama list
   # Should show vofc-engine:latest
   ```

4. **Install Service**
   ```powershell
   cd tools\vofc_processor
   .\install_service.ps1
   ```

5. **Verify Service**
   ```powershell
   nssm status VOFC-Processor
   ```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | Yes | - | Supabase project URL |
| `SUPABASE_KEY` | Yes | - | Supabase service role key |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL (treat as separate service) |
| `VOFC_DATA_DIR` | No | `C:\Tools\Ollama\Data` | Base data directory |

### Ollama Server Configuration

- **Server URL**: Configurable via `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- **Model Name**: `vofc-engine:latest`
- **Temperature**: 0.1
- **API Endpoint**: `/api/generate`
- **Timeout**: 300 seconds (5 minutes)
- **Validation**: JSON array format required
- **Connection**: HTTP POST requests (treats Ollama as separate server entity)

## Processing Flow

1. **Monitor** `/incoming` directory for PDF files
2. **Extract** text from PDF using PyMuPDF
3. **Load** reference subset from VOFC_Library.xlsx (if available)
4. **Call** `vofc-engine:latest` with document text + reference context
5. **Validate** JSON response from model
6. **Save** JSON output to `/processed/{filename}_vofc.json`
7. **Upload** to Supabase `submissions` table
8. **Archive** PDF to `/library` directory

## Error Handling

### Invalid JSON
- Saves raw response to `{filename}_error.txt` in `/processed`
- Logs error with full details
- Moves PDF to `/temp` for manual review

### Ollama Server Unavailable
- Checks Ollama server connectivity on startup
- Verifies model availability via `/api/tags` endpoint
- Logs error and exits if server unreachable or model not found
- Prevents service from running with invalid configuration
- Handles connection errors gracefully with clear error messages

### Supabase Upload Failure
- Logs error but continues processing
- JSON output still saved to `/processed`
- PDF still archived to `/library`

## Logging

### Log Files
- **Location**: `C:\Tools\Ollama\Data\logs\`
- **Format**: `vofc_processor_YYYYMMDD.log`
- **Rotation**: Daily

### Log Levels
- **INFO**: Normal processing flow
- **WARNING**: Non-critical issues (missing reference library, etc.)
- **ERROR**: Processing failures

### Service Logs
- **Stdout**: `vofc_processor_out.log`
- **Stderr**: `vofc_processor_err.log`

## Validation Criteria

✅ **Dropping a new PDF in `/incoming` automatically triggers processing**  
✅ **JSON output appears in `/processed`**  
✅ **File is moved to `/library`**  
✅ **A new record is visible in Supabase under `submissions` table**

## Differences from Old System

| Old (Phase-Based) | New (Unified) |
|-------------------|---------------|
| Multiple models (parser, engine, auditor) | Single model (vofc-engine) |
| Complex phase orchestration | Simple linear flow |
| Separate deduplication logic | Model handles internally |
| Multiple service dependencies | Single service |
| Complex error recovery | Simple retry on next cycle |

## Troubleshooting

### Service Not Starting
1. Check Python path in `install_service.ps1`
2. Verify model is available: `ollama list`
3. Check environment variables are set
4. Review service logs: `nssm status VOFC-Processor`

### No Processing
1. Verify PDFs are in `/incoming` directory
2. Check service is running: `nssm status VOFC-Processor`
3. Review logs in `/logs` directory
4. Verify model is responding: `ollama run vofc-engine:latest`

### Invalid JSON Errors
1. Check `*_error.txt` files in `/processed`
2. Review model response format
3. Verify model version: `ollama show vofc-engine:latest`
4. Check model training/configuration

### Supabase Upload Failures
1. Verify credentials (SUPABASE_URL, SUPABASE_KEY)
2. Check network connectivity
3. Review Supabase logs
4. Verify table schema matches expected format

## Future Enhancements

- [ ] Watchdog-based file monitoring (instead of polling)
- [ ] Retry logic for failed uploads
- [ ] Batch processing for multiple files
- [ ] Reference subset embedding for better matching
- [ ] Health check endpoint
- [ ] Metrics collection

