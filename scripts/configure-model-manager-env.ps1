# Configure Model Manager Service Environment Variables
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configure Model Manager Environment" -ForegroundColor Cyan
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

# Get environment variables from system (or Flask service)
Write-Host "Reading Supabase credentials from environment..." -ForegroundColor Yellow

$supabaseUrl = [System.Environment]::GetEnvironmentVariable("SUPABASE_URL", "Machine")
if (-not $supabaseUrl) {
    $supabaseUrl = [System.Environment]::GetEnvironmentVariable("SUPABASE_URL", "User")
}
if (-not $supabaseUrl) {
    $supabaseUrl = [System.Environment]::GetEnvironmentVariable("NEXT_PUBLIC_SUPABASE_URL", "Machine")
}
if (-not $supabaseUrl) {
    $supabaseUrl = [System.Environment]::GetEnvironmentVariable("NEXT_PUBLIC_SUPABASE_URL", "User")
}

$supabaseKey = [System.Environment]::GetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", "Machine")
if (-not $supabaseKey) {
    $supabaseKey = [System.Environment]::GetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", "User")
}

# If not found in environment, try to get from Flask service
if (-not $supabaseUrl -or -not $supabaseKey) {
    Write-Host "⚠️  Credentials not found in environment variables" -ForegroundColor Yellow
    Write-Host "Checking Flask service configuration..." -ForegroundColor Yellow
    
    $flaskEnv = nssm get VOFC-Flask AppEnvironment 2>&1
    if ($LASTEXITCODE -eq 0 -and $flaskEnv) {
        # Parse Flask environment variables
        $envLines = $flaskEnv -split "`n"
        foreach ($line in $envLines) {
            if ($line -match 'SUPABASE_URL=(.+)') {
                $supabaseUrl = $matches[1]
            }
            if ($line -match 'SUPABASE_SERVICE_ROLE_KEY=(.+)') {
                $supabaseKey = $matches[1]
            }
        }
    }
}

# If still not found, prompt user
if (-not $supabaseUrl -or -not $supabaseKey) {
    Write-Host ""
    Write-Host "❌ Supabase credentials not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please provide Supabase credentials:" -ForegroundColor Yellow
    Write-Host ""
    
    if (-not $supabaseUrl) {
        $supabaseUrl = Read-Host "Enter SUPABASE_URL"
    }
    
    if (-not $supabaseKey) {
        $supabaseKey = Read-Host "Enter SUPABASE_SERVICE_ROLE_KEY"
    }
}

if (-not $supabaseUrl -or -not $supabaseKey) {
    Write-Host "❌ Credentials are required!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Credentials found" -ForegroundColor Green
Write-Host ""

# Stop service before configuring
Write-Host "Stopping service..." -ForegroundColor Yellow
nssm stop $serviceName 2>&1 | Out-Null
Start-Sleep -Seconds 2

# Set environment variables in NSSM
Write-Host "Setting environment variables..." -ForegroundColor Yellow

# NSSM environment variables format: VAR1=value1 VAR2=value2
$envString = "SUPABASE_URL=$supabaseUrl SUPABASE_SERVICE_ROLE_KEY=$supabaseKey"

# Also try NEXT_PUBLIC_SUPABASE_URL as fallback
if ($supabaseUrl) {
    $envString += " NEXT_PUBLIC_SUPABASE_URL=$supabaseUrl"
}

nssm set $serviceName AppEnvironment $envString

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Environment variables configured" -ForegroundColor Green
} else {
    Write-Host "⚠️  Failed to set environment variables" -ForegroundColor Yellow
    Write-Host "You may need to set them manually:" -ForegroundColor Yellow
    Write-Host "  nssm set $serviceName AppEnvironment `"SUPABASE_URL=$supabaseUrl SUPABASE_SERVICE_ROLE_KEY=$supabaseKey`"" -ForegroundColor White
}

Write-Host ""

# Start service
Write-Host "Starting service..." -ForegroundColor Yellow
nssm start $serviceName

Start-Sleep -Seconds 3

$status = nssm status $serviceName 2>&1
if ($status -eq "SERVICE_RUNNING") {
    Write-Host "✅ Service started successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Service status: $status" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Check logs:" -ForegroundColor Cyan
    Write-Host "  C:\Tools\VOFC_Logs\model_manager.log" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Done" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

