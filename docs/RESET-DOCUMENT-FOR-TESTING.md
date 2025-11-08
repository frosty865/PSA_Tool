# How to Reset a Document for Testing/Reprocessing

This guide explains how to mark a document as "not processed" so you can test the deployment and reprocess it.

## Overview

The system prevents duplicate processing through several mechanisms:
1. **File location**: Processed files are moved from `incoming/` to `library/`
2. **In-memory tracking**: `processed_files` dict tracks recently processed files (resets on service restart)
3. **File hash**: Optional hash-based deduplication (in-memory only)
4. **Database**: `submissions` table has `file_hash` field for deduplication (if implemented)

## Steps to Reset a Document

### Method 0: File Stuck in `processing/` Directory

If you see a log message like:
```
⏭️  Skipping filename.pdf - already processed (0.0s ago)
```

And the file is in `C:\Tools\Ollama\Data\processing\`, it's stuck in the processing state.

**Quick Fix**:
```powershell
# Use the reset script (handles processing/ directory)
.\scripts\reset-document.ps1 -DocumentName "your-document.pdf"

# OR manually move it back
Move-Item "C:\Tools\Ollama\Data\processing\your-document.pdf" "C:\Tools\Ollama\Data\incoming\your-document.pdf"

# Then clear in-memory tracking via API or restart service
# API: POST /api/system/control with {"action": "clear_processed_tracking"}
# OR restart: .\scripts\restart-flask.ps1
```

### Method 1: Quick Reset (Recommended for Testing)

1. **Move file back to incoming/**:
   ```powershell
   # Move from library back to incoming
   Move-Item "C:\Tools\Ollama\Data\library\your-document.pdf" "C:\Tools\Ollama\Data\incoming\your-document.pdf"
   ```

2. **Remove JSON outputs** (optional, if you want clean reprocessing):
   ```powershell
   # Remove from processed directory
   Remove-Item "C:\Tools\Ollama\Data\processed\your-document_vofc.json" -ErrorAction SilentlyContinue
   
   # Remove from review directory
   Remove-Item "C:\Tools\Ollama\Data\review\your-document_vofc.json" -ErrorAction SilentlyContinue
   ```

3. **Restart the watcher service** (clears in-memory tracking):
   ```powershell
   # Restart the Flask service (which runs the watcher)
   .\scripts\restart-flask.ps1
   ```

4. **Wait 5 seconds** (if not restarting service):
   - The in-memory tracking allows reprocessing after 5 seconds
   - Or restart the service to clear immediately

### Method 2: Complete Reset (Including Database)

If you also want to remove the database submission:

1. **Follow Method 1 steps 1-2**

2. **Delete submission from database**:
   ```sql
   -- Find the submission by source_file in data JSONB
   SELECT id, data->>'source_file' as source_file 
   FROM submissions 
   WHERE data->>'source_file' LIKE '%your-document%';
   
   -- Delete the submission and related records
   DELETE FROM submission_vulnerability_ofc_links WHERE submission_id IN (
       SELECT id FROM submissions WHERE data->>'source_file' LIKE '%your-document%'
   );
   
   DELETE FROM submission_vulnerabilities WHERE submission_id IN (
       SELECT id FROM submissions WHERE data->>'source_file' LIKE '%your-document%'
   );
   
   DELETE FROM submission_options_for_consideration WHERE submission_id IN (
       SELECT id FROM submissions WHERE data->>'source_file' LIKE '%your-document%'
   );
   
   DELETE FROM submission_sources WHERE submission_id IN (
       SELECT id FROM submissions WHERE data->>'source_file' LIKE '%your-document%'
   );
   
   DELETE FROM submissions WHERE data->>'source_file' LIKE '%your-document%';
   ```

3. **Restart the watcher service**

### Method 3: PowerShell Script (Automated)

Create a script to automate the reset:

```powershell
# reset-document.ps1
param(
    [Parameter(Mandatory=$true)]
    [string]$DocumentName
)

$BASE_DIR = "C:\Tools\Ollama\Data"
$libraryPath = Join-Path $BASE_DIR "library\$DocumentName"
$incomingPath = Join-Path $BASE_DIR "incoming\$DocumentName"
$processedPath = Join-Path $BASE_DIR "processed\$($DocumentName.Replace('.pdf','').Replace('.docx',''))_vofc.json"
$reviewPath = Join-Path $BASE_DIR "review\$($DocumentName.Replace('.pdf','').Replace('.docx',''))_vofc.json"

Write-Host "Resetting document: $DocumentName" -ForegroundColor Yellow

# 1. Move from library to incoming
if (Test-Path $libraryPath) {
    Move-Item $libraryPath $incomingPath -Force
    Write-Host "✅ Moved from library to incoming" -ForegroundColor Green
} else {
    Write-Host "⚠️  File not found in library: $libraryPath" -ForegroundColor Yellow
}

# 2. Remove JSON outputs
if (Test-Path $processedPath) {
    Remove-Item $processedPath -Force
    Write-Host "✅ Removed processed JSON" -ForegroundColor Green
}

if (Test-Path $reviewPath) {
    Remove-Item $reviewPath -Force
    Write-Host "✅ Removed review JSON" -ForegroundColor Green
}

Write-Host "`nDocument reset complete!" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Restart the watcher service: .\scripts\restart-flask.ps1" -ForegroundColor Cyan
Write-Host "  2. Or wait 5 seconds for in-memory tracking to expire" -ForegroundColor Cyan
```

**Usage**:
```powershell
.\reset-document.ps1 -DocumentName "your-document.pdf"
```

## Directory Structure Reference

```
C:\Tools\Ollama\Data\
├── incoming/      → Place files here to trigger processing
├── processing/    → Temporary location during processing
├── processed/     → JSON outputs (remove to allow reprocessing)
├── library/       → Processed originals (move back to incoming/)
├── review/        → Review copies (remove to allow reprocessing)
└── errors/        → Failed documents
```

## Important Notes

1. **In-memory tracking**: The `processed_files` dict is cleared when the service restarts
2. **Time-based check**: Files can be reprocessed after 5 seconds even without restart
3. **File hash**: Currently only tracked in-memory, not in database (unless you implement it)
4. **Database submissions**: If you want to test the full sync again, delete the submission records

## Quick Commands

```powershell
# Use the reset script (handles all scenarios)
.\scripts\reset-document.ps1 -DocumentName "your-document.pdf"

# Move file back to incoming (from library)
Move-Item "C:\Tools\Ollama\Data\library\*.pdf" "C:\Tools\Ollama\Data\incoming\" -Force

# Move file from processing/ to incoming/ (if stuck)
Move-Item "C:\Tools\Ollama\Data\processing\*.pdf" "C:\Tools\Ollama\Data\incoming\" -Force

# Clear all processed JSONs (use with caution!)
Remove-Item "C:\Tools\Ollama\Data\processed\*_vofc.json" -Force
Remove-Item "C:\Tools\Ollama\Data\review\*_vofc.json" -Force

# Clear in-memory tracking (via API)
# POST to /api/system/control with: {"action": "clear_processed_tracking"}

# Restart watcher (clears in-memory tracking)
.\scripts\restart-flask.ps1
```

## API Endpoint for Clearing Tracking

You can clear the in-memory tracking without restarting the service:

```javascript
// From frontend or API client
fetch('/api/system/control', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ action: 'clear_processed_tracking' })
})
```

This clears the `processed_files` and `processed_file_hashes` dictionaries, allowing files to be reprocessed immediately.

