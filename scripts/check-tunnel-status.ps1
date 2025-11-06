# Check Tunnel and Flask Service Status
# Diagnoses 502 Bad Gateway errors

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tunnel & Flask Service Status Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Flask Service
Write-Host "1. Checking Flask Service (VOFC-Flask)..." -ForegroundColor Yellow
try {
    $flaskStatus = Get-Service "VOFC-Flask" -ErrorAction Stop
    if ($flaskStatus.Status -eq 'Running') {
        Write-Host "   ✅ Flask service is RUNNING" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Flask service is $($flaskStatus.Status)" -ForegroundColor Red
        Write-Host "   → Restart with: nssm restart `"VOFC-Flask`"" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Flask service not found" -ForegroundColor Red
    Write-Host "   → Install with: nssm install `"VOFC-Flask`" ..." -ForegroundColor Yellow
}

Write-Host ""

# Check Tunnel Service
Write-Host "2. Checking Tunnel Service (VOFC-Tunnel)..." -ForegroundColor Yellow
try {
    $tunnelStatus = Get-Service "VOFC-Tunnel" -ErrorAction Stop
    if ($tunnelStatus.Status -eq 'Running') {
        Write-Host "   ✅ Tunnel service is RUNNING" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Tunnel service is $($tunnelStatus.Status)" -ForegroundColor Red
        Write-Host "   → Restart with: nssm restart `"VOFC-Tunnel`"" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Tunnel service not found" -ForegroundColor Red
    Write-Host "   → Install with: nssm install `"VOFC-Tunnel`" ..." -ForegroundColor Yellow
}

Write-Host ""

# Test Flask locally
Write-Host "3. Testing Flask locally (http://localhost:8080)..." -ForegroundColor Yellow
try {
    $localResponse = Invoke-RestMethod -Uri "http://localhost:8080/api/system/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Flask is responding locally" -ForegroundColor Green
    Write-Host "   Status: $($localResponse.flask)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Flask is NOT responding locally" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   → Check Flask logs: Get-Content `"C:\Tools\nssm\logs\vofc_flask.log`" -Tail 50" -ForegroundColor Yellow
    Write-Host "   → Restart Flask: nssm restart `"VOFC-Flask`"" -ForegroundColor Yellow
}

Write-Host ""

# Test Flask through tunnel
Write-Host "4. Testing Flask through tunnel (https://flask.frostech.site)..." -ForegroundColor Yellow
try {
    $tunnelResponse = Invoke-RestMethod -Uri "https://flask.frostech.site/api/system/health" -TimeoutSec 10 -ErrorAction Stop
    Write-Host "   ✅ Flask is accessible through tunnel" -ForegroundColor Green
    Write-Host "   Status: $($tunnelResponse.flask)" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    if ($statusCode -eq 502) {
        Write-Host "   ❌ 502 Bad Gateway - Tunnel is up but Flask is not responding" -ForegroundColor Red
        Write-Host "   → Flask service may be stopped" -ForegroundColor Yellow
        Write-Host "   → Restart Flask: nssm restart `"VOFC-Flask`"" -ForegroundColor Yellow
    } elseif ($statusCode -eq 503) {
        Write-Host "   ❌ 503 Service Unavailable - Tunnel may be down" -ForegroundColor Red
        Write-Host "   → Restart tunnel: nssm restart `"VOFC-Tunnel`"" -ForegroundColor Yellow
    } else {
        Write-Host "   ❌ Tunnel test failed: HTTP $statusCode" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "   → Check tunnel logs: Get-Content `"C:\Users\frost\cloudflared\logs\cloudflared.log`" -Tail 50" -ForegroundColor Yellow
    }
}

Write-Host ""

# Check NSSM status
Write-Host "5. Checking NSSM service status..." -ForegroundColor Yellow
try {
    $nssmPath = "C:\Tools\nssm\nssm.exe"
    if (Test-Path $nssmPath) {
        Write-Host "   Checking VOFC-Flask..." -ForegroundColor Gray
        $flaskNssm = & $nssmPath status "VOFC-Flask" 2>&1
        Write-Host "   $flaskNssm" -ForegroundColor $(if ($flaskNssm -match "SERVICE_RUNNING") { "Green" } else { "Red" })
        
        Write-Host "   Checking VOFC-Tunnel..." -ForegroundColor Gray
        $tunnelNssm = & $nssmPath status "VOFC-Tunnel" 2>&1
        Write-Host "   $tunnelNssm" -ForegroundColor $(if ($tunnelNssm -match "SERVICE_RUNNING") { "Green" } else { "Red" })
    } else {
        Write-Host "   ⚠️  NSSM not found at $nssmPath" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️  Could not check NSSM status: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Quick Fix Commands:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Restart Flask:  nssm restart `"VOFC-Flask`"" -ForegroundColor White
Write-Host "Restart Tunnel: nssm restart `"VOFC-Tunnel`"" -ForegroundColor White
Write-Host "Restart All:    nssm restart `"VOFC-Flask`"; nssm restart `"VOFC-Tunnel`"" -ForegroundColor White
Write-Host ""

