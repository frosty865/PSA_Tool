# Resume/Start Model Manager Service
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Resume VOFC-ModelManager Service" -ForegroundColor Cyan
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

# Check current status
Write-Host "Checking service status..." -ForegroundColor Yellow
$status = nssm status $serviceName 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Service '$serviceName' not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install the service first:" -ForegroundColor Yellow
    Write-Host "  .\scripts\install-model-manager-nssm.ps1" -ForegroundColor White
    exit 1
}

Write-Host "Current status: $status" -ForegroundColor Cyan
Write-Host ""

if ($status -eq "SERVICE_PAUSED") {
    Write-Host "Service is paused. Attempting to resume..." -ForegroundColor Yellow
    nssm resume $serviceName
    
    Start-Sleep -Seconds 2
    
    $newStatus = nssm status $serviceName 2>&1
    if ($newStatus -eq "SERVICE_RUNNING") {
        Write-Host "✅ Service resumed successfully!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Resume failed. Status: $newStatus" -ForegroundColor Yellow
        Write-Host "Attempting stop and start..." -ForegroundColor Yellow
        
        nssm stop $serviceName
        Start-Sleep -Seconds 2
        nssm start $serviceName
        Start-Sleep -Seconds 2
        
        $finalStatus = nssm status $serviceName 2>&1
        if ($finalStatus -eq "SERVICE_RUNNING") {
            Write-Host "✅ Service started successfully!" -ForegroundColor Green
        } else {
            Write-Host "❌ Service failed to start. Status: $finalStatus" -ForegroundColor Red
            Write-Host ""
            Write-Host "Check error logs:" -ForegroundColor Cyan
            Write-Host "  C:\Tools\ModelManager\service_error.log" -ForegroundColor White
            Write-Host "  C:\Tools\VOFC_Logs\model_manager.log" -ForegroundColor White
        }
    }
} elseif ($status -eq "SERVICE_STOPPED") {
    Write-Host "Service is stopped. Starting..." -ForegroundColor Yellow
    nssm start $serviceName
    
    Start-Sleep -Seconds 2
    
    $newStatus = nssm status $serviceName 2>&1
    if ($newStatus -eq "SERVICE_RUNNING") {
        Write-Host "✅ Service started successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Service failed to start. Status: $newStatus" -ForegroundColor Red
        Write-Host ""
        Write-Host "Check error logs:" -ForegroundColor Cyan
        Write-Host "  C:\Tools\ModelManager\service_error.log" -ForegroundColor White
        Write-Host "  C:\Tools\VOFC_Logs\model_manager.log" -ForegroundColor White
    }
} elseif ($status -eq "SERVICE_RUNNING") {
    Write-Host "Service is running. Restarting to pick up code changes..." -ForegroundColor Yellow
    nssm restart $serviceName 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    $newStatus = nssm status $serviceName 2>&1
    if ($newStatus -eq "SERVICE_RUNNING") {
        Write-Host "✅ Service restarted successfully!" -ForegroundColor Green
        Write-Host "The updated code should now read environment variables dynamically." -ForegroundColor Cyan
    } else {
        Write-Host "⚠️  Restart status: $newStatus" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Unknown status: $status" -ForegroundColor Yellow
    Write-Host "Attempting to start..." -ForegroundColor Yellow
    nssm start $serviceName
    Start-Sleep -Seconds 2
    $newStatus = nssm status $serviceName 2>&1
    Write-Host "New status: $newStatus" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Done" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

