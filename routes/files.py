"""
File management routes
Routes: /api/files/*
"""

from flask import Blueprint, jsonify, request, send_file
from services.processor import list_incoming_files, get_file_info, move_file, write_file_to_folder
import os

files_bp = Blueprint('files', __name__)

@files_bp.route('/api/files/list', methods=['GET'])
def list_files():
    """List all files in incoming directory"""
    try:
        files = list_incoming_files()
        return jsonify({
            "success": True,
            "files": files,
            "service": "PSA Processing Server"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "files": [],
            "service": "PSA Processing Server"
        }), 500

@files_bp.route('/api/files/info', methods=['GET'])
def file_info():
    """Get information about a specific file"""
    try:
        filename = request.args.get('filename')
        if not filename:
            return jsonify({
                "success": False,
                "error": "filename parameter required",
                "service": "PSA Processing Server"
            }), 400
        
        info = get_file_info(filename)
        return jsonify({
            "success": True,
            "info": info,
            "service": "PSA Processing Server"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500

@files_bp.route('/api/files/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download a file from incoming directory"""
    try:
        from services.processor import INCOMING_DIR
        filename = os.path.basename(filename)
        filepath = os.path.join(INCOMING_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({
                "error": "File not found",
                "service": "PSA Processing Server"
            }), 404
        return send_file(filepath, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500

@files_bp.route('/api/files/write', methods=['POST'])
def write_file():
    """Write content to a file in specified folder"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        content = data.get('content')
        folder = data.get('folder', 'processed')
        
        result = write_file_to_folder(filename, content, folder)
        return jsonify({
            "success": True,
            **result,
            "service": "PSA Processing Server"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500

