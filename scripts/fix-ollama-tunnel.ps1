# Fix Ollama Tunnel Configuration
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fixing Ollama Tunnel Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Step 1: Stop user-installed Ollama processes
Write-Host "Step 1: Stopping user-installed Ollama processes..." -ForegroundColor Yellow
$userOllama = Get-Process ollama -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*AppData\Local\Programs\Ollama\ollama.exe" }
if ($userOllama) {
    Write-Host "  Found $($userOllama.Count) user-installed Ollama process(es)" -ForegroundColor Cyan
    foreach ($proc in $userOllama) {
        Write-Host "    Stopping process $($proc.Id)..." -ForegroundColor Gray
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Write-Host "  ✓ User-installed Ollama stopped" -ForegroundColor Green
} else {
    Write-Host "  ✓ No user-installed Ollama processes found" -ForegroundColor Green
}

# Step 2: Verify service-managed Ollama is running
Write-Host ""
Write-Host "Step 2: Verifying service-managed Ollama..." -ForegroundColor Yellow
$serviceOllama = Get-Service -Name "VOFC-Ollama" -ErrorAction SilentlyContinue
if ($serviceOllama -and $serviceOllama.Status -eq 'Running') {
    Write-Host "  ✓ VOFC-Ollama service is running" -ForegroundColor Green
    
    # Test if models are accessible
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 5
        $models = ($response.Content | ConvertFrom-Json).models
        Write-Host "  ✓ Ollama API accessible with $($models.Count) model(s)" -ForegroundColor Green
        foreach ($model in $models) {
            Write-Host "    - $($model.name)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ⚠ Ollama API not accessible: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ VOFC-Ollama service is not running!" -ForegroundColor Red
    Write-Host "    Starting service..." -ForegroundColor Yellow
    Start-Service -Name "VOFC-Ollama"
    Start-Sleep -Seconds 3
}

# Step 3: Update tunnel config to use 127.0.0.1:11434
Write-Host ""
Write-Host "Step 3: Verifying tunnel configuration..." -ForegroundColor Yellow
$configFile = "C:\Tools\cloudflared\config.yaml"
if (Test-Path $configFile) {
    $configContent = Get-Content $configFile -Raw
    if ($configContent -match "service:\s*http://127\.0\.0\.1:11434") {
        Write-Host "  ✓ Tunnel config already uses 127.0.0.1:11434" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Updating tunnel config..." -ForegroundColor Yellow
        $configContent = $configContent -replace "service:\s*http://localhost:11434", "service: http://127.0.0.1:11434"
        Set-Content -Path $configFile -Value $configContent -NoNewline
        Write-Host "  ✓ Tunnel config updated" -ForegroundColor Green
    }
} else {
    Write-Host "  ✗ Config file not found: $configFile" -ForegroundColor Red
}

# Step 4: Restart tunnel service
Write-Host ""
Write-Host "Step 4: Restarting tunnel service..." -ForegroundColor Yellow
$tunnelService = Get-Service -Name "VOFC-Tunnel" -ErrorAction SilentlyContinue
if ($tunnelService) {
    Write-Host "  Stopping tunnel service..." -ForegroundColor Cyan
    Stop-Service -Name "VOFC-Tunnel" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    
    Write-Host "  Starting tunnel service..." -ForegroundColor Cyan
    Start-Service -Name "VOFC-Tunnel"
    Start-Sleep -Seconds 5
    
    $status = Get-Service -Name "VOFC-Tunnel"
    if ($status.Status -eq 'Running') {
        Write-Host "  ✓ Tunnel service restarted successfully" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Tunnel service failed to start (Status: $($status.Status))" -ForegroundColor Red
    }
} else {
    Write-Host "  ✗ VOFC-Tunnel service not found!" -ForegroundColor Red
}

# Step 5: Test tunnel endpoint
Write-Host ""
Write-Host "Step 5: Testing tunnel endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
try {
    $tunnelResponse = Invoke-WebRequest -Uri "https://ollama.frostech.site/api/tags" -UseBasicParsing -TimeoutSec 10
    $tunnelModels = ($tunnelResponse.Content | ConvertFrom-Json).models
    if ($tunnelModels.Count -gt 0) {
        Write-Host "  ✓ Tunnel endpoint accessible with $($tunnelModels.Count) model(s)" -ForegroundColor Green
        foreach ($model in $tunnelModels) {
            Write-Host "    - $($model.name)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠ Tunnel endpoint accessible but returns 0 models" -ForegroundColor Yellow
        Write-Host "    This may indicate the tunnel is connecting to the wrong Ollama instance" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ Tunnel endpoint test failed: $_" -ForegroundColor Yellow
    Write-Host "    This may be normal if the tunnel is still connecting..." -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Done! Check the results above." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

