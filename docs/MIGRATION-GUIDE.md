# PSA Tool Migration Guide

## ✅ What Has Been Created

### Flask Backend Structure
- ✅ `app.py` - Main Flask application entry point
- ✅ `routes/` - Route blueprints organized by functionality
  - `system.py` - System health and version endpoints
  - `files.py` - File management endpoints
  - `process.py` - Document processing endpoints
  - `library.py` - VOFC library search endpoints
- ✅ `services/` - Backend service modules
  - `ollama_client.py` - Ollama API interactions
  - `supabase_client.py` - Supabase database operations
  - `processor.py` - File and document processing logic

### Data Directories
- ✅ `data/incoming/` - Files to be processed
- ✅ `data/processed/` - Successfully processed files
- ✅ `data/errors/` - Files that failed processing

### Configuration Files
- ✅ `requirements.txt` - Python dependencies
- ✅ `env.example` - Environment variable template
- ✅ `start.ps1` - PowerShell startup script
- ✅ `README-STRUCTURE.md` - Structure documentation

### Next.js API Proxy Routes
- ✅ `app/api/system/health/route.js` - Proxy to Flask health endpoint
- ✅ `app/api/files/list/route.js` - Proxy to Flask file listing
- ✅ `app/api/process/start/route.js` - Proxy to Flask processing
- ✅ `app/api/library/search/route.js` - Proxy to Flask library search

### Notes
- All references to "VOFC Engine" have been renamed to "PSA Tool"
- The project maintains backward compatibility with existing VOFC Library files

## 📋 Next Steps - Import Your Old Code

### Step 1: Copy Routes from Old server.py

Find your old Flask `server.py` file and copy routes into the appropriate files:

**routes/system.py** - Add routes for:
- `/` (root endpoint)
- `/api/system/health` (already has basic implementation)
- `/api/version` (already has basic implementation)

**routes/files.py** - Add routes for:
- `/api/files/list` (already has basic implementation)
- `/api/files/info` (already has basic implementation)
- `/api/files/upload` (if you have this)
- Any other `/api/files/*` routes

**routes/process.py** - Add routes for:
- `/api/process/start` (already has basic implementation)
- `/api/process/document` (already has basic implementation)
- `/api/process/status` (if you have this)
- Any other `/api/process/*` routes

**routes/library.py** - Add routes for:
- `/api/library/search` (already has basic implementation)
- `/api/library/entry` (already has basic implementation)
- Any other `/api/library/*` routes

### Step 2: Move Business Logic to Services

From your old `server.py`, move functions to:

**services/processor.py**:
- File reading/writing functions
- Document parsing (PDF, DOCX, etc.)
- Library file operations
- Any file system operations

**services/ollama_client.py**:
- All Ollama API calls
- Text generation functions
- Chat functions
- Model management

**services/supabase_client.py**:
- All Supabase database operations
- Data insertion/updates/queries
- Authentication helpers

### Step 3: Update Environment Variables

1. Copy `env.example` to `.env`
2. Fill in your actual values:
   ```env
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
   OLLAMA_URL=http://localhost:11434
   NEXT_PUBLIC_FLASK_URL=http://localhost:8080
   ```

### Step 4: Install Dependencies

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install Python dependencies
pip install -r requirements.txt
```

### Step 5: Add Library Files

Place your library files in the `data/` directory:
- `data/VOFC_Library.xlsx`
- `data/SAFE_VOFC_Library.pdf`

### Step 6: Test the Flask Server

```powershell
.\start.ps1
```

The server should start on `http://localhost:8080`. Test endpoints:
- `http://localhost:8080/` - Should return service info
- `http://localhost:8080/api/system/health` - Should return health status

### Step 7: Update Next.js API Routes

Your existing Next.js API routes in `app/api/` that interact with Flask should be updated to use the proxy routes or call Flask directly using the `NEXT_PUBLIC_FLASK_URL` environment variable.

## 🔄 Example: Converting a Route

### Old Route (in server.py):
```python
@app.route('/api/files/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    # ... processing logic ...
    return jsonify({"success": True})
```

### New Route (in routes/files.py):
```python
from flask import request, jsonify
from services.processor import save_incoming_file

@files_bp.route('/api/files/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    # Move business logic to service
    result = save_incoming_file(file)
    return jsonify(result)
```

### New Service Function (in services/processor.py):
```python
def save_incoming_file(file):
    """Save uploaded file to incoming directory"""
    try:
        file_path = INCOMING_DIR / file.filename
        file.save(str(file_path))
        return {"success": True, "filename": file.filename}
    except Exception as e:
        raise Exception(f"Failed to save file: {str(e)}")
```

## 📝 Notes

- The Flask server runs on port **8080** (not 5000) to avoid conflicts
- All routes are organized by functionality in separate files
- Business logic is separated from route handlers
- Next.js frontend proxies Flask requests through `/app/api/*` routes
- CORS is enabled for Next.js frontend communication

## 🐛 Troubleshooting

**Import errors**: Make sure you've installed all dependencies from `requirements.txt`

**Port conflicts**: Change `FLASK_PORT` in `.env` if 8080 is taken

**Supabase connection**: Verify your credentials in `.env`

**Ollama connection**: Ensure Ollama is running on the configured URL

