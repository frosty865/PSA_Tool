# Fix Model Manager Service Paths
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix VOFC-ModelManager Service Paths" -ForegroundColor Cyan
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

# Check current configuration
Write-Host "Current service configuration:" -ForegroundColor Yellow
$currentApp = nssm get $serviceName Application 2>&1
$currentParams = nssm get $serviceName AppParameters 2>&1
$currentDir = nssm get $serviceName AppDirectory 2>&1

Write-Host "  Application: $currentApp" -ForegroundColor Cyan
Write-Host "  Parameters: $currentParams" -ForegroundColor Cyan
Write-Host "  Directory: $currentDir" -ForegroundColor Cyan
Write-Host ""

# Stop service
Write-Host "Stopping service..." -ForegroundColor Yellow
nssm stop $serviceName 2>&1 | Out-Null
Start-Sleep -Seconds 2
Write-Host "✅ Service stopped" -ForegroundColor Green
Write-Host ""

# Update paths
Write-Host "Updating service paths..." -ForegroundColor Yellow
nssm set $serviceName Application $pythonPath
nssm set $serviceName AppParameters $scriptPath
nssm set $serviceName AppDirectory $workingDir

Write-Host "✅ Paths updated" -ForegroundColor Green
Write-Host ""

# Verify new configuration
Write-Host "New service configuration:" -ForegroundColor Yellow
$newApp = nssm get $serviceName Application 2>&1
$newParams = nssm get $serviceName AppParameters 2>&1
$newDir = nssm get $serviceName AppDirectory 2>&1

Write-Host "  Application: $newApp" -ForegroundColor Cyan
Write-Host "  Parameters: $newParams" -ForegroundColor Cyan
Write-Host "  Directory: $newDir" -ForegroundColor Cyan
Write-Host ""

# Start service
Write-Host "Starting service..." -ForegroundColor Yellow
nssm start $serviceName

Start-Sleep -Seconds 3

$status = nssm status $serviceName 2>&1
if ($status -eq "SERVICE_RUNNING") {
    Write-Host "✅ Service started successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Service status: $status" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Check error logs:" -ForegroundColor Cyan
    Write-Host "  C:\Tools\ModelManager\service_error.log" -ForegroundColor White
    Write-Host "  C:\Tools\VOFC_Logs\model_manager.log" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Done" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

