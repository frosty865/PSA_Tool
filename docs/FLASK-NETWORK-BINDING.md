# Flask Network Binding Configuration

## Current Configuration

Both Flask instances are configured to bind to all IPv4 interfaces:

### 1. Development/Project Flask (`app.py`)
```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)
```

### 2. Production Flask (`C:\Tools\VOFC-Flask\server.py`)
```python
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
# ...
app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG_MODE, threaded=True)
```

## Why `0.0.0.0`?

- **`0.0.0.0`** binds Flask to all IPv4 network interfaces
- Allows connections from:
  - `localhost` / `127.0.0.1` (local machine)
  - `0.0.0.0` (all network interfaces)
  - Cloudflare tunnel (via localhost)
- **Sufficient for tunnel use case** since tunnel connects via `localhost:8080`

## IPv6 Dual-Stack Support

For IPv6 support, you would need:

### Option 1: Production WSGI Server (Recommended)
Use Waitress or Gunicorn which support dual-stack:

```python
from waitress import serve

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8080)  # Automatically handles IPv4/IPv6
```

### Option 2: Flask Development Server (Limited)
Flask's development server (`app.run()`) only supports one address family at a time:
- `0.0.0.0` = IPv4 only
- `::` = IPv6 only

For dual-stack, you'd need to run two instances or use a production server.

## Current Setup (Tunnel Use Case)

**Current configuration is correct** for the Cloudflare tunnel:
- Tunnel connects via `http://localhost:8080` (IPv4)
- Flask bound to `0.0.0.0:8080` accepts all IPv4 connections
- No IPv6 needed for tunnel connectivity

## Verification

After restarting Flask, verify binding:

```powershell
netstat -ano | findstr :8080
```

**Expected output:**
```
TCP    0.0.0.0:8080         0.0.0.0:0              LISTENING       <PID>
```

This shows Flask is listening on all IPv4 interfaces.

## Troubleshooting

If tunnel still can't connect:

1. **Verify Flask is bound to 0.0.0.0:**
   ```powershell
   netstat -ano | findstr :8080
   ```
   Should show `0.0.0.0:8080`, not `127.0.0.1:8080`

2. **Restart Flask service:**
   ```powershell
   nssm restart "VOFC-Flask"
   ```

3. **Check firewall:**
   ```powershell
   Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*8080*"}
   ```
   Ensure port 8080 is allowed for inbound connections

4. **Test local connectivity:**
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8080/api/system/health"
   ```

