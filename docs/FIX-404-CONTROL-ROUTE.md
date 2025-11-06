# Fix 404 Error for /api/system/control

## Problem
The `/api/system/control` endpoint returns 404 even though:
- ✅ Route exists in `routes/system.py` (line 271)
- ✅ Blueprint is registered in `app.py` (line 36)
- ✅ Flask service is running

## Root Cause
Flask needs to be restarted to pick up route changes. The route was added/modified but Flask is still running the old code.

## Solution

### Option 1: Restart Flask Service (Recommended)

**Run as Administrator:**
```powershell
nssm restart "VOFC-Flask"
```

Wait 5-10 seconds for Flask to restart, then test:
```powershell
python scripts\test-process.py
```

### Option 2: Manual Restart via Services

1. Open **Services** (services.msc)
2. Find **VOFC-Flask**
3. Right-click → **Restart**

### Option 3: Stop and Start

```powershell
# Stop
nssm stop "VOFC-Flask"

# Wait a moment
Start-Sleep -Seconds 3

# Start
nssm start "VOFC-Flask"
```

## Verification

After restarting, test the endpoint:

```powershell
$body = @{action='process_existing'} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/api/system/control" -Method POST -Body $body -ContentType "application/json"
```

**Expected Response:**
```json
{
  "status": "ok",
  "message": "Processed X file(s), Y failed from incoming/"
}
```

## Why This Happens

Flask loads all routes when the application starts. If you:
- Add a new route
- Modify an existing route
- Change route decorators

Flask won't see these changes until it's restarted.

## Prevention

1. **Always restart Flask after route changes**
2. **Use Flask's debug mode** (auto-reloads on file changes) - but not recommended for production
3. **Test routes immediately after adding them**

## Alternative: Use Existing Endpoint

If you can't restart Flask right now, you can use the existing `/api/process/start` endpoint:

```powershell
# Process a specific file
$body = @{filename='yourfile.pdf'} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8080/api/process/start" -Method POST -Body $body -ContentType "application/json"
```

However, this only processes one file at a time, not all files in the incoming directory.

