# configure-service-dependencies.ps1
# Configures service startup dependencies to ensure correct startup order
# Run as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuring Service Dependencies" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    exit 1
}

# Service startup order and dependencies
# Format: @{ ServiceName = @("Dependency1", "Dependency2", ...) }
$serviceDependencies = @{
    # Core infrastructure services (no dependencies)
    "VOFC-Ollama" = @()  # Ollama server - must start first
    
    # Services that depend on Ollama
    "VOFC-Processor" = @("VOFC-Ollama")
    "VOFC-ModelManager" = @("VOFC-Ollama")
    "VOFC-AutoRetrain" = @("VOFC-Ollama")
    
    # Flask API (may depend on database/other services)
    "VOFC-Flask" = @("VOFC-Ollama")
    
    # Tunnel (depends on Flask)
    "VOFC-Tunnel" = @("VOFC-Flask")
}

Write-Host "Step 1: Setting service dependencies..." -ForegroundColor Yellow
Write-Host ""

foreach ($service in $serviceDependencies.Keys) {
    $deps = $serviceDependencies[$service]
    
    # Check if service exists
    $status = nssm status $service 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [$service] ⚠️  Service not installed, skipping" -ForegroundColor Yellow
        continue
    }
    
    Write-Host "  [$service]" -ForegroundColor Cyan
    
    if ($deps.Count -eq 0) {
        Write-Host "    No dependencies (core service)" -ForegroundColor Gray
        # Ensure no dependencies are set
        sc.exe config $service depend= "" 2>&1 | Out-Null
    } else {
        Write-Host "    Dependencies: $($deps -join ', ')" -ForegroundColor Gray
        
        # Verify all dependencies exist
        $allExist = $true
        foreach ($dep in $deps) {
            $depStatus = nssm status $dep 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host "    ⚠️  Dependency '$dep' not found" -ForegroundColor Yellow
                $allExist = $false
            }
        }
        
        if ($allExist) {
            # Set dependencies using sc.exe (Windows Service Control)
            # Format: sc config ServiceName depend= Dependency1/Dependency2
            $depString = $deps -join "/"
            $result = sc.exe config $service depend= $depString 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Dependencies configured" -ForegroundColor Green
            } else {
                Write-Host "    ✗ Failed to set dependencies: $result" -ForegroundColor Red
            }
        } else {
            Write-Host "    ⚠️  Skipping (missing dependencies)" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "Step 2: Setting startup delays (optional)..." -ForegroundColor Yellow
Write-Host ""

# Services that should wait a bit after dependencies start
$startupDelays = @{
    "VOFC-Processor" = 5      # Wait 5 seconds after Ollama starts
    "VOFC-ModelManager" = 10   # Wait 10 seconds after Ollama starts
    "VOFC-AutoRetrain" = 15   # Wait 15 seconds after Ollama starts
    "VOFC-Flask" = 3          # Wait 3 seconds after Ollama starts
    "VOFC-Tunnel" = 5         # Wait 5 seconds after Flask starts
}

foreach ($service in $startupDelays.Keys) {
    $delay = $startupDelays[$service]
    
    $status = nssm status $service 2>&1
    if ($LASTEXITCODE -ne 0) {
        continue
    }
    
    # NSSM doesn't directly support startup delays, but we can use AppThrottle
    # This prevents rapid restarts, giving dependencies time to start
    nssm set $service AppThrottle ($delay * 1000) 2>&1 | Out-Null
    Write-Host "  [$service] Startup throttle: ${delay}s" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Step 3: Verifying dependencies..." -ForegroundColor Yellow
Write-Host ""

foreach ($service in $serviceDependencies.Keys) {
    $status = nssm status $service 2>&1
    if ($LASTEXITCODE -ne 0) {
        continue
    }
    
    # Query service dependencies using sc.exe
    $queryOutput = sc.exe qc $service 2>&1
    
    # Convert to string if it's an array
    $query = if ($queryOutput -is [Array]) {
        $queryOutput -join "`n"
    } else {
        $queryOutput.ToString()
    }
    
    # Extract dependencies line
    $depLine = $query -split "`n" | Where-Object { $_ -match "DEPENDENCIES" } | Select-Object -First 1
    
    if ($depLine) {
        # Match pattern: "DEPENDENCIES       : ServiceName" or "DEPENDENCIES : -"
        if ($depLine -match "DEPENDENCIES\s+:\s+(.+)") {
            $deps = $matches[1].Trim()
            if ($deps -eq "" -or $deps -eq "-" -or $deps -match "^\s*$") {
                Write-Host "  [$service] No dependencies" -ForegroundColor Gray
            } else {
                Write-Host "  [$service] Dependencies: $deps" -ForegroundColor Green
            }
        } else {
            Write-Host "  [$service] $depLine" -ForegroundColor Gray
        }
    } else {
        Write-Host "  [$service] Could not find dependencies line" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Service Dependencies Configured!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Startup Order:" -ForegroundColor Yellow
Write-Host "  1. VOFC-Ollama (no dependencies)" -ForegroundColor White
Write-Host "  2. VOFC-Flask (depends on Ollama)" -ForegroundColor White
Write-Host "  3. VOFC-Processor (depends on Ollama)" -ForegroundColor White
Write-Host "  4. VOFC-ModelManager (depends on Ollama)" -ForegroundColor White
Write-Host "  5. VOFC-AutoRetrain (depends on Ollama)" -ForegroundColor White
Write-Host "  6. VOFC-Tunnel (depends on Flask)" -ForegroundColor White
Write-Host ""
Write-Host "Note: Windows will automatically start dependencies first." -ForegroundColor Gray
Write-Host ""

