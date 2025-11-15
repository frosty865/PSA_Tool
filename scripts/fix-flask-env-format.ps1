# Fix Flask Service Environment Variables Format
# NSSM requires newline-separated KEY=VALUE pairs, not space-separated
# Run as Administrator

$ErrorActionPreference = "Stop"

Write-Host "Fixing Flask service environment variables format..." -ForegroundColor Cyan
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

# Stop service first
Write-Host "Stopping Flask service..." -ForegroundColor Yellow
nssm stop $ServiceName
Start-Sleep -Seconds 2

# Read .env file
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

# Build newline-separated string
$envString = ""
foreach ($key in $envVars.Keys) {
    $value = $envVars[$key]
    if ($envString) {
        $envString += "`n"
    }
    $envString += "$key=$value"
}

# Clear and set with newline format
Write-Host "Setting environment variables with newline format..." -ForegroundColor Cyan
nssm set $ServiceName AppEnvironmentExtra ""
nssm set $ServiceName AppEnvironmentExtra $envString

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Environment variables set successfully" -ForegroundColor Green
} else {
    Write-Host "  ❌ Failed to set environment variables" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting Flask service..." -ForegroundColor Yellow
nssm start $ServiceName
Start-Sleep -Seconds 3

$status = nssm status $ServiceName
if ($status -eq "SERVICE_RUNNING") {
    Write-Host "  ✅ Flask service is running" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Service status: $status" -ForegroundColor Yellow
    Write-Host "  Check logs: C:\Tools\nssm\logs\vofc_flask_err.log" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Fix complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

