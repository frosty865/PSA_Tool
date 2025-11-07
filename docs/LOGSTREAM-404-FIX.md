# Logstream 404 Error Fix

## Problem
Frontend was getting 404 errors when trying to access `/api/system/logstream`:
```
GET https://flask.frostech.site/api/system/logstream 404 (Not Found)
```

## Root Cause
The `logstream` route existed in the project's `routes/system.py` but was missing from the running Flask instance at `C:\Tools\VOFC-Flask\routes\system.py`.

## Solution
Added the `logstream` route to `C:\Tools\VOFC-Flask\routes\system.py`:

```python
@system_bp.route('/api/system/logstream', methods=['GET', 'OPTIONS'])
def log_stream():
    """Server-Sent Events streaming of live processor log."""
    # ... SSE implementation
```

## Next Steps

**Restart Flask service to apply the change:**
```powershell
nssm restart "VOFC-Flask"
```

## Verification

After restarting, test the endpoint:
```powershell
# Test locally
Invoke-RestMethod -Uri "http://10.0.0.213:8080/api/system/logstream" -Method GET

# Test via tunnel
Invoke-RestMethod -Uri "https://flask.frostech.site/api/system/logstream" -Method GET
```

The endpoint should return a Server-Sent Events stream (text/event-stream content type).

## Note
The route streams logs from `C:\Tools\Ollama\Data\automation\vofc_auto_processor.log`. Ensure this file exists or the route will return an error message in the stream.

