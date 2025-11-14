"""
System routes for health checks and version info
Routes: /, /api/system/health, /api/version, /api/progress
"""

from flask import Blueprint, jsonify, request
from services.ollama_client import test_ollama
from services.supabase_client import test_supabase, get_supabase_client
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
    EST = ZoneInfo("America/New_York")
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

# Get Supabase client for lightweight routes
supabase = get_supabase_client()

def test_flask_service():
    """
    Check if Flask Windows service is running.
    Only checks 'vofc-flask' (lowercase) - the single Flask service.
    Returns 'ok' if running, 'offline' if stopped, 'unknown' if check fails.
    """
    # Only check vofc-flask (lowercase) - single Flask service
    service_names = ['vofc-flask']
    
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
                
                # Improved parsing: Handle format "STATE : 4  RUNNING" or "STATE              : 4  RUNNING"
                # Look for STATE line and extract state code
                for line in output.split('\n'):
                    line_upper = line.upper()
                    if 'STATE' in line_upper:
                        # Parse state code - can be "STATE : 4" or "STATE              : 4"
                        # Extract number after colon
                        if ':' in line:
                            # Split on colon and get the part after it
                            after_colon = line.split(':', 1)[1].strip()
                            # Extract first number (state code)
                            state_match = re.search(r'\b(\d+)\b', after_colon)
                            if state_match:
                                state_code = state_match.group(1)
                                # State codes: 1=STOPPED, 2=START_PENDING, 3=STOP_PENDING, 4=RUNNING, 7=PAUSED
                                if state_code == '4':
                                    logging.debug(f"Flask service {service_name} is RUNNING (state code 4)")
                                    return 'ok'
                                elif state_code == '1':
                                    logging.debug(f"Flask service {service_name} is STOPPED (state code 1)")
                                    return 'offline'
                                elif state_code == '7':
                                    logging.debug(f"Flask service {service_name} is PAUSED (state code 7)")
                                    return 'offline'
                
                # Fallback: check text in output (more reliable)
                if 'RUNNING' in output_upper and 'STOPPED' not in output_upper:
                    logging.debug(f"Flask service {service_name} is RUNNING (text match)")
                    return 'ok'
                elif 'STOPPED' in output_upper or 'STOP_PENDING' in output_upper:
                    logging.debug(f"Flask service {service_name} is STOPPED (text match)")
                    return 'offline'
                elif 'PAUSED' in output_upper or 'PAUSE_PENDING' in output_upper:
                    logging.debug(f"Flask service {service_name} is PAUSED (text match)")
                    return 'offline'
                else:
                    # Service exists but state unclear - log for debugging
                    logging.warning(f"Flask service {service_name} found but state unclear. Output: {output[:200]}")
                    continue  # Try next service name
            # If service not found (returncode != 0), try next name
            else:
                logging.debug(f"Service {service_name} not found (returncode: {result.returncode})")
        except subprocess.TimeoutExpired:
            logging.debug(f"Timeout checking Flask service {service_name}")
            continue
        except FileNotFoundError:
            logging.warning("sc.exe not found - cannot check Flask service status")
            return 'unknown'
        except Exception as e:
            logging.debug(f"Error checking Flask service {service_name}: {e}")
            continue
    
    # Service might not exist or access denied
    logging.warning("Flask service not found with any of the checked names")
    return 'unknown'

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
                                    elif state_code == '1' or 'STOPPED' in state_text.upper():
                                        return 'offline'
                                    elif state_code == '7' or 'PAUSED' in state_text.upper():
                                        return 'offline'
                                    break
                
                # Fallback: check text in output
                if 'RUNNING' in output_upper:
                    return 'ok'
                elif 'STOPPED' in output_upper or 'STOP_PENDING' in output_upper:
                    return 'offline'
                elif 'PAUSED' in output_upper or 'PAUSE_PENDING' in output_upper:
                    return 'offline'
                else:
                    continue  # Try next service name
            # If service not found, try next name
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logging.debug(f"Error checking tunnel service {service_name}: {e}")
            continue
    
    # If all service names failed, check if tunnel is accessible via URL
    try:
        tunnel_url = os.getenv("TUNNEL_URL", "https://flask.frostech.site")
        response = requests.get(f"{tunnel_url}/api/system/health", timeout=3)
        if response.status_code == 200:
            return 'ok'
        else:
            return 'offline'
    except Exception as e:
        logging.debug(f"Tunnel URL check failed: {e}")
    
    # Service might not exist or access denied
    return 'unknown'

def test_model_manager():
    """
    Check if Model Manager Windows service is running.
    Returns 'online' if running, 'paused' if paused, 'offline' if stopped, 'unknown' if check fails.
    """
    # Try actual service names first, then alternatives for compatibility
    service_names = ['VOFC-ModelManager', 'vofc-modelmanager', 'VOFC-Model-Manager', 'PSA-ModelManager', 'ModelManager']
    
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
                
                # Parse STATE line: "STATE : 4 RUNNING" or "STATE : 1 STOPPED" or "STATE : 7 PAUSED"
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
                                        return 'online'
                                    elif state_code == '7' or 'PAUSED' in state_text.upper():
                                        return 'paused'
                                    elif state_code == '1' or 'STOPPED' in state_text.upper():
                                        return 'offline'
                                    break
                
                # Fallback: check text in output
                if 'RUNNING' in output_upper:
                    return 'online'
                elif 'PAUSED' in output_upper or 'PAUSE_PENDING' in output_upper:
                    return 'paused'
                elif 'STOPPED' in output_upper or 'STOP_PENDING' in output_upper:
                    return 'offline'
                else:
                    continue  # Try next service name
            # If service not found, try next name
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logging.debug(f"Error checking model manager service {service_name}: {e}")
            continue
    
    # Service might not exist or access denied
    return 'unknown'

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
    
    # Get Ollama URL - try multiple environment variables for consistency
    ollama_url_raw = (
        os.getenv("OLLAMA_HOST") or 
        os.getenv("OLLAMA_URL") or 
        os.getenv("OLLAMA_API_BASE_URL") or
        "http://127.0.0.1:11434"
    )
    
    # Ensure URL is properly formatted
    ollama_base = ollama_url_raw.rstrip('/')
    if not ollama_base.startswith(('http://', 'https://')):
        ollama_base = f"http://{ollama_base}"
    
    # Get Flask URL for reporting
    flask_port = int(os.getenv('FLASK_PORT', '8080'))
    flask_url = f"http://127.0.0.1:{flask_port}"
    
    # Initialize components status
    # Check Flask service status (similar to tunnel and model manager checks)
    flask_service_status = test_flask_service()
    components = {
        "flask": flask_service_status if flask_service_status in ["ok", "offline", "unknown"] else "unknown",
        "ollama": "offline",
        "supabase": test_supabase(),
        "model_manager": test_model_manager()
    }
    
    # Check Ollama - use service function
    ollama_status = test_ollama()
    components["ollama"] = ollama_status if ollama_status in ["ok", "offline", "error"] else "offline"
    
    # Get tunnel URL (managed by NSSM service - Cloudflare tunnel)
    tunnel_url = os.getenv('TUNNEL_URL', 'https://flask.frostech.site')
    
    # Check tunnel service status (similar to model manager check)
    tunnel_status = test_tunnel_service()
    
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
        except Exception:
            # Connectivity check failed but service is running
            pass  # Keep status as "ok" if service is running
    
    # Get Model Manager last run time and next run time
    model_manager_info = {"status": components["model_manager"]}
    try:
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "services", "model_manager.py")
        # Try to read from the actual log file
        # Old log path archived - using Ollama\Data\logs instead
        log_path = None
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Look for last "Run Start" timestamp
                for line in reversed(lines):
                    if "=== VOFC Model Manager Run Start ===" in line:
                        # Extract timestamp from log line
                        try:
                            # Format: "2025-11-08 09:52:44,745 | INFO | === VOFC Model Manager Run Start ==="
                            timestamp_str = line.split(" | ")[0]
                            last_run = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                            next_run = last_run + timedelta(seconds=21600)  # 6 hours
                            model_manager_info["last_run"] = last_run.isoformat()
                            model_manager_info["next_run"] = next_run.isoformat()
                            break
                        except:
                            pass
    except Exception:
        pass  # If we can't read the log, just return status
    
    # Return lightweight response with service metadata
    return jsonify({
        "flask": components["flask"],
        "ollama": components["ollama"],
        "supabase": components["supabase"],
        "tunnel": tunnel_status,  # Tunnel is externally managed by NSSM
        "model_manager": components["model_manager"],  # Model Manager service status
        "model_manager_info": model_manager_info,  # Additional Model Manager info
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
        "model": os.getenv('OLLAMA_MODEL', 'psa-engine')
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
    try:
        import os
        from pathlib import Path
        
        # Use same path as auto-processor
        base_dir = Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))
        progress_file = base_dir / "automation" / "progress.json"
        
        # Get progress data - always refresh folder counts dynamically
        progress_data = {}
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                progress_data = json.load(f)
        except FileNotFoundError:
            progress_data = {
                "status": "unknown", 
                "message": "progress.json not found",
            }
        
        # Always update folder counts dynamically (don't rely on stale data)
        incoming_dir = base_dir / "incoming"
        processed_dir = base_dir / "processed"
        library_dir = base_dir / "library"
        errors_dir = base_dir / "errors"
        review_dir = base_dir / "review"
        temp_errors_dir = base_dir / "temp" / "errors"
        
        # Count files in each directory
        try:
            incoming_count = len(list(incoming_dir.glob("*.pdf"))) if incoming_dir.exists() else 0
            progress_data["incoming"] = incoming_count
            progress_data["incoming_label"] = "Pending Processing (Learning Mode)"
            progress_data["incoming_description"] = "Files waiting for processing or reprocessing to improve extraction"
        except Exception:
            progress_data["incoming"] = 0
            progress_data["incoming_label"] = "Pending Processing"
            progress_data["incoming_description"] = ""
            
        try:
            processed_count = len(list(processed_dir.glob("*.json"))) if processed_dir.exists() else 0
            progress_data["processed"] = processed_count
            progress_data["processed_label"] = "Processed JSON"
            progress_data["processed_description"] = "Extraction results (JSON files)"
        except Exception:
            progress_data["processed"] = 0
            progress_data["processed_label"] = "Processed JSON"
            progress_data["processed_description"] = ""
            
        try:
            library_count = len(list(library_dir.glob("*.pdf"))) if library_dir.exists() else 0
            progress_data["library"] = library_count
            progress_data["library_label"] = "Archived (Complete)"
            progress_data["library_description"] = "Files successfully processed with sufficient records"
        except Exception:
            progress_data["library"] = 0
            progress_data["library_label"] = "Archived (Complete)"
            progress_data["library_description"] = ""
            
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
        except Exception:
            progress_data["errors"] = 0
            progress_data["errors_label"] = "Processing Errors"
            progress_data["errors_description"] = ""
            
        try:
            review_count = len(list(review_dir.glob("*.json"))) if review_dir.exists() else 0
            progress_data["review"] = review_count
            progress_data["review_label"] = "Review Queue"
            progress_data["review_description"] = "Extraction results pending review"
        except Exception:
            progress_data["review"] = 0
            progress_data["review_label"] = "Review Queue"
            progress_data["review_description"] = ""
        
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
                    state_match = re.search(r'STATE\s*:\s*4', output_upper)
                    has_state_4 = state_match is not None
                    has_running = 'RUNNING' in output_upper
                    has_stopped = 'STOPPED' in output_upper
                    
                    # Primary check: State code 4 (RUNNING) - most reliable
                    if has_state_4:
                        service_running = True
                        logging.info(f"Service check: State code 4 found - service is running")
                        break  # Found running service, exit loop
                    # Fallback check: RUNNING keyword present and STOPPED not present
                    elif has_running and not has_stopped:
                        service_running = True
                        logging.info(f"Service check: RUNNING found, STOPPED not found - service is running")
                        break  # Found running service, exit loop
                    else:
                        # Log for debugging
                        logging.warning(f"Service check failed: RUNNING={has_running}, STOPPED={has_stopped}, State 4={has_state_4}")
                        logging.debug(f"Service output (first 200 chars): {result.stdout[:200]}")
                        # Service exists but not running, continue to check if it exists
                        if 'does not exist' not in result.stdout.lower() and 'does not exist' not in result.stderr.lower():
                            # Service exists but stopped
                            service_running = False
                            break  # Found service (stopped), exit loop
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
            
    except FileNotFoundError:
        # sc.exe not found (not Windows or PATH issue)
        logging.warning("sc.exe not found - cannot check service status")
        progress_data["watcher_status"] = "unknown"
    except Exception as e:
            logging.warning(f"Could not get watcher status: {e}", exc_info=True)
            progress_data["watcher_status"] = "unknown"
        
        # Ensure timestamp exists
        if "timestamp" not in progress_data:
            progress_data["timestamp"] = now_est().isoformat()
        
        return jsonify(progress_data)
    except Exception as e:
        import logging
        logging.error(f"Error reading progress.json: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": now_est().isoformat(),
            "incoming": 0,
            "incoming_label": "Pending Processing (Learning Mode)",
            "incoming_description": "Files waiting for processing or reprocessing to improve extraction",
            "processed": 0,
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
        base_dir = Path(os.getenv("VOFC_DATA_DIR", r"C:\Tools\Ollama\Data"))
        if not base_dir.exists():
            # Fallback to archive location if needed (for migration)
            archive_data = Path(r"C:\Tools\archive\VOFC\Data")
            if archive_data.exists():
                base_dir = archive_data
            else:
                base_dir = Path(r"C:\Tools\Ollama\Data")  # Default
        
        logs_dir = base_dir / "logs"
        today = now_est().strftime("%Y%m%d")
        log_file = logs_dir / f"vofc_processor_{today}.log"
        
        # Show all logs from today (not just last 1 hour) - user wants to see today's activity
        # Track session start time for initial connection
        session_start_time = now_est()
        today_start = session_start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Always use today's log file - don't fallback to old files
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
            response.headers["Connection"] = "keep-alive"
            response.headers["X-Accel-Buffering"] = "no"
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
        
        def parse_log_timestamp(line):
            """Parse timestamp from log line. Returns None if parsing fails."""
            try:
                # Log format: "2025-11-12 12:38:35 | INFO | ..."
                if '|' in line:
                    timestamp_str = line.split('|')[0].strip()
                    # Try parsing the timestamp
                    log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    # Convert to EST if needed
                    if EST:
                        log_time = EST.localize(log_time) if log_time.tzinfo is None else log_time.astimezone(EST)
                    return log_time
            except (ValueError, IndexError):
                pass
            return None
        
        def is_today_log(line):
            """Check if log line is from today."""
            if not line or not line.strip():
                return False
            
            # Must start with today's date
            today_date_str = now_est().strftime("%Y-%m-%d")
            if not line.strip().startswith(today_date_str):
                return False
            
            # Parse timestamp and verify it's from today (after midnight today)
            log_time = parse_log_timestamp(line)
            if log_time:
                return log_time >= today_start
            else:
                # If we can't parse timestamp but it starts with today's date, include it
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
                    # Check if file still exists and hasn't been rotated
                    if not log_file.exists():
                        # File might have been rotated, find the latest one
                        if logs_dir.exists():
                            log_files = sorted(logs_dir.glob("vofc_processor_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
                            if log_files:
                                log_file = log_files[0]
                                last_position = 0  # Reset position for new file
                                # Update today start for new day
                                session_start_time = now_est()
                                today_start = session_start_time.replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    if log_file.exists():
                        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(last_position)
                            new_lines = f.readlines()
                            
                            if new_lines:
                                # Filter to only today's lines
                                for line in new_lines:
                                    cleaned = line.strip()
                                    # Only send today's lines
                                    if is_today_log(cleaned):
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
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"  # Disable nginx buffering
    response.headers["Access-Control-Allow-Origin"] = "*"  # Allow CORS for SSE
    response.headers["Access-Control-Allow-Headers"] = "Cache-Control"
    return response

@system_bp.route('/api/system/logs')
def get_logs():
    """Get recent log lines from VOFC Processor (for polling fallback) - NEW VERSION with strict filtering."""
    try:
        import os
        from pathlib import Path
        from datetime import datetime, timedelta
        
        # Use VOFC Processor log file
        base_dir = Path(os.getenv("VOFC_DATA_DIR", r"C:\Tools\Ollama\Data"))
        if not base_dir.exists():
            # Fallback to archive location if needed (for migration)
            archive_data = Path(r"C:\Tools\archive\VOFC\Data")
            if archive_data.exists():
                base_dir = archive_data
            else:
                base_dir = Path(r"C:\Tools\Ollama\Data")  # Default
        
        logs_dir = base_dir / "logs"
        today = now_est().strftime("%Y%m%d")
        log_file = logs_dir / f"vofc_processor_{today}.log"
        
        # Always prefer today's log file - don't fallback to old files
        if not log_file.exists():
            # Return empty if today's log doesn't exist yet
            return jsonify({"lines": [], "error": f"Today's log file not found: {log_file}. The watcher may not have started yet."}), 200
        
        tail = request.args.get('tail', 50, type=int)
        
        # Show all logs from today (not just last 1 hour) - user wants to see today's activity
        today_date_str = now_est().strftime("%Y-%m-%d")
        today_start = now_est().replace(hour=0, minute=0, second=0, microsecond=0)
        
        def parse_log_timestamp(line):
            """Parse timestamp from log line. Returns None if parsing fails."""
            try:
                # Log format: "2025-11-12 12:38:35 | INFO | ..."
                if '|' in line:
                    timestamp_str = line.split('|')[0].strip()
                    # Try parsing the timestamp
                    log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    # Convert to EST if needed
                    if EST:
                        log_time = EST.localize(log_time) if log_time.tzinfo is None else log_time.astimezone(EST)
                    return log_time
            except (ValueError, IndexError):
                pass
            return None
        
        def is_today_log(line):
            """Check if log line is from today."""
            if not line or not line.strip():
                return False
            
            line_stripped = line.strip()
            
            # Must start with today's date
            if not line_stripped.startswith(today_date_str):
                return False
            
            # Parse timestamp and verify it's from today (after midnight today)
            log_time = parse_log_timestamp(line_stripped)
            if log_time:
                return log_time >= today_start
            else:
                # If we can't parse timestamp but it starts with today's date, include it
                return True
        
        # Read lines and filter to only show today's logs
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            # Filter to only today's lines
            today_lines = []
            for line in lines:
                line_stripped = line.strip()
                if is_today_log(line_stripped):
                    today_lines.append(line_stripped)
            
            # Return last N lines
            result_lines = today_lines[-tail:] if len(today_lines) > tail else today_lines
        
        return jsonify({"lines": result_lines}), 200
    except Exception as e:
        import logging
        logging.error(f"Error reading logs: {e}")
        return jsonify({"lines": [], "error": str(e)}), 200

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
        
        BASE_DIR = Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))
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
                from services.folder_watcher import start_folder_watcher
                # Start watcher in background thread
                start_folder_watcher()
                msg = "Watcher started"
            except Exception as e:
                logging.error(f"Error starting watcher: {e}")
                msg = f"Start watcher error: {str(e)}"
        
        elif action == "stop_watcher":
            try:
                from services.folder_watcher import stop_folder_watcher
                stop_folder_watcher()
                msg = "Watcher stopped"
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
                query = supabase.table('submissions').select('id, status, created_at, updated_at').eq('status', 'rejected')
                
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
                                
                                # Delete submission_vulnerability_ofc_links
                                supabase.table('submission_vulnerability_ofc_links').delete().eq('submission_id', submission_id).execute()
                                
                                # Delete submission_ofc_sources
                                supabase.table('submission_ofc_sources').delete().eq('submission_id', submission_id).execute()
                                
                                # Delete submission_options_for_consideration
                                supabase.table('submission_options_for_consideration').delete().eq('submission_id', submission_id).execute()
                                
                                # Delete submission_vulnerabilities
                                supabase.table('submission_vulnerabilities').delete().eq('submission_id', submission_id).execute()
                                
                                # Delete submission_sources
                                supabase.table('submission_sources').delete().eq('submission_id', submission_id).execute()
                                
                                # Finally, delete the main submission
                                delete_result = supabase.table('submissions').delete().eq('id', submission_id).execute()
                                
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
                        msg = f"PSA-Processor service is running and will automatically process {file_count} file(s) in incoming/ directory. Processing happens continuously every 30 seconds."
                    else:
                        msg = "PSA-Processor service is running. No files found in incoming/ directory. Files will be processed automatically when added."
                else:
                    msg = f"PSA-Processor service is {service_status}. Please start the service to process files. Files found: {file_count}"
                    logging.warning(f"[Admin Control] {msg}")
                
                logging.info(f"[Admin Control] {msg}")
            except Exception as e:
                import traceback
                error_msg = f"Error checking processing status: {e}"
                logging.error(f"[Admin Control] {error_msg}")
                logging.error(f"[Admin Control] Traceback: {traceback.format_exc()}")
                msg = f"Process existing check error: {str(e)}"
        
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
        res = supabase.table("disciplines").select("id, name, category").eq("is_active", True).execute()
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
        res = supabase.table("sectors").select("id, sector_name").eq("is_active", True).execute()
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
        res = supabase.table("subsectors").select("id, subsector_name").eq("is_active", True).execute()
        # Return as array directly (not wrapped) for compatibility with viewer
        return jsonify(res.data if res.data else []), 200
    except Exception as e:
        print(f"[Subsectors] Error: {str(e)}")
        # Return empty array on error to prevent viewer crashes
        return jsonify([]), 200

def get_tunnel_log_path():
    """Locate the most recent active tunnel log file."""
    possible_paths = [
        Path(r"C:\Tools\nssm\logs\vofc_tunnel.log"),
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
    
    try:
        path = get_tunnel_log_path()
        if not path:
            return jsonify({"error": "No tunnel log found", "lines": []}), 200  # Return 200 with empty lines
        
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.rstrip('\n\r') for line in f.readlines()[-100:]]
        
        return jsonify({
            "file": str(path),
            "lines": lines,
            "count": len(lines)
        }), 200
    except Exception as e:
        import logging
        logging.error(f"Error reading tunnel logs: {e}")
        return jsonify({
            "error": str(e),
            "lines": [],
            "file": None
        }), 200  # Return 200 to prevent frontend errors

