# Restart VOFC Model Manager Service
# Run this script as Administrator

$serviceName = "VOFC-ModelManager"

Write-Host "Restarting $serviceName..." -ForegroundColor Yellow

nssm restart $serviceName

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Service restarted successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting 3 seconds for service to start..." -ForegroundColor Cyan
    Start-Sleep -Seconds 3
    
    $status = nssm status $serviceName 2>&1
    if ($status -eq "SERVICE_RUNNING") {
        Write-Host "✅ Service is running" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Service status: $status" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Check logs:" -ForegroundColor Cyan
    Write-Host "  Get-Content -Path `"C:\Tools\VOFC_Logs\model_manager.log`" -Wait" -ForegroundColor White
} else {
    Write-Host "❌ Failed to restart service" -ForegroundColor Red
    Write-Host "   Make sure you're running as Administrator" -ForegroundColor Yellow
}

