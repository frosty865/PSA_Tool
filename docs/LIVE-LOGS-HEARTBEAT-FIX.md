# Live Logs Heartbeat Fix

## Problem
Live logs showing "Waiting for log entries..." with no heartbeat, even when the connection is working.

## Root Cause
1. **Old code running**: Flask service is running old code that looks for date-specific log files (`vofc_processor_20251114.log`) instead of the rolling log file (`vofc_processor.log`)
2. **No heartbeat**: When there are no today's logs, the endpoint doesn't send a heartbeat message to show the connection is active
3. **Filtering too strict**: Old logs are filtered out, leaving nothing to display

## Fixes Applied

### 1. Added Heartbeat Message
Updated `routes/system.py` `get_logs()` endpoint to always send a heartbeat when there are no today's logs:

```python
# Always add a heartbeat message if we have no today's logs
if not today_lines or len(today_lines) == 0:
    heartbeat_time = now_est().strftime("%Y-%m-%d %H:%M:%S")
    if not result_lines:
        result_lines = [f"{heartbeat_time} | INFO | 📡 Log monitor active - waiting for new log entries..."]
    else:
        result_lines.insert(0, f"{heartbeat_time} | INFO | 📡 Log monitor active - showing older logs (no recent activity)")
```

### 2. Log File Path
The code correctly uses `vofc_processor.log` (rolling log file), but the running service has old code. **Restart required**.

## Required Action

**Restart Flask service to pick up changes:**
```powershell
nssm restart vofc-flask
```

## Expected Behavior After Fix

1. **With no logs**: Shows heartbeat message: `📡 Log monitor active - waiting for new log entries...`
2. **With old logs only**: Shows heartbeat + old logs: `📡 Log monitor active - showing older logs (no recent activity)` followed by old log lines
3. **With today's logs**: Shows today's logs normally (no heartbeat needed)

## Verification

After restarting Flask:
1. Check logs endpoint: `curl http://localhost:8080/api/system/logs?tail=10`
2. Should see heartbeat message if no recent logs
3. Frontend should show the heartbeat instead of "Waiting for log entries..."

## Files Changed
- `routes/system.py` - Added heartbeat logic to `get_logs()` endpoint

