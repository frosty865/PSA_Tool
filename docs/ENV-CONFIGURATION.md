# Environment Variable Configuration

## Problem

VOFC-Processor service shows warning:
```
WARNING:root:Supabase credentials not configured (SUPABASE_URL, SUPABASE_KEY)
```

## Solution

The processor now automatically loads environment variables from `.env` file. Two methods are available:

### Method 1: Automatic .env Loading (Recommended)

The processor automatically looks for `.env` file in these locations:
1. Project root (parent of `tools/` directory)
2. Processor directory (`tools/vofc_processor/`)
3. `C:\Tools\PSA_Tool\.env`
4. `C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\.env`

**Requirements:**
- `python-dotenv` package must be installed
- `.env` file must exist in one of the locations above

**Install python-dotenv:**
```powershell
C:\Tools\python\python.exe -m pip install python-dotenv
```

**Verify .env file exists:**
```powershell
Test-Path "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\.env"
```

**Restart service:**
```powershell
nssm restart VOFC-Processor
```

### Method 2: Set Environment Variables via NSSM

If you prefer to set environment variables directly in the service (takes precedence over .env):

**Run as Administrator:**
```powershell
.\scripts\set-vofc-processor-env.ps1 -ServiceName VOFC-Processor
```

This script:
1. Reads `.env` file from project root
2. Extracts `SUPABASE_URL`, `SUPABASE_KEY`, `OLLAMA_BASE_URL`, `VOFC_DATA_DIR`
3. Sets them as NSSM environment variables for the service

**Verify variables are set:**
```powershell
nssm get VOFC-Processor AppEnvironmentExtra
```

**Restart service:**
```powershell
nssm restart VOFC-Processor
```

## .env File Format

Your `.env` file should contain:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
# Or use:
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Optional:
OLLAMA_BASE_URL=http://localhost:11434
VOFC_DATA_DIR=C:\Tools\Ollama\Data
```

## Priority Order

Environment variables are loaded in this order (later takes precedence):
1. System environment variables
2. NSSM service environment variables
3. `.env` file (loaded by processor)

This means:
- NSSM variables override `.env` file
- System variables override everything

## Troubleshooting

### Still Getting Warning After Adding .env

1. **Check python-dotenv is installed:**
   ```powershell
   C:\Tools\python\python.exe -m pip list | findstr dotenv
   ```

2. **Check .env file location:**
   ```powershell
   Test-Path "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\.env"
   ```

3. **Check service logs:**
   ```powershell
   Get-Content "C:\Tools\Ollama\Data\logs\vofc_processor*.log" -Tail 20
   ```
   Look for: `"Loaded environment variables from ..."`

4. **Verify variables in .env:**
   ```powershell
   Get-Content "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\.env" | Select-String "SUPABASE"
   ```

### python-dotenv Not Installed

**Install it:**
```powershell
C:\Tools\python\python.exe -m pip install python-dotenv
```

**Add to requirements.txt:**
```powershell
Add-Content "C:\Tools\py_scripts\vofc_processor\requirements.txt" "python-dotenv"
```

### Variables Not Loading

1. **Check file path:**
   - Processor looks in multiple locations
   - Check logs to see which path it tried

2. **Check file format:**
   - Must be `KEY=VALUE` format
   - No spaces around `=`
   - No quotes needed (but allowed)

3. **Check file permissions:**
   - Service account must be able to read the file
   - If service runs as SYSTEM, file must be readable by SYSTEM

### Using NSSM Variables Instead

If `.env` loading doesn't work, use NSSM variables:

```powershell
# Set individually
nssm set VOFC-Processor AppEnvironmentExtra "SUPABASE_URL=https://your-project.supabase.co"
nssm set VOFC-Processor AppEnvironmentExtra "SUPABASE_KEY=your-key"

# Or use the script
.\scripts\set-vofc-processor-env.ps1
```

## Verification

After configuration, check logs:
```powershell
Get-Content "C:\Tools\Ollama\Data\logs\vofc_processor*.log" -Tail 30 | Select-String -Pattern "Supabase|env|SUPABASE"
```

Should see:
- `"Loaded environment variables from ..."` (if .env loaded)
- `"Supabase credentials verified"` (if credentials found)
- No warnings about missing credentials

