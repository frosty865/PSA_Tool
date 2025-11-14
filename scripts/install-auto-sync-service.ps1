# Install Auto-Sync as a Windows Service
# This service will automatically sync code changes from project to Tools folders

Write-Host "=== Installing Auto-Sync Service ===" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$ServiceName = "VOFC-AutoSync"
$ScriptPath = Join-Path $PSScriptRoot "auto-sync-services.ps1"
$nssmPath = "C:\Tools\nssm\nssm.exe"

if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

# Check if service already exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Service $ServiceName already exists. Removing..." -ForegroundColor Yellow
    & $nssmPath stop $ServiceName 2>&1 | Out-Null
    Start-Sleep -Seconds 2
    & $nssmPath remove $ServiceName confirm 2>&1 | Out-Null
    Start-Sleep -Seconds 1
}

Write-Host "Installing $ServiceName..." -ForegroundColor Yellow
Write-Host "  Script: $ScriptPath" -ForegroundColor Gray

# Install service
& $nssmPath install $ServiceName "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" "-ExecutionPolicy Bypass -File `"$ScriptPath`" -AutoRestart"

# Configure service
& $nssmPath set $ServiceName AppDirectory (Split-Path $ScriptPath -Parent)
& $nssmPath set $ServiceName DisplayName "VOFC Auto-Sync (Code Sync Service)"
& $nssmPath set $ServiceName Description "Automatically syncs code changes from project folder to C:\Tools\* service directories"
& $nssmPath set $ServiceName Start SERVICE_AUTO_START
& $nssmPath set $ServiceName AppStdout "C:\Tools\nssm\logs\autosync_out.log"
& $nssmPath set $ServiceName AppStderr "C:\Tools\nssm\logs\autosync_err.log"
& $nssmPath set $ServiceName AppStopMethodSkip 6

Write-Host ""
Write-Host "✅ Service installed!" -ForegroundColor Green
Write-Host ""
Write-Host "Starting service..." -ForegroundColor Yellow
& $nssmPath start $ServiceName

Start-Sleep -Seconds 2

$status = & $nssmPath status $ServiceName 2>&1
if ($status -eq "SERVICE_RUNNING") {
    Write-Host "✅ Service is running!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Service status: $status" -ForegroundColor Yellow
    Write-Host "Check logs: C:\Tools\nssm\logs\autosync_err.log" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "The auto-sync service will now:" -ForegroundColor Cyan
Write-Host "  - Watch for file changes in project folder" -ForegroundColor Gray
Write-Host "  - Automatically sync to C:\Tools\VOFC-Flask" -ForegroundColor Gray
Write-Host "  - Automatically sync to C:\Tools\VOFC-Processor" -ForegroundColor Gray
Write-Host "  - Auto-restart services on critical file changes" -ForegroundColor Gray
Write-Host ""
Write-Host "Service management:" -ForegroundColor Cyan
Write-Host "  nssm status $ServiceName" -ForegroundColor White
Write-Host "  nssm restart $ServiceName" -ForegroundColor White
Write-Host "  nssm stop $ServiceName" -ForegroundColor White

