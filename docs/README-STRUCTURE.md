# PSA Tool - Flat Structure

This document describes the flat structure for the PSA Tool project.

## Directory Structure

```
PSA-Tool/
│
├── app.py                    # Main Flask app (entry point)
├── routes/                   # All Flask route files
│   ├── __init__.py
│   ├── files.py
│   ├── library.py
│   ├── process.py
│   └── system.py
│
├── services/                 # Backend service modules
│   ├── __init__.py
│   ├── ollama_client.py
│   ├── supabase_client.py
│   └── processor.py
│
├── data/                     # Data directories
│   ├── incoming/            # Files to be processed
│   ├── processed/           # Successfully processed files
│   ├── errors/              # Files that failed processing
│   ├── VOFC_Library.xlsx    # Baseline library data
│   └── SAFE_VOFC_Library.pdf # Baseline library PDF
│
├── app/                      # Next.js frontend (App Router)
│   ├── api/                 # Next.js API routes (proxies to Flask)
│   ├── components/          # React components
│   ├── lib/                 # Utility libraries
│   └── ...
│
├── .env                     # Environment variables (not in git)
├── .env.example             # Example environment file
├── requirements.txt          # Python dependencies
├── start.ps1                # PowerShell startup script
└── package.json             # Node.js dependencies

```

## Important Notes

### Next.js Frontend Location

**Current Status**: The Next.js frontend is currently at the **root level** in the `app/` directory (Next.js App Router structure).

**Recommended Structure** (per your instructions): The frontend should be in `vofc-viewer/` directory. You have two options:

1. **Keep current structure** (recommended for Next.js App Router):
   - Keep `app/` at root level
   - This is the standard Next.js 13+ App Router structure

2. **Move to vofc-viewer/**:
   - Move `app/`, `components/`, `styles/`, etc. into `vofc-viewer/`
   - Update imports and paths accordingly

### Next Steps

1. **Copy routes from old server.py**: Import all route handlers from your old Flask server into the appropriate route files:
   - `routes/system.py` → `/`, `/api/system/health`, `/api/version`
   - `routes/files.py` → `/api/files/*`
   - `routes/process.py` → `/api/process/*`
   - `routes/library.py` → `/api/library/*`

2. **Implement service logic**: Move business logic from old server.py into:
   - `services/processor.py` → File processing, document parsing
   - `services/ollama_client.py` → All Ollama API calls
   - `services/supabase_client.py` → All Supabase operations

3. **Set up data files**: Place your library files in `data/`:
   - `VOFC_Library.xlsx`
   - `SAFE_VOFC_Library.pdf`

4. **Configure environment**: Copy `.env.example` to `.env` and fill in your credentials

5. **Create Next.js API proxies**: Update `app/api/*` routes to proxy to Flask backend at `http://localhost:8080`

## Running the Application

### Start Flask Backend:
```powershell
.\start.ps1
```

### Start Next.js Frontend:
```powershell
npm run dev
```

The Flask server will run on `http://localhost:8080` and Next.js on `http://localhost:3000`.

