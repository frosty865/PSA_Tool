# Stop Flask Service (with dependencies)
# Run this script as Administrator

Write-Host "Stopping VOFC Flask Service and dependencies..." -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or run manually (stop dependents first):" -ForegroundColor Yellow
    Write-Host "  nssm stop VOFC-Tunnel" -ForegroundColor Cyan
    Write-Host "  nssm stop vofc-flask" -ForegroundColor Cyan
    exit 1
}

$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

# Stop services in dependency order (dependents first)
Write-Host "Stopping dependent services first..." -ForegroundColor Yellow

# 1. Stop VOFC-Tunnel (depends on Flask)
Write-Host "  Stopping VOFC-Tunnel..." -ForegroundColor Gray
& $nssmPath stop VOFC-Tunnel
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ VOFC-Tunnel stopped" -ForegroundColor Green
    Start-Sleep -Seconds 2
} else {
    Write-Host "  ⚠ VOFC-Tunnel stop failed or already stopped" -ForegroundColor Yellow
}

# 2. Stop vofc-flask
Write-Host "  Stopping vofc-flask..." -ForegroundColor Gray
& $nssmPath stop vofc-flask
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ vofc-flask stopped" -ForegroundColor Green
    Start-Sleep -Seconds 2
} else {
    Write-Host "  ✗ Failed to stop vofc-flask" -ForegroundColor Red
    Write-Host "  Error: $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Flask service and dependencies stopped successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "To restart:" -ForegroundColor Cyan
Write-Host "  nssm start vofc-flask" -ForegroundColor Gray
Write-Host "  nssm start VOFC-Tunnel" -ForegroundColor Gray

