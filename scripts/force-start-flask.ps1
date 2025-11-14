# Force Start Flask Service (handles PAUSED state)
# Run this script as Administrator

Write-Host "Force starting Flask service..." -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$ServiceName = "vofc-flask"
$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

# Check current status
Write-Host "Checking service status..." -ForegroundColor Yellow
$status = & $nssmPath status $ServiceName 2>&1
Write-Host "  Current status: $status" -ForegroundColor Gray
Write-Host ""

# Stop dependent service first
Write-Host "Stopping VOFC-Tunnel..." -ForegroundColor Yellow
& $nssmPath stop VOFC-Tunnel 2>&1 | Out-Null
Start-Sleep -Seconds 2

# Force stop Flask (works even if PAUSED)
Write-Host "Force stopping Flask service..." -ForegroundColor Yellow
& $nssmPath stop $ServiceName
Start-Sleep -Seconds 3

# Verify stopped
$checkStatus = & $nssmPath status $ServiceName 2>&1
if ($checkStatus -eq "SERVICE_STOPPED" -or $LASTEXITCODE -ne 0) {
    Write-Host "  ✓ Service is stopped" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Status: $checkStatus" -ForegroundColor Yellow
    Write-Host "  Attempting to start anyway..." -ForegroundColor Yellow
}
Write-Host ""

# Start Flask
Write-Host "Starting Flask service..." -ForegroundColor Yellow
& $nssmPath start $ServiceName

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Start command sent" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting 5 seconds for service to start..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
    
    # Check final status
    $finalStatus = & $nssmPath status $ServiceName 2>&1
    Write-Host "Service status: $finalStatus" -ForegroundColor Gray
    
    if ($finalStatus -eq "SERVICE_RUNNING") {
        Write-Host ""
        Write-Host "✅ Flask service is running!" -ForegroundColor Green
        
        # Start tunnel
        Write-Host ""
        Write-Host "Starting VOFC-Tunnel..." -ForegroundColor Yellow
        & $nssmPath start VOFC-Tunnel
        Start-Sleep -Seconds 2
        
        Write-Host ""
        Write-Host "✅ All services started!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Test with: curl http://localhost:8080/api/system/health" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "⚠️  Service status: $finalStatus" -ForegroundColor Yellow
        Write-Host "Check logs: C:\Tools\nssm\logs\vofc_flask_err.log" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "If still failing, check:" -ForegroundColor Cyan
        Write-Host "  1. Code synced: .\scripts\sync-flask-code.ps1" -ForegroundColor Gray
        Write-Host "  2. Dependencies installed in venv" -ForegroundColor Gray
        Write-Host "  3. Error logs for specific issues" -ForegroundColor Gray
    }
} else {
    Write-Host ""
    Write-Host "❌ Failed to start service" -ForegroundColor Red
    Write-Host "Check logs: C:\Tools\nssm\logs\vofc_flask_err.log" -ForegroundColor Yellow
    exit 1
}

