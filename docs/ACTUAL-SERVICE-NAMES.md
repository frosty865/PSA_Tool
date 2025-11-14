# Actual Windows Service Names

## Current Service Names (As Installed)

These are the **actual** service names currently registered with NSSM:

| Service | Actual Name | Display Name | Notes |
|---------|-------------|--------------|-------|
| Flask API | `vofc-flask` | VOFC Flask API Server | **Lowercase with hyphen** |
| Processor | `VOFC-Processor` | VOFC-Processor | Mixed case |
| Tunnel | `VOFC-Tunnel` | VOFC-Tunnel | Mixed case |
| Model Manager | `VOFC-ModelManager` | VOFC-ModelManager | Mixed case |
| Ollama | `VOFC-Ollama` | VOFC-Ollama | Mixed case |
| Auto Retrain | `VOFC-AutoRetrain` | VOFC-AutoRetrain | Mixed case |

## Code Updates

All service checks have been updated to:
1. **Check actual service names first** (as installed)
2. **Try variations** (case-insensitive, different formats)
3. **Fall back to alternatives** for compatibility

### Service Name Check Order

**Flask Service:**
- `vofc-flask` (actual)
- `VOFC-Flask` (alternative)
- `PSA-Flask` (future migration)

**Processor Service:**
- `VOFC-Processor` (actual)
- `vofc-processor` (case variation)
- `PSA-Processor` (future migration)

**Tunnel Service:**
- `VOFC-Tunnel` (actual)
- `vofc-tunnel` (case variation)
- `VOFC-Tunnel-Service` (alternative)
- `PSA-Tunnel` (future migration)

**Model Manager Service:**
- `VOFC-ModelManager` (actual)
- `vofc-modelmanager` (case variation)
- `VOFC-Model-Manager` (alternative)
- `PSA-ModelManager` (future migration)

**Ollama Service:**
- `VOFC-Ollama` (actual)
- `vofc-ollama` (case variation)
- `Ollama` (alternative)

**Auto Retrain Service:**
- `VOFC-AutoRetrain` (actual)
- `vofc-autoretrain` (case variation)
- `PSA-AutoRetrain` (future migration)

## Important Notes

1. **Service names are case-sensitive** in Windows, but code checks multiple variations
2. **Actual name is `vofc-flask`** (lowercase) - not `VOFC-Flask` or `PSA-Flask`
3. **Code checks actual names first** to ensure it finds running services
4. **Future migration** to `PSA-*` naming is supported but not required

## Verifying Service Names

To check actual service names on your system:

```powershell
# List all services
Get-Service | Where-Object {$_.Name -like "*vofc*" -or $_.Name -like "*psa*"}

# Or use NSSM
nssm list

# Check specific service
nssm status vofc-flask
nssm status VOFC-Processor
nssm status VOFC-Tunnel
nssm status VOFC-Ollama
nssm status VOFC-ModelManager
nssm status VOFC-AutoRetrain
```

## Migration Path

When ready to migrate service names:
1. Stop old service
2. Install with new name
3. Update code to check new name first
4. Remove old service

Code supports both during transition period.

