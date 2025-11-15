# Fix PAUSED Processor Service
# Run this script as Administrator

Write-Host "Fixing PAUSED Processor service..." -ForegroundColor Cyan
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

# Check current status
Write-Host "Current service status:" -ForegroundColor Yellow
$status = & $nssmPath status $ServiceName
Write-Host "  $status" -ForegroundColor Gray
Write-Host ""

# If paused, we need to stop it first (can't restart a paused service)
if ($status -eq "SERVICE_PAUSED") {
    Write-Host "Service is PAUSED - stopping it first..." -ForegroundColor Yellow
    
    # Force stop
    Write-Host "  Stopping $ServiceName..." -ForegroundColor Gray
    & $nssmPath stop $ServiceName
    Start-Sleep -Seconds 3
    
    # Verify it's stopped
    $newStatus = & $nssmPath status $ServiceName
    if ($newStatus -eq "SERVICE_STOPPED") {
        Write-Host "  [OK] Service stopped" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Service status: $newStatus" -ForegroundColor Yellow
        Write-Host "  Attempting to start anyway..." -ForegroundColor Yellow
    }
    Write-Host ""
}

# Verify service configuration
Write-Host "Checking service configuration..." -ForegroundColor Yellow
$appPath = & $nssmPath get $ServiceName Application
$appParams = & $nssmPath get $ServiceName AppParameters
$appDir = & $nssmPath get $ServiceName AppDirectory

Write-Host "  Application: $appPath" -ForegroundColor Gray
Write-Host "  Parameters: $appParams" -ForegroundColor Gray
Write-Host "  Directory: $appDir" -ForegroundColor Gray
Write-Host ""

# Check if files exist
if (-not (Test-Path $appPath)) {
    Write-Host "  [ERROR] Application path does not exist: $appPath" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $appParams)) {
    Write-Host "  [ERROR] Script path does not exist: $appParams" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $appDir)) {
    Write-Host "  [ERROR] Working directory does not exist: $appDir" -ForegroundColor Red
    exit 1
}

Write-Host "  [OK] All paths exist" -ForegroundColor Green
Write-Host ""

# Check if config directory exists
$configDir = Join-Path $appDir "config"
if (-not (Test-Path $configDir)) {
    Write-Host "  [WARN] Config directory missing: $configDir" -ForegroundColor Yellow
    Write-Host "  Syncing config directory..." -ForegroundColor Yellow
    $projectRoot = "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool"
    $sourceConfig = Join-Path $projectRoot "config"
    if (Test-Path $sourceConfig) {
        Copy-Item $sourceConfig $configDir -Recurse -Force
        Write-Host "  [OK] Config directory synced" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Source config not found: $sourceConfig" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [OK] Config directory exists" -ForegroundColor Green
}
Write-Host ""

# Now start the service
Write-Host "Starting Processor service..." -ForegroundColor Yellow
& $nssmPath start $ServiceName

if ($LASTEXITCODE -eq 0) {
    Start-Sleep -Seconds 3
    
    # Check status
    $finalStatus = & $nssmPath status $ServiceName
    if ($finalStatus -match "SERVICE_RUNNING") {
        Write-Host "  [OK] Service is running" -ForegroundColor Green
    } elseif ($finalStatus -eq "SERVICE_PAUSED") {
        Write-Host "  [ERROR] Service paused immediately - check logs:" -ForegroundColor Red
        Write-Host "    C:\Tools\Ollama\Data\logs\vofc_processor_err.log" -ForegroundColor Yellow
        Write-Host "    C:\Tools\nssm\logs\vofc_processor_err.log" -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "  [WARN] Service status: $finalStatus" -ForegroundColor Yellow
        Write-Host "  Check logs: C:\Tools\Ollama\Data\logs\vofc_processor_err.log" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [ERROR] Failed to start service" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Processor service fix complete!" -ForegroundColor Green

