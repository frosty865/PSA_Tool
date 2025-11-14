# Fix Flask Service to Use server.py Instead of app.py
# Run this script as Administrator

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix Flask Service Entry Point" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$ServiceName = "vofc-flask"
$FlaskDir = "C:\Tools\VOFC-Flask"

# Check current parameters
Write-Host "Current service parameters:" -ForegroundColor Cyan
$currentParams = nssm get $ServiceName AppParameters
Write-Host "  $currentParams" -ForegroundColor Gray

# Stop service
Write-Host ""
Write-Host "Stopping service..." -ForegroundColor Cyan
nssm stop $ServiceName
Start-Sleep -Seconds 2

# Update to use server.py
Write-Host "Updating to use server.py..." -ForegroundColor Cyan
nssm set $ServiceName AppParameters "-m waitress --listen=0.0.0.0:8080 server:app"

# Verify change
$newParams = nssm get $ServiceName AppParameters
Write-Host "New service parameters:" -ForegroundColor Cyan
Write-Host "  $newParams" -ForegroundColor Green

# Start service
Write-Host ""
Write-Host "Starting service..." -ForegroundColor Cyan
nssm start $ServiceName
Start-Sleep -Seconds 5

# Check status
$status = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($status) {
    Write-Host ""
    Write-Host "Service status: $($status.Status)" -ForegroundColor $(if ($status.Status -eq 'Running') { 'Green' } else { 'Yellow' })
    
    if ($status.Status -eq 'Running') {
        Write-Host "  ✓ Service is running!" -ForegroundColor Green
        
        # Check if listening on port
        Start-Sleep -Seconds 2
        $listening = netstat -ano | Select-String ":8080" | Select-String "LISTENING"
        if ($listening) {
            Write-Host "  ✓ Flask is listening on port 8080" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Port 8080 not yet listening (may need more time)" -ForegroundColor Yellow
        }
    } elseif ($status.Status -eq 'Paused') {
        Write-Host "  ⚠ Service is paused - check logs:" -ForegroundColor Yellow
        Write-Host "    C:\Tools\nssm\logs\vofc_flask_err.log" -ForegroundColor Gray
        if (Test-Path "C:\Tools\nssm\logs\vofc_flask_err.log") {
            Write-Host ""
            Write-Host "Last 5 lines of error log:" -ForegroundColor Cyan
            Get-Content "C:\Tools\nssm\logs\vofc_flask_err.log" -Tail 5
        }
    }
} else {
    Write-Host "  ✗ Could not get service status" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Done!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test with:" -ForegroundColor Cyan
Write-Host "  curl http://localhost:8080/api/system/health" -ForegroundColor White
Write-Host ""

