# NSSM Function Patterns

## Overview
This document captures the standard patterns for using NSSM (Non-Sucking Service Manager) commands in the VOFC system.

## Key Principles

### 1. Service Name Resolution
**Always use `find_service_name()` first** to resolve canonical names to actual Windows service names:
- Canonical names: `'VOFC-Ollama'`, `'vofc-flask'`, `'VOFC-Processor'`, etc.
- Actual names may vary: `'VOFC-Ollama'`, `'vofc-ollama'`, `'Ollama'`, etc.
- Use `SERVICE_NAME_VARIANTS` dictionary for compatibility

### 2. Standard NSSM Commands

#### Start Service
```python
subprocess.run(
    ['nssm', 'start', service_name],
    capture_output=True,
    text=True,
    timeout=15  # 15 second timeout
)
```
- **Wait time**: 3 seconds after start (allow service to fully initialize)
- **Error handling**: Check `result.returncode == 0`
- **Logging**: Log both canonical and actual service names

#### Stop Service
```python
subprocess.run(
    ['nssm', 'stop', service_name],
    capture_output=True,
    text=True,
    timeout=15  # 15 second timeout
)
```
- **Wait time**: 2 seconds after stop (allow service to fully stop)
- **Error handling**: Check `result.returncode == 0`
- **Logging**: Log both canonical and actual service names

#### Restart Service
```python
subprocess.run(
    ['nssm', 'restart', service_name],
    capture_output=True,
    text=True,
    timeout=15  # 15 second timeout
)
```
- **Note**: NSSM restart is atomic (stop + start in one command)
- **Error handling**: Check `result.returncode == 0`

#### Check Service Status
```python
subprocess.run(
    ['sc', 'query', service_name],  # Use 'sc', not 'nssm status'
    capture_output=True,
    text=True,
    timeout=3  # Faster timeout for status checks
)
```
- **State codes**: 1=STOPPED, 2=START_PENDING, 3=STOP_PENDING, 4=RUNNING
- **Detection**: Use regex `r'STATE\s*:\s*4'` for RUNNING state
- **Fallback**: Check for 'RUNNING' text if state code parsing fails

### 3. Service Status Detection Pattern

```python
def check_service_status(service_name: str) -> str:
    """Returns 'ok', 'offline', or 'unknown'"""
    result = subprocess.run(
        ['sc', 'query', service_name],
        capture_output=True,
        text=True,
        timeout=3
    )
    
    if result.returncode == 0:
        output_upper = result.stdout.upper()
        # Primary: Check for state code 4 (RUNNING)
        state_match_1 = re.search(r'STATE\s*:\s*4', output_upper)
        state_match_2 = re.search(r':\s*4\s+RUNNING', output_upper)
        has_state_4 = (state_match_1 is not None) or (state_match_2 is not None)
        
        # Fallback: Text matching
        has_running = 'RUNNING' in output_upper
        has_stopped = 'STOPPED' in output_upper
        
        if has_state_4 or (has_running and not has_stopped):
            return 'ok'
        elif has_stopped:
            return 'offline'
    
    return 'unknown'
```

### 4. Service Dependency Management

#### Dependency Map
```python
SERVICE_DEPENDENCIES = {
    'VOFC-Ollama': ['vofc-flask', 'VOFC-Processor', 'VOFC-ModelManager'],
    'vofc-flask': ['VOFC-Tunnel'],
    'VOFC-Processor': [],
    'VOFC-ModelManager': [],
    'VOFC-Tunnel': [],
}
```

#### Startup Order
```python
STARTUP_ORDER = [
    'VOFC-Ollama',      # Base service - no dependencies
    'VOFC-Processor',   # Depends on Ollama
    'VOFC-ModelManager', # Depends on Ollama
    'vofc-flask',       # Depends on Ollama
    'VOFC-Tunnel',      # Depends on Flask
]
```

#### Shutdown Order
```python
SHUTDOWN_ORDER = list(reversed(STARTUP_ORDER))
```

### 5. Cascading Restart Pattern

When restarting a service with dependencies:
1. **Stop dependents first** (in shutdown order)
2. **Stop the target service**
3. **Wait 2 seconds** between stops
4. **Start the target service**
5. **Start dependents** (in startup order)
6. **Wait 3 seconds** between starts

```python
def restart_with_dependencies(service_name: str):
    dependents = SERVICE_DEPENDENCIES.get(service_name, [])
    
    # Stop in shutdown order
    for dep in reversed(dependents):
        stop_service(dep)
        time.sleep(1)  # Brief pause between stops
    
    # Stop target
    stop_service(service_name)
    time.sleep(2)  # Allow full stop
    
    # Start target
    start_service(service_name)
    time.sleep(3)  # Allow full start
    
    # Start dependents in startup order
    for dep in dependents:
        start_service(dep)
        time.sleep(3)  # Allow full start
```

### 6. Error Handling Patterns

#### Timeout Handling
```python
try:
    result = subprocess.run(..., timeout=15)
except subprocess.TimeoutExpired:
    logger.warning(f"Timeout {operation} service {service_name}")
    return False, f"Timeout {operation} {service_name}"
```

#### Service Not Found
```python
actual_name = find_service_name(canonical_name)
if not actual_name:
    variants = SERVICE_NAME_VARIANTS.get(canonical_name, [canonical_name])
    return False, f"Service {canonical_name} not found (tried: {', '.join(variants)})"
```

#### Command Failure
```python
if result.returncode == 0:
    return True, f"Service {actual_name} {operation}ed"
else:
    error_msg = result.stderr or result.stdout or "Unknown error"
    logger.error(f"Failed to {operation} {actual_name}: {error_msg}")
    return False, f"Failed to {operation} {actual_name}: {error_msg}"
```

### 7. Service Name Variants

Always check multiple name variants for compatibility:
```python
SERVICE_NAME_VARIANTS = {
    'VOFC-Ollama': ['VOFC-Ollama', 'vofc-ollama', 'Ollama', 'ollama'],
    'vofc-flask': ['vofc-flask', 'VOFC-Flask', 'PSA-Flask'],
    'VOFC-Processor': ['VOFC-Processor', 'vofc-processor', 'PSA-Processor'],
    'VOFC-ModelManager': ['VOFC-ModelManager', 'vofc-modelmanager', 'VOFC-Model-Manager', 'PSA-ModelManager', 'ModelManager'],
    'VOFC-Tunnel': ['VOFC-Tunnel', 'vofc-tunnel', 'VOFC-Tunnel-Service', 'PSA-Tunnel', 'Cloudflare-Tunnel'],
}
```

### 8. Best Practices

1. **Always use `find_service_name()`** before NSSM operations
2. **Log both canonical and actual names** for debugging
3. **Use appropriate timeouts**: 15s for start/stop, 3s for status
4. **Add delays between operations**: 2s after stop, 3s after start
5. **Handle timeouts gracefully** with clear error messages
6. **Check service status** before operations when possible
7. **Use `sc query` for status**, not `nssm status`
8. **Respect dependency order** for cascading operations

### 9. Common Issues

#### Issue: Service not found
- **Solution**: Check `SERVICE_NAME_VARIANTS` and use `find_service_name()`
- **Debug**: Try all variants manually with `sc query <name>`

#### Issue: Timeout errors
- **Solution**: Increase timeout to 15 seconds for start/stop operations
- **Note**: Some services take longer to start (especially on first run)

#### Issue: Service appears running but isn't
- **Solution**: Use state code 4 detection, not just text matching
- **Debug**: Check `sc query` output for actual state code

#### Issue: Dependencies not restarting
- **Solution**: Use `restart_with_dependencies()` from `service_manager.py`
- **Debug**: Check `SERVICE_DEPENDENCIES` map is correct

## Reference Files

- **Python**: `routes/service_manager.py` - Main service management functions
- **Python**: `routes/system.py` - Service status checks and control endpoints
- **PowerShell**: `scripts/restart-services-with-deps.ps1` - PowerShell equivalent

## Quick Reference

```python
# Import
from routes.service_manager import (
    find_service_name,
    get_service_status,
    stop_service,
    start_service,
    restart_service,
    restart_with_dependencies
)

# Find actual service name
actual_name = find_service_name('VOFC-Ollama')

# Check status
actual_name, status = get_service_status('VOFC-Ollama')  # Returns: ('VOFC-Ollama', 'running')

# Control services
success, message = stop_service('VOFC-Ollama')
success, message = start_service('VOFC-Ollama')
success, message = restart_service('VOFC-Ollama')

# Restart with dependencies
success, message = restart_with_dependencies('VOFC-Ollama')
```

