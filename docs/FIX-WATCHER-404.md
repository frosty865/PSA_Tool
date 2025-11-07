# Fix Watcher Buttons 404 Error

## Problem

All watcher buttons return "error: not found" because Flask hasn't been restarted to load the new `/api/system/control` route.

## Solution

**Restart Flask service as Administrator:**

```powershell
# Run PowerShell as Administrator, then:
nssm restart "VOFC-Flask"
```

Wait 5-10 seconds for Flask to restart, then the watcher buttons will work.

## Verification

After restarting Flask, test the endpoint:

```powershell
$body = @{action='start_watcher'} | ConvertTo-Json
Invoke-RestMethod -Uri "http://10.0.0.213:8080/api/system/control" -Method POST -Body $body -ContentType "application/json"
```

**Expected Response:**
```json
{
  "status": "ok",
  "message": "Watcher started"
}
```

## Route Status

✅ Route has been added to: `C:\Tools\VOFC-Flask\routes\system.py`
- Route: `/api/system/control`
- Methods: `POST`, `OPTIONS`
- Line: 192

The route will be available after Flask restarts.

## Available Actions

- `start_watcher` - Start folder watcher
- `stop_watcher` - Stop folder watcher
- `process_existing` - Process all files in incoming/
- `sync_review` - Sync review files to Supabase
- `clear_errors` - Clear error folder

## Alternative: Restart via Services

1. Press `Win + R`
2. Type `services.msc` and press Enter
3. Find "VOFC-Flask" service
4. Right-click → Restart

