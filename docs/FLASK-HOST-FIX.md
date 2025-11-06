# Flask Host Binding Fix

## Problem
Flask was listening on `127.0.0.1:8080` (localhost only) instead of `0.0.0.0:8080` (all interfaces), preventing the Cloudflare tunnel from connecting.

## Root Cause
The NSSM service runs `server.py` from `C:\Tools\VOFC-Flask`, which had:
```python
SERVER_HOST = os.getenv('SERVER_HOST', '127.0.0.1')
```

## Solution
Changed the default to `0.0.0.0`:
```python
SERVER_HOST = os.getenv('SERVER_HOST', '0.0.0.0')
```

## Verification
After restarting Flask, verify it's listening on all interfaces:
```powershell
netstat -ano | findstr :8080
```

Should show:
```
TCP    0.0.0.0:8080         0.0.0.0:0              LISTENING       <PID>
```

Instead of:
```
TCP    127.0.0.1:8080         0.0.0.0:0              LISTENING       <PID>
```

## Restart Required
After making this change, restart the Flask service:
```powershell
nssm restart "VOFC-Flask"
```

## Alternative: Environment Variable
You can also set `SERVER_HOST=0.0.0.0` in the NSSM service environment variables:
```powershell
nssm set VOFC-Flask AppEnvironmentExtra SERVER_HOST=0.0.0.0
```

