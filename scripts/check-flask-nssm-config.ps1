# Check NSSM Flask Service Configuration
# Identifies which Flask instance is running and how it's configured

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NSSM Flask Service Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check NSSM path
$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

Write-Host "1. Checking Flask service configuration..." -ForegroundColor Yellow
try {
    # Get application path
    $appPath = & $nssmPath get "VOFC-Flask" AppDirectory 2>$null
    $exePath = & $nssmPath get "VOFC-Flask" AppExe 2>$null
    $args = & $nssmPath get "VOFC-Flask" AppParameters 2>$null
    
    Write-Host "   Application Directory: $appPath" -ForegroundColor Green
    Write-Host "   Executable: $exePath" -ForegroundColor Green
    Write-Host "   Parameters: $args" -ForegroundColor Green
    Write-Host ""
    
    # Check if app.py exists in that directory
    if ($appPath) {
        $appPyPath = Join-Path $appPath "app.py"
        if (Test-Path $appPyPath) {
            Write-Host "2. Checking app.py in service directory..." -ForegroundColor Yellow
            Write-Host "   ✅ Found: $appPyPath" -ForegroundColor Green
            
            # Check if it has host="0.0.0.0"
            $appContent = Get-Content $appPyPath -Raw
            if ($appContent -match 'host\s*=\s*["'']0\.0\.0\.0["'']') {
                Write-Host "   ✅ Configured to listen on 0.0.0.0" -ForegroundColor Green
            } elseif ($appContent -match 'host\s*=\s*["'']127\.0\.0\.1["'']') {
                Write-Host "   ❌ Configured to listen on 127.0.0.1 (localhost only)" -ForegroundColor Red
                Write-Host "   → This prevents tunnel from connecting" -ForegroundColor Yellow
            } else {
                Write-Host "   ⚠️  Host configuration not found or unclear" -ForegroundColor Yellow
            }
        } else {
            Write-Host "   ⚠️  app.py not found in service directory" -ForegroundColor Yellow
        }
    }
    
    # Check environment variables
    Write-Host ""
    Write-Host "3. Checking environment variables..." -ForegroundColor Yellow
    $envVars = & $nssmPath get "VOFC-Flask" AppEnvironmentExtra 2>$null
    if ($envVars) {
        Write-Host "   Environment variables:" -ForegroundColor Green
        $envVars | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
    } else {
        Write-Host "   ⚠️  No extra environment variables set" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "   ❌ Error checking NSSM configuration: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix Options:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If Flask is listening on 127.0.0.1 instead of 0.0.0.0:" -ForegroundColor White
Write-Host ""
Write-Host "Option 1: Update app.py in the service directory" -ForegroundColor Yellow
Write-Host "   Edit the app.py file in the service directory and change:" -ForegroundColor White
Write-Host "   app.run(host='127.0.0.1', ...)  →  app.run(host='0.0.0.0', ...)" -ForegroundColor Gray
Write-Host ""
Write-Host "Option 2: Set environment variable in NSSM" -ForegroundColor Yellow
Write-Host "   nssm set VOFC-Flask AppEnvironmentExtra FLASK_HOST=0.0.0.0" -ForegroundColor Gray
Write-Host ""
Write-Host "Then restart Flask:" -ForegroundColor White
Write-Host "   nssm restart `"VOFC-Flask`"" -ForegroundColor Yellow
Write-Host ""

