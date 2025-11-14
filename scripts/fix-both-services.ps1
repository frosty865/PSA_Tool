# Fix Both Flask and Tunnel Services
# Run this script as Administrator

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix Flask and Tunnel Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# ========================================
# FIX 1: Flask Service - Install Dependencies
# ========================================
Write-Host "Step 1: Fixing Flask Service..." -ForegroundColor Yellow
Write-Host ""

$FlaskService = "vofc-flask"
$FlaskDir = "C:\Tools\VOFC-Flask"
$PythonExe = "$FlaskDir\venv\Scripts\python.exe"
$RequirementsFile = "$FlaskDir\requirements.txt"
$AppParameters = "-m waitress --listen=0.0.0.0:8080 server:app"  # Use server.py, not app.py

# Stop Flask service
Write-Host "  Stopping Flask service..." -ForegroundColor Cyan
nssm stop $FlaskService -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Check if Python and venv exist
if (-not (Test-Path $PythonExe)) {
    Write-Host "  ERROR: Python executable not found: $PythonExe" -ForegroundColor Red
    Write-Host "  Please create virtual environment first:" -ForegroundColor Yellow
    Write-Host "    cd $FlaskDir" -ForegroundColor Cyan
    Write-Host "    python -m venv venv" -ForegroundColor Cyan
    Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host "    pip install -r requirements.txt" -ForegroundColor Cyan
    exit 1
}

# Install waitress and other dependencies
Write-Host "  Installing Python dependencies (waitress, etc.)..." -ForegroundColor Cyan
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
Write-Host "  Verifying waitress installation..." -ForegroundColor Cyan
$waitressCheck = & $PythonExe -c "import waitress; print('OK')" 2>&1
if ($waitressCheck -match "OK") {
    Write-Host "  ✓ waitress is installed" -ForegroundColor Green
} else {
    Write-Host "  ✗ waitress verification failed: $waitressCheck" -ForegroundColor Red
    exit 1
}

# Start Flask service
Write-Host "  Starting Flask service..." -ForegroundColor Cyan
nssm start $FlaskService
Start-Sleep -Seconds 3

# Check Flask status
$flaskStatus = Get-Service -Name $FlaskService -ErrorAction SilentlyContinue
if ($flaskStatus -and $flaskStatus.Status -eq 'Running') {
    Write-Host "  ✓ Flask service is running" -ForegroundColor Green
} else {
    Write-Host "  ✗ Flask service failed to start" -ForegroundColor Red
    Write-Host "  Check logs: C:\Tools\nssm\logs\vofc_flask_err.log" -ForegroundColor Yellow
    Get-Content "C:\Tools\nssm\logs\vofc_flask_err.log" -Tail 5 -ErrorAction SilentlyContinue
}

# Verify Flask is listening
Write-Host "  Verifying Flask is listening on port 8080..." -ForegroundColor Cyan
Start-Sleep -Seconds 2
$listening = netstat -ano | Select-String ":8080" | Select-String "LISTENING"
if ($listening) {
    Write-Host "  ✓ Flask is listening on port 8080" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Port 8080 not yet listening (may need more time)" -ForegroundColor Yellow
}

Write-Host ""

# ========================================
# FIX 2: Tunnel Service - Fix Config Path
# ========================================
Write-Host "Step 2: Fixing Tunnel Service..." -ForegroundColor Yellow
Write-Host ""

$TunnelService = "VOFC-Tunnel"
$CorrectConfigPath = "C:\Tools\cloudflared\config.yaml"
$WrongConfigPath = "C:\Users\frost\cloudflared\config.yml"

# Stop tunnel service
Write-Host "  Stopping tunnel service..." -ForegroundColor Cyan
nssm stop $TunnelService -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Check if correct config exists
if (-not (Test-Path $CorrectConfigPath)) {
    Write-Host "  ERROR: Config file not found: $CorrectConfigPath" -ForegroundColor Red
    Write-Host "  Please ensure the config file exists at the correct location." -ForegroundColor Yellow
    exit 1
}

# Check current config path
$currentParams = nssm get $TunnelService AppParameters
Write-Host "  Current parameters: $currentParams" -ForegroundColor Gray

# Update config path if needed
if ($currentParams -match [regex]::Escape($WrongConfigPath)) {
    Write-Host "  Updating config path to correct location..." -ForegroundColor Cyan
    $newParams = $currentParams -replace [regex]::Escape($WrongConfigPath), $CorrectConfigPath
    nssm set $TunnelService AppParameters $newParams
    Write-Host "  ✓ Config path updated" -ForegroundColor Green
} elseif ($currentParams -match [regex]::Escape($CorrectConfigPath)) {
    Write-Host "  ✓ Config path is already correct" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Config path doesn't match expected pattern" -ForegroundColor Yellow
    Write-Host "  Setting to correct path..." -ForegroundColor Cyan
    nssm set $TunnelService AppParameters "--config $CorrectConfigPath tunnel run ollama-tunnel"
    Write-Host "  ✓ Config path set" -ForegroundColor Green
}

# Remove incorrect dependency (if still exists)
Write-Host "  Removing incorrect service dependency..." -ForegroundColor Cyan
$currentDep = nssm get $TunnelService DependOnService
if ($currentDep -and $currentDep -ne "") {
    Write-Host "    Current dependency: $currentDep (removing)" -ForegroundColor Yellow
    nssm set $TunnelService DependOnService ""
    Write-Host "    ✓ Dependency removed" -ForegroundColor Green
} else {
    Write-Host "    ✓ No dependency set" -ForegroundColor Green
}

# Start tunnel service
Write-Host "  Starting tunnel service..." -ForegroundColor Cyan
nssm start $TunnelService
Start-Sleep -Seconds 3

# Check tunnel status
$tunnelStatus = Get-Service -Name $TunnelService -ErrorAction SilentlyContinue
if ($tunnelStatus -and $tunnelStatus.Status -eq 'Running') {
    Write-Host "  ✓ Tunnel service is running" -ForegroundColor Green
} else {
    Write-Host "  ✗ Tunnel service failed to start" -ForegroundColor Red
    Write-Host "  Check logs: C:\Tools\nssm\logs\vofc_tunnel_err.log" -ForegroundColor Yellow
    Get-Content "C:\Tools\nssm\logs\vofc_tunnel_err.log" -Tail 5 -ErrorAction SilentlyContinue
}

Write-Host ""

# ========================================
# Summary
# ========================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$flaskStatus = Get-Service -Name $FlaskService -ErrorAction SilentlyContinue
$tunnelStatus = Get-Service -Name $TunnelService -ErrorAction SilentlyContinue

Write-Host "Flask Service ($FlaskService):" -ForegroundColor Cyan
if ($flaskStatus -and $flaskStatus.Status -eq 'Running') {
    Write-Host "  Status: RUNNING ✓" -ForegroundColor Green
} else {
    Write-Host "  Status: $($flaskStatus.Status) ✗" -ForegroundColor Red
}

Write-Host "Tunnel Service ($TunnelService):" -ForegroundColor Cyan
if ($tunnelStatus -and $tunnelStatus.Status -eq 'Running') {
    Write-Host "  Status: RUNNING ✓" -ForegroundColor Green
} else {
    Write-Host "  Status: $($tunnelStatus.Status) ✗" -ForegroundColor Red
}

Write-Host ""

if (($flaskStatus -and $flaskStatus.Status -eq 'Running') -and ($tunnelStatus -and $tunnelStatus.Status -eq 'Running')) {
    Write-Host "✓ Both services are running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Test with:" -ForegroundColor Cyan
    Write-Host "  curl http://localhost:8080/api/system/health" -ForegroundColor White
    Write-Host "  curl https://flask.frostech.site/api/system/health" -ForegroundColor White
} else {
    Write-Host "⚠ Some services failed to start. Check logs above." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Log locations:" -ForegroundColor Cyan
    Write-Host "  Flask: C:\Tools\nssm\logs\vofc_flask_err.log" -ForegroundColor White
    Write-Host "  Tunnel: C:\Tools\nssm\logs\vofc_tunnel_err.log" -ForegroundColor White
}

Write-Host ""

