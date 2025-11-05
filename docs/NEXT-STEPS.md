# Cursor Execution Context
> Cursor: follow this deployment plan to finalize the PSA Tool migration.
> Do **not** rebuild or rename existing services (Flask, Ollama, Tunnel).
> These are managed via NSSM and already running externally.
> Your task is to verify that the PSA Tool code is correctly deployed,
> update the service directory path, and confirm all routes respond.


# PSA Tool - Next Steps

## 🎯 Current Status

✅ **Code Migration Complete**
- All Flask routes migrated to modular structure
- Services integrated (Flask, Ollama, Tunnel, Supabase)
- Environment variables configured
- Documentation complete

⚠️ **Service Deployment Pending**
- NSSM service still points to old location: `C:\Tools\VOFC-Flask`
- New code is in: `C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool`
- Service needs to be updated to use new code

## 📋 Required Actions

### Option 1: Deploy New Code to C:\Tools\VOFC-Flask (Recommended)

Since tools should remain in `C:\Tools`, copy the new code structure there:

```powershell
# 1. Backup current C:\Tools\VOFC-Flask (if needed)
Copy-Item "C:\Tools\VOFC-Flask" "C:\Tools\VOFC-Flask.backup" -Recurse -Force

# 2. Copy new code structure to C:\Tools\VOFC-Flask
$source = "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool"
$dest = "C:\Tools\VOFC-Flask"

# Copy essential files
Copy-Item "$source\app.py" "$dest\" -Force
Copy-Item "$source\routes" "$dest\" -Recurse -Force
Copy-Item "$source\services" "$dest\" -Recurse -Force
Copy-Item "$source\data" "$dest\" -Recurse -Force
Copy-Item "$source\requirements.txt" "$dest\" -Force
Copy-Item "$source\start.ps1" "$dest\" -Force

# 3. Copy .env file (if exists) or create from env.example
if (Test-Path "$source\.env") {
    Copy-Item "$source\.env" "$dest\" -Force
} else {
    Copy-Item "$source\env.example" "$dest\.env"
    Write-Host "⚠️  Please edit C:\Tools\VOFC-Flask\.env with your credentials"
}

# 4. Update NSSM service parameters (if needed)
# The service should use: python app.py
# Or if using Waitress: python -m waitress --listen=0.0.0.0:8080 app:app
```

### Option 2: Update NSSM Service to Point to New Location

If you want to keep code in the PSA_Tool directory:

```powershell
# Run as Administrator
$newPath = "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool"

nssm set VOFC-Flask AppDirectory "$newPath"
nssm set VOFC-Flask AppParameters "app.py"
# Or if using Waitress:
# nssm set VOFC-Flask AppParameters "-m waitress --listen=0.0.0.0:8080 app:app"
nssm restart VOFC-Flask
```

### Step 2: Configure Environment Variables

Ensure `.env` file in the service directory has:

```env
# Flask Configuration
FLASK_ENV=production
FLASK_PORT=8080

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-key

# Ollama Configuration
OLLAMA_HOST=http://127.0.0.1:11434

# Tunnel Configuration
TUNNEL_URL=https://flask.frostech.site

# Next.js Frontend
NEXT_PUBLIC_FLASK_URL=http://localhost:8080
```

### Step 3: Install Python Dependencies

```powershell
cd C:\Tools\VOFC-Flask  # or your service directory

# Create/activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Restart NSSM Service

```powershell
# Run as Administrator
nssm restart VOFC-Flask
```

### Step 5: Verify Integration

Test all endpoints:

```powershell
# Root endpoint
Invoke-WebRequest -Uri "http://localhost:8080/" | Select-Object -ExpandProperty Content

# Health endpoint (should show all services)
Invoke-WebRequest -Uri "http://localhost:8080/api/system/health" | Select-Object -ExpandProperty Content

# File listing
Invoke-WebRequest -Uri "http://localhost:8080/api/files/list" | Select-Object -ExpandProperty Content

# Library search
Invoke-WebRequest -Uri "http://localhost:8080/api/library/search?q=test" | Select-Object -ExpandProperty Content
```

Expected health response:
```json
{
  "flask": "ok",
  "ollama": "ok",
  "supabase": "ok",
  "tunnel": "managed",
  "service": "PSA Processing Server",
  "urls": {
    "flask": "http://127.0.0.1:8080",
    "ollama": "http://127.0.0.1:11434",
    "tunnel": "https://flask.frostech.site"
  },
  "timestamp": "..."
}
```

### Step 6: Add Library Files

Place these files in the `data/` directory:
- `VOFC_Library.xlsx`
- `SAFE_VOFC_Library.pdf`

### Step 7: Update Next.js Frontend (if needed)

Ensure frontend environment variables point to correct Flask URL:
- Development: `http://localhost:8080`
- Production: `https://flask.frostech.site`

## 🔍 Verification Checklist

- [ ] Code deployed to service location
- [ ] Environment variables configured
- [ ] Python dependencies installed
- [ ] NSSM service restarted
- [ ] Health endpoint shows all services "ok"
- [ ] Root endpoint returns "PSA Processing Server"
- [ ] File routes working
- [ ] Library routes working
- [ ] Tunnel accessible (if testing externally)
- [ ] Library files added to data/

## 📝 Additional Considerations

### Service Naming
Consider renaming NSSM service from `VOFC-Flask` to `PSA-Flask`:
```powershell
# Run as Administrator
nssm stop VOFC-Flask
nssm edit VOFC-Flask  # Change display name to "PSA-Flask"
# Or create new service
nssm install PSA-Flask "C:\Tools\python\python.exe"
nssm set PSA-Flask AppDirectory "C:\Tools\VOFC-Flask"
nssm set PSA-Flask AppParameters "app.py"
nssm start PSA-Flask
```

### Production Deployment
- Ensure all services (Flask, Ollama, Tunnel) are running as NSSM services
- Verify tunnel is accessible: `https://flask.frostech.site/api/system/health`
- Test frontend can communicate with Flask backend
- Monitor logs for any errors

## 🚨 Troubleshooting

**Service won't start:**
- Check NSSM service logs
- Verify Python path is correct
- Check .env file exists and is valid
- Ensure dependencies are installed

**Health endpoint shows services offline:**
- Verify Ollama service is running: `nssm status VOFC-Ollama`
- Check Supabase credentials in .env
- Verify OLLAMA_HOST is correct

**Routes return 404:**
- Verify blueprints are registered in app.py
- Check service is using new code (not old server.py)
- Restart service after code changes

---

**Priority**: Deploy new code to C:\Tools\VOFC-Flask and restart service to complete migration.

