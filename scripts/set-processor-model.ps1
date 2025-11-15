# Set Processor Model Environment Variable in NSSM
# Run this script as Administrator

Write-Host "Setting Processor model environment variable in NSSM..." -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$ServiceName = "VOFC-Processor"
$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

# Get current environment variables
Write-Host "Current environment variables:" -ForegroundColor Yellow
$currentEnv = & $nssmPath get $ServiceName AppEnvironmentExtra
if ($currentEnv) {
    Write-Host "  $currentEnv" -ForegroundColor Gray
} else {
    Write-Host "  (none)" -ForegroundColor Gray
}
Write-Host ""

# Read from .env file to get the correct model
$envFile = "C:\Tools\.env"
$modelName = "vofc-unified:latest"  # Default

if (Test-Path $envFile) {
    Write-Host "Reading from .env file: $envFile" -ForegroundColor Yellow
    $envContent = Get-Content $envFile
    foreach ($line in $envContent) {
        if ($line -match '^\s*VOFC_MODEL\s*=\s*(.+)$') {
            $modelName = $matches[1].Trim()
            Write-Host "  Found VOFC_MODEL: $modelName" -ForegroundColor Green
            break
        } elseif ($line -match '^\s*OLLAMA_MODEL\s*=\s*(.+)$' -and $modelName -eq "vofc-unified:latest") {
            $modelName = $matches[1].Trim()
            Write-Host "  Found OLLAMA_MODEL: $modelName" -ForegroundColor Green
        }
    }
} else {
    Write-Host "WARNING: .env file not found at $envFile" -ForegroundColor Yellow
    Write-Host "  Using default: $modelName" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setting VOFC_MODEL=$modelName" -ForegroundColor Yellow

# Stop service first
Write-Host "Stopping service..." -ForegroundColor Yellow
& $nssmPath stop $ServiceName
Start-Sleep -Seconds 2

# Build environment variable string
# NSSM requires newline-separated KEY=VALUE pairs
$envVars = @()
$envVars += "VOFC_MODEL=$modelName"
$envVars += "OLLAMA_MODEL=$modelName"

# If there are existing environment variables, preserve them (except VOFC_MODEL and OLLAMA_MODEL)
if ($currentEnv) {
    $existingVars = $currentEnv -split "`n" | Where-Object { $_ -and $_ -notmatch '^\s*VOFC_MODEL\s*=' -and $_ -notmatch '^\s*OLLAMA_MODEL\s*=' }
    $envVars += $existingVars
}

# Join with newlines
$envString = $envVars -join "`n"

# Set environment variables
Write-Host "Setting environment variables..." -ForegroundColor Yellow
& $nssmPath set $ServiceName AppEnvironmentExtra $envString

if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Environment variables set" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Failed to set environment variables" -ForegroundColor Red
    exit 1
}

# Verify
Write-Host ""
Write-Host "Verifying..." -ForegroundColor Yellow
$verifyEnv = & $nssmPath get $ServiceName AppEnvironmentExtra
if ($verifyEnv -match "VOFC_MODEL=$modelName") {
    Write-Host "  [OK] VOFC_MODEL verified: $modelName" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Verification failed - check manually" -ForegroundColor Yellow
}

# Start service
Write-Host ""
Write-Host "Starting service..." -ForegroundColor Yellow
& $nssmPath start $ServiceName
Start-Sleep -Seconds 3

# Check status
$status = & $nssmPath status $ServiceName
if ($status -match "SERVICE_RUNNING") {
    Write-Host "  [OK] Service is running" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Service status: $status" -ForegroundColor Yellow
    Write-Host "  Check logs: C:\Tools\Ollama\Data\logs\vofc_processor_err.log" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Processor model environment variable set!" -ForegroundColor Green
Write-Host ""
Write-Host "The service will now use model: $modelName" -ForegroundColor Cyan

