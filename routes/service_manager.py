"""
Service dependency management and cascading restart logic.
Handles service startup order and dependencies.
"""

import os
import logging
import subprocess
import re
from typing import List, Dict, Tuple, Optional

# Service dependencies map
# Key: service name, Value: list of services that depend on it
SERVICE_DEPENDENCIES = {
    'VOFC-Ollama': ['vofc-flask', 'VOFC-Processor', 'VOFC-ModelManager'],
    'vofc-flask': ['VOFC-Tunnel'],
    'VOFC-Processor': [],  # No services depend on processor
    'VOFC-ModelManager': [],  # No services depend on model manager
    'VOFC-Tunnel': [],  # No services depend on tunnel
}

# Service startup order (dependencies first)
STARTUP_ORDER = [
    'VOFC-Ollama',      # Base service - no dependencies
    'VOFC-Processor',    # Depends on Ollama
    'VOFC-ModelManager', # Depends on Ollama
    'vofc-flask',       # Depends on Ollama
    'VOFC-Tunnel',      # Depends on Flask
]

# Service shutdown order (reverse of startup - dependents first)
SHUTDOWN_ORDER = list(reversed(STARTUP_ORDER))

# Service name variations (for compatibility)
SERVICE_NAME_VARIANTS = {
    'VOFC-Ollama': ['VOFC-Ollama', 'vofc-ollama', 'Ollama', 'ollama'],
    'vofc-flask': ['vofc-flask', 'VOFC-Flask', 'PSA-Flask'],
    'VOFC-Processor': ['VOFC-Processor', 'vofc-processor', 'PSA-Processor'],
    'VOFC-ModelManager': ['VOFC-ModelManager', 'vofc-modelmanager', 'VOFC-Model-Manager', 'PSA-ModelManager', 'ModelManager'],
    'VOFC-Tunnel': ['VOFC-Tunnel', 'vofc-tunnel', 'VOFC-Tunnel-Service', 'PSA-Tunnel', 'Cloudflare-Tunnel'],
}

logger = logging.getLogger(__name__)


def find_service_name(canonical_name: str) -> Optional[str]:
    """
    Find the actual Windows service name for a canonical service name.
    Returns the first matching service name found, or None if not found.
    """
    variants = SERVICE_NAME_VARIANTS.get(canonical_name, [canonical_name])
    
    for variant in variants:
        try:
            result = subprocess.run(
                ['sc', 'query', variant],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                logger.debug(f"Found service {canonical_name} as {variant}")
                return variant
        except Exception as e:
            logger.debug(f"Error checking service {variant}: {e}")
            continue
    
    logger.warning(f"Service {canonical_name} not found with any variant")
    return None


def get_service_status(service_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Get service status.
    Returns: (actual_service_name, status) where status is 'running', 'stopped', 'unknown', or None if not found
    """
    actual_name = find_service_name(service_name)
    if not actual_name:
        return None, None
    
    try:
        result = subprocess.run(
            ['sc', 'query', actual_name],
            capture_output=True,
            text=True,
            timeout=3
        )
        
        if result.returncode == 0:
            output = result.stdout.upper()
            # Check for state code 4 (RUNNING)
            state_match = re.search(r'STATE\s*:\s*4', output)
            if state_match or ('RUNNING' in output and 'STOPPED' not in output):
                return actual_name, 'running'
            elif 'STOPPED' in output:
                return actual_name, 'stopped'
            else:
                return actual_name, 'unknown'
        else:
            return actual_name, None
    except Exception as e:
        logger.error(f"Error checking service {service_name}: {e}")
        return actual_name, None


def stop_service(service_name: str) -> Tuple[bool, str]:
    """
    Stop a Windows service using NSSM.
    Returns: (success, message)
    """
    actual_name = find_service_name(service_name)
    if not actual_name:
        return False, f"Service {service_name} not found"
    
    try:
        result = subprocess.run(
            ['nssm', 'stop', actual_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"Service {actual_name} stopped successfully")
            return True, f"Service {actual_name} stopped"
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"Failed to stop {actual_name}: {error_msg}")
            return False, f"Failed to stop {actual_name}: {error_msg}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout stopping {actual_name}"
    except Exception as e:
        logger.error(f"Error stopping {actual_name}: {e}")
        return False, f"Error stopping {actual_name}: {str(e)}"


def start_service(service_name: str) -> Tuple[bool, str]:
    """
    Start a Windows service using NSSM.
    Returns: (success, message)
    """
    actual_name = find_service_name(service_name)
    if not actual_name:
        return False, f"Service {service_name} not found"
    
    try:
        result = subprocess.run(
            ['nssm', 'start', actual_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"Service {actual_name} started successfully")
            return True, f"Service {actual_name} started"
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"Failed to start {actual_name}: {error_msg}")
            return False, f"Failed to start {actual_name}: {error_msg}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout starting {actual_name}"
    except Exception as e:
        logger.error(f"Error starting {actual_name}: {e}")
        return False, f"Error starting {actual_name}: {str(e)}"


def restart_service(service_name: str) -> Tuple[bool, str]:
    """
    Restart a Windows service using NSSM.
    Returns: (success, message)
    """
    actual_name = find_service_name(service_name)
    if not actual_name:
        return False, f"Service {service_name} not found"
    
    try:
        result = subprocess.run(
            ['nssm', 'restart', actual_name],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode == 0:
            logger.info(f"Service {actual_name} restarted successfully")
            return True, f"Service {actual_name} restarted"
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"Failed to restart {actual_name}: {error_msg}")
            return False, f"Failed to restart {actual_name}: {error_msg}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout restarting {actual_name}"
    except Exception as e:
        logger.error(f"Error restarting {actual_name}: {e}")
        return False, f"Error restarting {actual_name}: {str(e)}"


def get_dependent_services(service_name: str) -> List[str]:
    """
    Get list of services that depend on the given service.
    """
    return SERVICE_DEPENDENCIES.get(service_name, [])


def restart_with_dependencies(service_name: str) -> Dict[str, any]:
    """
    Restart a service and all services that depend on it, in the correct order.
    
    Process:
    1. Stop dependent services first (reverse dependency order)
    2. Stop the target service
    3. Start the target service
    4. Start dependent services (dependency order)
    
    Returns: {
        'success': bool,
        'message': str,
        'steps': List[Dict[str, str]],  # List of actions taken
        'errors': List[str]  # List of errors encountered
    }
    """
    logger.info(f"Restarting {service_name} with dependencies")
    
    result = {
        'success': True,
        'message': '',
        'steps': [],
        'errors': []
    }
    
    # Get dependent services
    dependents = get_dependent_services(service_name)
    
    if not dependents:
        # No dependencies - just restart the service
        success, msg = restart_service(service_name)
        result['steps'].append({
            'action': 'restart',
            'service': service_name,
            'status': 'success' if success else 'error',
            'message': msg
        })
        if not success:
            result['success'] = False
            result['errors'].append(msg)
        result['message'] = msg
        return result
    
    # Step 1: Stop dependent services (in shutdown order)
    services_to_stop = dependents + [service_name]
    # Sort by shutdown order (dependents first)
    services_to_stop_sorted = []
    for svc in SHUTDOWN_ORDER:
        if svc in services_to_stop:
            services_to_stop_sorted.append(svc)
    # Add any services not in SHUTDOWN_ORDER
    for svc in services_to_stop:
        if svc not in services_to_stop_sorted:
            services_to_stop_sorted.append(svc)
    
    logger.info(f"Stopping services in order: {services_to_stop_sorted}")
    for svc in services_to_stop_sorted:
        success, msg = stop_service(svc)
        result['steps'].append({
            'action': 'stop',
            'service': svc,
            'status': 'success' if success else 'error',
            'message': msg
        })
        if not success:
            result['success'] = False
            result['errors'].append(f"Failed to stop {svc}: {msg}")
    
    # Step 2: Start services in startup order
    services_to_start = [service_name] + dependents
    # Sort by startup order
    services_to_start_sorted = []
    for svc in STARTUP_ORDER:
        if svc in services_to_start:
            services_to_start_sorted.append(svc)
    # Add any services not in STARTUP_ORDER
    for svc in services_to_start:
        if svc not in services_to_start_sorted:
            services_to_start_sorted.append(svc)
    
    logger.info(f"Starting services in order: {services_to_start_sorted}")
    for svc in services_to_start_sorted:
        success, msg = start_service(svc)
        result['steps'].append({
            'action': 'start',
            'service': svc,
            'status': 'success' if success else 'error',
            'message': msg
        })
        if not success:
            result['success'] = False
            result['errors'].append(f"Failed to start {svc}: {msg}")
    
    # Build summary message
    if result['success']:
        result['message'] = f"Successfully restarted {service_name} and {len(dependents)} dependent service(s)"
    else:
        result['message'] = f"Restarted {service_name} with {len(result['errors'])} error(s). See steps for details."
    
    return result


def restart_all_services() -> Dict[str, any]:
    """
    Restart all services in the correct order.
    Stops all services, then starts them in dependency order.
    
    Returns: {
        'success': bool,
        'message': str,
        'steps': List[Dict[str, str]],
        'errors': List[str]
    }
    """
    logger.info("Restarting all services in dependency order")
    
    result = {
        'success': True,
        'message': '',
        'steps': [],
        'errors': []
    }
    
    # Step 1: Stop all services in shutdown order
    logger.info(f"Stopping all services in order: {SHUTDOWN_ORDER}")
    for svc in SHUTDOWN_ORDER:
        success, msg = stop_service(svc)
        result['steps'].append({
            'action': 'stop',
            'service': svc,
            'status': 'success' if success else 'error',
            'message': msg
        })
        if not success:
            # Don't fail completely - some services might not exist
            result['errors'].append(f"Failed to stop {svc}: {msg}")
    
    # Step 2: Start all services in startup order
    logger.info(f"Starting all services in order: {STARTUP_ORDER}")
    for svc in STARTUP_ORDER:
        success, msg = start_service(svc)
        result['steps'].append({
            'action': 'start',
            'service': svc,
            'status': 'success' if success else 'error',
            'message': msg
        })
        if not success:
            result['success'] = False
            result['errors'].append(f"Failed to start {svc}: {msg}")
    
    if result['success']:
        result['message'] = f"Successfully restarted all {len(STARTUP_ORDER)} services"
    else:
        result['message'] = f"Restarted services with {len(result['errors'])} error(s). See steps for details."
    
    return result

