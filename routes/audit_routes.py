"""
VOFC API Endpoint – Phase 3 Audit History
Returns audit trail entries from phase3_history for dashboard visibility.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from services.supabase_client import get_supabase_client
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def log_info(msg: str):
    """Log info message"""
    logger.info(msg)

def log_error(msg: str):
    """Log error message"""
    logger.error(msg)

audit_bp = Blueprint("audit", __name__)

@audit_bp.route("/api/audit/history", methods=["GET"])
def get_audit_history():
    """
    Get audit history from phase3_history table.
    
    Query parameters:
      ?limit=50
      ?offset=0
      ?submission_id=<uuid>
      ?model_version=<text>
      ?start_date=YYYY-MM-DD
      ?end_date=YYYY-MM-DD
    """
    try:
        supabase = get_supabase_client()
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))

        # Base query
        query = supabase.table("phase3_history").select("*").order("changed_at", desc=True)

        # Filters
        if submission_id := request.args.get("submission_id"):
            query = query.eq("submission_vuln_id", submission_id)

        if model_version := request.args.get("model_version"):
            query = query.eq("model_version", model_version)

        if start_date := request.args.get("start_date"):
            query = query.gte("changed_at", f"{start_date}T00:00:00Z")

        if end_date := request.args.get("end_date"):
            query = query.lte("changed_at", f"{end_date}T23:59:59Z")

        # Pagination
        query = query.range(offset, offset + limit - 1)

        res = query.execute()
        rows = res.data or []
        log_info(f"[API] Returned {len(rows)} phase3_history entries.")

        return jsonify({
            "count": len(rows),
            "limit": limit,
            "offset": offset,
            "data": rows
        }), 200

    except Exception as e:
        log_error(f"[API] /api/audit/history failed: {e}")
        import traceback
        log_error(f"[API] Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

