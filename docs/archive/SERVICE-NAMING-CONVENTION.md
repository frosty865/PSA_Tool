# PSA Service Naming Convention

## Standardized Naming

All PSA services follow the pattern: `PSA-{ServiceName}`

### Service Names

| Old Name | New Name | Description |
|----------|----------|-------------|
| `VOFC-Flask` | `PSA-Flask` | Flask API server |
| `VOFC-Processor` | `PSA-Processor` | Document processing service |
| `VOFC-Tunnel` / `VOFC-Tunnel-Service` | `PSA-Tunnel` | Cloudflare tunnel service |
| `VOFC-ModelManager` / `VOFC-Model-Manager` | `PSA-ModelManager` | Model management service |

### Directory Structure

```
C:\Tools\
├── PSA-Flask\              # Flask API server
│   ├── app.py
│   ├── routes/
│   ├── services/
│   ├── config/
│   ├── tools/
│   └── .env
│
├── PSA-Processor\           # Document processing service
│   ├── vofc_processor.py
│   ├── services/
│   └── .env
│
├── PSA-Data\                # Shared data directory (renamed from Ollama\Data)
│   ├── incoming/
│   ├── processed/
│   ├── library/
│   ├── review/
│   ├── errors/
│   └── logs/
│
├── PSA-Archive\              # Archive directory (renamed from archive\VOFC)
│   └── Data/
│
└── Ollama\                   # Ollama installation (unchanged)
    └── [Ollama files]
```

### Environment Variables

Update these environment variables to use new paths:
- `VOFC_BASE_DIR` → `PSA_DATA_DIR` (or keep for backward compatibility)
- `VOFC_DATA_DIR` → `PSA_DATA_DIR` (or keep for backward compatibility)

### Windows Services (NSSM)

All services registered with NSSM should use the new naming:
- `PSA-Flask`
- `PSA-Processor`
- `PSA-Tunnel`
- `PSA-ModelManager`

## Migration Priority

1. **High Priority**: Service names (affects Windows services)
2. **Medium Priority**: Directory paths (affects file operations)
3. **Low Priority**: Environment variable names (can maintain backward compatibility)

## Backward Compatibility

All updates maintain backward compatibility by:
- Checking new paths/names first
- Falling back to legacy paths/names if new ones don't exist
- Supporting both old and new service names during transition

