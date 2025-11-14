# Install and Configure Flask Service (vofc-flask)
# Run this script as Administrator

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Flask Service Installation & Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Service configuration
$ServiceName = "vofc-flask"
$FlaskDir = "C:\Tools\VOFC-Flask"
$PythonExe = "$FlaskDir\venv\Scripts\python.exe"
$AppParameters = "-m waitress --listen=0.0.0.0:8080 server:app"  # Use server.py, not app.py

# Check if Flask directory exists
if (-not (Test-Path $FlaskDir)) {
    Write-Host "ERROR: Flask directory not found: $FlaskDir" -ForegroundColor Red
    Write-Host "Please run migrate-all-services.ps1 first to set up the Flask directory." -ForegroundColor Yellow
    exit 1
}

# Check if Python executable exists
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: Python executable not found: $PythonExe" -ForegroundColor Red
    Write-Host "Please create the virtual environment first:" -ForegroundColor Yellow
    Write-Host "  cd $FlaskDir" -ForegroundColor Cyan
    Write-Host "  python -m venv venv" -ForegroundColor Cyan
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Cyan
    exit 1
}

# Install dependencies (waitress, etc.)
Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
$RequirementsFile = "$FlaskDir\requirements.txt"
if (Test-Path $RequirementsFile) {
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install -r $RequirementsFile
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠ pip install had errors, but continuing..." -ForegroundColor Yellow
    } else {
        Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
    }
} else {
    # Install waitress directly if requirements.txt doesn't exist
    Write-Host "  requirements.txt not found, installing waitress directly..." -ForegroundColor Yellow
    & $PythonExe -m pip install waitress flask flask-cors
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Failed to install waitress" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "  ✓ waitress installed" -ForegroundColor Green
    }
}

# Verify waitress is installed
Write-Host "Verifying waitress installation..." -ForegroundColor Cyan
$waitressCheck = & $PythonExe -c "import waitress; print('OK')" 2>&1
if ($waitressCheck -match "OK") {
    Write-Host "  ✓ waitress is installed" -ForegroundColor Green
} else {
    Write-Host "  ✗ waitress verification failed: $waitressCheck" -ForegroundColor Red
    Write-Host "  Attempting to install waitress again..." -ForegroundColor Yellow
    & $PythonExe -m pip install waitress
}

# Check if service already exists
$serviceExists = $false
try {
    $result = sc query $ServiceName 2>&1
    if ($LASTEXITCODE -eq 0) {
        $serviceExists = $true
        Write-Host "Service '$ServiceName' already exists" -ForegroundColor Yellow
    }
} catch {
    $serviceExists = $false
}

if ($serviceExists) {
    Write-Host "Updating existing service configuration..." -ForegroundColor Cyan
    nssm stop $ServiceName
    Start-Sleep -Seconds 2
} else {
    Write-Host "Installing new service..." -ForegroundColor Cyan
    nssm install $ServiceName $PythonExe
}

# Configure service
Write-Host "Configuring service..." -ForegroundColor Cyan
nssm set $ServiceName AppDirectory $FlaskDir
nssm set $ServiceName AppParameters $AppParameters
nssm set $ServiceName DisplayName "VOFC Flask API Server"
nssm set $ServiceName Description "Flask API server for PSA Tool (VOFC)"
nssm set $ServiceName Start SERVICE_AUTO_START

# Set up logging
$logDir = "C:\Tools\nssm\logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
nssm set $ServiceName AppStdout "$logDir\vofc_flask_out.log"
nssm set $ServiceName AppStderr "$logDir\vofc_flask_err.log"
nssm set $ServiceName AppStdoutCreationDisposition 4
nssm set $ServiceName AppStderrCreationDisposition 4
nssm set $ServiceName AppRotateFiles 1
nssm set $ServiceName AppRotateOnline 1
nssm set $ServiceName AppRotateBytes 10485760
nssm set $ServiceName AppRotateSeconds 86400

# Set restart behavior
nssm set $ServiceName AppExit Default Restart
nssm set $ServiceName AppRestartDelay 5000

Write-Host "  ✓ Service configured" -ForegroundColor Green

# Start service
Write-Host "Starting service..." -ForegroundColor Cyan
nssm start $ServiceName
Start-Sleep -Seconds 3

# Check status
$status = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($status -and $status.Status -eq 'Running') {
    Write-Host "  ✓ Service is running" -ForegroundColor Green
} else {
    Write-Host "  ✗ Service failed to start" -ForegroundColor Red
    Write-Host "  Check logs: $logDir\vofc_flask_err.log" -ForegroundColor Yellow
    exit 1
}

# Verify Flask is listening on port 8080
Write-Host "Verifying Flask is listening on port 8080..." -ForegroundColor Cyan
Start-Sleep -Seconds 2
$listening = netstat -ano | Select-String ":8080" | Select-String "LISTENING"
if ($listening) {
    Write-Host "  ✓ Flask is listening on port 8080" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Port 8080 not yet listening (may need a moment)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Flask service installed and started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Test with:" -ForegroundColor Cyan
Write-Host "  curl http://localhost:8080/api/system/health" -ForegroundColor White
Write-Host ""
Write-Host "Next step: Fix and start the tunnel service:" -ForegroundColor Yellow
Write-Host "  .\scripts\fix-tunnel-service-complete.ps1" -ForegroundColor White
Write-Host ""

