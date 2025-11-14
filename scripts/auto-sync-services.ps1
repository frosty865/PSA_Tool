# Automated Service Code Sync
# Watches project folder for changes and automatically syncs to C:\Tools\*
# Run this script as Administrator and leave it running

param(
    [switch]$WatchOnly = $false,  # Only watch, don't sync on startup
    [switch]$AutoRestart = $false  # Auto-restart services on critical file changes
)

Write-Host "=== Automated Service Code Sync ===" -ForegroundColor Cyan
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
$ProcessorTarget = "C:\Tools\VOFC-Processor"

if (-not (Test-Path $ProjectRoot)) {
    Write-Host "ERROR: Project root not found: $ProjectRoot" -ForegroundColor Red
    exit 1
}

# Files and directories to sync for Flask
$flaskItemsToSync = @(
    "routes",
    "services",
    "config",
    "server.py",
    "app.py",
    "requirements.txt"
)

# Files and directories to sync for Processor
$processorItemsToSync = @(
    "tools\vofc_processor"
)

$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

# Sync function
function Sync-Files {
    param(
        [string]$SourceRoot,
        [string]$TargetRoot,
        [array]$ItemsToSync,
        [string]$ServiceName = $null
    )
    
    $synced = $false
    foreach ($item in $ItemsToSync) {
        $sourcePath = Join-Path $SourceRoot $item
        $targetPath = Join-Path $TargetRoot $item
        
        if (Test-Path $sourcePath) {
            try {
                if ((Get-Item $sourcePath).PSIsContainer) {
                    # Directory - use robocopy for better sync
                    robocopy $sourcePath $targetPath /MIR /NFL /NDL /NJH /NJS /R:1 /W:1 /XD "__pycache__" ".git" "node_modules" | Out-Null
                } else {
                    # File - copy if different
                    $sourceHash = (Get-FileHash $sourcePath -Algorithm MD5).Hash
                    if (Test-Path $targetPath) {
                        $targetHash = (Get-FileHash $targetPath -Algorithm MD5).Hash
                        if ($sourceHash -ne $targetHash) {
                            Copy-Item $sourcePath $targetPath -Force
                            $synced = $true
                            Write-Host "  ✓ Synced: $item" -ForegroundColor Green
                        }
                    } else {
                        Copy-Item $sourcePath $targetPath -Force
                        $synced = $true
                        Write-Host "  ✓ Created: $item" -ForegroundColor Green
                    }
                }
            } catch {
                Write-Host "  ⚠ Error syncing $item : $_" -ForegroundColor Yellow
            }
        }
    }
    
    return $synced
}

# Initial sync (if not watch-only)
if (-not $WatchOnly) {
    Write-Host "Performing initial sync..." -ForegroundColor Yellow
    Write-Host ""
    
    Write-Host "Syncing Flask code..." -ForegroundColor Cyan
    $flaskSynced = Sync-Files -SourceRoot $ProjectRoot -TargetRoot $FlaskTarget -ItemsToSync $flaskItemsToSync -ServiceName "vofc-flask"
    
    Write-Host ""
    Write-Host "Syncing Processor code..." -ForegroundColor Cyan
    # For processor, sync the entire vofc_processor directory structure
    $processorSource = Join-Path $ProjectRoot "tools\vofc_processor"
    if (Test-Path $processorSource) {
        # Copy processor files maintaining structure
        $processorFiles = @(
            "vofc_processor.py",
            "extract",
            "model",
            "normalize",
            "storage"
        )
        foreach ($file in $processorFiles) {
            $src = Join-Path $processorSource $file
            $dst = Join-Path $ProcessorTarget $file
            if (Test-Path $src) {
                if ((Get-Item $src).PSIsContainer) {
                    robocopy $src $dst /MIR /NFL /NDL /NJH /NJS /R:1 /W:1 /XD "__pycache__" | Out-Null
                } else {
                    Copy-Item $src $dst -Force -ErrorAction SilentlyContinue
                }
                Write-Host "  ✓ Synced: $file" -ForegroundColor Green
            }
        }
    }
    
    Write-Host ""
    Write-Host "✅ Initial sync complete!" -ForegroundColor Green
    Write-Host ""
}

# File watcher setup
Write-Host "Setting up file watcher..." -ForegroundColor Yellow
Write-Host "Watching: $ProjectRoot" -ForegroundColor Gray
Write-Host ""

# Critical files that require service restart
$criticalFiles = @(
    "server.py",
    "app.py",
    "requirements.txt"
)

# Create file system watcher
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $ProjectRoot
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true
$watcher.Filter = "*.*"

# Filter out unnecessary files
$excludePatterns = @(
    "\.git",
    "__pycache__",
    "\.pyc$",
    "node_modules",
    "\.next",
    "\.env",
    "app\.",
    "docs\."
)

$action = {
    $path = $Event.SourceEventArgs.FullPath
    $changeType = $Event.SourceEventArgs.ChangeType
    $name = $Event.SourceEventArgs.Name
    
    # Skip excluded patterns
    $shouldSkip = $false
    foreach ($pattern in $excludePatterns) {
        if ($path -match $pattern) {
            $shouldSkip = $true
            break
        }
    }
    
    if ($shouldSkip) {
        return
    }
    
    # Determine which service needs sync
    $needsFlaskSync = $false
    $needsProcessorSync = $false
    $isCritical = $false
    
    # Check if it's a Flask file
    if ($path -match "\\routes\\" -or $path -match "\\services\\" -or $path -match "\\config\\" -or 
        $path -match "\\server\.py$" -or $path -match "\\app\.py$" -or $path -match "\\requirements\.txt$") {
        $needsFlaskSync = $true
        if ($path -match "\\server\.py$" -or $path -match "\\app\.py$" -or $path -match "\\requirements\.txt$") {
            $isCritical = $true
        }
    }
    
    # Check if it's a Processor file
    if ($path -match "\\tools\\vofc_processor\\") {
        $needsProcessorSync = $true
    }
    
    if ($needsFlaskSync -or $needsProcessorSync) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] File changed: $name ($changeType)" -ForegroundColor Cyan
        
        # Small delay to ensure file write is complete
        Start-Sleep -Milliseconds 500
        
        if ($needsFlaskSync) {
            Write-Host "  → Syncing to Flask..." -ForegroundColor Yellow
            $relativePath = $path.Replace($ProjectRoot, "").TrimStart("\")
            $item = $relativePath.Split("\")[0]
            
            if ($item -in $flaskItemsToSync -or $relativePath -match "^(routes|services|config)\\" -or $relativePath -match "^(server|app)\.py$") {
                Sync-Files -SourceRoot $ProjectRoot -TargetRoot $FlaskTarget -ItemsToSync @($item) -ServiceName "vofc-flask" | Out-Null
                
                if ($isCritical -and $AutoRestart) {
                    Write-Host "  → Restarting Flask service..." -ForegroundColor Yellow
                    & $nssmPath restart vofc-flask 2>&1 | Out-Null
                    Write-Host "  ✓ Flask service restarted" -ForegroundColor Green
                }
            }
        }
        
        if ($needsProcessorSync) {
            Write-Host "  → Syncing to Processor..." -ForegroundColor Yellow
            $processorSource = Join-Path $ProjectRoot "tools\vofc_processor"
            $relativePath = $path.Replace($processorSource, "").TrimStart("\")
            $item = $relativePath.Split("\")[0]
            
            $src = Join-Path $processorSource $item
            $dst = Join-Path $ProcessorTarget $item
            if (Test-Path $src) {
                if ((Get-Item $src).PSIsContainer) {
                    robocopy $src $dst /MIR /NFL /NDL /NJH /NJS /R:1 /W:1 /XD "__pycache__" | Out-Null
                } else {
                    Copy-Item $src $dst -Force -ErrorAction SilentlyContinue
                }
                Write-Host "  ✓ Synced: $item" -ForegroundColor Green
                
                if ($AutoRestart -and ($item -eq "vofc_processor.py")) {
                    Write-Host "  → Restarting Processor service..." -ForegroundColor Yellow
                    & $nssmPath restart VOFC-Processor 2>&1 | Out-Null
                    Write-Host "  ✓ Processor service restarted" -ForegroundColor Green
                }
            }
        }
        
        Write-Host ""
    }
}

# Register event handlers
Register-ObjectEvent -InputObject $watcher -EventName "Changed" -Action $action | Out-Null
Register-ObjectEvent -InputObject $watcher -EventName "Created" -Action $action | Out-Null
Register-ObjectEvent -InputObject $watcher -EventName "Deleted" -Action $action | Out-Null

Write-Host "✅ File watcher active!" -ForegroundColor Green
Write-Host ""
Write-Host "Watching for changes in:" -ForegroundColor Cyan
Write-Host "  - Flask: routes/, services/, config/, server.py, app.py" -ForegroundColor Gray
Write-Host "  - Processor: tools/vofc_processor/" -ForegroundColor Gray
Write-Host ""
if ($AutoRestart) {
    Write-Host "Auto-restart: ENABLED (services will restart on critical file changes)" -ForegroundColor Yellow
} else {
    Write-Host "Auto-restart: DISABLED (use -AutoRestart to enable)" -ForegroundColor Gray
}
Write-Host ""
Write-Host "Press Ctrl+C to stop watching..." -ForegroundColor Cyan
Write-Host ""

# Keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    $watcher.EnableRaisingEvents = $false
    $watcher.Dispose()
    Write-Host ""
    Write-Host "File watcher stopped." -ForegroundColor Yellow
}

