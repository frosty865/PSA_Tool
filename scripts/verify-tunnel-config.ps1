# Verify Cloudflare Tunnel Configuration
# Checks that tunnel config points to correct services

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cloudflare Tunnel Configuration Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check multiple possible config locations
$configPaths = @(
    "C:\Users\frost\cloudflared\config.yml",
    "C:\Tools\cloudflared\config.yaml",
    "C:\Tools\cloudflared\config.yml",
    "$env:USERPROFILE\.cloudflared\config.yml"
)

$foundConfig = $null
foreach ($path in $configPaths) {
    if (Test-Path $path) {
        Write-Host "✅ Found config file: $path" -ForegroundColor Green
        $foundConfig = $path
        break
    }
}

if (-not $foundConfig) {
    Write-Host "❌ No tunnel config file found in expected locations:" -ForegroundColor Red
    $configPaths | ForEach-Object { Write-Host "   - $_" -ForegroundColor Gray }
    Write-Host ""
    Write-Host "→ Check NSSM service configuration for actual config path:" -ForegroundColor Yellow
    Write-Host "   nssm get VOFC-Tunnel AppParameters" -ForegroundColor Gray
    exit
}

Write-Host ""
Write-Host "Reading configuration..." -ForegroundColor Yellow
$config = Get-Content $foundConfig -Raw

# Check for required hostnames
Write-Host ""
Write-Host "Configuration Check:" -ForegroundColor Yellow

$checks = @{
    "ollama.frostech.site" = "http://localhost:11434"
    "flask.frostech.site" = "http://localhost:8080"
    "backend.frostech.site" = "http://localhost:8080"
}

$allGood = $true
foreach ($hostname in $checks.Keys) {
    $expectedService = $checks[$hostname]
    if ($config -match $hostname) {
        Write-Host "   ✅ $hostname configured" -ForegroundColor Green
        if ($config -match "$hostname[\s\S]*?service:\s*$expectedService") {
            Write-Host "      ✅ Points to $expectedService" -ForegroundColor Green
        } else {
            Write-Host "      ⚠️  Service may not match expected: $expectedService" -ForegroundColor Yellow
            $allGood = $false
        }
    } else {
        Write-Host "   ❌ $hostname NOT found in config" -ForegroundColor Red
        $allGood = $false
    }
}

# Check for credentials file
if ($config -match "credentials-file") {
    Write-Host "   ✅ Credentials file specified" -ForegroundColor Green
    $credMatch = [regex]::Match($config, "credentials-file:\s*(.+)")
    if ($credMatch.Success) {
        $credPath = $credMatch.Groups[1].Value.Trim()
        if (Test-Path $credPath) {
            Write-Host "      ✅ Credentials file exists: $credPath" -ForegroundColor Green
        } else {
            Write-Host "      ❌ Credentials file NOT found: $credPath" -ForegroundColor Red
            $allGood = $false
        }
    }
} else {
    Write-Host "   ⚠️  No credentials-file specified" -ForegroundColor Yellow
}

# Check for tunnel name
if ($config -match "tunnel:\s*(\S+)") {
    $tunnelName = [regex]::Match($config, "tunnel:\s*(\S+)").Groups[1].Value
    Write-Host "   ✅ Tunnel name: $tunnelName" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  No tunnel name specified" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "✅ Configuration looks correct!" -ForegroundColor Green
    Write-Host ""
    Write-Host "If tunnel still shows 502 errors:" -ForegroundColor Yellow
    Write-Host "1. Restart Flask: nssm restart `"VOFC-Flask`"" -ForegroundColor White
    Write-Host "2. Restart Tunnel: nssm restart `"VOFC-Tunnel`"" -ForegroundColor White
    Write-Host "3. Verify Flask is listening on 0.0.0.0:8080:" -ForegroundColor White
    Write-Host "   netstat -ano | findstr :8080" -ForegroundColor Gray
} else {
    Write-Host "⚠️  Configuration issues found" -ForegroundColor Yellow
    Write-Host "Review the config file: $foundConfig" -ForegroundColor White
}
Write-Host ""

