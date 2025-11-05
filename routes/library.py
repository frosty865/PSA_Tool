"""
PSA Library routes
Routes: /api/library/*
"""

from flask import Blueprint, jsonify, request
from services.processor import search_library, get_library_entry

library_bp = Blueprint('library', __name__)

@library_bp.route('/api/library/search', methods=['GET', 'POST', 'OPTIONS'])
def search_library_route():
    """Search the PSA library"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if request.method == 'POST':
            data = request.get_json()
            query = data.get('query', '') or data.get('q', '')
        else:
            query = request.args.get('query', '') or request.args.get('q', '')
        
        if not query:
            return jsonify({
                "success": False,
                "error": "query parameter required",
                "results": [],
                "service": "PSA Processing Server"
            }), 400
        
        results = search_library(query)
        return jsonify({
            "success": True,
            **results,
            "service": "PSA Processing Server"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "results": [],
            "service": "PSA Processing Server"
        }), 500

@library_bp.route('/api/library/entry', methods=['GET'])
def get_entry():
    """Get a specific library entry"""
    try:
        entry_id = request.args.get('id')
        if not entry_id:
            return jsonify({
                "success": False,
                "error": "id parameter required",
                "service": "PSA Processing Server"
            }), 400
        
        entry = get_library_entry(entry_id)
        return jsonify({
            "success": True,
            "entry": entry,
            "service": "PSA Processing Server"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500

# Add more library routes as needed from your old server.py

