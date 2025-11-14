"""
Learning Event Logger

Records completed processing jobs into Supabase learning_events table
"""

import os
import json
import statistics
from datetime import datetime
from pathlib import Path

try:
    from supabase import create_client, Client
except ImportError:
    raise ImportError("supabase-py package not installed. Install with: pip install supabase")

# Get Supabase credentials from environment
from config import Config
SUPABASE_URL = Config.SUPABASE_URL or ""
SUPABASE_SERVICE_ROLE_KEY = Config.SUPABASE_SERVICE_ROLE_KEY

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def log_learning_event(submission_id: str, result_path: str, model_version: str = "psa-engine:latest"):
    """
    Create a learning_event record in Supabase.
    
    Args:
        submission_id: UUID of the submission created by sync
        result_path: Path to the processed JSON result file
        model_version: Model version used (default: psa-engine:latest)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result_file = Path(result_path)
        if not result_file.exists():
            print(f"[LearningLogger] Result file not found: {result_path}")
            return False
        
        with open(result_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[LearningLogger] Unable to read result JSON: {e}")
        return False
    
    # Handle different result formats
    # If result is a string (from Ollama), try to parse it as JSON
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            # If it's not JSON, create minimal metadata
            data = {
                "vulnerabilities": [],
                "options_for_consideration": [],
                "ofcs": [],
                "raw_response": data,
                "parser_version": model_version
            }
    
    # Try to calculate a representative confidence score
    # Check both 'options_for_consideration' and 'ofcs' keys
    confidences = []
    ofcs = data.get("options_for_consideration", []) or data.get("ofcs", [])
    
    for o in ofcs:
        if isinstance(o, dict):
            conf_score = o.get("confidence_score")
            if isinstance(conf_score, (int, float)):
                confidences.append(float(conf_score))
    
    # Calculate average confidence, default to None if no confidences found
    avg_confidence = None
    if confidences:
        try:
            avg_confidence = float(statistics.mean(confidences))
        except (statistics.StatisticsError, ValueError):
            avg_confidence = None
    
    # Build metadata
    vulnerabilities = data.get("vulnerabilities", [])
    if not isinstance(vulnerabilities, list):
        vulnerabilities = []
    
    metadata = {
        "vulnerability_count": len(vulnerabilities),
        "ofc_count": len(ofcs),
        "parser_version": data.get("parser_version", model_version),
        "file_name": os.path.basename(result_path)
    }
    
    # Create learning event record
    # Note: Supabase handles dict -> jsonb conversion automatically
    record = {
        "submission_id": submission_id,
        "event_type": "auto_parse",
        "approved": False,
        "model_version": model_version,
        "confidence_score": avg_confidence,
        "metadata": metadata if metadata else None,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # Remove None values to avoid database errors
    record = {k: v for k, v in record.items() if v is not None}
    
    try:
        supabase.table("learning_events").insert(record).execute()
        print(f"[LearningLogger] ✅ Logged learning_event for submission {submission_id}")
        return True
    except Exception as e:
        print(f"[LearningLogger] ⚠️  Failed to log learning_event: {e}")
        return False

