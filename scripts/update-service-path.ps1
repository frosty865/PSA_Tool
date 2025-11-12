# update-service-path.ps1
# Updates VOFC-Processor service to use C:\Tools\VOFC path instead of Programs path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Updating VOFC-Processor Service Path" -ForegroundColor Cyan
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
$PythonPath = "C:\Program Files\Python311\python.exe"
$ScriptPath = "C:\Tools\VOFC\tools\vofc_processor\vofc_processor.py"
$AppDirectory = "C:\Tools\VOFC\tools\vofc_processor"

# Verify paths exist
Write-Host "Step 1: Verifying paths..." -ForegroundColor Yellow

if (-not (Test-Path $PythonPath)) {
    Write-Host "  ✗ Python not found at: $PythonPath" -ForegroundColor Red
    $PythonPath = "C:\Python311\python.exe"
    if (-not (Test-Path $PythonPath)) {
        Write-Host "  ✗ Python not found at: $PythonPath" -ForegroundColor Red
        Write-Host "  Please install Python 3.11 or update the path" -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "  ✓ Python found: $PythonPath" -ForegroundColor Green

if (-not (Test-Path $ScriptPath)) {
    Write-Host "  ✗ Script not found at: $ScriptPath" -ForegroundColor Red
    Write-Host "  Please ensure files are copied to C:\Tools\VOFC\tools\vofc_processor\" -ForegroundColor Yellow
    exit 1
}
Write-Host "  ✓ Script found: $ScriptPath" -ForegroundColor Green

if (-not (Test-Path $AppDirectory)) {
    Write-Host "  ✗ Directory not found: $AppDirectory" -ForegroundColor Red
    Write-Host "  Creating directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $AppDirectory -Force | Out-Null
    Write-Host "  ✓ Directory created" -ForegroundColor Green
} else {
    Write-Host "  ✓ Directory exists: $AppDirectory" -ForegroundColor Green
}
Write-Host ""

# Check if service exists
Write-Host "Step 2: Checking service status..." -ForegroundColor Yellow
$status = nssm status $ServiceName 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Service not found: $ServiceName" -ForegroundColor Red
    Write-Host "  Please install the service first using install_service.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Host "  ✓ Service exists" -ForegroundColor Green
Write-Host "  Current status: $status" -ForegroundColor Gray
Write-Host ""

# Stop service if running
if ($status -eq "SERVICE_RUNNING" -or $status -eq "SERVICE_PAUSED") {
    Write-Host "Step 3: Stopping service..." -ForegroundColor Yellow
    nssm stop $ServiceName 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    $newStatus = nssm status $ServiceName 2>&1
    if ($newStatus -eq "SERVICE_STOPPED") {
        Write-Host "  ✓ Service stopped" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Service status: $newStatus" -ForegroundColor Yellow
    }
} else {
    Write-Host "Step 3: Service already stopped" -ForegroundColor Gray
}
Write-Host ""

# Update service configuration
Write-Host "Step 4: Updating service configuration..." -ForegroundColor Yellow

Write-Host "  Setting Application..." -ForegroundColor Gray
nssm set $ServiceName Application $PythonPath 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "    ✓ Application set" -ForegroundColor Green
} else {
    Write-Host "    ✗ Failed to set Application" -ForegroundColor Red
}

Write-Host "  Setting AppParameters..." -ForegroundColor Gray
nssm set $ServiceName AppParameters $ScriptPath 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "    ✓ AppParameters set" -ForegroundColor Green
} else {
    Write-Host "    ✗ Failed to set AppParameters" -ForegroundColor Red
}

Write-Host "  Setting AppDirectory..." -ForegroundColor Gray
nssm set $ServiceName AppDirectory $AppDirectory 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "    ✓ AppDirectory set" -ForegroundColor Green
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
Write-Host "Service Path Update Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service: $ServiceName" -ForegroundColor White
Write-Host "Script Path: $ScriptPath" -ForegroundColor White
Write-Host "Working Directory: $AppDirectory" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Start the service: nssm start $ServiceName" -ForegroundColor Gray
Write-Host "  2. Check status: nssm status $ServiceName" -ForegroundColor Gray
Write-Host "  3. Check logs: Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_out.log -Tail 20" -ForegroundColor Gray
Write-Host ""

