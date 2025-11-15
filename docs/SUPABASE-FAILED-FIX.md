# Supabase "failed" Status Fix

## Problem
Health check shows `"supabase":"failed"` even though Supabase is configured and working.

## Root Cause
The Flask Windows service (NSSM) doesn't have access to environment variables from `.env` files. NSSM services need environment variables set explicitly via `nssm set`.

## Solution

### Option 1: Use Sync Script (Recommended)
Run the sync script as Administrator:
```powershell
# Run PowerShell as Administrator, then:
cd C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool
.\scripts\sync-flask-env.ps1
```

This will:
1. Read `.env` file
2. Set all environment variables in the Flask service
3. Verify configuration

### Option 2: Manual Setup
Set environment variables manually in NSSM:

```powershell
# Run as Administrator
nssm set vofc-flask AppEnvironmentExtra "SUPABASE_URL=https://wivohgbuuwxoyfyzntsd.supabase.co SUPABASE_SERVICE_ROLE_KEY=your-key SUPABASE_ANON_KEY=your-key TUNNEL_URL=https://flask.frostech.site FLASK_PORT=8080"
```

**Note:** Replace `your-key` with actual values from your `.env` file.

### Option 3: Quick Fix (Read from .env)
If you have a `.env` file in `C:\Tools\VOFC-Flask`, you can modify the Flask service to load it, but NSSM doesn't support this natively. The sync script is the best approach.

## After Setting Variables

**Restart Flask service:**
```powershell
nssm restart vofc-flask
```

## Verification

After restart, check health:
```bash
curl http://localhost:8080/api/system/health
```

Should show:
```json
{
  "supabase": "ok",
  ...
}
```

## Files Created
- `scripts/sync-flask-env.ps1` - Automated sync script

