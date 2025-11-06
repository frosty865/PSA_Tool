"""
Document processing routes
Routes: /api/process/*
"""

from flask import Blueprint, jsonify, request
from services.processor import process_file, process_document
from services.queue_manager import add_job, load_queue

process_bp = Blueprint('process', __name__)

@process_bp.route('/api/process/start', methods=['POST', 'OPTIONS'])
def start_processing():
    """Start processing a file"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                "success": False,
                "error": "filename required",
                "service": "PSA Processing Server"
            }), 400
        
        result = process_file(filename)
        return jsonify({
            "success": True,
            "result": result,
            "service": "PSA Processing Server"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500

@process_bp.route('/api/process/document', methods=['POST', 'OPTIONS'])
def process_document_route():
    """Process a document (PDF, DOCX, etc.)"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        document_type = data.get('type', 'pdf')
        
        if not file_path:
            return jsonify({
                "success": False,
                "error": "file_path required",
                "service": "PSA Processing Server"
            }), 400
        
        result = process_document(file_path, document_type)
        return jsonify({
            "success": True,
            "result": result,
            "service": "PSA Processing Server"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500

@process_bp.route('/api/process/<filename>', methods=['GET', 'POST'])
def process_specific_file(filename):
    """Process a specific file by filename"""
    try:
        result = process_file(filename)
        return jsonify({
            "success": True,
            "result": result,
            "service": "PSA Processing Server"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500

@process_bp.route('/api/process/submit', methods=['POST'])
def submit_job():
    """Submit a file for processing (adds to queue)"""
    try:
        data = request.get_json()
        filename = data.get("filename")
        
        if not filename:
            return jsonify({
                "error": "filename required",
                "service": "PSA Processing Server"
            }), 400
        
        add_job(filename)
        return jsonify({
            "status": "queued",
            "filename": filename,
            "service": "PSA Processing Server"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500

@process_bp.route('/api/process/queue', methods=['GET'])
def get_queue():
    """Get current processing queue status"""
    try:
        queue = load_queue()
        return jsonify({
            "queue": queue,
            "service": "PSA Processing Server"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "queue": [],
            "service": "PSA Processing Server"
        }), 500

