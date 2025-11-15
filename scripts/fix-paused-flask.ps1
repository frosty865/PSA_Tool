# Fix PAUSED Flask Service
# Run this script as Administrator

Write-Host "Fixing PAUSED Flask service..." -ForegroundColor Cyan
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
Write-Host "Current service status:" -ForegroundColor Yellow
$status = & $nssmPath status $ServiceName
Write-Host "  $status" -ForegroundColor Gray
Write-Host ""

# If paused, we need to stop it first (can't restart a paused service)
if ($status -eq "SERVICE_PAUSED") {
    Write-Host "Service is PAUSED - stopping it first..." -ForegroundColor Yellow
    
    # Stop dependent service first
    Write-Host "  Stopping VOFC-Tunnel..." -ForegroundColor Gray
    & $nssmPath stop VOFC-Tunnel 2>&1 | Out-Null
    Start-Sleep -Seconds 2
    
    # Force stop Flask
    Write-Host "  Stopping vofc-flask..." -ForegroundColor Gray
    & $nssmPath stop $ServiceName
    Start-Sleep -Seconds 3
    
    # Verify it's stopped
    $newStatus = & $nssmPath status $ServiceName
    if ($newStatus -eq "SERVICE_STOPPED") {
        Write-Host "  [OK] Service stopped" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Service status: $newStatus" -ForegroundColor Yellow
        Write-Host "  Attempting to start anyway..." -ForegroundColor Yellow
    }
    Write-Host ""
}

# Now start the service
Write-Host "Starting Flask service..." -ForegroundColor Yellow
& $nssmPath start $ServiceName

if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Start command sent" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting 5 seconds for service to start..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
    
    # Check status
    $finalStatus = & $nssmPath status $ServiceName
    Write-Host "Service status: $finalStatus" -ForegroundColor Gray
    
    if ($finalStatus -eq "SERVICE_RUNNING") {
        Write-Host ""
        Write-Host "[OK] Flask service is running!" -ForegroundColor Green
        
        # Restart tunnel
        Write-Host ""
        Write-Host "Restarting VOFC-Tunnel..." -ForegroundColor Yellow
        & $nssmPath start VOFC-Tunnel
        Start-Sleep -Seconds 2
        
        Write-Host ""
        Write-Host "[OK] All services started!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Test with: curl http://localhost:8080/api/system/health" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "[WARN] Service status: $finalStatus" -ForegroundColor Yellow
        Write-Host "Check logs: C:\Tools\nssm\logs\vofc_flask_err.log" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "[FAIL] Failed to start service" -ForegroundColor Red
    Write-Host "Check logs: C:\Tools\nssm\logs\vofc_flask_err.log" -ForegroundColor Yellow
    exit 1
}

