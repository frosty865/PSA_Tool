# Sync Flask code from project to C:\Tools\VOFC-Flask
# Run this script as Administrator

Write-Host "Syncing Flask code to service directory..." -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$ProjectRoot = "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool"
$FlaskTarget = "C:\Tools\VOFC-Flask"

if (-not (Test-Path $ProjectRoot)) {
    Write-Host "ERROR: Project root not found: $ProjectRoot" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $FlaskTarget)) {
    Write-Host "ERROR: Flask target directory not found: $FlaskTarget" -ForegroundColor Red
    exit 1
}

Write-Host "Source: $ProjectRoot" -ForegroundColor Gray
Write-Host "Target: $FlaskTarget" -ForegroundColor Gray
Write-Host ""

# Files and directories to sync
$itemsToSync = @(
    "routes",
    "services",
    "config",
    "server.py",
    "app.py",
    "requirements.txt"
)

$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

# Stop Flask service first
Write-Host "Stopping Flask service..." -ForegroundColor Yellow
& $nssmPath stop VOFC-Tunnel 2>&1 | Out-Null
Start-Sleep -Seconds 2
& $nssmPath stop vofc-flask 2>&1 | Out-Null
Start-Sleep -Seconds 2

# Sync files
Write-Host "Syncing files..." -ForegroundColor Yellow
foreach ($item in $itemsToSync) {
    $sourcePath = Join-Path $ProjectRoot $item
    $targetPath = Join-Path $FlaskTarget $item
    
    if (Test-Path $sourcePath) {
        if (Test-Path $targetPath) {
            if ((Get-Item $sourcePath).PSIsContainer) {
                # Directory - use robocopy for better sync
                Write-Host "  Syncing directory: $item" -ForegroundColor Gray
                robocopy $sourcePath $targetPath /MIR /NFL /NDL /NJH /NJS /R:3 /W:1 | Out-Null
            } else {
                # File - copy
                Write-Host "  Copying file: $item" -ForegroundColor Gray
                Copy-Item $sourcePath $targetPath -Force
            }
            Write-Host "    ✓ $item" -ForegroundColor Green
        } else {
            Write-Host "  Creating: $item" -ForegroundColor Gray
            if ((Get-Item $sourcePath).PSIsContainer) {
                Copy-Item $sourcePath $targetPath -Recurse -Force
            } else {
                Copy-Item $sourcePath $targetPath -Force
            }
            Write-Host "    ✓ $item" -ForegroundColor Green
        }
    } else {
        Write-Host "  ⚠ Source not found: $item" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "✅ Code sync complete!" -ForegroundColor Green
Write-Host ""

# Restart Flask service
Write-Host "Restarting Flask service..." -ForegroundColor Yellow
& $nssmPath start vofc-flask
Start-Sleep -Seconds 3
& $nssmPath start VOFC-Tunnel
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "✅ Flask service restarted with new code!" -ForegroundColor Green
Write-Host ""
Write-Host "Test with: curl http://localhost:8080/api/system/health" -ForegroundColor Cyan

