# Service Migration Script
# Removes old services and installs new VOFC-Processor service

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VOFC Service Migration Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# ============================================================
# PART 1: Remove Old Services
# ============================================================
Write-Host "PART 1: Removing Old Services" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow
Write-Host ""

$oldServices = @("VOFC-Phase1", "VOFC-AutoProcessor", "VOFC-Auditor")

foreach ($service in $oldServices) {
    Write-Host "Checking $service..." -ForegroundColor White
    
    # Check if service exists
    $status = nssm status $service 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Found $service - removing..." -ForegroundColor Yellow
        
        # Stop service
        Write-Host "    Stopping service..." -ForegroundColor Gray
        nssm stop $service | Out-Null
        Start-Sleep -Seconds 2
        
        # Remove service
        Write-Host "    Removing service..." -ForegroundColor Gray
        nssm remove $service confirm | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ $service removed successfully" -ForegroundColor Green
        } else {
            Write-Host "  ✗ Failed to remove $service" -ForegroundColor Red
        }
    } else {
        Write-Host "  $service does not exist (skipping)" -ForegroundColor Gray
    }
    Write-Host ""
}

# ============================================================
# PART 2: Verify Old Services Are Gone
# ============================================================
Write-Host "Verifying old services are removed..." -ForegroundColor Yellow
$allRemoved = $true
foreach ($service in $oldServices) {
    $status = nssm status $service 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ⚠️  WARNING: $service still exists!" -ForegroundColor Red
        $allRemoved = $false
    }
}

if ($allRemoved) {
    Write-Host "  ✓ All old services removed" -ForegroundColor Green
} else {
    Write-Host "  ✗ Some services still exist - please remove manually" -ForegroundColor Red
}
Write-Host ""

# ============================================================
# PART 3: Install New Service
# ============================================================
Write-Host "PART 2: Installing New Service" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow
Write-Host ""

# Check if service already exists
Write-Host "Checking if VOFC-Processor already exists..." -ForegroundColor White
$existingStatus = nssm status VOFC-Processor 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  VOFC-Processor already exists!" -ForegroundColor Yellow
    $response = Read-Host "  Do you want to remove and reinstall? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "    Stopping existing service..." -ForegroundColor Gray
        nssm stop VOFC-Processor | Out-Null
        Start-Sleep -Seconds 2
        
        Write-Host "    Removing existing service..." -ForegroundColor Gray
        nssm remove VOFC-Processor confirm | Out-Null
        Write-Host "  ✓ Existing service removed" -ForegroundColor Green
    } else {
        Write-Host "  Skipping installation (service already exists)" -ForegroundColor Yellow
        exit 0
    }
    Write-Host ""
}

# Navigate to service directory
$serviceDir = Join-Path $PSScriptRoot "..\tools\vofc_processor"
if (-not (Test-Path $serviceDir)) {
    Write-Host "ERROR: Service directory not found: $serviceDir" -ForegroundColor Red
    Write-Host "Please ensure you're running this from the scripts directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "Service directory: $serviceDir" -ForegroundColor White
Set-Location $serviceDir

# Check if required files exist
Write-Host "Checking required files..." -ForegroundColor White
$requiredFiles = @("vofc_processor.py", "requirements.txt", "install_service.ps1")
$allFilesExist = $true
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file not found!" -ForegroundColor Red
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Host "ERROR: Required files missing!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Install Python dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor White
Write-Host "  Running: pip install -r requirements.txt" -ForegroundColor Gray
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠️  WARNING: Some dependencies may have failed to install" -ForegroundColor Yellow
    Write-Host "  You may need to install them manually" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
}
Write-Host ""

# Check environment variables
Write-Host "Checking environment variables..." -ForegroundColor White
$supabaseUrl = $env:SUPABASE_URL
$supabaseKey = $env:SUPABASE_KEY

if (-not $supabaseUrl) {
    Write-Host "  ⚠️  WARNING: SUPABASE_URL not set" -ForegroundColor Yellow
    Write-Host "  You can set it with: `$env:SUPABASE_URL = 'https://your-project.supabase.co'" -ForegroundColor Gray
} else {
    Write-Host "  ✓ SUPABASE_URL is set" -ForegroundColor Green
}

if (-not $supabaseKey) {
    Write-Host "  ⚠️  WARNING: SUPABASE_KEY not set" -ForegroundColor Yellow
    Write-Host "  You can set it with: `$env:SUPABASE_KEY = 'your-key'" -ForegroundColor Gray
} else {
    Write-Host "  ✓ SUPABASE_KEY is set" -ForegroundColor Green
}
Write-Host ""

# Check Ollama
Write-Host "Checking Ollama server..." -ForegroundColor White
try {
    $ollamaList = ollama list 2>&1
    if ($LASTEXITCODE -eq 0) {
        if ($ollamaList -match "vofc-engine") {
            Write-Host "  ✓ Ollama is running and vofc-engine model is available" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  WARNING: Ollama is running but vofc-engine:latest not found" -ForegroundColor Yellow
            Write-Host "  Available models:" -ForegroundColor Gray
            Write-Host $ollamaList -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠️  WARNING: Could not connect to Ollama server" -ForegroundColor Yellow
        Write-Host "  Make sure Ollama is running: ollama serve" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ⚠️  WARNING: Ollama command not found" -ForegroundColor Yellow
    Write-Host "  Make sure Ollama is installed and in PATH" -ForegroundColor Gray
}
Write-Host ""

# Run installation script
Write-Host "Running installation script..." -ForegroundColor White
Write-Host "  Executing: .\install_service.ps1" -ForegroundColor Gray
Write-Host ""

.\install_service.ps1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Installation Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Verify service is running
    Write-Host "Verifying service status..." -ForegroundColor White
    Start-Sleep -Seconds 3
    $serviceStatus = nssm status VOFC-Processor 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Service is installed" -ForegroundColor Green
        Write-Host ""
        Write-Host "Service Management Commands:" -ForegroundColor Yellow
        Write-Host "  Start:   nssm start VOFC-Processor" -ForegroundColor White
        Write-Host "  Stop:    nssm stop VOFC-Processor" -ForegroundColor White
        Write-Host "  Status:  nssm status VOFC-Processor" -ForegroundColor White
        Write-Host "  Logs:    Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_out.log -Tail 50" -ForegroundColor White
    } else {
        Write-Host "  ⚠️  Service may not have started - check logs" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Installation Failed!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the error messages above for details" -ForegroundColor Yellow
    Write-Host "See docs/SERVICE-MIGRATION-GUIDE.md for troubleshooting" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Set environment variables (if not already set)" -ForegroundColor White
Write-Host "  2. Test by dropping a PDF in C:\Tools\Ollama\Data\incoming\" -ForegroundColor White
Write-Host "  3. Check logs: C:\Tools\Ollama\Data\logs\vofc_processor_out.log" -ForegroundColor White
Write-Host ""

