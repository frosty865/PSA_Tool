# Fix Paused Service Issue

## Problem

Service gets stuck in `SERVICE_PAUSED` state and cannot be started normally.

**Error:**
```
VOFC-Processor: Unexpected status SERVICE_PAUSED in response to START control.
```

## Solution

### Option 1: Use the Fix Script (Recommended)

Run PowerShell **as Administrator**, then:

```powershell
.\scripts\fix-paused-service.ps1 -ServiceName VOFC-Processor
```

The script will:
1. Check if running as Administrator
2. Resume the service if paused
3. Stop the service completely
4. Wait for it to fully stop
5. Start it again
6. Verify it's running

### Option 2: Manual Fix (Administrator Required)

1. **Open PowerShell as Administrator:**
   - Right-click PowerShell
   - Select "Run as Administrator"

2. **Resume the service (if paused):**
   ```powershell
   sc.exe continue VOFC-Processor
   Start-Sleep -Seconds 2
   ```

3. **Stop the service:**
   ```powershell
   sc.exe stop VOFC-Processor
   Start-Sleep -Seconds 5
   ```

4. **Verify it's stopped:**
   ```powershell
   sc.exe query VOFC-Processor
   ```
   Should show `STATE: 1 STOPPED`

5. **Start the service:**
   ```powershell
   nssm start VOFC-Processor
   ```

6. **Verify it's running:**
   ```powershell
   nssm status VOFC-Processor
   ```
   Should show `SERVICE_RUNNING`

### Option 3: Force Remove and Reinstall (Last Resort)

If the service is completely stuck:

1. **Remove the service:**
   ```powershell
   nssm stop VOFC-Processor
   nssm remove VOFC-Processor confirm
   Start-Sleep -Seconds 5
   ```

2. **Reinstall the service:**
   ```powershell
   cd C:\Tools\py_scripts\vofc_processor
   .\install_service.ps1
   ```

## Why This Happens

Services can get stuck in PAUSED state when:
- Service was manually paused
- Service process crashed but Windows didn't fully stop it
- Service control commands were interrupted
- Service is waiting for a resource that's unavailable

## Prevention

- Always use `nssm stop` or `sc.exe stop` before restarting services
- Don't pause services manually unless necessary
- Ensure services have proper error handling to avoid crashes

## Troubleshooting

### "Access is denied" Error

**Solution:** Run PowerShell as Administrator. Service control requires elevated privileges.

### Service Still Paused After Stop

**Solution:** Use `sc.exe continue` first, then stop, then start.

### Service Won't Start After Fix

**Check:**
1. Service configuration: `nssm edit VOFC-Processor`
2. Python path: `nssm get VOFC-Processor Application`
3. Script path: `nssm get VOFC-Processor AppParameters`
4. Logs: `C:\Tools\Ollama\Data\logs\vofc_processor*.log`

### Service Keeps Getting Paused

**Possible causes:**
- Service script has an error and crashes immediately
- Missing Python dependencies
- Invalid file paths
- Permission issues

**Check logs:**
```powershell
Get-Content "C:\Tools\Ollama\Data\logs\vofc_processor*.log" -Tail 50
```

