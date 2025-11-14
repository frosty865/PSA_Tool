# Service Migration Status

## Services with Code to Migrate

### ✅ Flask Server
- **Status**: Ready for migration
- **Location**: `C:\Tools\VOFC-Flask`
- **Files**: `app.py`, `routes/`, `services/`, `config/`, `tools/`, `requirements.txt`, `start.ps1`
- **Migration Script**: Included in `migrate-all-services.ps1`

### ✅ Processor Service
- **Status**: Ready for migration
- **Location**: `C:\Tools\VOFC-Processor`
- **Files**: `tools/vofc_processor/` directory
- **Migration Script**: Included in `migrate-all-services.ps1`

## Services with Configuration Only

### ⚠️ Tunnel Service (VOFC-Tunnel)
- **Status**: Configuration files only (no Python code)
- **Location**: `C:\Tools\VOFC-Tunnel` (for reference files)
- **Actual Config**: 
  - `C:\Tools\cloudflared\config.yaml` (actual config)
  - `C:\Users\frost\cloudflared\config.yml` (service config)
- **Files to Migrate**:
  - `cloudflared-config.yml` (reference copy)
  - `fix-tunnel-service.ps1` (utility script)
- **Service Type**: Runs `cloudflared.exe` via NSSM (not Python)
- **Migration Script**: Included in `migrate-all-services.ps1` (Step 3)

### ❓ Model Manager (VOFC-ModelManager)
- **Status**: Not found in project
- **Location**: `C:\Tools\VOFC-ModelManager` (if exists)
- **Files**: Unknown - may be separate service or integrated elsewhere
- **Migration Script**: Checks for files in `migrate-all-services.ps1` (Step 4)

## Migration Summary

| Service | Code Files | Config Files | Status |
|---------|-----------|--------------|--------|
| Flask | ✅ Yes | ✅ Yes | ✅ Ready |
| Processor | ✅ Yes | ✅ Yes | ✅ Ready |
| Tunnel | ❌ No (cloudflared.exe) | ✅ Yes | ✅ Ready |
| Model Manager | ❓ Unknown | ❓ Unknown | ⚠️ Check needed |

## What Gets Migrated

### Flask Server (`C:\Tools\VOFC-Flask`)
- All Python code (app.py, routes, services)
- Configuration files
- Utility tools
- Requirements and startup scripts

### Processor (`C:\Tools\VOFC-Processor`)
- Processor Python code
- Installation scripts
- Requirements

### Tunnel (`C:\Tools\VOFC-Tunnel`)
- Reference configuration file
- Utility scripts
- **Note**: Actual tunnel runs cloudflared.exe, not Python

### Model Manager (`C:\Tools\VOFC-ModelManager`)
- Only if files are found
- Script checks common locations

## Running Migration

```powershell
# Complete migration (all services)
.\scripts\migrate-all-services.ps1
```

This will:
1. Migrate Flask server
2. Migrate Processor service
3. Copy Tunnel configuration files
4. Check for and migrate Model Manager files (if found)

## After Migration

### Tunnel Service
- No code changes needed (runs cloudflared.exe)
- Configuration files are reference copies
- Actual config remains at `C:\Tools\cloudflared\config.yaml`

### Model Manager
- If files were found, they're migrated
- If not found, service may be separate or integrated elsewhere
- Check `C:\Tools\VOFC-ModelManager` after migration

