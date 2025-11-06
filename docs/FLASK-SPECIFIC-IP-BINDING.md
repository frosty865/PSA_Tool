# Flask Specific IP Binding

## Configuration Change

Flask is now bound to a specific IP address: `10.0.0.213:8080`

**File:** `C:\Tools\VOFC-Flask\server.py`
```python
if __name__ == "__main__":
    app.run(host="10.0.0.213", port=8080)
```

## Important: Tunnel Configuration Update Required

Since Flask is now bound to a specific IP (`10.0.0.213`) instead of all interfaces (`0.0.0.0`), the Cloudflare tunnel configuration must be updated to point to this IP address.

### Current Tunnel Config (Needs Update)
```yaml
ingress:
  - hostname: flask.frostech.site
    service: http://localhost:8080  # ❌ Won't work with specific IP binding
```

### Required Tunnel Config Update
```yaml
ingress:
  - hostname: flask.frostech.site
    service: http://10.0.0.213:8080  # ✅ Points to Flask's bound IP
```

## Update Tunnel Configuration

1. **Edit tunnel config file:**
   ```powershell
   notepad "C:\Users\frost\cloudflared\config.yml"
   ```

2. **Update the service URLs:**
   ```yaml
   ingress:
     - hostname: ollama.frostech.site
       service: http://localhost:11434
     - hostname: backend.frostech.site
       service: http://10.0.0.213:8080  # Changed from localhost
     - hostname: flask.frostech.site
       service: http://10.0.0.213:8080  # Changed from localhost
     - service: http_status:404
   ```

3. **Restart tunnel service:**
   ```powershell
   nssm restart "VOFC-Tunnel"
   ```

## Verification

After updating:

1. **Check Flask is bound to the correct IP:**
   ```powershell
   netstat -ano | findstr :8080
   ```
   Should show: `TCP    10.0.0.213:8080    0.0.0.0:0    LISTENING`

2. **Test tunnel connectivity:**
   ```powershell
   Invoke-RestMethod -Uri "https://flask.frostech.site/api/system/health"
   ```

## Alternative: Use Environment Variable

If you want flexibility, you can use an environment variable:

```python
SERVER_HOST = os.getenv('SERVER_HOST', '10.0.0.213')
app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG_MODE, threaded=True)
```

Then set in NSSM:
```powershell
nssm set VOFC-Flask AppEnvironmentExtra SERVER_HOST=10.0.0.213
```

## Network Considerations

- Flask will **only** accept connections on `10.0.0.213:8080`
- `localhost` and `127.0.0.1` connections will **not work** unless that IP is also `10.0.0.213`
- Ensure `10.0.0.213` is a valid IP on your network interface
- Firewall rules may need to allow connections to this specific IP

