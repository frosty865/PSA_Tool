# Watcher Status Diagnosis - Issues Found

## Summary
Three issues were identified:

1. **Watcher Status Detection**: Flask server needs restart to pick up code changes
2. **File Processing Failure**: Missing module `normalize.filter` in deployed service
3. **Outdated Logs**: Log streaming showing old logs from yesterday

## Issue 1: Watcher Status Shows "Stopped" (Service is Actually Running)

**Status**: ✅ Fixed in code, requires Flask server restart

**Root Cause**: The service check logic in `routes/system.py` was working correctly, but the Flask server needs to be restarted to pick up the improved logging and detection code.

**Fix Applied**:
- Improved service status detection logic with better logging
- Added explicit checks for RUNNING state and state code 4
- Enhanced error handling and debug logging

**Action Required**: 
- Restart the `VOFC-Flask` Windows service to pick up code changes
- Command (requires admin): `sc stop VOFC-Flask` then `sc start VOFC-Flask`

## Issue 2: File Stuck in Incoming Directory

**Status**: ❌ Processing failing due to missing module

**Root Cause**: The deployed service at `C:\Tools\vofc_processor\run_processor.py` is trying to import:
```python
from normalize.filter import filter_records
```
But this module doesn't exist. The file `Safe-Schools-Best-Practices.pdf` keeps failing with:
```
ModuleNotFoundError: No module named 'normalize.filter'
```

**Current Behavior**:
- Watcher detects the file ✅
- Processing starts ✅
- Extraction works ✅
- Fails at filtering step ❌

**Fix Applied**:
- Added periodic check for existing files (every 5 minutes) in `tools/vofc_processor/vofc_processor.py`
- This will help catch files that were missed when service started

**Action Required**:
- Fix the import in `C:\Tools\vofc_processor\run_processor.py` line 130
- The correct import should be from the normalization module structure
- Check if `filter_records` function exists or needs to be created
- Or remove the filter step if not needed

## Issue 3: Outdated Logs in UI

**Status**: ⚠️ Logs showing from yesterday (2025-11-12 12:38:35)

**Root Cause**: The log streaming endpoint may be:
- Reading from wrong log file
- Not filtering correctly by date
- Showing cached/stale data

**Fix Applied**:
- Previously improved log filtering in `routes/system.py` to show only last 1 hour
- Added session-based filtering to prevent old logs on initial connection

**Action Required**:
- Verify log file path is correct: `C:\Tools\Ollama\Data\logs\vofc_processor_YYYYMMDD.log`
- Check if Flask server is reading from correct log file
- Restart Flask server to clear any caching

## Recommended Actions

1. **Immediate**: Fix the missing module import in deployed service
   - Location: `C:\Tools\vofc_processor\run_processor.py` line 130
   - Either create the missing module or fix the import path

2. **Restart Services** (requires admin):
   ```powershell
   sc stop VOFC-Flask
   sc start VOFC-Flask
   ```

3. **Verify Log File Path**: Ensure Flask is reading from current log file

4. **Test Processing**: Once module import is fixed, the stuck file should process automatically

## Files Modified

- `routes/system.py`: Improved watcher status detection
- `tools/vofc_processor/vofc_processor.py`: Added periodic check for existing files

