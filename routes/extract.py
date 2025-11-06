"""
Document Extraction Routes
PHASE 2-5: Handles extraction pipeline for pending document submissions
"""

import os
import logging
from pathlib import Path
from flask import Blueprint, jsonify, request
from services.document_extractor import extract_from_document
from services.submission_saver import save_extraction_to_submission
from services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
extract_bp = Blueprint('extract', __name__)

@extract_bp.route('/api/documents/extract/<submission_id>', methods=['POST', 'OPTIONS'])
def extract_submission(submission_id):
    """
    PHASE 2-5: Extract vulnerabilities and OFCs from a pending document submission.
    
    Args:
        submission_id: UUID of submission with status='pending'
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        client = get_supabase_client()
        
        # Get submission record
        submission_result = client.table('submissions').select('*').eq('id', submission_id).single().execute()
        
        if not submission_result.data:
            return jsonify({
                "success": False,
                "error": f"Submission {submission_id} not found",
                "service": "PSA Processing Server"
            }), 404
        
        submission = submission_result.data
        
        # Check if submission is in pending status
        if submission.get('status') != 'pending':
            return jsonify({
                "success": False,
                "error": f"Submission {submission_id} is not in 'pending' status (current: {submission.get('status')})",
                "service": "PSA Processing Server"
            }), 400
        
        # Get file path from submission data
        data = submission.get('data', {})
        if isinstance(data, str):
            import json
            data = json.loads(data)
        
        filename = data.get('filename')
        if not filename:
            return jsonify({
                "success": False,
                "error": "No filename in submission data",
                "service": "PSA Processing Server"
            }), 400
        
        # Find file in incoming directory
        base_dir = Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))
        incoming_dir = base_dir / "incoming"
        file_path = incoming_dir / filename
        
        if not file_path.exists():
            return jsonify({
                "success": False,
                "error": f"File not found: {file_path}",
                "service": "PSA Processing Server"
            }), 404
        
        # Prepare source info from submission data
        source_info = {
            'source_title': data.get('source_title', filename),
            'source_type': data.get('source_type', 'unknown'),
            'url': data.get('url') or data.get('source_url'),
            'agency': data.get('agency') or data.get('author_org'),
            'publication_year': data.get('publication_year') or data.get('publication_date', '').split('-')[0] if data.get('publication_date') else None,
            'content_restriction': data.get('content_restriction', 'public'),
            'sector': 'Defense Installations',  # Default, can be inferred
            'subsector': 'Facilities Engineering'  # Default
        }
        
        # PHASE 2-5: Run extraction pipeline
        logger.info(f"Starting extraction for submission {submission_id}")
        extraction_results = extract_from_document(
            file_path=str(file_path),
            submission_id=submission_id,
            source_info=source_info
        )
        
        # Save extraction results to submission tables
        save_stats = save_extraction_to_submission(submission_id, extraction_results)
        
        # Update submission status to 'pending_review'
        from datetime import datetime
        client.table('submissions').update({
            'status': 'pending_review',
            'updated_at': datetime.now().isoformat()
        }).eq('id', submission_id).execute()
        
        return jsonify({
            "success": True,
            "message": "Extraction complete",
            "submission_id": submission_id,
            "extraction_stats": {
                "sections": extraction_results.get('sections', 0),
                "vulnerabilities": len(extraction_results.get('vulnerabilities', [])),
                "ofcs": len(extraction_results.get('ofcs', [])),
                "links": len(extraction_results.get('links', [])),
                "tables": extraction_results.get('tables', 0),
                "figures": extraction_results.get('figures', 0)
            },
            "save_stats": save_stats,
            "service": "PSA Processing Server"
        }), 200
        
    except Exception as e:
        logger.exception(f"Extraction failed for submission {submission_id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500

@extract_bp.route('/api/documents/extract-pending', methods=['POST', 'OPTIONS'])
def extract_all_pending():
    """
    Extract all pending document submissions.
    Finds all submissions with status='pending' and document_upload=true, then processes them.
    """
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        client = get_supabase_client()
        
        # Find all pending document submissions
        # Note: We need to filter by data->>'document_upload' = 'true'
        # This requires a more complex query
        result = client.table('submissions').select('*').eq('status', 'pending').execute()
        
        pending_submissions = []
        for sub in result.data or []:
            data = sub.get('data', {})
            if isinstance(data, str):
                import json
                try:
                    data = json.loads(data)
                except:
                    continue
            
            if data.get('document_upload') and sub.get('source') == 'document_upload':
                pending_submissions.append(sub)
        
        if not pending_submissions:
            return jsonify({
                "success": True,
                "message": "No pending document submissions found",
                "processed": 0,
                "service": "PSA Processing Server"
            }), 200
        
        processed = 0
        errors = []
        
        for submission in pending_submissions:
            try:
                # Call extract endpoint for each submission
                extract_result = extract_submission(submission['id'])
                if extract_result[1] == 200:  # Check status code
                    processed += 1
                else:
                    errors.append(f"{submission['id']}: {extract_result[0].get_json().get('error', 'Unknown error')}")
            except Exception as e:
                errors.append(f"{submission['id']}: {str(e)}")
        
        return jsonify({
            "success": True,
            "message": f"Processed {processed} of {len(pending_submissions)} pending submissions",
            "processed": processed,
            "total": len(pending_submissions),
            "errors": errors if errors else None,
            "service": "PSA Processing Server"
        }), 200
        
    except Exception as e:
        logger.exception(f"Failed to extract pending submissions: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500

