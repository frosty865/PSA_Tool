# Service Migration Guide - Unified PSA Naming Convention

## Overview

This guide helps migrate all services to the unified `PSA-*` naming convention and folder structure.

## Service Name Changes

| Old Service Name | New Service Name | Location |
|-----------------|------------------|----------|
| `VOFC-Flask` | `PSA-Flask` | `C:\Tools\PSA-Flask` |
| `VOFC-Processor` | `PSA-Processor` | `C:\Tools\PSA-Processor` |
| `VOFC-Tunnel` / `VOFC-Tunnel-Service` | `PSA-Tunnel` | `C:\Tools\PSA-Tunnel` (if applicable) |
| `VOFC-ModelManager` / `VOFC-Model-Manager` | `PSA-ModelManager` | `C:\Tools\PSA-ModelManager` (if applicable) |

## Directory Structure Changes

| Old Path | New Path | Notes |
|----------|----------|-------|
| `C:\Tools\VOFC-Flask` | `C:\Tools\PSA-Flask` | Flask API server |
| `C:\Tools\vofc_processor` | `C:\Tools\PSA-Processor` | Document processor |
| `C:\Tools\archive\VOFC\Data` | `C:\Tools\PSA-Archive\Data` | Archive directory |
| `C:\Tools\Ollama\Data` | `C:\Tools\PSA-Data` | **Optional** - can keep as is (shared data) |

## Migration Steps

### Step 1: Stop All Services

```powershell
# Stop all services before migration
nssm stop PSA-Flask
nssm stop PSA-Processor
nssm stop PSA-Tunnel
nssm stop PSA-ModelManager

# Or if using legacy names:
nssm stop VOFC-Flask
nssm stop VOFC-Processor
nssm stop VOFC-Tunnel
nssm stop VOFC-ModelManager
```

### Step 2: Migrate Flask Server

```powershell
# Run the migration script
cd C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool
.\scripts\migrate-python-to-tools.ps1

# This creates C:\Tools\PSA-Flask with all Python code
```

### Step 3: Migrate Processor Service

```powershell
# Create new directory
New-Item -ItemType Directory -Path "C:\Tools\PSA-Processor" -Force

# Copy processor files (if they exist at old location)
if (Test-Path "C:\Tools\vofc_processor") {
    Copy-Item "C:\Tools\vofc_processor\*" "C:\Tools\PSA-Processor\" -Recurse -Force
}

# Or copy from project
Copy-Item "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\tools\vofc_processor\*" "C:\Tools\PSA-Processor\" -Recurse -Force
```

### Step 4: Update Windows Services

#### Update PSA-Flask Service

```powershell
# Remove old service (if exists)
nssm stop VOFC-Flask
nssm remove VOFC-Flask confirm

# Install new service
nssm install PSA-Flask "C:\Tools\PSA-Flask\venv\Scripts\python.exe"
nssm set PSA-Flask AppParameters "-m waitress --listen=0.0.0.0:8080 app:app"
nssm set PSA-Flask AppDirectory "C:\Tools\PSA-Flask"
nssm set PSA-Flask Start SERVICE_AUTO_START
nssm start PSA-Flask
```

#### Update PSA-Processor Service

```powershell
# Use the updated install script
cd C:\Tools\PSA-Processor
.\install_service.ps1

# Or manually:
nssm stop VOFC-Processor
nssm remove VOFC-Processor confirm

nssm install PSA-Processor "C:\Tools\python\python.exe" "C:\Tools\PSA-Processor\vofc_processor.py"
nssm set PSA-Processor AppDirectory "C:\Tools\PSA-Processor"
nssm set PSA-Processor Start SERVICE_AUTO_START
nssm start PSA-Processor
```

#### Update PSA-Tunnel Service (if applicable)

```powershell
# Stop old service
nssm stop VOFC-Tunnel
# Or: nssm stop VOFC-Tunnel-Service

# Update service name (if using NSSM)
nssm set VOFC-Tunnel Name "PSA-Tunnel"
# Or reinstall with new name
```

#### Update PSA-ModelManager Service (if applicable)

```powershell
# Stop old service
nssm stop VOFC-ModelManager
# Or: nssm stop VOFC-Model-Manager

# Update service name
nssm set VOFC-ModelManager Name "PSA-ModelManager"
# Or reinstall with new name
```

### Step 5: Update Environment Variables

Update `.env` files in each service directory:

```powershell
# Update PSA-Flask .env
# No changes needed - paths are already updated in code

# Update PSA-Processor .env (if it has one)
# Check for any hardcoded paths
```

### Step 6: Verify Services

```powershell
# Check service status
nssm status PSA-Flask
nssm status PSA-Processor
nssm status PSA-Tunnel
nssm status PSA-ModelManager

# Check service logs
Get-Content "C:\Tools\PSA-Data\logs\psa_flask.log" -Tail 50
Get-Content "C:\Tools\PSA-Data\logs\psa_processor.log" -Tail 50
```

### Step 7: Test Endpoints

```powershell
# Test Flask API
Invoke-WebRequest -Uri "http://localhost:8080/api/system/health"

# Check processor is running
nssm status PSA-Processor
```

## Backward Compatibility

All code has been updated to:
1. **Check new service names first** (`PSA-*`)
2. **Fall back to legacy names** (`VOFC-*`) if new ones don't exist
3. **Support both during transition period**

This means you can migrate services gradually without breaking functionality.

## Rollback Plan

If issues occur, you can rollback by:

1. **Stop new services**
   ```powershell
   nssm stop PSA-Flask
   nssm stop PSA-Processor
   ```

2. **Restart legacy services** (if they still exist)
   ```powershell
   nssm start VOFC-Flask
   nssm start VOFC-Processor
   ```

3. **Update code references** (temporarily) to use legacy names first

## Verification Checklist

After migration:
- [ ] All services running with new names
- [ ] Flask API responds at `http://localhost:8080`
- [ ] Health check endpoint works
- [ ] Processor service processes files correctly
- [ ] Logs are written to correct locations
- [ ] No errors in service logs
- [ ] Next.js frontend can connect to Flask backend

## Troubleshooting

### Service Won't Start

1. Check service logs: `nssm status PSA-Flask`
2. Check Python path: `nssm get PSA-Flask Application`
3. Check working directory: `nssm get PSA-Flask AppDirectory`
4. Verify files exist at new location

### Import Errors

1. Verify all Python files were copied
2. Check `__init__.py` files exist in packages
3. Verify virtual environment is set up correctly

### Path Not Found Errors

1. Check environment variables in `.env` file
2. Verify data directories exist: `C:\Tools\PSA-Data\` (or `C:\Tools\Ollama\Data`)
3. Check service working directory matches file locations

## Next Steps

After successful migration:
1. Update documentation with new paths
2. Update any deployment scripts
3. Remove legacy service names (after verification period)
4. Clean up old directories (after backup)

