# Log Reading Fix - Live Logs Not Working

## Problem
Live logs weren't showing for 2 days because:
1. Log file filtering was too strict - required lines to start with today's date
2. Log file had test content without proper timestamps
3. No fallback when no timestamped lines found

## Root Cause
The filtering logic in `routes/system.py` was:
- Requiring lines to start with today's date (YYYY-MM-DD format)
- Filtering out any lines that didn't match
- No fallback when logs were malformed or didn't have timestamps

## Fix Applied

### 1. Made Log Reading More Robust
Updated `get_logs()` endpoint in `routes/system.py`:
- **Fallback mode**: If no today's logs found, return last N lines regardless of date
- **Less strict filtering**: Try to parse timestamp first, then check date
- **Always show something**: If logs exist but aren't formatted, show them anyway

### 2. Fixed Log Streaming
Updated `log_stream()` endpoint:
- **Include all lines if no timestamped lines**: Fallback for malformed logs
- **Better error handling**: Don't silently drop lines

### 3. Key Changes

**Before:**
```python
# Strict filtering - only lines starting with today's date
if not line_stripped.startswith(today_date_str):
    return False
```

**After:**
```python
# Try timestamp first, then date, then include anyway (fallback)
if not today_lines:
    # Fallback: return last N lines regardless of date
    all_lines = [line.strip() for line in lines if line.strip()]
    result_lines = all_lines[-tail:] if len(all_lines) > tail else all_lines
```

## Verification

Run the diagnostic script:
```bash
python tools/test_log_reading.py
```

This will show:
- Log file location and size
- Last 20 lines
- How many lines match today's date
- Fallback behavior

## Next Steps

1. **Restart Flask service** to pick up changes:
   ```powershell
   nssm restart vofc-flask
   ```

2. **Verify processor is writing logs**:
   ```powershell
   # Check if processor is running
   sc query VOFC-Processor
   
   # Check log file is being written
   Get-Content "C:\Tools\Ollama\Data\logs\vofc_processor.log" -Tail 20
   ```

3. **Test the endpoint**:
   ```bash
   curl http://localhost:8080/api/system/logs?tail=50
   ```

## Expected Behavior

- **If logs have timestamps**: Show only today's logs
- **If logs don't have timestamps**: Show last N lines (fallback)
- **If log file is empty**: Return empty array
- **Always show something**: If logs exist, they'll be shown even if malformed

## Files Changed
- `routes/system.py` - Fixed `get_logs()` and `log_stream()` endpoints
- `tools/test_log_reading.py` - New diagnostic script

