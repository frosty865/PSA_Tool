# Tunnel 502 Error Diagnosis

## Problem

Flask is running fine locally, but getting 502 errors when accessing through tunnel:
- `Flask server unavailable (502)`
- But `curl http://localhost:8080/api/system/health` works

## Root Cause

The **tunnel service** is either:
1. Not running
2. Running but can't reach Flask on localhost:8080
3. Misconfigured (pointing to wrong port/URL)

## Quick Diagnosis

Run this script:
```powershell
.\scripts\check-tunnel-status.ps1
```

Or manually check:

### 1. Check Tunnel Service
```powershell
nssm status "VOFC-Tunnel"
```

**Expected**: `SERVICE_RUNNING`

**If stopped**:
```powershell
nssm start "VOFC-Tunnel"
```

### 2. Check Tunnel Configuration

Tunnel config should be at: `C:\Users\frost\cloudflared\config.yml`

Should contain:
```yaml
ingress:
  - hostname: flask.frostech.site
    service: http://localhost:8080
```

**Verify**:
```powershell
Get-Content "C:\Users\frost\cloudflared\config.yml"
```

### 3. Test Tunnel from Browser

Open: `https://flask.frostech.site/api/system/health`

**Expected**: JSON response with Flask health

**If 502**: Tunnel is running but can't reach Flask

### 4. Check Tunnel Logs

```powershell
Get-Content "C:\Users\frost\cloudflared\logs\cloudflared.log" -Tail 50
```

Look for:
- Connection errors
- "dial tcp 127.0.0.1:8080: connectex: No connection could be made"
- Configuration errors

## Common Fixes

### Fix 1: Restart Tunnel
```powershell
nssm restart "VOFC-Tunnel"
```

### Fix 2: Verify Flask is Listening
```powershell
# Check if Flask is listening on port 8080
netstat -ano | findstr :8080
```

Should show Flask process listening.

### Fix 3: Verify Tunnel Config
```powershell
# Check tunnel config
Get-Content "C:\Users\frost\cloudflared\config.yml"
```

Ensure `service: http://localhost:8080` is correct.

### Fix 4: Check Firewall
```powershell
# Check Windows Firewall rules
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Flask*" -or $_.DisplayName -like "*8080*"}
```

Tunnel should be able to access localhost:8080 (no firewall should block this).

## Verification

After fixes, test:

1. **Local Flask**:
   ```powershell
   curl http://localhost:8080/api/system/health
   ```
   Should return: `{"flask":"ok",...}`

2. **Tunnel Flask**:
   ```powershell
   Invoke-RestMethod -Uri "https://flask.frostech.site/api/system/health"
   ```
   Should return same response

3. **Buttons**:
   - Click "Process Existing Files"
   - Should see success, not 502 error

## Why This Happens

- **Tunnel service stopped**: NSSM service may have crashed or been stopped
- **Tunnel config wrong**: Points to wrong port or URL
- **Flask not listening**: Flask may have stopped but service shows as running
- **Network issue**: Firewall or network configuration blocking tunnel→Flask connection

## Prevention

1. **Monitor services**: Set up monitoring for tunnel service
2. **Auto-restart**: Configure NSSM to auto-restart on failure
3. **Health checks**: Regular health checks through tunnel
4. **Logging**: Monitor tunnel logs for early warning signs

