# Restart Flask Service
# Applies changes to routes and configuration

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Restarting Flask Service" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if NSSM is available
$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

# Check current status
Write-Host "1. Checking Flask service status..." -ForegroundColor Yellow
try {
    $status = & $nssmPath status "VOFC-Flask" 2>&1
    Write-Host "   Current status: $status" -ForegroundColor $(if ($status -match "RUNNING") { "Green" } else { "Yellow" })
} catch {
    Write-Host "   ⚠️  Could not check status: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""

# Restart service
Write-Host "2. Restarting Flask service..." -ForegroundColor Yellow
try {
    & $nssmPath restart "VOFC-Flask"
    Write-Host "   ✅ Flask service restart command sent" -ForegroundColor Green
    Write-Host "   Waiting 5 seconds for service to restart..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
} catch {
    Write-Host "   ❌ Failed to restart Flask: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   → Try running as Administrator" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Verify service is running
Write-Host "3. Verifying Flask is running..." -ForegroundColor Yellow
try {
    $newStatus = & $nssmPath status "VOFC-Flask" 2>&1
    if ($newStatus -match "RUNNING") {
        Write-Host "   ✅ Flask service is RUNNING" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Flask service status: $newStatus" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️  Could not verify status" -ForegroundColor Yellow
}

Write-Host ""

# Test endpoint
Write-Host "4. Testing Flask health endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
try {
    $response = Invoke-RestMethod -Uri "http://10.0.0.213:8080/api/system/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Flask is responding" -ForegroundColor Green
    Write-Host "   Status: $($response.flask)" -ForegroundColor Gray
} catch {
    Write-Host "   ⚠️  Flask not responding yet: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "   → Wait a few more seconds and try again" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Restart Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test logstream endpoint:" -ForegroundColor White
Write-Host "   http://10.0.0.213:8080/api/system/logstream" -ForegroundColor Yellow
Write-Host ""

