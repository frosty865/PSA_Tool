# Check Ollama GPU and CPU Utilization
# This script checks if Ollama is using GPU/CPU resources efficiently

Write-Host ""
Write-Host "Checking Ollama Resource Utilization..." -ForegroundColor Cyan
Write-Host ("=" * 60)

# Check Ollama processes
Write-Host ""
Write-Host "Ollama Processes:" -ForegroundColor Yellow
$ollamaProcesses = Get-Process ollama -ErrorAction SilentlyContinue
if ($ollamaProcesses) {
    foreach ($proc in $ollamaProcesses) {
        $cpuPercent = if ($proc.CPU) { [math]::Round($proc.CPU, 2) } else { "N/A" }
        $memoryMB = [math]::Round($proc.WorkingSet / 1MB, 2)
        Write-Host "  Process ID: $($proc.Id)" -ForegroundColor White
        Write-Host "    CPU Time: $cpuPercent seconds" -ForegroundColor Gray
        Write-Host "    Memory: $memoryMB MB" -ForegroundColor Gray
    }
} else {
    Write-Host "  WARNING: No Ollama processes found" -ForegroundColor Red
}

# Check GPU utilization
Write-Host ""
Write-Host "GPU Utilization:" -ForegroundColor Yellow
try {
    $gpuInfo = nvidia-smi --query-gpu=name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>$null
    if ($gpuInfo) {
        $gpuData = $gpuInfo -split ","
        Write-Host "  GPU: $($gpuData[0].Trim())" -ForegroundColor White
        $gpuUtil = [int]$gpuData[1].Trim()
        $memUtil = [int]$gpuData[2].Trim()
        Write-Host "    GPU Utilization: $gpuUtil%" -ForegroundColor $(if ($gpuUtil -lt 50) { "Red" } elseif ($gpuUtil -lt 80) { "Yellow" } else { "Green" })
        Write-Host "    Memory Utilization: $memUtil%" -ForegroundColor $(if ($memUtil -lt 50) { "Red" } elseif ($memUtil -lt 80) { "Yellow" } else { "Green" })
        Write-Host "    Memory Used: $($gpuData[3].Trim()) MB / $($gpuData[4].Trim()) MB" -ForegroundColor White
        Write-Host "    Temperature: $($gpuData[5].Trim()) C" -ForegroundColor White
        
        if ($gpuUtil -lt 10) {
            Write-Host "    WARNING: GPU is underutilized!" -ForegroundColor Red
        }
    } else {
        Write-Host "  WARNING: nvidia-smi not available or no NVIDIA GPU detected" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  WARNING: Could not check GPU: $_" -ForegroundColor Yellow
}

# Check CPU utilization
Write-Host ""
Write-Host "CPU Utilization:" -ForegroundColor Yellow
$cpuUsage = Get-Counter '\Processor(_Total)\% Processor Time' -ErrorAction SilentlyContinue
if ($cpuUsage) {
    $cpuPercent = [math]::Round($cpuUsage.CounterSamples[0].CookedValue, 2)
    Write-Host "  Total CPU Usage: $cpuPercent%" -ForegroundColor $(if ($cpuPercent -lt 50) { "Red" } elseif ($cpuPercent -lt 80) { "Yellow" } else { "Green" })
    
    # Check per-core usage
    $cores = Get-Counter '\Processor(*)\% Processor Time' -ErrorAction SilentlyContinue
    if ($cores) {
        $coreCount = ($cores.CounterSamples | Where-Object { $_.InstanceName -notmatch '_Total' }).Count
        Write-Host "  CPU Cores: $coreCount" -ForegroundColor White
    }
} else {
    Write-Host "  WARNING: Could not retrieve CPU usage" -ForegroundColor Yellow
}

# Check Ollama API for model info
Write-Host ""
Write-Host "Ollama API Status:" -ForegroundColor Yellow
try {
    $ollamaHost = $env:OLLAMA_HOST
    if (-not $ollamaHost) {
        $ollamaHost = "http://127.0.0.1:11434"
    }
    
    # Check if Ollama is responding
    $tagsResponse = Invoke-RestMethod -Uri "$ollamaHost/api/tags" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  OK: Ollama is online" -ForegroundColor Green
    Write-Host "  Models available: $($tagsResponse.models.Count)" -ForegroundColor White
    
    # Check for GPU info in model details
    if ($tagsResponse.models.Count -gt 0) {
        $modelName = $tagsResponse.models[0].name
        Write-Host "  Checking model: $modelName" -ForegroundColor White
        
        try {
            $modelInfo = Invoke-RestMethod -Uri "$ollamaHost/api/show" -Method POST -Body (@{name=$modelName} | ConvertTo-Json) -ContentType "application/json" -TimeoutSec 5 -ErrorAction Stop
            if ($modelInfo.details) {
                Write-Host "    Model details available" -ForegroundColor Gray
            }
        } catch {
            Write-Host "    WARNING: Could not get model details: $_" -ForegroundColor Yellow
        }
    }
    
    # Check for running processes
    try {
        $psResponse = Invoke-RestMethod -Uri "$ollamaHost/api/ps" -Method GET -TimeoutSec 5 -ErrorAction Stop
        if ($psResponse.models) {
            Write-Host "  Active model processes: $($psResponse.models.Count)" -ForegroundColor White
            foreach ($model in $psResponse.models) {
                $vramMB = [math]::Round($model.size_vram / 1MB, 2)
                Write-Host "    - $($model.name): $vramMB MB VRAM" -ForegroundColor Gray
            }
        } else {
            Write-Host "  No active model processes" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  WARNING: Could not check active processes: $_" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "  ERROR: Ollama API not responding: $_" -ForegroundColor Red
}

# Check Ollama environment variables
Write-Host ""
Write-Host "Ollama Configuration:" -ForegroundColor Yellow
$ollamaEnvVars = @(
    "OLLAMA_HOST",
    "OLLAMA_NUM_GPU",
    "OLLAMA_NUM_THREAD",
    "OLLAMA_NUMA",
    "CUDA_VISIBLE_DEVICES",
    "OLLAMA_GPU_LAYERS"
)

foreach ($var in $ollamaEnvVars) {
    $value = [Environment]::GetEnvironmentVariable($var, "Machine")
    if (-not $value) {
        $value = [Environment]::GetEnvironmentVariable($var, "User")
    }
    if (-not $value) {
        $value = (Get-Item "Env:$var" -ErrorAction SilentlyContinue).Value
    }
    if ($value) {
        Write-Host "  $var = $value" -ForegroundColor White
    } else {
        Write-Host "  $var = (not set)" -ForegroundColor Gray
    }
}

# Check NSSM service environment
Write-Host ""
Write-Host "NSSM Service Configuration:" -ForegroundColor Yellow
try {
    $nssmEnv = nssm get "VOFC-Ollama" AppEnvironmentExtra 2>$null
    if ($nssmEnv) {
        Write-Host "  Environment variables:" -ForegroundColor White
        $nssmEnv -split "`n" | ForEach-Object {
            if ($_ -match "=") {
                Write-Host "    $_" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "  No custom environment variables set" -ForegroundColor Gray
    }
} catch {
    Write-Host "  WARNING: Could not check NSSM config: $_" -ForegroundColor Yellow
}

# Recommendations
Write-Host ""
Write-Host "Recommendations:" -ForegroundColor Cyan
if ($gpuInfo) {
    $gpuParts = $gpuInfo -split ","
    if ($gpuParts.Count -gt 1) {
        $gpuUtil = [int]$gpuParts[1].Trim()
        if ($gpuUtil -lt 10) {
            Write-Host "  WARNING: GPU is underutilized. Consider:" -ForegroundColor Yellow
            Write-Host "     - Set OLLAMA_NUM_GPU=1 to enable GPU" -ForegroundColor White
            Write-Host "     - Set OLLAMA_GPU_LAYERS to use more GPU layers" -ForegroundColor White
            Write-Host "     - Check if model supports GPU acceleration" -ForegroundColor White
        }
    }
}

Write-Host ""
