# Automated Model Retraining System

## Overview

The automated model retraining system monitors learning metrics and triggers model retraining when performance declines below acceptable thresholds.

## Purpose

When the model's acceptance rate drops below a threshold (default: 60%), the system automatically:
1. Detects the performance decline
2. Records a retraining event
3. Triggers model refresh/retraining
4. Logs all actions for auditing

## Architecture

```
Learning Stats → Retrain Monitor → Performance Check → Retrain Trigger
     ↓                ↓                    ↓                ↓
Supabase        Background Thread    Accept Rate < 0.6    Ollama CLI
```

## Components

### `services/model_retrainer.py`

The core retraining monitor that:
- Runs as a background daemon thread
- Checks learning stats every hour (configurable)
- Evaluates average accept rate over last 5 cycles
- Triggers retraining when threshold is breached
- Logs all events to `logs/model_retrainer.log`

**Configuration:**
- `THRESHOLD = 0.6` - Accept rate threshold (60%)
- `WINDOW = 5` - Number of learning cycles to evaluate
- `CHECK_INTERVAL_MIN = 60` - Check frequency (minutes)
- `MIN_STATS_REQUIRED = 3` - Minimum stats before triggering

### `services/supabase_client.py` Helpers

**`get_recent_learning_stats(limit=5)`**
- Retrieves recent learning statistics from Supabase
- Returns list of stats ordered by timestamp (most recent first)
- Returns empty list if table doesn't exist (graceful degradation)

**`record_retrain_event(avg_accept_rate, stats_window_size)`**
- Records retraining events in Supabase
- Tries `system_events` table first
- Falls back to `learning_events` table if `system_events` doesn't exist
- Includes metadata about trigger conditions

### `services/ollama_client.py` - `retrain_model()`

**Current Implementation:**
- Pulls latest model version from Ollama registry
- Uses `ollama pull` command
- 10-minute timeout for model pull
- Logs success/failure

**Future Enhancements:**
- Export approved/rejected samples from Supabase
- Create fine-tuning dataset
- Run fine-tuning script
- Create new model version
- Restart model service

## Integration

The retrain monitor is automatically started when Flask starts:

```python
# In app.py
from services.model_retrainer import start_retrain_monitor
start_retrain_monitor(interval_minutes=60)
```

## Workflow

### Step-by-Step Process

| Step | Action | Details |
|------|--------|---------|
| **1️⃣** | Monitor runs (every 60 min) | Background thread checks learning stats |
| **2️⃣** | Fetch recent stats | Gets last 5 learning cycles from Supabase |
| **3️⃣** | Calculate average | Computes average accept rate from stats |
| **4️⃣** | Evaluate condition | Compares average to threshold (0.6) |
| **5️⃣** | Trigger retraining | If below threshold, calls `retrain_model()` |
| **6️⃣** | Record event | Logs retraining event to Supabase |
| **7️⃣** | Pull model | Executes `ollama pull` to refresh model |

## Logging

All retraining activities are logged to:
- **File:** `logs/model_retrainer.log`
- **Format:** `%(asctime)s - %(levelname)s - %(message)s`
- **Level:** INFO (warnings and errors also logged)

## Configuration

### Environment Variables

None required - uses default configuration.

### Adjusting Thresholds

Edit `services/model_retrainer.py`:
```python
THRESHOLD = 0.6  # Change to desired accept rate threshold
WINDOW = 5       # Change number of cycles to evaluate
CHECK_INTERVAL_MIN = 60  # Change check frequency (minutes)
```

## Testing

### Manual Test

Run the retrainer in CLI mode:
```bash
python services/model_retrainer.py
```

This performs a single check and reports the result.

### Simulate Low Performance

To test retraining trigger:
1. Manually insert low accept_rate values into `learning_stats` table
2. Wait for next monitor cycle (or reduce `CHECK_INTERVAL_MIN` for testing)
3. Check `logs/model_retrainer.log` for trigger events

## Monitoring

### Check Retrain Monitor Status

Monitor logs:
```bash
tail -f logs/model_retrainer.log
```

### View Retraining Events

Query Supabase:
```sql
-- Check system_events table
SELECT * FROM system_events 
WHERE event_type = 'model_retrain' 
ORDER BY timestamp DESC;

-- Or check learning_events (fallback)
SELECT * FROM learning_events 
WHERE event_type = 'model_retrain' 
ORDER BY created_at DESC;
```

## Future Enhancements

1. **Fine-tuning Integration**
   - Export training data from Supabase
   - Generate fine-tuning dataset
   - Run fine-tuning pipeline
   - Deploy new model version

2. **Admin Notifications**
   - Email alerts when retraining is triggered
   - Dashboard notifications
   - Webhook support

3. **Advanced Triggers**
   - Multiple metric evaluation (not just accept rate)
   - Time-weighted averages
   - Confidence score trends
   - Custom threshold per model version

4. **Retraining Strategies**
   - Incremental fine-tuning
   - Full model retraining
   - A/B testing of new models
   - Rollback capability

## Troubleshooting

### Monitor Not Running

Check Flask startup logs for:
```
✅ Model retrain monitor thread started
```

### No Retraining Triggered

Possible causes:
- Not enough learning stats (need at least 3 cycles)
- Accept rate above threshold
- Learning stats table doesn't exist
- Check `logs/model_retrainer.log` for details

### Ollama Pull Fails

- Verify Ollama CLI is in PATH
- Check Ollama service is running
- Verify model name is correct
- Check network connectivity to Ollama registry

