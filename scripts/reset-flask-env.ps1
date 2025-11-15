# Completely Reset Flask Service Environment Variables
# Clears and resets with proper format
# Run as Administrator

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Reset Flask Service Environment Variables" -ForegroundColor Cyan
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

# Stop service
Write-Host "Stopping Flask service..." -ForegroundColor Yellow
nssm stop $ServiceName
Start-Sleep -Seconds 3

# Clear environment variables completely
Write-Host "Clearing existing environment variables..." -ForegroundColor Cyan
nssm set $ServiceName AppEnvironmentExtra ""
Start-Sleep -Seconds 1

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

# Build environment string with newlines
# NSSM AppEnvironmentExtra requires newline-separated KEY=VALUE pairs
$envLines = @()
foreach ($key in $envVars.Keys) {
    $value = $envVars[$key]
    $envLines += "$key=$value"
}

# Join with newlines
$envString = $envLines -join "`n"

Write-Host "Setting environment variables (newline-separated format)..." -ForegroundColor Cyan
Write-Host "  Format: KEY1=value1`nKEY2=value2`n..." -ForegroundColor Gray

# Set using a temporary file to ensure proper newline handling
$tempFile = [System.IO.Path]::GetTempFileName()
$envString | Out-File -FilePath $tempFile -Encoding ASCII -NoNewline
$envContent = Get-Content $tempFile -Raw
Remove-Item $tempFile

# Set environment variables
# Use -Command to properly pass the newline string
$result = nssm set $ServiceName AppEnvironmentExtra $envString

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ Environment variables set successfully" -ForegroundColor Green
    Write-Host "  Set $($envVars.Count) variables" -ForegroundColor Green
} else {
    Write-Host "  ❌ Failed to set environment variables" -ForegroundColor Red
    Write-Host "  Exit code: $LASTEXITCODE" -ForegroundColor Yellow
    exit 1
}

# Verify
Write-Host ""
Write-Host "Verifying configuration..." -ForegroundColor Cyan
$verifyResult = nssm get $ServiceName AppEnvironmentExtra 2>&1
if ($LASTEXITCODE -eq 0) {
    $lineCount = ($verifyResult -split "`n").Count
    Write-Host "  ✅ Verified: $lineCount lines configured" -ForegroundColor Green
    Write-Host "  First few lines:" -ForegroundColor Gray
    ($verifyResult -split "`n")[0..2] | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
} else {
    Write-Host "  ⚠️  Could not verify" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Starting Flask service..." -ForegroundColor Yellow
nssm start $ServiceName
Start-Sleep -Seconds 5

$status = nssm status $ServiceName
if ($status -eq "SERVICE_RUNNING") {
    Write-Host "  ✅ Flask service is running" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Service status: $status" -ForegroundColor Yellow
    Write-Host "  Check logs: C:\Tools\nssm\logs\vofc_flask_err.log" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Reset complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

