# Complete Service Migration Guide

## Overview

This guide covers migrating **ALL** services to `C:\Tools` with organized structure.

## Services to Migrate

1. **Flask Server** → `C:\Tools\PSA-Flask`
2. **Processor Service** → `C:\Tools\PSA-Processor`
3. **Utility Tools** → Included in Flask migration

## Quick Migration

### Option 1: Complete Migration (Recommended)

```powershell
.\scripts\migrate-all-services.ps1
```

This migrates:
- Flask server (app.py, routes, services, config)
- Processor service (vofc_processor)
- All utility tools

### Option 2: Individual Migration

#### Flask Only
```powershell
.\scripts\migrate-python-to-tools.ps1
```

#### Processor Only
```powershell
# Manual migration
New-Item -ItemType Directory -Path "C:\Tools\PSA-Processor" -Force
Copy-Item "tools\vofc_processor\*" "C:\Tools\PSA-Processor\" -Recurse -Force
```

## Migration Steps

### Step 1: Run Complete Migration Script

```powershell
cd C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool
.\scripts\migrate-all-services.ps1
```

### Step 2: Copy Environment Files

```powershell
# Flask .env
Copy-Item ".env" "C:\Tools\PSA-Flask\.env"

# Processor .env (if it has one)
if (Test-Path "C:\Tools\vofc_processor\.env") {
    Copy-Item "C:\Tools\vofc_processor\.env" "C:\Tools\PSA-Processor\.env"
}
```

### Step 3: Set Up Virtual Environments

#### Flask Virtual Environment
```powershell
cd C:\Tools\PSA-Flask
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Processor Virtual Environment (if needed)
```powershell
cd C:\Tools\PSA-Processor
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 4: Update Windows Services

#### Update Flask Service (vofc-flask)
```powershell
# Stop service
nssm stop vofc-flask

# Update paths
nssm set vofc-flask Application "C:\Tools\PSA-Flask\venv\Scripts\python.exe"
nssm set vofc-flask AppDirectory "C:\Tools\PSA-Flask"
nssm set vofc-flask AppParameters "-m waitress --listen=0.0.0.0:8080 app:app"

# Start service
nssm start vofc-flask
```

#### Update Processor Service (VOFC-Processor)
```powershell
# Use the install script (recommended)
cd C:\Tools\PSA-Processor
.\install_service.ps1

# Or manually:
nssm stop VOFC-Processor
nssm remove VOFC-Processor confirm

nssm install VOFC-Processor "C:\Tools\python\python.exe" "C:\Tools\PSA-Processor\vofc_processor.py"
nssm set VOFC-Processor AppDirectory "C:\Tools\PSA-Processor"
nssm set VOFC-Processor Start SERVICE_AUTO_START
nssm start VOFC-Processor
```

### Step 5: Verify Services

```powershell
# Check Flask
nssm status vofc-flask
Invoke-WebRequest -Uri "http://localhost:8080/api/system/health"

# Check Processor
nssm status VOFC-Processor
Get-Content "C:\Tools\Ollama\Data\logs\vofc_processor_*.log" -Tail 20
```

## Directory Structure After Migration

```
C:\Tools\
├── PSA-Flask\              # Flask API server
│   ├── app.py
│   ├── routes/
│   ├── services/
│   ├── config/
│   ├── tools/
│   ├── requirements.txt
│   ├── start.ps1
│   └── .env
│
├── PSA-Processor\          # Document processor
│   ├── vofc_processor.py
│   ├── install_service.ps1
│   ├── requirements.txt
│   └── .env (if needed)
│
└── Ollama\                 # Data directories (unchanged)
    └── Data\
        ├── incoming/
        ├── processed/
        ├── library/
        └── logs/
```

## Troubleshooting

### Flask Service Won't Start
1. Check Python path: `nssm get vofc-flask Application`
2. Verify .env file exists: `Test-Path "C:\Tools\PSA-Flask\.env"`
3. Check service logs: `nssm status vofc-flask`
4. Test manually: `cd C:\Tools\PSA-Flask && .\start.ps1`

### Processor Service Won't Start
1. Check Python path: `nssm get VOFC-Processor Application`
2. Verify script exists: `Test-Path "C:\Tools\PSA-Processor\vofc_processor.py"`
3. Check service logs: `Get-Content "C:\Tools\Ollama\Data\logs\vofc_processor_*.log" -Tail 50`
4. Verify .env file (if processor uses one)

### Import Errors
1. Verify all files were copied
2. Check `__init__.py` files exist in packages
3. Verify virtual environment is activated
4. Check Python path in service configuration

## Verification Checklist

After migration:
- [ ] Flask server starts successfully
- [ ] Processor service starts successfully
- [ ] All API endpoints respond correctly
- [ ] Health check endpoint works
- [ ] Processor processes files correctly
- [ ] Logs are written to correct locations
- [ ] No errors in service logs
- [ ] Next.js frontend can connect to Flask backend

## Rollback Plan

If issues occur:

1. **Stop new services**
   ```powershell
   nssm stop vofc-flask
   nssm stop VOFC-Processor
   ```

2. **Restart legacy services** (if they still exist at old locations)
   ```powershell
   # Update service to point back to old location
   nssm set vofc-flask AppDirectory "C:\Tools\VOFC-Flask"
   nssm start vofc-flask
   ```

3. **Restore from backup** (if you created one)

## Next Steps

After successful migration:
1. Test all functionality
2. Monitor logs for 24-48 hours
3. Remove old directories (after verification)
4. Update documentation with new paths

