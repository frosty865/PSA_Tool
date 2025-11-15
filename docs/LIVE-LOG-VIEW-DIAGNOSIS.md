# Live Log View Diagnosis

## Problem Summary
The live log view on the processing monitor page may not be displaying logs correctly.

## Architecture Overview

### Frontend (Next.js)
- **Location**: `app/admin/processing/page.jsx`
- **Method**: Polling every 3 seconds
- **Endpoint**: `/api/system/logs?tail=50`
- **Initial Load**: Fetches last 50 lines on mount
- **Polling**: Checks for new lines every 3 seconds

### API Proxy (Next.js)
- **Location**: `app/api/system/logs/route.js`
- **Function**: Proxies requests to Flask backend
- **Timeout**: 30 seconds
- **Error Handling**: Always returns 200 with heartbeat messages

### Backend (Flask)
- **Location**: `routes/system.py`
- **Endpoint**: `/api/system/logs`
- **Log File**: `vofc_processor.log` (rolling log file)
- **Filtering**: Shows today's logs, falls back to last N lines if no today's logs

## Potential Issues

### 1. **Hash-Based Deduplication May Be Too Aggressive**
**Location**: `app/admin/processing/page.jsx:294-299`

The frontend uses the first 100 characters of each line as a hash to detect duplicates. This could cause issues if:
- Log lines have identical prefixes but different content
- Timestamps are the same but messages differ
- The hash comparison is case-sensitive or whitespace-sensitive

**Code**:
```javascript
const hash = line.substring(0, 100)
if (!lastKnownLines.has(hash)) {
  lastKnownLines.add(hash)
  return true
}
```

**Fix**: Consider using a more robust hash (e.g., full line hash) or include line number/timestamp in comparison.

### 2. **Polling Logic May Skip Updates**
**Location**: `app/admin/processing/page.jsx:320-322`

When there are no new lines, the code returns `prev` without updating. This means:
- If the initial load fails, the view stays empty
- If polling starts before initial load completes, it might miss logs
- The heartbeat logic only triggers if there's no existing heartbeat

**Code**:
```javascript
// No new lines, but keep existing (don't clear)
return prev
```

### 3. **Initial Load and Polling Race Condition**
**Location**: `app/admin/processing/page.jsx:367-369`

The initial load and polling setup have a 2-second delay, but:
- If initial load takes longer than 2 seconds, polling might start with empty state
- Both use the same `lastKnownLines` Set, which could cause conflicts
- The initial load tracks lines in `lastKnownLines`, but polling uses a different scope

**Code**:
```javascript
loadInitialLogs()
setTimeout(setupPolling, 2000)
```

### 4. **Backend Log File Path Issues**
**Location**: `routes/system.py:916-930`

The backend checks multiple paths for the log file, but:
- If the log file doesn't exist, it returns a heartbeat message
- The heartbeat might not be visible if the frontend filters it out
- File permissions could prevent reading

**Possible Paths**:
- `Config.DATA_DIR / "logs" / "vofc_processor.log"`
- `Config.ARCHIVE_DIR / "logs" / "vofc_processor.log"`
- `C:\Tools\Ollama\Data\logs\vofc_processor.log`
- `C:\Tools\VOFC_Logs\vofc_processor.log`
- `C:\Tools\nssm\logs\vofc_processor.log`

### 5. **Response Format Validation**
**Location**: `app/admin/processing/page.jsx:196-199`

The frontend validates that `data.lines` is an array, but:
- If Flask returns an error response, it might not have the expected structure
- The proxy route should handle this, but there might be edge cases

### 6. **Empty Lines Filtering**
**Location**: `app/admin/processing/page.jsx:277`

The code filters out empty lines, which is good, but:
- If all lines are filtered out, `validLines` will be empty
- The heartbeat logic might not trigger if `validLines.length === 0` but `prev.length > 0`

## Diagnostic Steps

### 1. Check Browser Console
Open browser DevTools and check for:
- `[Live Logs]` console messages
- Network errors in the Network tab
- Failed fetch requests to `/api/system/logs`

### 2. Test Backend Directly
```powershell
# Test Flask endpoint directly
Invoke-WebRequest -Uri "http://localhost:8080/api/system/logs?tail=10" | Select-Object -ExpandProperty Content

# Check if log file exists
Test-Path "C:\Tools\Ollama\Data\logs\vofc_processor.log"
Get-Content "C:\Tools\Ollama\Data\logs\vofc_processor.log" -Tail 10
```

### 3. Test Next.js Proxy
```powershell
# Test Next.js proxy (if running locally)
Invoke-WebRequest -Uri "http://localhost:3000/api/system/logs?tail=10" | Select-Object -ExpandProperty Content
```

### 4. Check Flask Service Status
```powershell
# Check if Flask service is running
Get-Service | Where-Object {$_.Name -like "*flask*"}

# Check Flask logs
Get-Content "C:\Tools\Ollama\Data\logs\vofc_processor.log" -Tail 50 | Select-String "get_logs|system/logs"
```

## Recommended Fixes

### Fix 1: Improve Hash-Based Deduplication
Use a more robust hash that includes the full line or a better unique identifier:

```javascript
// Instead of first 100 chars, use full line hash or include timestamp
const hash = line // Use full line for comparison
// OR
const hash = `${line.substring(0, 50)}-${line.length}` // Include length for uniqueness
```

### Fix 2: Fix Race Condition Between Initial Load and Polling
Ensure polling doesn't start until initial load completes:

```javascript
// Load initial logs and start polling
loadInitialLogs().then(() => {
  // Only start polling after initial load completes
  setupPolling()
}).catch(() => {
  // Even on error, start polling (it will show error status)
  setupPolling()
})
```

### Fix 3: Improve Heartbeat Logic
Always show a heartbeat if there are no logs, even if previous state exists:

```javascript
// No valid lines from API - always show heartbeat if no logs
if (validLines.length === 0) {
  const hasHeartbeat = prev.some(line => line && line.includes('[MONITOR]'))
  if (!hasHeartbeat || prev.length === 0) {
    const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19)
    return [`${timestamp} | INFO | [MONITOR] Connected - waiting for log entries...`]
  }
  return prev
}
```

### Fix 4: Add Debug Logging
Add more detailed logging to track what's happening:

```javascript
console.log('[Live Logs] Poll result:', {
  validLinesCount: validLines.length,
  prevLinesCount: prev.length,
  newLinesCount: newLines.length,
  hasHeartbeat: prev.some(line => line && line.includes('[MONITOR]'))
})
```

## Quick Test Script

Create a test script to verify the endpoint:

```javascript
// Test in browser console on the processing page
async function testLogs() {
  try {
    const res = await fetch('/api/system/logs?tail=10')
    const data = await res.json()
    console.log('Response:', data)
    console.log('Lines count:', data.lines?.length)
    console.log('First line:', data.lines?.[0])
    return data
  } catch (err) {
    console.error('Error:', err)
  }
}
testLogs()
```

## Next Steps

1. **Check browser console** for `[Live Logs]` messages
2. **Test backend endpoint** directly to verify Flask is responding
3. **Check log file** exists and is readable
4. **Verify Flask service** is running and has latest code
5. **Apply fixes** based on which issue is identified

