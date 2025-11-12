# Quick Fix for Service Issues

## Current Issues

Based on the service check:
- **VOFC-ModelManager**: Paused + Missing environment variables
- **VOFC-AutoRetrain**: Paused + Missing environment variables
- **VOFC-Flask**: Missing environment variables (but running)
- **VOFC-Ollama**: Missing environment variables (but running - may be optional)

## Quick Fix (Run as Administrator)

### Option 1: Master Script (Recommended)

```powershell
# Run PowerShell as Administrator
.\scripts\fix-all-services.ps1
```

This will:
1. Fix all paused services
2. Set missing environment variables from `.env` file
3. Restart services

### Option 2: Step-by-Step

**Step 1: Fix Paused Services**
```powershell
.\scripts\fix-paused-service.ps1 -ServiceName VOFC-ModelManager
.\scripts\fix-paused-service.ps1 -ServiceName VOFC-AutoRetrain
```

**Step 2: Set Environment Variables**
```powershell
.\scripts\set-model-manager-env.ps1
.\scripts\set-autoretrain-env.ps1
```

**Step 3: Restart Services**
```powershell
nssm restart VOFC-ModelManager
nssm restart VOFC-AutoRetrain
```

## Verify Fix

After running the fixes, verify everything is correct:

```powershell
.\scripts\check-all-services.ps1
```

## Environment Variables

All scripts read from your `.env` file located at:
- `C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\.env`

Required variables:
- `SUPABASE_URL` (or `NEXT_PUBLIC_SUPABASE_URL`)
- `SUPABASE_SERVICE_ROLE_KEY` (or `SUPABASE_KEY`)

## Notes

- **VOFC-Ollama**: Environment variables may be optional - Ollama may not need them
- **VOFC-Flask**: Environment variables may be optional - Flask may load from `.env` directly
- **VOFC-Processor**: Already correctly configured ✓
- **VOFC-Tunnel**: No environment variables needed ✓

