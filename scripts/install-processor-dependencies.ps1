# Install Dependencies for VOFC-Processor Service
# This script installs required Python packages in the service's Python environment

Write-Host "Installing VOFC-Processor Dependencies..." -ForegroundColor Cyan
Write-Host ""

# Service configuration
$ServiceName = "VOFC-Processor"
$TargetDir = "C:\Tools\VOFC-Processor"

# Find Python executable used by the service
$PythonPath = $null

# Check NSSM for the service's Python path
try {
    $nssmPath = "C:\Tools\nssm\nssm.exe"
    if (-not (Test-Path $nssmPath)) {
        $nssmPath = "nssm"
    }
    
    $serviceApp = & $nssmPath get $ServiceName Application 2>&1
    if ($LASTEXITCODE -eq 0 -and $serviceApp) {
        $PythonPath = $serviceApp.Trim()
        Write-Host "Found Python from service configuration: $PythonPath" -ForegroundColor Green
    }
} catch {
    Write-Host "Could not read service configuration, trying common paths..." -ForegroundColor Yellow
}

# Try common Python paths if service config didn't work
if (-not $PythonPath -or -not (Test-Path $PythonPath)) {
    $possiblePaths = @(
        "C:\Tools\python\python.exe",
        "C:\Tools\python.exe",
        "python.exe"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $PythonPath = $path
            Write-Host "Found Python at: $PythonPath" -ForegroundColor Green
            break
        }
    }
}

if (-not $PythonPath -or -not (Test-Path $PythonPath)) {
    Write-Host "Error: Python not found. Please ensure Python is installed." -ForegroundColor Red
    Write-Host "Tried paths:" -ForegroundColor Yellow
    Write-Host "  - C:\Tools\python\python.exe" -ForegroundColor Yellow
    Write-Host "  - C:\Tools\python.exe" -ForegroundColor Yellow
    Write-Host "  - python.exe (from PATH)" -ForegroundColor Yellow
    exit 1
}

# Check if requirements.txt exists
$RequirementsFile = Join-Path $TargetDir "requirements.txt"
if (-not (Test-Path $RequirementsFile)) {
    # Try project root
    $ProjectRequirements = Join-Path $PSScriptRoot "..\requirements.txt"
    if (Test-Path $ProjectRequirements) {
        Write-Host "Copying requirements.txt from project root..." -ForegroundColor Yellow
        Copy-Item $ProjectRequirements $RequirementsFile -Force
    } else {
        Write-Host "Warning: requirements.txt not found. Installing watchdog only..." -ForegroundColor Yellow
        Write-Host "Installing watchdog..." -ForegroundColor Cyan
        & $PythonPath -m pip install watchdog==3.0.0
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ watchdog installed successfully!" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to install watchdog" -ForegroundColor Red
            exit 1
        }
        exit 0
    }
}

# Install all requirements
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Cyan
Write-Host "  Python: $PythonPath" -ForegroundColor Gray
Write-Host "  Requirements: $RequirementsFile" -ForegroundColor Gray
Write-Host ""

# Upgrade pip first
Write-Host "Upgrading pip..." -ForegroundColor Cyan
& $PythonPath -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: pip upgrade failed, continuing anyway..." -ForegroundColor Yellow
}

# Install requirements
Write-Host "Installing packages..." -ForegroundColor Cyan
& $PythonPath -m pip install -r $RequirementsFile

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ All dependencies installed successfully!" -ForegroundColor Green
    
    # Verify watchdog specifically
    Write-Host ""
    Write-Host "Verifying watchdog installation..." -ForegroundColor Cyan
    $watchdogCheck = & $PythonPath -c "import watchdog; print(watchdog.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ watchdog version: $watchdogCheck" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Warning: Could not verify watchdog installation" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "❌ Failed to install some dependencies" -ForegroundColor Red
    Write-Host "Please check the error messages above" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Restart the VOFC-Processor service:" -ForegroundColor White
Write-Host "     nssm restart $ServiceName" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Check service status:" -ForegroundColor White
Write-Host "     nssm status $ServiceName" -ForegroundColor Gray
Write-Host ""

