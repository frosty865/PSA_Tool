# Python Server-Side Code Relocation Plan

## Target Structure

All Python server-side code will be relocated to:
```
C:\Tools\PSA-Flask\
├── app.py                    # Flask entry point
├── routes/                    # Route blueprints
│   ├── __init__.py
│   ├── analytics.py
│   ├── audit_routes.py
│   ├── disciplines.py
│   ├── extract.py
│   ├── files.py
│   ├── learning.py
│   ├── library.py
│   ├── model.py
│   ├── models.py
│   ├── process.py
│   ├── processing.py
│   └── system.py
├── services/                  # Service modules
│   ├── __init__.py
│   ├── approval_sync.py
│   ├── document_extractor.py
│   ├── folder_watcher.py
│   ├── heuristics.py
│   ├── learning_logger.py
│   ├── ollama_client.py
│   ├── postprocess.py
│   ├── preprocess.py
│   ├── processor.py
│   ├── queue_manager.py
│   ├── retraining_exporter.py
│   ├── submission_saver.py
│   ├── supabase_client.py
│   ├── processing/
│   ├── processor/
│   └── vofc_parser/
├── config/                    # Configuration files
│   └── vofc_config.yaml
├── tools/                     # Utility scripts
│   ├── check_database_duplicates.py
│   ├── cleanup_orphaned_files.py
│   ├── clear_submission_tables.py
│   ├── dedupe_vulnerabilities.py
│   ├── diagnose_extraction.py
│   ├── extract_production_patterns.py
│   ├── reset_data_folders.py
│   ├── seed_extractor.py
│   ├── seed_retrain.py
│   └── vofc_processor/
├── requirements.txt
├── start.ps1
├── .env                       # Environment variables (copy from project)
└── venv/                     # Virtual environment (optional)

```

## Files to Move

### Core Application
- `app.py` → `C:\Tools\PSA-Flask\app.py`
- `routes/` → `C:\Tools\PSA-Flask\routes\`
- `services/` → `C:\Tools\PSA-Flask\services\`
- `config/` → `C:\Tools\PSA-Flask\config\`
- `tools/` → `C:\Tools\PSA-Flask\tools\`
- `requirements.txt` → `C:\Tools\PSA-Flask\requirements.txt`
- `start.ps1` → `C:\Tools\PSA-Flask\start.ps1`
- `env.example` → `C:\Tools\PSA-Flask\env.example`

### Test Files (Optional)
- `test_sync_individual.py` → `C:\Tools\PSA-Flask\tests\`
- `test_sync_manual.py` → `C:\Tools\PSA-Flask\tests\`

## Files to Keep in Project (Next.js Only)

These stay in the project root:
- `app/` - Next.js frontend
- `components/` - React components
- `public/` - Static assets
- `package.json` - Node.js dependencies
- `next.config.mjs` - Next.js configuration
- `.vercelignore` - Vercel deployment config
- `tailwind.config.js` - Tailwind CSS config
- `tsconfig.json` - TypeScript config
- `docs/` - Documentation (can stay or move)
- `supabase/` - Supabase migrations
- `scripts/` - SQL scripts (can stay)

## Code Updates Required

### 1. Path References in Python Code
Update all hardcoded paths that reference the project directory:
- `C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool` → `C:\Tools\PSA-Flask`
- Relative paths may need adjustment

### 2. Environment Variable References
Update `.env` file location references:
- Old: `C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\.env`
- New: `C:\Tools\PSA-Flask\.env`

### 3. Data Directory References
Keep data directories separate (they're already at `C:\Tools\Ollama\Data`):
- `C:\Tools\Ollama\Data\incoming`
- `C:\Tools\Ollama\Data\processed`
- `C:\Tools\Ollama\Data\library`
- `C:\Tools\Ollama\Data\logs`

### 4. Next.js API Routes
No changes needed - they proxy to Flask via environment variables:
- `NEXT_PUBLIC_FLASK_URL` or `NEXT_PUBLIC_FLASK_API_URL`
- These should point to the Flask server URL (via tunnel or localhost)

## Migration Steps

1. **Create target directory structure**
2. **Copy all Python files**
3. **Update path references in Python code**
4. **Update environment variable loading**
5. **Update Windows service configuration (if using NSSM)**
6. **Test Flask server startup**
7. **Update documentation**

## Windows Service Configuration

If using NSSM to run Flask as a service:
```powershell
# Update service to point to new location
nssm set PSA-Flask Application "C:\Tools\PSA-Flask\venv\Scripts\python.exe"
nssm set PSA-Flask AppDirectory "C:\Tools\PSA-Flask"
nssm set PSA-Flask AppParameters "-m waitress --listen=0.0.0.0:8080 app:app"
nssm restart PSA-Flask
```

## Verification Checklist

- [ ] All Python files copied to `C:\Tools\PSA-Flask`
- [ ] Path references updated in Python code
- [ ] Environment variables updated
- [ ] Flask server starts successfully
- [ ] All API endpoints respond correctly
- [ ] Next.js frontend can connect to Flask backend
- [ ] Windows service (if used) points to new location
- [ ] Documentation updated

