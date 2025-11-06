# Backend Connectivity Troubleshooting Guide

This guide helps diagnose and fix issues with Flask backend connectivity, especially when the Admin Panel shows "unknown" or "offline" status for models and system events.

## Quick Diagnostic Script

Run the automated diagnostic script first:

```powershell
.\scripts\test-backend-endpoints.ps1
```

This script will test all endpoints and provide specific guidance for any issues found.

## Manual Troubleshooting Steps

### 🧩 Step 1: Confirm Flask Backend is Reachable

From PowerShell on the same server, run:

```powershell
curl http://localhost:8080/api/system/health
```

**Expected Response:**
```json
{
  "flask": "ok",
  "ollama": "ok",
  "supabase": "ok",
  "tunnel": "ok"
}
```

**If you get "connection refused" or "not found":**

Your Flask backend isn't responding on port 8080.

**→ Restart it:**
```powershell
nssm restart "VOFC-Flask"
```

**Additional checks:**
```powershell
# Check service status
Get-Service "VOFC-Flask"

# Check Flask logs
Get-Content "C:\Tools\nssm\logs\vofc_flask.log" -Tail 50
```

---

### 🧩 Step 2: Check Next.js Environment Variables

In your web `.env` (on Vercel or local build), confirm:

**For Development (localhost):**
```env
NEXT_PUBLIC_FLASK_URL=http://localhost:8080
NEXT_PUBLIC_FLASK_API_URL=http://localhost:8080/api
```

**For Production (tunnel):**
```env
NEXT_PUBLIC_FLASK_URL=https://flask.frostech.site
NEXT_PUBLIC_FLASK_API_URL=https://flask.frostech.site/api
```

**Then redeploy or restart the Next.js server:**
```powershell
# If running locally
npm run dev

# If on Vercel, push changes to trigger redeploy
```

**Note:** The `getFlaskUrl()` function in `app/lib/server-utils.js` automatically detects production vs development, but explicit environment variables take priority.

---

### 🧩 Step 3: Test Backend Endpoints Directly

Test each endpoint through the tunnel:

**Flask health:**
```powershell
curl https://flask.frostech.site/api/system/health
```

**Learning stats:**
```powershell
curl https://flask.frostech.site/api/learning/stats
```

**System events:**
```powershell
curl https://flask.frostech.site/api/system/events
```

**Model info:**
```powershell
curl https://flask.frostech.site/api/models/info
```

**If any return 502 Bad Gateway:**
- Tunnel may be down
- Flask may not be running
- Check tunnel service: `nssm status "VOFC-Tunnel"`

**If any return 404:**
- Route may not be registered in Flask
- Check route exists in `routes/*.py` files
- Verify blueprint is registered in `app.py`

---

### 🧩 Step 4: Verify Routes are Registered in Flask

Make sure `app.py` includes:

```python
from routes.system import system_bp
from routes.models import models_bp
from routes.learning import learning_bp

app.register_blueprint(system_bp)
app.register_blueprint(models_bp)
app.register_blueprint(learning_bp)
```

**Current route registrations (verify these exist):**

| Blueprint | Routes | File |
|-----------|--------|------|
| `system_bp` | `/api/system/health`, `/api/system/events` | `routes/system.py` |
| `models_bp` | `/api/models/info`, `/api/system/events` | `routes/models.py` |
| `learning_bp` | `/api/learning/stats` | `routes/learning.py` |

**If `models_bp` isn't registered:**
- `/api/models/info` will return 404
- `/api/system/events` will return 404
- Frontend will show "unknown" and "offline"

**To fix:**
1. Open `app.py`
2. Verify `from routes.models import models_bp` exists
3. Verify `app.register_blueprint(models_bp)` exists
4. Restart Flask: `nssm restart "VOFC-Flask"`

---

### 🧩 Step 5: Check Admin Panel Console Errors

Open browser dev tools → Network tab → refresh `/admin/models`.

**Look for:**
- `GET /api/models/info → 404`
- `GET /api/system/events → 502`
- `GET /api/system/health → 503`

**This confirms exactly which backend endpoint is failing.**

**Common errors:**

| Error | Meaning | Fix |
|-------|---------|-----|
| `404 Not Found` | Route not registered or wrong path | Check `app.py` blueprint registration |
| `502 Bad Gateway` | Tunnel can't reach Flask | Check Flask is running, restart tunnel |
| `503 Service Unavailable` | Flask is down | Restart Flask service |
| `ECONNREFUSED` | Can't connect to server | Check firewall, verify URL |
| `ENOTFOUND` | DNS lookup failed | Check tunnel URL configuration |

---

## 🧠 Expected Healthy Response Pattern

| Endpoint | Expected Response | Purpose |
|----------|------------------|---------|
| `/api/models/info` | `{ "name": "vofc-engine:latest", "size_gb": 4.4, "version": "latest" }` | Model info |
| `/api/system/health` | `{ "flask":"ok","ollama":"ok","supabase":"ok","tunnel":"ok" }` | Status check |
| `/api/learning/stats` | `[{"timestamp":"...","accept_rate":0.88,...}]` | Learning trends |
| `/api/system/events` | `[{"timestamp":"...","event_type":"model_retrain","notes":"..." }]` | Retrain log |

---

## Quick Fixes

### Flask Not Responding
```powershell
# Restart Flask service
nssm restart "VOFC-Flask"

# Check if it's running
Get-Service "VOFC-Flask"

# View recent logs
Get-Content "C:\Tools\nssm\logs\vofc_flask.log" -Tail 50
```

### Tunnel Not Working
```powershell
# Check tunnel status
nssm status "VOFC-Tunnel"

# Restart tunnel
nssm restart "VOFC-Tunnel"

# Check tunnel logs
Get-Content "C:\Tools\nssm\logs\vofc_tunnel.log" -Tail 50
```

### Routes Not Found (404)
1. Verify blueprint is imported in `app.py`
2. Verify blueprint is registered: `app.register_blueprint(models_bp)`
3. Check route exists in `routes/models.py` or `routes/system.py`
4. Restart Flask: `nssm restart "VOFC-Flask"`

### Environment Variables Not Set
1. Create `.env.local` in project root
2. Add:
   ```env
   NEXT_PUBLIC_FLASK_URL=http://localhost:8080
   NEXT_PUBLIC_FLASK_API_URL=http://localhost:8080/api
   ```
3. Restart Next.js dev server

---

## Verification Checklist

After fixing issues, verify:

- [ ] Local Flask health check returns all "ok"
- [ ] Tunnel endpoints return 200 (not 502/404)
- [ ] All NSSM services are running
- [ ] Blueprints are registered in `app.py`
- [ ] Environment variables are set correctly
- [ ] Admin Panel shows correct model info (not "unknown")
- [ ] Admin Panel shows system events (not empty)
- [ ] No console errors in browser dev tools

---

## Still Having Issues?

1. **Run the diagnostic script:**
   ```powershell
   .\scripts\test-backend-endpoints.ps1
   ```

2. **Check all service logs:**
   ```powershell
   # Flask
   Get-Content "C:\Tools\nssm\logs\vofc_flask.log" -Tail 100
   
   # Tunnel
   Get-Content "C:\Tools\nssm\logs\vofc_tunnel.log" -Tail 100
   ```

3. **Verify route paths match exactly:**
   - Flask route: `/api/models/info`
   - Next.js proxy: `/api/models/info` → calls `${FLASK_URL}/api/models/info`
   - Frontend: calls `/api/models/info` (relative URL)

4. **Test with curl directly:**
   ```powershell
   # Local
   curl http://localhost:8080/api/models/info
   
   # Tunnel
   curl https://flask.frostech.site/api/models/info
   ```

---

## Related Documentation

- [Route Reference](ROUTE-REFERENCE.md) - Complete API endpoint list
- [Quick Start](QUICK-START.md) - Initial setup guide
- [Database Schema](DATABASE-SCHEMA.md) - Database structure

