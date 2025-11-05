# PSA Tool - Route Reference

## ✅ All Routes Return Valid JSON with Service Metadata

All routes include `"service": "PSA Processing Server"` in their responses.

## System Routes (`/api/system/*`)

### `GET /`
Root endpoint - service info
```json
{
  "service": "PSA Processing Server",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "health": "/api/system/health",
    "files": "/api/files/list"
  }
}
```

### `GET /api/system/health`
Health check endpoint - aggregates Flask, Ollama, and Supabase status
```json
{
  "flask": "ok",
  "ollama": "ok|offline|error",
  "supabase": "ok|error|missing",
  "service": "PSA Processing Server",
  "urls": {
    "flask": "http://127.0.0.1:8080",
    "ollama": "http://127.0.0.1:11434"
  },
  "timestamp": "2025-11-05T..."
}
```

### `GET /api/health`
Simple health check
```json
{
  "status": "ok",
  "message": "PSA Flask backend online",
  "service": "PSA Processing Server",
  "model": "psa-engine"
}
```

### `GET /api/progress`
Get processing progress
```json
{
  "status": "idle|processing|completed|error",
  "message": "No active processing",
  "current_file": null,
  "progress_percent": 0,
  "service": "PSA Processing Server"
}
```

### `GET /api/version`
Version information
```json
{
  "version": "1.0.0",
  "service": "PSA Processing Server"
}
```

## File Routes (`/api/files/*`)

### `GET /api/files/list`
List all files in incoming directory
```json
{
  "success": true,
  "files": [
    {
      "filename": "document.pdf",
      "size": 12345,
      "modified": 1234567890
    }
  ],
  "service": "PSA Processing Server"
}
```

### `GET /api/files/info?filename=document.pdf`
Get file information
```json
{
  "success": true,
  "info": {
    "filename": "document.pdf",
    "size": 12345,
    "modified": 1234567890,
    "path": "..."
  },
  "service": "PSA Processing Server"
}
```

### `GET /api/files/download/<filename>`
Download a file (returns file, not JSON)

### `POST /api/files/write`
Write content to a file
```json
Request:
{
  "filename": "output.json",
  "content": {...},
  "folder": "processed"
}

Response:
{
  "success": true,
  "path": "...",
  "service": "PSA Processing Server"
}
```

## Process Routes (`/api/process/*`)

### `POST /api/process/start`
Start processing a file
```json
Request:
{
  "filename": "document.pdf"
}

Response:
{
  "success": true,
  "result": {...},
  "service": "PSA Processing Server"
}
```

### `POST /api/process/document`
Process a document
```json
Request:
{
  "file_path": "...",
  "type": "pdf"
}

Response:
{
  "success": true,
  "result": {...},
  "service": "PSA Processing Server"
}
```

### `GET /api/process/<filename>`
Process a specific file by filename
```json
{
  "success": true,
  "result": {...},
  "service": "PSA Processing Server"
}
```

## Library Routes (`/api/library/*`)

### `GET /api/library/search?q=security`
Search the library
```json
{
  "success": true,
  "query": "security",
  "results": [...],
  "service": "PSA Processing Server"
}
```

### `POST /api/library/search`
Search the library (POST)
```json
Request:
{
  "query": "security"
}

Response:
{
  "success": true,
  "query": "security",
  "results": [...],
  "service": "PSA Processing Server"
}
```

### `GET /api/library/entry?id=123`
Get a specific library entry
```json
{
  "success": true,
  "entry": {
    "id": "123",
    "data": {...}
  },
  "service": "PSA Processing Server"
}
```

## Notes

- All routes support CORS (Cross-Origin Resource Sharing)
- All routes return JSON with `"service": "PSA Processing Server"` metadata
- Health checks assume Ollama and Tunnel are managed by NSSM services
- No subprocess calls - all communication via REST API
- File operations use `data/incoming/`, `data/processed/`, `data/errors/`

