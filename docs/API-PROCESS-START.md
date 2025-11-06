# API Endpoint: `/api/process/start`

## What SHOULD Be There

### Endpoint Details
- **URL**: `http://localhost:8080/api/process/start`
- **Method**: `POST` (NOT GET - visiting in browser won't work)
- **Content-Type**: `application/json`
- **Required Body**: `{"filename": "yourfile.pdf"}`

### Expected Behavior

1. **Receives**: JSON with filename
2. **Processes**: File using `services/processor.py::process_file()`
3. **Returns**: JSON with processing result

### What It Actually Does

The route calls `process_file()` from `services/processor.py`, which:

1. **Finds the file**: Looks in `data/incoming/` directory (or uses full path if provided)
2. **Extracts text**: Uses appropriate parser (PDF, DOCX, TXT, XLSX)
3. **Runs Ollama model**: Sends first 4000 characters to `psa-engine:latest`
4. **Returns**: Raw model response (text analysis)

**Note**: This is a SIMPLE processor - it does NOT:
- ❌ Preprocess into chunks
- ❌ Post-process results
- ❌ Save to Supabase
- ❌ Move files to library/processed
- ❌ Create JSON outputs

### Current Implementation

```python
@process_bp.route('/api/process/start', methods=['POST', 'OPTIONS'])
def start_processing():
    """Start processing a file"""
    # Requires: {"filename": "file.pdf"}
    # Calls: services.processor.process_file(filename)
    # Returns: {"success": True, "result": <model_output>}
```

### What You'll Get Back

**Success Response (200)**:
```json
{
  "success": true,
  "result": "<Ollama model text response>",
  "service": "PSA Processing Server"
}
```

**Error Response (400/500)**:
```json
{
  "success": false,
  "error": "error message",
  "service": "PSA Processing Server"
}
```

## How to Test It

### Using curl:
```bash
curl -X POST http://localhost:8080/api/process/start \
  -H "Content-Type: application/json" \
  -d '{"filename": "yourfile.pdf"}'
```

### Using PowerShell:
```powershell
$body = @{filename='yourfile.pdf'} | ConvertTo-Json
Invoke-RestMethod -Uri 'http://localhost:8080/api/process/start' -Method POST -Body $body -ContentType 'application/json'
```

### Using Python:
```python
import requests
response = requests.post(
    'http://localhost:8080/api/process/start',
    json={'filename': 'yourfile.pdf'}
)
print(response.json())
```

## Why You See "Nothing"

1. **It's a POST endpoint** - Visiting `http://localhost:8080/api/process/start` in a browser sends a GET request, which returns 404
2. **Flask needs restart** - If the route returns 404 even with POST, Flask hasn't loaded the route yet
3. **File must exist** - The file must be in `data/incoming/` directory

## Full Pipeline Alternative

If you want the FULL processing pipeline (preprocess → model → postprocess → save), use:

- **`/api/system/control`** with `{"action": "process_existing"}` - Processes all files in `C:\Tools\Ollama\Data\incoming`
- **`/api/process`** (POST with multipart/form-data) - Uploads and processes a file through the full pipeline

## Route Status

- ✅ Route exists: `routes/process.py` line 24
- ✅ Blueprint registered: `app.py` line 38
- ⚠️ **Flask needs restart** to load the route (currently returns 404)

## Fix

Restart Flask service:
```powershell
# Run as Administrator
nssm restart "VOFC-Flask"
```

Then test with POST request (not browser GET).

