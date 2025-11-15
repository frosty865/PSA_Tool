# Live Log View - Identified Issues

## Critical Issues Found

### Issue 1: Hash-Based Deduplication Logic Flaw
**Location**: `app/admin/processing/page.jsx:293-300`

**Problem**: The code uses the first 100 characters as a hash to detect duplicates. This has several problems:
1. If two log lines have identical prefixes (e.g., same timestamp and message start), they'll be treated as duplicates even if they're different
2. The hash doesn't account for the full line content
3. If the backend returns lines in a different order, the comparison might miss new lines

**Current Code**:
```javascript
const newLines = validLines.filter(line => {
  const hash = line.substring(0, 100)
  if (!lastKnownLines.has(hash)) {
    lastKnownLines.add(hash)
    return true
  }
  return false
})
```

**Impact**: New log lines might not appear if they share the same first 100 characters with previously seen lines.

### Issue 2: Polling Logic Doesn't Handle Backend Returning Same Lines
**Location**: `app/admin/processing/page.jsx:291-322`

**Problem**: The backend always returns the last 50 lines. The polling logic compares these against `lastKnownLines` to find new ones. However:
- If the backend returns the same 50 lines (no new logs), `newLines` will be empty
- The code returns `prev` without updating, which is correct
- BUT: If the initial load failed or returned empty, `prev` might be empty or just have a heartbeat
- The heartbeat logic only triggers if `validLines.length === 0`, but if `validLines` has old lines we've already seen, no heartbeat is shown

**Current Code**:
```javascript
if (validLines.length > 0) {
  // Find new lines...
  if (newLines.length > 0) {
    // Add new lines
  }
  // No new lines, but keep existing (don't clear)
  return prev  // <-- This might keep an empty or stale state
}
```

**Impact**: If initial load fails but polling succeeds with old lines, the view might show nothing or stale data.

### Issue 3: Race Condition Between Initial Load and Polling
**Location**: `app/admin/processing/page.jsx:367-369`

**Problem**: 
- `loadInitialLogs()` is called immediately (async, no await)
- `setupPolling()` is called after 2 seconds via `setTimeout`
- Both functions share the same `lastKnownLines` Set
- If `loadInitialLogs()` is still running when polling starts, there could be a race condition
- If `loadInitialLogs()` fails but polling succeeds, `lastKnownLines` might be empty, causing all lines to be treated as new

**Current Code**:
```javascript
loadInitialLogs()
setTimeout(setupPolling, 2000)
```

**Impact**: Polling might start before initial load completes, causing duplicate lines or missed updates.

### Issue 4: Hash Set Memory Management Issue
**Location**: `app/admin/processing/page.jsx:309-316`

**Problem**: When `lastKnownLines.size > 500`, the code clears the entire set and rebuilds it from `trimmed` lines. However:
- If a log line appears again after the set is cleared, it will be treated as new
- The hash set might grow faster than expected if there are many unique log lines
- The rebuild happens during state update, which could cause issues

**Current Code**:
```javascript
if (lastKnownLines.size > 500) {
  lastKnownLines.clear()
  trimmed.forEach(line => {
    if (line) lastKnownLines.add(line.substring(0, 100))
  })
}
```

**Impact**: After clearing, previously seen lines might appear as duplicates or new lines might be missed.

### Issue 5: No Response Status Check
**Location**: `app/admin/processing/page.jsx:249-253`

**Problem**: The code doesn't check if the response is OK before trying to parse JSON. While the proxy should always return 200, if there's an error, the response might not be valid JSON.

**Current Code**:
```javascript
const res = await fetch('/api/system/logs?tail=50', { 
  cache: 'no-store',
  signal: controller.signal
})
// No check for res.ok before parsing
const data = await res.json()
```

**Impact**: If the response is not OK, JSON parsing might fail, though there is error handling for this.

## Recommended Fixes

### Fix 1: Use Full Line Hash or Better Unique Identifier
```javascript
// Use full line as hash, or include timestamp + message
const hash = line // Full line comparison
// OR use a more robust hash
const hash = `${line.substring(0, 50)}-${line.length}-${line.substring(line.length - 20)}`
```

### Fix 2: Ensure Polling Waits for Initial Load
```javascript
// Make loadInitialLogs return a promise and wait for it
const loadInitialLogs = async (retry = 0) => {
  // ... existing code ...
  return { success: true, lines: validLines }
}

// Wait for initial load before starting polling
loadInitialLogs().then((result) => {
  if (result.success && result.lines.length > 0) {
    // Initial load succeeded, start polling
    setupPolling()
  } else {
    // Initial load failed or empty, still start polling (it will show heartbeat)
    setupPolling()
  }
}).catch(() => {
  // On error, still start polling
  setupPolling()
})
```

### Fix 3: Improve New Line Detection
Instead of comparing against a hash set, track the last seen line and only add lines that come after it:

```javascript
// Track the last line we've seen (by full content or by position)
let lastSeenLineIndex = -1

// In polling:
const currentLines = validLines
// Find the index of the last line we've seen
const lastSeenIndex = currentLines.findIndex(line => 
  lastKnownLines.has(line.substring(0, 100))
)

if (lastSeenIndex >= 0) {
  // We found where we left off, add everything after it
  const newLines = currentLines.slice(lastSeenIndex + 1)
  // Add new lines...
} else {
  // Last seen line not found, might be new file or rotation
  // Add all lines as new (or compare differently)
}
```

### Fix 4: Add Response Status Check
```javascript
const res = await fetch('/api/system/logs?tail=50', { 
  cache: 'no-store',
  signal: controller.signal
})

if (!res.ok) {
  // Handle error response
  const errorText = await res.text()
  console.error('[Live Logs] Response not OK:', res.status, errorText)
  // Return error heartbeat
  return
}

const data = await res.json()
```

## Quick Diagnostic Test

To test if the issue is with hash comparison, add this to the browser console on the processing page:

```javascript
// Test the hash comparison logic
const testLines = [
  '2025-01-15 10:00:00 | INFO | Processing file 1',
  '2025-01-15 10:00:01 | INFO | Processing file 2',
  '2025-01-15 10:00:00 | INFO | Processing file 1' // Duplicate first 100 chars
]

const lastKnown = new Set()
testLines.forEach(line => {
  const hash = line.substring(0, 100)
  console.log('Line:', line)
  console.log('Hash:', hash)
  console.log('Seen before?', lastKnown.has(hash))
  lastKnown.add(hash)
})
```

## Next Steps

1. **Add logging** to see what's happening:
   - Log when new lines are detected
   - Log the hash values being compared
   - Log the state of `lastKnownLines`

2. **Test the endpoint** directly to verify it's returning logs:
   ```javascript
   fetch('/api/system/logs?tail=10').then(r => r.json()).then(console.log)
   ```

3. **Check browser console** for `[Live Logs]` messages to see what's happening

4. **Apply fixes** based on which issue is causing the problem

