# Test Tunnel Connection to Flask
# Diagnoses why tunnel returns 502 even when Flask is working

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tunnel Connection Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Flask locally
Write-Host "1. Testing Flask locally (http://localhost:8080)..." -ForegroundColor Yellow
try {
    $localResponse = Invoke-RestMethod -Uri "http://localhost:8080/api/system/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   ✅ Flask is responding locally" -ForegroundColor Green
    Write-Host "   Response: $($localResponse | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Flask is NOT responding locally" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   → Flask may not be running or not listening on port 8080" -ForegroundColor Yellow
    exit
}

Write-Host ""

# Test 2: Flask through tunnel
Write-Host "2. Testing Flask through tunnel (https://flask.frostech.site)..." -ForegroundColor Yellow
try {
    $tunnelResponse = Invoke-RestMethod -Uri "https://flask.frostech.site/api/system/health" -TimeoutSec 10 -ErrorAction Stop
    Write-Host "   ✅ Flask is accessible through tunnel" -ForegroundColor Green
    Write-Host "   Response: $($tunnelResponse | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "   ❌ Tunnel test failed: HTTP $statusCode" -ForegroundColor Red
    
    if ($statusCode -eq 502) {
        Write-Host "   → 502 Bad Gateway: Tunnel is running but can't reach Flask" -ForegroundColor Yellow
        Write-Host "   → Possible causes:" -ForegroundColor Yellow
        Write-Host "     1. Tunnel config points to wrong port" -ForegroundColor White
        Write-Host "     2. Flask not listening on 127.0.0.1:8080 (only listening on specific interface)" -ForegroundColor White
        Write-Host "     3. Firewall blocking tunnel→Flask connection" -ForegroundColor White
        Write-Host "     4. Tunnel needs restart to pick up config changes" -ForegroundColor White
    } elseif ($statusCode -eq 503) {
        Write-Host "   → 503 Service Unavailable: Tunnel service may be misconfigured" -ForegroundColor Yellow
    } else {
        Write-Host "   → Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""

# Test 3: Check Flask listening on port 8080
Write-Host "3. Checking if Flask is listening on port 8080..." -ForegroundColor Yellow
$listening = netstat -ano | findstr ":8080" | findstr "LISTENING"
if ($listening) {
    Write-Host "   ✅ Port 8080 is in LISTENING state" -ForegroundColor Green
    Write-Host "   $listening" -ForegroundColor Gray
} else {
    Write-Host "   ❌ Port 8080 is NOT in LISTENING state" -ForegroundColor Red
    Write-Host "   → Flask may not be bound to port 8080" -ForegroundColor Yellow
}

Write-Host ""

# Test 4: Check tunnel config
Write-Host "4. Checking tunnel configuration..." -ForegroundColor Yellow
$configPath = "C:\Users\frost\cloudflared\config.yml"
if (Test-Path $configPath) {
    Write-Host "   ✅ Config file found: $configPath" -ForegroundColor Green
    $config = Get-Content $configPath -Raw
    if ($config -match "flask\.frostech\.site") {
        Write-Host "   ✅ Config contains flask.frostech.site" -ForegroundColor Green
        if ($config -match "localhost:8080" -or $config -match "127\.0\.0\.1:8080") {
            Write-Host "   ✅ Config points to localhost:8080" -ForegroundColor Green
        } else {
            Write-Host "   ❌ Config does NOT point to localhost:8080" -ForegroundColor Red
            Write-Host "   → Tunnel may be pointing to wrong port/URL" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ⚠️  Config does not contain flask.frostech.site" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ❌ Config file not found: $configPath" -ForegroundColor Red
    Write-Host "   → Check tunnel configuration" -ForegroundColor Yellow
}

Write-Host ""

# Test 5: Check tunnel logs for errors
Write-Host "5. Checking recent tunnel logs..." -ForegroundColor Yellow
$logPath = "C:\Users\frost\cloudflared\logs\cloudflared.log"
if (Test-Path $logPath) {
    $recentLogs = Get-Content $logPath -Tail 20 -ErrorAction SilentlyContinue
    if ($recentLogs) {
        $errorLogs = $recentLogs | Select-String -Pattern "error|failed|502|connect|dial" -CaseSensitive:$false
        if ($errorLogs) {
            Write-Host "   ⚠️  Found potential errors in logs:" -ForegroundColor Yellow
            $errorLogs | ForEach-Object { Write-Host "   $_" -ForegroundColor Red }
        } else {
            Write-Host "   ✅ No obvious errors in recent logs" -ForegroundColor Green
        }
    }
} else {
    Write-Host "   ⚠️  Log file not found: $logPath" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Recommended Actions:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Restart tunnel to pick up any config changes:" -ForegroundColor White
Write-Host "   nssm restart `"VOFC-Tunnel`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Verify Flask is listening on all interfaces (0.0.0.0:8080):" -ForegroundColor White
Write-Host "   netstat -ano | findstr :8080" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Check tunnel logs for connection errors:" -ForegroundColor White
Write-Host "   Get-Content `"C:\Users\frost\cloudflared\logs\cloudflared.log`" -Tail 50" -ForegroundColor Yellow
Write-Host ""

