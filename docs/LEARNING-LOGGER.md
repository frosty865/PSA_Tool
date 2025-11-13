# Learning Event Logger

## Overview

The Learning Event Logger automatically records every completed file processing job into the Supabase `learning_events` table. This enables the ML training system to track parsing performance and build a knowledge base of approved patterns.

## Purpose

Every completed job (file processed → JSON result saved → synced to Supabase) triggers:

✅ An insert into the `learning_events` table containing:
- `submission_id` - Link to the new submission
- `event_type: 'auto_parse'` - Indicates automatic parsing event
- `approved: false` - Set to false until analyst review
- `model_version` - Model used (e.g., `psa-engine:latest`)
- `confidence_score` - Average of all OFC or vulnerability confidences
- `metadata` - Summary of vulnerability/OFC counts and parser version

## Architecture

```
File Processing → JSON Result → Supabase Sync → Learning Event Log
                                        ↓
                                learning_events table
```

## Components

### `services/learning_logger.py`

The learning logger module:

- Reads processed JSON results
- Calculates average confidence scores from OFCs
- Builds metadata summary
- Inserts learning event record into Supabase

### Integration with Queue System

The queue worker in `services/queue_manager.py` automatically calls the learning logger after successful Supabase sync.

## Data Flow

### Step 1: Processing Complete
```json
{
  "vulnerabilities": [...],
  "options_for_consideration": [
    {"confidence_score": 0.85},
    {"confidence_score": 0.92}
  ],
  "parser_version": "psa-engine:latest"
}
```

### Step 2: Learning Event Created
```json
{
  "submission_id": "uuid-here",
  "event_type": "auto_parse",
  "approved": false,
  "model_version": "psa-engine:latest",
  "confidence_score": 0.885,
  "metadata": {
    "vulnerability_count": 3,
    "ofc_count": 5,
    "parser_version": "psa-engine:latest",
    "file_name": "document.pdf.json"
  }
}
```

## Schema Alignment

The learning logger matches the `learning_events` table schema:

| Column | Type | Example | Source |
|--------|------|---------|--------|
| `submission_id` | `uuid` | Link to submissions | From sync result |
| `event_type` | `text` | `'auto_parse'` | Fixed value |
| `approved` | `boolean` | `false` | Fixed value (until review) |
| `model_version` | `text` | `'psa-engine:latest'` | Parameter |
| `confidence_score` | `decimal` | `0.85` | Calculated average |
| `metadata` | `jsonb` | `{...}` | Built from result |
| `created_at` | `timestamptz` | Auto | Current timestamp |

## Confidence Score Calculation

The logger calculates confidence scores by:

1. Extracting all `confidence_score` values from OFCs
2. Filtering valid numeric values
3. Calculating arithmetic mean
4. Using `None` if no valid confidence scores found

```python
confidences = [0.85, 0.92, 0.78]
avg_confidence = statistics.mean(confidences)  # 0.85
```

## Metadata Structure

The metadata JSON contains:

```json
{
  "vulnerability_count": 3,
  "ofc_count": 5,
  "parser_version": "psa-engine:latest",
  "file_name": "document.pdf.json"
}
```

## Error Handling

The learning logger is **non-blocking**:

- If logging fails, the job is still marked as "done"
- Errors are logged but don't affect processing
- Sync can succeed even if learning event logging fails

### Example Error Handling

```python
try:
    log_learning_event(submission_id, result_path)
except Exception as learning_err:
    # Don't fail if learning event logging fails
    print(f"⚠️  Warning: Learning event logging failed: {str(learning_err)}")
    job["learning_event_error"] = str(learning_err)
```

## Usage

### Automatic Usage

The learning logger runs automatically after every successful file processing:

1. File processed → JSON saved
2. Supabase sync creates submission
3. Learning event logged automatically

### Manual Usage

```python
from services.learning_logger import log_learning_event

# Log a learning event
success = log_learning_event(
    submission_id="uuid-here",
    result_path="data/processed/document.pdf.json",
    model_version="psa-engine:latest"
)
```

## Integration Points

### Queue Manager Integration

In `services/queue_manager.py`:

```python
# After Supabase sync
submission_id = sync_processed_result(str(out_path))

# Log the learning event
try:
    log_learning_event(submission_id, str(out_path), model_version="psa-engine:latest")
except Exception as learning_err:
    # Non-blocking error handling
    print(f"⚠️  Warning: Learning event logging failed: {str(learning_err)}")
```

## Workflow

### Complete Processing Flow

```
1. File Upload
   ↓
2. Queue Job Added
   ↓
3. Worker Processes File
   ↓
4. JSON Result Saved
   ↓
5. Supabase Sync (creates submission)
   ↓
6. Learning Event Logged ← NEW
   ↓
7. Job Marked as "done"
```

### Learning Event Lifecycle

1. **Creation**: Event created with `approved: false`
2. **Review**: Analyst reviews submission in dashboard
3. **Approval**: When submission approved, event `approved` can be updated to `true`
4. **Training**: Approved events feed ML training algorithm

## Benefits

✅ **Automatic Tracking**: Every parse is logged automatically
✅ **Performance Metrics**: Confidence scores track model performance
✅ **Training Data**: Approved events become training examples
✅ **Audit Trail**: Complete history of all parsing operations
✅ **Non-Blocking**: Failures don't affect processing

## Troubleshooting

### Common Issues

1. **"Unable to read result JSON"**
   - Check that result file exists at `result_path`
   - Verify JSON format is valid

2. **"Failed to log learning_event"**
   - Check Supabase connection
   - Verify `learning_events` table exists
   - Check RLS policies allow inserts (or use service role key)

3. **Confidence score is None**
   - No OFCs had confidence scores
   - This is normal - some results may not have confidence data

### Verification

Check learning events in Supabase:

```sql
SELECT * FROM learning_events 
WHERE event_type = 'auto_parse' 
ORDER BY created_at DESC 
LIMIT 10;
```

## Related Documentation

- `docs/SUPABASE-SCHEMA.md` - Complete database schema
- `docs/SUPABASE-SYNC.md` - Supabase sync integration
- `docs/QUEUE-SYSTEM.md` - Queue system documentation

---

**Last Updated:** 2024-01-XX  
**Status:** ✅ Integrated and Ready
















