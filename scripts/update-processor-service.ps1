# Update VOFC-Processor Service
# Run this script as Administrator to update the service with latest code

Write-Host "Updating VOFC-Processor Service..." -ForegroundColor Cyan

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$ServiceName = "VOFC-Processor"
$ProjectRoot = "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool"
$SourceDir = Join-Path $ProjectRoot "tools\vofc_processor"
$TargetDir = "C:\Tools\VOFC-Processor"
$LegacyDir = "C:\Tools\vofc_processor"

# Ensure target directories exist
if (-not (Test-Path $TargetDir)) {
    Write-Host "Creating $TargetDir..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

# Copy updated files
Write-Host "Copying updated files..." -ForegroundColor Cyan
if (Test-Path $SourceDir) {
    # Copy main script
    $sourceFile = Join-Path $SourceDir "vofc_processor.py"
    $targetFile = Join-Path $TargetDir "vofc_processor.py"
    if (Test-Path $sourceFile) {
        Copy-Item $sourceFile $targetFile -Force
        Write-Host "  ✓ Copied vofc_processor.py" -ForegroundColor Green
    }
    
    # Copy subdirectories
    Get-ChildItem $SourceDir -Directory | ForEach-Object {
        $targetSubDir = Join-Path $TargetDir $_.Name
        Copy-Item $_.FullName $targetSubDir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  ✓ Copied $($_.Name)" -ForegroundColor Green
    }
    
    # Also copy to legacy location for compatibility
    if (Test-Path $LegacyDir) {
        Copy-Item $sourceFile (Join-Path $LegacyDir "vofc_processor.py") -Force -ErrorAction SilentlyContinue
        Write-Host "  ✓ Copied to legacy location" -ForegroundColor Green
    }
} else {
    Write-Host "  ⚠️  Source directory not found: $SourceDir" -ForegroundColor Yellow
}

# Update service configuration
Write-Host "`nUpdating service configuration..." -ForegroundColor Cyan
$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

# Check if service exists
$serviceStatus = nssm status $ServiceName 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠️  Service $ServiceName not found" -ForegroundColor Yellow
    Write-Host "  Run install_service.ps1 to install the service" -ForegroundColor Yellow
    exit 1
}

# Update service to use new path
Write-Host "  Updating service to use: $TargetDir" -ForegroundColor Yellow
& $nssmPath set $ServiceName Application "C:\Tools\python\python.exe"
& $nssmPath set $ServiceName AppParameters (Join-Path $TargetDir "vofc_processor.py")
& $nssmPath set $ServiceName AppDirectory $TargetDir

# Restart service
Write-Host "`nRestarting service..." -ForegroundColor Cyan
& $nssmPath restart $ServiceName

Start-Sleep -Seconds 3

# Verify service is running
$status = nssm status $ServiceName
if ($status -eq "SERVICE_RUNNING") {
    Write-Host "`n✅ Service updated and running successfully!" -ForegroundColor Green
    Write-Host "  Service: $ServiceName" -ForegroundColor Gray
    Write-Host "  Path: $TargetDir" -ForegroundColor Gray
    Write-Host "  Status: Running" -ForegroundColor Gray
} else {
    Write-Host "`n⚠️  Service status: $status" -ForegroundColor Yellow
    Write-Host "  Check logs: C:\Tools\Ollama\Data\logs\vofc_processor_*.log" -ForegroundColor Yellow
}

Write-Host "`nDone!" -ForegroundColor Green

