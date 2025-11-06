# Backend Endpoint Diagnostic Script
# Tests all Flask endpoints to verify connectivity
# Follows the troubleshooting guide from the user

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PSA Tool Backend Diagnostic Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Test local Flask
Write-Host "🧩 Step 1: Confirm Flask backend is reachable" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow
Write-Host "Testing: curl http://localhost:8080/api/system/health" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/api/system/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✓ Local Flask is reachable" -ForegroundColor Green
    Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Gray
    $health = $response.Content | ConvertFrom-Json
    Write-Host "  Expected: {`"flask`":`"ok`",`"ollama`":`"ok`",`"supabase`":`"ok`",`"tunnel`":`"ok`"}" -ForegroundColor Gray
    Write-Host "  Actual Response:" -ForegroundColor Gray
    $health | ConvertTo-Json -Depth 3 | Write-Host -ForegroundColor Gray
    
    # Check individual components
    if ($health.flask -eq "ok") { Write-Host "  ✓ Flask: OK" -ForegroundColor Green } else { Write-Host "  ✗ Flask: $($health.flask)" -ForegroundColor Red }
    if ($health.ollama -eq "ok") { Write-Host "  ✓ Ollama: OK" -ForegroundColor Green } else { Write-Host "  ✗ Ollama: $($health.ollama)" -ForegroundColor Red }
    if ($health.supabase -eq "ok") { Write-Host "  ✓ Supabase: OK" -ForegroundColor Green } else { Write-Host "  ✗ Supabase: $($health.supabase)" -ForegroundColor Red }
    if ($health.tunnel -eq "ok") { Write-Host "  ✓ Tunnel: OK" -ForegroundColor Green } else { Write-Host "  ✗ Tunnel: $($health.tunnel)" -ForegroundColor Red }
} catch {
    Write-Host "✗ Local Flask is NOT reachable" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "  → Restart Flask service:" -ForegroundColor Yellow
    Write-Host "    nssm restart `"VOFC-Flask`"" -ForegroundColor White
    Write-Host ""
    Write-Host "  If that doesn't work, check:" -ForegroundColor Yellow
    Write-Host "    - Flask service status: Get-Service `"VOFC-Flask`"" -ForegroundColor White
    Write-Host "    - Flask logs: Get-Content `"C:\Tools\nssm\logs\vofc_flask.log`" -Tail 50" -ForegroundColor White
    exit 1
}
Write-Host ""

# Step 2: Check Next.js environment variables
Write-Host "🧩 Step 2: Check Next.js environment variables" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow
Write-Host "Looking for .env files..." -ForegroundColor Cyan

$envFiles = @(".env", ".env.local", ".env.production", ".env.development")
$foundEnv = $false

foreach ($envFile in $envFiles) {
    $envPath = Join-Path $PSScriptRoot "..\$envFile"
    if (Test-Path $envPath) {
        $foundEnv = $true
        Write-Host "  Found: $envFile" -ForegroundColor Green
        $content = Get-Content $envPath | Where-Object { $_ -match "FLASK" -or $_ -match "NEXT_PUBLIC" }
        if ($content) {
            Write-Host "  Relevant variables:" -ForegroundColor Gray
            $content | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        } else {
            Write-Host "  ⚠ No Flask-related variables found" -ForegroundColor Yellow
        }
    }
}

if (-not $foundEnv) {
    Write-Host "  ⚠ No .env files found" -ForegroundColor Yellow
    Write-Host "  → Create .env.local with:" -ForegroundColor Yellow
    Write-Host "    NEXT_PUBLIC_FLASK_URL=http://localhost:8080" -ForegroundColor White
    Write-Host "    NEXT_PUBLIC_FLASK_API_URL=http://localhost:8080/api" -ForegroundColor White
    Write-Host "    (Or use tunnel URL for production: https://flask.frostech.site)" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "  Expected variables:" -ForegroundColor Cyan
    Write-Host "    NEXT_PUBLIC_FLASK_URL=http://localhost:8080 (dev) or https://flask.frostech.site (prod)" -ForegroundColor Gray
    Write-Host "    NEXT_PUBLIC_FLASK_API_URL=http://localhost:8080/api (dev) or https://flask.frostech.site/api (prod)" -ForegroundColor Gray
}
Write-Host ""

# Step 3: Test tunnel endpoints directly
Write-Host "🧩 Step 3: Test backend endpoints directly" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow

$tunnelEndpoints = @(
    @{ Name = "Flask health"; Path = "/api/system/health"; Expected = "{`"flask`":`"ok`",...}" },
    @{ Name = "Learning stats"; Path = "/api/learning/stats"; Expected = "[{`"timestamp`":`"...`",`"accept_rate`":0.88,...}]" },
    @{ Name = "System events"; Path = "/api/system/events"; Expected = "[{`"timestamp`":`"...`",`"event_type`":`"model_retrain`",...}]" },
    @{ Name = "Model info"; Path = "/api/models/info"; Expected = "{`"name`":`"vofc-engine:latest`",`"size_gb`":4.4,...}" }
)

$allPassed = $true
foreach ($endpoint in $tunnelEndpoints) {
    $url = "https://flask.frostech.site$($endpoint.Path)"
    Write-Host "Testing: $($endpoint.Name)" -ForegroundColor Cyan
    Write-Host "  URL: $url" -ForegroundColor Gray
    Write-Host "  Expected: $($endpoint.Expected)" -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 10 -ErrorAction Stop
        Write-Host "  ✓ Success (Status: $($response.StatusCode))" -ForegroundColor Green
        
        # Try to parse JSON
        try {
            $json = $response.Content | ConvertFrom-Json
            if ($json -is [Array]) {
                Write-Host "  Response: Array with $($json.Count) items" -ForegroundColor Gray
            } else {
                Write-Host "  Response: $($response.Content.Substring(0, [Math]::Min(200, $response.Content.Length)))..." -ForegroundColor Gray
            }
        } catch {
            Write-Host "  Response: $($response.Content.Substring(0, [Math]::Min(200, $response.Content.Length)))..." -ForegroundColor Gray
        }
    } catch {
        $allPassed = $false
        $statusCode = $null
        try {
            $statusCode = $_.Exception.Response.StatusCode.value__
        } catch {}
        
        if ($statusCode -eq 502) {
            Write-Host "  ✗ 502 Bad Gateway - Tunnel may be down or Flask not running" -ForegroundColor Red
            Write-Host "    → Check tunnel service: nssm status `"VOFC-Tunnel`"" -ForegroundColor Yellow
        } elseif ($statusCode -eq 404) {
            Write-Host "  ✗ 404 Not Found - Route may not be registered in Flask" -ForegroundColor Red
            Write-Host "    → Verify route exists in routes/*.py files" -ForegroundColor Yellow
        } elseif ($statusCode) {
            Write-Host "  ✗ Error: HTTP $statusCode - $($_.Exception.Message)" -ForegroundColor Red
        } else {
            Write-Host "  ✗ Connection failed: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "    → Check tunnel connectivity or DNS" -ForegroundColor Yellow
        }
    }
    Write-Host ""
}

# Step 4: Verify routes are registered in Flask
Write-Host "🧩 Step 4: Verify routes are registered in Flask" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow
Write-Host "Checking app.py for registered blueprints..." -ForegroundColor Cyan

$appPyPath = Join-Path $PSScriptRoot "..\app.py"
if (Test-Path $appPyPath) {
    $content = Get-Content $appPyPath -Raw
    $requiredBlueprints = @(
        @{ Name = "system_bp"; Route = "/api/system/health"; File = "routes.system" },
        @{ Name = "models_bp"; Route = "/api/models/info, /api/system/events"; File = "routes.models" },
        @{ Name = "learning_bp"; Route = "/api/learning/stats"; File = "routes.learning" }
    )
    
    foreach ($bp in $requiredBlueprints) {
        if ($content -match "from routes\.(system|models|learning)") {
            # Check if blueprint is imported
            $importPattern = "from routes\.(system|models|learning)"
            if ($content -match "from routes\.$($bp.Name.Replace('_bp', ''))") {
                Write-Host "  ✓ $($bp.Name) is imported" -ForegroundColor Green
            }
        }
        
        if ($content -match "register_blueprint\($($bp.Name)\)") {
            Write-Host "  ✓ $($bp.Name) is registered" -ForegroundColor Green
            Write-Host "    Routes: $($bp.Route)" -ForegroundColor Gray
        } else {
            Write-Host "  ✗ $($bp.Name) is NOT registered" -ForegroundColor Red
            Write-Host "    → Add: app.register_blueprint($($bp.Name))" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  ⚠ app.py not found at expected location: $appPyPath" -ForegroundColor Yellow
}
Write-Host ""

# Step 5: Check NSSM service status
Write-Host "🧩 Step 5: Check NSSM service status" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow

$services = @("VOFC-Flask", "VOFC-Ollama", "VOFC-Tunnel")
$allServicesRunning = $true
foreach ($service in $services) {
    try {
        $status = Get-Service -Name $service -ErrorAction Stop
        $statusText = if ($status.Status -eq "Running") { "✓ Running" } else { "✗ $($status.Status)" }
        $color = if ($status.Status -eq "Running") { "Green" } else { "Red" }
        Write-Host "$service : $statusText" -ForegroundColor $color
        if ($status.Status -ne "Running") {
            $allServicesRunning = $false
            Write-Host "  → Start service: Start-Service `"$service`"" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "$service : ✗ Not found" -ForegroundColor Red
        $allServicesRunning = $false
    }
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Diagnostic Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($allPassed -and $allServicesRunning) {
    Write-Host "✓ All checks passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Expected healthy response pattern:" -ForegroundColor Cyan
    Write-Host "  /api/models/info     → {`"name`":`"vofc-engine:latest`",`"size_gb`":4.4,`"version`":`"latest`"}" -ForegroundColor Gray
    Write-Host "  /api/system/health  → {`"flask`":`"ok`",`"ollama`":`"ok`",`"supabase`":`"ok`",`"tunnel`":`"ok`"}" -ForegroundColor Gray
    Write-Host "  /api/learning/stats → [{`"timestamp`":`"...`",`"accept_rate`":0.88,...}]" -ForegroundColor Gray
    Write-Host "  /api/system/events  → [{`"timestamp`":`"...`",`"event_type`":`"model_retrain`",...}]" -ForegroundColor Gray
} else {
    Write-Host "✗ Some issues detected. Review the output above." -ForegroundColor Red
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. If local Flask fails, restart: nssm restart `"VOFC-Flask`"" -ForegroundColor White
    Write-Host "2. If tunnel endpoints fail, check tunnel: nssm status `"VOFC-Tunnel`"" -ForegroundColor White
    Write-Host "3. Verify environment variables in .env file" -ForegroundColor White
    Write-Host "4. Check Flask logs: Get-Content `"C:\Tools\nssm\logs\vofc_flask.log`" -Tail 50" -ForegroundColor White
    Write-Host "5. Check Admin Panel console errors (F12 → Network tab)" -ForegroundColor White
}
Write-Host ""

