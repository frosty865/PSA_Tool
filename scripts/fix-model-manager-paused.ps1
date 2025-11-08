# Fix Model Manager Service Paused State
# Resumes the service if it's paused and ensures it stays running
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix Model Manager Paused State" -ForegroundColor Cyan
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

Write-Host "Checking service status..." -ForegroundColor Yellow
$status = nssm status $serviceName 2>&1

Write-Host "Current status: $status" -ForegroundColor Cyan
Write-Host ""

if ($status -eq "SERVICE_PAUSED") {
    Write-Host "Service is paused. Resuming..." -ForegroundColor Yellow
    nssm resume $serviceName 2>&1 | Out-Null
    
    Start-Sleep -Seconds 2
    
    $newStatus = nssm status $serviceName 2>&1
    if ($newStatus -eq "SERVICE_RUNNING") {
        Write-Host "✅ Service resumed successfully!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Service status after resume: $newStatus" -ForegroundColor Yellow
        Write-Host "Trying to start instead..." -ForegroundColor Yellow
        nssm start $serviceName 2>&1 | Out-Null
        Start-Sleep -Seconds 2
        $finalStatus = nssm status $serviceName 2>&1
        Write-Host "Final status: $finalStatus" -ForegroundColor Cyan
    }
} elseif ($status -eq "SERVICE_RUNNING") {
    Write-Host "✅ Service is already running" -ForegroundColor Green
} elseif ($status -eq "SERVICE_STOPPED") {
    Write-Host "Service is stopped. Starting..." -ForegroundColor Yellow
    nssm start $serviceName 2>&1 | Out-Null
    Start-Sleep -Seconds 2
    $newStatus = nssm status $serviceName 2>&1
    Write-Host "Status after start: $newStatus" -ForegroundColor Cyan
} else {
    Write-Host "⚠️  Unknown service status: $status" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Checking service configuration..." -ForegroundColor Yellow

# Ensure service is set to auto-start
nssm set $serviceName Start SERVICE_AUTO_START 2>&1 | Out-Null
Write-Host "✅ Auto-start configured" -ForegroundColor Green

# Ensure AppExit is set to restart
nssm set $serviceName AppExit Default Restart 2>&1 | Out-Null
Write-Host "✅ Auto-restart on exit configured" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Done" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Final service status:" -ForegroundColor Yellow
$finalStatus = nssm status $serviceName 2>&1
Write-Host "  $finalStatus" -ForegroundColor $(if ($finalStatus -eq "SERVICE_RUNNING") { "Green" } else { "Yellow" })
Write-Host ""
Write-Host "Monitor logs:" -ForegroundColor Cyan
Write-Host "  Get-Content -Path `"C:\Tools\VOFC_Logs\model_manager.log`" -Wait" -ForegroundColor White
Write-Host ""

