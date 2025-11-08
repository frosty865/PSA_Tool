# Fix VOFC-AutoRetrain service if it's in PAUSED state
# This script resumes a paused service and verifies it's running

$SERVICE_NAME = "VOFC-AutoRetrain"

Write-Host "=== Checking VOFC-AutoRetrain Service Status ===" -ForegroundColor Cyan
Write-Host ""

# Check current status
$status = sc query $SERVICE_NAME
Write-Host "Current service status:" -ForegroundColor Yellow
Write-Host $status
Write-Host ""

# Check if service is paused
if ($status -match "PAUSED|PAUSE_PENDING") {
    Write-Host "⚠️  Service is PAUSED. Attempting to resume..." -ForegroundColor Yellow
    
    # Try to resume the service
    $resumeResult = nssm resume $SERVICE_NAME
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Resume command executed successfully" -ForegroundColor Green
        Start-Sleep -Seconds 2
        
        # Check status again
        $newStatus = sc query $SERVICE_NAME
        Write-Host "`nNew service status:" -ForegroundColor Yellow
        Write-Host $newStatus
        
        if ($newStatus -match "RUNNING") {
            Write-Host "`n✅ Service is now RUNNING" -ForegroundColor Green
        } else {
            Write-Host "`n⚠️  Service is not running. Attempting stop/start..." -ForegroundColor Yellow
            
            # Stop the service
            nssm stop $SERVICE_NAME
            Start-Sleep -Seconds 3
            
            # Start the service
            nssm start $SERVICE_NAME
            Start-Sleep -Seconds 2
            
            # Check final status
            $finalStatus = sc query $SERVICE_NAME
            Write-Host "`nFinal service status:" -ForegroundColor Yellow
            Write-Host $finalStatus
            
            if ($finalStatus -match "RUNNING") {
                Write-Host "`n✅ Service is now RUNNING" -ForegroundColor Green
            } else {
                Write-Host "`n❌ Service failed to start. Check logs:" -ForegroundColor Red
                Write-Host "  C:\Tools\VOFC_Logs\auto_retrain_job.log" -ForegroundColor White
                Write-Host "  C:\Tools\VOFC_Logs\autoretrain_stderr.log" -ForegroundColor White
            }
        }
    } else {
        Write-Host "❌ Failed to resume service. Attempting stop/start..." -ForegroundColor Red
        
        # Stop the service
        nssm stop $SERVICE_NAME
        Start-Sleep -Seconds 3
        
        # Start the service
        nssm start $SERVICE_NAME
        Start-Sleep -Seconds 2
        
        # Check status
        $finalStatus = sc query $SERVICE_NAME
        Write-Host "`nService status after restart:" -ForegroundColor Yellow
        Write-Host $finalStatus
        
        if ($finalStatus -match "RUNNING") {
            Write-Host "`n✅ Service is now RUNNING" -ForegroundColor Green
        } else {
            Write-Host "`n❌ Service failed to start. Check logs:" -ForegroundColor Red
            Write-Host "  C:\Tools\VOFC_Logs\auto_retrain_job.log" -ForegroundColor White
            Write-Host "  C:\Tools\VOFC_Logs\autoretrain_stderr.log" -ForegroundColor White
        }
    }
} elseif ($status -match "RUNNING") {
    Write-Host "✅ Service is already RUNNING" -ForegroundColor Green
} elseif ($status -match "STOPPED|STOP_PENDING") {
    Write-Host "⚠️  Service is STOPPED. Starting service..." -ForegroundColor Yellow
    nssm start $SERVICE_NAME
    Start-Sleep -Seconds 2
    
    $newStatus = sc query $SERVICE_NAME
    Write-Host "`nService status:" -ForegroundColor Yellow
    Write-Host $newStatus
    
    if ($newStatus -match "RUNNING") {
        Write-Host "`n✅ Service is now RUNNING" -ForegroundColor Green
    } else {
        Write-Host "`n❌ Service failed to start. Check logs:" -ForegroundColor Red
        Write-Host "  C:\Tools\VOFC_Logs\auto_retrain_job.log" -ForegroundColor White
        Write-Host "  C:\Tools\VOFC_Logs\autoretrain_stderr.log" -ForegroundColor White
    }
} else {
    Write-Host "⚠️  Unknown service state. Attempting to start..." -ForegroundColor Yellow
    nssm start $SERVICE_NAME
    Start-Sleep -Seconds 2
    
    $newStatus = sc query $SERVICE_NAME
    Write-Host "`nService status:" -ForegroundColor Yellow
    Write-Host $newStatus
}

# Verify auto-start and restart configuration
Write-Host "`n=== Verifying Service Configuration ===" -ForegroundColor Cyan
$startType = nssm get $SERVICE_NAME Start
$exitAction = nssm get $SERVICE_NAME AppExit

Write-Host "Start Type: $startType" -ForegroundColor Gray
Write-Host "Exit Action: $exitAction" -ForegroundColor Gray

if ($startType -notmatch "SERVICE_AUTO_START") {
    Write-Host "`n⚠️  Setting Start Type to SERVICE_AUTO_START..." -ForegroundColor Yellow
    nssm set $SERVICE_NAME Start SERVICE_AUTO_START
}

if ($exitAction -notmatch "Restart") {
    Write-Host "`n⚠️  Setting Exit Action to Restart..." -ForegroundColor Yellow
    nssm set $SERVICE_NAME AppExit Default Restart
}

Write-Host "`n=== Done ===" -ForegroundColor Green

