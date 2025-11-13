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
from datetime import datetime
from pathlib import Path

system_bp = Blueprint('system', __name__)

# Get Supabase client for lightweight routes
supabase = get_supabase_client()

def test_tunnel_service():
    """
    Check if VOFC Tunnel Windows service is running.
    Returns 'ok' if running, 'offline' if stopped, 'unknown' if check fails.
    """
    try:
        # Use sc query to check service status (works on Windows)
        result = subprocess.run(
            ['sc', 'query', 'VOFC-Tunnel'],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode == 0:
            output = result.stdout
            # Check if service is running
            if 'RUNNING' in output:
                return 'ok'
            elif 'STOPPED' in output or 'STOP_PENDING' in output:
                return 'offline'
            else:
                return 'unknown'
        else:
            # Service might not exist or access denied
            return 'unknown'
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # sc command not available or timeout
        return 'unknown'

def test_model_manager():
    """
    Check if VOFC Model Manager Windows service is running.
    Returns 'ok' if running, 'offline' if stopped, 'unknown' if check fails.
    """
    try:
        # Use sc query to check service status (works on Windows)
        result = subprocess.run(
            ['sc', 'query', 'VOFC-ModelManager'],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode == 0:
            output = result.stdout
            # Check if service is running
            if 'RUNNING' in output:
                return 'ok'
            elif 'PAUSED' in output or 'PAUSE_PENDING' in output:
                # Service is paused - try to resume it automatically
                try:
                    resume_result = subprocess.run(
                        ['nssm', 'resume', 'VOFC-ModelManager'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if resume_result.returncode == 0:
                        # Give it a moment, then check again
                        import time
                        time.sleep(1)
                        # Re-check status
                        recheck = subprocess.run(
                            ['sc', 'query', 'VOFC-ModelManager'],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if 'RUNNING' in recheck.stdout:
                            return 'ok'
                except:
                    pass  # If resume fails, continue to return 'offline'
                return 'offline'  # Paused services are treated as offline
            elif 'STOPPED' in output or 'STOP_PENDING' in output:
                return 'offline'
            else:
                return 'unknown'
        else:
            # Service might not exist or access denied
            return 'unknown'
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # sc command not available or timeout
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
        log_path = r"C:\Tools\VOFC_Logs\model_manager.log"
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
        "timestamp": datetime.now().isoformat()
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
        
        # Get watcher status from new module
        try:
            from services.folder_watcher import get_watcher_status
            progress_data["watcher_status"] = get_watcher_status()
        except Exception as e:
            logging.warning(f"Could not get watcher status: {e}")
            progress_data["watcher_status"] = "unknown"
        
        # Ensure timestamp exists
        if "timestamp" not in progress_data:
            progress_data["timestamp"] = datetime.now().isoformat()
        
        return jsonify(progress_data)
    except Exception as e:
        import logging
        logging.error(f"Error reading progress.json: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
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
            base_dir = Path(r"C:\Tools\VOFC\Data")
        
        logs_dir = base_dir / "logs"
        today = datetime.now().strftime("%Y%m%d")
        log_file = logs_dir / f"vofc_processor_{today}.log"
        
        # Fallback to most recent log file if today's doesn't exist
        if not log_file.exists() and logs_dir.exists():
            log_files = sorted(logs_dir.glob("vofc_processor_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            if log_files:
                log_file = log_files[0]
        
        try:
            # First, send last 50 lines for context
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    # Send last 50 lines
                    for line in lines[-50:]:
                        cleaned = line.strip()
                        if cleaned:
                            yield f"data: {cleaned}\n\n"
            
            # Then stream new lines
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                # Start at end of file for new lines only
                f.seek(0, 2)
                
                while True:
                    line = f.readline()
                    if line:
                        # Clean and send line
                        cleaned = line.strip()
                        if cleaned:
                            yield f"data: {cleaned}\n\n"
                    else:
                        # No new line, wait a bit
                        time.sleep(1)
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
            base_dir = Path(r"C:\Tools\VOFC\Data")
        
        logs_dir = base_dir / "logs"
        today = datetime.now().strftime("%Y%m%d")
        log_file = logs_dir / f"vofc_processor_{today}.log"
        
        # Fallback to most recent log file if today's doesn't exist
        if not log_file.exists() and logs_dir.exists():
            log_files = sorted(logs_dir.glob("vofc_processor_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            if log_files:
                log_file = log_files[0]
        
        tail = request.args.get('tail', 50, type=int)
        
        if not log_file.exists():
            return jsonify({"lines": [], "error": f"Log file not found: {log_file}"}), 200
        
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            recent_lines = [line.strip() for line in lines[-tail:] if line.strip()]
        
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

