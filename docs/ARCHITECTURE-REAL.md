# PSA Tool - Real Architecture Documentation

**Last Updated:** 2025-01-XX  
**Status:** Production Architecture (As Deployed)

## Overview

PSA Tool is a Next.js frontend with a Flask backend, deployed on Windows using NSSM services.

---

## 1. DEPLOYMENT ARCHITECTURE

### 1.1 Project Structure (Development)

```
PSA_Tool/                          # Git repository
├── app/                           # Next.js frontend
│   ├── admin/                     # Admin pages
│   ├── api/                       # Next.js API routes (proxies to Flask)
│   ├── components/                # React components
│   ├── dashboard/                 # Dashboard pages
│   ├── lib/                       # Frontend utilities
│   └── [pages]/                   # User-facing pages
├── routes/                        # Flask route blueprints
├── services/                      # Flask service modules
├── tools/                         # Utility scripts
│   └── vofc_processor/            # Processor service code
├── app.py                         # Flask app entry point
├── server.py                      # Production entry point (for waitress)
├── requirements.txt               # Python dependencies
└── package.json                   # Node.js dependencies
```

### 1.2 Production Deployment Structure

```
C:\Tools\
├── VOFC-Flask\                    # Flask backend (deployed from project)
│   ├── app.py                     # Flask application
│   ├── server.py                  # Waitress entry point
│   ├── routes/                    # Route blueprints
│   ├── services/                  # Service modules
│   ├── config/                    # Configuration
│   ├── tools/                     # Utility scripts
│   ├── venv/                      # Python virtual environment
│   ├── .env                       # Environment variables
│   └── requirements.txt
│
├── VOFC-Processor\                # Document processor service
│   ├── vofc_processor.py          # Main processor script
│   ├── services/                  # Processor services
│   ├── extract/                   # Extraction modules
│   ├── model/                     # Model client
│   ├── normalize/                 # Normalization modules
│   └── storage/                   # Storage modules
│
├── Ollama\                        # Ollama installation
│   ├── Data\                      # Data directories
│   │   ├── incoming/              # Files to process
│   │   ├── processed/             # Processed JSON files
│   │   ├── library/               # Archived complete files
│   │   ├── review/                # Files pending review
│   │   ├── errors/                # Failed processing
│   │   └── logs/                  # Log files
│   └── [Ollama binaries]
│
└── nssm\                          # NSSM service manager
    └── logs/                      # Service logs
```

---

## 2. WINDOWS SERVICES (NSSM)

### 2.1 Service Names (ACTUAL - As Installed)

| Service | Service Name | Directory | Port | Status |
|---------|-------------|-----------|------|--------|
| Flask API | `vofc-flask` | `C:\Tools\VOFC-Flask` | 8080 | ✅ Active |
| Processor | `VOFC-Processor` | `C:\Tools\VOFC-Processor` | N/A | ✅ Active |
| Tunnel | `VOFC-Tunnel` | `C:\Tools\cloudflared` | N/A | ⚠️ Check |
| Ollama | `VOFC-Ollama` | `C:\Tools\Ollama` | 11434 | ✅ Active |

**CRITICAL:** Only ONE Flask service exists: `vofc-flask` (lowercase). Any `VOFC-Flask` or `PSA-Flask` services are duplicates and must be removed.

### 2.2 Service Configuration

**Flask Service (`vofc-flask`):**
- **Application:** `C:\Tools\VOFC-Flask\venv\Scripts\python.exe`
- **AppDirectory:** `C:\Tools\VOFC-Flask`
- **AppParameters:** `-m waitress --listen=0.0.0.0:8080 server:app`
- **Display Name:** "VOFC Flask API Server"
- **Entry Point:** `server.py` (imports `app` from `app.py`)

**Processor Service (`VOFC-Processor`):**
- **Application:** `C:\Tools\python\python.exe`
- **AppDirectory:** `C:\Tools\VOFC-Processor`
- **AppParameters:** `C:\Tools\VOFC-Processor\vofc_processor.py`
- **Display Name:** "VOFC Processor Service"

---

## 3. NETWORK ARCHITECTURE

### 3.1 Production Flow

```
Internet
    ↓
Vercel (Next.js Frontend)
    ↓ HTTPS
Cloudflare Tunnel (VOFC-Tunnel)
    ↓ HTTP
Flask Backend (vofc-flask :8080)
    ↓
├── Supabase (Database)
├── Ollama (AI Model :11434)
└── File System (C:\Tools\Ollama\Data)
```

### 3.2 Environment Variables

**Vercel (Production Frontend):**
- `NEXT_PUBLIC_FLASK_URL` or `NEXT_PUBLIC_FLASK_API_URL` → `https://flask.frostech.site`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

**Flask Backend (`C:\Tools\VOFC-Flask\.env`):**
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY` or `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OLLAMA_URL` → `http://localhost:11434`
- `VOFC_BASE_DIR` → `C:\Tools\Ollama\Data`
- `VOFC_DATA_DIR` → `C:\Tools\Ollama\Data`

**Processor Service (`C:\Tools\VOFC-Processor\.env` or `C:\Tools\.env`):**
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY` or `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `OLLAMA_URL` → `http://localhost:11434`
- `VOFC_BASE_DIR` → `C:\Tools\Ollama\Data`
- `MIN_RECORDS_FOR_LIBRARY` → `5` (default)

---

## 4. FLASK ROUTES (Backend)

### 4.1 Route Blueprints (Registered in `app.py`)

| Blueprint | File | Routes |
|-----------|------|--------|
| `processing_bp` | `routes/processing.py` | `/api/processing/*` |
| `system_bp` | `routes/system.py` | `/api/system/*` |
| `models_bp` | `routes/models.py` | `/api/models/*`, `/api/system/events` |
| `learning_bp` | `routes/learning.py` | `/api/learning/*` |
| `analytics_bp` | `routes/analytics.py` | `/api/analytics/*` |
| `extract_bp` | `routes/extract.py` | `/api/documents/extract/*` |
| `process_bp` | `routes/process.py` | `/api/process/*` |
| `library_bp` | `routes/library.py` | `/api/library/*` |
| `files_bp` | `routes/files.py` | `/api/files/*` |
| `audit_bp` | `routes/audit_routes.py` | `/api/audit/*` |
| `disciplines_bp` | `routes/disciplines.py` | `/api/disciplines/*` |

### 4.2 Key Flask Endpoints

**System:**
- `GET /api/system/health` - Health check (Flask, Ollama, Supabase, Tunnel)
- `GET /api/system/progress` - Processing progress and folder counts
- `GET /api/system/logs?tail=50` - Recent log lines
- `GET /api/system/control` - System control (process pending, etc.)

**Processing:**
- `POST /api/process/start` - Start document processing
- `GET /api/processing/status` - Processing status

**Learning:**
- `GET /api/learning/stats` - Learning statistics
- `GET /api/learning/heuristics` - Learning heuristics

**Analytics:**
- `GET /api/analytics/summary` - Analytics summary

**Models:**
- `GET /api/models/info` - Model information
- `GET /api/system/events` - System events

---

## 5. NEXT.JS ROUTES (Frontend)

### 5.1 Pages (26 total)

**Public:**
- `/splash` - Login/Landing page
- `/login` - Login page (alternative)

**User Pages:**
- `/` - Main dashboard (vulnerability search)
- `/submit` - Submit new vulnerability
- `/submit-psa` - Submit documents for processing
- `/submit/bulk` - Bulk submission
- `/profile` - User profile
- `/assessment` - Generate vulnerability assessment
- `/review` - Review submissions
- `/dashboard` - Processing dashboard
- `/dashboard/analytics` - Analytics dashboard
- `/dashboard/learning` - Learning dashboard
- `/learning` - Learning monitor

**Admin Pages:**
- `/admin` - Admin overview
- `/admin/review` - Review submissions
- `/admin/users` - User management
- `/admin/models` - Model analytics
- `/admin/ofc-requests` - OFC requests management
- `/admin/ofcs` - OFCs management
- `/admin/softmatches` - Soft matches
- `/admin/analytics` - Analytics
- `/admin/audit` - Audit logs
- `/admin/learning` - Learning monitor
- `/admin/processing` - Processing monitor
- `/admin/test` - Test page
- `/admin/test-auth` - Authentication test

### 5.2 Next.js API Routes (66 total)

**Authentication (`/api/auth/*`):**
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/register`
- `GET /api/auth/validate`
- `GET /api/auth/verify`
- `GET /api/auth/permissions`

**System (`/api/system/*`):**
- `GET /api/system/health` - Proxy to Flask
- `GET /api/system/progress` - Proxy to Flask
- `GET /api/system/logs` - Proxy to Flask
- `GET /api/system/control` - System control
- `GET /api/system/events` - Proxy to Flask
- `GET /api/system/logstream` - Log streaming
- `GET /api/system/tunnel/logs` - Tunnel logs

**Submissions (`/api/submissions/*`):**
- `GET /api/submissions`
- `POST /api/submissions`
- `GET /api/submissions/[id]`
- `POST /api/submissions/[id]/approve`
- `POST /api/submissions/[id]/reject`
- `POST /api/submissions/[id]/edit`
- `DELETE /api/submissions/[id]`
- `POST /api/submissions/bulk`
- `POST /api/submissions/structured`
- `POST /api/submissions/ofc-request`
- `POST /api/submissions/[id]/approve-vulnerability`
- `POST /api/submissions/[id]/ofcs/[ofcId]`
- `POST /api/submissions/[id]/vulnerabilities/[vulnId]`
- `POST /api/submissions/cleanup-rejected`

**Admin (`/api/admin/*`):**
- `GET /api/admin/stats`
- `GET /api/admin/users`
- `GET /api/admin/submissions`
- `GET /api/admin/vulnerabilities`
- `GET /api/admin/ofcs`
- `GET /api/admin/ofc-requests`
- `POST /api/admin/ofc-requests/[id]/approve`
- `POST /api/admin/ofc-requests/[id]/reject`
- `POST /api/admin/ofc-requests/[id]/implement`
- `POST /api/admin/submissions/[id]/update-data`
- `POST /api/admin/generate-ofcs`
- `POST /api/admin/check-duplicates`
- `POST /api/admin/check-users-profiles`
- `POST /api/admin/cleanup-tables`
- `POST /api/admin/disable-rls`
- `GET /api/admin/audit`

**Dashboard (`/api/dashboard/*`):**
- `GET /api/dashboard/overview`
- `GET /api/dashboard/system` - Proxy to Flask
- `GET /api/dashboard/status` - Combined health + progress
- `GET /api/dashboard/stream` - Stream URL

**Analytics (`/api/analytics/*`):**
- `GET /api/analytics/summary` - Proxy to Flask

**Learning (`/api/learning/*`):**
- `GET /api/learning/stats` - Proxy to Flask
- `GET /api/learning/heuristics` - Proxy to Flask
- `GET /api/learning/retrain-events` - Proxy to Flask

**Documents (`/api/documents/*`):**
- `POST /api/documents/submit`
- `POST /api/documents/parse-metadata`
- `POST /api/documents/process-one`
- `POST /api/documents/process-pending`

**Files (`/api/files/*`):**
- `GET /api/files/list` - Proxy to Flask

**Process (`/api/process/*`):**
- `POST /api/process/start` - Proxy to Flask

**Library (`/api/library/*`):**
- `GET /api/library/search` - Proxy to Flask

**Disciplines (`/api/disciplines/*`):**
- `GET /api/disciplines`
- `GET /api/disciplines/[id]`

**Sectors (`/api/sectors/*`):**
- `GET /api/sectors`

**Subsectors (`/api/subsectors/*`):**
- `GET /api/subsectors`

**Sources (`/api/sources/*`):**
- `POST /api/sources/assign-citation`

**Models (`/api/models/*`):**
- `GET /api/models/info` - Proxy to Flask

**Proxy (`/api/proxy/*`):**
- `GET /api/proxy/flask/progress` - Proxy to Flask
- `POST /api/proxy/flask/process-pending` - Proxy to Flask

**Monitor (`/api/monitor/*`):**
- `GET /api/monitor/processing`
- `GET /api/monitor/system`

**Health:**
- `GET /api/health`

---

## 6. DATA FLOW

### 6.1 Document Processing Flow

```
1. User uploads PDF → /submit-psa
   ↓
2. File saved to C:\Tools\Ollama\Data\incoming\
   ↓
3. VOFC-Processor service detects file (every 30s)
   ↓
4. Processor extracts text → chunks → Ollama model
   ↓
5. Records extracted → Supabase upload
   ↓
6. JSON saved to C:\Tools\Ollama\Data\processed\
   ↓
7. If records >= MIN_RECORDS_FOR_LIBRARY (5):
   → Move to C:\Tools\Ollama\Data\library\
   Else:
   → Keep in incoming/ for reprocessing (learning mode)
```

### 6.2 Submission Review Flow

```
1. User submits vulnerability → /submit
   ↓
2. Saved to Supabase (submissions table)
   ↓
3. Admin reviews → /admin/review
   ↓
4. Approve/Reject → Updates Supabase
   ↓
5. Approved → vulnerabilities table
```

---

## 7. KEY FILES

### 7.1 Flask Backend

- `app.py` - Flask app with all blueprints registered
- `server.py` - Production entry point (imports from app.py)
- `routes/system.py` - System health, progress, logs
- `routes/processing.py` - Processing routes
- `services/supabase_client.py` - Supabase client
- `services/ollama_client.py` - Ollama client

### 7.2 Processor Service

- `tools/vofc_processor/vofc_processor.py` - Main processor script
- `services/processor/processor/run_processor.py` - Processing orchestration
- `services/processor/model/vofc_client.py` - Ollama model client
- `services/processor/normalization/supabase_upload.py` - Supabase upload

### 7.3 Frontend

- `app/lib/server-utils.js` - Flask URL detection, safe fetch
- `app/lib/supabase-client.js` - Supabase client
- `app/components/components/VOFCProcessingDashboard.jsx` - Processing dashboard
- `app/components/components/SubmissionReview.jsx` - Submission review

---

## 8. DEPLOYMENT NOTES

### 8.1 Flask Service

- **Entry Point:** `server.py` (not `app.py`)
- **Command:** `-m waitress --listen=0.0.0.0:8080 server:app`
- **Why:** `server.py` imports `app` from `app.py`, allowing separation of dev/prod

### 8.2 Processor Service

- **Entry Point:** `vofc_processor.py`
- **Location:** `C:\Tools\VOFC-Processor\`
- **Data Source:** `C:\Tools\Ollama\Data\incoming\`
- **Processing:** Continuous (every 30 seconds)

### 8.3 Frontend (Vercel)

- **Build:** `npm run build`
- **Deploy:** Automatic on git push
- **Environment:** Vercel dashboard
- **Flask URL:** `https://flask.frostech.site` (via Cloudflare tunnel)

---

## 9. TROUBLESHOOTING

### 9.1 Flask Service Not Running

```powershell
# Check service status
sc query vofc-flask

# Check logs
Get-Content C:\Tools\nssm\logs\vofc_flask_err.log -Tail 50

# Restart service
nssm restart vofc-flask
```

### 9.2 Processor Not Processing Files

```powershell
# Check service status
sc query VOFC-Processor

# Check logs
Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_*.log -Tail 50

# Verify files in incoming
Get-ChildItem C:\Tools\Ollama\Data\incoming\*.pdf
```

### 9.3 Frontend Can't Reach Flask

1. Check tunnel service: `sc query VOFC-Tunnel`
2. Test tunnel URL: `curl https://flask.frostech.site/api/system/health`
3. Check Vercel env vars: `NEXT_PUBLIC_FLASK_URL`
4. Check Flask is listening: `netstat -ano | findstr :8080`

---

## 10. MIGRATION NOTES

**DO NOT USE:**
- ❌ `PSA-Flask` (doesn't exist)
- ❌ `PSA-Processor` (doesn't exist)
- ❌ `PSA-Data` (doesn't exist)

**USE:**
- ✅ `vofc-flask` (service name, lowercase)
- ✅ `VOFC-Flask` (directory name)
- ✅ `VOFC-Processor` (service and directory)
- ✅ `C:\Tools\Ollama\Data` (data directory)

---

**This document reflects the ACTUAL production architecture as deployed.**

