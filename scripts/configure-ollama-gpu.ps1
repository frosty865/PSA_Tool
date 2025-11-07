# Configure Ollama to use GPU
# This script sets environment variables for Ollama to utilize GPU resources

Write-Host ""
Write-Host "Configuring Ollama for GPU Usage..." -ForegroundColor Cyan
Write-Host ("=" * 60)

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host ""
    Write-Host "WARNING: This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# GPU Configuration
Write-Host ""
Write-Host "GPU Configuration:" -ForegroundColor Yellow

# Check for NVIDIA GPU
try {
    $gpuInfo = nvidia-smi --query-gpu=name --format=csv,noheader,nounits 2>$null
    if ($gpuInfo) {
        Write-Host "  Detected GPU: $($gpuInfo.Trim())" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: No NVIDIA GPU detected" -ForegroundColor Yellow
        Write-Host "  Ollama will use CPU only" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  WARNING: Could not detect GPU: $_" -ForegroundColor Yellow
}

# Recommended settings for GPU
Write-Host ""
Write-Host "Recommended Settings:" -ForegroundColor Yellow
Write-Host "  OLLAMA_NUM_GPU=1          (Use 1 GPU)" -ForegroundColor White
Write-Host "  OLLAMA_GPU_LAYERS=35      (Use 35 layers on GPU, adjust based on model size)" -ForegroundColor White
Write-Host "  OLLAMA_NUM_THREAD=8       (CPU threads for non-GPU operations)" -ForegroundColor White

# Get current NSSM environment
Write-Host ""
Write-Host "Current NSSM Configuration:" -ForegroundColor Yellow
try {
    $currentEnv = nssm get "VOFC-Ollama" AppEnvironmentExtra 2>$null
    if ($currentEnv) {
        Write-Host "  Current environment variables:" -ForegroundColor White
        $currentEnv -split "`n" | ForEach-Object {
            if ($_ -match "=") {
                Write-Host "    $_" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "  No environment variables currently set" -ForegroundColor Gray
    }
} catch {
    Write-Host "  Could not read current config: $_" -ForegroundColor Yellow
}

# Ask for confirmation
Write-Host ""
Write-Host "Do you want to configure Ollama to use GPU? (Y/N)" -ForegroundColor Cyan
$response = Read-Host

if ($response -ne "Y" -and $response -ne "y") {
    Write-Host "Configuration cancelled." -ForegroundColor Yellow
    exit 0
}

# Build new environment string
Write-Host ""
Write-Host "Setting GPU configuration..." -ForegroundColor Yellow

$newEnvVars = @()
if ($currentEnv) {
    # Preserve existing variables
    $currentEnv -split "`n" | ForEach-Object {
        if ($_ -match "=" -and $_ -notmatch "OLLAMA_NUM_GPU" -and $_ -notmatch "OLLAMA_GPU_LAYERS" -and $_ -notmatch "OLLAMA_NUM_THREAD") {
            $newEnvVars += $_
        }
    }
}

# Add GPU configuration
$newEnvVars += "OLLAMA_NUM_GPU=1"
$newEnvVars += "OLLAMA_GPU_LAYERS=35"
$newEnvVars += "OLLAMA_NUM_THREAD=8"

$envString = $newEnvVars -join "`n"

# Set NSSM environment
try {
    nssm set "VOFC-Ollama" AppEnvironmentExtra $envString
    Write-Host "  OK: Environment variables set" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "New Configuration:" -ForegroundColor Yellow
    $newEnvVars | ForEach-Object {
        Write-Host "    $_" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "IMPORTANT: Restart Ollama service for changes to take effect:" -ForegroundColor Yellow
    Write-Host "  nssm restart VOFC-Ollama" -ForegroundColor White
    Write-Host ""
    
    Write-Host "Do you want to restart Ollama now? (Y/N)" -ForegroundColor Cyan
    $restart = Read-Host
    
    if ($restart -eq "Y" -or $restart -eq "y") {
        Write-Host ""
        Write-Host "Restarting Ollama service..." -ForegroundColor Yellow
        nssm restart "VOFC-Ollama"
        Start-Sleep -Seconds 5
        Write-Host "  OK: Ollama service restarted" -ForegroundColor Green
        Write-Host ""
        Write-Host "Note: It may take 30-60 seconds for Ollama to fully start and load models." -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "  ERROR: Failed to set environment variables: $_" -ForegroundColor Red
    Write-Host "  You may need to set them manually:" -ForegroundColor Yellow
    Write-Host "    nssm set VOFC-Ollama AppEnvironmentExtra OLLAMA_NUM_GPU=1`nOLLAMA_GPU_LAYERS=35`nOLLAMA_NUM_THREAD=8" -ForegroundColor White
}

Write-Host ""

