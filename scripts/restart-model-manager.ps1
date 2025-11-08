# Restart VOFC Model Manager Service
# Run this script as Administrator

$serviceName = "VOFC-ModelManager"

Write-Host "Checking $serviceName status..." -ForegroundColor Yellow
$currentStatus = nssm status $serviceName 2>&1
Write-Host "Current status: $currentStatus" -ForegroundColor Cyan
Write-Host ""

# Handle paused state
if ($currentStatus -eq "SERVICE_PAUSED") {
    Write-Host "Service is paused. Resuming first..." -ForegroundColor Yellow
    nssm resume $serviceName 2>&1 | Out-Null
    Start-Sleep -Seconds 2
    
    $statusAfterResume = nssm status $serviceName 2>&1
    if ($statusAfterResume -eq "SERVICE_RUNNING") {
        Write-Host "✅ Service resumed successfully" -ForegroundColor Green
        Write-Host ""
        Write-Host "Check logs:" -ForegroundColor Cyan
        Write-Host "  Get-Content -Path `"C:\Tools\VOFC_Logs\model_manager.log`" -Wait" -ForegroundColor White
        exit 0
    } else {
        Write-Host "⚠️  Resume didn't work. Stopping and restarting..." -ForegroundColor Yellow
        nssm stop $serviceName 2>&1 | Out-Null
        Start-Sleep -Seconds 2
    }
}

Write-Host "Restarting $serviceName..." -ForegroundColor Yellow
nssm restart $serviceName

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Service restart command sent" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting 3 seconds for service to start..." -ForegroundColor Cyan
    Start-Sleep -Seconds 3
    
    $status = nssm status $serviceName 2>&1
    if ($status -eq "SERVICE_RUNNING") {
        Write-Host "✅ Service is running" -ForegroundColor Green
    } elseif ($status -eq "SERVICE_PAUSED") {
        Write-Host "⚠️  Service is paused. Try running: .\scripts\fix-model-manager-paused.ps1" -ForegroundColor Yellow
    } else {
        Write-Host "⚠️  Service status: $status" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Check logs:" -ForegroundColor Cyan
    Write-Host "  Get-Content -Path `"C:\Tools\VOFC_Logs\model_manager.log`" -Wait" -ForegroundColor White
} else {
    Write-Host "❌ Failed to restart service" -ForegroundColor Red
    Write-Host "   Make sure you're running as Administrator" -ForegroundColor Yellow
    Write-Host "   Or try: .\scripts\fix-model-manager-paused.ps1" -ForegroundColor Yellow
}

