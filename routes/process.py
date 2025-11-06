"""
Document processing routes
Routes: /api/process/*
"""

import os
import json
import logging
from pathlib import Path
from flask import Blueprint, jsonify, request
from services.processor import process_file, process_document, INCOMING_DIR
from services.queue_manager import add_job, load_queue
from services.preprocess import preprocess_document
from services.ollama_client import run_model_on_chunks
from services.supabase_client import save_results

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@process_bp.route('/api/process', methods=['POST', 'OPTIONS'])
def process_upload():
    """
    Process uploaded file: preprocess → model inference → save to Supabase
    
    Accepts multipart/form-data with 'file' field
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Step 1: Get uploaded file
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "No file uploaded. Use 'file' field in multipart/form-data.",
                "service": "PSA Processing Server"
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "No file selected",
                "service": "PSA Processing Server"
            }), 400
        
        logger.info(f"Received file upload: {file.filename}")
        
        # Step 2: Save file to incoming directory
        # Use VOFC-Processor incoming directory if it exists, otherwise use project data/incoming
        incoming_dir = Path("C:/Tools/VOFC-Processor/incoming")
        if not incoming_dir.exists():
            # Fallback to project data/incoming
            incoming_dir = INCOMING_DIR
        
        incoming_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitize filename to prevent path traversal
        safe_filename = os.path.basename(file.filename)
        saved_path = incoming_dir / safe_filename
        
        # Save file
        file.save(str(saved_path))
        logger.info(f"File saved to: {saved_path}")
        
        # Step 3: Preprocess document into chunks
        try:
            logger.info(f"Starting preprocessing for {safe_filename}")
            chunks = preprocess_document(str(saved_path))
            logger.info(f"Preprocessing complete: {len(chunks)} chunks created")
        except Exception as e:
            logger.error(f"Preprocessing failed: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"Preprocessing failed: {str(e)}",
                "step": "preprocessing",
                "service": "PSA Processing Server"
            }), 500
        
        if not chunks:
            return jsonify({
                "success": False,
                "error": "No chunks created from document. Document may be empty or unreadable.",
                "service": "PSA Processing Server"
            }), 400
        
        # Step 4: Run model inference on chunks
        try:
            logger.info(f"Running model inference on {len(chunks)} chunks")
            results = run_model_on_chunks(chunks)
            logger.info(f"Model inference complete: {len(results)} results")
        except Exception as e:
            logger.error(f"Model inference failed: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"Model inference failed: {str(e)}",
                "step": "model_inference",
                "chunks_created": len(chunks),
                "service": "PSA Processing Server"
            }), 500
        
        # Step 5: Save results to Supabase
        try:
            logger.info(f"Saving {len(results)} results to Supabase")
            save_stats = save_results(results, source_file=safe_filename)
            logger.info(f"Supabase save complete: {save_stats}")
        except Exception as e:
            logger.error(f"Supabase save failed: {str(e)}")
            # Don't fail the entire request if Supabase save fails
            # Return results anyway but note the error
            save_stats = {
                "saved": 0,
                "errors": len(results),
                "error": str(e)
            }
        
        # Step 6: Return success response
        return jsonify({
            "success": True,
            "message": "File processed successfully",
            "file": safe_filename,
            "chunks": len(chunks),
            "results": len(results),
            "supabase": save_stats,
            "status": "ok",
            "service": "PSA Processing Server"
        }), 200
        
    except Exception as e:
        logger.exception(f"Unexpected error in process_upload: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Processing failed: {str(e)}",
            "service": "PSA Processing Server"
        }), 500

