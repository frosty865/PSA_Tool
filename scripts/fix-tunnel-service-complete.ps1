# Complete Tunnel Service Fix and Verification Script
# Run this script as Administrator to fix and verify VOFC-Tunnel service
# This is CRITICAL for production - Vercel needs this tunnel to access Flask API

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VOFC-Tunnel Service Fix & Verification" -ForegroundColor Cyan
Write-Host "CRITICAL: Required for production access" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Service name
$ServiceName = "VOFC-Tunnel"

# Expected paths
$CloudflaredExe = "C:\Tools\cloudflared\cloudflared.exe"
$CloudflaredDir = "C:\Tools\cloudflared"
$ConfigFile = "C:\Tools\cloudflared\config.yaml"
$CredentialsFile = "C:\Users\frost\.cloudflared\17152659-d3ad-4abf-ae71-d0cc9d2b89e3.json"
$ExpectedParams = "--config C:\Tools\cloudflared\config.yaml tunnel run ollama-tunnel"

# Verification step
Write-Host "Step 1: Verifying prerequisites..." -ForegroundColor Yellow
Write-Host ""

$allGood = $true

# Check cloudflared.exe
if (Test-Path $CloudflaredExe) {
    Write-Host "  ✓ cloudflared.exe exists: $CloudflaredExe" -ForegroundColor Green
} else {
    Write-Host "  ✗ cloudflared.exe MISSING: $CloudflaredExe" -ForegroundColor Red
    $allGood = $false
}

# Check config file
if (Test-Path $ConfigFile) {
    Write-Host "  ✓ Config file exists: $ConfigFile" -ForegroundColor Green
    $configContent = Get-Content $ConfigFile -Raw
    if ($configContent -match "flask\.frostech\.site") {
        Write-Host "    ✓ Config contains flask.frostech.site" -ForegroundColor Green
    } else {
        Write-Host "    ⚠ Config may not have flask.frostech.site" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ Config file MISSING: $ConfigFile" -ForegroundColor Red
    $allGood = $false
}

# Check credentials file
if (Test-Path $CredentialsFile) {
    Write-Host "  ✓ Credentials file exists: $CredentialsFile" -ForegroundColor Green
} else {
    Write-Host "  ✗ Credentials file MISSING: $CredentialsFile" -ForegroundColor Red
    Write-Host "    This is required for Cloudflare tunnel authentication" -ForegroundColor Yellow
    $allGood = $false
}

# Check if service exists
$serviceExists = $false
try {
    $status = nssm status $ServiceName 2>&1
    if ($LASTEXITCODE -eq 0) {
        $serviceExists = $true
        Write-Host "  ✓ Service exists: $ServiceName" -ForegroundColor Green
    }
} catch {
    Write-Host "  ⚠ Service check failed (may not exist)" -ForegroundColor Yellow
}

if (-not $allGood) {
    Write-Host ""
    Write-Host "ERROR: Prerequisites not met. Please fix missing files before continuing." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Checking current service configuration..." -ForegroundColor Yellow
Write-Host ""

if ($serviceExists) {
    $currentApp = nssm get $ServiceName Application
    $currentDir = nssm get $ServiceName AppDirectory
    $currentParams = nssm get $ServiceName AppParameters
    
    Write-Host "  Current Application: $currentApp" -ForegroundColor Cyan
    Write-Host "  Current AppDirectory: $currentDir" -ForegroundColor Cyan
    Write-Host "  Current AppParameters: $currentParams" -ForegroundColor Cyan
    Write-Host ""
    
    $needsUpdate = $false
    
    if ($currentApp -ne $CloudflaredExe) {
        Write-Host "  ⚠ Application path needs update" -ForegroundColor Yellow
        $needsUpdate = $true
    }
    
    if ($currentDir -ne $CloudflaredDir) {
        Write-Host "  ⚠ AppDirectory needs update" -ForegroundColor Yellow
        $needsUpdate = $true
    }
    
    if ($currentParams -ne $ExpectedParams) {
        Write-Host "  ⚠ AppParameters need update" -ForegroundColor Yellow
        Write-Host "    Expected: $ExpectedParams" -ForegroundColor Gray
        $needsUpdate = $true
    }
    
    if (-not $needsUpdate) {
        Write-Host "  ✓ Service configuration is correct" -ForegroundColor Green
    }
} else {
    Write-Host "  ⚠ Service does not exist - will need to be created" -ForegroundColor Yellow
    $needsUpdate = $true
}

Write-Host ""
Write-Host "Step 3: Updating service configuration..." -ForegroundColor Yellow
Write-Host ""

if ($needsUpdate) {
    # Stop service if running
    Write-Host "  Stopping service (if running)..." -ForegroundColor Cyan
    Stop-Service -Name $ServiceName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    
    if ($serviceExists) {
        # Update existing service
        Write-Host "  Updating existing service..." -ForegroundColor Cyan
        nssm set $ServiceName Application $CloudflaredExe
        nssm set $ServiceName AppDirectory $CloudflaredDir
        nssm set $ServiceName AppParameters $ExpectedParams
    } else {
        # Install new service
        Write-Host "  Installing new service..." -ForegroundColor Cyan
        nssm install $ServiceName $CloudflaredExe
        nssm set $ServiceName AppDirectory $CloudflaredDir
        nssm set $ServiceName AppParameters $ExpectedParams
        nssm set $ServiceName DisplayName "VOFC-Tunnel (Cloudflare Tunnel)"
        nssm set $ServiceName Description "Cloudflare Tunnel for external access to Flask API and Ollama"
        nssm set $ServiceName Start SERVICE_AUTO_START
    }
    
    # Configure NSSM settings for cloudflared to run properly as a service
    Write-Host "  Configuring NSSM service settings..." -ForegroundColor Cyan
    
    # Set exit action to restart (cloudflared should stay running)
    nssm set $ServiceName AppExit Default Restart
    
    # Set restart delay to 5 seconds (give it time to reconnect)
    nssm set $ServiceName AppRestartDelay 5000
    
    # Enable console output (helps with debugging)
    nssm set $ServiceName AppNoConsole 0
    
    # Ensure log directory exists
    $logDir = "C:\Tools\nssm\logs"
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    
    # Set up logging
    nssm set $ServiceName AppStdout "$logDir\vofc_tunnel_out.log"
    nssm set $ServiceName AppStderr "$logDir\vofc_tunnel_err.log"
    nssm set $ServiceName AppStdoutCreationDisposition 4  # Open always
    nssm set $ServiceName AppStderrCreationDisposition 4   # Open always
    nssm set $ServiceName AppRotateFiles 1                # Enable log rotation
    nssm set $ServiceName AppRotateOnline 1                # Rotate while service is running
    nssm set $ServiceName AppRotateBytes 10485760          # 10MB per log file
    nssm set $ServiceName AppRotateSeconds 86400            # Daily rotation
    
    # Remove incorrect service dependency (tunnel doesn't need Flask to start)
    # The tunnel can start independently and will connect to Flask when it's available
    nssm set $ServiceName DependOnService ""
    
    Write-Host "  ✓ Service configured" -ForegroundColor Green
} else {
    Write-Host "  ✓ No updates needed" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 4: Verifying final configuration..." -ForegroundColor Yellow
Write-Host ""

$finalApp = nssm get $ServiceName Application
$finalDir = nssm get $ServiceName AppDirectory
$finalParams = nssm get $ServiceName AppParameters

Write-Host "  Application: $finalApp" -ForegroundColor Cyan
Write-Host "  AppDirectory: $finalDir" -ForegroundColor Cyan
Write-Host "  AppParameters: $finalParams" -ForegroundColor Cyan
Write-Host ""

if ($finalApp -eq $CloudflaredExe -and $finalDir -eq $CloudflaredDir -and $finalParams -eq $ExpectedParams) {
    Write-Host "  ✓ Configuration verified" -ForegroundColor Green
} else {
    Write-Host "  ✗ Configuration mismatch!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 5: Starting service..." -ForegroundColor Yellow
Write-Host ""

try {
    Start-Service -Name $ServiceName
    Start-Sleep -Seconds 3
    
    $status = Get-Service -Name $ServiceName
    if ($status.Status -eq 'Running') {
        Write-Host "  ✓ Service is RUNNING" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Service failed to start. Status: $($status.Status)" -ForegroundColor Red
        Write-Host "  Check logs: Get-EventLog -LogName Application -Source cloudflared -Newest 10" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "  ✗ Error starting service: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tunnel Service Fix Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service Status:" -ForegroundColor White
$finalStatus = Get-Service -Name $ServiceName
Write-Host "  Name: $($finalStatus.Name)" -ForegroundColor Cyan
Write-Host "  Status: $($finalStatus.Status)" -ForegroundColor $(if ($finalStatus.Status -eq 'Running') { 'Green' } else { 'Red' })
Write-Host "  Display Name: $($finalStatus.DisplayName)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test the tunnel:" -ForegroundColor White
Write-Host "  curl https://flask.frostech.site/api/system/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "If the tunnel is working, you should get a JSON response with system status." -ForegroundColor Gray
Write-Host "If you get 502/503/530 errors, check:" -ForegroundColor Yellow
Write-Host "  1. Flask service is running: nssm status vofc-flask" -ForegroundColor Gray
Write-Host "  2. Flask is listening on port 8080" -ForegroundColor Gray
Write-Host "  3. Tunnel config points to correct Flask IP (10.0.0.213:8080)" -ForegroundColor Gray
Write-Host ""

