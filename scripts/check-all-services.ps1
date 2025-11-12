# check-all-services.ps1
# Comprehensive check of all VOFC services for correct configuration and location
# Run as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VOFC Services Configuration Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator - some checks may fail" -ForegroundColor Yellow
    Write-Host ""
}

# Expected configuration
$expectedPython = "C:\Tools\python\python.exe"
$expectedBase = "C:\Tools\py_scripts"

# Service configurations
$serviceConfigs = @{
    "VOFC-Ollama" = @{
        Type = "Executable"
        ExpectedApp = "C:\Tools\Ollama\ollama.exe"
        ExpectedDir = "C:\Tools\Ollama"
        NeedsEnv = $true
    }
    "VOFC-Flask" = @{
        Type = "Python"
        ExpectedApp = $expectedPython
        ExpectedDir = "C:\Tools\VOFC-Flask"
        ExpectedScript = "server.py"
        NeedsEnv = $true
    }
    "VOFC-Processor" = @{
        Type = "Python"
        ExpectedApp = $expectedPython
        ExpectedDir = "$expectedBase\vofc_processor"
        ExpectedScript = "$expectedBase\vofc_processor\vofc_processor.py"
        NeedsEnv = $true
    }
    "VOFC-ModelManager" = @{
        Type = "Python"
        ExpectedApp = $expectedPython
        ExpectedDir = "$expectedBase\model_manager"
        ExpectedScript = "$expectedBase\model_manager\model_manager.py"
        NeedsEnv = $true
    }
    "VOFC-AutoRetrain" = @{
        Type = "Python"
        ExpectedApp = $expectedPython
        ExpectedDir = "$expectedBase\auto_retrain"
        ExpectedScript = "$expectedBase\auto_retrain\auto_retrain_job.py"
        NeedsEnv = $true
    }
    "VOFC-Tunnel" = @{
        Type = "Executable"
        ExpectedApp = "C:\Tools\cloudflared\cloudflared.exe"
        ExpectedDir = "C:\Tools\cloudflared"
        NeedsEnv = $false
    }
}

$issues = @()
$pausedServices = @()

Write-Host "Checking services..." -ForegroundColor Yellow
Write-Host ""

foreach ($svcName in $serviceConfigs.Keys) {
    $config = $serviceConfigs[$svcName]
    Write-Host "=== $svcName ===" -ForegroundColor Cyan
    
    # Check if service exists
    $status = nssm status $svcName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Service not found" -ForegroundColor Red
        $issues += "${svcName}: Service not installed"
        Write-Host ""
        continue
    }
    
    # Check status
    $statusColor = if ($status -eq "SERVICE_RUNNING") { "Green" } 
                   elseif ($status -eq "SERVICE_PAUSED") { "Red" } 
                   else { "Yellow" }
    Write-Host "  Status: $status" -ForegroundColor $statusColor
    
    if ($status -eq "SERVICE_PAUSED") {
        $pausedServices += $svcName
        $issues += "${svcName}: Service is paused"
    }
    
    # Get service configuration
    $app = nssm get $svcName Application 2>&1
    $params = nssm get $svcName AppParameters 2>&1
    $dir = nssm get $svcName AppDirectory 2>&1
    $env = nssm get $svcName AppEnvironmentExtra 2>&1
    
    # Check application path
    if ($config.Type -eq "Python") {
        if ($app -ne $config.ExpectedApp) {
            Write-Host "  ✗ Python path incorrect" -ForegroundColor Red
            Write-Host "    Current: $app" -ForegroundColor Gray
            Write-Host "    Expected: $($config.ExpectedApp)" -ForegroundColor Yellow
            $issues += "${svcName}: Python path incorrect ($app)"
        } else {
            Write-Host "  ✓ Python path correct" -ForegroundColor Green
        }
        
        # Check script path
        if ($config.ExpectedScript) {
            if ($params -notlike "*$($config.ExpectedScript)*") {
                Write-Host "  ⚠️  Script path may be incorrect" -ForegroundColor Yellow
                Write-Host "    Current: $params" -ForegroundColor Gray
                Write-Host "    Expected: $($config.ExpectedScript)" -ForegroundColor Yellow
                $issues += "${svcName}: Script path may be incorrect"
            } else {
                Write-Host "  ✓ Script path correct" -ForegroundColor Green
            }
        }
    } elseif ($config.Type -eq "Executable") {
        if ($app -notlike "*$($config.ExpectedApp)*") {
            Write-Host "  ⚠️  Executable path may be incorrect" -ForegroundColor Yellow
            Write-Host "    Current: $app" -ForegroundColor Gray
            Write-Host "    Expected: $($config.ExpectedApp)" -ForegroundColor Yellow
        } else {
            Write-Host "  ✓ Executable path correct" -ForegroundColor Green
        }
    }
    
    # Check directory
    if ($dir -notlike "*$($config.ExpectedDir)*") {
        Write-Host "  ⚠️  Directory may be incorrect" -ForegroundColor Yellow
        Write-Host "    Current: $dir" -ForegroundColor Gray
        Write-Host "    Expected: $($config.ExpectedDir)" -ForegroundColor Yellow
        if ($config.Type -eq "Python") {
            $issues += "${svcName}: Directory may be incorrect"
        }
    } else {
        Write-Host "  ✓ Directory correct" -ForegroundColor Green
    }
    
    # Check environment variables
    if ($config.NeedsEnv) {
        if ($env -match "not exist" -or $env -eq "") {
            Write-Host "  ⚠️  Environment variables not set" -ForegroundColor Yellow
            $issues += "${svcName}: Environment variables not set"
        } else {
            Write-Host "  ✓ Environment variables set" -ForegroundColor Green
        }
    }
    
    Write-Host ""
}

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($issues.Count -eq 0) {
    Write-Host "✓ All services are correctly configured!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Found $($issues.Count) issue(s):" -ForegroundColor Yellow
    foreach ($issue in $issues) {
        Write-Host "  - $issue" -ForegroundColor Yellow
    }
}

if ($pausedServices.Count -gt 0) {
    Write-Host ""
    Write-Host "⚠️  Paused services found:" -ForegroundColor Red
    foreach ($svc in $pausedServices) {
        Write-Host "  - $svc" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "To fix paused services, run:" -ForegroundColor Cyan
    foreach ($svc in $pausedServices) {
        Write-Host "  .\scripts\fix-paused-service.ps1 -ServiceName $svc" -ForegroundColor White
    }
}

Write-Host ""

