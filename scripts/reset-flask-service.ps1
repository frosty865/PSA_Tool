# Reset Flask Service - Stop completely then start fresh
# Run this script as Administrator

Write-Host "Resetting Flask service (stop then start)..." -ForegroundColor Cyan
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
$status = & $nssmPath status $ServiceName 2>&1
Write-Host "  $status" -ForegroundColor Gray
Write-Host ""

# Stop dependent service first
Write-Host "Stopping VOFC-Tunnel..." -ForegroundColor Yellow
& $nssmPath stop VOFC-Tunnel 2>&1 | Out-Null
Start-Sleep -Seconds 2

# Force stop Flask (works for PAUSED, STOPPED, or RUNNING)
Write-Host "Stopping Flask service..." -ForegroundColor Yellow
& $nssmPath stop $ServiceName
$stopExitCode = $LASTEXITCODE
Start-Sleep -Seconds 3

# Verify stopped
$checkStatus = & $nssmPath status $ServiceName 2>&1
Write-Host "  Status after stop: $checkStatus" -ForegroundColor Gray

# If still not stopped, try using sc.exe directly
if ($checkStatus -ne "SERVICE_STOPPED" -and $stopExitCode -ne 0) {
    Write-Host "  Attempting force stop with sc.exe..." -ForegroundColor Yellow
    & sc.exe stop $ServiceName 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    $checkStatus = & $nssmPath status $ServiceName 2>&1
    Write-Host "  Status after sc stop: $checkStatus" -ForegroundColor Gray
}

Write-Host ""

# Start Flask
Write-Host "Starting Flask service..." -ForegroundColor Yellow
& $nssmPath start $ServiceName

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Start command sent" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting 8 seconds for service to fully start..." -ForegroundColor Gray
    Start-Sleep -Seconds 8
    
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
        Write-Host "Recent errors:" -ForegroundColor Cyan
        Get-Content C:\Tools\nssm\logs\vofc_flask_err.log -Tail 10 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    }
} else {
    Write-Host ""
    Write-Host "❌ Failed to start service" -ForegroundColor Red
    Write-Host "Check logs: C:\Tools\nssm\logs\vofc_flask_err.log" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Recent errors:" -ForegroundColor Cyan
    Get-Content C:\Tools\nssm\logs\vofc_flask_err.log -Tail 10 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    exit 1
}

