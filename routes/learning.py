"""
Learning API Routes
Handles analyst feedback and learning event recording.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging
from services.supabase_client import insert_learning_event

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

learning_bp = Blueprint("learning", __name__)


@learning_bp.route("/api/learning/event", methods=["POST"])
def record_learning_event():
    """
    Store a learning feedback event in Supabase.
    
    Request Body (JSON):
    {
        "submission_id": "uuid" (optional),
        "record_id": "uuid" (optional, alternative to submission_id),
        "event_type": "approval" | "rejection" | "correction" | "edited",
        "approved": true | false,
        "model_version": "psa-engine:latest" (optional),
        "confidence_score": 0.85 (optional, 0.0-1.0),
        "metadata": {} (optional, JSON object)
    }
    
    Returns:
        JSON response with status and event details
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Missing request body",
                "status": "error"
            }), 400
        
        # Validate required fields
        if "event_type" not in data:
            return jsonify({
                "error": "Missing required field: event_type",
                "status": "error"
            }), 400
        
        # Validate event_type
        valid_event_types = ["approval", "rejection", "correction", "edited"]
        if data["event_type"] not in valid_event_types:
            return jsonify({
                "error": f"Invalid event_type. Must be one of: {', '.join(valid_event_types)}",
                "status": "error"
            }), 400
        
        # Build event data
        event_data = {
            "event_type": data["event_type"],
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Handle submission_id or record_id
        if "submission_id" in data:
            event_data["submission_id"] = data["submission_id"]
        elif "record_id" in data:
            event_data["submission_id"] = data["record_id"]  # Use record_id as submission_id
        
        # Handle approved field (derive from event_type if not provided)
        if "approved" in data:
            event_data["approved"] = bool(data["approved"])
        else:
            # Auto-set based on event_type
            event_data["approved"] = data["event_type"] == "approval"
        
        # Optional fields
        if "model_version" in data:
            event_data["model_version"] = data["model_version"]
        else:
            # Default model version
            event_data["model_version"] = "psa-engine:latest"
        
        if "confidence_score" in data:
            confidence = float(data["confidence_score"])
            if 0.0 <= confidence <= 1.0:
                event_data["confidence_score"] = confidence
            else:
                logger.warning(f"Invalid confidence_score {confidence}, ignoring")
        
        if "metadata" in data:
            event_data["metadata"] = data["metadata"]
        
        # Insert learning event
        result = insert_learning_event(event_data)
        
        if result:
            return jsonify({
                "status": "recorded",
                "event_type": data["event_type"],
                "event_id": result.get("id"),
                "message": "Learning event recorded successfully"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "error": "Failed to record learning event"
            }), 500
            
    except Exception as e:
        logger.error(f"Error recording learning event: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@learning_bp.route("/api/learning/stats", methods=["GET"])
def get_learning_stats():
    """
    Get learning statistics (requires learning_stats table).
    
    Query Parameters:
    - limit: Number of recent stats to return (default: 10)
    
    Returns:
        JSON response with learning statistics
    """
    try:
        from services.supabase_client import get_supabase_client
        
        limit = int(request.args.get("limit", 10))
        
        client = get_supabase_client()
        
        # Try to get learning stats (table may not exist)
        try:
            # Order by timestamp descending (most recent first)
            # Note: Supabase Python client uses desc parameter
            result = client.table("learning_stats").select("*").order("timestamp", desc=True).limit(limit).execute()
            
            if result.data:
                return jsonify({
                    "status": "ok",
                    "stats": result.data,
                    "count": len(result.data)
                }), 200
            else:
                return jsonify({
                    "status": "ok",
                    "stats": [],
                    "count": 0,
                    "message": "No learning statistics available"
                }), 200
                
        except Exception as e:
            # Table doesn't exist or other error
            return jsonify({
                "status": "error",
                "error": "Learning stats table not available",
                "message": str(e)
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting learning stats: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@learning_bp.route("/api/learning/heuristics", methods=["GET"])
def get_heuristics():
    """
    Get current heuristic parameters (confidence thresholds).
    
    Returns:
        JSON response with current heuristic configuration
    """
    try:
        from services.heuristics import load_heuristics_config
        
        config = load_heuristics_config()
        
        return jsonify({
            "status": "ok",
            "heuristics": {
                "confidence_threshold": config.get("confidence_threshold"),
                "high_confidence_threshold": config.get("high_confidence_threshold"),
                "last_updated": config.get("last_updated"),
                "accept_rate": config.get("accept_rate")
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting heuristics: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

