"""
Service Health Check Utilities

Provides functions to check the health of external services (Ollama, Supabase, etc.)
following the Zero-Error Architecture principle of dependency verification.
"""

import logging
import requests
from typing import Optional, Dict, Any

from config.exceptions import ServiceError
from config import Config

logger = logging.getLogger(__name__)


def check_service_health(service_name: str) -> bool:
    """
    Check if a Windows service is running.
    
    Args:
        service_name: Name of the service to check
    
    Returns:
        True if service is running, False otherwise
    
    Raises:
        ServiceError: If service check fails unexpectedly
    """
    import subprocess
    
    try:
        result = subprocess.run(
            ['sc', 'query', service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False
        
        # Check if service state contains "RUNNING"
        output = result.stdout.upper()
        return "RUNNING" in output or ("STATE" in output and "4" in output)
        
    except subprocess.TimeoutExpired:
        raise ServiceError(f"Service check timeout for {service_name}")
    except FileNotFoundError:
        raise ServiceError("'sc' command not found - cannot check service status")
    except Exception as e:
        raise ServiceError(f"Unexpected error checking service {service_name}: {e}")


def check_ollama_health(
    ollama_url: Optional[str] = None,
    timeout: int = 5
) -> Dict[str, Any]:
    """
    Check if Ollama service is healthy and reachable.
    
    Args:
        ollama_url: Ollama base URL (defaults to Config.OLLAMA_URL)
        timeout: Request timeout in seconds
    
    Returns:
        Dictionary with health status:
        {
            'healthy': bool,
            'reachable': bool,
            'models_available': bool,
            'model_count': int,
            'error': Optional[str]
        }
    
    Raises:
        ServiceError: If Ollama is required but unreachable
    """
    if ollama_url is None:
        ollama_url = Config.OLLAMA_URL
    
    # Normalize URL
    if not ollama_url.startswith(('http://', 'https://')):
        ollama_url = f"http://{ollama_url}"
    ollama_url = ollama_url.rstrip('/')
    
    result = {
        'healthy': False,
        'reachable': False,
        'models_available': False,
        'model_count': 0,
        'error': None
    }
    
    try:
        # Check if Ollama API is reachable
        tags_url = f"{ollama_url}/api/tags"
        response = requests.get(tags_url, timeout=timeout)
        
        if response.status_code == 200:
            result['reachable'] = True
            
            # Check if models are available
            data = response.json()
            models = data.get('models', [])
            result['model_count'] = len(models)
            result['models_available'] = len(models) > 0
            result['healthy'] = result['models_available']
            
            if not result['models_available']:
                result['error'] = "Ollama is reachable but no models are available"
        else:
            result['error'] = f"Ollama API returned status {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        result['error'] = f"Cannot connect to Ollama at {ollama_url}"
    except requests.exceptions.Timeout:
        result['error'] = f"Ollama request timeout after {timeout} seconds"
    except requests.exceptions.RequestException as e:
        result['error'] = f"Ollama request failed: {e}"
    except Exception as e:
        result['error'] = f"Unexpected error checking Ollama: {e}"
    
    return result


def check_supabase_health(
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    timeout: int = 5
) -> Dict[str, Any]:
    """
    Check if Supabase service is healthy and reachable.
    
    Args:
        supabase_url: Supabase URL (defaults to Config.SUPABASE_URL)
        supabase_key: Supabase key (defaults to Config.SUPABASE_ANON_KEY)
        timeout: Request timeout in seconds
    
    Returns:
        Dictionary with health status:
        {
            'healthy': bool,
            'reachable': bool,
            'authenticated': bool,
            'error': Optional[str]
        }
    
    Note: This does not raise ServiceError because Supabase may be optional.
    Use verify_dependencies() if Supabase is required.
    """
    if supabase_url is None:
        supabase_url = Config.SUPABASE_URL
    if supabase_key is None:
        supabase_key = Config.SUPABASE_ANON_KEY
    
    result = {
        'healthy': False,
        'reachable': False,
        'authenticated': False,
        'error': None
    }
    
    if not supabase_url or not supabase_key:
        result['error'] = "Supabase credentials not configured"
        return result
    
    try:
        # Try to reach Supabase REST API
        # Use a simple endpoint that doesn't require authentication
        health_url = f"{supabase_url.rstrip('/')}/rest/v1/"
        response = requests.get(health_url, timeout=timeout)
        
        if response.status_code in (200, 401, 403):  # 401/403 means service is up but auth failed
            result['reachable'] = True
            result['authenticated'] = response.status_code == 200
            result['healthy'] = result['authenticated']
            
            if not result['authenticated']:
                result['error'] = "Supabase is reachable but authentication failed"
        else:
            result['error'] = f"Supabase API returned status {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        result['error'] = f"Cannot connect to Supabase at {supabase_url}"
    except requests.exceptions.Timeout:
        result['error'] = f"Supabase request timeout after {timeout} seconds"
    except requests.exceptions.RequestException as e:
        result['error'] = f"Supabase request failed: {e}"
    except Exception as e:
        result['error'] = f"Unexpected error checking Supabase: {e}"
    
    return result

