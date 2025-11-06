# Approval Sync System

## Overview

The Approval Sync system automatically detects when analysts approve submissions in the Supabase dashboard and updates the corresponding `learning_events` records. This enables the ML training system to track approved patterns and improve extraction accuracy.

## Purpose

When analysts review a submission in the Supabase dashboard and mark it as "approved", the system automatically:

✅ Detects the status change (via background polling)  
✅ Updates the related `learning_events` record with:
- `event_type: "approval"`
- `approved: true`
- `reviewed_at` timestamp in metadata
✅ Creates learning events for submissions that don't have them

## Architecture

```
Analyst Approval → Supabase Dashboard → Status = "approved" → Approval Monitor → learning_events Updated
                                                                    ↓
                                                            Background Thread
                                                          (checks every 5 minutes)
```

## Components

### `services/approval_sync.py`

The approval sync module:

- Polls Supabase for newly approved submissions (every 5 minutes)
- Updates existing `learning_events` records to reflect approval
- Creates new `learning_events` records if none exist
- Runs as a background daemon thread

### Integration with Flask

The approval monitor starts automatically when Flask starts, alongside the queue worker.

## Workflow

### Step-by-Step Process

| Step | Trigger | Action |
|------|---------|--------|
| **1️⃣** | Analyst reviews submission | Marks submission as `"approved"` in dashboard |
| **2️⃣** | Approval monitor runs (every 5 min) | Queries Supabase for approved submissions |
| **3️⃣** | Finds approved submission | Checks if `learning_event` exists |
| **4️⃣** | Updates learning event | Sets `approved: true`, `event_type: "approval"` |
| **5️⃣** | ML training ready | Approved event available for training algorithm |

### Data Flow

#### Before Approval
```json
{
  "submission_id": "uuid-here",
  "event_type": "auto_parse",
  "approved": false,
  "model_version": "psa-engine:latest",
  "confidence_score": 0.85
}
```

#### After Approval Sync
```json
{
  "submission_id": "uuid-here",
  "event_type": "approval",
  "approved": true,
  "model_version": "psa-engine:latest",
  "confidence_score": 0.85,
  "metadata": {
    "reviewed_at": "2025-11-05T...",
    "auto_approved": true
  }
}
```

## Implementation Details

### Polling Strategy

- **Interval**: Checks every 5 minutes (configurable)
- **Time Window**: Only checks submissions updated in the last 24 hours
- **Efficiency**: Only processes submissions with `status = "approved"`

### Update Logic

1. **Existing Learning Event**:
   - Updates `approved` to `true`
   - Changes `event_type` to `"approval"`
   - Preserves existing metadata
   - Adds `reviewed_at` timestamp

2. **No Learning Event**:
   - Creates new `learning_event` record
   - Sets `event_type: "approval"`
   - Sets `approved: true`
   - Includes metadata with `auto_generated: true`

### Error Handling

- Errors are logged but don't stop the monitor
- Failed syncs will be retried on next cycle
- Non-blocking: doesn't affect other services

## Configuration

### Polling Interval

Default: 5 minutes

Can be customized in `app.py`:

```python
start_approval_monitor(interval_minutes=10)  # Check every 10 minutes
```

### Environment Variables

Uses existing Supabase credentials:

```env
SUPABASE_URL=https://xyz.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

**No additional configuration needed.**

## Verification

### Check Monitor Started

When Flask starts, you should see:

```
[ApprovalSync] ✅ Background approval monitor started (checking every 5 minutes)
```

### Test Approval Sync

1. **Mark Submission Approved**:
   - Go to Supabase Dashboard
   - Find a submission with `status = "pending_review"`
   - Update it to `status = "approved"`

2. **Wait for Sync** (up to 5 minutes):
   - Monitor checks every 5 minutes
   - Look for log message: `[ApprovalSync] ✅ Updated learning_event for submission <uuid>`

3. **Verify in Supabase**:
   ```sql
   SELECT * FROM learning_events 
   WHERE submission_id = '<submission_id>'
   AND event_type = 'approval'
   AND approved = true;
   ```

### Expected Results

- `event_type` = `'approval'`
- `approved` = `true`
- `metadata` contains `reviewed_at` timestamp

## Troubleshooting

### Common Issues

1. **"Approval monitor not starting"**
   - Check Flask startup logs
   - Verify `app.py` imports `start_approval_monitor`
   - Check for import errors

2. **"No learning events updated"**
   - Verify submissions exist with `status = "approved"`
   - Check time window (only last 24 hours)
   - Verify Supabase connection

3. **"Learning event not found"**
   - Monitor creates new learning event automatically
   - Check if submission_id matches

### Debugging

Enable verbose logging:

```python
# In approval_sync.py, add debug prints
print(f"[ApprovalSync] Checking for approvals... Found {len(res.data)} approved submissions")
```

## Integration Points

### Flask Startup

In `app.py`:

```python
# Start background queue worker
from services.queue_manager import start_worker
start_worker()

# Start approval monitor
from services.approval_sync import start_approval_monitor
start_approval_monitor(interval_minutes=5)
```

### Background Threads

The Flask service now runs two background threads:

1. **Queue Worker** - Processes file jobs
2. **Approval Monitor** - Syncs approved submissions

Both run as daemon threads and start automatically.

## Benefits

✅ **Automatic Sync**: No manual intervention needed  
✅ **Real-time Updates**: Approved events available for training  
✅ **Audit Trail**: Complete history of approvals  
✅ **ML Training Ready**: Approved events feed learning algorithm  
✅ **Non-Blocking**: Failures don't affect other services  

## Related Documentation

- `docs/LEARNING-LOGGER.md` - Learning event creation
- `docs/SUPABASE-SCHEMA.md` - Database schema
- `docs/SUPABASE-SYNC.md` - Supabase sync integration

---

**Last Updated:** 2024-11-05  
**Status:** ✅ Integrated and Ready







