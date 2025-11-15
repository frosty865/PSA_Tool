"""
Disciplines routes
Routes: /api/disciplines
"""

from flask import Blueprint, jsonify, request
from services.supabase_client import get_supabase_client

bp = Blueprint("disciplines", __name__, url_prefix="/api/disciplines")


@bp.route("/", methods=["GET"])
def get_disciplines():
    """Get all disciplines from database"""
    try:
        # Get query parameters
        category = request.args.get("category")
        active = request.args.get("active")
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Build query - include subtypes
        query = supabase.table("disciplines").select("*, discipline_subtypes(id, name, description, code, is_active)").order("category, name")
        
        # Apply filters
        if category:
            query = query.eq("category", category)
        
        if active is not None:
            query = query.eq("is_active", active.lower() == "true")
        
        # Execute query
        result = query.execute()
        
        return jsonify({
            "success": True,
            "disciplines": result.data or []
        }), 200
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route("/<int:discipline_id>", methods=["GET"])
def get_discipline(discipline_id):
    """Get a specific discipline by ID"""
    try:
        supabase = get_supabase_client()
        result = supabase.table("disciplines").select("*").eq("id", discipline_id).execute()
        
        if not result.data:
            return jsonify({
                "success": False,
                "error": "Discipline not found"
            }), 404
        
        return jsonify({
            "success": True,
            "discipline": result.data[0]
        }), 200
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

