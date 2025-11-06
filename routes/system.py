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
from datetime import datetime
from pathlib import Path

system_bp = Blueprint('system', __name__)

# Get Supabase client for lightweight routes
supabase = get_supabase_client()

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
        "supabase": test_supabase()
    }
    
    # Check Ollama - use service function
    ollama_status = test_ollama()
    components["ollama"] = ollama_status if ollama_status in ["ok", "offline", "error"] else "offline"
    
    # Get tunnel URL (managed by NSSM service - Cloudflare tunnel)
    tunnel_url = os.getenv('TUNNEL_URL', 'https://flask.frostech.site')
    
    # Check tunnel connectivity by attempting to reach the health endpoint through the tunnel
    tunnel_status = "unknown"
    try:
        import requests
        # Try to reach Flask through the tunnel (quick check with short timeout)
        tunnel_health_url = f"{tunnel_url}/api/health"
        tunnel_response = requests.get(tunnel_health_url, timeout=3)
        if tunnel_response.status_code == 200:
            tunnel_status = "ok"
        else:
            tunnel_status = "error"
    except Exception as e:
        # Tunnel check failed - could be tunnel down or network issue
        tunnel_status = "error"
    
    # Return lightweight response with service metadata
    return jsonify({
        "flask": components["flask"],
        "ollama": components["ollama"],
        "supabase": components["supabase"],
        "tunnel": tunnel_status,  # Tunnel is externally managed by NSSM
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
    """Get progress from Ollama automation progress.json file"""
    try:
        import os
        from pathlib import Path
        
        # Use same path as auto-processor
        base_dir = Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))
        progress_file = base_dir / "automation" / "progress.json"
        
        with open(progress_file, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({
            "status": "unknown", 
            "message": "progress.json not found",
            "timestamp": datetime.now().isoformat(),
            "incoming": 0,
            "processed": 0,
            "library": 0,
            "errors": 0,
            "review": 0
        }), 200  # Return 200 with default values instead of 404
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
            "review": 0
        }), 200

@system_bp.route('/api/system/logstream', methods=['GET', 'OPTIONS'])
def log_stream():
    """Server-Sent Events streaming of live processor log."""
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
        
        # Use same path as auto-processor
        base_dir = Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))
        log_file = base_dir / "automation" / "vofc_auto_processor.log"
        
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
    """Get recent log lines (for polling fallback)."""
    try:
        import os
        from pathlib import Path
        
        base_dir = Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))
        log_file = base_dir / "automation" / "vofc_auto_processor.log"
        
        tail = request.args.get('tail', 50, type=int)
        
        if not log_file.exists():
            return jsonify({"lines": [], "error": "Log file not found"}), 200
        
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
                from ollama_auto_processor import sync_review_to_supabase
                sync_review_to_supabase()
                msg = "Review sync triggered"
            except Exception as e:
                logging.error(f"Error in sync_review: {e}")
                msg = f"Sync error: {str(e)}"
        
        elif action == "start_watcher":
            try:
                from ollama_auto_processor import start_folder_watcher
                # Start watcher in background thread
                watcher_thread = threading.Thread(target=start_folder_watcher, daemon=True)
                watcher_thread.start()
                msg = "Watcher started"
            except Exception as e:
                logging.error(f"Error starting watcher: {e}")
                msg = f"Start watcher error: {str(e)}"
        
        elif action == "stop_watcher":
            try:
                # Flag file to halt watcher loop gracefully
                stop_file = AUTOMATION_DIR / "watcher.stop"
                stop_file.parent.mkdir(parents=True, exist_ok=True)
                with open(stop_file, "w") as f:
                    f.write("1")
                msg = "Watcher stop signal written"
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
        
        elif action == "process_existing":
            try:
                from ollama_auto_processor import get_incoming_files, process_file
                import traceback
                
                INCOMING_DIR = BASE_DIR / "incoming"
                logging.info(f"[Admin Control] process_existing: Checking {INCOMING_DIR}")
                
                existing_files = get_incoming_files()
                logging.info(f"[Admin Control] Found {len(existing_files)} file(s) to process")
                
                if not existing_files:
                    msg = "No files found in incoming/ directory"
                    logging.info(f"[Admin Control] {msg}")
                else:
                    processed = 0
                    failed = 0
                    for filepath in existing_files:
                        try:
                            logging.info(f"[Admin Control] Processing {filepath.name}...")
                            process_file(filepath)
                            processed += 1
                            logging.info(f"[Admin Control] Successfully processed {filepath.name}")
                        except Exception as e:
                            failed += 1
                            error_msg = f"Error processing {filepath.name}: {e}"
                            logging.error(f"[Admin Control] {error_msg}")
                            logging.error(f"[Admin Control] Traceback: {traceback.format_exc()}")
                    
                    msg = f"Processed {processed} file(s), {failed} failed from incoming/"
                    logging.info(f"[Admin Control] {msg}")
            except Exception as e:
                import traceback
                error_msg = f"Error processing existing files: {e}"
                logging.error(f"[Admin Control] {error_msg}")
                logging.error(f"[Admin Control] Traceback: {traceback.format_exc()}")
                msg = f"Process existing error: {str(e)}"
        
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

