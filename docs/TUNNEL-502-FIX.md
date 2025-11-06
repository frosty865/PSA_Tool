# Fixing 502 Bad Gateway and 404 Errors

## Problem

Getting 502 errors when accessing Flask through tunnel:
- `Flask server unavailable (502). Check tunnel status and Flask service.`
- `GET https://flask.frostech.site/api/system/logstream 404 (Not Found)`

## Root Causes

1. **502 Bad Gateway**: Tunnel is down OR Flask service is not running
2. **404 on logstream**: Route might not be registered OR frontend accessing wrong URL

## Solutions

### Step 1: Check Flask Service Status

```powershell
# Check if Flask service is running
Get-Service "VOFC-Flask"

# Check service status via NSSM
nssm status "VOFC-Flask"

# Restart Flask if needed
nssm restart "VOFC-Flask"

# Check Flask logs
Get-Content "C:\Tools\nssm\logs\vofc_flask.log" -Tail 50
```

### Step 2: Check Tunnel Service Status

```powershell
# Check if tunnel service is running
Get-Service "VOFC-Tunnel"

# Check tunnel status via NSSM
nssm status "VOFC-Tunnel"

# Restart tunnel if needed
nssm restart "VOFC-Tunnel"

# Check tunnel logs
Get-Content "C:\Users\frost\cloudflared\logs\cloudflared.log" -Tail 50
```

### Step 3: Test Flask Locally

```powershell
# Test Flask directly (bypassing tunnel)
curl http://localhost:8080/api/system/health

# Should return:
# {"flask":"ok","ollama":"ok","supabase":"ok","tunnel":"ok"}
```

### Step 4: Test Tunnel

```powershell
# Test tunnel from browser or PowerShell
Invoke-RestMethod -Uri "https://flask.frostech.site/api/system/health"

# Should return same health check
```

### Step 5: Fix Logstream 404

The logstream route exists in Flask but frontend might be accessing it incorrectly.

**Flask Route**: `/api/system/logstream` (exists in `routes/system.py` line 192)

**Frontend Access**: The frontend in `app/admin/processing/page.jsx` is trying to access it directly via tunnel URL, which might fail if tunnel is down.

**Solution**: Use Next.js proxy route instead of direct tunnel access.

---

## Quick Fixes

### Fix 1: Restart Services

```powershell
# Restart all services
nssm restart "VOFC-Flask"
nssm restart "VOFC-Tunnel"
nssm restart "VOFC-Ollama"
```

### Fix 2: Update Frontend to Use Proxy

The frontend should use `/api/system/logstream` (Next.js proxy) instead of direct tunnel URL.

### Fix 3: Check Environment Variables

Ensure `NEXT_PUBLIC_FLASK_URL` is set correctly:
- **Development**: `http://localhost:8080`
- **Production**: `https://flask.frostech.site`

---

## Verification

After fixes, test:

1. **Flask Health** (local):
   ```powershell
   curl http://localhost:8080/api/system/health
   ```

2. **Flask Health** (tunnel):
   ```powershell
   Invoke-RestMethod -Uri "https://flask.frostech.site/api/system/health"
   ```

3. **Control Action**:
   - Click "Process Existing Files" button
   - Should see success message, not 502 error

4. **Logstream**:
   - Should see logs appearing in Live Logs section
   - No 404 errors in console

---

## Common Issues

### Issue: Tunnel shows "online" but 502 errors

**Cause**: Flask service stopped but tunnel still running

**Fix**: Restart Flask service
```powershell
nssm restart "VOFC-Flask"
```

### Issue: Flask works locally but not through tunnel

**Cause**: Tunnel configuration issue or tunnel service stopped

**Fix**: Restart tunnel service
```powershell
nssm restart "VOFC-Tunnel"
```

### Issue: 404 on logstream

**Cause**: Frontend accessing wrong URL or route not registered

**Fix**: Ensure frontend uses Next.js proxy (`/api/system/logstream`) not direct tunnel URL

---

## Service Dependencies

```
VOFC-Tunnel (Cloudflare) → VOFC-Flask (Flask app) → VOFC-Ollama (Ollama API)
```

All three services must be running for full functionality.

