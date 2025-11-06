# Model Route Setup - Complete

## ✅ Setup Complete

### Step 1: Folder Structure ✓
```
PSA_Tool/
├── app.py              ← main Flask entry point
├── routes/
│   ├── system.py
│   ├── model.py        ← NEW: Model blueprint
│   └── models.py        ← Existing (different purpose)
```

### Step 2: Created `routes/model.py` ✓

The file contains:
- `model_bp` blueprint
- `/api/run_model` route that calls Ollama directly
- Uses `vofc-engine:latest` model
- Limits text to 4000 characters
- Returns full Ollama API response

### Step 3: Registered Blueprint in `app.py` ✓

Added:
```python
from routes.model import model_bp
app.register_blueprint(model_bp)
```

### Step 4: Removed Duplicate Route ✓

Removed `/api/run_model` from `routes/system.py` to avoid conflicts.

## Route Details

**Endpoint**: `POST /api/run_model`

**Request**:
```json
{
  "text": "your text input here"
}
```

**Response** (200):
```json
{
  "model": "vofc-engine:latest",
  "created_at": "2025-01-XX...",
  "response": "<model's text response>",
  "done": true,
  ...
}
```

## Next Step: Restart Flask

**Run as Administrator:**
```powershell
nssm restart "VOFC-Flask"
```

**Wait 5-10 seconds**, then test:
```powershell
$body = @{text='Summarize the vulnerabilities from this paragraph.'} | ConvertTo-Json
Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/run_model' -Method POST -Body $body -ContentType 'application/json'
```

## Verification

After restart, verify the route is available:
```powershell
python scripts\check-all-routes.py
```

You should see:
```
[OK] POST   /api/run_model                       -> 200
```

## Files Modified

1. ✅ Created: `routes/model.py`
2. ✅ Updated: `app.py` (added import and registration)
3. ✅ Updated: `routes/system.py` (removed duplicate route)

All changes are complete and ready for Flask restart!

