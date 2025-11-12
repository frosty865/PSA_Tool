# migrate-all-services-to-tools.ps1
# Migrates all VOFC services to C:\Tools\python and C:\Tools\py_scripts
# For server deployment - all services run from C:\Tools

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Migrate All VOFC Services to C:\Tools" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Configuration
$PythonPath = "C:\Tools\python\python.exe"
$ToolsScriptsDir = "C:\Tools\py_scripts"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# Verify Python
if (-not (Test-Path $PythonPath)) {
    $PythonPath = "C:\Tools\python.exe"
    if (-not (Test-Path $PythonPath)) {
        Write-Host "ERROR: Python not found at C:\Tools\python\" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✓ Python: $PythonPath" -ForegroundColor Green

# Ensure C:\Tools\py_scripts exists
if (-not (Test-Path $ToolsScriptsDir)) {
    New-Item -ItemType Directory -Path $ToolsScriptsDir -Force | Out-Null
    Write-Host "✓ Created: $ToolsScriptsDir" -ForegroundColor Green
}

# Define services to migrate
$services = @(
    @{
        Name = "VOFC-Processor"
        Script = "vofc_processor.py"
        SourceDir = Join-Path $ProjectRoot "tools\vofc_processor"
        TargetDir = Join-Path $ToolsScriptsDir "vofc_processor"
        WorkingDir = Join-Path $ToolsScriptsDir "vofc_processor"
    },
    @{
        Name = "VOFC-ModelManager"
        Script = "model_manager.py"
        SourceDir = Join-Path $ProjectRoot "services"
        TargetDir = Join-Path $ToolsScriptsDir "model_manager"
        WorkingDir = Join-Path $ToolsScriptsDir "model_manager"
    },
    @{
        Name = "VOFC-AutoRetrain"
        Script = "auto_retrain_job.py"
        SourceDir = "C:\Tools"  # May already be there
        TargetDir = Join-Path $ToolsScriptsDir "auto_retrain"
        WorkingDir = Join-Path $ToolsScriptsDir "auto_retrain"
        Optional = $true
    }
)

Write-Host ""
Write-Host "Step 1: Copying service scripts to C:\Tools\py_scripts..." -ForegroundColor Yellow
Write-Host ""

foreach ($service in $services) {
    $sourceFile = Join-Path $service.SourceDir $service.Script
    $targetFile = Join-Path $service.TargetDir $service.Script
    
    Write-Host "  [$($service.Name)]" -ForegroundColor Cyan
    
    # Check if source exists
    if (-not (Test-Path $sourceFile)) {
        if ($service.Optional) {
            Write-Host "    ⚠️  Source not found (optional): $sourceFile" -ForegroundColor Yellow
            Write-Host "    Skipping..." -ForegroundColor Gray
            continue
        } else {
            Write-Host "    ✗ Source not found: $sourceFile" -ForegroundColor Red
            Write-Host "    Please ensure the file exists" -ForegroundColor Yellow
            continue
        }
    }
    
    # Create target directory
    if (-not (Test-Path $service.TargetDir)) {
        New-Item -ItemType Directory -Path $service.TargetDir -Force | Out-Null
    }
    
    # Copy script
    Copy-Item $sourceFile $targetFile -Force
    Write-Host "    ✓ Copied: $($service.Script)" -ForegroundColor Green
    
    # Copy related files if they exist
    $relatedFiles = @("requirements.txt", "__init__.py", "*.yaml", "*.yml", "*.json")
    foreach ($pattern in $relatedFiles) {
        $sourcePattern = Join-Path $service.SourceDir $pattern
        $files = Get-ChildItem -Path $sourcePattern -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            Copy-Item $file.FullName $service.TargetDir -Force -ErrorAction SilentlyContinue
            Write-Host "    ✓ Copied: $($file.Name)" -ForegroundColor Gray
        }
    }
}

Write-Host ""
Write-Host "Step 2: Updating service configurations..." -ForegroundColor Yellow
Write-Host ""

foreach ($service in $services) {
    $targetFile = Join-Path $service.TargetDir $service.Script
    
    # Skip if file doesn't exist
    if (-not (Test-Path $targetFile)) {
        continue
    }
    
    Write-Host "  [$($service.Name)]" -ForegroundColor Cyan
    
    # Check if service exists
    $status = nssm status $service.Name 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    ⚠️  Service not installed, skipping update" -ForegroundColor Yellow
        Write-Host "    Install with: .\scripts\install-$($service.Name.ToLower().Replace('vofc-', 'vofc-')).ps1" -ForegroundColor Gray
        continue
    }
    
    Write-Host "    Current status: $status" -ForegroundColor Gray
    
    # Stop service if running
    if ($status -eq "SERVICE_RUNNING" -or $status -eq "SERVICE_PAUSED") {
        Write-Host "    Stopping service..." -ForegroundColor Gray
        nssm stop $service.Name 2>&1 | Out-Null
        Start-Sleep -Seconds 2
    }
    
    # Update service configuration
    Write-Host "    Updating paths..." -ForegroundColor Gray
    nssm set $service.Name Application $PythonPath 2>&1 | Out-Null
    nssm set $service.Name AppParameters $targetFile 2>&1 | Out-Null
    nssm set $service.Name AppDirectory $service.WorkingDir 2>&1 | Out-Null
    
    # Verify
    $verifyApp = nssm get $service.Name Application 2>&1
    $verifyParams = nssm get $service.Name AppParameters 2>&1
    $verifyDir = nssm get $service.Name AppDirectory 2>&1
    
    if ($verifyApp -eq $PythonPath -and $verifyParams -eq $targetFile) {
        Write-Host "    ✓ Service updated successfully" -ForegroundColor Green
    } else {
        Write-Host "    ⚠️  Verification mismatch" -ForegroundColor Yellow
        Write-Host "      App: $verifyApp" -ForegroundColor Gray
        Write-Host "      Params: $verifyParams" -ForegroundColor Gray
        Write-Host "      Dir: $verifyDir" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Step 3: Installing Python dependencies..." -ForegroundColor Yellow
Write-Host ""

# Collect all requirements.txt files
$requirementsFiles = @()
foreach ($service in $services) {
    $reqFile = Join-Path $service.TargetDir "requirements.txt"
    if (Test-Path $reqFile) {
        $requirementsFiles += $reqFile
    }
}

if ($requirementsFiles.Count -gt 0) {
    Write-Host "  Found $($requirementsFiles.Count) requirements.txt file(s)" -ForegroundColor Gray
    
    # Install from each requirements file
    foreach ($reqFile in $requirementsFiles) {
        Write-Host "  Installing from: $reqFile" -ForegroundColor Gray
        & $PythonPath -m pip install -r $reqFile 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✓ Dependencies installed" -ForegroundColor Green
        } else {
            Write-Host "    ⚠️  Some dependencies may have failed" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  ⚠️  No requirements.txt files found" -ForegroundColor Yellow
    Write-Host "  Installing common dependencies..." -ForegroundColor Gray
    & $PythonPath -m pip install pandas PyMuPDF requests supabase 2>&1 | Out-Null
}

Write-Host ""
Write-Host "Step 4: Configuring service dependencies..." -ForegroundColor Yellow
Write-Host ""

# Run dependency configuration script
$depScript = Join-Path $PSScriptRoot "configure-service-dependencies.ps1"
if (Test-Path $depScript) {
    Write-Host "  Running dependency configuration..." -ForegroundColor Gray
    & $depScript
} else {
    Write-Host "  ⚠️  Dependency script not found, skipping" -ForegroundColor Yellow
    Write-Host "  Run manually: .\scripts\configure-service-dependencies.ps1" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Migration Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services migrated:" -ForegroundColor White
foreach ($service in $services) {
    $targetFile = Join-Path $service.TargetDir $service.Script
    if (Test-Path $targetFile) {
        Write-Host "  ✓ $($service.Name) -> $targetFile" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  $($service.Name) -> Not found" -ForegroundColor Yellow
    }
}
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Start services: nssm start <ServiceName>" -ForegroundColor Gray
Write-Host "  2. Check status: nssm status <ServiceName>" -ForegroundColor Gray
Write-Host "  3. Check logs in: C:\Tools\Ollama\Data\logs\" -ForegroundColor Gray
Write-Host ""

