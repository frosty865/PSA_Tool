# NSSM Service Configuration Errors

## Summary of Issues Found

### ✅ Services with Errors

1. **vofc-flask / VOFC-Flask** (both services exist, pointing to same config)
   - ❌ **Application path missing**: `C:\Tools\PSA-Flask\venv\Scripts\python.exe`
   - ✅ **VOFC-Flask venv exists**: `C:\Tools\VOFC-Flask\venv\Scripts\python.exe`
   - ❌ **AppParameters incorrect**: `server.py` (should be `-m waitress --listen=0.0.0.0:8080 server:app`)
   - ✅ **AppDirectory exists**: `C:\Tools\PSA-Flask`

2. **VOFC-Processor**
   - ⚠️ **AppDirectory is old location**: `C:\Tools\vofc_processor`
   - ✅ **Should be**: `C:\Tools\VOFC-Processor` (exists)
   - ✅ **Application exists**: `C:\Tools\python\python.exe`

3. **VOFC-ModelManager**
   - ❌ **AppDirectory missing**: `C:\Tools\py_scripts\model_manager`
   - ⚠️ **Service may need to be removed or reconfigured**

4. **VOFC-AutoRetrain**
   - ❌ **AppDirectory missing**: `C:\Tools\py_scripts\auto_retrain`
   - ⚠️ **Service may need to be removed or reconfigured**

### ✅ Services with Correct Configuration

- **VOFC-Tunnel**: ✅ All paths exist, but service is STOPPED
  - ⚠️ **CRITICAL**: This service is required for production!
  - Vercel (production frontend) depends on `https://flask.frostech.site` to access Flask API
  - Service must be running for production to work
  - See fix script: `.\scripts\fix-tunnel-service-complete.ps1`
- **VOFC-Ollama**: ✅ All paths exist

## Fixes Required

### 1. Fix Flask Service (vofc-flask)

**Option A: Use VOFC-Flask (recommended)**
```powershell
nssm set vofc-flask Application "C:\Tools\VOFC-Flask\venv\Scripts\python.exe"
nssm set vofc-flask AppDirectory "C:\Tools\VOFC-Flask"
nssm set vofc-flask AppParameters "-m waitress --listen=0.0.0.0:8080 server:app"
nssm restart vofc-flask
```

**Option B: Use PSA-Flask (if venv needs to be created)**
```powershell
# First create venv in PSA-Flask
cd C:\Tools\PSA-Flask
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Then update service
nssm set vofc-flask Application "C:\Tools\PSA-Flask\venv\Scripts\python.exe"
nssm set vofc-flask AppDirectory "C:\Tools\PSA-Flask"
nssm set vofc-flask AppParameters "-m waitress --listen=0.0.0.0:8080 server:app"
nssm restart vofc-flask
```

**Remove duplicate VOFC-Flask service (if exists):**
```powershell
nssm remove VOFC-Flask confirm
```

### 2. Fix Processor Service

```powershell
cd C:\Tools\VOFC-Processor
.\install_service.ps1
```

Or manually:
```powershell
nssm set VOFC-Processor AppDirectory "C:\Tools\VOFC-Processor"
nssm set VOFC-Processor AppParameters "C:\Tools\VOFC-Processor\vofc_processor.py"
nssm restart VOFC-Processor
```

### 3. Fix Model Manager Service

**Option A: Remove service (if not needed)**
```powershell
nssm stop VOFC-ModelManager
nssm remove VOFC-ModelManager confirm
```

**Option B: Reconfigure (if files exist elsewhere)**
```powershell
# Find where model_manager.py actually is
Get-ChildItem -Path C:\Tools -Recurse -Filter "model_manager.py" -ErrorAction SilentlyContinue

# Then update service with correct path
nssm set VOFC-ModelManager AppDirectory "<actual_path>"
nssm set VOFC-ModelManager AppParameters "<actual_path>\model_manager.py"
```

### 4. Fix AutoRetrain Service

**Option A: Remove service (if not needed)**
```powershell
nssm stop VOFC-AutoRetrain
nssm remove VOFC-AutoRetrain confirm
```

**Option B: Reconfigure (if files exist elsewhere)**
```powershell
# Find where auto_retrain_job.py actually is
Get-ChildItem -Path C:\Tools -Recurse -Filter "auto_retrain_job.py" -ErrorAction SilentlyContinue

# Then update service with correct path
nssm set VOFC-AutoRetrain AppDirectory "<actual_path>"
nssm set VOFC-AutoRetrain AppParameters "<actual_path>\auto_retrain_job.py"
```

### 5. Fix Tunnel Service (CRITICAL for Production)

**This is REQUIRED for production - Vercel needs this tunnel!**

```powershell
# Run the complete fix script (as Administrator)
.\scripts\fix-tunnel-service-complete.ps1
```

Or manually:
```powershell
nssm set VOFC-Tunnel Application "C:\Tools\cloudflared\cloudflared.exe"
nssm set VOFC-Tunnel AppDirectory "C:\Tools\cloudflared"
nssm set VOFC-Tunnel AppParameters "--config C:\Tools\cloudflared\config.yaml tunnel run ollama-tunnel"
nssm start VOFC-Tunnel
```

**Verify tunnel is working:**
```powershell
curl https://flask.frostech.site/api/system/health
```

## Quick Fix Script

```powershell
# Fix Flask (use VOFC-Flask)
nssm set vofc-flask Application "C:\Tools\VOFC-Flask\venv\Scripts\python.exe"
nssm set vofc-flask AppDirectory "C:\Tools\VOFC-Flask"
nssm set vofc-flask AppParameters "-m waitress --listen=0.0.0.0:8080 server:app"

# Fix Processor
cd C:\Tools\VOFC-Processor
.\install_service.ps1

# Remove duplicate VOFC-Flask if exists
nssm remove VOFC-Flask confirm 2>&1 | Out-Null

# Check Model Manager and AutoRetrain - remove if not needed
# nssm remove VOFC-ModelManager confirm
# nssm remove VOFC-AutoRetrain confirm
```

## Verification

After fixes, verify all services:

```powershell
$services = @('vofc-flask', 'VOFC-Processor', 'VOFC-Tunnel', 'VOFC-Ollama')
foreach ($svc in $services) {
    Write-Host "`n=== $svc ===" -ForegroundColor Cyan
    $app = nssm get $svc Application
    $dir = nssm get $svc AppDirectory
    Write-Host "Application: $app"
    Write-Host "AppDirectory: $dir"
    if ($app -and (Test-Path $app)) { Write-Host "✓ Application exists" -ForegroundColor Green } else { Write-Host "✗ Application missing" -ForegroundColor Red }
    if ($dir -and (Test-Path $dir)) { Write-Host "✓ Directory exists" -ForegroundColor Green } else { Write-Host "✗ Directory missing" -ForegroundColor Red }
}
```


