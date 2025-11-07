# Restart Flask Service (Administrator Required)

## Problem
Flask service restart requires Administrator privileges. The route has been added but Flask needs to be restarted to load it.

## Solution: Manual Restart

**Run PowerShell as Administrator**, then run:**

```powershell
nssm restart "VOFC-Flask"
```

Or use the full path:
```powershell
C:\Tools\nssm\nssm.exe restart "VOFC-Flask"
```

## Alternative: Restart via Services

1. Press `Win + R`
2. Type `services.msc` and press Enter
3. Find "VOFC-Flask" service
4. Right-click → Restart

## Verification

After restarting, test the endpoint:

```powershell
# Test health endpoint first
Invoke-RestMethod -Uri "http://10.0.0.213:8080/api/system/health"

# Test logstream endpoint
Invoke-RestMethod -Uri "http://10.0.0.213:8080/api/system/logstream" -Method GET
```

The logstream endpoint should return Server-Sent Events (text/event-stream) content.

## Route Status

✅ Route has been added to: `C:\Tools\VOFC-Flask\routes\system.py`
- Route: `/api/system/logstream`
- Methods: `GET`, `OPTIONS`
- Line: 192

The route will be available after Flask restarts.

