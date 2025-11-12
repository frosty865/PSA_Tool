# ModelManager Updated for vofc-unified

## Changes Made

ModelManager has been updated to work with the unified model approach:

### Model Name
- **Before**: `vofc-engine`
- **After**: `vofc-unified`

### Version Handling
- Now properly handles "latest" tag
- Creates versioned models: `vofc-unified:v2`, `vofc-unified:v3`, etc.
- When current version is "latest", creates v2
- Increments version numbers correctly

### Retraining Behavior
When ModelManager triggers retraining:
1. Creates new version: `vofc-unified:v2` (if current is `vofc-unified:latest`)
2. Uses Modelfile from training_data directory
3. Registers retrain event in Supabase

## Important Notes

### Manual Model Update Required
After ModelManager creates a new version (e.g., `vofc-unified:v2`), you need to:

1. **Update Processor to use new version:**
   ```powershell
   .\scripts\set-model-vofc-unified.ps1
   # Or manually:
   nssm set VOFC-Processor AppEnvironmentExtra "OLLAMA_MODEL=vofc-unified:v2"
   nssm restart VOFC-Processor
   ```

2. **Or keep using latest:**
   - If you want to always use the latest version, you can update the Modelfile to tag new versions as "latest"
   - Or manually tag: `ollama tag vofc-unified:v2 vofc-unified:latest`

### Current Configuration
- **Model Name**: `vofc-unified`
- **Current Version**: `latest` (as used by processor)
- **New Versions**: Will be created as `v2`, `v3`, etc.

## Service Status

After updating, restart the ModelManager service:

```powershell
# Fix paused service
.\scripts\fix-paused-service.ps1 -ServiceName VOFC-ModelManager

# Set environment variables
.\scripts\set-model-manager-env.ps1

# Restart
nssm restart VOFC-ModelManager
```

## Verification

Check that ModelManager is monitoring the correct model:

```powershell
Get-Content "C:\Tools\VOFC_Logs\model_manager.log" -Tail 20
```

Look for:
- `[CHECK] vofc-unified:latest | yield=...`
- Model name should be `vofc-unified`, not `vofc-engine`

