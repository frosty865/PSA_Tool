# Reinstall Model Manager NSSM Service
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Reinstall VOFC-ModelManager Service" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$serviceName = "VOFC-ModelManager"
$pythonPath = "C:\Tools\python\python.exe"
$scriptPath = "C:\Tools\ModelManager\model_manager.py"
$workingDir = "C:\Tools\ModelManager"

# Remove existing service
Write-Host "Removing existing service..." -ForegroundColor Yellow
nssm stop $serviceName 2>&1 | Out-Null
Start-Sleep -Seconds 2
nssm remove $serviceName confirm 2>&1 | Out-Null
Start-Sleep -Seconds 1
Write-Host "✅ Old service removed" -ForegroundColor Green
Write-Host ""

# Install new service
Write-Host "Installing service..." -ForegroundColor Yellow
nssm install $serviceName $pythonPath $scriptPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install service!" -ForegroundColor Red
    exit 1
}

# Configure service
Write-Host "Configuring service..." -ForegroundColor Yellow
nssm set $serviceName AppDirectory $workingDir
nssm set $serviceName Start SERVICE_AUTO_START
nssm set $serviceName AppStdout "$workingDir\service_output.log"
nssm set $serviceName AppStderr "$workingDir\service_error.log"

Write-Host "✅ Service configured" -ForegroundColor Green
Write-Host ""

# Start service
Write-Host "Starting service..." -ForegroundColor Yellow
nssm start $serviceName

Start-Sleep -Seconds 3

$status = nssm status $serviceName 2>&1
if ($status -eq "SERVICE_RUNNING") {
    Write-Host "✅ Service installed and running!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Service status: $status" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Service location: C:\Tools\ModelManager" -ForegroundColor Cyan
Write-Host "Python: C:\Tools\python\python.exe" -ForegroundColor Cyan

