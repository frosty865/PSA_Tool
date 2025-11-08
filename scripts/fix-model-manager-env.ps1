# Fix Model Manager Service Environment Variables
# Sets the correct Supabase credentials in the NSSM service
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix Model Manager Environment Variables" -ForegroundColor Cyan
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

# Get the correct credentials from user-level environment variables
Write-Host "Reading Supabase credentials from environment..." -ForegroundColor Yellow

$supabaseUrl = [System.Environment]::GetEnvironmentVariable("SUPABASE_URL", "User")
if (-not $supabaseUrl) {
    $supabaseUrl = [System.Environment]::GetEnvironmentVariable("NEXT_PUBLIC_SUPABASE_URL", "User")
}

$supabaseKey = [System.Environment]::GetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", "User")

if (-not $supabaseUrl -or -not $supabaseKey) {
    Write-Host "❌ Supabase credentials not found in user environment variables!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please set them first:" -ForegroundColor Yellow
    Write-Host '  [System.Environment]::SetEnvironmentVariable("SUPABASE_URL", "https://your-project.supabase.co", "User")' -ForegroundColor White
    Write-Host '  [System.Environment]::SetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", "eyJ...", "User")' -ForegroundColor White
    Write-Host ""
    Write-Host "Or update the .env file with the correct credentials." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Found credentials:" -ForegroundColor Green
Write-Host "   SUPABASE_URL: $($supabaseUrl.Substring(0, [Math]::Min(50, $supabaseUrl.Length)))..." -ForegroundColor Cyan
Write-Host "   SUPABASE_SERVICE_ROLE_KEY: $($supabaseKey.Substring(0, [Math]::Min(20, $supabaseKey.Length)))... (length: $($supabaseKey.Length))" -ForegroundColor Cyan
Write-Host ""

# Validate key format
if ($supabaseKey.Length -lt 100) {
    Write-Host "⚠️  Warning: Service role key seems too short (should be 200+ characters)" -ForegroundColor Yellow
}
if (-not $supabaseKey.StartsWith("eyJ")) {
    Write-Host "⚠️  Warning: Service role key should start with 'eyJ' (JWT format)" -ForegroundColor Yellow
    Write-Host "   You might be using the wrong key" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Continue anyway? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        exit 1
    }
}

Write-Host ""

# Stop service before configuring (handle paused state)
Write-Host "Stopping service..." -ForegroundColor Yellow
$currentStatus = nssm status $serviceName 2>&1
if ($currentStatus -eq "SERVICE_RUNNING" -or $currentStatus -eq "SERVICE_PAUSED") {
    nssm stop $serviceName 2>&1 | Out-Null
    Start-Sleep -Seconds 2
    # If still paused, try to resume then stop
    $status = nssm status $serviceName 2>&1
    if ($status -eq "SERVICE_PAUSED") {
        Write-Host "Service is paused, attempting to resume then stop..." -ForegroundColor Yellow
        nssm resume $serviceName 2>&1 | Out-Null
        Start-Sleep -Seconds 1
        nssm stop $serviceName 2>&1 | Out-Null
        Start-Sleep -Seconds 2
    }
}

# Set environment variables in NSSM
Write-Host "Setting environment variables in NSSM..." -ForegroundColor Yellow

$envString = "SUPABASE_URL=$supabaseUrl SUPABASE_SERVICE_ROLE_KEY=$supabaseKey NEXT_PUBLIC_SUPABASE_URL=$supabaseUrl"

nssm set $serviceName AppEnvironment $envString

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Environment variables configured" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to set environment variables" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Start service (handle paused state)
Write-Host "Starting service..." -ForegroundColor Yellow
$currentStatus = nssm status $serviceName 2>&1
if ($currentStatus -eq "SERVICE_PAUSED") {
    Write-Host "Service is paused, resuming..." -ForegroundColor Yellow
    nssm resume $serviceName 2>&1 | Out-Null
    Start-Sleep -Seconds 2
} else {
    nssm start $serviceName 2>&1 | Out-Null
    Start-Sleep -Seconds 3
}

$status = nssm status $serviceName 2>&1
if ($status -eq "SERVICE_RUNNING") {
    Write-Host "✅ Service started successfully!" -ForegroundColor Green
} elseif ($status -eq "SERVICE_PAUSED") {
    Write-Host "⚠️  Service is paused. Trying to resume..." -ForegroundColor Yellow
    nssm resume $serviceName 2>&1 | Out-Null
    Start-Sleep -Seconds 2
    $status = nssm status $serviceName 2>&1
    if ($status -eq "SERVICE_RUNNING") {
        Write-Host "✅ Service resumed successfully!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Service status: $status" -ForegroundColor Yellow
        Write-Host "   Try manually: nssm start $serviceName" -ForegroundColor Cyan
    }
} else {
    Write-Host "⚠️  Service status: $status" -ForegroundColor Yellow
    Write-Host "   Try manually: nssm start $serviceName" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Done" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check logs:" -ForegroundColor Cyan
Write-Host "  Get-Content -Path `"C:\Tools\VOFC_Logs\model_manager.log`" -Wait" -ForegroundColor White
Write-Host ""

