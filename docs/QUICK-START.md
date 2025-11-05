# PSA Tool - Quick Start Guide

## 🚀 Getting Started

### 1. Setup Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```powershell
# Copy example file
Copy-Item env.example .env

# Edit .env with your credentials:
# - NEXT_PUBLIC_SUPABASE_URL
# - SUPABASE_SERVICE_ROLE_KEY
# - NEXT_PUBLIC_SUPABASE_ANON_KEY
# - OLLAMA_URL (default: http://localhost:11434)
```

### 3. Add Library Files

Place these files in the `data/` directory:
- `VOFC_Library.xlsx`
- `SAFE_VOFC_Library.pdf`

### 4. Start Flask Server

```powershell
.\start.ps1
```

Or manually:
```powershell
python app.py
```

The server will start on `http://localhost:8080`

### 5. Test Endpoints

Open your browser or use PowerShell:

```powershell
# Test root endpoint
Invoke-WebRequest -Uri "http://localhost:8080/" | Select-Object -ExpandProperty Content

# Test health endpoint
Invoke-WebRequest -Uri "http://localhost:8080/api/system/health" | Select-Object -ExpandProperty Content
```

Expected responses:
- `/` → `{"service": "PSA Processing Server", "status": "running", "version": "1.0.0"}`
- `/api/system/health` → `{"flask": "ok", "ollama": "ok|offline", "supabase": "ok|error", "timestamp": "..."}`

### 6. Start Next.js Frontend (Optional)

In a separate terminal:

```powershell
npm install
npm run dev
```

Frontend will start on `http://localhost:3000`

## 📁 Project Structure

```
PSA-Tool/
├── app.py                    # Flask entry point
├── routes/                   # Route blueprints
│   ├── system.py            # Health, version
│   ├── files.py             # File management
│   ├── process.py           # Document processing
│   └── library.py           # Library search
├── services/                 # Business logic
│   ├── ollama_client.py     # Ollama integration
│   ├── supabase_client.py   # Supabase integration
│   └── processor.py         # File processing
└── data/                     # Data files
    ├── incoming/            # Files to process
    ├── processed/           # Processed files
    └── errors/              # Failed files
```

## 🔧 Troubleshooting

### Port Already in Use
Change `FLASK_PORT` in `.env` or modify `app.py`:
```python
app.run(host="0.0.0.0", port=8081, debug=True)
```

### Missing Dependencies
```powershell
pip install -r requirements.txt
```

### Supabase Connection Issues
Verify your credentials in `.env`:
- `NEXT_PUBLIC_SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

### Ollama Not Responding
Ensure Ollama is running:
```powershell
# Check if Ollama is running
Invoke-WebRequest -Uri "http://localhost:11434/api/tags"
```

## 📝 Next Steps

1. **Migrate Routes**: If you have an old `server.py`, copy routes into `routes/`
2. **Implement Logic**: Add business logic to `services/` modules
3. **Test Endpoints**: Verify all routes work correctly
4. **Deploy**: Configure for production deployment

For detailed migration instructions, see `MIGRATION-GUIDE.md`

