# PSA Tool - Planned Architecture

**Last Updated:** 2025-01-XX  
**Status:** Planned Architecture (As Designed)  
**Source of Truth:** `server.py` and `app.py`

---

## 1. ENTRY POINTS

### 1.1 Development Entry Point

**File:** `app.py`  
**Command:** `python app.py`  
**Purpose:** Direct Flask development server

```python
# app.py
from flask import Flask
from routes.processing import processing_bp
from routes.system import system_bp
# ... all blueprints ...

app = Flask(__name__)

# Register all blueprints
app.register_blueprint(processing_bp)
app.register_blueprint(system_bp)
# ... all blueprints ...

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

### 1.2 Production Entry Point

**File:** `server.py`  
**Command:** `-m waitress --listen=0.0.0.0:8080 server:app`  
**Purpose:** Production WSGI server (Waitress)

```python
# server.py
"""
Flask Server Entry Point for Production
Used by waitress/NSSM service: -m waitress --listen=0.0.0.0:8080 server:app

This file imports the Flask app from app.py to maintain separation
between development (app.py) and production (server.py) entry points.
"""

from app import app

# Export app for waitress
__all__ = ['app']
```

**Why:** Separation of concerns - development uses Flask's built-in server, production uses Waitress WSGI server.

---

## 2. SERVICE CONFIGURATION

### 2.1 Flask Service (vofc-flask)

**Service Name:** `vofc-flask` (lowercase)  
**Directory:** `C:\Tools\VOFC-Flask`  
**NSSM Configuration:**

```powershell
nssm set vofc-flask Application "C:\Tools\VOFC-Flask\venv\Scripts\python.exe"
nssm set vofc-flask AppDirectory "C:\Tools\VOFC-Flask"
nssm set vofc-flask AppParameters "-m waitress --listen=0.0.0.0:8080 server:app"
nssm set vofc-flask DisplayName "VOFC Flask API Server"
```

**CRITICAL:** Must use `server:app` (not `app:app`). This tells Waitress to:
1. Import `server.py` module
2. Use the `app` variable from that module
3. `server.py` imports `app` from `app.py`

### 2.2 Processor Service (VOFC-Processor)

**Service Name:** `VOFC-Processor`  
**Directory:** `C:\Tools\VOFC-Processor`  
**NSSM Configuration:**

```powershell
nssm set VOFC-Processor Application "C:\Tools\python\python.exe"
nssm set VOFC-Processor AppDirectory "C:\Tools\VOFC-Processor"
nssm set VOFC-Processor AppParameters "C:\Tools\VOFC-Processor\vofc_processor.py"
```

---

## 3. PROJECT STRUCTURE

### 3.1 Development (Git Repository)

```
PSA_Tool/
├── app.py                    # Flask app with all blueprints
├── server.py                 # Production entry point (imports from app.py)
├── routes/                   # Route blueprints
│   ├── processing.py
│   ├── system.py
│   ├── models.py
│   ├── learning.py
│   ├── analytics.py
│   ├── extract.py
│   ├── process.py
│   ├── library.py
│   ├── files.py
│   ├── audit_routes.py
│   └── disciplines.py
├── services/                 # Service modules
├── tools/                    # Utility scripts
│   └── vofc_processor/       # Processor service code
├── app/                      # Next.js frontend
├── requirements.txt
└── package.json
```

### 3.2 Production Deployment

```
C:\Tools\
├── VOFC-Flask\               # Flask backend (copied from project)
│   ├── app.py                # Flask app (all blueprints registered)
│   ├── server.py             # Production entry point
│   ├── routes/               # Route blueprints
│   ├── services/             # Service modules
│   ├── config/               # Configuration
│   ├── tools/                # Utility scripts
│   ├── venv/                 # Python virtual environment
│   ├── .env                  # Environment variables
│   └── requirements.txt
│
├── VOFC-Processor\           # Document processor
│   ├── vofc_processor.py
│   ├── services/
│   ├── extract/
│   ├── model/
│   ├── normalize/
│   └── storage/
│
└── Ollama\
    └── Data\
        ├── incoming/
        ├── processed/
        ├── library/
        ├── review/
        ├── errors/
        └── logs/
```

---

## 4. BLUEPRINT REGISTRATION

**All blueprints MUST be registered in `app.py`:**

```python
# app.py
from flask import Flask
from routes.processing import processing_bp
from routes.system import system_bp
from routes.models import models_bp
from routes.learning import learning_bp
from routes.analytics import bp as analytics_bp
from routes.extract import extract_bp
from routes.process import process_bp
from routes.library import library_bp
from routes.files import files_bp
from routes.audit_routes import audit_bp
from routes.disciplines import bp as disciplines_bp

app = Flask(__name__)

# Register all blueprints for production
app.register_blueprint(processing_bp)
app.register_blueprint(system_bp)
app.register_blueprint(models_bp)
app.register_blueprint(learning_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(extract_bp)
app.register_blueprint(process_bp)
app.register_blueprint(library_bp)
app.register_blueprint(files_bp)
app.register_blueprint(audit_bp)
app.register_blueprint(disciplines_bp)
```

**Why:** `server.py` imports `app` from `app.py`. If blueprints aren't registered in `app.py`, they won't be available in production.

---

## 5. SERVICE NAMES

### 5.1 Actual Service Names (As Installed)

| Service | Service Name | Directory |
|---------|-------------|-----------|
| Flask API | `vofc-flask` | `C:\Tools\VOFC-Flask` |
| Processor | `VOFC-Processor` | `C:\Tools\VOFC-Processor` |
| Tunnel | `VOFC-Tunnel` | `C:\Tools\cloudflared` |
| Ollama | `VOFC-Ollama` | `C:\Tools\Ollama` |

**CRITICAL:** Only ONE Flask service exists: `vofc-flask` (lowercase). Any `VOFC-Flask` or `PSA-Flask` services are duplicates and must be removed.

### 5.2 Service Detection

**Flask Service Check:**
- Only checks `vofc-flask` (lowercase)
- No alternatives or fallbacks
- Single service, single name

**Code:**
```python
# routes/system.py
def test_flask_service():
    service_names = ['vofc-flask']  # Only one service
    # ... check service ...
```

---

## 6. DEPLOYMENT WORKFLOW

### 6.1 Development

```powershell
# Activate virtual environment
cd C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run Flask development server
python app.py
```

### 6.2 Production Deployment

```powershell
# 1. Copy code to production directory
Copy-Item -Path "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\*" `
          -Destination "C:\Tools\VOFC-Flask\" `
          -Recurse -Exclude ".git","node_modules","app"

# 2. Create virtual environment
cd C:\Tools\VOFC-Flask
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Configure NSSM service
nssm set vofc-flask Application "C:\Tools\VOFC-Flask\venv\Scripts\python.exe"
nssm set vofc-flask AppDirectory "C:\Tools\VOFC-Flask"
nssm set vofc-flask AppParameters "-m waitress --listen=0.0.0.0:8080 server:app"

# 4. Start service
nssm start vofc-flask
```

---

## 7. KEY PRINCIPLES

### 7.1 Entry Point Separation

- **Development:** `app.py` runs Flask directly
- **Production:** `server.py` imports from `app.py`, used by Waitress
- **Why:** Allows different configurations for dev/prod

### 7.2 Blueprint Registration

- **All blueprints registered in `app.py`**
- **`server.py` only imports `app` from `app.py`**
- **No blueprints registered in `server.py`**

### 7.3 Service Naming

- **Flask service:** `vofc-flask` (lowercase, single service)
- **Processor service:** `VOFC-Processor` (mixed case)
- **No alternatives, no fallbacks, no duplicates**

### 7.4 Waitress Command

- **MUST use:** `-m waitress --listen=0.0.0.0:8080 server:app`
- **NEVER use:** `-m waitress --listen=0.0.0.0:8080 app:app`
- **Why:** Production uses `server.py`, not `app.py` directly

---

## 8. TROUBLESHOOTING

### 8.1 Service Won't Start

**Check NSSM configuration:**
```powershell
nssm get vofc-flask Application
nssm get vofc-flask AppDirectory
nssm get vofc-flask AppParameters
```

**Must be:**
- Application: `C:\Tools\VOFC-Flask\venv\Scripts\python.exe`
- AppDirectory: `C:\Tools\VOFC-Flask`
- AppParameters: `-m waitress --listen=0.0.0.0:8080 server:app`

### 8.2 Routes Return 404

**Check blueprint registration:**
```python
# app.py must have all blueprints registered
app.register_blueprint(processing_bp)
app.register_blueprint(system_bp)
# ... all blueprints ...
```

### 8.3 Import Errors

**Verify `server.py` exists:**
```powershell
Test-Path "C:\Tools\VOFC-Flask\server.py"
```

**Verify `server.py` imports correctly:**
```python
# server.py must have:
from app import app
__all__ = ['app']
```

---

## 9. MIGRATION CHECKLIST

When deploying or updating:

- [ ] All blueprints registered in `app.py`
- [ ] `server.py` exists and imports from `app.py`
- [ ] NSSM uses `server:app` (not `app:app`)
- [ ] Service name is `vofc-flask` (lowercase)
- [ ] No duplicate Flask services exist
- [ ] Virtual environment has all dependencies
- [ ] `.env` file exists in `C:\Tools\VOFC-Flask\`

---

**This document reflects the PLANNED architecture as designed. All code and documentation must align with this architecture.**

