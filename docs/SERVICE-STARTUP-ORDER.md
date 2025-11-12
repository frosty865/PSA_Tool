# Service Startup Order Configuration

## Overview

VOFC services have dependencies that require them to start in a specific order. This document explains how startup order is managed.

## Service Dependencies

### Startup Order

1. **VOFC-Ollama** (No dependencies)
   - Core infrastructure service
   - Must start first - all other services depend on it
   - Provides Ollama API server

2. **VOFC-Flask** (Depends on: Ollama)
   - API server
   - Waits for Ollama to be ready
   - Provides REST API endpoints

3. **VOFC-Processor** (Depends on: Ollama)
   - Document processing service
   - Waits for Ollama to be ready
   - Processes PDFs from incoming directory

4. **VOFC-ModelManager** (Depends on: Ollama)
   - Model management service
   - Waits for Ollama to be ready
   - Monitors and retrains models

5. **VOFC-AutoRetrain** (Depends on: Ollama)
   - Automatic retraining service
   - Waits for Ollama to be ready
   - Runs scheduled retraining jobs

6. **VOFC-Tunnel** (Depends on: Flask)
   - Cloudflare tunnel service
   - Waits for Flask to be ready
   - Provides external access

## Configuration Methods

### Method 1: Windows Service Dependencies (Recommended)

Windows automatically manages service dependencies. When a service is configured with dependencies, Windows will:

1. Start dependencies first
2. Wait for dependencies to be running
3. Then start the dependent service

**Configure dependencies:**
```powershell
# Run as Administrator
.\scripts\configure-service-dependencies.ps1
```

This script uses `sc.exe config` to set service dependencies:
```powershell
sc.exe config VOFC-Processor depend= VOFC-Ollama
sc.exe config VOFC-Flask depend= VOFC-Ollama
sc.exe config VOFC-Tunnel depend= VOFC-Flask
```

**Benefits:**
- Automatic - Windows handles startup order
- Reliable - Built into Windows service manager
- Persistent - Survives reboots
- No manual intervention needed

### Method 2: Manual Startup Script

For manual control or testing, use the ordered startup script:

```powershell
# Run as Administrator
.\scripts\start-services-ordered.ps1
```

This script:
- Starts services in dependency order
- Waits between services (configurable delays)
- Reports success/failure for each service
- Shows final status

**Startup delays:**
- VOFC-Ollama: 0s (starts immediately)
- VOFC-Flask: 5s (waits for Ollama)
- VOFC-Processor: 3s (waits for Ollama)
- VOFC-ModelManager: 3s (waits for Ollama)
- VOFC-AutoRetrain: 3s (waits for Ollama)
- VOFC-Tunnel: 5s (waits for Flask)

### Method 3: Stop Services in Reverse Order

When stopping services, stop dependents first:

```powershell
# Run as Administrator
.\scripts\stop-services-ordered.ps1
```

Stop order (reverse of startup):
1. VOFC-Tunnel
2. VOFC-AutoRetrain
3. VOFC-ModelManager
4. VOFC-Processor
5. VOFC-Flask
6. VOFC-Ollama

## Verification

### Check Service Dependencies

```powershell
# Check dependencies for a service
sc.exe qc VOFC-Processor

# Or query all services
$services = @("VOFC-Processor", "VOFC-Flask", "VOFC-ModelManager", "VOFC-AutoRetrain", "VOFC-Tunnel")
foreach ($svc in $services) {
    Write-Host "`n[$svc]" -ForegroundColor Cyan
    sc.exe qc $svc | Select-String "DEPENDENCIES"
}
```

### Check Service Status

```powershell
# Check all services
$services = @("VOFC-Ollama", "VOFC-Flask", "VOFC-Processor", "VOFC-ModelManager", "VOFC-AutoRetrain", "VOFC-Tunnel")
foreach ($svc in $services) {
    $status = nssm status $svc 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "$svc : $status" -ForegroundColor $(if ($status -eq "SERVICE_RUNNING") { "Green" } else { "Yellow" })
    }
}
```

## Automatic Startup on Boot

When services are set to `SERVICE_AUTO_START`, Windows will:

1. Start services in dependency order automatically
2. Wait for dependencies to be ready
3. Start dependent services

**Verify auto-start is enabled:**
```powershell
nssm get VOFC-Processor Start
# Should return: SERVICE_AUTO_START
```

**Enable auto-start:**
```powershell
nssm set VOFC-Processor Start SERVICE_AUTO_START
```

## Troubleshooting

### Service Won't Start

1. **Check dependencies are running:**
   ```powershell
   nssm status VOFC-Ollama
   ```

2. **Check dependency configuration:**
   ```powershell
   sc.exe qc VOFC-Processor | Select-String "DEPENDENCIES"
   ```

3. **Check service logs:**
   ```powershell
   Get-Content "C:\Tools\Ollama\Data\logs\<service>_*.log" -Tail 20
   ```

### Service Starts Too Early

If a service starts before its dependency is ready:

1. **Increase startup delay** in `start-services-ordered.ps1`
2. **Add health check** in service startup code
3. **Use retry logic** in service initialization

### Dependency Not Working

If Windows isn't respecting dependencies:

1. **Verify dependency is set:**
   ```powershell
   sc.exe qc <ServiceName> | Select-String "DEPENDENCIES"
   ```

2. **Reconfigure dependencies:**
   ```powershell
   .\scripts\configure-service-dependencies.ps1
   ```

3. **Check service status:**
   ```powershell
   sc.exe query <DependencyName>
   ```

## Best Practices

1. **Always configure dependencies** - Use `configure-service-dependencies.ps1` after installing services
2. **Test startup order** - Use `start-services-ordered.ps1` to verify
3. **Monitor logs** - Check service logs after startup
4. **Set auto-start** - Ensure services start automatically on boot
5. **Use health checks** - Services should verify dependencies are ready before starting

## Scripts Reference

- `scripts/configure-service-dependencies.ps1` - Configure Windows service dependencies
- `scripts/start-services-ordered.ps1` - Start services in order (manual)
- `scripts/stop-services-ordered.ps1` - Stop services in reverse order
- `scripts/migrate-all-services-to-tools.ps1` - Migrates services and configures dependencies

## Example: Full Startup Sequence

```powershell
# 1. Configure dependencies (one-time setup)
.\scripts\configure-service-dependencies.ps1

# 2. Start services in order
.\scripts\start-services-ordered.ps1

# 3. Verify all services are running
$services = @("VOFC-Ollama", "VOFC-Flask", "VOFC-Processor", "VOFC-ModelManager", "VOFC-AutoRetrain", "VOFC-Tunnel")
foreach ($svc in $services) {
    $status = nssm status $svc 2>&1
    Write-Host "$svc : $status"
}
```

Expected output:
```
VOFC-Ollama : SERVICE_RUNNING
VOFC-Flask : SERVICE_RUNNING
VOFC-Processor : SERVICE_RUNNING
VOFC-ModelManager : SERVICE_RUNNING
VOFC-AutoRetrain : SERVICE_RUNNING
VOFC-Tunnel : SERVICE_RUNNING
```

