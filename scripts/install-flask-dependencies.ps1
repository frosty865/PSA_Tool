# Install Flask Dependencies and Fix Service
# Run this script as Administrator

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Install Flask Dependencies" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$FlaskService = "vofc-flask"
$FlaskDir = "C:\Tools\VOFC-Flask"
$PythonExe = "$FlaskDir\venv\Scripts\python.exe"
$RequirementsFile = "$FlaskDir\requirements.txt"

# Stop service
Write-Host "Stopping Flask service..." -ForegroundColor Cyan
nssm stop $FlaskService -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Verify paths
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: Python executable not found: $PythonExe" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $FlaskDir)) {
    Write-Host "ERROR: Flask directory not found: $FlaskDir" -ForegroundColor Red
    exit 1
}

# Change to Flask directory
Set-Location $FlaskDir

# Upgrade pip first
Write-Host "Upgrading pip..." -ForegroundColor Cyan
& $PythonExe -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠ pip upgrade had issues, but continuing..." -ForegroundColor Yellow
}

# Install dependencies
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Cyan
if (Test-Path $RequirementsFile) {
    Write-Host "  Reading: $RequirementsFile" -ForegroundColor Gray
    & $PythonExe -m pip install -r $RequirementsFile
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Failed to install from requirements.txt" -ForegroundColor Red
        Write-Host "  Attempting to install core dependencies directly..." -ForegroundColor Yellow
        
        # Install core dependencies manually
        & $PythonExe -m pip install waitress flask flask-cors python-dotenv supabase requests pandas openpyxl
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ✗ Failed to install core dependencies" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "  ✓ Dependencies installed from requirements.txt" -ForegroundColor Green
    }
} else {
    Write-Host "  requirements.txt not found, installing core dependencies..." -ForegroundColor Yellow
    & $PythonExe -m pip install waitress flask flask-cors python-dotenv supabase requests pandas openpyxl
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Failed to install dependencies" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "  ✓ Core dependencies installed" -ForegroundColor Green
    }
}

# Verify critical modules
Write-Host "Verifying critical modules..." -ForegroundColor Cyan

$modules = @("waitress", "flask", "flask_cors")
$allGood = $true

foreach ($module in $modules) {
    $check = & $PythonExe -c "import $($module.Replace('_', '.')); print('OK')" 2>&1
    if ($check -match "OK") {
        Write-Host "  ✓ $module is installed" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $module is NOT installed: $check" -ForegroundColor Red
        $allGood = $false
    }
}

if (-not $allGood) {
    Write-Host ""
    Write-Host "ERROR: Some critical modules are missing!" -ForegroundColor Red
    Write-Host "Attempting to install missing modules..." -ForegroundColor Yellow
    & $PythonExe -m pip install waitress flask flask-cors
    exit 1
}

# Verify app.py can be imported
Write-Host "Verifying app.py can be imported..." -ForegroundColor Cyan
$appCheck = & $PythonExe -c "import sys; sys.path.insert(0, r'$FlaskDir'); import app; print('OK')" 2>&1
if ($appCheck -match "OK") {
    Write-Host "  ✓ app.py can be imported" -ForegroundColor Green
} else {
    Write-Host "  ⚠ app.py import check: $appCheck" -ForegroundColor Yellow
    Write-Host "  (This may be OK if it's just missing optional dependencies)" -ForegroundColor Gray
}

# Start service
Write-Host ""
Write-Host "Starting Flask service..." -ForegroundColor Cyan
nssm start $FlaskService
Start-Sleep -Seconds 5

# Check status
$status = Get-Service -Name $FlaskService -ErrorAction SilentlyContinue
if ($status) {
    Write-Host "Service status: $($status.Status)" -ForegroundColor $(if ($status.Status -eq 'Running') { 'Green' } else { 'Yellow' })
    
    if ($status.Status -eq 'Paused') {
        Write-Host ""
        Write-Host "Service is PAUSED. Checking logs..." -ForegroundColor Yellow
        if (Test-Path "C:\Tools\nssm\logs\vofc_flask_err.log") {
            Write-Host "Last 10 lines of error log:" -ForegroundColor Cyan
            Get-Content "C:\Tools\nssm\logs\vofc_flask_err.log" -Tail 10
        }
        Write-Host ""
        Write-Host "Try manually starting the service:" -ForegroundColor Yellow
        Write-Host "  nssm start $FlaskService" -ForegroundColor White
        Write-Host ""
        Write-Host "Or test manually:" -ForegroundColor Yellow
        Write-Host "  cd $FlaskDir" -ForegroundColor White
        Write-Host "  .\venv\Scripts\python.exe -m waitress --listen=0.0.0.0:8080 server:app" -ForegroundColor White
    } elseif ($status.Status -eq 'Running') {
        Write-Host "  ✓ Service is running!" -ForegroundColor Green
        
        # Verify port
        Start-Sleep -Seconds 2
        $listening = netstat -ano | Select-String ":8080" | Select-String "LISTENING"
        if ($listening) {
            Write-Host "  ✓ Flask is listening on port 8080" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Port 8080 not yet listening (may need more time)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  ✗ Could not get service status" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Done!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

