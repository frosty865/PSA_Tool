# Fix Model Manager Service Python Path
# Updates the existing service to use the virtual environment Python
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix VOFC-ModelManager Python Path" -ForegroundColor Cyan
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

Write-Host "✅ Running as Administrator" -ForegroundColor Green
Write-Host ""

# Auto-detect project root
$scriptLocation = $PSScriptRoot
if ($scriptLocation -match '\\scripts$') {
    $projectRoot = Split-Path $scriptLocation -Parent
} else {
    $projectRoot = $scriptLocation
}

$serviceName = "VOFC-ModelManager"

# Check if service exists
$existingStatus = nssm status $serviceName 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Service '$serviceName' not found!" -ForegroundColor Red
    Write-Host "   Please install the service first using install-vofc-model-manager.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Service found: $serviceName" -ForegroundColor Green
Write-Host "   Current status: $existingStatus" -ForegroundColor Cyan
Write-Host ""

# Find Python path
$venvPython = Join-Path $projectRoot "venv\Scripts\python.exe"
$systemPython = "C:\Program Files\Python311\python.exe"

if (Test-Path $venvPython) {
    $pythonPath = $venvPython
    Write-Host "✅ Found virtual environment Python: $pythonPath" -ForegroundColor Green
} elseif (Test-Path $systemPython) {
    $pythonPath = $systemPython
    Write-Host "⚠️  Virtual environment not found, using system Python: $pythonPath" -ForegroundColor Yellow
    Write-Host "   Note: Make sure dependencies are installed: pip install -r requirements.txt" -ForegroundColor Yellow
} else {
    Write-Host "❌ Python not found!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Stopping service..." -ForegroundColor Yellow
nssm stop $serviceName 2>&1 | Out-Null
Start-Sleep -Seconds 2

Write-Host "Updating Python path..." -ForegroundColor Yellow
nssm set $serviceName Application $pythonPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to update Python path!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Python path updated" -ForegroundColor Green
Write-Host ""

# Verify the script path is still correct
$scriptPath = Join-Path $projectRoot "services\model_manager.py"
if (-not (Test-Path $scriptPath)) {
    Write-Host "❌ Script not found at: $scriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Verifying script path..." -ForegroundColor Yellow
nssm set $serviceName AppParameters "`"$scriptPath`""

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Warning: Failed to update script path" -ForegroundColor Yellow
}

Write-Host "✅ Script path verified" -ForegroundColor Green
Write-Host ""

# Test Python can import dependencies
Write-Host "Testing Python dependencies..." -ForegroundColor Yellow
$testCmd = "& `"$pythonPath`" -c `"import requests; import supabase; print('OK')`""
try {
    $result = Invoke-Expression $testCmd 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python dependencies are available" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Warning: Some dependencies may be missing" -ForegroundColor Yellow
        Write-Host "   Install with: & `"$pythonPath`" -m pip install -r requirements.txt" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Warning: Could not test dependencies" -ForegroundColor Yellow
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
    Write-Host "Check the logs:" -ForegroundColor Cyan
    Write-Host "  C:\Tools\VOFC_Logs\model_manager.log" -ForegroundColor White
    Write-Host "  C:\Tools\VOFC_Logs\model_manager.err.log" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Update Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

