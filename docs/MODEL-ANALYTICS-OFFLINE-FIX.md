# Fix Model Analytics Showing All Services Offline

## Problem

The Model Analytics & Performance page shows:
- **Flask:** Offline
- **Ollama:** Offline  
- **Supabase:** Offline
- **Model Status:** Offline

## Root Cause

The page calls `/api/system/health` to check service status. This endpoint is returning 404 because Flask hasn't been restarted since the route was added.

## Solution

**Restart Flask as Administrator:**

```powershell
# Run PowerShell as Administrator, then:
nssm restart "VOFC-Flask"
```

Wait 10-15 seconds for Flask to fully restart.

## Endpoints Used by Model Analytics

The Model Analytics page calls these endpoints:

1. **`/api/system/health`** - System health (Flask, Ollama, Supabase)
   - Flask route: `routes/system.py` line 33
   - Next.js proxy: `app/api/system/health/route.js`
   - **Status:** Needs Flask restart

2. **`/api/system/events`** - System events timeline
   - Flask route: `routes/models.py` (system events)
   - Next.js proxy: `app/api/system/events/route.js`
   - **Status:** Should work if Flask is running

3. **`/api/models/info`** - Model information
   - Flask route: `routes/models.py` (model info)
   - Next.js proxy: `app/api/models/info/route.js`
   - **Status:** Should work if Flask is running

4. **`/api/learning/stats`** - Learning statistics
   - Flask route: `routes/learning.py`
   - Next.js proxy: `app/api/learning/stats/route.js`
   - **Status:** Should work if Flask is running

## Verify the Fix

After restarting Flask, test the health endpoint:

```powershell
Invoke-RestMethod -Uri "http://10.0.0.213:8080/api/system/health" -Method GET
```

**Expected Response:**
```json
{
  "flask": "ok",
  "ollama": "ok",
  "supabase": "ok",
  "tunnel": "ok",
  "service": "PSA Processing Server",
  "urls": {
    "flask": "http://127.0.0.1:8080",
    "ollama": "http://127.0.0.1:11434",
    "tunnel": "https://flask.frostech.site"
  },
  "timestamp": "2025-11-07T09:30:00.000000"
}
```

## Frontend Behavior

The Model Analytics page:
- Fetches health data every 60 seconds
- Shows "Offline" when `health.flask !== 'ok'`, `health.ollama !== 'ok'`, or `health.supabase !== 'ok'`
- Sets `health` to `null` if the fetch fails (404, 502, etc.)

After Flask restarts, the page should automatically refresh and show:
- **Flask:** Online ✅
- **Ollama:** Online ✅ (if Ollama is running)
- **Supabase:** Online ✅ (if Supabase is accessible)

## Troubleshooting

If services still show "Offline" after restart:

1. **Check Flask is running:**
   ```powershell
   nssm status "VOFC-Flask"
   ```
   Should show: `SERVICE_RUNNING`

2. **Test health endpoint directly:**
   ```powershell
   Invoke-RestMethod -Uri "http://10.0.0.213:8080/api/system/health"
   ```

3. **Check Flask logs for errors:**
   ```powershell
   Get-Content "C:\Tools\VOFC-Flask\logs\flask.log" -Tail 50
   ```

4. **Verify route exists:**
   ```powershell
   Select-String -Path "C:\Tools\VOFC-Flask\routes\system.py" -Pattern "/api/system/health"
   ```

5. **Check Ollama service:**
   ```powershell
   nssm status "VOFC-Ollama"
   Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags"
   ```

6. **Check tunnel:**
   ```powershell
   nssm status "VOFC-Tunnel"
   Invoke-RestMethod -Uri "https://flask.frostech.site/api/system/health"
   ```

## Related Issues

- See `docs/FLASK-404-ROUTES-FIX.md` for fixing 404 errors on other routes
- See `docs/FIX-WATCHER-404.md` for fixing watcher control buttons

