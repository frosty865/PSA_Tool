# Verify Logstream Route is Available
# Tests if the route is accessible after Flask restart

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Logstream Route Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check if route exists in code
Write-Host "1. Checking if route exists in code..." -ForegroundColor Yellow
$routeFile = "C:\Tools\VOFC-Flask\routes\system.py"
if (Test-Path $routeFile) {
    $content = Get-Content $routeFile -Raw
    if ($content -match "@system_bp\.route\(['\`"]/api/system/logstream['\`"]") {
        Write-Host "   ✅ Route found in routes/system.py" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Route NOT found in routes/system.py" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "   ❌ routes/system.py not found" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 2: Check Flask service status
Write-Host "2. Checking Flask service status..." -ForegroundColor Yellow
$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

try {
    $status = & $nssmPath status "VOFC-Flask" 2>&1
    if ($status -match "RUNNING") {
        Write-Host "   ✅ Flask service is RUNNING" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Flask service status: $status" -ForegroundColor Yellow
        Write-Host "   → Start with: nssm start `"VOFC-Flask`"" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ⚠️  Could not check status" -ForegroundColor Yellow
}

Write-Host ""

# Test 3: Test health endpoint (verify Flask is responding)
Write-Host "3. Testing Flask health endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://10.0.0.213:8080/api/system/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Flask is responding" -ForegroundColor Green
    Write-Host "   Status: $($health.flask)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Flask is NOT responding" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   → Flask may not be running or not accessible" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Test 4: Test logstream endpoint
Write-Host "4. Testing logstream endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://10.0.0.213:8080/api/system/logstream" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Logstream endpoint is accessible!" -ForegroundColor Green
    Write-Host "   Status Code: $($response.StatusCode)" -ForegroundColor Gray
    Write-Host "   Content Type: $($response.Headers['Content-Type'])" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 404) {
        Write-Host "   ❌ 404 Not Found - Route not loaded" -ForegroundColor Red
        Write-Host "   → Flask needs to be restarted to load the new route" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   Restart Flask (run as Administrator):" -ForegroundColor White
        Write-Host "   nssm restart `"VOFC-Flask`"" -ForegroundColor Yellow
    } else {
        Write-Host "   ❌ Error: HTTP $statusCode" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "If you see 404, restart Flask as Administrator:" -ForegroundColor White
Write-Host "  nssm restart `"VOFC-Flask`"" -ForegroundColor Yellow
Write-Host ""

