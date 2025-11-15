# Fix Processor Service Path
# Run this script as Administrator to update the service to use the correct path

Write-Host "Fixing Processor service path..." -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

$ServiceName = "VOFC-Processor"
$CorrectScriptPath = "C:\Tools\VOFC-Processor\vofc_processor.py"
$CorrectDirectory = "C:\Tools\VOFC-Processor"

# Check if correct path exists
if (-not (Test-Path $CorrectScriptPath)) {
    Write-Host "ERROR: Script not found at: $CorrectScriptPath" -ForegroundColor Red
    Write-Host "Please run sync-processor-code.ps1 first to sync the code" -ForegroundColor Yellow
    exit 1
}

Write-Host "Current service configuration:" -ForegroundColor Yellow
$currentParams = & $nssmPath get $ServiceName AppParameters
$currentDir = & $nssmPath get $ServiceName AppDirectory
Write-Host "  AppParameters: $currentParams" -ForegroundColor Gray
Write-Host "  AppDirectory: $currentDir" -ForegroundColor Gray
Write-Host ""

# Stop service
Write-Host "Stopping service..." -ForegroundColor Yellow
& $nssmPath stop $ServiceName
Start-Sleep -Seconds 2

# Update paths
Write-Host "Updating service paths..." -ForegroundColor Yellow
& $nssmPath set $ServiceName AppParameters $CorrectScriptPath
& $nssmPath set $ServiceName AppDirectory $CorrectDirectory

Write-Host "  ✓ AppParameters: $CorrectScriptPath" -ForegroundColor Green
Write-Host "  ✓ AppDirectory: $CorrectDirectory" -ForegroundColor Green
Write-Host ""

# Restart service
Write-Host "Starting service..." -ForegroundColor Yellow
& $nssmPath start $ServiceName
Start-Sleep -Seconds 3

# Check status
$status = & $nssmPath status $ServiceName
if ($status -match "SERVICE_RUNNING") {
    Write-Host "  ✓ Service is running" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Service status: $status" -ForegroundColor Yellow
    Write-Host "  Check logs: C:\Tools\Ollama\Data\logs\vofc_processor_err.log" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Service path updated!" -ForegroundColor Green
Write-Host ""
Write-Host "The service should now write logs to: C:\Tools\Ollama\Data\logs\vofc_processor.log" -ForegroundColor Cyan
Write-Host "Check the log file in a few seconds to verify it's working." -ForegroundColor Cyan

