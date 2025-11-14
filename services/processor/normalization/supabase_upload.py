"""
Supabase Upload Module
Handles uploading extracted records to Supabase with deduplication.
"""
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from config.exceptions import ServiceError, ConfigurationError

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logging.warning("supabase library not available - uploads will be skipped")


def init_supabase() -> Optional[Client]:
    """Initialize Supabase client from centralized config."""
    if not SUPABASE_AVAILABLE:
        logging.warning("Supabase library not available - install with: pip install supabase")
        return None
    
    from config import Config
    
    # Check offline mode first
    if Config.SUPABASE_OFFLINE_MODE:
        logging.info("Supabase offline mode enabled - Supabase uploads will be skipped")
        return None
    
    supabase_url = Config.SUPABASE_URL
    # Check both SUPABASE_ANON_KEY and NEXT_PUBLIC_SUPABASE_ANON_KEY for compatibility
    supabase_key = Config.SUPABASE_ANON_KEY
    
    if not supabase_url:
        logging.warning("SUPABASE_URL or NEXT_PUBLIC_SUPABASE_URL environment variable not set - Supabase uploads will be skipped (set SUPABASE_OFFLINE_MODE=true to explicitly enable offline mode)")
        return None
    
    if not supabase_key:
        logging.warning("SUPABASE_ANON_KEY or NEXT_PUBLIC_SUPABASE_ANON_KEY environment variable not set - Supabase uploads will be skipped (set SUPABASE_OFFLINE_MODE=true to explicitly enable offline mode)")
        return None
    
    try:
        client = create_client(supabase_url, supabase_key)
        logging.debug(f"Supabase client initialized successfully (URL: {supabase_url[:30]}...)")
        return client
    except Exception as e:
        logging.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
        logging.error(f"  SUPABASE_URL: {'set' if supabase_url else 'not set'}")
        logging.error(f"  SUPABASE_ANON_KEY: {'set' if supabase_key else 'not set'}")
        # Return None for optional Supabase - caller should handle offline mode
        return None


def check_existing_vulnerability(supabase: Client, dedupe_key: str) -> Optional[str]:
    """
    Check if vulnerability exists in Supabase using dedupe_key.
    Returns vulnerability ID if found, None otherwise.
    """
    if not supabase:
        return None
    
    try:
        response = supabase.table("vulnerabilities").select("id").eq("dedupe_key", dedupe_key).limit(1).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get("id")
    except Exception as e:
        logging.debug(f"Could not check for existing vulnerability: {e}")
    
    return None


def normalize_confidence(value: Any) -> str:
    """Normalize confidence to High/Medium/Low."""
    if not value:
        return "Medium"
    value_str = str(value).strip().title()
    confidence_map = {
        "high": "High", "medium": "Medium", "low": "Low",
        "critical": "High", "severe": "High"
    }
    return confidence_map.get(value_str.lower(), "Medium")


def normalize_impact_level(value: Any) -> str:
    """Normalize impact_level to High/Moderate/Low."""
    if not value:
        return "Moderate"
    value_str = str(value).strip().title()
    impact_map = {
        "high": "High", "moderate": "Moderate", "low": "Low",
        "medium": "Moderate", "critical": "High", "severe": "High"
    }
    return impact_map.get(value_str.lower(), "Moderate")


def upload_to_supabase(
    file_path: str,
    records: List[Dict[str, Any]],
    supabase: Optional[Client] = None
) -> Optional[str]:
    """
    Upload processed records to Supabase with deduplication.
    
    Args:
        file_path: Path to source PDF file
        records: List of extracted records
        supabase: Optional Supabase client (will initialize if not provided)
        
    Returns:
        Submission ID if successful, None otherwise
    """
    if not SUPABASE_AVAILABLE:
        logging.warning("Supabase library not available - skipping upload (install with: pip install supabase)")
        return None
    
    if not supabase:
        logging.debug("Supabase client not provided, attempting to initialize...")
        supabase = init_supabase()
        if not supabase:
            logging.warning("Supabase not configured - skipping upload (check SUPABASE_URL and SUPABASE_ANON_KEY environment variables)")
            return None
    
    if not records:
        logging.info("No records to upload - skipping Supabase upload")
        return None
    
    logging.debug(f"Attempting to upload {len(records)} records to Supabase...")
    
    try:
        submission_id = str(uuid.uuid4())
        processed_vuln_ids = []
        processed_ofc_ids = []
        inserted_count = 0
        linked_count = 0
        
        # Extract document title from file path for taxonomy inference
        document_title = os.path.basename(file_path).replace("_", " ").replace("-", " ").rsplit(".", 1)[0]
        
        # Process each record
        for record in records:
            vulnerability = record.get("vulnerability", "").strip()
            if not vulnerability:
                continue
            
            # Validate and correct taxonomy before processing
            from .taxonomy_inference import validate_and_correct_taxonomy
            record = validate_and_correct_taxonomy(record, document_title=document_title)
            
            # Get OFCs (handle both "options" and "options_for_consideration" fields)
            options_for_consideration = record.get("options") or record.get("options_for_consideration", [])
            if isinstance(options_for_consideration, str):
                options_for_consideration = [options_for_consideration]
            elif not isinstance(options_for_consideration, list):
                options_for_consideration = []
            
            discipline = record.get("discipline", "").strip()
            sector = record.get("sector", "").strip()
            subsector = record.get("subsector", "").strip()
            confidence = normalize_confidence(record.get("confidence", "Medium"))
            impact_level = normalize_impact_level(record.get("impact_level", "Moderate"))
            
            # Calculate dedupe_key
            import hashlib
            dedupe_key = hashlib.sha256(
                f"{vulnerability.lower().strip()}{options_for_consideration[0] if options_for_consideration else ''}".encode()
            ).hexdigest()
            
            # Check if vulnerability already exists
            existing_vuln_id = check_existing_vulnerability(supabase, dedupe_key)
            
            if existing_vuln_id:
                logging.debug(f"Vulnerability already exists, linking: {vulnerability[:50]}...")
                processed_vuln_ids.append(existing_vuln_id)
                linked_count += 1
            else:
                # Insert new vulnerability
                vuln_payload = {
                    "vulnerability": vulnerability,
                    "discipline": discipline if discipline else None,
                    "confidence": confidence,
                    "impact_level": impact_level,
                    "dedupe_key": dedupe_key
                }
                
                try:
                    vuln_response = supabase.table("vulnerabilities").insert(vuln_payload).execute()
                    if vuln_response.data and len(vuln_response.data) > 0:
                        existing_vuln_id = vuln_response.data[0].get("id")
                        processed_vuln_ids.append(existing_vuln_id)
                        inserted_count += 1
                    else:
                        logging.warning(f"Failed to insert vulnerability: {vulnerability[:50]}...")
                        continue
                except Exception as e:
                    logging.error(f"Error inserting vulnerability: {e}", exc_info=True)
                    # Continue with next vulnerability - don't fail entire batch
                    continue
            
            # Process OFCs
            for ofc_text in options_for_consideration:
                if not ofc_text or not ofc_text.strip():
                    continue
                
                ofc_text = str(ofc_text).strip()
                
                # Check if OFC already exists
                try:
                    ofc_check = supabase.table("options_for_consideration").select("id").eq("option_text", ofc_text).limit(1).execute()
                    if ofc_check.data and len(ofc_check.data) > 0:
                        ofc_id = ofc_check.data[0].get("id")
                    else:
                        # Insert new OFC
                        ofc_payload = {
                            "option_text": ofc_text,
                            "discipline": discipline if discipline else None
                        }
                        ofc_response = supabase.table("options_for_consideration").insert(ofc_payload).execute()
                        if ofc_response.data and len(ofc_response.data) > 0:
                            ofc_id = ofc_response.data[0].get("id")
                        else:
                            logging.warning(f"Failed to insert OFC: {ofc_text[:50]}...")
                            continue
                    
                    processed_ofc_ids.append(ofc_id)
                    
                    # Link vulnerability to OFC
                    try:
                        link_payload = {
                            "vulnerability_id": existing_vuln_id,
                            "ofc_id": ofc_id
                        }
                        supabase.table("vulnerability_ofc_links").insert(link_payload).execute()
                    except Exception as e:
                        logging.debug(f"Link may already exist: {e}")
                        
                except Exception as e:
                    logging.warning(f"Error processing OFC: {e}", exc_info=True)
                    # Continue with next OFC - don't fail entire batch
        
        # Create submission record
        submission_payload = {
            "id": submission_id,
            "type": "document",
            "status": "pending_review",
            "source": "vofc_processor",
            "submitter_email": "system@vofc.local",
            "document_name": os.path.basename(file_path),
            "data": {
                "source_file": os.path.basename(file_path),
                "processed_at": datetime.utcnow().isoformat(),
                "records": records,
                "model_version": Config.DEFAULT_MODEL,
                "inserted_count": inserted_count,
                "linked_count": linked_count
            },
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("submissions").insert(submission_payload).execute()
        
        if result.data:
            logging.info(f"✅ Uploaded to Supabase: submission_id={submission_id} ({inserted_count} inserted, {linked_count} linked)")
            return submission_id
        else:
            logging.warning(f"Supabase insert returned no data for {file_path}")
            return None
            
    except ServiceError:
        # Re-raise ServiceError as-is
        raise
    except Exception as e:
        logging.error(f"Error uploading to Supabase: {e}", exc_info=True)
        raise ServiceError(f"Supabase upload failed: {e}") from e

