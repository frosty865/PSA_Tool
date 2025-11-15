# Sync Processor code from project to C:\Tools\VOFC-Processor
# Run this script as Administrator

Write-Host "Syncing Processor code to service directory..." -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$ProjectRoot = "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool"
$ProcessorSource = Join-Path $ProjectRoot "tools\vofc_processor"
$ProcessorTarget = "C:\Tools\VOFC-Processor"
$LegacyPath = "C:\Tools\vofc_processor"

# Also sync to legacy path for compatibility
$LegacyTarget = $LegacyPath

if (-not (Test-Path $ProjectRoot)) {
    Write-Host "ERROR: Project root not found: $ProjectRoot" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ProcessorSource)) {
    Write-Host "ERROR: Processor source not found: $ProcessorSource" -ForegroundColor Red
    exit 1
}

# Ensure target directory exists
if (-not (Test-Path $ProcessorTarget)) {
    Write-Host "Creating target directory: $ProcessorTarget" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $ProcessorTarget -Force | Out-Null
}

Write-Host "Source: $ProcessorSource" -ForegroundColor Gray
Write-Host "Target: $ProcessorTarget" -ForegroundColor Gray
Write-Host ""

$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

# Stop Processor service first
Write-Host "Stopping Processor service..." -ForegroundColor Yellow
& $nssmPath stop VOFC-Processor 2>&1 | Out-Null
Start-Sleep -Seconds 2

# Files and directories to sync
$itemsToSync = @(
    "vofc_processor.py",
    "extract",
    "model",
    "normalize",
    "storage",
    "services"
)

# Sync files
Write-Host "Syncing files..." -ForegroundColor Yellow
foreach ($item in $itemsToSync) {
    $sourcePath = Join-Path $ProcessorSource $item
    $targetPath = Join-Path $ProcessorTarget $item
    
    if (Test-Path $sourcePath) {
        if ((Get-Item $sourcePath).PSIsContainer) {
            # Directory - use robocopy for better sync
            Write-Host "  Syncing directory: $item" -ForegroundColor Gray
            robocopy $sourcePath $targetPath /MIR /NFL /NDL /NJH /NJS /R:3 /W:1 /XD "__pycache__" "*.pyc" | Out-Null
        } else {
            # File - copy
            Write-Host "  Copying file: $item" -ForegroundColor Gray
            Copy-Item $sourcePath $targetPath -Force
        }
        Write-Host "    [OK] $item" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Source not found: $item" -ForegroundColor Yellow
    }
}

# Also copy config directory (needed for Config import) to both locations
$configSource = Join-Path $ProjectRoot "config"
$configTarget = Join-Path $ProcessorTarget "config"
$configLegacyTarget = Join-Path $LegacyTarget "config"
if (Test-Path $configSource) {
    Write-Host "  Syncing config directory..." -ForegroundColor Gray
    # Sync to new location
    robocopy $configSource $configTarget /MIR /NFL /NDL /NJH /NJS /R:3 /W:1 /XD "__pycache__" "*.pyc" | Out-Null
    Write-Host "    [OK] config (new location)" -ForegroundColor Green
    # Also sync to legacy location for compatibility
    if (Test-Path $LegacyTarget) {
        robocopy $configSource $configLegacyTarget /MIR /NFL /NDL /NJH /NJS /R:3 /W:1 /XD "__pycache__" "*.pyc" | Out-Null
        Write-Host "    [OK] config (legacy location)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Code sync complete!" -ForegroundColor Green
Write-Host ""

# Update NSSM service configuration to point to correct path
Write-Host "Updating service configuration..." -ForegroundColor Yellow
$correctScriptPath = Join-Path $ProcessorTarget "vofc_processor.py"
& $nssmPath set VOFC-Processor AppParameters $correctScriptPath
& $nssmPath set VOFC-Processor AppDirectory $ProcessorTarget

Write-Host "  [OK] Service configured to use: $correctScriptPath" -ForegroundColor Green
Write-Host ""

# Restart Processor service
Write-Host "Restarting Processor service..." -ForegroundColor Yellow
& $nssmPath start VOFC-Processor
Start-Sleep -Seconds 3

# Check status
$status = & $nssmPath status VOFC-Processor
if ($status -match "SERVICE_RUNNING") {
    Write-Host "  [OK] Service is running" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Service status: $status" -ForegroundColor Yellow
    Write-Host "  Check logs: C:\Tools\Ollama\Data\logs\vofc_processor_err.log" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Processor service updated and restarted!" -ForegroundColor Green
Write-Host ""
Write-Host "Log file location: C:\Tools\Ollama\Data\logs\vofc_processor.log" -ForegroundColor Cyan

