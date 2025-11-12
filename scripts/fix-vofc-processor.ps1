# fix-vofc-processor.ps1
# Fixes paused service and installs missing dependencies

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fixing VOFC-Processor Service" -ForegroundColor Cyan
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

# Check Python path
if (-not (Test-Path $PythonPath)) {
    $PythonPath = "C:\Python311\python.exe"
    if (-not (Test-Path $PythonPath)) {
        Write-Host "ERROR: Python not found!" -ForegroundColor Red
        Write-Host "Please install Python 3.11 or update the PythonPath variable" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "Step 1: Fixing paused service..." -ForegroundColor Yellow

# Check current status
$status = nssm status $ServiceName 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Current status: $status" -ForegroundColor Gray
    
    if ($status -eq "SERVICE_PAUSED") {
        Write-Host "  Service is paused. Stopping..." -ForegroundColor Yellow
        nssm stop $ServiceName 2>&1 | Out-Null
        Start-Sleep -Seconds 3
        
        # Verify stopped
        $newStatus = nssm status $ServiceName 2>&1
        if ($newStatus -eq "SERVICE_STOPPED") {
            Write-Host "  ✓ Service stopped successfully" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Service status: $newStatus" -ForegroundColor Yellow
        }
    } elseif ($status -eq "SERVICE_RUNNING") {
        Write-Host "  Service is running. Stopping to install dependencies..." -ForegroundColor Yellow
        nssm stop $ServiceName 2>&1 | Out-Null
        Start-Sleep -Seconds 3
    }
} else {
    Write-Host "  Service not found or not accessible" -ForegroundColor Yellow
}
Write-Host ""

# Step 2: Install Python dependencies
Write-Host "Step 2: Installing Python dependencies..." -ForegroundColor Yellow

# Try multiple locations for requirements.txt
$requirementsPaths = @(
    "C:\Tools\VOFC\tools\vofc_processor\requirements.txt",
    "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\tools\vofc_processor\requirements.txt"
)

$requirementsPath = $null
foreach ($path in $requirementsPaths) {
    if (Test-Path $path) {
        $requirementsPath = $path
        break
    }
}

if ($requirementsPath) {
    Write-Host "  Found requirements.txt at: $requirementsPath" -ForegroundColor Gray
    Write-Host "  Installing from requirements.txt..." -ForegroundColor Gray
    & $PythonPath -m pip install -r $requirementsPath
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Dependencies installed successfully" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Failed to install dependencies" -ForegroundColor Red
    }
} else {
    Write-Host "  ⚠️  requirements.txt not found, installing dependencies manually..." -ForegroundColor Yellow
    
    $packages = @("pandas", "PyMuPDF", "requests", "supabase")
    foreach ($package in $packages) {
        Write-Host "  Installing $package..." -ForegroundColor Gray
        & $PythonPath -m pip install $package
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✓ $package installed" -ForegroundColor Green
        } else {
            Write-Host "    ✗ Failed to install $package" -ForegroundColor Red
        }
    }
}
Write-Host ""

# Step 3: Verify dependencies
Write-Host "Step 3: Verifying dependencies..." -ForegroundColor Yellow
$packages = @("pandas", "fitz", "requests", "supabase")
$allInstalled = $true

foreach ($package in $packages) {
    $check = & $PythonPath -c "import $package; print('OK')" 2>&1
    if ($check -match "OK") {
        Write-Host "  ✓ $package is available" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $package is NOT available" -ForegroundColor Red
        $allInstalled = $false
    }
}
Write-Host ""

# Step 4: Check environment variables
Write-Host "Step 4: Checking environment variables..." -ForegroundColor Yellow
$supabaseUrl = [Environment]::GetEnvironmentVariable("SUPABASE_URL", "Machine")
$supabaseKey = [Environment]::GetEnvironmentVariable("SUPABASE_KEY", "Machine")

if (-not $supabaseUrl) {
    $supabaseUrl = [Environment]::GetEnvironmentVariable("SUPABASE_URL", "User")
}
if (-not $supabaseKey) {
    $supabaseKey = [Environment]::GetEnvironmentVariable("SUPABASE_KEY", "User")
    if (-not $supabaseKey) {
        $supabaseKey = [Environment]::GetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", "User")
    }
}

if ($supabaseUrl) {
    Write-Host "  ✓ SUPABASE_URL is set" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  SUPABASE_URL is not set" -ForegroundColor Yellow
}

if ($supabaseKey) {
    Write-Host "  ✓ SUPABASE_KEY is set" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  SUPABASE_KEY is not set" -ForegroundColor Yellow
}
Write-Host ""

# Step 5: Update service path to C:\Tools\VOFC if needed
Write-Host "Step 5: Updating service path to C:\Tools\VOFC..." -ForegroundColor Yellow
$currentParams = nssm get $ServiceName AppParameters 2>&1
$targetPath = "C:\Tools\VOFC\tools\vofc_processor\vofc_processor.py"

if ($currentParams -ne $targetPath) {
    Write-Host "  Current path: $currentParams" -ForegroundColor Gray
    Write-Host "  Updating to: $targetPath" -ForegroundColor Gray
    
    if (Test-Path $targetPath) {
        nssm set $ServiceName AppParameters $targetPath 2>&1 | Out-Null
        nssm set $ServiceName AppDirectory "C:\Tools\VOFC\tools\vofc_processor" 2>&1 | Out-Null
        Write-Host "  ✓ Service path updated" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Target path not found: $targetPath" -ForegroundColor Yellow
        Write-Host "  Service will continue using current path" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✓ Service already using correct path" -ForegroundColor Green
}
Write-Host ""

# Step 6: Start service
if ($allInstalled) {
    Write-Host "Step 6: Starting service..." -ForegroundColor Yellow
    nssm start $ServiceName 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    
    $finalStatus = nssm status $ServiceName 2>&1
    if ($finalStatus -eq "SERVICE_RUNNING") {
        Write-Host "  ✓ Service started successfully!" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Service status: $finalStatus" -ForegroundColor Yellow
        Write-Host "  Check logs at: C:\Tools\Ollama\Data\logs\" -ForegroundColor Gray
    }
} else {
    Write-Host "Step 6: Skipping service start (dependencies not fully installed)" -ForegroundColor Yellow
    Write-Host "  Please fix dependency issues and start the service manually" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Service: $ServiceName" -ForegroundColor White
Write-Host "Status: $(nssm status $ServiceName 2>&1)" -ForegroundColor White
Write-Host "Dependencies: $(if ($allInstalled) { 'Installed' } else { 'Missing' })" -ForegroundColor $(if ($allInstalled) { 'Green' } else { 'Red' })
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Check service status: nssm status $ServiceName" -ForegroundColor Gray
Write-Host "  2. Check logs: Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_out.log -Tail 20" -ForegroundColor Gray
Write-Host "  3. Test by dropping a PDF in: C:\Tools\Ollama\Data\incoming\" -ForegroundColor Gray
Write-Host ""

