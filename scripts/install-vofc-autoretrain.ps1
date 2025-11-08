# Install VOFC Auto-Retrain Job as Windows Service
# This script sets up the auto-retrain job to run nightly/weekly

$ErrorActionPreference = "Stop"

# Configuration
$SERVICE_NAME = "VOFC-AutoRetrain"
$SCRIPT_PATH = "C:\Tools\auto_retrain_job.py"
$PROJECT_ROOT = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# Detect Python executable (prefer venv)
$PYTHON_EXE = $null
$VENV_PYTHON = Join-Path $PROJECT_ROOT "venv\Scripts\python.exe"
if (Test-Path $VENV_PYTHON) {
    $PYTHON_EXE = $VENV_PYTHON
    Write-Host "Using virtual environment Python: $PYTHON_EXE" -ForegroundColor Green
} else {
    # Try to find Python in common locations
    $PYTHON_PATHS = @(
        "C:\Program Files\Python311\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python312\python.exe",
        "python.exe"  # System PATH
    )
    
    foreach ($path in $PYTHON_PATHS) {
        if (Test-Path $path) {
            $PYTHON_EXE = $path
            Write-Host "Using Python: $PYTHON_EXE" -ForegroundColor Yellow
            break
        }
    }
    
    if (-not $PYTHON_EXE) {
        Write-Host "ERROR: Python executable not found!" -ForegroundColor Red
        Write-Host "Please install Python or create a virtual environment." -ForegroundColor Red
        exit 1
    }
}

# Verify script exists
if (-not (Test-Path $SCRIPT_PATH)) {
    Write-Host "ERROR: Script not found at: $SCRIPT_PATH" -ForegroundColor Red
    Write-Host "Please ensure the auto_retrain_job.py file is located at C:\Tools\" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n=== Installing VOFC Auto-Retrain Service ===" -ForegroundColor Cyan
Write-Host "Service Name: $SERVICE_NAME"
Write-Host "Python: $PYTHON_EXE"
Write-Host "Script: $SCRIPT_PATH"
Write-Host "Working Directory: $PROJECT_ROOT"
Write-Host ""

# Check if NSSM is available
$NSSM = "nssm"
try {
    $null = Get-Command $NSSM -ErrorAction Stop
} catch {
    Write-Host "ERROR: NSSM not found in PATH!" -ForegroundColor Red
    Write-Host "Please install NSSM or add it to your PATH." -ForegroundColor Red
    exit 1
}

# Check if service already exists
$existing = Get-Service -Name $SERVICE_NAME -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Service already exists. Removing existing service..." -ForegroundColor Yellow
    nssm stop $SERVICE_NAME
    Start-Sleep -Seconds 2
    nssm remove $SERVICE_NAME confirm
    Start-Sleep -Seconds 1
}

# Install service
Write-Host "Installing service..." -ForegroundColor Green
nssm install $SERVICE_NAME $PYTHON_EXE "$SCRIPT_PATH"

# Configure service
Write-Host "Configuring service parameters..." -ForegroundColor Green

# Set working directory (use project root for training_data access)
nssm set $SERVICE_NAME AppDirectory $PROJECT_ROOT

# Set output files
$LOG_DIR = "C:\Tools\VOFC_Logs"
New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null
nssm set $SERVICE_NAME AppStdout (Join-Path $LOG_DIR "autoretrain_stdout.log")
nssm set $SERVICE_NAME AppStderr (Join-Path $LOG_DIR "autoretrain_stderr.log")

# Set restart behavior
nssm set $SERVICE_NAME AppExit Default Restart

# Set startup type
nssm set $SERVICE_NAME Start SERVICE_AUTO_START

# Optional: Set recovery options (restart on failure)
Write-Host "Configuring recovery options..." -ForegroundColor Green
nssm set $SERVICE_NAME AppRestartDelay 60000  # 1 minute delay before restart
nssm set $SERVICE_NAME AppThrottle 300000      # 5 minute throttle (max 1 restart per 5 min)

# Load environment variables from .env if it exists
$ENV_FILE = Join-Path $PROJECT_ROOT ".env"
if (Test-Path $ENV_FILE) {
    Write-Host "Loading environment variables from .env file..." -ForegroundColor Green
    $envVars = @()
    
    Get-Content $ENV_FILE | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"').Trim("'")
            if ($key -and $value) {
                $envVars += "$key=$value"
            }
        }
    }
    
    if ($envVars.Count -gt 0) {
        $envString = $envVars -join "`n"
        nssm set $SERVICE_NAME AppEnvironmentExtra $envString
        Write-Host "Set $($envVars.Count) environment variables" -ForegroundColor Green
    }
} else {
    Write-Host "Warning: .env file not found. Service will use system environment variables." -ForegroundColor Yellow
}

# Verify configuration
Write-Host "`n=== Service Configuration ===" -ForegroundColor Cyan
nssm get $SERVICE_NAME App
nssm get $SERVICE_NAME AppDirectory
nssm get $SERVICE_NAME Start

Write-Host "`n=== Installation Complete ===" -ForegroundColor Green
Write-Host "Service Name: $SERVICE_NAME"
Write-Host "`nTo start the service, run:" -ForegroundColor Yellow
Write-Host "  nssm start $SERVICE_NAME" -ForegroundColor White
Write-Host "`nTo check service status:" -ForegroundColor Yellow
Write-Host "  sc query $SERVICE_NAME" -ForegroundColor White
Write-Host "`nLogs will be written to:" -ForegroundColor Yellow
Write-Host "  $LOG_DIR\auto_retrain_job.log" -ForegroundColor White
Write-Host "  $LOG_DIR\autoretrain_stdout.log" -ForegroundColor White
Write-Host "  $LOG_DIR\autoretrain_stderr.log" -ForegroundColor White

