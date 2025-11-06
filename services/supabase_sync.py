"""
Supabase Sync Layer

Uploads processed results (JSON) into Supabase submission tables
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path

try:
    from supabase import create_client, Client
except ImportError:
    raise ImportError("supabase-py package not installed. Install with: pip install supabase")

# Get Supabase credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").rstrip('/')
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def sync_processed_result(result_path: str, submitter_email: str = "system@psa.local"):
    """
    Upload parsed JSON result into Supabase submission tables.
    
    Args:
        result_path: Path to the processed JSON result file
        submitter_email: Email of the submitter (default: system@psa.local)
    
    Returns:
        submission_id: UUID of the created submission
    """
    # Read the result file
    result_file = Path(result_path)
    if not result_file.exists():
        raise FileNotFoundError(f"Result file not found: {result_path}")
    
    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Handle different result formats
    # If result is a string (from Ollama), try to parse it as JSON
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            # If it's not JSON, wrap it in a structure
            data = {
                "vulnerabilities": [],
                "ofcs": [],
                "sources": [],
                "raw_response": data,
                "parser_version": "psa-engine:latest"
            }
    
    # 1. Create submission record
    submission_id = str(uuid.uuid4())
    submission_data = {
        "id": submission_id,
        "type": "document",
        "status": "pending_review",
        "source": "psa_tool_auto",
        "submitter_email": submitter_email,
        "submitted_by": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "data": data,  # Store full result as JSON
    }
    
    try:
        supabase.table("submissions").insert(submission_data).execute()
    except Exception as e:
        raise Exception(f"Failed to create submission record: {str(e)}")
    
    # 2. Extract and insert vulnerabilities
    vulnerabilities = data.get("vulnerabilities", [])
    if not isinstance(vulnerabilities, list):
        vulnerabilities = []
    
    for v in vulnerabilities:
        if not isinstance(v, dict):
            continue
        
        vrec = {
            "id": str(uuid.uuid4()),
            "submission_id": submission_id,
            "vulnerability": v.get("text") or v.get("vulnerability") or v.get("title") or str(v),
            "discipline": v.get("discipline") or v.get("category") or None,
            "sector": v.get("sector") or None,
            "subsector": v.get("subsector") or None,
            "source": v.get("source") or None,
            "source_title": v.get("source_title") or None,
            "source_url": v.get("source_url") or None,
            "parser_version": data.get("parser_version", "psa-engine:latest"),
            "parsed_at": datetime.utcnow().isoformat(),
        }
        
        # Remove None values to avoid database errors
        vrec = {k: v for k, v in vrec.items() if v is not None}
        
        try:
            supabase.table("submission_vulnerabilities").insert(vrec).execute()
        except Exception as e:
            print(f"⚠️  Warning: Failed to insert vulnerability: {str(e)}")
            # Continue processing other vulnerabilities
    
    # 3. Extract and insert OFCs
    ofcs = data.get("ofcs") or data.get("options_for_consideration") or []
    if not isinstance(ofcs, list):
        ofcs = []
    
    for o in ofcs:
        if not isinstance(o, dict):
            continue
        
        orec = {
            "id": str(uuid.uuid4()),
            "submission_id": submission_id,
            "option_text": o.get("text") or o.get("option_text") or o.get("title") or str(o),
            "discipline": o.get("discipline") or o.get("category") or None,
            "confidence_score": float(o.get("confidence_score", 0.8)) if o.get("confidence_score") else None,
            "source": o.get("source") or None,
            "source_title": o.get("source_title") or None,
            "source_url": o.get("source_url") or None,
            "citations": json.dumps(o.get("citations", [])) if o.get("citations") else None,
        }
        
        # Remove None values
        orec = {k: v for k, v in orec.items() if v is not None}
        
        try:
            supabase.table("submission_options_for_consideration").insert(orec).execute()
        except Exception as e:
            print(f"⚠️  Warning: Failed to insert OFC: {str(e)}")
            # Continue processing other OFCs
    
    # 4. Insert sources if available
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        sources = []
    
    for s in sources:
        if not isinstance(s, dict):
            continue
        
        srec = {
            "id": str(uuid.uuid4()),
            "submission_id": submission_id,
            "source_text": s.get("text") or s.get("citation") or s.get("title") or str(s),
            "source_title": s.get("title") or None,
            "source_url": s.get("url") or s.get("source_url") or None,
            "author_org": s.get("author_org") or s.get("organization") or None,
            "publication_year": int(s.get("year")) if s.get("year") else None,
            "content_restriction": s.get("restriction") or s.get("content_restriction", "public"),
        }
        
        # Remove None values
        srec = {k: v for k, v in srec.items() if v is not None}
        
        try:
            supabase.table("submission_sources").insert(srec).execute()
        except Exception as e:
            print(f"⚠️  Warning: Failed to insert source: {str(e)}")
            # Continue processing other sources
    
    print(f"✅ Synced results to Supabase for submission {submission_id}")
    return submission_id

