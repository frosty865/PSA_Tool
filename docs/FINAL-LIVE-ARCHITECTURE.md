# Final Live Architecture

## Component Overview

| Component | Role | Runs As | Notes |
|-----------|------|---------|-------|
| **VOFC-Processor** | Background ingestion engine — watches `C:\Tools\Ollama\Data\incoming\`, extracts text, calls `vofc-unified:latest`, uploads JSON & Supabase records. | Windows Service (VOFC-Processor) | No user interaction. 30-second loop. |
| **VOFC-Flask** | REST API for the web frontend (`/api/system/health`, `/api/submissions`, `/api/files/list`, etc.). | Windows Service (VOFC-Flask) | Required for live website and dashboard. |
| **Ollama** | Model host (LLM endpoint for both Processor & Flask). | Windows Service (VOFC-Ollama) | Must stay running; listen on `http://127.0.0.1:11434`. |
| **Supabase (remote)** | Central DB / dedupe authority. | Managed | Receives inserts, reference lookups, dashboard queries. |
| **Cloudflare Tunnel** | Optional external access. | Windows Service (VOFC-Tunnel) | Publishes Flask API to the public domain. |

---

## ⚙️ Keep Running

These services must be running for the system to function:

```powershell
nssm start VOFC-Processor     # ingestion engine
nssm start VOFC-Flask         # backend API
nssm start VOFC-Ollama        # model server
```

### Service Dependencies

```
VOFC-Processor → VOFC-Ollama (for model calls)
VOFC-Processor → Supabase (for inserts/dedupe)
VOFC-Flask → Supabase (for dashboard reads)
VOFC-Flask → VOFC-Processor (status polling only)
VOFC-Tunnel → VOFC-Flask (optional, for external access)
```

**Important:** Processor and Flask are **independent peers**:
- ✅ Processor can run without Flask
- ✅ Flask can run without Processor (dashboard still works)
- ✅ No circular dependencies
- ✅ Each service can restart independently

---

## ❌ Keep Disabled

These old services should be stopped and disabled:

```powershell
# Stop services
nssm stop VOFC-Chunker
nssm stop VOFC-AutoProcessor

# Disable auto-start
nssm set VOFC-Chunker Start SERVICE_DISABLED
nssm set VOFC-AutoProcessor Start SERVICE_DISABLED
```

### Deprecated Services

- **VOFC-Chunker**: Old chunking system (replaced by unified pipeline)
- **VOFC-AutoProcessor**: Old 3-phase processor (replaced by VOFC-Processor)

---

## Inter-Service Communication

```
[VOFC-Processor] ---> Ollama (localhost:11434/api/generate)
       |
       +--> Supabase (HTTPS API) for inserts / dedupe
       |
[VOFC-Flask] ---> Supabase (reads for dashboard)
       |
       +--> VOFC-Processor (status polling via logs or shared table)
```

**Key Points:**
- Processor and Flask are **peers** — no dependency cycle
- Frontend (zophielgroup.com) interacts **only with Flask**
- Flask **never triggers document ingestion directly**
- Each service can operate independently

---

## 🧠 Operational Rule

> **"Flask stays on for visibility and control, but all ingestion is performed by VOFC-Processor."**

**Benefits:**
- ✅ If web API restarts, background processing continues uninterrupted
- ✅ If Processor restarts, web interface remains available
- ✅ No circular dependencies
- ✅ Independent scaling and maintenance

---

## Data Flow

### Automatic Processing (VOFC-Processor)

```
PDF File → C:\Tools\Ollama\Data\incoming\
    ↓
VOFC-Processor (30s loop detects file)
    ↓
Extract text (PyMuPDF)
    ↓
Call vofc-unified:latest via Ollama API (localhost:11434/api/generate)
    ↓
Parse JSON response
    ↓
Upload to Supabase (with deduplication via HTTPS API)
    ↓
Move to C:\Tools\Ollama\Data\library\
```

**Communication:**
- **Ollama**: Direct HTTP API calls (`http://127.0.0.1:11434/api/generate`)
- **Supabase**: HTTPS API for inserts and deduplication checks
- **No Flask dependency**: Processor operates independently

### Web Interface (VOFC-Flask)

```
User → Web Frontend (zophielgroup.com)
    ↓
Next.js API Routes
    ↓
VOFC-Flask REST API
    ↓
Supabase (queries/reads for dashboard)
    ↓
VOFC-Processor (status polling via logs or shared table)
```

**Communication:**
- **Supabase**: Read-only queries for dashboard data
- **VOFC-Processor**: Status polling (logs or shared database table)
- **No ingestion triggers**: Flask never initiates document processing

---

## Service Status Check

```powershell
# Check all services
nssm status VOFC-Processor
nssm status VOFC-Flask
nssm status VOFC-Ollama
nssm status VOFC-Tunnel

# Verify old services are disabled
nssm status VOFC-Chunker        # Should be SERVICE_STOPPED or not exist
nssm status VOFC-AutoProcessor  # Should be SERVICE_STOPPED or not exist
```

---

## Security & Access Control

### Port Visibility & Firewall Rules

- **VOFC-Ollama** → Bind to `127.0.0.1` only (do not expose externally)
  - Port: `11434` (localhost only)
  - Firewall: Block inbound connections from external networks
  - Reason: AI models should not be accessible from outside

- **VOFC-Flask** → Exposed through Cloudflare Tunnel only (never open raw port 8080)
  - Port: `8080` (localhost only)
  - External Access: Via Cloudflare Tunnel only
  - Firewall: Block inbound connections to port 8080 from external networks
  - Reason: Tunnel provides authentication, DDoS protection, and SSL

- **VOFC-Processor** → No inbound connections; outbound HTTPS only to Supabase
  - No listening ports
  - Outbound: HTTPS to Supabase API only
  - Firewall: Allow outbound HTTPS (443) to Supabase domain
  - Reason: Background service should not accept connections

- **Supabase Keys** → Stored securely in `.env` or Windows environment variables
  - Never commit keys to version control
  - Use Windows environment variables for services (NSSM)
  - Rotate keys periodically
  - Use service role key only for Processor (not anon key)

### Security Best Practices

1. **Environment Variables**: Store all secrets in `.env` or Windows environment variables (not in code)
2. **Service Isolation**: Each service runs with minimal required permissions
3. **Network Isolation**: Services communicate via localhost or HTTPS only
4. **Key Rotation**: Rotate Supabase keys and API tokens regularly
5. **Logging**: Monitor logs for unauthorized access attempts

---

## Environment Variables

| Variable | Description | Example | Required By |
|-----------|-------------|----------|-------------|
| `OLLAMA_MODEL` | Model tag used by Processor | `vofc-unified:latest` | VOFC-Processor |
| `OLLAMA_BASE_URL` | Ollama server address | `http://127.0.0.1:11434` | VOFC-Processor |
| `SUPABASE_URL` | Base Supabase endpoint | `https://xyz.supabase.co` | VOFC-Processor, VOFC-Flask |
| `SUPABASE_KEY` | Service key for inserts | `eyJhbGci...` | VOFC-Processor |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (alternative) | `eyJhbGci...` | VOFC-Processor |
| `NEXT_PUBLIC_SUPABASE_URL` | Public Supabase URL (fallback) | `https://xyz.supabase.co` | VOFC-Processor, VOFC-Flask |
| `LOG_LEVEL` | Logging verbosity | `INFO`, `DEBUG`, `WARNING`, `ERROR` | VOFC-Processor |
| `PROCESS_INTERVAL` | Seconds between directory scans | `30` | VOFC-Processor |
| `VOFC_DATA_DIR` | Base data directory | `C:\Tools\Ollama\Data` | VOFC-Processor |
| `FLASK_PORT` | Flask server port | `8080` | VOFC-Flask |
| `FLASK_ENV` | Flask environment | `production` | VOFC-Flask |

### Setting Environment Variables

**For VOFC-Processor (via NSSM):**
```powershell
# Set individual variable
C:\Tools\nssm\nssm.exe set VOFC-Processor AppEnvironmentExtra "OLLAMA_MODEL=vofc-unified:latest`nSUPABASE_URL=https://xyz.supabase.co"

# Or use script
.\scripts\set-vofc-processor-env.ps1
```

**For VOFC-Flask (via NSSM):**
```powershell
C:\Tools\nssm\nssm.exe set VOFC-Flask AppEnvironmentExtra "FLASK_PORT=8080`nFLASK_ENV=production"
```

**For local development (.env file):**
```env
OLLAMA_MODEL=vofc-unified:latest
OLLAMA_BASE_URL=http://127.0.0.1:11434
SUPABASE_URL=https://xyz.supabase.co
SUPABASE_KEY=eyJhbGci...
LOG_LEVEL=INFO
PROCESS_INTERVAL=30
```

---

## Daily Health Checklist

Quick verification steps for daily operations or after service restarts:

### 1. Service Status Check
```powershell
nssm status VOFC-Processor    # Must be SERVICE_RUNNING
nssm status VOFC-Flask       # Must be SERVICE_RUNNING
nssm status VOFC-Ollama      # Must be SERVICE_RUNNING
```

### 2. Ollama Model Verification
```powershell
# Check if model is available
curl http://127.0.0.1:11434/api/tags

# Should return JSON with vofc-unified:latest in models list
```

### 3. Flask API Health Check
```powershell
# Check Flask health endpoint
curl http://127.0.0.1:8080/api/system/health

# Should return: { "flask": "ok", "ollama": "ok", "supabase": "ok", ... }
```

### 4. Processing Verification
- ✅ Confirm new PDFs disappear from `C:\Tools\Ollama\Data\incoming\`
- ✅ Verify processed files appear in `C:\Tools\Ollama\Data\library\`
- ✅ Check for error files in `C:\Tools\Ollama\Data\processed\*_error.txt`

### 5. Database Verification
```sql
-- Check Supabase for recent inserts
SELECT COUNT(*), MAX(created_at) 
FROM vulnerabilities 
WHERE created_at >= CURRENT_DATE;

-- Should show today's records with recent timestamps
```

### 6. Log Verification
```powershell
# Check Processor logs for errors
Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_err.log -Tail 20

# Should not show repeated errors (occasional warnings OK)
```

### Quick Health Script
```powershell
# Run all checks at once
.\scripts\manage-services.ps1 status
curl http://127.0.0.1:11434/api/tags
curl http://127.0.0.1:8080/api/system/health
Get-ChildItem C:\Tools\Ollama\Data\incoming\*.pdf | Measure-Object
Get-ChildItem C:\Tools\Ollama\Data\library\*.pdf | Measure-Object
```

---

## Configuration

### VOFC-Processor
- **Script**: `C:\Tools\py_scripts\vofc_processor\vofc_processor.py`
- **Incoming**: `C:\Tools\Ollama\Data\incoming\`
- **Processed**: `C:\Tools\Ollama\Data\processed\`
- **Library**: `C:\Tools\Ollama\Data\library\`
- **Model**: `vofc-unified:latest` (via `OLLAMA_MODEL` env var)
- **Loop Interval**: 30 seconds

### VOFC-Flask
- **Script**: `C:\Tools\VOFC-Flask\server.py`
- **Port**: `8080` (default)
- **Endpoints**: `/api/system/*`, `/api/submissions/*`, `/api/files/*`

### VOFC-Ollama
- **Port**: `11434` (default)
- **Models**: `vofc-unified:latest` (primary)
- **API**: `http://127.0.0.1:11434/api/generate`

---

## Troubleshooting

### VOFC-Processor not processing files
1. Check service status: `nssm status VOFC-Processor`
2. Check logs: `C:\Tools\Ollama\Data\logs\vofc_processor_err.log`
3. Verify incoming directory: `C:\Tools\Ollama\Data\incoming\`
4. Verify Ollama is running: `nssm status VOFC-Ollama`
5. Check model availability: `curl http://127.0.0.1:11434/api/tags`

### VOFC-Flask not responding
1. Check service status: `nssm status VOFC-Flask`
2. Check port: `netstat -ano | findstr :8080`
3. Check logs: NSSM stdout/stderr logs
4. Verify Ollama connection: `curl http://127.0.0.1:11434/api/tags`

### Old services still running
1. Stop: `nssm stop VOFC-Chunker`
2. Disable: `nssm set VOFC-Chunker Start SERVICE_DISABLED`
3. Repeat for `VOFC-AutoProcessor`

---

## Migration Notes

- **Old System**: 3-phase chunking pipeline (`phase1_parser`, `phase2_engine`, `phase3_auditor`)
- **New System**: Unified pipeline (single model call, direct JSON extraction)
- **Format Change**: From `chunks_processed`/`phase1_parser_count` to `records`/`links`
- **Deduplication**: Now uses `dedupe_key` (SHA1 hash) instead of `panda_signature`

---

## Quick Start Commands

```powershell
# Start all required services
nssm start VOFC-Ollama
nssm start VOFC-Processor
nssm start VOFC-Flask
nssm start VOFC-Tunnel  # Optional

# Check status
nssm status VOFC-Processor
nssm status VOFC-Flask
nssm status VOFC-Ollama

# Restart after code changes
nssm restart VOFC-Processor
nssm restart VOFC-Flask
```

---

## Last Updated
2025-11-12

