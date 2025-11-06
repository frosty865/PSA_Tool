# Processing Workflow Debug Guide

## Issue Found: Route Returns 404

The `/api/system/control` endpoint is returning 404, which means Flask isn't finding the route even though it's registered.

## Workflow Steps (Current)

1. **Trigger**: `POST /api/system/control` with `{"action": "process_existing"}`
2. **Route Handler**: `routes/system.py` → `system_control()` function
3. **Import**: `from ollama_auto_processor import get_incoming_files, process_file`
4. **Get Files**: `get_incoming_files()` - looks in `C:\Tools\Ollama\Data\incoming`
5. **Process Each**: `process_file(filepath)` for each file
6. **Pipeline**: 
   - `process_document_file()` → preprocess → model → postprocess
   - `handle_successful_processing()` → save JSON, move files
   - `handle_failed_processing()` → error log, move to errors/

## Potential Breaks

### 1. Route Not Found (404)
**Symptom**: Endpoint returns 404
**Fix**: Restart Flask service
```powershell
nssm restart "VOFC-Flask"
```

### 2. Import Error
**Symptom**: Error in Flask logs about `ollama_auto_processor` not found
**Fix**: Ensure `ollama_auto_processor.py` is in the Python path or same directory

### 3. No Files Found
**Symptom**: Message says "No files found in incoming/ directory"
**Fix**: 
- Check `C:\Tools\Ollama\Data\incoming` has files
- Verify file extensions: `.pdf`, `.docx`, `.txt`, `.xlsx`

### 4. Processing Fails Silently
**Symptom**: Files found but nothing happens
**Fix**: Check logs:
- `C:\Tools\Ollama\Data\automation\vofc_auto_processor.log`
- `C:\Tools\nssm\logs\vofc_flask.log`

### 5. Ollama Not Available
**Symptom**: Processing starts but fails at model step
**Fix**: Check Ollama is running:
```powershell
Get-Service "VOFC-Ollama"
```

## Enhanced Logging Added

The workflow now has detailed logging at each step:

1. **Route Handler**: Logs when `process_existing` is called
2. **File Discovery**: Logs how many files found
3. **Each File**: Logs start, success, or failure for each file
4. **Errors**: Full traceback logged for debugging

## Testing the Workflow

### Step 1: Check Files Exist
```powershell
Get-ChildItem "C:\Tools\Ollama\Data\incoming" -File
```

### Step 2: Test Flask Endpoint
```powershell
python scripts\test-process.py
```

### Step 3: Check Logs
```powershell
# Auto-processor logs
Get-Content "C:\Tools\Ollama\Data\automation\vofc_auto_processor.log" -Tail 50

# Flask logs
Get-Content "C:\Tools\nssm\logs\vofc_flask.log" -Tail 50
```

### Step 4: Verify Results
```powershell
# Check processed files
Get-ChildItem "C:\Tools\Ollama\Data\processed" -Filter "*_vofc.json"

# Check library files
Get-ChildItem "C:\Tools\Ollama\Data\library"

# Check errors
Get-ChildItem "C:\Tools\Ollama\Data\errors"
```

## Next Steps

1. **Restart Flask** to pick up route changes:
   ```powershell
   nssm restart "VOFC-Flask"
   ```

2. **Run test script**:
   ```powershell
   python scripts\test-process.py
   ```

3. **Check logs** for detailed error messages

4. **Verify files** are in the correct directory with correct extensions

