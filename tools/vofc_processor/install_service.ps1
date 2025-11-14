# install_service.ps1
# Installs VOFC Processor as a Windows background service using NSSM
# Uses VOFC-Processor naming convention

$ServiceName = "VOFC-Processor"  # Standard name

# Check if service is marked for deletion and wait if needed
Write-Host "Checking for existing service..." -ForegroundColor Gray
$existingStatus = nssm status $ServiceName 2>&1
if ($LASTEXITCODE -eq 0) {
    # Service exists - check if it's marked for deletion
    $scQuery = sc.exe query $ServiceName 2>&1
    if ($scQuery -match "MARKED_FOR_DELETION" -or $scQuery -match "DELETE_PENDING") {
        Write-Host "  Service is marked for deletion. Waiting for cleanup..." -ForegroundColor Yellow
        Write-Host "  This may take 10-30 seconds..." -ForegroundColor Gray
        
        # Wait up to 30 seconds
        $waited = 0
        while ($waited -lt 30) {
            Start-Sleep -Seconds 2
            $waited += 2
            $checkStatus = sc.exe query $ServiceName 2>&1
            if ($checkStatus -match "does not exist" -or $LASTEXITCODE -ne 0) {
                Write-Host "  ✓ Service cleaned up after $waited seconds" -ForegroundColor Green
                break
            }
            Write-Host "  Waiting... ($waited/30 seconds)" -ForegroundColor Gray
        }
        
        # If still marked, try to force remove
        if ($waited -ge 30) {
            Write-Host "  ⚠️  Service still marked for deletion" -ForegroundColor Yellow
            Write-Host "  Attempting force removal..." -ForegroundColor Gray
            nssm stop $ServiceName 2>&1 | Out-Null
            Start-Sleep -Seconds 2
            sc.exe delete $ServiceName 2>&1 | Out-Null
            Start-Sleep -Seconds 5
        }
    } else {
        # Service exists and is not marked for deletion - ask to remove
        Write-Host "  Service already exists. Removing..." -ForegroundColor Yellow
        nssm stop $ServiceName 2>&1 | Out-Null
        Start-Sleep -Seconds 2
        nssm remove $ServiceName confirm 2>&1 | Out-Null
        Start-Sleep -Seconds 3
    }
}
# Server deployment paths - all services run from C:\Tools with VOFC-* naming
$PythonPath = "C:\Tools\python\python.exe"
$ScriptPath = "C:\Tools\VOFC-Processor\vofc_processor.py"
$TargetDir = "C:\Tools\VOFC-Processor"

# Check Python path - try multiple locations
if (-not (Test-Path $PythonPath)) {
    $PythonPath = "C:\Tools\python.exe"
    if (-not (Test-Path $PythonPath)) {
        Write-Host "Error: Python not found at C:\Tools\python\python.exe or C:\Tools\python.exe" -ForegroundColor Red
        Write-Host "Please ensure Python is installed at C:\Tools\python\" -ForegroundColor Yellow
        exit 1
    }
}

# Ensure target directory exists
if (-not (Test-Path $TargetDir)) {
    Write-Host "Creating directory: $TargetDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

# Copy files from source to target if running from project directory
$SourceDir = $PSScriptRoot
if (Test-Path (Join-Path $SourceDir "vofc_processor.py")) {
    $sourceFile = Join-Path $SourceDir "vofc_processor.py"
    $targetFile = Join-Path $TargetDir "vofc_processor.py"
    
    if (-not (Test-Path $targetFile) -or (Test-Path $sourceFile -and (Get-Item $sourceFile).LastWriteTime -gt (Get-Item $targetFile).LastWriteTime)) {
        Write-Host "Copying vofc_processor.py to $TargetDir" -ForegroundColor Yellow
        Copy-Item $sourceFile $targetFile -Force
    }
}

if (Test-Path (Join-Path $SourceDir "requirements.txt")) {
    Copy-Item (Join-Path $SourceDir "requirements.txt") (Join-Path $TargetDir "requirements.txt") -Force -ErrorAction SilentlyContinue
}

if (Test-Path (Join-Path $SourceDir "__init__.py")) {
    Copy-Item (Join-Path $SourceDir "__init__.py") (Join-Path $TargetDir "__init__.py") -Force -ErrorAction SilentlyContinue
}

# Verify script path exists (check new location first, then legacy)
if (-not (Test-Path $ScriptPath)) {
    # Try legacy path
    $LegacyScriptPath = "C:\Tools\vofc_processor\vofc_processor.py"
    if (Test-Path $LegacyScriptPath) {
        Write-Host "Found script at legacy location, using: $LegacyScriptPath" -ForegroundColor Yellow
        $ScriptPath = $LegacyScriptPath
        $TargetDir = "C:\Tools\vofc_processor"
    } else {
        Write-Host "Error: vofc_processor.py not found at: $ScriptPath" -ForegroundColor Red
        Write-Host "Please ensure files are copied to C:\Tools\VOFC-Processor\" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "Installing $ServiceName..."
Write-Host "  Python: $PythonPath"
Write-Host "  Script: $ScriptPath"

# Check if NSSM is available - try C:\Tools\nssm first
$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
    $nssmCheck = Get-Command nssm -ErrorAction SilentlyContinue
    if (-not $nssmCheck) {
        Write-Host "Error: NSSM not found. Please install NSSM at C:\Tools\nssm\ or add it to PATH" -ForegroundColor Red
        exit 1
    }
}

# Install service
& $nssmPath install $ServiceName $PythonPath $ScriptPath

# Configure service - use script directory as working directory
$AppDirectory = Split-Path $ScriptPath -Parent
& $nssmPath set $ServiceName AppDirectory $AppDirectory
& $nssmPath set $ServiceName Start SERVICE_AUTO_START
& $nssmPath set $ServiceName AppStdout "C:\Tools\Ollama\Data\logs\vofc_processor_out.log"
& $nssmPath set $ServiceName AppStderr "C:\Tools\Ollama\Data\logs\vofc_processor_err.log"
& $nssmPath set $ServiceName AppStopMethodSkip 6

Write-Host "Service installed. Starting now..."
& $nssmPath start $ServiceName

Write-Host "Service installation complete!"
Write-Host "  Service Name: $ServiceName"
Write-Host "  Status: Check with 'nssm status $ServiceName'"
Write-Host "  Logs: C:\Tools\Ollama\Data\logs\"

