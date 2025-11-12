# Production Pattern Extractor - PowerShell Wrapper
# Ensures the script runs with the correct Python interpreter

$ErrorActionPreference = "Stop"

# Try to find Python in common locations (check C:\Tools\python first)
$pythonPaths = @(
    "C:\Tools\python\python.exe",  # Project-specific location
    "C:\Program Files\Python311\python.exe",
    "C:\Program Files (x86)\Python311\python.exe",
    "C:\Python311\python.exe",
    "C:\Program Files\Python312\python.exe",
    "C:\Program Files (x86)\Python312\python.exe",
    "C:\Python312\python.exe"
)

$pythonExe = $null

# Check for Python in common locations
foreach ($path in $pythonPaths) {
    if (Test-Path $path) {
        $pythonExe = $path
        break
    }
}

# Try py launcher
if (-not $pythonExe) {
    try {
        $pyVersion = & py -3 --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonExe = "py -3"
        }
    } catch {
        # py launcher not available
    }
}

# Try python in PATH
if (-not $pythonExe) {
    try {
        $pythonVersion = & python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonExe = "python"
        }
    } catch {
        # python not in PATH
    }
}

# If no Python found, show error
if (-not $pythonExe) {
    Write-Host "ERROR: Python not found. Please install Python 3.11 or later." -ForegroundColor Red
    Write-Host ""
    Write-Host "Checked locations:"
    foreach ($path in $pythonPaths) {
        Write-Host "  - $path"
    }
    exit 1
}

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $scriptDir "extract_production_patterns.py"

Write-Host "Using Python: $pythonExe" -ForegroundColor Green
Write-Host "Running: $scriptPath" -ForegroundColor Cyan
Write-Host ""

# Run the script
try {
    if ($pythonExe -match "^py ") {
        # py launcher
        & $pythonExe $scriptPath $args
    } else {
        # Full path or python command
        & $pythonExe $scriptPath $args
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Script failed with error code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} catch {
    Write-Host ""
    Write-Host "Error running script: $_" -ForegroundColor Red
    exit 1
}

