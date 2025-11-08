# Fix Model Manager Service
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix VOFC-ModelManager Service" -ForegroundColor Cyan
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

# Check service status
Write-Host "Checking service status..." -ForegroundColor Yellow
$status = nssm status VOFC-ModelManager 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "Current status: $status" -ForegroundColor Cyan
    Write-Host ""
    
    # Try to resume if paused
    if ($status -eq "SERVICE_PAUSED") {
        Write-Host "Service is paused. Attempting to resume..." -ForegroundColor Yellow
        nssm resume VOFC-ModelManager
        Start-Sleep -Seconds 2
        
        $newStatus = nssm status VOFC-ModelManager 2>&1
        if ($newStatus -eq "SERVICE_RUNNING") {
            Write-Host "✅ Service resumed successfully!" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Service status: $newStatus" -ForegroundColor Yellow
            Write-Host "Attempting to restart..." -ForegroundColor Yellow
            
            nssm stop VOFC-ModelManager
            Start-Sleep -Seconds 2
            nssm start VOFC-ModelManager
            Start-Sleep -Seconds 2
            
            $finalStatus = nssm status VOFC-ModelManager 2>&1
            if ($finalStatus -eq "SERVICE_RUNNING") {
                Write-Host "✅ Service restarted successfully!" -ForegroundColor Green
            } else {
                Write-Host "❌ Service failed to start. Status: $finalStatus" -ForegroundColor Red
                Write-Host ""
                Write-Host "You may need to reinstall the service:" -ForegroundColor Yellow
                Write-Host "  nssm remove VOFC-ModelManager confirm" -ForegroundColor White
                Write-Host "  nssm install VOFC-ModelManager `"C:\Program Files\Python311\python.exe`" `"C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\services\model_manager.py`"" -ForegroundColor White
            }
        }
    } elseif ($status -eq "SERVICE_STOPPED") {
        Write-Host "Service is stopped. Starting..." -ForegroundColor Yellow
        nssm start VOFC-ModelManager
        Start-Sleep -Seconds 2
        
        $newStatus = nssm status VOFC-ModelManager 2>&1
        if ($newStatus -eq "SERVICE_RUNNING") {
            Write-Host "✅ Service started successfully!" -ForegroundColor Green
        } else {
            Write-Host "❌ Service failed to start. Status: $newStatus" -ForegroundColor Red
        }
    } elseif ($status -eq "SERVICE_RUNNING") {
        Write-Host "✅ Service is already running!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Unknown service status: $status" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Service 'VOFC-ModelManager' not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install the service with:" -ForegroundColor Yellow
    Write-Host "  nssm install VOFC-ModelManager `"C:\Program Files\Python311\python.exe`" `"C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\services\model_manager.py`"" -ForegroundColor White
    Write-Host "  nssm set VOFC-ModelManager AppDirectory `"C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool`"" -ForegroundColor White
    Write-Host "  nssm set VOFC-ModelManager Start SERVICE_AUTO_START" -ForegroundColor White
    Write-Host "  nssm start VOFC-ModelManager" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Done" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

