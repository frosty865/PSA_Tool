# API Endpoint: `/api/run_model`

## What It Does

Runs the Ollama model directly with text input. This endpoint calls Ollama's API directly at `http://127.0.0.1:11434/api/generate`.

## Endpoint Details

- **URL**: `http://localhost:8080/api/run_model`
- **Method**: `POST`
- **Content-Type**: `application/json`

## Request Format

```json
{
  "text": "your text input here",
  "model": "vofc-engine:latest"  // optional, defaults to vofc-engine:latest
}
```

**Note**: Text is automatically limited to 4000 characters.

## Response Format

**Success (200)**:
Returns the full Ollama API response:
```json
{
  "model": "vofc-engine:latest",
  "created_at": "2025-01-XX...",
  "response": "<model's text response>",
  "done": true,
  ...
}
```

**Error (400/500)**:
```json
{
  "error": "error message",
  "service": "PSA Processing Server"
}
```

## Examples

### Using PowerShell:
```powershell
$body = @{text='Summarize the vulnerabilities from this paragraph.'} | ConvertTo-Json
Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/run_model' -Method POST -Body $body -ContentType 'application/json'
```

### Using curl (PowerShell):
```powershell
curl.exe -X POST http://127.0.0.1:8080/api/run_model `
  -H "Content-Type: application/json" `
  -d "{`"text`": `"Summarize the vulnerabilities from this paragraph.`"}"
```

### Using Python:
```python
import requests

response = requests.post(
    'http://localhost:8080/api/run_model',
    json={'text': 'Summarize the vulnerabilities from this paragraph.'}
)
print(response.json())
```

## Implementation Details

The route:
1. Accepts JSON with `text` field (limited to 4000 chars)
2. Calls Ollama directly at `http://127.0.0.1:11434/api/generate`
3. Uses model `vofc-engine:latest` by default
4. Returns the full Ollama API response

## Route Location

- **File**: `routes/system.py`
- **Blueprint**: `system_bp`
- **Line**: ~453

## Status

- ✅ Route added to `routes/system.py`
- ✅ Blueprint already registered in `app.py`
- ⚠️ **Flask needs restart** to load the route

## Fix

Restart Flask service:
```powershell
# Run as Administrator
nssm restart "VOFC-Flask"
```

Wait 5-10 seconds, then test:
```powershell
$body = @{text='test input'} | ConvertTo-Json
Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/run_model' -Method POST -Body $body -ContentType 'application/json'
```

## Direct Ollama Alternative

If Flask isn't available, call Ollama directly:
```powershell
$body = @{
    model='vofc-engine:latest'
    prompt='test input'
    stream=$false
} | ConvertTo-Json

Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/generate' -Method POST -Body $body -ContentType 'application/json'
```
