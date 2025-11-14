# Permanently Fix Ollama Configuration
# Run this script as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Permanently Fix Ollama Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Step 1: Stop all user-installed Ollama processes
Write-Host "Step 1: Stopping user-installed Ollama processes..." -ForegroundColor Yellow
$userOllama = Get-Process ollama -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*AppData\Local\Programs\Ollama\ollama.exe" }
if ($userOllama) {
    Write-Host "  Found $($userOllama.Count) user-installed Ollama process(es)" -ForegroundColor Cyan
    foreach ($proc in $userOllama) {
        Write-Host "    Stopping process $($proc.Id) ($($proc.Path))..." -ForegroundColor Gray
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Write-Host "  ✓ User-installed Ollama stopped" -ForegroundColor Green
} else {
    Write-Host "  ✓ No user-installed Ollama processes found" -ForegroundColor Green
}

# Step 2: Disable user-installed Ollama from auto-starting
Write-Host ""
Write-Host "Step 2: Disabling user-installed Ollama auto-start..." -ForegroundColor Yellow

# Check Windows Startup folder
$startupPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$startupItems = Get-ChildItem -Path $startupPath -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "*ollama*" }
if ($startupItems) {
    Write-Host "  Found startup items:" -ForegroundColor Cyan
    foreach ($item in $startupItems) {
        Write-Host "    - $($item.Name)" -ForegroundColor Gray
        # Remove shortcut (optional - comment out if you want to keep it)
        # Remove-Item -Path $item.FullName -Force
    }
}

# Check Registry Run key
$regRun = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue
if ($regRun) {
    $ollamaKeys = $regRun.PSObject.Properties | Where-Object { $_.Value -like "*ollama*" -and $_.Value -notlike "*VOFC*" }
    if ($ollamaKeys) {
        Write-Host "  Found registry startup entries:" -ForegroundColor Cyan
        foreach ($key in $ollamaKeys) {
            Write-Host "    - $($key.Name): $($key.Value)" -ForegroundColor Gray
            # Remove registry entry (optional - comment out if you want to keep it)
            # Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name $key.Name -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "  ⚠ Note: To permanently disable, manually remove startup entries above" -ForegroundColor Yellow

# Step 3: Verify service-managed Ollama
Write-Host ""
Write-Host "Step 3: Verifying service-managed Ollama..." -ForegroundColor Yellow
$serviceOllama = Get-Service -Name "VOFC-Ollama" -ErrorAction SilentlyContinue
if ($serviceOllama -and $serviceOllama.Status -eq 'Running') {
    Write-Host "  ✓ VOFC-Ollama service is running" -ForegroundColor Green
    
    # Wait a moment for service to be ready
    Start-Sleep -Seconds 2
    
    # Test if models are accessible
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 5
        $models = ($response.Content | ConvertFrom-Json).models
        if ($models.Count -gt 0) {
            Write-Host "  ✓ Ollama API accessible with $($models.Count) model(s):" -ForegroundColor Green
            foreach ($model in $models) {
                Write-Host "    - $($model.name)" -ForegroundColor Gray
            }
        } else {
            Write-Host "  ⚠ Ollama API accessible but no models found" -ForegroundColor Yellow
            Write-Host "    Check OLLAMA_MODELS environment variable" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ⚠ Ollama API not accessible: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ VOFC-Ollama service is not running!" -ForegroundColor Red
    Write-Host "    Starting service..." -ForegroundColor Yellow
    Start-Service -Name "VOFC-Ollama"
    Start-Sleep -Seconds 5
}

# Step 4: Verify only service-managed Ollama is running
Write-Host ""
Write-Host "Step 4: Verifying only service-managed Ollama is running..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
$allOllama = Get-Process ollama -ErrorAction SilentlyContinue
$serviceOllamaProcs = $allOllama | Where-Object { $_.Path -notlike "*AppData\Local\Programs\Ollama\ollama.exe" }
$userOllamaProcs = $allOllama | Where-Object { $_.Path -like "*AppData\Local\Programs\Ollama\ollama.exe" }

if ($serviceOllamaProcs) {
    Write-Host "  ✓ Service-managed Ollama running ($($serviceOllamaProcs.Count) process(es))" -ForegroundColor Green
    foreach ($proc in $serviceOllamaProcs) {
        Write-Host "    - PID $($proc.Id)" -ForegroundColor Gray
    }
}

if ($userOllamaProcs) {
    Write-Host "  ⚠ User-installed Ollama still running ($($userOllamaProcs.Count) process(es))" -ForegroundColor Yellow
    Write-Host "    These will need to be stopped manually or disabled from auto-start" -ForegroundColor Yellow
    foreach ($proc in $userOllamaProcs) {
        Write-Host "    - PID $($proc.Id): $($proc.Path)" -ForegroundColor Gray
    }
} else {
    Write-Host "  ✓ No user-installed Ollama processes running" -ForegroundColor Green
}

# Step 5: Restart tunnel service to pick up config
Write-Host ""
Write-Host "Step 5: Restarting tunnel service..." -ForegroundColor Yellow
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

# Step 6: Test tunnel endpoint
Write-Host ""
Write-Host "Step 6: Testing tunnel endpoint..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
try {
    $tunnelResponse = Invoke-WebRequest -Uri "https://ollama.frostech.site/api/tags" -UseBasicParsing -TimeoutSec 10
    $tunnelModels = ($tunnelResponse.Content | ConvertFrom-Json).models
    if ($tunnelModels.Count -gt 0) {
        Write-Host "  ✓ Tunnel endpoint accessible with $($tunnelModels.Count) model(s):" -ForegroundColor Green
        foreach ($model in $tunnelModels) {
            Write-Host "    - $($model.name)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠ Tunnel endpoint accessible but returns 0 models" -ForegroundColor Yellow
        Write-Host "    The tunnel may be connecting to the wrong Ollama instance" -ForegroundColor Yellow
        Write-Host "    Verify tunnel config uses: http://127.0.0.1:11434" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ Tunnel endpoint test failed: $_" -ForegroundColor Yellow
    Write-Host "    This may be normal if the tunnel is still connecting..." -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To prevent user-installed Ollama from auto-starting:" -ForegroundColor Yellow
Write-Host "1. Open Task Manager → Startup tab" -ForegroundColor White
Write-Host "2. Disable any Ollama entries" -ForegroundColor White
Write-Host "3. Or uninstall user-installed Ollama if not needed" -ForegroundColor White
Write-Host ""
Write-Host "Note: Ollama config.yaml being empty is normal - Ollama uses" -ForegroundColor Gray
Write-Host "      environment variables (OLLAMA_MODELS) for configuration." -ForegroundColor Gray
Write-Host ""

