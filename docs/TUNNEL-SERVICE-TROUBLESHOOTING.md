# VOFC-Tunnel Service Troubleshooting Guide

## Common Error: "Cannot start service 'VOFC-Tunnel'"

### Symptoms
- Service exists but won't start
- Error: "Service 'VOFC-Tunnel' cannot be started due to the following error: Cannot start service 'VOFC-Tunnel' on computer '.'"
- Service status shows "Stopped"

### Root Causes

1. **NSSM Configuration Issues**
   - Service not configured to restart on exit
   - Missing console output settings
   - Incorrect exit behavior

2. **Cloudflared Authentication Issues**
   - Invalid or expired credentials
   - Missing credentials file
   - Network connectivity issues

3. **Permission Issues**
   - Service account doesn't have permissions
   - Log directory not accessible

4. **Port/Network Conflicts**
   - Another process using required ports
   - Firewall blocking connections

## Fix Steps

### Step 1: Run Fix Script (Recommended)

Run as **Administrator**:

```powershell
.\scripts\fix-tunnel-service-complete.ps1
```

This script will:
- Verify all prerequisites
- Configure NSSM settings properly
- Set up logging
- Attempt to start the service

### Step 2: Manual NSSM Configuration

If the script doesn't work, configure manually (as Administrator):

```powershell
# Set exit behavior to restart
nssm set VOFC-Tunnel AppExit Default Restart

# Set restart delay (5 seconds)
nssm set VOFC-Tunnel AppRestartDelay 5000

# Enable console output
nssm set VOFC-Tunnel AppNoConsole 0

# Verify configuration
nssm get VOFC-Tunnel AppExit
nssm get VOFC-Tunnel AppRestartDelay
```

### Step 3: Check Service Account

Verify the service is running under the correct account:

```powershell
nssm get VOFC-Tunnel ObjectName
```

Should be `LocalSystem` or your user account. If it's wrong:

```powershell
nssm set VOFC-Tunnel ObjectName "LocalSystem"
```

### Step 4: Test Cloudflared Manually

Test if cloudflared works when run directly:

```powershell
cd C:\Tools\cloudflared
.\cloudflared.exe --config config.yaml tunnel run ollama-tunnel
```

If this works but the service doesn't, it's likely a service configuration issue.

### Step 5: Check Logs

Check NSSM logs for errors:

```powershell
# Error log
Get-Content "C:\Tools\nssm\logs\vofc_tunnel_err.log" -Tail 50

# Output log
Get-Content "C:\Tools\nssm\logs\vofc_tunnel_out.log" -Tail 50
```

Check Windows Event Log:

```powershell
Get-EventLog -LogName System -Source "Service Control Manager" -Newest 20 | 
    Where-Object {$_.Message -like "*VOFC-Tunnel*"} | 
    Format-List TimeGenerated, EntryType, Message
```

### Step 6: Verify Prerequisites

```powershell
# Check cloudflared.exe exists
Test-Path "C:\Tools\cloudflared\cloudflared.exe"

# Check config file exists
Test-Path "C:\Tools\cloudflared\config.yaml"

# Check credentials exist
Test-Path "C:\Users\frost\.cloudflared\17152659-d3ad-4abf-ae71-d0cc9d2b89e3.json"

# Test cloudflared version
& "C:\Tools\cloudflared\cloudflared.exe" --version
```

### Step 7: Reinstall Service (Last Resort)

If nothing else works, remove and reinstall:

```powershell
# Stop and remove
nssm stop VOFC-Tunnel
nssm remove VOFC-Tunnel confirm

# Reinstall
nssm install VOFC-Tunnel "C:\Tools\cloudflared\cloudflared.exe"
nssm set VOFC-Tunnel AppDirectory "C:\Tools\cloudflared"
nssm set VOFC-Tunnel AppParameters "--config C:\Tools\cloudflared\config.yaml tunnel run ollama-tunnel"
nssm set VOFC-Tunnel DisplayName "VOFC-Tunnel (Cloudflare Tunnel)"
nssm set VOFC-Tunnel Description "Cloudflare Tunnel for external access to Flask API and Ollama"
nssm set VOFC-Tunnel Start SERVICE_AUTO_START
nssm set VOFC-Tunnel AppExit Default Restart
nssm set VOFC-Tunnel AppRestartDelay 5000
nssm set VOFC-Tunnel AppNoConsole 0

# Set up logging
$logDir = "C:\Tools\nssm\logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force
}
nssm set VOFC-Tunnel AppStdout "$logDir\vofc_tunnel_out.log"
nssm set VOFC-Tunnel AppStderr "$logDir\vofc_tunnel_err.log"
nssm set VOFC-Tunnel AppStdoutCreationDisposition 4
nssm set VOFC-Tunnel AppStderrCreationDisposition 4

# Start service
nssm start VOFC-Tunnel
```

## Verification

After fixing, verify the service is running:

```powershell
Get-Service VOFC-Tunnel
```

Should show `Status: Running`

Test the tunnel:

```powershell
curl https://flask.frostech.site/api/system/health
```

Should return JSON with system status.

## Additional Notes

- **Always run NSSM commands as Administrator**
- Cloudflared needs network access to Cloudflare's servers
- The service may take 10-30 seconds to fully connect after starting
- Check Cloudflare dashboard to verify tunnel is active
- If tunnel connects but Flask isn't accessible, check Flask service is running

