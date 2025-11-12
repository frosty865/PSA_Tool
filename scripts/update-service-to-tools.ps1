# update-service-to-tools.ps1
# Updates VOFC-Processor service to use C:\Tools\python and C:\Tools\py_scripts
# For server deployment - all services run from C:\Tools

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Updating VOFC-Processor to C:\Tools" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$ServiceName = "VOFC-Processor"
$PythonPath = "C:\Tools\python\python.exe"
$ScriptPath = "C:\Tools\py_scripts\vofc_processor\vofc_processor.py"
$AppDirectory = "C:\Tools\py_scripts\vofc_processor"

# Verify Python path
Write-Host "Step 1: Verifying Python..." -ForegroundColor Yellow
if (-not (Test-Path $PythonPath)) {
    $PythonPath = "C:\Tools\python.exe"
    if (-not (Test-Path $PythonPath)) {
        Write-Host "  ✗ Python not found at C:\Tools\python\" -ForegroundColor Red
        Write-Host "  Please ensure Python is installed at C:\Tools\python\" -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "  ✓ Python found: $PythonPath" -ForegroundColor Green

# Verify script path
Write-Host "Step 2: Verifying script location..." -ForegroundColor Yellow
if (-not (Test-Path $ScriptPath)) {
    Write-Host "  ✗ Script not found at: $ScriptPath" -ForegroundColor Red
    Write-Host "  Please ensure vofc_processor.py is at C:\Tools\py_scripts\vofc_processor\" -ForegroundColor Yellow
    exit 1
}
Write-Host "  ✓ Script found: $ScriptPath" -ForegroundColor Green
Write-Host ""

# Check service status
Write-Host "Step 3: Checking service status..." -ForegroundColor Yellow
$status = nssm status $ServiceName 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Service not found: $ServiceName" -ForegroundColor Red
    Write-Host "  Please install the service first using install_service.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Host "  ✓ Service exists" -ForegroundColor Green
Write-Host "  Current status: $status" -ForegroundColor Gray

# Stop service if running
if ($status -eq "SERVICE_RUNNING" -or $status -eq "SERVICE_PAUSED") {
    Write-Host "  Stopping service..." -ForegroundColor Gray
    nssm stop $ServiceName 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    $newStatus = nssm status $ServiceName 2>&1
    if ($newStatus -eq "SERVICE_STOPPED") {
        Write-Host "  ✓ Service stopped" -ForegroundColor Green
    }
}
Write-Host ""

# Update service configuration
Write-Host "Step 4: Updating service configuration..." -ForegroundColor Yellow

Write-Host "  Setting Application (Python)..." -ForegroundColor Gray
nssm set $ServiceName Application $PythonPath 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "    ✓ Application set to: $PythonPath" -ForegroundColor Green
} else {
    Write-Host "    ✗ Failed to set Application" -ForegroundColor Red
}

Write-Host "  Setting AppParameters (Script)..." -ForegroundColor Gray
nssm set $ServiceName AppParameters $ScriptPath 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "    ✓ AppParameters set to: $ScriptPath" -ForegroundColor Green
} else {
    Write-Host "    ✗ Failed to set AppParameters" -ForegroundColor Red
}

Write-Host "  Setting AppDirectory (Working Directory)..." -ForegroundColor Gray
nssm set $ServiceName AppDirectory $AppDirectory 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "    ✓ AppDirectory set to: $AppDirectory" -ForegroundColor Green
} else {
    Write-Host "    ✗ Failed to set AppDirectory" -ForegroundColor Red
}
Write-Host ""

# Verify configuration
Write-Host "Step 5: Verifying configuration..." -ForegroundColor Yellow
$verifyApp = nssm get $ServiceName Application 2>&1
$verifyParams = nssm get $ServiceName AppParameters 2>&1
$verifyDir = nssm get $ServiceName AppDirectory 2>&1

Write-Host "  Application: $verifyApp" -ForegroundColor $(if ($verifyApp -eq $PythonPath) { 'Green' } else { 'Yellow' })
Write-Host "  AppParameters: $verifyParams" -ForegroundColor $(if ($verifyParams -eq $ScriptPath) { 'Green' } else { 'Yellow' })
Write-Host "  AppDirectory: $verifyDir" -ForegroundColor $(if ($verifyDir -eq $AppDirectory) { 'Green' } else { 'Yellow' })
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Service Updated Successfully!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service: $ServiceName" -ForegroundColor White
Write-Host "Python: $PythonPath" -ForegroundColor White
Write-Host "Script: $ScriptPath" -ForegroundColor White
Write-Host "Working Directory: $AppDirectory" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Install Python dependencies:" -ForegroundColor Gray
Write-Host "     & `"$PythonPath`" -m pip install -r C:\Tools\py_scripts\vofc_processor\requirements.txt" -ForegroundColor DarkGray
Write-Host "  2. Start the service: nssm start $ServiceName" -ForegroundColor Gray
Write-Host "  3. Check status: nssm status $ServiceName" -ForegroundColor Gray
Write-Host "  4. Check logs: Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_out.log -Tail 20" -ForegroundColor Gray
Write-Host ""

