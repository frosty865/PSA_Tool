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

def test_tunnel_service():
    """
    Check if VOFC Tunnel Windows service is running.
    Returns 'ok' if running, 'offline' if stopped, 'unknown' if check fails.
    """
    # Try multiple possible service names
    service_names = ['VOFC-Tunnel', 'VOFC-Tunnel-Service', 'Cloudflare-Tunnel']
    
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
    Check if VOFC Model Manager Windows service is running.
    Returns 'online' if running, 'paused' if paused, 'offline' if stopped, 'unknown' if check fails.
    """
    # Try multiple possible service names
    service_names = ['VOFC-ModelManager', 'VOFC-Model-Manager', 'ModelManager']
    
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
    components = {
        "flask": "ok",
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
        
        # Get progress data
        progress_data = {}
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                progress_data = json.load(f)
        except FileNotFoundError:
            progress_data = {
                "status": "unknown", 
                "message": "progress.json not found",
                "incoming": 0,
                "processed": 0,
                "library": 0,
                "errors": 0,
                "review": 0
            }
        
        # Get watcher status by checking VOFC-Processor service and log file
        try:
            # Check if VOFC-Processor service is running
            import subprocess
            result = subprocess.run(
                ['sc', 'query', 'VOFC-Processor'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Check for RUNNING state (can be "STATE : 4  RUNNING" or just "RUNNING")
            service_running = 'RUNNING' in result.stdout.upper() and 'STOPPED' not in result.stdout.upper()
            # Also check for state code 4 (RUNNING)
            if not service_running:
                service_running = 'STATE' in result.stdout and ': 4' in result.stdout
            
            # Check log file for recent heartbeat (within last 60 seconds)
            watcher_active = False
            try:
                from pathlib import Path
                from datetime import datetime
                log_dir = Path(r"C:\Tools\Ollama\Data\logs")
                if not log_dir.exists():
                    log_dir = Path(r"C:\Tools\VOFC\Data\logs")
                
                if log_dir.exists():
                    log_file = log_dir / f"vofc_processor_{now_est().strftime('%Y%m%d')}.log"
                    if log_file.exists():
                        # Read last few lines to check for heartbeat
                        with open(log_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            # Check last 50 lines for heartbeat (more lines to catch recent heartbeats)
                            for line in reversed(lines[-50:]):
                                if 'Watcher heartbeat' in line or 'still monitoring' in line:
                                    # Extract timestamp from log line
                                    try:
                                        # Log format: "2025-11-13 10:18:19 | INFO | ..." (no milliseconds in local time format)
                                        if '|' in line:
                                            timestamp_str = line.split('|')[0].strip()
                                            # Try parsing with and without milliseconds
                                            try:
                                                log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                                            except ValueError:
                                                # Try with milliseconds
                                                try:
                                                    log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                                                except ValueError:
                                                    # Try with microseconds
                                                    log_time = datetime.strptime(timestamp_str.split(',')[0], '%Y-%m-%d %H:%M:%S')
                                            # Convert log_time to EST for comparison (assuming log is in EST)
                                            # If log_time is naive, assume it's EST
                                            if log_time.tzinfo is None:
                                                log_time = log_time.replace(tzinfo=EST) if EST else log_time
                                            now = now_est()
                                            diff_seconds = (now - log_time).total_seconds()
                                            # If heartbeat is within last 90 seconds, watcher is active (30s interval + buffer)
                                            if diff_seconds < 90:
                                                watcher_active = True
                                                logging.debug(f"Found recent watcher heartbeat: {timestamp_str} ({diff_seconds:.1f}s ago)")
                                                break
                                    except Exception as parse_err:
                                        logging.debug(f"Could not parse timestamp from log line: {line[:100]} - {parse_err}")
                                        pass
            except Exception as log_error:
                logging.debug(f"Could not check log file for watcher status: {log_error}")
            
            # Determine status: running if service is running AND recent heartbeat found
            if service_running and watcher_active:
                progress_data["watcher_status"] = "running"
            elif service_running:
                # Service is running but no recent heartbeat - check if log file exists and is readable
                log_file = log_dir / f"vofc_processor_{now_est().strftime('%Y%m%d')}.log"
                if log_file.exists():
                    # Log file exists but no heartbeat found - might be starting up or log format issue
                    progress_data["watcher_status"] = "unknown"
                    logging.debug(f"Service running but no recent heartbeat found in {log_file}")
                else:
                    # Log file doesn't exist yet - service might be starting
                    progress_data["watcher_status"] = "unknown"
            else:
                progress_data["watcher_status"] = "stopped"
        except Exception as e:
            logging.warning(f"Could not get watcher status: {e}")
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
            "processed": 0,
            "library": 0,
            "errors": 0,
            "review": 0,
            "watcher_status": "unknown"
        }), 200

@system_bp.route('/api/system/logstream', methods=['GET', 'OPTIONS'])
def log_stream():
    """Server-Sent Events streaming of live VOFC Processor log."""
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
        from datetime import datetime
        
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
        
        try:
            # First, send last 50 lines from today for context
            today_date_str = now_est().strftime("%Y-%m-%d")
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    # Filter to only today's lines and send last 50
                    today_lines = [line.strip() for line in lines if line.strip() and line.strip().startswith(today_date_str)]
                    for line in today_lines[-50:]:
                        if line:
                            yield f"data: {line}\n\n"
            
            # Then stream new lines - tail the file in real-time
            last_position = 0
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(0, 2)  # Seek to end
                    last_position = f.tell()
            
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
                    
                    if log_file.exists():
                        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                            f.seek(last_position)
                            new_lines = f.readlines()
                            
                            if new_lines:
                                # Filter to only today's lines
                                today_date_str = now_est().strftime("%Y-%m-%d")
                                for line in new_lines:
                                    cleaned = line.strip()
                                    # Only send lines from today
                                    if cleaned and cleaned.startswith(today_date_str):
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
    """Get recent log lines from VOFC Processor (for polling fallback)."""
    try:
        import os
        from pathlib import Path
        from datetime import datetime
        
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
        
        # Read lines and filter to only show today's logs
        today_date_str = now_est().strftime("%Y-%m-%d")
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            # Filter to only lines from today (check timestamp in log line)
            today_lines = []
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                # Check if line starts with today's date (log format: "2025-11-13 10:35:19 | ...")
                if line_stripped.startswith(today_date_str):
                    today_lines.append(line_stripped)
            
            # Return last N lines from today
            recent_lines = today_lines[-tail:] if len(today_lines) > tail else today_lines
        
        return jsonify({"lines": recent_lines}), 200
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
                # Note: sync_review functionality moved to VOFC-Processor service
                msg = "Review sync is handled by VOFC-Processor service. Use the service logs to monitor sync status."
                logging.warning(f"[Admin Control] sync_review: {msg}")
            except Exception as e:
                logging.error(f"Error in sync_review: {e}")
                msg = f"Sync error: {str(e)}"
        
        elif action == "sync_review_to_submissions":
            try:
                # Note: sync_review_to_submissions functionality moved to VOFC-Processor service
                msg = "Review files sync is handled by VOFC-Processor service."
                logging.warning(f"[Admin Control] sync_review_to_submissions: {msg}")
            except Exception as e:
                logging.error(f"Error in sync_review_to_submissions: {e}")
                msg = f"Sync error: {str(e)}"
        
        elif action == "clear_processed_tracking":
            try:
                # Note: Processed tracking is no longer used - VOFC-Processor handles deduplication
                msg = "Processed file tracking is deprecated. VOFC-Processor uses Supabase for deduplication."
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
                
                # Check if VOFC-Processor service is running
                try:
                    import subprocess
                    result = subprocess.run(
                        ['nssm', 'status', 'VOFC-Processor'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0 and 'SERVICE_RUNNING' in result.stdout:
                        service_status = "running"
                    else:
                        service_status = "not running"
                except:
                    service_status = "unknown"
                
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

