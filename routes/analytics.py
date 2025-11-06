"""
Analytics routes for dashboard metrics
Routes: /api/analytics/summary, /api/admin/export/learning-events
"""

from flask import Blueprint, jsonify, request
import json
import os
from datetime import datetime

try:
    from services.retraining_exporter import export_approved_events
except ImportError:
    export_approved_events = None

bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@bp.route("/summary", methods=["GET"])
def get_summary():
    """Get cached analytics summary from local JSON file."""
    path = os.path.join(os.path.dirname(__file__), "..", "data", "analytics.json")
    try:
        if not os.path.exists(path):
            return jsonify({"status": "pending", "message": "Analytics not ready"}), 202
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        data["retrieved_at"] = datetime.utcnow().isoformat()
        return jsonify(data)
    except json.JSONDecodeError as e:
        return jsonify({
            "error": "Invalid JSON in analytics file",
            "message": str(e),
            "path": path
        }), 500
    except Exception as e:
        return jsonify({
            "error": "Failed to load analytics summary",
            "message": str(e),
            "path": path
        }), 500


# Admin export route for retraining
@bp.route("/admin/export/learning-events", methods=["POST"])
def export_learning_events():
    """
    Export approved learning events to JSONL file for model retraining.
    Protected endpoint - should be called by admin users only.
    """
    if export_approved_events is None:
        return jsonify({"error": "Retraining exporter not available"}), 500
    
    try:
        # Get limit from request (optional, default 1000)
        limit = request.json.get("limit", 1000) if request.is_json else 1000
        limit = int(limit) if isinstance(limit, (int, str)) else 1000
        
        # Export approved events
        out_path = export_approved_events(limit=limit)
        
        # Return file path info (relative to data directory)
        rel_path = os.path.relpath(out_path, os.path.join(os.path.dirname(__file__), ".."))
        
        return jsonify({
            "success": True,
            "message": f"Exported {limit} approved events",
            "file_path": rel_path,
            "absolute_path": out_path,
            "exported_at": datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

