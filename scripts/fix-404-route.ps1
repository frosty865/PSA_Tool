# Fix 404 Route Issue
# The /api/system/control route exists but returns 404
# This script helps diagnose and fix the issue

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fixing 404 Route Issue" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify route exists in code
Write-Host "Step 1: Verifying route exists in code..." -ForegroundColor Yellow
$routeFile = "routes\system.py"
if (Test-Path $routeFile) {
    $content = Get-Content $routeFile -Raw
    if ($content -match "@system_bp\.route\(.*/api/system/control") {
        Write-Host "  [OK] Route found in routes/system.py" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Route NOT found in routes/system.py" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [ERROR] routes/system.py not found" -ForegroundColor Red
    exit 1
}

# Step 2: Verify blueprint is registered
Write-Host "Step 2: Verifying blueprint registration..." -ForegroundColor Yellow
$appFile = "app.py"
if (Test-Path $appFile) {
    $content = Get-Content $appFile -Raw
    if ($content -match "register_blueprint\(system_bp\)") {
        Write-Host "  [OK] system_bp is registered in app.py" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] system_bp NOT registered in app.py" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [ERROR] app.py not found" -ForegroundColor Red
    exit 1
}

# Step 3: Check Flask service status
Write-Host "Step 3: Checking Flask service status..." -ForegroundColor Yellow
try {
    $service = Get-Service -Name "VOFC-Flask" -ErrorAction Stop
    Write-Host "  Service status: $($service.Status)" -ForegroundColor $(if ($service.Status -eq "Running") { "Green" } else { "Yellow" })
    
    if ($service.Status -ne "Running") {
        Write-Host "  [WARN] Flask service is not running" -ForegroundColor Yellow
        Write-Host "  Starting Flask service..." -ForegroundColor Cyan
        Start-Service -Name "VOFC-Flask"
        Start-Sleep -Seconds 3
    }
} catch {
    Write-Host "  [ERROR] Flask service not found: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  You may need to create the service with NSSM" -ForegroundColor Yellow
}

# Step 4: Restart Flask to pick up route changes
Write-Host "Step 4: Restarting Flask to pick up route changes..." -ForegroundColor Yellow
try {
    Write-Host "  Restarting VOFC-Flask service..." -ForegroundColor Cyan
    Restart-Service -Name "VOFC-Flask" -ErrorAction Stop
    Write-Host "  [OK] Flask service restarted" -ForegroundColor Green
    Write-Host "  Waiting 5 seconds for Flask to start..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5
} catch {
    Write-Host "  [ERROR] Failed to restart Flask: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Try manually: nssm restart `"VOFC-Flask`"" -ForegroundColor Yellow
}

# Step 5: Test the endpoint
Write-Host "Step 5: Testing the endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
try {
    $body = @{action='process_existing'} | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "http://localhost:8080/api/system/control" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
    Write-Host "  [OK] Endpoint is now accessible!" -ForegroundColor Green
    Write-Host "  Response: $($response.message)" -ForegroundColor Gray
} catch {
    $statusCode = $null
    try {
        $statusCode = $_.Exception.Response.StatusCode.value__
    } catch {}
    
    if ($statusCode -eq 404) {
        Write-Host "  [ERROR] Still getting 404 - route may not be loaded" -ForegroundColor Red
        Write-Host "  Check Flask logs: Get-Content `"C:\Tools\nssm\logs\vofc_flask.log`" -Tail 50" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Possible issues:" -ForegroundColor Yellow
        Write-Host "  1. Flask may need more time to start" -ForegroundColor White
        Write-Host "  2. There may be an import error preventing the route from loading" -ForegroundColor White
        Write-Host "  3. Check if ollama_auto_processor.py is in the Python path" -ForegroundColor White
    } else {
        Write-Host "  [ERROR] Request failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Done" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

