# Server Migration Guide - All Services to C:\Tools

## Overview

All VOFC services have been migrated to run from `C:\Tools` instead of project directories. This ensures server-ready deployment with no project directory dependencies.

## Server Structure

```
C:\Tools\
├── python\
│   └── python.exe              # Python 3.11+
├── py_scripts\                  # All service scripts
│   ├── vofc_processor\
│   │   ├── vofc_processor.py
│   │   ├── requirements.txt
│   │   └── __init__.py
│   ├── model_manager\
│   │   └── model_manager.py
│   └── auto_retrain\
│       └── auto_retrain_job.py  # (if exists)
├── nssm\
│   └── nssm.exe                 # NSSM service manager
└── Ollama\
    └── Data\
        ├── incoming\
        ├── processed\
        ├── library\
        └── logs\
```

## Services

### 1. VOFC-Processor
- **Script**: `C:\Tools\py_scripts\vofc_processor\vofc_processor.py`
- **Working Directory**: `C:\Tools\py_scripts\vofc_processor`
- **Python**: `C:\Tools\python\python.exe`
- **Install**: `tools\vofc_processor\install_service.ps1`

### 2. VOFC-ModelManager
- **Script**: `C:\Tools\py_scripts\model_manager\model_manager.py`
- **Working Directory**: `C:\Tools\py_scripts\model_manager`
- **Python**: `C:\Tools\python\python.exe`
- **Install**: `scripts\install-model-manager-service.ps1`

### 3. VOFC-AutoRetrain
- **Script**: `C:\Tools\py_scripts\auto_retrain\auto_retrain_job.py`
- **Working Directory**: `C:\Tools\py_scripts\auto_retrain`
- **Python**: `C:\Tools\python\python.exe`
- **Install**: `scripts\install-vofc-autoretrain.ps1`

## Migration Steps

### Option 1: Automated Migration (Recommended)

Run the migration script to move all services and update configurations:

```powershell
# Run as Administrator
cd C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\scripts
.\migrate-all-services-to-tools.ps1
```

This script will:
1. Copy all service scripts to `C:\Tools\py_scripts`
2. Update all service configurations
3. Install Python dependencies
4. Stop/restart services as needed

### Option 2: Manual Migration

#### Step 1: Copy Scripts

```powershell
# VOFC Processor
Copy-Item "tools\vofc_processor\*" -Destination "C:\Tools\py_scripts\vofc_processor\" -Recurse -Force

# Model Manager
New-Item -ItemType Directory -Path "C:\Tools\py_scripts\model_manager" -Force
Copy-Item "services\model_manager.py" -Destination "C:\Tools\py_scripts\model_manager\model_manager.py" -Force

# Auto Retrain (if exists)
New-Item -ItemType Directory -Path "C:\Tools\py_scripts\auto_retrain" -Force
Copy-Item "C:\Tools\auto_retrain_job.py" -Destination "C:\Tools\py_scripts\auto_retrain\auto_retrain_job.py" -Force
```

#### Step 2: Update Each Service

For each service, run:

```powershell
# Stop service
nssm stop <ServiceName>

# Update paths
nssm set <ServiceName> Application "C:\Tools\python\python.exe"
nssm set <ServiceName> AppParameters "C:\Tools\py_scripts\<service_dir>\<script>.py"
nssm set <ServiceName> AppDirectory "C:\Tools\py_scripts\<service_dir>"

# Start service
nssm start <ServiceName>
```

#### Step 3: Install Dependencies

```powershell
& "C:\Tools\python\python.exe" -m pip install -r C:\Tools\py_scripts\vofc_processor\requirements.txt
& "C:\Tools\python\python.exe" -m pip install pandas requests supabase python-dotenv
```

## Verification

### Check Service Paths

```powershell
# Check all VOFC services
$services = @("VOFC-Processor", "VOFC-ModelManager", "VOFC-AutoRetrain")
foreach ($svc in $services) {
    Write-Host "`n[$svc]" -ForegroundColor Cyan
    nssm get $svc Application
    nssm get $svc AppParameters
    nssm get $svc AppDirectory
    nssm status $svc
}
```

### Verify Files Exist

```powershell
Test-Path "C:\Tools\python\python.exe"
Test-Path "C:\Tools\py_scripts\vofc_processor\vofc_processor.py"
Test-Path "C:\Tools\py_scripts\model_manager\model_manager.py"
```

## Updated Install Scripts

All install scripts have been updated to use `C:\Tools` paths:

- ✅ `tools\vofc_processor\install_service.ps1`
- ✅ `scripts\install-model-manager-service.ps1`
- ✅ `scripts\install-vofc-autoretrain.ps1`

## Benefits

1. **Server-Ready**: No project directory dependencies
2. **Centralized**: All services in one location (`C:\Tools`)
3. **Consistent**: All services use same Python installation
4. **Maintainable**: Easy to update and manage
5. **Portable**: Can be deployed to any server with same structure

## Troubleshooting

### Service Not Starting

1. Check Python path:
   ```powershell
   & "C:\Tools\python\python.exe" --version
   ```

2. Check script exists:
   ```powershell
   Test-Path "C:\Tools\py_scripts\<service>\<script>.py"
   ```

3. Check logs:
   ```powershell
   Get-Content "C:\Tools\Ollama\Data\logs\<service>_*.log" -Tail 20
   ```

### Dependencies Missing

Install dependencies using server Python:
```powershell
& "C:\Tools\python\python.exe" -m pip install <package>
```

### Service Path Wrong

Use the update script:
```powershell
.\scripts\update-service-to-tools.ps1
```

## Next Steps

After migration:

1. ✅ Verify all services are running: `nssm status <ServiceName>`
2. ✅ Test each service with a sample task
3. ✅ Monitor logs for errors
4. ✅ Update any documentation referencing old paths
5. ✅ Remove old project directory service files (optional)

## Notes

- Services will continue to work from old locations until migrated
- Old install scripts will still work but install to new locations
- Environment variables should be set at system level, not in project `.env`
- Logs remain in `C:\Tools\Ollama\Data\logs\` for consistency

