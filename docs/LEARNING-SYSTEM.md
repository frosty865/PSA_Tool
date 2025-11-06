# Learning Feedback and Adaptive Improvement System

## Overview

The learning system records analyst feedback (approvals, rejections, corrections) and uses it to automatically adjust system heuristics, improving extraction accuracy over time.

## Architecture

### Components

1. **Learning Engine** (`services/learning_engine.py`)
   - Processes learning events periodically
   - Calculates acceptance rates and statistics
   - Triggers heuristic adjustments

2. **Heuristics Service** (`services/heuristics.py`)
   - Manages confidence thresholds
   - Adjusts thresholds based on acceptance rates
   - Persists configuration to `data/heuristics_config.json`

3. **Learning API** (`routes/learning.py`)
   - Records analyst feedback events
   - Provides statistics and heuristic information

4. **Supabase Integration** (`services/supabase_client.py`)
   - Stores learning events in `learning_events` table
   - Optionally stores statistics in `learning_stats` table

---

## How It Works

### 1. Event Recording

Analysts provide feedback through the frontend, which calls:

```http
POST /api/learning/event
Content-Type: application/json

{
  "submission_id": "uuid",
  "event_type": "approval",
  "approved": true,
  "model_version": "psa-engine:latest",
  "confidence_score": 0.85,
  "metadata": {
    "vulnerability_id": "uuid",
    "ofc_count": 3
  }
}
```

**Event Types:**
- `approval` - Submission/vulnerability was approved
- `rejection` - Submission/vulnerability was rejected
- `correction` - Analyst made corrections
- `edited` - Analyst edited the content

### 2. Learning Cycle

Every 60 minutes (configurable), the learning engine:

1. **Fetches Events**: Retrieves learning events from the last cycle period
2. **Categorizes**: Separates events by type (accepted, rejected, edited)
3. **Calculates Statistics**:
   - Total events
   - Acceptance rate
   - Average confidence scores (accepted vs rejected)
   - Confidence gap
4. **Adjusts Heuristics**: Updates confidence thresholds based on acceptance rate
5. **Stores Statistics**: Saves statistics (if `learning_stats` table exists)

### 3. Heuristic Adjustment

The system adjusts confidence thresholds based on acceptance rate:

- **High Accept Rate (>0.8)**: Model is too conservative → Lower threshold
- **Low Accept Rate (<0.5)**: Model is too permissive → Raise threshold
- **Medium Accept Rate (0.5-0.8)**: Make small adjustments toward target (0.65)

**Adjustment Logic:**
```python
TARGET_ACCEPT_RATE = 0.65
ADJUSTMENT_STEP = 0.05

if accept_rate > 0.8:
    new_threshold = current_threshold - 0.05  # Lower
elif accept_rate < 0.5:
    new_threshold = current_threshold + 0.05  # Raise
else:
    # Adjust proportionally toward target
    new_threshold = current_threshold - (rate_diff * 0.05)
```

---

## API Endpoints

### Record Learning Event

```http
POST /api/learning/event
Content-Type: application/json

{
  "submission_id": "uuid" (optional),
  "record_id": "uuid" (optional, alternative to submission_id),
  "event_type": "approval" | "rejection" | "correction" | "edited",
  "approved": true | false,
  "model_version": "psa-engine:latest" (optional),
  "confidence_score": 0.85 (optional, 0.0-1.0),
  "metadata": {} (optional)
}
```

**Response:**
```json
{
  "status": "recorded",
  "event_type": "approval",
  "event_id": "uuid",
  "message": "Learning event recorded successfully"
}
```

### Get Learning Statistics

```http
GET /api/learning/stats?limit=10
```

**Response:**
```json
{
  "status": "ok",
  "stats": [
    {
      "timestamp": "2025-01-15T10:30:00",
      "total_events": 25,
      "accepted": 18,
      "rejected": 5,
      "edited": 2,
      "accept_rate": 0.72,
      "avg_accepted_confidence": 0.85,
      "avg_rejected_confidence": 0.62
    }
  ],
  "count": 1
}
```

**Note:** Requires `learning_stats` table. Returns 404 if table doesn't exist.

### Get Heuristics

```http
GET /api/learning/heuristics
```

**Response:**
```json
{
  "status": "ok",
  "heuristics": {
    "confidence_threshold": 0.72,
    "high_confidence_threshold": 0.87,
    "last_updated": "2025-01-15T10:30:00",
    "accept_rate": 0.72
  }
}
```

---

## Configuration

### Learning Monitor Interval

The learning monitor runs every 60 minutes by default. To change:

```python
# In app.py
start_learning_monitor(interval_minutes=30)  # Run every 30 minutes
```

### Heuristics Configuration

Heuristics are stored in `data/heuristics_config.json`:

```json
{
  "confidence_threshold": 0.72,
  "high_confidence_threshold": 0.87,
  "last_updated": "2025-01-15T10:30:00",
  "accept_rate": 0.72,
  "adjustment_history": [
    {
      "timestamp": "2025-01-15T10:30:00",
      "old_threshold": 0.70,
      "new_threshold": 0.72,
      "accept_rate": 0.72,
      "reason": "Adjusting toward target (0.72 vs 0.65)"
    }
  ]
}
```

**Default Thresholds:**
- `confidence_threshold`: 0.7 (minimum confidence for acceptance)
- `high_confidence_threshold`: 0.85 (high confidence threshold)

---

## Database Schema

### `learning_events` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `submission_id` | `uuid` | Foreign key to `submissions.id` (nullable) |
| `event_type` | `text` | `'approval'`, `'rejection'`, `'correction'`, `'edited'` |
| `approved` | `boolean` | Whether event represents approved example |
| `model_version` | `text` | Model version (e.g., `'psa-engine:latest'`) |
| `confidence_score` | `decimal` | Confidence score (0.0-1.0) |
| `metadata` | `jsonb` | Additional event metadata |
| `created_at` | `timestamptz` | Creation timestamp |

### `learning_stats` Table (Optional)

If you want to track learning statistics over time, create this table:

```sql
CREATE TABLE learning_stats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  timestamp TIMESTAMPTZ NOT NULL,
  window_minutes INTEGER,
  total_events INTEGER,
  accepted INTEGER,
  rejected INTEGER,
  edited INTEGER,
  accept_rate DECIMAL(3,3),
  avg_accepted_confidence DECIMAL(3,3),
  avg_rejected_confidence DECIMAL(3,3),
  confidence_gap DECIMAL(3,3),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Integration Examples

### Frontend: Record Approval

```javascript
async function recordApproval(submissionId, confidenceScore) {
  const response = await fetch('/api/learning/event', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      submission_id: submissionId,
      event_type: 'approval',
      approved: true,
      model_version: 'psa-engine:latest',
      confidence_score: confidenceScore,
      metadata: {
        vulnerability_id: submissionId,
        ofc_count: 3
      }
    })
  });
  
  return await response.json();
}
```

### Frontend: Record Rejection

```javascript
async function recordRejection(submissionId, reason) {
  const response = await fetch('/api/learning/event', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      submission_id: submissionId,
      event_type: 'rejection',
      approved: false,
      model_version: 'psa-engine:latest',
      metadata: {
        rejection_reason: reason
      }
    })
  });
  
  return await response.json();
}
```

### Get Current Thresholds

```javascript
async function getHeuristics() {
  const response = await fetch('/api/learning/heuristics');
  const data = await response.json();
  console.log('Current confidence threshold:', data.heuristics.confidence_threshold);
  return data.heuristics;
}
```

---

## Monitoring

### Logs

The learning system logs all activities:

```
2025-01-15 10:30:00 - INFO - Starting learning engine cycle (looking back 60 minutes)...
2025-01-15 10:30:01 - INFO - Learning cycle complete: {'total_events': 25, 'accept_rate': 0.72, ...}
2025-01-15 10:30:01 - INFO - Adjusted confidence threshold: 0.700 → 0.720 (Adjusting toward target)
```

### Metrics

Track learning effectiveness by monitoring:
- Acceptance rate trends
- Confidence score distributions
- Threshold adjustment frequency
- Model version performance

---

## Best Practices

1. **Consistent Feedback**: Ensure analysts provide feedback for all reviewed items
2. **Metadata**: Include relevant metadata (vulnerability_id, ofc_count) for better analysis
3. **Model Versioning**: Track model versions to compare performance across updates
4. **Threshold Monitoring**: Review threshold adjustments regularly to ensure they're reasonable
5. **Statistics Review**: Periodically review learning statistics to identify trends

---

## Troubleshooting

### Learning Monitor Not Running

**Check:** Verify the monitor started in Flask logs:
```
✅ Learning monitor thread started (checking every 60 minutes)
```

**Fix:** Ensure `start_learning_monitor()` is called in `app.py`

### No Events Being Processed

**Check:** Verify events are being recorded:
```sql
SELECT COUNT(*) FROM learning_events WHERE created_at > NOW() - INTERVAL '1 hour';
```

**Fix:** Ensure frontend is calling `/api/learning/event` endpoint

### Thresholds Not Adjusting

**Check:** Review heuristics config file:
```bash
cat data/heuristics_config.json
```

**Fix:** Ensure acceptance rate is significantly different from target (0.65) to trigger adjustments

### Statistics Not Saving

**Note:** `learning_stats` table is optional. If it doesn't exist, statistics are logged but not persisted.

**Fix:** Create `learning_stats` table (see Database Schema section)

---

## Related Documentation

- `docs/LEARNING-LOGGER.md` - Learning event creation from approval sync
- `docs/APPROVAL-SYNC.md` - How approvals trigger learning events
- `docs/SUPABASE-SCHEMA.md` - Complete database schema including `learning_events`

---

**Last Updated:** 2025-01-15  
**Version:** 1.0.0

