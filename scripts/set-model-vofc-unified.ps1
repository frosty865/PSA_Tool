# Quick script to set OLLAMA_MODEL to vofc-unified:latest
# Must be run as Administrator

param(
    [string]$ServiceName = "VOFC-Processor",
    [string]$ModelName = "vofc-unified:latest"
)

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "ERROR: This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run PowerShell as Administrator:" -ForegroundColor Yellow
    Write-Host "  1. Right-click PowerShell" -ForegroundColor Yellow
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host "  3. Run this script again" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setting Model for $ServiceName" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get current environment variables
Write-Host "Current environment variables:" -ForegroundColor Yellow
$currentEnvRaw = nssm get $ServiceName AppEnvironmentExtra 2>&1
$existingVars = @{}

if ($currentEnvRaw -notmatch "not exist" -and $currentEnvRaw -ne "") {
    # Parse existing environment variables
    # NSSM returns them as newline-separated KEY=VALUE pairs
    $currentEnvRaw -split "`n" | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1]
            $value = $matches[2]
            $existingVars[$key] = $value
            Write-Host "  $key=$value" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "  No environment variables currently set" -ForegroundColor Gray
}

# Preserve existing variables and add/update OLLAMA_MODEL
$existingVars["OLLAMA_MODEL"] = $ModelName

Write-Host ""
Write-Host "Setting OLLAMA_MODEL=$ModelName (preserving existing variables)..." -ForegroundColor Yellow

# Build the combined environment string (NSSM expects newline-separated KEY=VALUE pairs)
$envString = ($existingVars.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n"

try {
    nssm set $ServiceName AppEnvironmentExtra $envString 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Model set successfully (all variables preserved)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Failed to set model" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ✗ Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Verifying..." -ForegroundColor Yellow
$verify = nssm get $ServiceName AppEnvironmentExtra 2>&1
if ($verify -match "OLLAMA_MODEL") {
    Write-Host "  ✓ Verified: $verify" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Verification unclear: $verify" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Model Configuration Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Restart the service to apply changes:" -ForegroundColor Yellow
Write-Host "  nssm restart $ServiceName" -ForegroundColor Cyan
Write-Host ""

