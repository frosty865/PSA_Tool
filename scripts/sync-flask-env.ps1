# Sync Environment Variables to Flask Service
# Reads .env file and sets environment variables in NSSM service

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Sync Environment Variables to Flask Service" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$ServiceName = "vofc-flask"
$envFile = ".env"

# Check if .env file exists
if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: .env file not found at $envFile" -ForegroundColor Red
    exit 1
}

# Check if service exists
$serviceExists = $false
try {
    $result = sc query $ServiceName 2>&1
    if ($LASTEXITCODE -eq 0) {
        $serviceExists = $true
    }
} catch {
    $serviceExists = $false
}

if (-not $serviceExists) {
    Write-Host "ERROR: Service '$ServiceName' not found" -ForegroundColor Red
    exit 1
}

Write-Host "Reading .env file..." -ForegroundColor Cyan
$envVars = @{}
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#')) {
        if ($line -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            # Remove quotes if present
            if ($value.StartsWith('"') -and $value.EndsWith('"')) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            if ($value.StartsWith("'") -and $value.EndsWith("'")) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            $envVars[$key] = $value
        }
    }
}

Write-Host "Found $($envVars.Count) environment variables" -ForegroundColor Green
Write-Host ""

# Critical variables that Flask needs
# Note: SUPABASE_ANON_KEY is optional if SUPABASE_SERVICE_ROLE_KEY is set
$criticalVars = @(
    'SUPABASE_URL',
    'SUPABASE_SERVICE_ROLE_KEY',
    'NEXT_PUBLIC_SUPABASE_URL',
    'NEXT_PUBLIC_SUPABASE_ANON_KEY',
    'TUNNEL_URL',
    'FLASK_PORT',
    'OLLAMA_HOST'
)

# Optional variables (only needed if service role key is not set)
$optionalVars = @(
    'SUPABASE_ANON_KEY'
)

Write-Host "Setting environment variables in NSSM service..." -ForegroundColor Cyan

# Build environment string for NSSM
# NSSM AppEnvironmentExtra requires newline-separated KEY=VALUE pairs
# Format: KEY1=value1\nKEY2=value2\n...
$envString = ""
$setCount = 0
$missingCount = 0

foreach ($key in $envVars.Keys) {
    $value = $envVars[$key]
    if ($envString) {
        $envString += "`n"  # PowerShell newline character
    }
    $envString += "$key=$value"
    $setCount++
    
    if ($criticalVars -contains $key) {
        Write-Host "  [OK] $key" -ForegroundColor Green
    }
}

# Check for missing critical variables
Write-Host ""
Write-Host "Checking critical variables..." -ForegroundColor Cyan
foreach ($criticalVar in $criticalVars) {
    if ($envVars.ContainsKey($criticalVar)) {
        Write-Host "  [OK] $criticalVar" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] $criticalVar (not in .env)" -ForegroundColor Yellow
        $missingCount++
    }
}

# Check optional variables (informational only)
Write-Host ""
Write-Host "Checking optional variables..." -ForegroundColor Cyan
foreach ($optionalVar in $optionalVars) {
    if ($envVars.ContainsKey($optionalVar)) {
        Write-Host "  [OK] $optionalVar" -ForegroundColor Green
    } else {
        # SUPABASE_ANON_KEY is only needed if SUPABASE_SERVICE_ROLE_KEY is not set
        if ($optionalVar -eq 'SUPABASE_ANON_KEY' -and $envVars.ContainsKey('SUPABASE_SERVICE_ROLE_KEY')) {
            Write-Host "  [INFO] $optionalVar (optional - SERVICE_ROLE_KEY is set)" -ForegroundColor Gray
        } else {
            Write-Host "  [WARN] $optionalVar (not in .env)" -ForegroundColor Yellow
        }
    }
}

if ($missingCount -gt 0) {
    Write-Host ""
    Write-Host "[WARN] Warning: $missingCount critical variables missing from .env" -ForegroundColor Yellow
    Write-Host "   Service may not work correctly without these variables" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "[OK] All critical variables present" -ForegroundColor Green
}

Write-Host ""
Write-Host "Setting AppEnvironmentExtra in NSSM..." -ForegroundColor Cyan
Write-Host "  Using newline-separated format (NSSM requirement)" -ForegroundColor Gray

# Clear existing AppEnvironmentExtra first to avoid conflicts
nssm set $ServiceName AppEnvironmentExtra ""

# Set environment variables in NSSM
# NSSM AppEnvironmentExtra requires newline-separated KEY=VALUE pairs
# PowerShell's backtick-n creates actual newlines that NSSM can parse
nssm set $ServiceName AppEnvironmentExtra $envString

if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Environment variables set successfully" -ForegroundColor Green
    Write-Host "  Set $setCount variables" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Failed to set environment variables" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Verifying configuration..." -ForegroundColor Cyan
$verifyResult = nssm get $ServiceName AppEnvironmentExtra 2>&1
if ($LASTEXITCODE -eq 0) {
    $varCount = ($verifyResult -split ' ').Count
    Write-Host "  ✅ Verified: $varCount variables configured" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Could not verify (service may need restart)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Environment variables synced!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  IMPORTANT: Restart Flask service to apply changes:" -ForegroundColor Yellow
Write-Host "   nssm restart $ServiceName" -ForegroundColor Cyan
Write-Host ""

