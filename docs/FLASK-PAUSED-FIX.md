# Flask Service Paused/Failed to Start Fix

## Problem
Flask service is paused or fails to start with error:
```
ValueError: invalid literal for int() with base 10: '8080 FLASK_ENV=production SUPABASE_URL=...'
```

## Root Cause
NSSM's `AppEnvironmentExtra` was set with space-separated environment variables, but NSSM requires **newline-separated** KEY=VALUE pairs. When Python tries to read `FLASK_PORT`, it gets the entire space-separated string instead of just "8080".

## Solution

### Quick Fix (Run as Administrator)
```powershell
# Run PowerShell as Administrator, then:
cd C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool
.\scripts\fix-flask-env-format.ps1
```

This script will:
1. Stop the Flask service
2. Read `.env` file
3. Set environment variables with proper newline format
4. Start the Flask service

### Manual Fix
If you prefer to fix manually:

```powershell
# Run as Administrator
# 1. Stop service
nssm stop vofc-flask

# 2. Clear existing environment variables
nssm set vofc-flask AppEnvironmentExtra ""

# 3. Set with newline format (use the sync script)
.\scripts\sync-flask-env.ps1

# 4. Start service
nssm start vofc-flask
```

## Verification

After fixing, check service status:
```powershell
nssm status vofc-flask
```

Should show: `SERVICE_RUNNING`

Check health:
```bash
curl http://localhost:8080/api/system/health
```

Should show all components as "ok".

## Files Created
- `scripts/fix-flask-env-format.ps1` - Quick fix script
- `scripts/sync-flask-env.ps1` - Updated to use newline format
- `docs/FLASK-PAUSED-FIX.md` - This document

