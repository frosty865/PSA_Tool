# Install VOFC Model Manager Service
# Run this script as Administrator
#
# This script installs and configures the VOFC-ModelManager service
# to run continuously, checking model performance every 6 hours.

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Install VOFC-ModelManager Service" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Running as Administrator" -ForegroundColor Green
Write-Host ""

# Auto-detect project root (this script is in scripts/ directory)
$scriptLocation = $PSScriptRoot
if ($scriptLocation -match '\\scripts$') {
    $projectRoot = Split-Path $scriptLocation -Parent
} else {
    # If not in scripts/, assume current directory is project root
    $projectRoot = $scriptLocation
}

# Configuration
$serviceName = "VOFC-ModelManager"

# Try to use virtual environment Python first, fallback to system Python
$venvPython = Join-Path $projectRoot "venv\Scripts\python.exe"
$systemPython = "C:\Program Files\Python311\python.exe"

if (Test-Path $venvPython) {
    $pythonPath = $venvPython
    Write-Host "✅ Using virtual environment Python: $pythonPath" -ForegroundColor Green
} elseif (Test-Path $systemPython) {
    $pythonPath = $systemPython
    Write-Host "⚠️  Using system Python (venv not found): $pythonPath" -ForegroundColor Yellow
    Write-Host "   Note: Make sure all dependencies are installed in system Python" -ForegroundColor Yellow
} else {
    Write-Host "❌ Python not found!" -ForegroundColor Red
    Write-Host "   Checked:" -ForegroundColor Yellow
    Write-Host "     - $venvPython" -ForegroundColor Yellow
    Write-Host "     - $systemPython" -ForegroundColor Yellow
    exit 1
}

$scriptPath = Join-Path $projectRoot "services\model_manager.py"
$workingDir = $projectRoot
$logDir = "C:\Tools\VOFC_Logs"
$stdoutLog = "$logDir\model_manager.out.log"
$stderrLog = "$logDir\model_manager.err.log"

Write-Host "Detected project root: $projectRoot" -ForegroundColor Cyan
Write-Host ""

# Check if service already exists
$existingStatus = nssm status $serviceName 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "⚠️  Service '$serviceName' already exists!" -ForegroundColor Yellow
    Write-Host "Current status: $existingStatus" -ForegroundColor Cyan
    Write-Host ""
    $response = Read-Host "Remove and reinstall? (y/N)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "Stopping existing service..." -ForegroundColor Yellow
        nssm stop $serviceName 2>&1 | Out-Null
        Start-Sleep -Seconds 2
        Write-Host "Removing existing service..." -ForegroundColor Yellow
        nssm remove $serviceName confirm 2>&1 | Out-Null
        Start-Sleep -Seconds 1
        Write-Host "✅ Service removed" -ForegroundColor Green
    } else {
        Write-Host "Cancelled. Exiting." -ForegroundColor Yellow
        exit 0
    }
}

# Verify paths exist
Write-Host "Verifying paths..." -ForegroundColor Yellow

if (-not (Test-Path $pythonPath)) {
    Write-Host "❌ Python not found at: $pythonPath" -ForegroundColor Red
    Write-Host "Please update the path in this script." -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Python found: $pythonPath" -ForegroundColor Green

if (-not (Test-Path $scriptPath)) {
    Write-Host "❌ Model Manager script not found at: $scriptPath" -ForegroundColor Red
    Write-Host "Please ensure the script exists." -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Script found: $scriptPath" -ForegroundColor Green

if (-not (Test-Path $workingDir)) {
    Write-Host "⚠️  Working directory not found: $workingDir" -ForegroundColor Yellow
    Write-Host "Creating directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $workingDir -Force | Out-Null
    Write-Host "✅ Created working directory" -ForegroundColor Green
} else {
    Write-Host "✅ Working directory exists: $workingDir" -ForegroundColor Green
}

# Create log directory if it doesn't exist
if (-not (Test-Path $logDir)) {
    Write-Host "Creating log directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    Write-Host "✅ Created log directory: $logDir" -ForegroundColor Green
} else {
    Write-Host "✅ Log directory exists: $logDir" -ForegroundColor Green
}

Write-Host ""

# Install service
Write-Host "Installing service..." -ForegroundColor Yellow
Write-Host "  Service Name: $serviceName" -ForegroundColor Cyan
Write-Host "  Python: $pythonPath" -ForegroundColor Cyan
Write-Host "  Script: $scriptPath" -ForegroundColor Cyan
Write-Host "  Working Directory: $workingDir" -ForegroundColor Cyan
Write-Host ""

nssm install $serviceName $pythonPath $scriptPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install service!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Service installed" -ForegroundColor Green
Write-Host ""

# Configure service parameters
Write-Host "Configuring service parameters..." -ForegroundColor Yellow

nssm set $serviceName AppDirectory $workingDir
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Warning: Failed to set AppDirectory" -ForegroundColor Yellow
}

nssm set $serviceName AppStdout $stdoutLog
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Warning: Failed to set AppStdout" -ForegroundColor Yellow
}

nssm set $serviceName AppStderr $stderrLog
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Warning: Failed to set AppStderr" -ForegroundColor Yellow
}

nssm set $serviceName AppExit Default Restart
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Warning: Failed to set AppExit" -ForegroundColor Yellow
}

nssm set $serviceName Start SERVICE_AUTO_START
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Warning: Failed to set auto-start" -ForegroundColor Yellow
}

Write-Host "✅ Service configured" -ForegroundColor Green
Write-Host ""

# Configure environment variables
Write-Host "Configuring environment variables..." -ForegroundColor Yellow

# Try to load from .env file first
$envFile = Join-Path $projectRoot ".env"
$supabaseUrl = $null
$supabaseKey = $null

if (Test-Path $envFile) {
    Write-Host "Reading .env file..." -ForegroundColor Cyan
    $envContent = Get-Content $envFile
    foreach ($line in $envContent) {
        if ($line -match '^\s*SUPABASE_URL\s*=\s*(.+)$') {
            $supabaseUrl = $matches[1].Trim()
        }
        if ($line -match '^\s*NEXT_PUBLIC_SUPABASE_URL\s*=\s*(.+)$' -and -not $supabaseUrl) {
            $supabaseUrl = $matches[1].Trim()
        }
        if ($line -match '^\s*SUPABASE_SERVICE_ROLE_KEY\s*=\s*(.+)$') {
            $supabaseKey = $matches[1].Trim()
        }
    }
}

# Fallback to system environment variables
if (-not $supabaseUrl) {
    $supabaseUrl = [System.Environment]::GetEnvironmentVariable("SUPABASE_URL", "Machine")
    if (-not $supabaseUrl) {
        $supabaseUrl = [System.Environment]::GetEnvironmentVariable("SUPABASE_URL", "User")
    }
    if (-not $supabaseUrl) {
        $supabaseUrl = [System.Environment]::GetEnvironmentVariable("NEXT_PUBLIC_SUPABASE_URL", "Machine")
    }
    if (-not $supabaseUrl) {
        $supabaseUrl = [System.Environment]::GetEnvironmentVariable("NEXT_PUBLIC_SUPABASE_URL", "User")
    }
}

if (-not $supabaseKey) {
    $supabaseKey = [System.Environment]::GetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", "Machine")
    if (-not $supabaseKey) {
        $supabaseKey = [System.Environment]::GetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", "User")
    }
}

# Set environment variables in NSSM if found
if ($supabaseUrl -and $supabaseKey) {
    $envString = "SUPABASE_URL=$supabaseUrl SUPABASE_SERVICE_ROLE_KEY=$supabaseKey"
    if ($supabaseUrl) {
        $envString += " NEXT_PUBLIC_SUPABASE_URL=$supabaseUrl"
    }
    
    nssm set $serviceName AppEnvironment $envString
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Environment variables configured from .env/system environment" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Warning: Failed to set environment variables" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Supabase credentials not found in .env or system environment" -ForegroundColor Yellow
    Write-Host "   The service will try to load from .env file at runtime" -ForegroundColor Cyan
    Write-Host "   Or run: .\scripts\configure-model-manager-env.ps1" -ForegroundColor Cyan
}
Write-Host ""

# Set recovery options (self-healing)
Write-Host "Setting recovery options (self-healing)..." -ForegroundColor Yellow
sc failure $serviceName reset= 0 actions= restart/60000/restart/60000/restart/60000 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Recovery options configured (auto-restart on failure)" -ForegroundColor Green
} else {
    Write-Host "⚠️  Warning: Failed to set recovery options (non-critical)" -ForegroundColor Yellow
}
Write-Host ""

# Test Supabase connection before starting
Write-Host "Testing Supabase connection..." -ForegroundColor Yellow
$testScript = @"
import sys
from pathlib import Path
sys.path.insert(0, r'$workingDir')

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_file = Path(r'$workingDir') / '.env'
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass
except Exception:
    pass

try:
    from services.supabase_client import get_supabase_client
    s = get_supabase_client()
    result = s.table('learning_events').select('*').limit(1).execute()
    print('✅ Supabase connection successful')
    print(f'   Found {len(result.data)} learning events (sample)')
    sys.exit(0)
except Exception as e:
    print(f'❌ Supabase connection failed: {e}')
    sys.exit(1)
"@

$testScriptPath = "$env:TEMP\test_supabase_connection.py"
$testScript | Out-File -FilePath $testScriptPath -Encoding UTF8

& $pythonPath $testScriptPath
$supabaseTestResult = $LASTEXITCODE

Remove-Item $testScriptPath -ErrorAction SilentlyContinue

if ($supabaseTestResult -ne 0) {
    Write-Host "⚠️  Supabase connection test failed!" -ForegroundColor Yellow
    Write-Host "   The service will still be installed, but may fail to start." -ForegroundColor Yellow
    Write-Host "   Please check your SUPABASE_URL and SUPABASE_KEY environment variables." -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Continue with installation anyway? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Cancelled. Please fix Supabase configuration and try again." -ForegroundColor Yellow
        nssm remove $serviceName confirm 2>&1 | Out-Null
        exit 1
    }
} else {
    Write-Host "✅ Supabase connection test passed" -ForegroundColor Green
}
Write-Host ""

# Start service
Write-Host "Starting service..." -ForegroundColor Yellow
nssm start $serviceName

Start-Sleep -Seconds 3

$status = nssm status $serviceName 2>&1
if ($status -eq "SERVICE_RUNNING") {
    Write-Host "✅ Service started successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Service status: $status" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Check the logs:" -ForegroundColor Cyan
    Write-Host "  $logDir\model_manager.log" -ForegroundColor White
    Write-Host "  $stdoutLog" -ForegroundColor White
    Write-Host "  $stderrLog" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verify service status
Write-Host "Service Status:" -ForegroundColor Yellow
$serviceStatus = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($serviceStatus) {
    Write-Host "  Status: $($serviceStatus.Status)" -ForegroundColor $(if ($serviceStatus.Status -eq 'Running') { 'Green' } else { 'Yellow' })
    Write-Host "  Start Type: $($serviceStatus.StartType)" -ForegroundColor Cyan
} else {
    Write-Host "  ⚠️  Could not retrieve service status" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Service commands:" -ForegroundColor Yellow
Write-Host "  nssm status $serviceName" -ForegroundColor White
Write-Host "  nssm start $serviceName" -ForegroundColor White
Write-Host "  nssm stop $serviceName" -ForegroundColor White
Write-Host "  nssm restart $serviceName" -ForegroundColor White
Write-Host "  Get-Service '$serviceName'" -ForegroundColor White
Write-Host ""

Write-Host "Monitor logs:" -ForegroundColor Yellow
Write-Host "  Get-Content -Path `"$logDir\model_manager.log`" -Wait" -ForegroundColor White
Write-Host "  Get-Content -Path `"$stdoutLog`" -Wait" -ForegroundColor White
Write-Host "  Get-Content -Path `"$stderrLog`" -Wait" -ForegroundColor White
Write-Host ""

