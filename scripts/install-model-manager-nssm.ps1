# Install Model Manager as NSSM Service
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Install VOFC-ModelManager NSSM Service" -ForegroundColor Cyan
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

Write-Host "✅ Running as Administrator" -ForegroundColor Green
Write-Host ""

# Configuration
$serviceName = "VOFC-ModelManager"
$pythonPath = "C:\Tools\python\python.exe"
$scriptPath = "C:\Tools\ModelManager\model_manager.py"
$workingDir = "C:\Tools\ModelManager"

# Verify paths
if (-not (Test-Path $pythonPath)) {
    Write-Host "❌ Python not found at: $pythonPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $scriptPath)) {
    Write-Host "❌ Model Manager script not found at: $scriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "✅ All paths verified" -ForegroundColor Green
Write-Host ""

# Check if service already exists
$existingStatus = nssm status $serviceName 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "⚠️  Service '$serviceName' already exists!" -ForegroundColor Yellow
    Write-Host "Current status: $existingStatus" -ForegroundColor Cyan
    Write-Host ""
    $response = Read-Host "Remove and reinstall? (y/N)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "Stopping service..." -ForegroundColor Yellow
        nssm stop $serviceName 2>&1 | Out-Null
        Start-Sleep -Seconds 2
        Write-Host "Removing service..." -ForegroundColor Yellow
        nssm remove $serviceName confirm 2>&1 | Out-Null
        Start-Sleep -Seconds 1
        Write-Host "✅ Service removed" -ForegroundColor Green
    } else {
        Write-Host "Cancelled. Exiting." -ForegroundColor Yellow
        exit 0
    }
}

# Create working directory if it doesn't exist
if (-not (Test-Path $workingDir)) {
    New-Item -ItemType Directory -Path $workingDir -Force | Out-Null
    Write-Host "✅ Created working directory: $workingDir" -ForegroundColor Green
}

Write-Host "Installing NSSM service..." -ForegroundColor Yellow
Write-Host "  Service Name: $serviceName" -ForegroundColor Cyan
Write-Host "  Python: $pythonPath" -ForegroundColor Cyan
Write-Host "  Script: $scriptPath" -ForegroundColor Cyan
Write-Host "  Working Directory: $workingDir" -ForegroundColor Cyan
Write-Host ""

# Install service
nssm install $serviceName $pythonPath $scriptPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install service!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Service installed" -ForegroundColor Green
Write-Host ""

# Configure service
Write-Host "Configuring service..." -ForegroundColor Yellow
nssm set $serviceName AppDirectory $workingDir
nssm set $serviceName Start SERVICE_AUTO_START
nssm set $serviceName AppStdout "$workingDir\service_output.log"
nssm set $serviceName AppStderr "$workingDir\service_error.log"
nssm set $serviceName AppRotateFiles 1
nssm set $serviceName AppRotateOnline 1
nssm set $serviceName AppRotateSeconds 86400
nssm set $serviceName AppRotateBytes 10485760

Write-Host "✅ Service configured" -ForegroundColor Green
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
    Write-Host "Check the logs:" -ForegroundColor Cyan
    Write-Host "  C:\Tools\VOFC_Logs\model_manager.log" -ForegroundColor White
    Write-Host "  $workingDir\service_output.log" -ForegroundColor White
    Write-Host "  $workingDir\service_error.log" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service commands:" -ForegroundColor Yellow
Write-Host "  nssm status $serviceName" -ForegroundColor White
Write-Host "  nssm start $serviceName" -ForegroundColor White
Write-Host "  nssm stop $serviceName" -ForegroundColor White
Write-Host "  nssm restart $serviceName" -ForegroundColor White
Write-Host "  nssm edit $serviceName" -ForegroundColor White

