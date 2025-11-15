# Flask Service Still Paused - Complete Fix

## Problem
Flask service remains paused even after setting environment variables. Error shows:
```
ValueError: invalid literal for int() with base 10: '8080 FLASK_ENV=production SUPABASE_URL=...'
```

## Root Cause
NSSM's `AppEnvironmentExtra` is still passing environment variables as a space-separated string instead of individual variables, even when set with newlines.

## Solution (Two-Part Fix)

### Part 1: Update Code (Defensive Parsing)
I've added defensive parsing to `config/__init__.py` to handle malformed environment variables. **You need to sync this code to `C:\Tools\VOFC-Flask`:**

```powershell
# Sync the updated config file
Copy-Item "config\__init__.py" "C:\Tools\VOFC-Flask\config\__init__.py" -Force
```

### Part 2: Reset Environment Variables (Run as Administrator)
```powershell
# Run PowerShell as Administrator, then:
cd C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool
.\scripts\reset-flask-env.ps1
```

This script will:
1. Stop the Flask service
2. Clear all environment variables
3. Read `.env` file
4. Set environment variables with proper newline format
5. Start the Flask service

## Alternative: Manual Fix

If the script doesn't work, try setting variables individually:

```powershell
# Run as Administrator
nssm stop vofc-flask

# Clear all
nssm set vofc-flask AppEnvironmentExtra ""

# Set critical variables only (one at a time or use the script)
# The reset script handles this automatically
```

## Verification

After running the reset script:
1. Check service status: `nssm status vofc-flask` (should be `SERVICE_RUNNING`)
2. Check logs: `Get-Content "C:\Tools\nssm\logs\vofc_flask_err.log" -Tail 10`
3. Check health: `curl http://localhost:8080/api/system/health`

## Files Changed
- `config/__init__.py` - Added defensive parsing for FLASK_PORT and OLLAMA_PORT
- `scripts/reset-flask-env.ps1` - Complete reset script
- `docs/FLASK-STILL-PAUSED-FIX.md` - This document

## Important Notes
1. **Code must be synced** - The defensive parsing fix needs to be in `C:\Tools\VOFC-Flask\config\__init__.py`
2. **Run as Administrator** - The reset script requires admin privileges
3. **Service will restart** - The script automatically restarts the service after setting variables

