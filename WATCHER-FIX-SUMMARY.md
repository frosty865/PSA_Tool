# Watcher Debug and Fix Summary

## Issues Found

### 1. ✅ Watcher Status Detection - FIXED
- **Problem**: API showed `watcher_status: "stopped"` even though service is running
- **Fix Applied**: Improved regex pattern in `routes/system.py` to detect STATE: 4 more reliably
- **Status**: Code updated, requires Flask service restart to take effect

### 2. ⚠️ Service Running Old Code - PARTIALLY FIXED
- **Problem**: Service is running from `C:\Tools\vofc_processor\vofc_processor.py` (legacy path) with old code
- **Evidence**: Logs show "🔍 Periodic scan found new file" and "Found existing PDF files (including subdirectories)" which are not in current code
- **Fix Applied**: 
  - ✅ Copied updated `vofc_processor.py` to both `C:\Tools\vofc_processor\` and `C:\Tools\VOFC-Processor\`
  - ✅ Copied updated subdirectories (services, extract, model, normalize, etc.)
- **Action Required**: Service needs to be restarted to pick up new code (requires admin)

### 3. ⚠️ Files Not Being Processed
- **Problem**: Files detected but not processed
- **Root Cause**: Service is running old code that doesn't have the updated processing logic
- **Fix**: Will be resolved once service is restarted with new code

## Files Updated

### Code Files
- ✅ `routes/system.py` - Improved watcher status detection
- ✅ `tools/vofc_processor/vofc_processor.py` - Updated processing logic with learning mode
- ✅ Copied to `C:\Tools\vofc_processor\vofc_processor.py`
- ✅ Copied to `C:\Tools\VOFC-Processor\vofc_processor.py`
- ✅ Copied all subdirectories to both locations

## Action Required (Run as Administrator)

### Option 1: Restart Service (if using legacy path)
```powershell
# Restart service to pick up new code
nssm restart VOFC-Processor
```

### Option 2: Update Service to Use New Path
```powershell
# Update service to use C:\Tools\VOFC-Processor (recommended)
nssm set VOFC-Processor Application "C:\Tools\python\python.exe"
nssm set VOFC-Processor AppParameters "C:\Tools\VOFC-Processor\vofc_processor.py"
nssm set VOFC-Processor AppDirectory "C:\Tools\VOFC-Processor"
nssm restart VOFC-Processor
```

### Option 3: Use Install Script (Recommended)
```powershell
# Run install script to update service configuration
cd C:\Tools\VOFC-Processor
.\install_service.ps1
```

## Expected Behavior After Restart

1. **Watcher Status**: Should show "running" when service is running
2. **File Processing**: Files should be processed immediately when detected
3. **Learning Mode**: Files with < 5 records will stay in incoming for reprocessing
4. **Log Messages**: Should see "🚀 NEW FILE DETECTED" and "VOFC Processor - Starting processing cycle"

## Verification

After restarting the service, check:
```powershell
# Check service status
nssm status VOFC-Processor

# Check logs for new messages
Get-Content "C:\Tools\Ollama\Data\logs\vofc_processor_*.log" -Tail 20

# Check watcher status via API
curl http://localhost:8080/api/system/progress | python -m json.tool | Select-String "watcher_status"
```

