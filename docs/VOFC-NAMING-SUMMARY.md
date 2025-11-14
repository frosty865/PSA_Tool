# VOFC Service Naming - Final Summary

## Actual Service Names and Locations

All services use **VOFC-*** naming convention (matching actual installed service names):

| Service | Service Name | Directory Location |
|---------|-------------|-------------------|
| Flask API | `vofc-flask` (lowercase) | `C:\Tools\VOFC-Flask` |
| Processor | `VOFC-Processor` | `C:\Tools\VOFC-Processor` |
| Tunnel | `VOFC-Tunnel` | (if applicable) |
| Model Manager | `VOFC-ModelManager` | (if applicable) |

## Directory Structure

```
C:\Tools\
├── VOFC-Flask\              # Flask API server
│   ├── app.py
│   ├── routes/
│   ├── services/
│   ├── config/
│   ├── tools/
│   ├── requirements.txt
│   ├── start.ps1
│   └── .env
│
├── VOFC-Processor\          # Document processor
│   ├── vofc_processor.py
│   ├── install_service.ps1
│   ├── requirements.txt
│   └── .env (if needed)
│
└── Ollama\                  # Data directories (unchanged)
    └── Data\
        ├── incoming/
        ├── processed/
        ├── library/
        └── logs/
```

## Migration Scripts

- **`scripts/migrate-python-to-tools.ps1`** - Migrates Flask server only
- **`scripts/migrate-all-services.ps1`** - Migrates Flask + Processor

## Quick Migration

```powershell
# Complete migration (all services)
.\scripts\migrate-all-services.ps1

# Or Flask only
.\scripts\migrate-python-to-tools.ps1
```

## Service Updates

### Flask Service (vofc-flask)
```powershell
nssm set vofc-flask Application "C:\Tools\VOFC-Flask\venv\Scripts\python.exe"
nssm set vofc-flask AppDirectory "C:\Tools\VOFC-Flask"
nssm set vofc-flask AppParameters "-m waitress --listen=0.0.0.0:8080 server:app"
nssm restart vofc-flask
```

### Processor Service (VOFC-Processor)
```powershell
cd C:\Tools\VOFC-Processor
.\install_service.ps1
```

## Files Updated

All code references updated to use:
- `C:\Tools\VOFC-Flask` (not PSA-Flask)
- `C:\Tools\VOFC-Processor` (not PSA-Processor)
- Service name checks use actual names: `vofc-flask`, `VOFC-Processor`, etc.

