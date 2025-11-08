# Verify Model Manager Service Environment Variables
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Verify Model Manager Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$serviceName = "VOFC-ModelManager"

Write-Host "Checking NSSM service configuration..." -ForegroundColor Yellow
Write-Host ""

# Get current environment variables
$currentEnv = nssm get $serviceName AppEnvironment 2>&1

if ($LASTEXITCODE -ne 0 -or -not $currentEnv) {
    Write-Host "❌ No environment variables configured!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Run the configuration script:" -ForegroundColor Yellow
    Write-Host "  .\scripts\configure-model-manager-env.ps1" -ForegroundColor White
    exit 1
}

Write-Host "Current environment variables:" -ForegroundColor Green
Write-Host $currentEnv -ForegroundColor White
Write-Host ""

# Check if Supabase variables are present
$hasUrl = $currentEnv -match "SUPABASE_URL="
$hasKey = $currentEnv -match "SUPABASE_SERVICE_ROLE_KEY="

if ($hasUrl -and $hasKey) {
    Write-Host "✅ Supabase credentials are configured" -ForegroundColor Green
} else {
    Write-Host "❌ Missing Supabase credentials!" -ForegroundColor Red
    if (-not $hasUrl) {
        Write-Host "  Missing: SUPABASE_URL" -ForegroundColor Yellow
    }
    if (-not $hasKey) {
        Write-Host "  Missing: SUPABASE_SERVICE_ROLE_KEY" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Run the configuration script:" -ForegroundColor Yellow
    Write-Host "  .\scripts\configure-model-manager-env.ps1" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "Checking service status..." -ForegroundColor Yellow
$status = nssm status $serviceName 2>&1
Write-Host "Service status: $status" -ForegroundColor $(if ($status -eq "SERVICE_RUNNING") { "Green" } else { "Yellow" })

if ($status -ne "SERVICE_RUNNING") {
    Write-Host ""
    Write-Host "⚠️  Service is not running. Restarting..." -ForegroundColor Yellow
    nssm restart $serviceName 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    $status = nssm status $serviceName 2>&1
    Write-Host "Service status after restart: $status" -ForegroundColor $(if ($status -eq "SERVICE_RUNNING") { "Green" } else { "Red" })
}

Write-Host ""
Write-Host "Checking recent logs..." -ForegroundColor Yellow
$logFile = "C:\Tools\VOFC_Logs\model_manager.log"
if (Test-Path $logFile) {
    Write-Host "Last 5 lines from log:" -ForegroundColor Cyan
    Get-Content $logFile -Tail 5 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
} else {
    Write-Host "⚠️  Log file not found: $logFile" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Verification complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

