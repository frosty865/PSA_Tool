# VOFC Model Manager

## Overview

The Model Manager is an autonomous maintenance service that monitors model performance, checks learning event metrics, and triggers conditional retraining when thresholds are met.

## Features

- **Autonomous Monitoring**: Checks model performance from Supabase `view_model_performance_summary`
- **Conditional Retraining**: Only retrains when performance drops below thresholds or new verified data is available
- **Silent Operation**: Runs in background, logs to file
- **Complete Traceability**: Records all retraining events in `learning_events` table

## Installation Location

The Model Manager is installed in its own directory:
- **Script**: `C:\Tools\ModelManager\model_manager.py`
- **Working Directory**: `C:\Tools\ModelManager`
- **Logs**: `C:\Tools\VOFC_Logs\model_manager.log`

## Configuration

Edit `C:\Tools\ModelManager\model_manager.py` to adjust:

```python
MODEL_NAME = "vofc-engine"
MIN_VULN_YIELD = 80.0      # minimum acceptable vuln yield %
MIN_DELTA_SCORE = 0        # if below, retraining candidate
MIN_NEW_EVENTS = 3         # minimum new learning events since last retrain
```

## Retraining Triggers

The manager retrains when **any** of these conditions are met:

1. **Vulnerability Yield < 80%**: Model is extracting fewer vulnerabilities than expected
2. **Delta Score < 0**: Model performance has degraded
3. **≥ 3 New Learning Events**: Enough new training data is available

## Usage

### Manual Testing

```bash
python services/model_manager.py
```

### Deploy as Windows Service (NSSM)

**Option 1: Use the installation script (Recommended)**
```powershell
# Run PowerShell as Administrator
.\scripts\install-model-manager-service.ps1
```

**Option 2: Manual installation**
```powershell
nssm install VOFC-ModelManager "C:\Tools\python\python.exe" "C:\Tools\ModelManager\model_manager.py"
nssm set VOFC-ModelManager AppDirectory "C:\Tools\ModelManager"
nssm set VOFC-ModelManager Start SERVICE_AUTO_START
nssm set VOFC-ModelManager AppStdout "C:\Tools\ModelManager\service_output.log"
nssm set VOFC-ModelManager AppStderr "C:\Tools\ModelManager\service_error.log"
nssm start VOFC-ModelManager
```

### Schedule with Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 2:00 AM
4. Action: Start a program
   - Program: `C:\Program Files\Python311\python.exe`
   - Arguments: `C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\services\model_manager.py`
   - Start in: `C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool`

## Logs

Logs are written to:
- **File**: `C:\Tools\VOFC_Logs\model_manager.log`
- **Format**: `%(asctime)s | %(levelname)s | %(message)s`

## How It Works

1. **Query Performance Summary**: Fetches model performance data from `view_model_performance_summary` view
2. **Check Learning Events**: Counts recent learning events (last 7 days)
3. **Evaluate Thresholds**: Compares current metrics against configured thresholds
4. **Trigger Retraining**: If thresholds are met, creates new model version using Modelfile
5. **Log Event**: Records retraining event in `learning_events` table

## Retraining Process

When retraining is triggered:

1. Extracts version number from current model (e.g., "v2" → "v3")
2. Runs: `ollama create vofc-engine:v3 -f training_data/Modelfile`
3. Creates new model with enhanced system prompts
4. Logs retraining event to Supabase

## Database Requirements

The manager requires:

- **View**: `view_model_performance_summary` with columns:
  - `model_id`
  - `model_version`
  - `vuln_yield_pct`
  - `avg_delta_score`
  
- **Table**: `learning_events` for logging retraining events

## Integration with Flask

You can also trigger the model manager from Flask:

```python
# In routes/system.py
elif action == "run_model_manager":
    try:
        from services.model_manager import evaluate_models
        evaluate_models()
        msg = "Model manager evaluation completed"
    except Exception as e:
        logging.error(f"Error in model manager: {e}")
        msg = f"Model manager error: {str(e)}"
```

## Troubleshooting

### "No summary data found"
- Check that `view_model_performance_summary` view exists in Supabase
- Verify the view returns data for your models

### "Modelfile not found"
- Ensure `training_data/Modelfile` exists
- Run `python scripts/build_usss_training.py` to create it

### "Retraining failed"
- Check Ollama is running: `ollama list`
- Verify Modelfile syntax is correct
- Check logs in `C:\Tools\VOFC_Logs\model_manager.log`

### "Could not register retrain event"
- This is non-critical - retraining still completes
- Check `learning_events` table schema matches expected fields
- Verify Supabase connection is working

## Example Log Output

```
2025-11-08 04:30:00 | INFO | === VOFC Model Manager Run Start ===
2025-11-08 04:30:01 | INFO | [CHECK] vofc-engine:v2 | yield=75.5% delta=-50
2025-11-08 04:30:01 | INFO | [INFO] Recent learning events (last 7 days): 5
2025-11-08 04:30:01 | INFO | [DECISION] Retraining triggered: yield=75.5%<80.0%, delta=-50<0, new_events=5>=3
2025-11-08 04:30:01 | INFO | [ACTION] Retraining vofc-engine:v3 due to yield=75.5%<80.0%, delta=-50<0, new_events=5>=3
2025-11-08 04:30:15 | INFO | [SUCCESS] Model vofc-engine:v3 created successfully
2025-11-08 04:30:16 | INFO | [SUCCESS] Registered retrain event for vofc-engine:v3
2025-11-08 04:30:16 | INFO | === VOFC Model Manager Run End ===
```

## Notes

- The manager uses the **Modelfile** approach (system prompts), not full fine-tuning
- For actual weight training, use external frameworks (Hugging Face, Unsloth, Axolotl)
- The manager is designed to be non-intrusive - it only acts when thresholds are met
- All operations are logged for auditability

