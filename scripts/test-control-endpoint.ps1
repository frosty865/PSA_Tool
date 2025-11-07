# Test Control Endpoint
# Tests if /api/system/control is accessible

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing Control Endpoint" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Test locally
Write-Host "1. Testing Flask locally (http://10.0.0.213:8080)..." -ForegroundColor Yellow
try {
    $body = @{action='start_watcher'} | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "http://10.0.0.213:8080/api/system/control" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Flask control endpoint is responding locally" -ForegroundColor Green
    Write-Host "   Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    if ($statusCode -eq 404) {
        Write-Host "   ❌ Control endpoint returned 404" -ForegroundColor Red
        Write-Host "   → Route not found. Flask may need to be restarted." -ForegroundColor Yellow
    } elseif ($statusCode) {
        Write-Host "   ❌ Control endpoint returned HTTP $statusCode" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    } else {
        Write-Host "   ❌ Failed to connect: $($_.Exception.Message)" -ForegroundColor Red
    }
}
Write-Host ""

# Test 2: Test through tunnel
Write-Host "2. Testing Flask through tunnel (https://flask.frostech.site)..." -ForegroundColor Yellow
try {
    $body = @{action='start_watcher'} | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "https://flask.frostech.site/api/system/control" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Flask control endpoint is accessible through tunnel" -ForegroundColor Green
    Write-Host "   Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.Value__
    if ($statusCode -eq 404) {
        Write-Host "   ❌ Control endpoint returned 404 through tunnel" -ForegroundColor Red
        Write-Host "   → Route not found. Flask may need to be restarted." -ForegroundColor Yellow
    } elseif ($statusCode -eq 502) {
        Write-Host "   ❌ Tunnel returned 502 Bad Gateway" -ForegroundColor Red
        Write-Host "   → Tunnel is running but can't reach Flask" -ForegroundColor Yellow
    } else {
        Write-Host "   ❌ Failed: HTTP $statusCode" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}
Write-Host ""

# Test 3: Check if route exists in file
Write-Host "3. Checking if route exists in Flask code..." -ForegroundColor Yellow
$routeFile = "C:\Tools\VOFC-Flask\routes\system.py"
if (Test-Path $routeFile) {
    $content = Get-Content $routeFile -Raw
    if ($content -match "@system_bp\.route\(.*/api/system/control") {
        Write-Host "   ✅ Route found in $routeFile" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Route NOT found in $routeFile" -ForegroundColor Red
    }
} else {
    Write-Host "   ❌ Route file not found: $routeFile" -ForegroundColor Red
}
Write-Host ""

# Test 4: Check Flask service status
Write-Host "4. Checking Flask service status..." -ForegroundColor Yellow
try {
    $status = & nssm status "VOFC-Flask" 2>&1
    if ($status -match "RUNNING") {
        Write-Host "   ✅ Flask service is RUNNING" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Flask service status: $status" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Could not check Flask service status" -ForegroundColor Red
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Recommended Actions:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If the endpoint returns 404:" -ForegroundColor White
Write-Host "  1. Restart Flask as Administrator:" -ForegroundColor Yellow
Write-Host "     nssm restart `"VOFC-Flask`"" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Wait 10 seconds, then test again:" -ForegroundColor Yellow
Write-Host "     .\scripts\test-control-endpoint.ps1" -ForegroundColor Cyan
Write-Host ""

