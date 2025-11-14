"""
Dependency Verification Utility

Verifies all dependencies before operations, following the Zero-Error Architecture principle:
"No critical operation runs without verifying its dependencies."
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
import subprocess
import requests

from config.exceptions import DependencyError
from config import Config

logger = logging.getLogger(__name__)


def verify_dependencies(
    operation_name: str,
    deps: Dict[str, Union[str, Path, List[Union[str, Path]]]]
) -> None:
    """
    Verify all dependencies exist before operation.
    
    Args:
        operation_name: Name of the operation (for error messages)
        deps: Dictionary mapping dependency types to values:
            - 'file': Path to file that must exist
            - 'directory': Path to directory that must exist (will be created if missing)
            - 'service': Service name that must be running
            - 'env_var': Environment variable name that must be set
            - 'network': URL that must be reachable
    
    Raises:
        DependencyError: If any dependency is missing or unavailable
    
    Example:
        verify_dependencies('process_pdf', {
            'file': Path('/path/to/file.pdf'),
            'directory': Config.INCOMING_DIR,
            'service': 'VOFC-Processor',
            'network': 'http://localhost:11434'
        })
    """
    missing = []
    errors = []
    
    for dep_type, dep_value in deps.items():
        if dep_type == 'file':
            # Single file or list of files
            files = dep_value if isinstance(dep_value, list) else [dep_value]
            for file_path in files:
                file_path = Path(file_path)
                if not file_path.exists():
                    missing.append(f"File not found: {file_path}")
                elif not file_path.is_file():
                    missing.append(f"Path exists but is not a file: {file_path}")
                elif not os.access(file_path, os.R_OK):
                    missing.append(f"File exists but is not readable: {file_path}")
        
        elif dep_type == 'directory':
            # Single directory or list of directories
            dirs = dep_value if isinstance(dep_value, list) else [dep_value]
            for dir_path in dirs:
                dir_path = Path(dir_path)
                if not dir_path.exists():
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                        logger.info(f"Created directory: {dir_path}")
                    except Exception as e:
                        missing.append(f"Directory does not exist and cannot be created: {dir_path} ({e})")
                elif not dir_path.is_dir():
                    missing.append(f"Path exists but is not a directory: {dir_path}")
                elif not os.access(dir_path, os.W_OK):
                    missing.append(f"Directory exists but is not writable: {dir_path}")
        
        elif dep_type == 'service':
            # Single service name or list of service names
            services = dep_value if isinstance(dep_value, list) else [dep_value]
            for service_name in services:
                if not _check_service_running(service_name):
                    missing.append(f"Service not running: {service_name}")
        
        elif dep_type == 'env_var':
            # Single env var name or list of env var names
            env_vars = dep_value if isinstance(dep_value, list) else [dep_value]
            for env_var in env_vars:
                if not os.getenv(env_var):
                    missing.append(f"Environment variable not set: {env_var}")
        
        elif dep_type == 'network':
            # Single URL or list of URLs
            urls = dep_value if isinstance(dep_value, list) else [dep_value]
            for url in urls:
                if not _check_network_reachable(url):
                    missing.append(f"Network endpoint not reachable: {url}")
        
        else:
            errors.append(f"Unknown dependency type: {dep_type}")
    
    if errors:
        raise DependencyError(
            f"Invalid dependency specification for operation '{operation_name}':\n" +
            "\n".join(f"  - {e}" for e in errors)
        )
    
    if missing:
        raise DependencyError(
            f"Operation '{operation_name}' cannot proceed. Missing dependencies:\n" +
            "\n".join(f"  - {m}" for m in missing)
        )


def _check_service_running(service_name: str) -> bool:
    """
    Check if a Windows service is running.
    
    Args:
        service_name: Name of the service to check
    
    Returns:
        True if service is running, False otherwise
    """
    try:
        # Use sc query to check service status
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
        return "RUNNING" in output or "STATE" in output and "4" in output
        
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.warning(f"Could not check service status for {service_name}: {e}")
        return False


def _check_network_reachable(url: str, timeout: int = 5) -> bool:
    """
    Check if a network endpoint is reachable.
    
    Args:
        url: URL to check
        timeout: Timeout in seconds
    
    Returns:
        True if endpoint is reachable, False otherwise
    """
    try:
        # Try a HEAD request first (lighter than GET)
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code < 500  # Accept 2xx, 3xx, 4xx (but not 5xx)
    except requests.exceptions.RequestException:
        # If HEAD fails, try GET (some servers don't support HEAD)
        try:
            response = requests.get(url, timeout=timeout, allow_redirects=True)
            return response.status_code < 500
        except requests.exceptions.RequestException:
            return False

