# PowerShell script to migrate Python server-side code to C:\Tools\VOFC-Flask
# NOTE: For complete migration of ALL services, use: .\scripts\migrate-all-services.ps1
# This script only migrates the Flask server
# Run this script from the project root directory

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Flask Server Migration to C:\Tools\VOFC-Flask" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NOTE: This script only migrates the Flask server." -ForegroundColor Yellow
Write-Host "      For complete migration (Flask + Processor), use:" -ForegroundColor Yellow
Write-Host "      .\scripts\migrate-all-services.ps1" -ForegroundColor Cyan
Write-Host ""

# Define source and target directories
$ProjectRoot = $PSScriptRoot | Split-Path -Parent
$TargetRoot = "C:\Tools\VOFC-Flask"

# Directories and files to migrate
$ItemsToMigrate = @(
    @{ Source = "app.py"; Target = "app.py" },
    @{ Source = "routes"; Target = "routes" },
    @{ Source = "services"; Target = "services" },
    @{ Source = "config"; Target = "config" },
    @{ Source = "tools"; Target = "tools" },
    @{ Source = "requirements.txt"; Target = "requirements.txt" },
    @{ Source = "start.ps1"; Target = "start.ps1" },
    @{ Source = "env.example"; Target = "env.example" }
)

# Test files (optional)
$TestFiles = @(
    "test_sync_individual.py",
    "test_sync_manual.py"
)

Write-Host "Step 1: Creating target directory structure..." -ForegroundColor Yellow
if (-not (Test-Path $TargetRoot)) {
    New-Item -ItemType Directory -Path $TargetRoot -Force | Out-Null
    Write-Host "  Created: $TargetRoot" -ForegroundColor Green
} else {
    Write-Host "  Directory exists: $TargetRoot" -ForegroundColor Yellow
    $response = Read-Host "  Directory already exists. Continue? (y/n)"
    if ($response -ne "y") {
        Write-Host "Migration cancelled." -ForegroundColor Red
        exit 1
    }
}

# Create subdirectories
$SubDirs = @("routes", "services", "config", "tools", "tests", "logs")
foreach ($dir in $SubDirs) {
    $targetPath = Join-Path $TargetRoot $dir
    if (-not (Test-Path $targetPath)) {
        New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
        Write-Host "  Created: $targetPath" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Step 2: Copying files and directories..." -ForegroundColor Yellow

foreach ($item in $ItemsToMigrate) {
    $sourcePath = Join-Path $ProjectRoot $item.Source
    $targetPath = Join-Path $TargetRoot $item.Target
    
    if (Test-Path $sourcePath) {
        if (Test-Path $sourcePath -PathType Container) {
            # Copy directory
            Write-Host "  Copying directory: $($item.Source) -> $($item.Target)" -ForegroundColor Cyan
            Copy-Item -Path $sourcePath -Destination $targetPath -Recurse -Force
        } else {
            # Copy file
            Write-Host "  Copying file: $($item.Source) -> $($item.Target)" -ForegroundColor Cyan
            Copy-Item -Path $sourcePath -Destination $targetPath -Force
        }
        Write-Host "    ✓ Copied successfully" -ForegroundColor Green
    } else {
        Write-Host "    ⚠ Not found: $sourcePath" -ForegroundColor Yellow
    }
}

# Copy test files if they exist
Write-Host ""
Write-Host "Step 3: Copying test files (if any)..." -ForegroundColor Yellow
$testTargetDir = Join-Path $TargetRoot "tests"
foreach ($testFile in $TestFiles) {
    $sourcePath = Join-Path $ProjectRoot $testFile
    if (Test-Path $sourcePath) {
        $targetPath = Join-Path $testTargetDir $testFile
        Copy-Item -Path $sourcePath -Destination $targetPath -Force
        Write-Host "  ✓ Copied: $testFile" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Step 4: Creating .gitkeep files for empty directories..." -ForegroundColor Yellow
$EmptyDirs = @("logs")
foreach ($dir in $EmptyDirs) {
    $dirPath = Join-Path $TargetRoot $dir
    $gitkeep = Join-Path $dirPath ".gitkeep"
    if (-not (Test-Path $gitkeep)) {
        New-Item -ItemType File -Path $gitkeep -Force | Out-Null
    }
}

Write-Host ""
Write-Host "Step 5: Path references already updated!" -ForegroundColor Green
Write-Host "  The following files have been pre-updated to support C:\Tools\VOFC-Flask:" -ForegroundColor Yellow
Write-Host "    ✓ tools/vofc_processor/vofc_processor.py (.env paths)" -ForegroundColor Green
Write-Host "    ✓ tools/cleanup_orphaned_files.py (project dir exclusions)" -ForegroundColor Green
Write-Host "    ✓ tools/reset_data_folders.py (training data paths)" -ForegroundColor Green
Write-Host "    ✓ tools/seed_retrain.py (training data paths)" -ForegroundColor Green
Write-Host "    ✓ tools/seed_extractor.py (training data paths)" -ForegroundColor Green
Write-Host "    ✓ sync-env.ps1 (Flask path)" -ForegroundColor Green
Write-Host ""
Write-Host "  Note: All files check new location first, then fall back to legacy paths" -ForegroundColor Cyan
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Migration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Copy .env file to C:\Tools\VOFC-Flask\.env" -ForegroundColor White
Write-Host "2. Update Windows service to use new location:" -ForegroundColor White
Write-Host "   nssm set vofc-flask Application `"C:\Tools\VOFC-Flask\venv\Scripts\python.exe`"" -ForegroundColor Cyan
Write-Host "   nssm set vofc-flask AppDirectory `"C:\Tools\VOFC-Flask`"" -ForegroundColor Cyan
Write-Host "   nssm set vofc-flask AppParameters `"-m waitress --listen=0.0.0.0:8080 server:app`"" -ForegroundColor Cyan
Write-Host "   nssm restart vofc-flask" -ForegroundColor Cyan
Write-Host "   (Note: Service name is 'vofc-flask' - lowercase)" -ForegroundColor Gray
Write-Host "3. Test Flask server: cd C:\Tools\VOFC-Flask && .\start.ps1" -ForegroundColor White
Write-Host "4. See docs/COMPLETE-MIGRATION-GUIDE.md for complete migration (all services)" -ForegroundColor White
Write-Host ""
Write-Host "Note: Actual service names (check with 'nssm status'):" -ForegroundColor Cyan
Write-Host "  - vofc-flask (actual service name - lowercase)" -ForegroundColor Gray
Write-Host "  - VOFC-Processor (actual service name)" -ForegroundColor Gray
Write-Host "  - VOFC-Tunnel (actual service name)" -ForegroundColor Gray
Write-Host "  - VOFC-ModelManager (actual service name)" -ForegroundColor Gray
Write-Host "  (Future migration target: PSA-* naming)" -ForegroundColor Yellow
Write-Host ""

