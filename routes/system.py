"""
System routes for health checks and version info
Routes: /, /api/system/health, /api/version, /api/progress
"""

from flask import Blueprint, jsonify, request
from services.ollama_client import test_ollama
from services.supabase_client import test_supabase, get_supabase_client
import os
import json
from datetime import datetime

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
    tunnel_status = "managed"  # Tunnel is managed by NSSM, Flask doesn't control it
    
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
        with open(r"C:\Tools\Ollama\automation\progress.json", "r") as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"status": "unknown", "message": "progress.json not found"}), 404

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

