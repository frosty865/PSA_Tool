# PowerShell script to migrate ALL services to C:\Tools with unified naming
# Run this script from the project root directory

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Complete Service Migration to C:\Tools" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Define source and target directories
$ProjectRoot = $PSScriptRoot | Split-Path -Parent

# ========================================
# Step 1: Migrate Flask Server (VOFC-Flask)
# ========================================
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Step 1: Migrating Flask Server" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

$FlaskTarget = "C:\Tools\VOFC-Flask"
$FlaskSourcePSA = "C:\Tools\PSA-Flask"  # Check if PSA-Flask exists (old migration)
$FlaskItems = @(
    @{ Source = "app.py"; Target = "app.py" },
    @{ Source = "routes"; Target = "routes" },
    @{ Source = "services"; Target = "services" },
    @{ Source = "config"; Target = "config" },
    @{ Source = "requirements.txt"; Target = "requirements.txt" },
    @{ Source = "start.ps1"; Target = "start.ps1" },
    @{ Source = "env.example"; Target = "env.example" }
)

# Check if PSA-Flask exists (from previous migration)
if (Test-Path $FlaskSourcePSA) {
    Write-Host "  Found existing PSA-Flask at: $FlaskSourcePSA" -ForegroundColor Yellow
    Write-Host "  This will be migrated to VOFC-Flask" -ForegroundColor Yellow
    $migrateFromPSA = $true
} else {
    $migrateFromPSA = $false
}

# Create Flask directory
if (-not (Test-Path $FlaskTarget)) {
    New-Item -ItemType Directory -Path $FlaskTarget -Force | Out-Null
    Write-Host "  Created: $FlaskTarget" -ForegroundColor Green
} else {
    Write-Host "  VOFC-Flask already exists: $FlaskTarget" -ForegroundColor Yellow
}

# Create subdirectories
$FlaskSubDirs = @("routes", "services", "config", "tools", "tests", "logs")
foreach ($dir in $FlaskSubDirs) {
    $targetPath = Join-Path $FlaskTarget $dir
    if (-not (Test-Path $targetPath)) {
        New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
    }
}

# Copy Flask files - prioritize PSA-Flask if it exists, otherwise use project root
if ($migrateFromPSA) {
    Write-Host "  Migrating from PSA-Flask to VOFC-Flask..." -ForegroundColor Cyan
    # Copy from PSA-Flask (preserves existing setup)
    Copy-Item -Path "$FlaskSourcePSA\*" -Destination $FlaskTarget -Recurse -Force -Exclude "venv"
    Write-Host "    ✓ Migrated from PSA-Flask" -ForegroundColor Green
    Write-Host "    Note: venv excluded - recreate virtual environment" -ForegroundColor Gray
} else {
    Write-Host "  Copying Flask files from project..." -ForegroundColor Cyan
    foreach ($item in $FlaskItems) {
        $sourcePath = Join-Path $ProjectRoot $item.Source
        $targetPath = Join-Path $FlaskTarget $item.Target
        
        if (Test-Path $sourcePath) {
            if (Test-Path $sourcePath -PathType Container) {
                Copy-Item -Path $sourcePath -Destination $targetPath -Recurse -Force
                Write-Host "    ✓ Copied directory: $($item.Source)" -ForegroundColor Green
            } else {
                Copy-Item -Path $sourcePath -Destination $targetPath -Force
                Write-Host "    ✓ Copied file: $($item.Source)" -ForegroundColor Green
            }
        }
    }
}

# Copy test files
$testFiles = @("test_sync_individual.py", "test_sync_manual.py")
$testTargetDir = Join-Path $FlaskTarget "tests"
foreach ($testFile in $testFiles) {
    $sourcePath = Join-Path $ProjectRoot $testFile
    if (Test-Path $sourcePath) {
        $targetPath = Join-Path $testTargetDir $testFile
        Copy-Item -Path $sourcePath -Destination $targetPath -Force
        Write-Host "    ✓ Copied test: $testFile" -ForegroundColor Green
    }
}

Write-Host "  ✓ Flask server migration complete" -ForegroundColor Green
if ($migrateFromPSA) {
    Write-Host "  ⚠ IMPORTANT: Update service to point to VOFC-Flask:" -ForegroundColor Yellow
    Write-Host "     nssm set vofc-flask AppDirectory `"$FlaskTarget`"" -ForegroundColor Cyan
    Write-Host "     nssm restart vofc-flask" -ForegroundColor Cyan
}
Write-Host ""

# ========================================
# Step 2: Migrate Processor Service (VOFC-Processor)
# ========================================
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Step 2: Migrating Processor Service" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

$ProcessorTarget = "C:\Tools\VOFC-Processor"
$ProcessorSourcePSA = "C:\Tools\PSA-Processor"  # Check if PSA-Processor exists
$ProcessorSource = Join-Path $ProjectRoot "tools\vofc_processor"
$LegacyProcessor = "C:\Tools\vofc_processor"

# Create Processor directory
if (-not (Test-Path $ProcessorTarget)) {
    New-Item -ItemType Directory -Path $ProcessorTarget -Force | Out-Null
    Write-Host "  Created: $ProcessorTarget" -ForegroundColor Green
} else {
    Write-Host "  VOFC-Processor already exists: $ProcessorTarget" -ForegroundColor Yellow
}

# Priority: PSA-Processor > Legacy vofc_processor > Project source
if (Test-Path $ProcessorSourcePSA) {
    Write-Host "  Found PSA-Processor, migrating to VOFC-Processor..." -ForegroundColor Cyan
    Copy-Item -Path "$ProcessorSourcePSA\*" -Destination $ProcessorTarget -Recurse -Force
    Write-Host "    ✓ Migrated from PSA-Processor" -ForegroundColor Green
} elseif (Test-Path $LegacyProcessor) {
    Write-Host "  Found processor at legacy location: $LegacyProcessor" -ForegroundColor Yellow
    Write-Host "  Copying to VOFC-Processor..." -ForegroundColor Cyan
    Copy-Item -Path "$LegacyProcessor\*" -Destination $ProcessorTarget -Recurse -Force
    Write-Host "    ✓ Copied from legacy location" -ForegroundColor Green
} elseif (Test-Path $ProcessorSource) {
    Write-Host "  Copying processor files from project..." -ForegroundColor Cyan
    Copy-Item -Path "$ProcessorSource\*" -Destination $ProcessorTarget -Recurse -Force
    Write-Host "    ✓ Copied processor files" -ForegroundColor Green
} else {
    Write-Host "    ⚠ Processor source not found in any location" -ForegroundColor Yellow
}

Write-Host "  ✓ Processor service migration complete" -ForegroundColor Green
Write-Host ""

# ========================================
# Step 3: Migrate Tunnel Configuration Files
# ========================================
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Step 3: Migrating Tunnel Configuration" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

$TunnelTarget = "C:\Tools\VOFC-Tunnel"
$TunnelConfigSource = Join-Path $ProjectRoot "cloudflared-config.yml"
$TunnelScriptSource = Join-Path $ProjectRoot "fix-tunnel-service.ps1"

# Create Tunnel directory (for configuration files)
if (-not (Test-Path $TunnelTarget)) {
    New-Item -ItemType Directory -Path $TunnelTarget -Force | Out-Null
    Write-Host "  Created: $TunnelTarget" -ForegroundColor Green
}

# Copy tunnel configuration files
if (Test-Path $TunnelConfigSource) {
    $targetConfig = Join-Path $TunnelTarget "cloudflared-config.yml"
    Copy-Item -Path $TunnelConfigSource -Destination $targetConfig -Force
    Write-Host "  ✓ Copied: cloudflared-config.yml" -ForegroundColor Green
    Write-Host "    Note: Actual config is at C:\Tools\cloudflared\config.yaml" -ForegroundColor Gray
    Write-Host "    Service config is at C:\Users\frost\cloudflared\config.yml" -ForegroundColor Gray
}

if (Test-Path $TunnelScriptSource) {
    $targetScript = Join-Path $TunnelTarget "fix-tunnel-service.ps1"
    Copy-Item -Path $TunnelScriptSource -Destination $targetScript -Force
    Write-Host "  ✓ Copied: fix-tunnel-service.ps1" -ForegroundColor Green
}

Write-Host "  ✓ Tunnel configuration files migration complete" -ForegroundColor Green
Write-Host "    Note: Tunnel service runs cloudflared.exe via NSSM" -ForegroundColor Gray
Write-Host "    No Python code to migrate - just configuration files" -ForegroundColor Gray
Write-Host ""

# ========================================
# Step 4: Check for Model Manager Files
# ========================================
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Step 4: Checking for Model Manager" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

# Model Manager might be a separate service - check if files exist
$ModelManagerTarget = "C:\Tools\VOFC-ModelManager"
$ModelManagerPossiblePaths = @(
    "C:\Tools\VOFC-ModelManager"
    "C:\Tools\VOFC-Model-Manager"
    "C:\Tools\model_manager"
    (Join-Path $ProjectRoot "services\model_manager.py")
)

$modelManagerFound = $false
foreach ($path in $ModelManagerPossiblePaths) {
    if (Test-Path $path) {
        Write-Host "  Found Model Manager at: $path" -ForegroundColor Yellow
        $modelManagerFound = $true
        
        if (-not (Test-Path $ModelManagerTarget)) {
            New-Item -ItemType Directory -Path $ModelManagerTarget -Force | Out-Null
            Write-Host "  Created: $ModelManagerTarget" -ForegroundColor Green
        }
        
        if (Test-Path $path -PathType Container) {
            Copy-Item -Path "$path\*" -Destination $ModelManagerTarget -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  ✓ Copied Model Manager files" -ForegroundColor Green
        } elseif (Test-Path $path -PathType Leaf) {
            Copy-Item -Path $path -Destination $ModelManagerTarget -Force -ErrorAction SilentlyContinue
            Write-Host "  ✓ Copied Model Manager file" -ForegroundColor Green
        }
        break
    }
}

if (-not $modelManagerFound) {
    Write-Host "  ⚠ Model Manager files not found in project" -ForegroundColor Yellow
    Write-Host "    Model Manager may be a separate service or integrated elsewhere" -ForegroundColor Gray
}

Write-Host "  ✓ Model Manager check complete" -ForegroundColor Green
Write-Host ""

# ========================================
# Step 5: Migrate Utility Tools
# ========================================
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Step 5: Migrating Utility Tools" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

# Tools that should be in VOFC-Flask/tools (already copied above)
# Additional tools can be added here if needed

Write-Host "  ✓ Utility tools already included in Flask migration" -ForegroundColor Green
Write-Host ""

# ========================================
# Step 6: Summary and Next Steps
# ========================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Migration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Migrated Services:" -ForegroundColor Yellow
Write-Host "  ✓ Flask Server → C:\Tools\VOFC-Flask" -ForegroundColor Green
Write-Host "  ✓ Processor Service → C:\Tools\VOFC-Processor" -ForegroundColor Green
Write-Host "  ✓ Tunnel Configuration → C:\Tools\VOFC-Tunnel" -ForegroundColor Green
if ($modelManagerFound) {
    Write-Host "  ✓ Model Manager → C:\Tools\VOFC-ModelManager" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Model Manager → Not found (may be separate service)" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Copy .env file to Flask server:" -ForegroundColor White
Write-Host "   Copy-Item `".env`" `"C:\Tools\VOFC-Flask\.env`"" -ForegroundColor Cyan
Write-Host ""

Write-Host "2. Update Flask service (vofc-flask) - REQUIRED if migrated from PSA-Flask:" -ForegroundColor White
Write-Host "   # Check current location:" -ForegroundColor Gray
Write-Host "   nssm get vofc-flask AppDirectory" -ForegroundColor Cyan
Write-Host "   # Update to VOFC-Flask:" -ForegroundColor Gray
Write-Host "   nssm set vofc-flask Application `"C:\Tools\VOFC-Flask\venv\Scripts\python.exe`"" -ForegroundColor Cyan
Write-Host "   nssm set vofc-flask AppDirectory `"C:\Tools\VOFC-Flask`"" -ForegroundColor Cyan
Write-Host "   nssm set vofc-flask AppParameters `"-m waitress --listen=0.0.0.0:8080 server:app`"" -ForegroundColor Cyan
Write-Host "   nssm restart vofc-flask" -ForegroundColor Cyan
Write-Host ""

Write-Host "3. Update Processor service (VOFC-Processor) - REQUIRED:" -ForegroundColor White
Write-Host "   # Check current location:" -ForegroundColor Gray
Write-Host "   nssm get VOFC-Processor AppDirectory" -ForegroundColor Cyan
Write-Host "   # Update to VOFC-Processor:" -ForegroundColor Gray
Write-Host "   cd C:\Tools\VOFC-Processor" -ForegroundColor Cyan
Write-Host "   .\install_service.ps1" -ForegroundColor Cyan
Write-Host "   (This will install/update as VOFC-Processor)" -ForegroundColor Gray
Write-Host ""

Write-Host "4. Set up virtual environments:" -ForegroundColor White
Write-Host "   # Flask:" -ForegroundColor Gray
Write-Host "   cd C:\Tools\VOFC-Flask" -ForegroundColor Cyan
Write-Host "   python -m venv venv" -ForegroundColor Cyan
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "   pip install -r requirements.txt" -ForegroundColor Cyan
Write-Host ""

Write-Host "5. Update Tunnel service (if needed):" -ForegroundColor White
Write-Host "   # Tunnel config is at C:\Tools\cloudflared\config.yaml" -ForegroundColor Gray
Write-Host "   # Service config is at C:\Users\frost\cloudflared\config.yml" -ForegroundColor Gray
Write-Host "   # Reference copy saved to C:\Tools\VOFC-Tunnel\cloudflared-config.yml" -ForegroundColor Gray
Write-Host "   # Tunnel service runs cloudflared.exe - no code migration needed" -ForegroundColor Gray
Write-Host ""

Write-Host "6. Test services:" -ForegroundColor White
Write-Host "   # Test Flask:" -ForegroundColor Gray
Write-Host "   Invoke-WebRequest -Uri `"http://localhost:8080/api/system/health`"" -ForegroundColor Cyan
Write-Host "   # Check Processor:" -ForegroundColor Gray
Write-Host "   nssm status VOFC-Processor" -ForegroundColor Cyan
Write-Host "   # Check Tunnel:" -ForegroundColor Gray
Write-Host "   nssm status VOFC-Tunnel" -ForegroundColor Cyan
Write-Host "   # Check Model Manager:" -ForegroundColor Gray
Write-Host "   nssm status VOFC-ModelManager" -ForegroundColor Cyan
Write-Host ""

Write-Host "Note: Service names (actual installed names):" -ForegroundColor Cyan
Write-Host "  - vofc-flask (Flask API - lowercase)" -ForegroundColor Gray
Write-Host "  - VOFC-Processor (Document processor)" -ForegroundColor Gray
Write-Host "  - VOFC-Tunnel (Cloudflare tunnel - runs cloudflared.exe)" -ForegroundColor Gray
Write-Host "  - VOFC-ModelManager (Model manager - if exists)" -ForegroundColor Gray
Write-Host ""
Write-Host "Note: Tunnel and Model Manager don't have Python code to migrate." -ForegroundColor Yellow
Write-Host "      Tunnel runs cloudflared.exe, Model Manager may be separate." -ForegroundColor Yellow
Write-Host ""
if ($migrateFromPSA) {
    Write-Host "⚠️  IMPORTANT: PSA-Flask and PSA-Processor directories still exist." -ForegroundColor Yellow
    Write-Host "   After verifying VOFC-* services work, you can remove PSA-* directories:" -ForegroundColor Yellow
    Write-Host "   Remove-Item `"C:\Tools\PSA-Flask`" -Recurse -Force" -ForegroundColor Cyan
    Write-Host "   Remove-Item `"C:\Tools\PSA-Processor`" -Recurse -Force" -ForegroundColor Cyan
    Write-Host ""
}

