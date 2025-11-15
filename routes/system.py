"""
System routes for health checks and version info
Routes: /, /api/system/health, /api/version, /api/progress
"""

from flask import Blueprint, jsonify, request
from services.ollama_client import test_ollama
from services.supabase_client import test_supabase, get_supabase_client
from config import Config
from config.exceptions import ServiceError, DependencyError
from config.service_health import check_ollama_health, check_supabase_health, check_service_health
from routes.service_manager import restart_service
import os
import json
import requests
import subprocess
import logging
import re
from datetime import datetime
from pathlib import Path

# EST/EDT timezone handling
try:
    from zoneinfo import ZoneInfo
    try:
        EST = ZoneInfo("America/New_York")
    except Exception:
        # If ZoneInfo fails, try pytz
        import pytz
        EST = pytz.timezone("America/New_York")
except ImportError:
    # Fallback for Python < 3.9
    try:
        import pytz
        EST = pytz.timezone("America/New_York")
    except ImportError:
        EST = None

def now_est():
    """Get current time in EST/EDT."""
    if EST:
        return datetime.now(EST)
    else:
        # Fallback to local time if timezone libraries not available
        return datetime.now()

system_bp = Blueprint('system', __name__)

# Supabase client - lazy loaded (only when needed)
# Don't initialize at module level to avoid startup errors if Supabase is not configured
def get_supabase():
    """Get Supabase client, handling configuration errors gracefully."""
    try:
        return get_supabase_client()
    except Exception as e:
        logging.debug(f"Supabase client not available: {e}")
        return None

def test_flask_service():
    """
    Check if Flask Windows service is running.
    Only checks 'vofc-flask' (lowercase) - the single Flask service.
    Returns 'ok' if running, 'offline' if stopped, 'failed' if check fails.
    Simple and reliable: just check for state code 4 in sc query output.
    """
    service_name = 'vofc-flask'
    
    try:
        result = subprocess.run(
            ['sc', 'query', service_name],
            capture_output=True,
            text=True,
            timeout=3
        )
        
        if result.returncode == 0:
            output = result.stdout
            # Simple check: State code 4 = RUNNING
            if re.search(r'STATE\s*:\s*4', output, re.IGNORECASE):
                logging.debug(f"Flask service {service_name} is RUNNING (state 4)")
                return 'ok'
            else:
                # Service exists but not running = failed (primary service must be running)
                logging.debug(f"Flask service {service_name} is not running")
                return 'failed'
        else:
            logging.debug(f"Flask service {service_name} not found (returncode: {result.returncode})")
            return 'failed'
    except subprocess.TimeoutExpired:
        logging.warning(f"Timeout checking Flask service {service_name}")
        return 'failed'
    except FileNotFoundError:
        raise ServiceError("'sc.exe' not found - cannot check Flask service status")
    except Exception as e:
        logging.error(f"Error checking Flask service {service_name}: {e}", exc_info=True)
        return 'failed'

def test_processor_service():
    """
    Check if VOFC-Processor Windows service is running (the watcher/processor).
    Returns 'ok' if running, 'offline' if stopped, 'failed' if check fails.
    Simple and reliable: just check for state code 4 in sc query output.
    """
    service_names = ['VOFC-Processor', 'vofc-processor', 'PSA-Processor']
    
    for service_name in service_names:
        try:
            result = subprocess.run(
                ['sc', 'query', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                output = result.stdout
                # Simple check: State code 4 = RUNNING
                if re.search(r'STATE\s*:\s*4', output, re.IGNORECASE):
                    logging.debug(f"Processor service {service_name} is RUNNING (state 4)")
                    return 'ok'
                else:
                    # Service exists but not running = failed (primary service must be running)
                    logging.debug(f"Processor service {service_name} is not running")
                    continue  # Try next service name
            else:
                # Service not found, try next name
                continue
        except subprocess.TimeoutExpired:
            logging.warning(f"Timeout checking processor service {service_name}")
            continue
        except FileNotFoundError:
            raise ServiceError("'sc.exe' not found - cannot check processor service status")
        except Exception as e:
            logging.warning(f"Error checking processor service {service_name}: {e}")
            continue
    
    # Service not found with any name or check failed
    return 'failed'

def test_tunnel_service():
    """
    Check if Tunnel Windows service is running.
    Returns 'ok' if running, 'offline' if stopped, 'unknown' if check fails.
    """
    # Try actual service names first, then alternatives for compatibility
    service_names = ['VOFC-Tunnel', 'vofc-tunnel', 'VOFC-Tunnel-Service', 'PSA-Tunnel', 'Cloudflare-Tunnel']
    
    for service_name in service_names:
        try:
            # Use sc query to check service status (works on Windows)
            result = subprocess.run(
                ['sc', 'query', service_name],
                capture_output=True,
                text=True,
                timeout=3
            )
            
            if result.returncode == 0:
                output = result.stdout
                output_upper = output.upper()
                
                # Parse STATE line: "STATE : 4 RUNNING" or "STATE : 1 STOPPED"
                if 'STATE' in output_upper:
                    # Find the STATE line
                    for line in output.split('\n'):
                        if 'STATE' in line.upper():
                            # Extract state code and status
                            parts = line.split()
                            # Look for state code (number after STATE :)
                            for i, part in enumerate(parts):
                                if part.upper() == 'STATE' and i + 2 < len(parts):
                                    state_code = parts[i + 2]
                                    state_text = ' '.join(parts[i + 3:]) if i + 3 < len(parts) else ''
                                    
                                    if state_code == '4' or 'RUNNING' in state_text.upper():
                                        return 'ok'
                                    else:
                                        # Service exists but not running = failed (primary service must be running)
                                        return 'failed'
                                    break
                
                # Fallback: check text in output
                if 'RUNNING' in output_upper:
                    return 'ok'
                else:
                    # Service exists but not running = failed
                    return 'failed'
            else:
                # Service not found, try next name
                continue
        except subprocess.TimeoutExpired:
            logging.warning(f"Timeout checking tunnel service {service_name}")
            continue
        except FileNotFoundError:
            raise ServiceError("'sc.exe' not found - cannot check tunnel service status. System may not be Windows or PATH is misconfigured.")
        except subprocess.SubprocessError as e:
            logging.warning(f"Subprocess error checking tunnel service {service_name}: {e}")
            continue
        except Exception as e:
            logging.error(f"Unexpected error checking tunnel service {service_name}: {e}", exc_info=True)
            continue
    
    # If all service names failed, check if tunnel is accessible via URL
    try:
        tunnel_url = Config.TUNNEL_URL
        response = requests.get(f"{tunnel_url}/api/system/health", timeout=3)
        if response.status_code == 200:
            return 'ok'
        else:
            return 'failed'
    except requests.exceptions.ConnectionError as e:
        logging.debug(f"Tunnel URL connection failed: {e}")
    except requests.exceptions.Timeout as e:
        logging.debug(f"Tunnel URL request timeout: {e}")
    except requests.exceptions.RequestException as e:
        logging.debug(f"Tunnel URL request failed: {e}")
    except Exception as e:
        logging.error(f"Unexpected error checking tunnel URL: {e}", exc_info=True)
    
    # Service might not exist or access denied
    return 'failed'

# Model Manager service removed - no longer used

@system_bp.route('/')
def index():
    """Root endpoint - service info"""
    return jsonify({
        "service": "PSA Processing Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/system/health",
            "files": "/api/files/list"
        }
    })

@system_bp.route('/api/system/health', methods=['GET', 'OPTIONS'])
def health():
    """
    Lightweight system health check endpoint - optimized for <200ms response time.
    Checks Flask, Ollama, and Supabase connectivity.
    Assumes Ollama and Tunnel are managed by NSSM services.
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    # Get Ollama URL from centralized config (already normalized)
    ollama_base = Config.OLLAMA_URL
    
    # Get Flask URL for reporting
    flask_url = Config.FLASK_URL_LOCAL
    
    # Initialize components status
    # Check Flask service status (similar to tunnel checks)
    flask_service_status = test_flask_service()
    watcher_status = test_processor_service()  # VOFC-Processor service (watcher)
    supabase_status = test_supabase()
    components = {
        "flask": flask_service_status if flask_service_status == "ok" else "failed",
        "ollama": "failed",  # Will be set below
        "supabase": supabase_status if supabase_status == "ok" else "failed",
        "tunnel": "failed",  # Will be set below
        "watcher": watcher_status if watcher_status == "ok" else "failed"
    }
    
    # SELF-HEALING: Log Supabase failures (can't auto-restart external service, but log clearly)
    if components["supabase"] == "failed":
        logging.error("Supabase is failed - cannot auto-restart (external service). Check configuration and connectivity.")
    
    # SELF-HEALING: Automatically restart failed primary services
    if components["flask"] == "failed":
        logging.warning("Flask service is failed - attempting automatic restart")
        try:
            success, msg = restart_service("vofc-flask")
            if success:
                logging.info(f"Flask service restarted successfully: {msg}")
                components["flask"] = "ok"  # Assume ok after restart
            else:
                logging.error(f"Failed to restart Flask service: {msg}")
        except Exception as e:
            logging.error(f"Error restarting Flask service: {e}", exc_info=True)
    
    if components["watcher"] == "failed":
        logging.warning("Watcher service is failed - attempting automatic restart")
        try:
            success, msg = restart_service("VOFC-Processor")
            if success:
                logging.info(f"Watcher service restarted successfully: {msg}")
                components["watcher"] = "ok"  # Assume ok after restart
            else:
                logging.error(f"Failed to restart Watcher service: {msg}")
        except Exception as e:
            logging.error(f"Error restarting Watcher service: {e}", exc_info=True)
    
    # Check Ollama - use service function
    ollama_status = test_ollama()
    components["ollama"] = ollama_status if ollama_status == "ok" else "failed"
    
    # SELF-HEALING: Restart Ollama if failed
    if components["ollama"] == "failed":
        logging.warning("Ollama service is failed - attempting automatic restart")
        try:
            success, msg = restart_service("VOFC-Ollama")
            if success:
                logging.info(f"Ollama service restarted successfully: {msg}")
                # Re-check after restart
                import time
                time.sleep(2)  # Give service time to start
                ollama_status = test_ollama()
                components["ollama"] = ollama_status if ollama_status == "ok" else "failed"
            else:
                logging.error(f"Failed to restart Ollama service: {msg}")
        except Exception as e:
            logging.error(f"Error restarting Ollama service: {e}", exc_info=True)
    
    # Get tunnel URL (managed by NSSM service - Cloudflare tunnel)
    tunnel_url = Config.TUNNEL_URL
    
    # Check tunnel service status
    tunnel_status = test_tunnel_service()
    components["tunnel"] = tunnel_status if tunnel_status == "ok" else "failed"
    
    # SELF-HEALING: Restart Tunnel if failed
    if components["tunnel"] == "failed":
        logging.warning("Tunnel service is failed - attempting automatic restart")
        try:
            success, msg = restart_service("VOFC-Tunnel")
            if success:
                logging.info(f"Tunnel service restarted successfully: {msg}")
                components["tunnel"] = "ok"  # Assume ok after restart
            else:
                logging.error(f"Failed to restart Tunnel service: {msg}")
        except Exception as e:
            logging.error(f"Error restarting Tunnel service: {e}", exc_info=True)
    
    # Also try to verify connectivity through the tunnel (secondary check)
    if tunnel_status == "ok":
        try:
            import requests
            # Try to reach Flask through the tunnel (quick check with short timeout)
            tunnel_health_url = f"{tunnel_url}/api/health"
            tunnel_response = requests.get(tunnel_health_url, timeout=2)
            if tunnel_response.status_code != 200:
                # Service is running but tunnel may have connectivity issues
                tunnel_status = "error"
                components["tunnel"] = "error"
        except requests.exceptions.ConnectionError:
            # Connectivity check failed but service is running - tunnel may have connectivity issues
            logging.debug("Tunnel service is running but connectivity check failed")
            components["tunnel"] = "error"
        except requests.exceptions.Timeout:
            logging.debug("Tunnel connectivity check timed out")
            components["tunnel"] = "error"
        except requests.exceptions.RequestException as e:
            logging.debug(f"Tunnel connectivity check failed: {e}")
            components["tunnel"] = "error"
        except Exception as e:
            logging.error(f"Unexpected error during tunnel connectivity check: {e}", exc_info=True)
            components["tunnel"] = "error"
    
    # Return lightweight response with service metadata
    return jsonify({
        "flask": components["flask"],
        "ollama": components["ollama"],
        "supabase": components["supabase"],
        "tunnel": components["tunnel"],  # Tunnel is externally managed by NSSM
        "watcher": components["watcher"],  # VOFC-Processor service (watcher/processor)
        "service": "PSA Processing Server",
        "urls": {
            "flask": flask_url,
            "ollama": ollama_base,
            "tunnel": tunnel_url  # Public tunnel URL
        },
        "timestamp": now_est().isoformat()
    }), 200

@system_bp.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Simple health check endpoint"""
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({
        "status": "ok",
        "message": "PSA Flask backend online",
        "service": "PSA Processing Server",
        "model": Config.DEFAULT_MODEL
    }), 200

@system_bp.route('/api/progress', methods=['GET', 'OPTIONS'])
def get_processing_progress():
    """Get current document processing progress"""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        from services.processor import get_progress
        progress = get_progress()
        if not isinstance(progress, dict):
            progress = {
                "status": "idle",
                "message": "No active processing",
                "current_file": None,
                "progress_percent": 0
            }
        if "progress_percent" not in progress:
            progress["progress_percent"] = 0
        progress["service"] = "PSA Processing Server"
        return jsonify(progress), 200
    except Exception as e:
        import logging
        logging.error(f"Error in get_processing_progress: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to get progress: {str(e)}",
            "current_file": None,
            "progress_percent": 0,
            "service": "PSA Processing Server"
        }), 500

@system_bp.route('/api/version')
def version():
    """Version endpoint"""
    return jsonify({
        "version": "1.0.0",
        "service": "PSA Processing Server"
    })

@system_bp.route('/api/system/progress')
def progress():
    """Get processing progress and watcher status."""
    # Use centralized configuration
    from config import Config
    from config.api_contracts import validate_progress_response
    from config.dependencies import verify_dependencies
    from config.exceptions import DependencyError, FileOperationError
    
    try:
        # Verify dependencies before proceeding
        verify_dependencies('get_progress', {
            'directory': Config.DATA_DIR,
            'directory': Config.INCOMING_DIR,
            'directory': Config.PROCESSED_DIR,
        })
    except DependencyError as e:
        logging.error(f"Dependency check failed for progress endpoint: {e}")
        return jsonify({
            "status": "error",
            "message": f"System configuration error: {e}",
            "timestamp": now_est().isoformat()
        }), 503
    
    try:
        base_dir = Config.DATA_DIR
        progress_file = Config.PROGRESS_FILE
        
        # Get progress data - always refresh folder counts dynamically
        progress_data = {}
        try:
            if progress_file.exists():
                # Use utf-8-sig to handle BOM if present
                with open(progress_file, "r", encoding="utf-8-sig") as f:
                    progress_data = json.load(f)
            else:
                # progress.json doesn't exist - that's OK, we'll create default structure
                progress_data = {
                    "status": "idle", 
                    "message": "Monitoring folders",
                }
                logging.debug(f"progress.json not found at {progress_file} - using defaults")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"Error reading progress.json: {e}")
            progress_data = {
                "status": "idle", 
                "message": "Monitoring folders",
            }
        
        # Use centralized configuration paths (already validated at startup)
        incoming_dir = Config.INCOMING_DIR
        processed_dir = Config.PROCESSED_DIR
        library_dir = Config.LIBRARY_DIR
        errors_dir = Config.ERRORS_DIR
        review_dir = Config.REVIEW_DIR
        temp_errors_dir = Config.TEMP_DIR / "errors"
        
        # Count files in each directory with better error handling
        try:
            if incoming_dir.exists():
                incoming_count = len(list(incoming_dir.glob("*.pdf")))
            else:
                incoming_count = 0
            progress_data["incoming"] = incoming_count
            progress_data["incoming_label"] = "Pending Processing (Learning Mode)"
            progress_data["incoming_description"] = "Files waiting for processing or reprocessing to improve extraction"
        except PermissionError as e:
            logging.error(f"Permission denied counting incoming files: {e}")
            raise FileOperationError(f"Cannot access incoming directory: {e}")
        except OSError as e:
            logging.error(f"OS error counting incoming files: {e}")
            raise FileOperationError(f"File system error accessing incoming directory: {e}")
        except Exception as e:
            logging.error(f"Unexpected error counting incoming files: {e}", exc_info=True)
            raise FileOperationError(f"Unexpected error counting incoming files: {e}")
            
        try:
            if processed_dir.exists():
                processed_count = len(list(processed_dir.glob("*.json")))
            else:
                processed_count = 0
            progress_data["processed"] = processed_count
            progress_data["processed_label"] = "Processed JSON"
            progress_data["processed_description"] = "Extraction results (JSON files)"
        except PermissionError as e:
            logging.error(f"Permission denied counting processed files: {e}")
            raise FileOperationError(f"Cannot access processed directory: {e}")
        except OSError as e:
            logging.error(f"OS error counting processed files: {e}")
            raise FileOperationError(f"File system error accessing processed directory: {e}")
        except Exception as e:
            logging.error(f"Unexpected error counting processed files: {e}", exc_info=True)
            raise FileOperationError(f"Unexpected error counting processed files: {e}")
            
        try:
            if library_dir.exists():
                library_count = len(list(library_dir.glob("*.pdf")))
            else:
                library_count = 0
            progress_data["library"] = library_count
            progress_data["library_label"] = "Archived (Complete)"
            progress_data["library_description"] = "Files successfully processed with sufficient records"
        except PermissionError as e:
            logging.error(f"Permission denied counting library files: {e}")
            raise FileOperationError(f"Cannot access library directory: {e}")
        except OSError as e:
            logging.error(f"OS error counting library files: {e}")
            raise FileOperationError(f"File system error accessing library directory: {e}")
        except Exception as e:
            logging.error(f"Unexpected error counting library files: {e}", exc_info=True)
            raise FileOperationError(f"Unexpected error counting library files: {e}")
            
        try:
            # Count errors from both errors directory and temp/errors
            errors_count = 0
            if errors_dir.exists():
                errors_count += len(list(errors_dir.glob("*.*")))
            if temp_errors_dir.exists():
                errors_count += len(list(temp_errors_dir.glob("*.pdf")))
            progress_data["errors"] = errors_count
            progress_data["errors_label"] = "Processing Errors"
            progress_data["errors_description"] = "Files that failed processing (moved to errors)"
        except PermissionError as e:
            logging.error(f"Permission denied counting error files: {e}")
            raise FileOperationError(f"Cannot access errors directory: {e}")
        except OSError as e:
            logging.error(f"OS error counting error files: {e}")
            raise FileOperationError(f"File system error accessing errors directory: {e}")
        except Exception as e:
            logging.error(f"Unexpected error counting error files: {e}", exc_info=True)
            raise FileOperationError(f"Unexpected error counting error files: {e}")
            
        try:
            if review_dir.exists():
                review_count = len(list(review_dir.glob("*.json")))
            else:
                review_count = 0
            progress_data["review"] = review_count
            progress_data["review_label"] = "Review Queue"
            progress_data["review_description"] = "Extraction results pending review"
        except PermissionError as e:
            logging.error(f"Permission denied counting review files: {e}")
            raise FileOperationError(f"Cannot access review directory: {e}")
        except OSError as e:
            logging.error(f"OS error counting review files: {e}")
            raise FileOperationError(f"File system error accessing review directory: {e}")
        except Exception as e:
            logging.error(f"Unexpected error counting review files: {e}", exc_info=True)
            raise FileOperationError(f"Unexpected error counting review files: {e}")
        
        # Update status if not set
        if "status" not in progress_data:
            progress_data["status"] = "idle"
        
        # Update message if it's the "not found" message
        if progress_data.get("message") == "progress.json not found":
            progress_data["message"] = "Monitoring folders"
        
        # Always update timestamp to current time
        progress_data["timestamp"] = now_est().isoformat()
        
        # Get watcher status by checking Processor service
        # SIMPLIFIED: If service is running, watcher is running (it's a continuous process)
        # Try actual service names first, then alternatives for compatibility
        service_names = ['VOFC-Processor', 'vofc-processor', 'PSA-Processor']
        service_running = False
        result = None
        
        for service_name in service_names:
            try:
                import subprocess
                result = subprocess.run(
                    ['sc', 'query', service_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # Check for RUNNING state
                # Windows service states: 1=STOPPED, 2=START_PENDING, 3=STOP_PENDING, 4=RUNNING
                if result.returncode == 0:
                    output_upper = result.stdout.upper()
                    # Check for state code 4 (RUNNING) - more reliable than text matching
                    # Format: "STATE              : 4  RUNNING" or "STATE : 4  RUNNING"
                    # Try multiple regex patterns to handle different whitespace
                    state_match_1 = re.search(r'STATE\s*:\s*4', output_upper)
                    state_match_2 = re.search(r':\s*4\s+RUNNING', output_upper)
                    has_state_4 = (state_match_1 is not None) or (state_match_2 is not None)
                    has_running = 'RUNNING' in output_upper
                    has_stopped = 'STOPPED' in output_upper
                    
                    logging.debug(f"Service {service_name} check: State 4={has_state_4}, RUNNING={has_running}, STOPPED={has_stopped}")
                    
                    # Primary check: State code 4 (RUNNING) - most reliable
                    if has_state_4:
                        service_running = True
                        logging.info(f"Service {service_name} is RUNNING (state code 4 detected)")
                        break  # Found running service, exit loop
                    # Fallback check: RUNNING keyword present and STOPPED not present
                    elif has_running and not has_stopped:
                        service_running = True
                        logging.info(f"Service {service_name} is RUNNING (text match: RUNNING found, STOPPED not found)")
                        break  # Found running service, exit loop
                    else:
                        # Log for debugging
                        logging.warning(f"Service check failed for {service_name}: RUNNING={has_running}, STOPPED={has_stopped}, State 4={has_state_4}")
                        logging.debug(f"Service output (first 200 chars): {result.stdout[:200]}")
                        # Service exists but state check didn't match - continue to next service name
                        # Don't break here - let the loop continue to try other service names
                        continue
                else:
                    logging.warning(f"Service query returned non-zero exit code: {result.returncode}, stderr: {result.stderr}")
                    continue  # Try next service name
            except subprocess.TimeoutExpired:
                logging.warning(f"Timeout checking {service_name} service status")
                continue  # Try next service name
            except FileNotFoundError:
                # sc.exe not found (not Windows or PATH issue)
                logging.warning("sc.exe not found - cannot check service status")
                progress_data["watcher_status"] = "unknown"
                break
            except Exception as e:
                logging.debug(f"Error checking {service_name}: {e}")
                continue  # Try next service name
        
        # Process result - set watcher status based on service status
        if service_running:
            progress_data["watcher_status"] = "running"
            logging.debug("Watcher status set to: running")
        elif result is not None:
            # Service is not running - check if it exists at all
            if result.returncode != 0 or 'does not exist' in result.stdout.lower() or 'does not exist' in result.stderr.lower():
                # Service doesn't exist or can't be queried
                progress_data["watcher_status"] = "unknown"
                logging.debug("Watcher status set to: unknown (service not found)")
            else:
                # Service exists but is stopped
                progress_data["watcher_status"] = "stopped"
                logging.debug("Watcher status set to: stopped (service exists but not running)")
        else:
            # No service found at all
            progress_data["watcher_status"] = "unknown"
            logging.debug("Watcher status set to: unknown (no service found)")
        
        # Ensure timestamp exists
        if "timestamp" not in progress_data:
            progress_data["timestamp"] = now_est().isoformat()
        
        # Validate response against contract
        validate_progress_response(progress_data)
        
        return jsonify(progress_data), 200
    
    except DependencyError as e:
        # Already handled above, but keep for safety
        logging.error(f"Dependency check failed for progress endpoint: {e}")
        return jsonify({
            "status": "error",
            "message": f"System configuration error: {e}",
            "timestamp": now_est().isoformat()
        }), 503
    except FileOperationError as e:
        logging.error(f"File operation error in progress endpoint: {e}")
        return jsonify({
            "status": "error",
            "message": f"File system error: {e}",
            "timestamp": now_est().isoformat()
        }), 503
    except Exception as e:
        logging.error(f"Unexpected error in progress endpoint: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Unexpected error: {e}",
            "timestamp": now_est().isoformat(),
            "incoming": 0,
            "processed_label": "Processed JSON",
            "processed_description": "Extraction results (JSON files)",
            "library": 0,
            "library_label": "Archived (Complete)",
            "library_description": "Files successfully processed with sufficient records",
            "errors": 0,
            "errors_label": "Processing Errors",
            "errors_description": "Files that failed processing (moved to errors)",
            "review": 0,
            "review_label": "Review Queue",
            "review_description": "Extraction results pending review",
            "watcher_status": "unknown"
        }), 200

@system_bp.route('/api/system/logstream', methods=['GET', 'OPTIONS'])
def log_stream():
    """Server-Sent Events streaming of live VOFC Processor log - NEW VERSION with strict filtering."""
    from flask import Response
    import time
    
    if request.method == 'OPTIONS':
        response = Response('', status=200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Cache-Control'
        return response
    
    def stream():
        import os
        from pathlib import Path
        from datetime import datetime, timedelta
        
        # Use VOFC Processor log file
        base_dir = Config.DATA_DIR
        if not base_dir.exists():
            # Fallback to archive location if needed (for migration)
            archive_data = Config.ARCHIVE_DIR
            if archive_data.exists():
                base_dir = archive_data
            else:
                base_dir = Config.DATA_DIR  # Default
        
        logs_dir = base_dir / "logs"
        # Use single rolling log file (not date-specific)
        log_file = logs_dir / "vofc_processor.log"
        
        # Show all logs from today (not just last 1 hour) - user wants to see today's activity
        # Track session start time for initial connection
        session_start_time = now_est()
        today_start = session_start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check if log file exists
        if not log_file.exists():
            # If today's log doesn't exist, return empty stream
            def empty_stream():
                yield f"data: [INFO] Today's log file not found: {log_file}. The watcher may not have started yet.\n\n"
                import time
                while True:
                    time.sleep(5)
                    # Check again if file was created
                    if log_file.exists():
                        break
            response = Response(empty_stream(), mimetype="text/event-stream")
            response.headers["Cache-Control"] = "no-cache"
            # Note: "Connection" header is not allowed in WSGI (PEP 3333) - removed
            response.headers["X-Accel-Buffering"] = "no"
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
        
        def parse_log_timestamp(line):
            """Parse timestamp from log line. Returns None if parsing fails."""
            try:
                # Log format: "2025-11-12 12:38:35 | INFO | ..." or "2025-11-12 12:38:35,253 | INFO | ..."
                if '|' in line:
                    timestamp_str = line.split('|')[0].strip()
                    # Try parsing with milliseconds first (Python default format)
                    try:
                        log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                    except ValueError:
                        # Try without milliseconds
                        try:
                            log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            return None
                    # Convert to EST if needed
                    if EST:
                        # Handle both zoneinfo and pytz
                        if log_time.tzinfo is None:
                            # Naive datetime - need to localize
                            if hasattr(EST, 'localize'):
                                # pytz
                                log_time = EST.localize(log_time)
                            else:
                                # zoneinfo - replace tzinfo directly
                                log_time = log_time.replace(tzinfo=EST)
                        else:
                            # Already timezone-aware - convert to EST
                            log_time = log_time.astimezone(EST)
                    return log_time
            except (ValueError, IndexError):
                pass
            return None
        
        def is_today_log(line):
            """Check if log line is from today."""
            if not line or not line.strip():
                return False
            
            line_stripped = line.strip()
            
            # Try to parse timestamp first
            log_time = parse_log_timestamp(line_stripped)
            if log_time:
                # If we can parse timestamp, check if it's from today
                return log_time >= today_start
            
            # If no timestamp, check if it starts with today's date
            today_date_str = now_est().strftime("%Y-%m-%d")
            if line_stripped.startswith(today_date_str):
                return True
            
            # If line doesn't have a timestamp and doesn't start with today's date,
            # include it anyway if we're not getting any timestamped lines (fallback for malformed logs)
            # This ensures we always show something if logs are being written
            return True
        
        try:
            # Get current file position - start from end of file (only new logs)
            # Don't send old logs on initial connection
            last_position = 0
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(0, 2)  # Seek to end
                    last_position = f.tell()
                    # Send a marker that we're starting fresh
                    yield f"data: [INFO] Live log stream started at {session_start_time.strftime('%Y-%m-%d %H:%M:%S')} - showing logs from today\n\n"
            
            # Stream new lines only - tail the file in real-time
            while True:
                try:
                    # Check if file still exists (single rolling log file)
                    if not log_file.exists():
                        # Log file doesn't exist yet, wait for it to be created
                        time.sleep(2)
                        continue
                    
                    if log_file.exists():
                        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(last_position)
                            new_lines = f.readlines()
                            
                            if new_lines:
                                # Filter to only today's lines, but include all if no timestamped lines found
                                sent_count = 0
                                for line in new_lines:
                                    cleaned = line.strip()
                                    if cleaned:  # Skip empty lines
                                        # Only send today's lines (or all if no timestamps)
                                        if is_today_log(cleaned):
                                            yield f"data: {cleaned}\n\n"
                                            sent_count += 1
                                
                                # If no lines were sent but we have new lines, send them anyway (malformed logs)
                                if sent_count == 0 and new_lines:
                                    for line in new_lines:
                                        cleaned = line.strip()
                                        if cleaned:
                                            yield f"data: {cleaned}\n\n"
                                
                                # Update position
                                last_position = f.tell()
                            else:
                                # No new lines, wait a bit
                                time.sleep(0.5)  # Check more frequently
                    else:
                        # File doesn't exist, wait longer
                        time.sleep(2)
                        
                except (IOError, OSError) as e:
                    # File might be locked or rotated, wait and retry
                    time.sleep(1)
                    # Reset position if file was rotated
                    if log_file.exists():
                        try:
                            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                                f.seek(0, 2)
                                last_position = f.tell()
                        except:
                            last_position = 0
        except FileNotFoundError:
            yield f"data: [ERROR] Log file not found: {log_file}\n\n"
            time.sleep(5)
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
            time.sleep(5)
    
    response = Response(stream(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    # Note: "Connection" header is not allowed in WSGI (PEP 3333) - removed
    response.headers["X-Accel-Buffering"] = "no"  # Disable nginx buffering
    response.headers["Access-Control-Allow-Origin"] = "*"  # Allow CORS for SSE
    response.headers["Access-Control-Allow-Headers"] = "Cache-Control"
    return response

@system_bp.route('/api/system/logs')
def get_logs():
    """Get recent log lines from VOFC Processor - BULLETPROOF VERSION that ALWAYS returns something."""
    try:
        import os
        from pathlib import Path
        from datetime import datetime, timedelta
        
        # MULTIPLE FALLBACK PATHS for log file location
        log_file = None
        possible_paths = [
            Config.DATA_DIR / "logs" / "vofc_processor.log",
            Config.ARCHIVE_DIR / "logs" / "vofc_processor.log",
            Path(r"C:\Tools\Ollama\Data\logs\vofc_processor.log"),
            Path(r"C:\Tools\VOFC_Logs\vofc_processor.log"),
            Path(r"C:\Tools\nssm\logs\vofc_processor.log"),
        ]
        
        # Try each path until we find the log file
        # Priority: Use Config.LOGS_DIR first (where processor writes), then fallbacks
        for path in possible_paths:
            if path.exists() and path.is_file():
                log_file = path
                logging.info(f"[MONITOR] Reading logs from: {log_file}")
                break
        
        # If no log file found, return heartbeat immediately
        if not log_file or not log_file.exists():
            heartbeat_time = now_est().strftime("%Y-%m-%d %H:%M:%S")
            heartbeat_msg = f"{heartbeat_time} | INFO | [MONITOR] Log file not found - checking paths: {', '.join(str(p) for p in possible_paths)}"
            logging.debug(heartbeat_msg)
            return jsonify({"lines": [heartbeat_msg], "status": "waiting", "message": "Log file not found yet"}), 200
        
        tail = request.args.get('tail', 50, type=int)
        
        # Show all logs from today (not just last 1 hour) - user wants to see today's activity
        today_date_str = now_est().strftime("%Y-%m-%d")
        today_start = now_est().replace(hour=0, minute=0, second=0, microsecond=0)
        heartbeat_time = now_est().strftime("%Y-%m-%d %H:%M:%S")
        
        def parse_log_timestamp(line):
            """Parse timestamp from log line. Returns None if parsing fails."""
            try:
                # Log format: "2025-11-12 12:38:35 | INFO | ..." or "2025-11-12 12:38:35,253 | INFO | ..."
                if '|' in line:
                    timestamp_str = line.split('|')[0].strip()
                    # Try parsing with milliseconds first (Python default format)
                    try:
                        log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                    except ValueError:
                        # Try without milliseconds
                        try:
                            log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            return None
                    # Convert to EST if needed
                    if EST:
                        # Handle both zoneinfo and pytz
                        if log_time.tzinfo is None:
                            # Naive datetime - need to localize
                            if hasattr(EST, 'localize'):
                                # pytz
                                log_time = EST.localize(log_time)
                            else:
                                # zoneinfo - replace tzinfo directly
                                log_time = log_time.replace(tzinfo=EST)
                        else:
                            # Already timezone-aware - convert to EST
                            log_time = log_time.astimezone(EST)
                    return log_time
            except (ValueError, IndexError, AttributeError):
                pass
            return None
        
        def is_today_log(line):
            """Check if log line is from today - ALWAYS returns True if line exists (fallback)."""
            if not line or not line.strip():
                return False
            
            line_stripped = line.strip()
            
            # Try to parse timestamp first
            log_time = parse_log_timestamp(line_stripped)
            if log_time:
                # If we can parse timestamp, check if it's from today
                return log_time >= today_start
            
            # If no timestamp, check if it starts with today's date
            if line_stripped.startswith(today_date_str):
                return True
            
            # FALLBACK: If line doesn't have a timestamp, include it anyway
            # This ensures we always show something if logs are being written
            return True
        
        # BULLETPROOF: Try to read file with multiple error handling strategies
        result_lines = []
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
                # Filter to only today's lines
                today_lines = []
                for line in lines:
                    line_stripped = line.strip()
                    if line_stripped and is_today_log(line_stripped):
                        today_lines.append(line_stripped)
                
                # If no today's lines found, fallback to last N lines (for malformed logs or if file is empty)
                if not today_lines:
                    # Just return the last N lines regardless of date
                    all_lines = [line.strip() for line in lines if line.strip()]
                    result_lines = all_lines[-tail:] if len(all_lines) > tail else all_lines
                    logging.debug(f"No today's logs found, returning last {len(result_lines)} lines (fallback mode)")
                else:
                    # Return last N lines from today
                    result_lines = today_lines[-tail:] if len(today_lines) > tail else today_lines
                    logging.debug(f"Found {len(today_lines)} today's logs, returning last {len(result_lines)}")
        except PermissionError as e:
            logging.error(f"Permission denied reading log file: {e}")
            result_lines = [f"{heartbeat_time} | ERROR | [MONITOR] Permission denied reading log file: {log_file}"]
        except OSError as e:
            logging.error(f"OS error reading log file: {e}")
            result_lines = [f"{heartbeat_time} | ERROR | [MONITOR] File system error reading log: {str(e)}"]
        except Exception as e:
            logging.error(f"Unexpected error reading log file: {e}", exc_info=True)
            result_lines = [f"{heartbeat_time} | ERROR | [MONITOR] Error reading log file: {str(e)}"]
        
        # ALWAYS ensure we return at least something - NEVER return empty array
        if not result_lines:
            # No logs at all - add heartbeat
            result_lines = [f"{heartbeat_time} | INFO | [MONITOR] Log monitor active - waiting for new log entries..."]
        
        # Validate response against contract
        from config.api_contracts import validate_logs_response
        try:
            response_data = validate_logs_response({"lines": result_lines})
        except Exception as e:
            # If validation fails, return anyway with what we have
            logging.warning(f"Log response validation failed: {e}, returning anyway")
            response_data = {"lines": result_lines}
        
        return jsonify(response_data), 200
    
    except Exception as e:
        # BULLETPROOF: Always return something, even on unexpected errors
        logging.error(f"Unexpected error in get_logs: {e}", exc_info=True)
        heartbeat_time = now_est().strftime("%Y-%m-%d %H:%M:%S")
        error_msg = f"{heartbeat_time} | ERROR | [MONITOR] Error reading logs: {str(e)}"
        return jsonify({"lines": [error_msg], "status": "error", "message": str(e)}), 200

@system_bp.route("/api/system/control", methods=["POST", "OPTIONS"])
def system_control():
    """Control endpoint for auto-processor actions"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json() or {}
        action = data.get("action", "")
        msg = "no_action"
        
        import os
        from pathlib import Path
        import threading
        import logging
        
        # Standardize on VOFC_DATA_DIR (with fallback to VOFC_BASE_DIR for compatibility)
        BASE_DIR = Config.DATA_DIR
        ERROR_DIR = BASE_DIR / "errors"
        AUTOMATION_DIR = BASE_DIR / "automation"
        
        if action == "sync_review":
            try:
                # Note: sync_review functionality moved to PSA-Processor service
                msg = "Review sync is handled by PSA-Processor service. Use the service logs to monitor sync status."
                logging.warning(f"[Admin Control] sync_review: {msg}")
            except Exception as e:
                logging.error(f"Error in sync_review: {e}")
                msg = f"Sync error: {str(e)}"
        
        elif action == "sync_review_to_submissions":
            try:
                # Note: sync_review_to_submissions functionality moved to PSA-Processor service
                msg = "Review files sync is handled by PSA-Processor service."
                logging.warning(f"[Admin Control] sync_review_to_submissions: {msg}")
            except Exception as e:
                logging.error(f"Error in sync_review_to_submissions: {e}")
                msg = f"Sync error: {str(e)}"
        
        elif action == "clear_processed_tracking":
            try:
                # Note: Processed tracking is no longer used - PSA-Processor handles deduplication
                msg = "Processed file tracking is deprecated. PSA-Processor uses Supabase for deduplication."
                logging.info(f"[Admin Control] clear_processed_tracking: {msg}")
            except Exception as e:
                logging.error(f"Error clearing processed tracking: {e}")
                msg = f"Clear error: {str(e)}"
        
        elif action == "enable_processed_tracking":
            try:
                # Note: Processed tracking is no longer used
                msg = "Processed file tracking is deprecated. VOFC-Processor uses Supabase for deduplication."
                logging.info(f"[Admin Control] enable_processed_tracking: {msg}")
            except Exception as e:
                logging.error(f"Error enabling processed tracking: {e}")
                msg = f"Enable error: {str(e)}"
        
        elif action == "disable_processed_tracking":
            try:
                # Note: Processed tracking is no longer used
                msg = "Processed file tracking is deprecated. VOFC-Processor uses Supabase for deduplication."
                logging.info(f"[Admin Control] disable_processed_tracking: {msg}")
            except Exception as e:
                logging.error(f"Error disabling processed tracking: {e}")
                msg = f"Disable error: {str(e)}"
        
        elif action == "start_watcher":
            try:
                import subprocess
                # Start VOFC-Processor service via NSSM (the actual watcher/processor)
                service_names = ['VOFC-Processor', 'vofc-processor', 'PSA-Processor']
                started = False
                error_msg = None
                
                for service_name in service_names:
                    try:
                        # Check if service exists first
                        check_result = subprocess.run(
                            ['sc', 'query', service_name],
                            capture_output=True,
                            text=True,
                            timeout=3
                        )
                        if check_result.returncode == 0:
                            # Service exists, try to start it
                            result = subprocess.run(
                                ['nssm', 'start', service_name],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            if result.returncode == 0:
                                started = True
                                msg = f"VOFC-Processor service ({service_name}) started successfully"
                                logging.info(f"[Admin Control] {msg}")
                                break
                            else:
                                error_msg = result.stderr or result.stdout or "Unknown error"
                        else:
                            continue  # Service doesn't exist, try next name
                    except subprocess.TimeoutExpired:
                        error_msg = f"Timeout starting {service_name}"
                        continue
                    except Exception as e:
                        error_msg = str(e)
                        continue
                
                if not started:
                    if error_msg:
                        msg = f"Failed to start VOFC-Processor service: {error_msg}"
                    else:
                        msg = "VOFC-Processor service not found. Please check service name and NSSM configuration."
                    logging.error(f"[Admin Control] {msg}")
            except Exception as e:
                logging.error(f"Error starting watcher: {e}")
                msg = f"Start watcher error: {str(e)}"
        
        elif action == "stop_watcher":
            try:
                import subprocess
                # Stop VOFC-Processor service via NSSM (the actual watcher/processor)
                service_names = ['VOFC-Processor', 'vofc-processor', 'PSA-Processor']
                stopped = False
                error_msg = None
                
                for service_name in service_names:
                    try:
                        # Check if service exists first
                        check_result = subprocess.run(
                            ['sc', 'query', service_name],
                            capture_output=True,
                            text=True,
                            timeout=3
                        )
                        if check_result.returncode == 0:
                            # Service exists, try to stop it
                            result = subprocess.run(
                                ['nssm', 'stop', service_name],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            if result.returncode == 0:
                                stopped = True
                                msg = f"VOFC-Processor service ({service_name}) stopped successfully"
                                logging.info(f"[Admin Control] {msg}")
                                break
                            else:
                                error_msg = result.stderr or result.stdout or "Unknown error"
                        else:
                            continue  # Service doesn't exist, try next name
                    except subprocess.TimeoutExpired:
                        error_msg = f"Timeout stopping {service_name}"
                        continue
                    except Exception as e:
                        error_msg = str(e)
                        continue
                
                if not stopped:
                    if error_msg:
                        msg = f"Failed to stop VOFC-Processor service: {error_msg}"
                    else:
                        msg = "VOFC-Processor service not found. Please check service name and NSSM configuration."
                    logging.error(f"[Admin Control] {msg}")
            except Exception as e:
                logging.error(f"Error stopping watcher: {e}")
                msg = f"Stop watcher error: {str(e)}"
        
        elif action == "clear_errors":
            try:
                cleared = 0
                for f in ERROR_DIR.glob("*.*"):
                    try:
                        f.unlink(missing_ok=True)
                        cleared += 1
                    except Exception:
                        pass
                msg = f"Error folder cleared ({cleared} files removed)"
            except Exception as e:
                logging.error(f"Error clearing errors: {e}")
                msg = f"Clear errors error: {str(e)}"
        
        elif action == "cleanup_review_temp":
            try:
                # Cleanup review temp files manually
                review_temp_dir = BASE_DIR / "review" / "temp"
                if review_temp_dir.exists():
                    cleared = 0
                    for f in review_temp_dir.glob("*.*"):
                        try:
                            f.unlink(missing_ok=True)
                            cleared += 1
                        except Exception:
                            pass
                    msg = f"Review temp files cleanup completed ({cleared} files removed)"
                else:
                    msg = "Review temp directory not found"
            except Exception as e:
                logging.error(f"Error in cleanup_review_temp: {e}")
                msg = f"Cleanup error: {str(e)}"
        
        elif action == "clear_logs":
            try:
                # Find and truncate the log file
                possible_paths = [
                    Config.DATA_DIR / "logs" / "vofc_processor.log",
                    Config.ARCHIVE_DIR / "logs" / "vofc_processor.log",
                    Path(r"C:\Tools\Ollama\Data\logs\vofc_processor.log"),
                    Path(r"C:\Tools\VOFC_Logs\vofc_processor.log"),
                    Path(r"C:\Tools\nssm\logs\vofc_processor.log"),
                ]
                
                log_file = None
                for path in possible_paths:
                    if path.exists() and path.is_file():
                        log_file = path
                        break
                
                if log_file:
                    # Truncate the file (wipe it)
                    with open(log_file, 'w', encoding='utf-8') as f:
                        f.write('')  # Write empty string to truncate
                    msg = f"Log file cleared: {log_file}"
                    logging.info(f"[Admin Control] {msg}")
                else:
                    msg = "Log file not found - no log file to clear"
                    logging.warning(f"[Admin Control] {msg}")
            except PermissionError as e:
                logging.error(f"Permission denied clearing log file: {e}")
                msg = f"Permission denied: Cannot clear log file ({str(e)})"
            except Exception as e:
                logging.error(f"Error clearing logs: {e}", exc_info=True)
                msg = f"Clear logs error: {str(e)}"
        
        elif action == "cleanup_rejected_submissions":
            try:
                import traceback
                from datetime import datetime, timedelta
                
                # Get optional parameters
                request_data = request.get_json(silent=True) or {}
                older_than_days = request_data.get('older_than_days')
                dry_run = request_data.get('dry_run', False)
                
                logging.info(f"[Admin Control] cleanup_rejected_submissions: older_than_days={older_than_days}, dry_run={dry_run}")
                
                # Query rejected submissions
                supabase_client = get_supabase()
                if not supabase_client:
                    return jsonify({"error": "Supabase not configured"}), 503
                query = supabase_client.table('submissions').select('id, status, created_at, updated_at').eq('status', 'rejected')
                
                # Filter by date if specified
                if older_than_days and isinstance(older_than_days, (int, float)) and older_than_days > 0:
                    cutoff_date = datetime.utcnow() - timedelta(days=int(older_than_days))
                    query = query.lte('updated_at', cutoff_date.isoformat())
                
                result = query.execute()
                rejected_submissions = result.data if result.data else []
                
                if not rejected_submissions:
                    msg = "No rejected submissions found"
                    logging.info(f"[Admin Control] {msg}")
                else:
                    if dry_run:
                        msg = f"DRY RUN: Found {len(rejected_submissions)} rejected submission(s) that would be deleted"
                        logging.info(f"[Admin Control] {msg}")
                    else:
                        deleted_count = 0
                        error_count = 0
                        errors = []
                        
                        for submission in rejected_submissions:
                            submission_id = submission['id']
                            try:
                                # Delete from related tables first (due to foreign key constraints)
                                # Note: These deletes are idempotent - safe to run even if data doesn't exist
                                
                                # Get Supabase client (already checked above, but get it again for this loop)
                                if not supabase_client:
                                    supabase_client = get_supabase()
                                    if not supabase_client:
                                        raise Exception("Supabase not configured")
                                
                                # Delete submission_vulnerability_ofc_links
                                supabase_client.table('submission_vulnerability_ofc_links').delete().eq('submission_id', submission_id).execute()
                                
                                # Delete submission_ofc_sources
                                supabase_client.table('submission_ofc_sources').delete().eq('submission_id', submission_id).execute()
                                
                                # Delete submission_options_for_consideration
                                supabase_client.table('submission_options_for_consideration').delete().eq('submission_id', submission_id).execute()
                                
                                # Delete submission_vulnerabilities
                                supabase_client.table('submission_vulnerabilities').delete().eq('submission_id', submission_id).execute()
                                
                                # Delete submission_sources
                                supabase_client.table('submission_sources').delete().eq('submission_id', submission_id).execute()
                                
                                # Finally, delete the main submission
                                delete_result = supabase_client.table('submissions').delete().eq('id', submission_id).execute()
                                
                                deleted_count += 1
                                logging.info(f"[Admin Control] Deleted rejected submission {submission_id}")
                                
                            except Exception as delete_err:
                                error_count += 1
                                errors.append(f"Submission {submission_id}: {str(delete_err)}")
                                logging.error(f"[Admin Control] Failed to delete submission {submission_id}: {delete_err}")
                        
                        if error_count > 0:
                            msg = f"Cleanup complete: {deleted_count} deleted, {error_count} errors. Errors: {'; '.join(errors[:5])}"
                        else:
                            msg = f"Cleanup complete: {deleted_count} rejected submission(s) deleted"
                        logging.info(f"[Admin Control] {msg}")
                        
            except Exception as e:
                logging.error(f"Error in cleanup_rejected_submissions: {e}")
                logging.error(traceback.format_exc())
                msg = f"Cleanup error: {str(e)}"
        
        elif action == "process_existing":
            try:
                import traceback
                from pathlib import Path
                
                # Check if Processor service is running (try actual names first, then alternatives)
                service_names = ['VOFC-Processor', 'vofc-processor', 'PSA-Processor']
                service_status = "unknown"
                
                for service_name in service_names:
                    try:
                        import subprocess
                        result = subprocess.run(
                            ['nssm', 'status', service_name],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if result.returncode == 0 and 'SERVICE_RUNNING' in result.stdout:
                            service_status = "running"
                            break  # Found running service
                        elif result.returncode == 0:
                            service_status = "not running"
                            break  # Found service but not running
                    except:
                        continue  # Try next service name
                
                INCOMING_DIR = BASE_DIR / "incoming"
                logging.info(f"[Admin Control] process_existing: Checking {INCOMING_DIR}")
                
                # Count files in incoming directory
                if INCOMING_DIR.exists():
                    existing_files = list(INCOMING_DIR.glob("*.pdf"))
                    file_count = len(existing_files)
                    logging.info(f"[Admin Control] Found {file_count} PDF file(s) in incoming/")
                else:
                    file_count = 0
                    logging.warning(f"[Admin Control] Incoming directory not found: {INCOMING_DIR}")
                
                if service_status == "running":
                    if file_count > 0:
                        msg = f"VOFC-Processor service is running and will automatically process {file_count} file(s) in incoming/ directory. Processing happens continuously every 30 seconds."
                    else:
                        msg = "VOFC-Processor service is running. No files found in incoming/ directory. Files will be processed automatically when added."
                else:
                    msg = f"VOFC-Processor service is {service_status}. Please start the service to process files. Files found: {file_count}"
                    logging.warning(f"[Admin Control] {msg}")
                
                logging.info(f"[Admin Control] {msg}")
            except Exception as e:
                import traceback
                error_msg = f"Error checking processing status: {e}"
                logging.error(f"[Admin Control] {error_msg}")
                logging.error(f"[Admin Control] Traceback: {traceback.format_exc()}")
                msg = f"Process existing check error: {str(e)}"
        
        elif action == "process_pending":
            try:
                import subprocess
                from pathlib import Path
                
                INCOMING_DIR = BASE_DIR / "incoming"
                
                # Count files in incoming directory
                if INCOMING_DIR.exists():
                    pdf_files = list(INCOMING_DIR.glob("*.pdf"))
                    file_count = len(pdf_files)
                else:
                    file_count = 0
                    logging.warning(f"[Admin Control] Incoming directory not found: {INCOMING_DIR}")
                
                if file_count == 0:
                    msg = "No files found in incoming/ directory to process"
                    logging.info(f"[Admin Control] process_pending: {msg}")
                else:
                    # Check if Processor service is running
                    service_names = ['VOFC-Processor', 'vofc-processor', 'PSA-Processor']
                    service_running = False
                    
                    for service_name in service_names:
                        try:
                            result = subprocess.run(
                                ['sc', 'query', service_name],
                                capture_output=True,
                                text=True,
                                timeout=3
                            )
                            if result.returncode == 0:
                                output_upper = result.stdout.upper()
                                if 'STATE' in output_upper and ('STATE' in output_upper and '4' in output_upper.split() or 'RUNNING' in output_upper):
                                    service_running = True
                                    break
                        except:
                            continue
                    
                    if service_running:
                        # Service is running - it will process files automatically
                        # We can't trigger it directly, but we can tell the user
                        msg = f"Found {file_count} file(s) in incoming/. VOFC-Processor service is running and will process them automatically (every 30 seconds). Files are being processed now."
                    else:
                        msg = f"Found {file_count} file(s) in incoming/, but VOFC-Processor service is not running. Please start the service to process files."
                        logging.warning(f"[Admin Control] {msg}")
                
                logging.info(f"[Admin Control] process_pending: {msg}")
            except Exception as e:
                logging.error(f"Error in process_pending: {e}")
                msg = f"Process pending error: {str(e)}"
        
        elif action == "process_one":
            try:
                import subprocess
                from pathlib import Path
                
                # Get submission_id from request
                request_data = request.get_json(silent=True) or {}
                submission_id = request_data.get('submission_id') or request_data.get('id')
                filename = request_data.get('filename')
                
                if not submission_id and not filename:
                    msg = "process_one requires either submission_id or filename"
                    logging.warning(f"[Admin Control] {msg}")
                else:
                    if filename:
                        # Process specific file from incoming directory
                        INCOMING_DIR = BASE_DIR / "incoming"
                        file_path = INCOMING_DIR / filename
                        
                        if file_path.exists():
                            # Check if processor service is running
                            service_names = ['VOFC-Processor', 'vofc-processor', 'PSA-Processor']
                            service_running = False
                            
                            for service_name in service_names:
                                try:
                                    result = subprocess.run(
                                        ['sc', 'query', service_name],
                                        capture_output=True,
                                        text=True,
                                        timeout=3
                                    )
                                    if result.returncode == 0 and ('RUNNING' in result.stdout.upper() or 'STATE' in result.stdout.upper() and '4' in result.stdout):
                                        service_running = True
                                        break
                                except:
                                    continue
                            
                            if service_running:
                                msg = f"File {filename} will be processed by VOFC-Processor service (running). Processing happens automatically every 30 seconds."
                            else:
                                msg = f"File {filename} found, but VOFC-Processor service is not running. Please start the service to process files."
                        else:
                            msg = f"File {filename} not found in incoming/ directory"
                    else:
                        # Process submission from database (would need to call extract endpoint)
                        msg = f"Processing submission {submission_id} - this requires calling the extract endpoint, which is handled separately"
                
                logging.info(f"[Admin Control] process_one: {msg}")
            except Exception as e:
                logging.error(f"Error in process_one: {e}")
                msg = f"Process one error: {str(e)}"
        
        elif action == "restart_ollama_with_deps":
            try:
                from routes.service_manager import restart_with_dependencies
                result = restart_with_dependencies('VOFC-Ollama')
                
                if result['success']:
                    msg = result['message']
                    # Include step details in response
                    steps_summary = "\n".join([
                        f"  • {step['action']} {step['service']}: {step['status']} - {step['message']}"
                        for step in result['steps']
                    ])
                    msg = f"{msg}\n\nSteps:\n{steps_summary}"
                else:
                    msg = result['message']
                    if result['errors']:
                        errors_summary = "\n".join([f"  • {err}" for err in result['errors']])
                        msg = f"{msg}\n\nErrors:\n{errors_summary}"
                
                logging.info(f"[Admin Control] restart_ollama_with_deps: {msg}")
            except Exception as e:
                logging.error(f"Error in restart_ollama_with_deps: {e}")
                msg = f"Restart Ollama with dependencies error: {str(e)}"
        
        elif action == "restart_service_with_deps":
            try:
                from routes.service_manager import restart_with_dependencies
                # Get service name from request
                request_data = request.get_json(silent=True) or {}
                service_name = request_data.get('service_name') or request_data.get('service')
                
                if not service_name:
                    msg = "restart_service_with_deps requires service_name parameter"
                    logging.warning(f"[Admin Control] {msg}")
                else:
                    result = restart_with_dependencies(service_name)
                    
                    if result['success']:
                        msg = result['message']
                        steps_summary = "\n".join([
                            f"  • {step['action']} {step['service']}: {step['status']} - {step['message']}"
                            for step in result['steps']
                        ])
                        msg = f"{msg}\n\nSteps:\n{steps_summary}"
                    else:
                        msg = result['message']
                        if result['errors']:
                            errors_summary = "\n".join([f"  • {err}" for err in result['errors']])
                            msg = f"{msg}\n\nErrors:\n{errors_summary}"
                    
                    logging.info(f"[Admin Control] restart_service_with_deps ({service_name}): {msg}")
            except Exception as e:
                logging.error(f"Error in restart_service_with_deps: {e}")
                msg = f"Restart service with dependencies error: {str(e)}"
        
        elif action == "restart_all_services":
            try:
                from routes.service_manager import restart_all_services
                result = restart_all_services()
                
                if result['success']:
                    msg = result['message']
                    steps_summary = "\n".join([
                        f"  • {step['action']} {step['service']}: {step['status']} - {step['message']}"
                        for step in result['steps']
                    ])
                    msg = f"{msg}\n\nSteps:\n{steps_summary}"
                else:
                    msg = result['message']
                    if result['errors']:
                        errors_summary = "\n".join([f"  • {err}" for err in result['errors']])
                        msg = f"{msg}\n\nErrors:\n{errors_summary}"
                
                logging.info(f"[Admin Control] restart_all_services: {msg}")
            except Exception as e:
                logging.error(f"Error in restart_all_services: {e}")
                msg = f"Restart all services error: {str(e)}"
        
        else:
            msg = f"Unknown action: {action}"
        
        logging.info(f"[Admin Control] {msg}")
        return jsonify({"status": "ok", "message": msg}), 200
        
    except Exception as e:
        import logging
        logging.error(f"Error in system_control: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@system_bp.route("/api/disciplines", methods=["GET", "OPTIONS"])
def get_disciplines():
    """Return all active security disciplines."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        supabase_client = get_supabase()
        if not supabase_client:
            return jsonify({"error": "Supabase not configured"}), 503
        res = supabase_client.table("disciplines").select("id, name, category, code, discipline_subtypes(id, name, code, is_active)").eq("is_active", True).execute()
        # Return as array directly (not wrapped) for compatibility with viewer
        return jsonify(res.data if res.data else []), 200
    except Exception as e:
        print(f"[Disciplines] Error: {str(e)}")
        # Return empty array on error to prevent viewer crashes
        return jsonify([]), 200

@system_bp.route("/api/sectors", methods=["GET", "OPTIONS"])
def get_sectors():
    """Return all active sectors."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        supabase_client = get_supabase()
        if not supabase_client:
            return jsonify({"error": "Supabase not configured"}), 503
        res = supabase_client.table("sectors").select("id, sector_name").eq("is_active", True).execute()
        # Return as array directly (not wrapped) for compatibility with viewer
        return jsonify(res.data if res.data else []), 200
    except Exception as e:
        print(f"[Sectors] Error: {str(e)}")
        # Return empty array on error to prevent viewer crashes
        return jsonify([]), 200

@system_bp.route("/api/subsectors", methods=["GET", "OPTIONS"])
def get_subsectors():
    """Return all active subsectors."""
    if request.method == 'OPTIONS':
        return '', 200
    try:
        supabase_client = get_supabase()
        if not supabase_client:
            return jsonify({"error": "Supabase not configured"}), 503
        res = supabase_client.table("subsectors").select("id, subsector_name").eq("is_active", True).execute()
        # Return as array directly (not wrapped) for compatibility with viewer
        return jsonify(res.data if res.data else []), 200
    except Exception as e:
        print(f"[Subsectors] Error: {str(e)}")
        # Return empty array on error to prevent viewer crashes
        return jsonify([]), 200

def get_tunnel_log_path():
    """Locate the most recent active tunnel log file."""
    possible_paths = [
        Config.TUNNEL_LOG_PATHS[0],
        Path(r"C:\Users\frost\OneDrive\Desktop\Projects\VOFC Engine\logs\tunnel_out.log"),
        Path(r"C:\Users\frost\VOFC_Logs\tunnel_2025-11-03_09-45-08.log")
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    # fallback: newest file in VOFC_Logs directory
    vofc_dir = Path(r"C:\Users\frost\VOFC_Logs")
    if vofc_dir.exists():
        log_files = sorted(
            vofc_dir.glob("tunnel_*.log"), 
            key=lambda f: f.stat().st_mtime, 
            reverse=True
        )
        if log_files:
            return log_files[0]
    
    return None

@system_bp.route("/api/system/tunnel/logs", methods=["GET", "OPTIONS"])
def get_tunnel_logs():
    """Return the last 100 lines of the tunnel log."""
    if request.method == 'OPTIONS':
        return '', 200
    
    from config.exceptions import FileOperationError
    
    try:
        path = get_tunnel_log_path()
        if not path:
            return jsonify({"error": "No tunnel log found", "lines": []}), 200  # Return 200 with empty lines
        
        # Verify file exists and is readable before opening
        if not path.exists():
            raise FileNotFoundError(f"Tunnel log file not found: {path}")
        if not path.is_file():
            raise FileOperationError(f"Tunnel log path is not a file: {path}")
        
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.rstrip('\n\r') for line in f.readlines()[-100:]]
        
        return jsonify({
            "file": str(path),
            "lines": lines,
            "count": len(lines)
        }), 200
    
    except FileNotFoundError as e:
        logging.warning(f"Tunnel log file not found: {e}")
        return jsonify({
            "error": f"Tunnel log file not found: {e}",
            "lines": [],
            "file": None
        }), 200
    except PermissionError as e:
        logging.error(f"Permission denied reading tunnel log: {e}")
        raise FileOperationError(f"Cannot read tunnel log file (permission denied): {e}")
    except OSError as e:
        logging.error(f"OS error reading tunnel log: {e}")
        raise FileOperationError(f"File system error reading tunnel log: {e}")
    except Exception as e:
        logging.error(f"Unexpected error reading tunnel logs: {e}", exc_info=True)
        raise FileOperationError(f"Unexpected error reading tunnel logs: {e}")

