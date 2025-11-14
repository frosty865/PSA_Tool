# Python Server-Side Code Relocation - Summary

## ✅ Completed Updates

All code references have been updated to support the new location: `C:\Tools\PSA-Flask`

### Files Updated

1. **tools/vofc_processor/vofc_processor.py**
   - Added `C:\Tools\PSA-Flask\.env` as primary .env path
   - Kept legacy paths as fallbacks

2. **tools/cleanup_orphaned_files.py**
   - Added `C:\Tools\PSA-Flask` to excluded project directories
   - Prevents cleanup scripts from deleting Flask server files

3. **tools/reset_data_folders.py**
   - Updated training data path to check new location first
   - Falls back to legacy path if new location doesn't exist

4. **tools/seed_retrain.py**
   - Updated training data paths to check `C:\Tools\PSA-Flask\training_data` first
   - Falls back to legacy path

5. **tools/seed_extractor.py**
   - Updated training data paths to check new location first
   - Falls back to legacy path

6. **sync-env.ps1**
   - Updated Flask path from `C:\Tools\VOFC-Flask` to `C:\Tools\PSA-Flask`

## 📋 Migration Steps

### Step 1: Run Migration Script
```powershell
cd C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool
.\scripts\migrate-python-to-tools.ps1
```

This will:
- Create `C:\Tools\PSA-Flask` directory structure
- Copy all Python files and directories
- Set up proper folder structure

### Step 2: Copy Environment File
```powershell
Copy-Item "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\.env" "C:\Tools\PSA-Flask\.env"
```

Or use the sync script:
```powershell
.\sync-env.ps1
```

### Step 3: Set Up Virtual Environment (if needed)
```powershell
cd C:\Tools\PSA-Flask
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 4: Update Windows Service (if using NSSM)
```powershell
# Stop service first
nssm stop PSA-Flask

# Update paths
nssm set PSA-Flask Application "C:\Tools\PSA-Flask\venv\Scripts\python.exe"
nssm set PSA-Flask AppDirectory "C:\Tools\PSA-Flask"
nssm set PSA-Flask AppParameters "-m waitress --listen=0.0.0.0:8080 app:app"

# Start service
nssm start PSA-Flask
```

### Step 5: Test Flask Server
```powershell
cd C:\Tools\PSA-Flask
.\start.ps1
```

Verify endpoints:
- `http://localhost:8080/` - Root endpoint
- `http://localhost:8080/api/system/health` - Health check

### Step 6: Update Next.js Environment (if needed)
If your Next.js app uses environment variables to point to Flask:
- Check `NEXT_PUBLIC_FLASK_URL` or `NEXT_PUBLIC_FLASK_API_URL`
- These should point to your Flask server (via tunnel or localhost)
- No changes needed if using tunnel URL

## 📁 Final Structure

```
C:\Tools\
├── PSA-Flask\              # Flask backend (NEW)
│   ├── app.py
│   ├── routes/
│   ├── services/
│   ├── config/
│   ├── tools/
│   ├── requirements.txt
│   ├── start.ps1
│   └── .env
│
├── Ollama\                 # Data directories (unchanged)
│   └── Data\
│       ├── incoming/
│       ├── processed/
│       ├── library/
│       └── logs/
│
└── [other tools...]
```

## 🔄 Backward Compatibility

All updated files maintain backward compatibility:
- They check the new location first (`C:\Tools\PSA-Flask`)
- Fall back to legacy paths if new location doesn't exist
- This allows gradual migration without breaking existing setups

## ⚠️ Important Notes

1. **Data Directories**: Data directories (`C:\Tools\Ollama\Data`) remain unchanged - they're shared between services

2. **Training Data**: Training data can be moved to `C:\Tools\PSA-Flask\training_data` or kept in the project directory - code handles both

3. **Environment Variables**: The `.env` file should be copied to the new location

4. **Windows Services**: If using NSSM, service configuration must be updated

5. **Next.js Project**: The Next.js frontend stays in the project directory - only Python code moves

## ✅ Verification Checklist

After migration:
- [ ] Flask server starts successfully from new location
- [ ] All API endpoints respond correctly
- [ ] Health check endpoint works
- [ ] Next.js frontend can connect to Flask backend
- [ ] Windows service (if used) points to new location
- [ ] Environment variables loaded correctly
- [ ] Logs are written to correct location
- [ ] Data directories accessible

## 🆘 Troubleshooting

### Flask server won't start
- Check Python path in virtual environment
- Verify `.env` file exists in `C:\Tools\PSA-Flask`
- Check port 8080 is not in use
- Review error messages in console

### Import errors
- Verify all Python files were copied
- Check `__init__.py` files exist in packages
- Ensure virtual environment is activated

### Environment variables not loading
- Verify `.env` file is in `C:\Tools\PSA-Flask`
- Check file permissions
- Review path references in code

### Service won't start
- Verify NSSM paths are correct
- Check service logs: `nssm status PSA-Flask`
- Ensure Python executable path is correct

