# Restart Folder Watcher

## Quick Restart

Use the PowerShell script:
```powershell
.\scripts\restart-watcher.ps1
```

## Manual Restart via API

### Step 1: Stop Watcher
```powershell
$body = @{action='stop_watcher'} | ConvertTo-Json
Invoke-RestMethod -Uri "http://10.0.0.213:8080/api/system/control" -Method POST -Body $body -ContentType "application/json"
```

### Step 2: Start Watcher
```powershell
$body = @{action='start_watcher'} | ConvertTo-Json
Invoke-RestMethod -Uri "http://10.0.0.213:8080/api/system/control" -Method POST -Body $body -ContentType "application/json"
```

## Via Admin Panel

1. Navigate to `/admin/processing`
2. Click **⏹️ Stop Watcher**
3. Wait 2 seconds
4. Click **▶️ Start Watcher**

## What the Watcher Does

The folder watcher monitors `C:\Tools\Ollama\Data\incoming` for new files and automatically processes them through the pipeline.

## Troubleshooting

### 404 Error on `/api/system/control`

The route needs to be added to the running Flask instance:
- Route exists in project: `routes/system.py`
- Must be copied to: `C:\Tools\VOFC-Flask\routes\system.py`
- Then restart Flask: `nssm restart "VOFC-Flask"`

### Watcher Not Starting

1. Check Flask logs: `Get-Content "C:\Tools\nssm\logs\vofc_flask.log" -Tail 50`
2. Verify `watchdog` is installed: `pip list | findstr watchdog`
3. Check incoming directory exists: `Test-Path "C:\Tools\Ollama\Data\incoming"`

