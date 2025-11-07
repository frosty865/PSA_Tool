# Fix Flask 404 Errors for Control and Logstream Routes

## Problem

When clicking watcher control buttons or accessing the logstream, you see:
- `Error: Not found` or `404 (Not Found)`
- Routes `/api/system/control` and `/api/system/logstream` are not available

## Root Cause

Flask hasn't been restarted since the routes were added to `C:\Tools\VOFC-Flask\routes\system.py`. Flask loads routes at startup, so new routes won't be available until Flask restarts.

## Solution

**Restart Flask as Administrator:**

```powershell
# Run PowerShell as Administrator, then:
nssm restart "VOFC-Flask"
```

Wait 10-15 seconds for Flask to fully restart.

## Verify the Fix

After restarting, test the endpoints:

### Test Control Endpoint
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

### Test Logstream Endpoint
```powershell
Invoke-RestMethod -Uri "http://10.0.0.213:8080/api/system/logstream" -Method GET
```

**Expected:** SSE stream starts (you'll see log lines)

## Alternative: Use the Restart Script

```powershell
.\scripts\restart-flask.ps1
```

## Why This Happens

1. Routes are defined in `C:\Tools\VOFC-Flask\routes\system.py`
2. Flask loads all routes when it starts
3. If Flask was running before routes were added, they won't be available
4. Restarting Flask reloads all route definitions

## Prevention

After adding new routes to `C:\Tools\VOFC-Flask\routes\`, always restart Flask:

```powershell
nssm restart "VOFC-Flask"
```

## Troubleshooting

If restart doesn't fix it:

1. **Check Flask is running:**
   ```powershell
   nssm status "VOFC-Flask"
   ```
   Should show: `SERVICE_RUNNING`

2. **Check Flask logs:**
   ```powershell
   Get-Content "C:\Tools\VOFC-Flask\logs\flask.log" -Tail 50
   ```
   Look for import errors or route registration issues.

3. **Verify route file exists:**
   ```powershell
   Test-Path "C:\Tools\VOFC-Flask\routes\system.py"
   ```
   Should return: `True`

4. **Check route is registered in app.py:**
   ```powershell
   Select-String -Path "C:\Tools\VOFC-Flask\server.py" -Pattern "system_bp|system"
   ```
   Should show blueprint registration.

