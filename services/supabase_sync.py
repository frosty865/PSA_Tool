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

# Add logging
import logging
logger = logging.getLogger(__name__)
# Set logging level to INFO to see debug messages
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)


def sync_processed_result(result_path: str, submitter_email: str = "system@psa.local"):
    """
    Upload parsed JSON result into Supabase submission tables.
    
    Args:
        result_path: Path to the processed JSON result file
        submitter_email: Email of the submitter (default: system@psa.local)
    
    Returns:
        submission_id: UUID of the created submission
    """
    logger.info(f"[SYNC] Starting sync for: {result_path}")
    logger.info(f"[SYNC] Supabase URL: {SUPABASE_URL[:30]}..." if SUPABASE_URL else "[SYNC] Supabase URL: NOT SET")
    logger.info(f"[SYNC] Supabase Key: {'SET' if SUPABASE_SERVICE_ROLE_KEY else 'NOT SET'}")
    
    # Verify Supabase client is available
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        error_msg = f"Supabase credentials not configured. URL: {'SET' if SUPABASE_URL else 'NOT SET'}, Key: {'SET' if SUPABASE_SERVICE_ROLE_KEY else 'NOT SET'}"
        logger.error(f"[SYNC] {error_msg}")
        raise ValueError(error_msg)
    
    # Read the result file
    result_file = Path(result_path)
    if not result_file.exists():
        error_msg = f"Result file not found: {result_path}"
        logger.error(f"[SYNC] {error_msg}")
        raise FileNotFoundError(error_msg)
    
    logger.info(f"[SYNC] Reading result file: {result_file} ({result_file.stat().st_size} bytes)")
    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    logger.info(f"[SYNC] Loaded JSON data. Top-level keys: {list(data.keys())}")
    
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
    
    # IMPORTANT: We preserve the FULL original data in the data JSONB column
    # We only READ from data to extract values for separate tables - we never modify or remove from data
    # The data column contains the complete original result structure including:
    # - All vulnerabilities with their IDs (discipline_id, sector_id, subsector_id)
    # - All OFCs with their IDs and vulnerability references
    # - All sources
    # - All metadata (source_file, processed_at, phase counts, etc.)
    # - Everything is preserved - nothing is subtracted or removed
    
    # 1. Create submission record with FULL data preserved
    submission_id = str(uuid.uuid4())
    
    # Note: source_file and document_name are stored in the data JSONB column, not as separate columns
    # The submissions table doesn't have source_file or document_name columns
    
    # Build submission data with only REQUIRED fields
    # Store optional fields in data JSONB to avoid schema mismatches
    # Use 'document' type for auto-processed documents (after migration allows it)
    # Extract document_name from data if available
    document_name = data.get("document_name") or data.get("source_file") or None
    
    submission_data = {
        "id": submission_id,
        "type": "document",  # Use 'document' for auto-processed documents with multiple vulnerabilities/OFCs
        "status": "pending_review",
        "source": "psa_tool_auto",
        "data": data,  # Store FULL original data as JSON - nothing is removed or modified
    }
    
    # Add document_name if available (after migration adds this column)
    if document_name:
        submission_data["document_name"] = document_name
    
    # Add timestamps (these should always exist)
    submission_data["created_at"] = datetime.utcnow().isoformat()
    submission_data["updated_at"] = datetime.utcnow().isoformat()
    
    # Extract metadata for separate columns (more reliable for querying)
    parser_version = data.get("parser_version", "vofc-parser:latest")
    engine_version = data.get("engine_version", "vofc-engine:latest")
    auditor_version = data.get("auditor_version", "vofc-auditor:latest")
    
    # Also store metadata in data JSONB for backup/redundancy
    metadata_to_store = {}
    if submitter_email:
        metadata_to_store["submitter_email"] = submitter_email
    metadata_to_store["parser_version"] = parser_version
    metadata_to_store["engine_version"] = engine_version
    metadata_to_store["auditor_version"] = auditor_version
    
    # Merge metadata into data JSONB (for redundancy and full data preservation)
    if "data" in submission_data and isinstance(submission_data["data"], dict):
        submission_data["data"].update(metadata_to_store)
    else:
        submission_data["data"] = {**data, **metadata_to_store}
    
    # Insert with metadata columns (after migration adds them)
    try:
        # Include metadata as separate columns for better querying/indexing
        submission_data["submitter_email"] = submitter_email
        submission_data["parser_version"] = parser_version
        submission_data["engine_version"] = engine_version
        submission_data["auditor_version"] = auditor_version
        
        # Remove None values
        submission_data = {k: v for k, v in submission_data.items() if v is not None}
        
        logger.info(f"Inserting submission {submission_id} into Supabase...")
        logger.info(f"   Using fields: {list(submission_data.keys())}")
        result = supabase.table("submissions").insert(submission_data).execute()
        logger.info(f"[OK] Successfully created submission {submission_id}")
        if not result.data:
            raise Exception("Insert returned no data - submission may not have been created")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to create submission record: {error_msg}")
        logger.error(f"   Submission data keys: {list(submission_data.keys())}")
        logger.error(f"   Error type: {type(e).__name__}")
        import traceback
        logger.error(f"   Traceback: {traceback.format_exc()}")
        raise Exception(f"Failed to create submission record: {error_msg}")
    
    # 2. Extract and insert vulnerabilities into separate table
    # NOTE: We READ from data but do NOT modify it - data remains complete in the data column
    # Store vulnerability IDs mapped by vulnerability text for linking to OFCs
    
    # Handle different data formats:
    # 1. Standard format: {"vulnerabilities": [...], "options_for_consideration": [...]}
    # 2. Phase3 auditor format: {"accepted": [...], "needs_review": [...], "rejected": [...], "records": [...]}
    # 3. Phase1 parser format: {"records": [{"vulnerabilities": [...], "vulnerability": "...", "ofc": "...", ...}]}
    vulnerabilities = data.get("vulnerabilities", [])
    
    # If phase1_parser format (has "records" array with nested structure)
    if not vulnerabilities and "records" in data and isinstance(data.get("records"), list):
        records = data.get("records", [])
        logger.info(f"[SYNC] Detected Phase1 parser format, extracting from {len(records)} records")
        
        # Extract vulnerabilities from records
        vulnerabilities = []
        for record in records:
            # Handle nested vulnerabilities array
            if "vulnerabilities" in record and isinstance(record.get("vulnerabilities"), list):
                for vuln_obj in record.get("vulnerabilities", []):
                    vuln_text = vuln_obj.get("vulnerability", "") or vuln_obj.get("text", "")
                    if vuln_text:
                        vuln_entry = {
                            "vulnerability": vuln_text,
                            "discipline": vuln_obj.get("discipline"),
                            "sector": vuln_obj.get("sector"),
                            "subsector": vuln_obj.get("subsector"),
                            "source_context": vuln_obj.get("source_context"),
                            "confidence_score": vuln_obj.get("confidence") or vuln_obj.get("confidence_score"),
                            "page_ref": record.get("source_page") or record.get("page_range"),
                            "chunk_id": record.get("chunk_id"),
                            "source_file": record.get("source_file"),
                        }
                        vulnerabilities.append(vuln_entry)
            
            # Handle direct vulnerability field
            elif "vulnerability" in record and record.get("vulnerability"):
                vuln_text = record.get("vulnerability", "")
                if vuln_text:
                    vuln_entry = {
                        "vulnerability": vuln_text,
                        "discipline": record.get("discipline"),
                        "sector": record.get("sector"),
                        "subsector": record.get("subsector"),
                        "source_context": record.get("source_context"),
                        "confidence_score": record.get("confidence") or record.get("confidence_score"),
                        "page_ref": record.get("source_page") or record.get("page_range"),
                        "chunk_id": record.get("chunk_id"),
                        "source_file": record.get("source_file"),
                    }
                    vulnerabilities.append(vuln_entry)
        
        logger.info(f"[SYNC] Extracted {len(vulnerabilities)} vulnerabilities from Phase1 parser format")
    
    # If phase3_auditor format, extract from accepted + needs_review + records
    elif not vulnerabilities and ("accepted" in data or "needs_review" in data or "records" in data):
        logger.info(f"[SYNC] Detected Phase3 auditor format, extracting from accepted/needs_review/records")
        accepted = data.get("accepted", [])
        needs_review = data.get("needs_review", [])
        records = data.get("records", [])
        # Combine all records (accepted + needs_review + any in records)
        all_records = accepted + needs_review
        # Add records that aren't already in accepted/needs_review
        record_texts = {r.get("vulnerability", "").lower()[:100] for r in all_records}
        for rec in records:
            rec_text = rec.get("vulnerability", "").lower()[:100]
            if rec_text and rec_text not in record_texts:
                all_records.append(rec)
                record_texts.add(rec_text)
        # Convert to vulnerabilities format
        vulnerabilities = []
        for rec in all_records:
            vuln_text = rec.get("vulnerability", "") or rec.get("text", "")
            if vuln_text:
                vuln_obj = {
                    "vulnerability": vuln_text,
                    "discipline_id": rec.get("discipline_id"),
                    "discipline": rec.get("discipline"),
                    "category": rec.get("category"),
                    "sector_id": rec.get("sector_id"),
                    "sector": rec.get("sector"),
                    "subsector_id": rec.get("subsector_id"),
                    "subsector": rec.get("subsector"),
                    "page_ref": rec.get("page_ref"),
                    "chunk_id": rec.get("chunk_id"),
                    "severity_level": rec.get("severity_level"),
                    "confidence_score": rec.get("confidence_score"),
                    "intent": rec.get("intent"),
                    "source_context": rec.get("source_context"),
                    "audit_status": rec.get("audit_status", "accepted" if rec in accepted else "needs_review" if rec in needs_review else "pending"),
                    "review_reason": rec.get("review_reason"),
                    "rejection_reason": rec.get("rejection_reason"),
                }
                vulnerabilities.append(vuln_obj)
        logger.info(f"[SYNC] Converted Phase3 format: {len(accepted)} accepted + {len(needs_review)} needs_review = {len(vulnerabilities)} vulnerabilities")
    
    if not isinstance(vulnerabilities, list):
        vulnerabilities = []
    
    logger.info(f"[SYNC] Found {len(vulnerabilities)} vulnerabilities in result data")
    if len(vulnerabilities) == 0:
        logger.warning(f"[SYNC] No vulnerabilities found in data. Data keys: {list(data.keys())}")
        # Check if data structure is different
        if "final_records" in data:
            logger.warning(f"[SYNC] Found 'final_records' key - result may need restructuring")
    
    vuln_count = 0
    vuln_id_map = {}  # Map: vulnerability_text -> vulnerability_id
    
    for v in vulnerabilities:
        if not isinstance(v, dict):
            continue
        
        # Extract vulnerability text - try multiple field names
        vuln_text = v.get("vulnerability") or v.get("text") or v.get("title") or str(v)
        if not vuln_text or not vuln_text.strip():
            logger.warning(f"Skipping vulnerability with no text: {v}")
            continue
        
        # Store IDs directly and resolve to names
        discipline_id = v.get("discipline_id")
        discipline = v.get("discipline") or v.get("category")
        category = v.get("category")
        
        if not discipline and discipline_id:
            # Try to get discipline name and category from ID
            disc_record = supabase.table("disciplines").select("name, category").eq("id", discipline_id).maybe_single().execute()
            if disc_record.data:
                discipline = disc_record.data.get("name") or disc_record.data.get("category")
                if not category:
                    category = disc_record.data.get("category")
        
        sector_id = v.get("sector_id")
        sector = v.get("sector")
        if not sector and sector_id:
            sector_record = supabase.table("sectors").select("sector_name").eq("id", sector_id).maybe_single().execute()
            if sector_record.data:
                sector = sector_record.data.get("sector_name")
        
        subsector_id = v.get("subsector_id")
        subsector = v.get("subsector")
        if not subsector and subsector_id:
            subsector_record = supabase.table("subsectors").select("subsector_name").eq("id", subsector_id).maybe_single().execute()
            if subsector_record.data:
                subsector = subsector_record.data.get("subsector_name")
        
        vuln_id = str(uuid.uuid4())
        vrec = {
            "id": vuln_id,
            "submission_id": submission_id,
            "vulnerability": vuln_text,
            "discipline_id": discipline_id,  # Store ID directly
            "discipline": discipline,  # Store resolved name
            "category": category,  # Store category
            "sector_id": sector_id,  # Store ID
            "sector": sector,  # Store resolved name
            "subsector_id": subsector_id,  # Store ID directly
            "subsector": subsector,  # Store resolved name
            "page_ref": v.get("page_ref"),
            "chunk_id": v.get("chunk_id"),
            "severity_level": v.get("severity_level"),  # Severity level (Very Low, Low, Medium, High, Very High)
            "audit_status": v.get("audit_status", "pending"),  # Track review status
            "source": v.get("source") or data.get("source_file") or None,
            "source_title": v.get("source_title") or data.get("source_file") or None,
            "source_url": v.get("source_url") or None,
            "parser_version": data.get("parser_version", "vofc-parser:latest"),
            "parsed_at": datetime.utcnow().isoformat(),
            # Additional fields from Phase 2/3 (if present in data)
            "confidence_score": v.get("confidence_score"),  # Confidence score from Phase 2/3
            "intent": v.get("intent"),  # Intent classification from Phase 2
            "source_context": v.get("source_context"),  # Source context if present
            "description": v.get("description"),  # Description if present
            "recommendations": json.dumps(v.get("recommendations")) if v.get("recommendations") else None,  # Recommendations as JSON
            "review_reason": v.get("review_reason"),  # Review reason if present
            "rejection_reason": v.get("rejection_reason"),  # Rejection reason if present
            "audit_confidence_adjusted": v.get("audit_confidence_adjusted"),  # Adjusted confidence if present
            "audit_notes": v.get("audit_notes"),  # Audit notes if present
        }
        
        # Remove None values to avoid database errors
        vrec = {k: v for k, v in vrec.items() if v is not None}
        
        try:
            result = supabase.table("submission_vulnerabilities").insert(vrec).execute()
            if result.data:
                # Store the vulnerability ID for linking - use normalized text for matching
                # Store both exact match and normalized versions
                vuln_text_normalized = vuln_text.strip().lower()
                vuln_id_map[vuln_text] = vuln_id  # Exact match
                vuln_id_map[vuln_text_normalized] = vuln_id  # Normalized match
                logger.info(f"Stored vulnerability mapping: '{vuln_text[:50] if len(vuln_text) > 50 else vuln_text}...' -> {vuln_id}")
                vuln_count += 1
        except Exception as e:
            logger.warning(f"Warning: Failed to insert vulnerability: {str(e)}")
            logger.warning(f"   Vulnerability data: {vrec}")
            # Continue processing other vulnerabilities
    
    # 3. Extract and insert OFCs into separate table
    # NOTE: We READ from data but do NOT modify it - data remains complete in the data column
    # Store OFC IDs for linking to vulnerabilities
    ofcs = data.get("ofcs") or data.get("options_for_consideration") or []
    
    # If phase1_parser format (has "records" array with nested structure)
    if len(ofcs) == 0 and "records" in data and isinstance(data.get("records"), list):
        records = data.get("records", [])
        logger.info(f"[SYNC] Extracting OFCs from Phase1 parser format")
        
        # Extract OFCs from records
        ofcs = []
        for record in records:
            # Handle nested vulnerabilities array (OFCs are inside vulnerability objects)
            if "vulnerabilities" in record and isinstance(record.get("vulnerabilities"), list):
                for vuln_obj in record.get("vulnerabilities", []):
                    ofc_text = vuln_obj.get("ofc") or vuln_obj.get("option_text")
                    vuln_text = vuln_obj.get("vulnerability", "")
                    if ofc_text:
                        ofcs.append({
                            "option_text": ofc_text if isinstance(ofc_text, str) else str(ofc_text),
                            "vulnerability": vuln_text,
                            "discipline": vuln_obj.get("discipline"),
                            "sector": vuln_obj.get("sector"),
                            "subsector": vuln_obj.get("subsector"),
                            "confidence_score": vuln_obj.get("confidence") or vuln_obj.get("confidence_score"),
                            "source_context": vuln_obj.get("source_context"),
                            "page_ref": record.get("source_page") or record.get("page_range"),
                            "chunk_id": record.get("chunk_id"),
                            "source_file": record.get("source_file"),
                        })
            
            # Handle direct ofc field
            elif "ofc" in record and record.get("ofc"):
                ofc_text = record.get("ofc", "")
                vuln_text = record.get("vulnerability", "")
                if ofc_text:
                    ofcs.append({
                        "option_text": ofc_text if isinstance(ofc_text, str) else str(ofc_text),
                        "vulnerability": vuln_text,
                        "discipline": record.get("discipline"),
                        "sector": record.get("sector"),
                        "subsector": record.get("subsector"),
                        "confidence_score": record.get("confidence") or record.get("confidence_score"),
                        "source_context": record.get("source_context"),
                        "page_ref": record.get("source_page") or record.get("page_range"),
                        "chunk_id": record.get("chunk_id"),
                        "source_file": record.get("source_file"),
                    })
        
        logger.info(f"[SYNC] Extracted {len(ofcs)} OFCs from Phase1 parser format")
    
    # If phase3_auditor format, extract OFCs from records (they have "ofc" field)
    elif len(ofcs) == 0 and ("accepted" in data or "needs_review" in data or "records" in data):
        logger.info(f"[SYNC] Extracting OFCs from Phase3 auditor format")
        accepted = data.get("accepted", [])
        needs_review = data.get("needs_review", [])
        records = data.get("records", [])
        all_records = accepted + needs_review + records
        
        # Extract OFCs from records
        ofcs = []
        for rec in all_records:
            # Handle different OFC field names
            ofc_text = rec.get("ofc") or rec.get("option_text") or rec.get("options_for_consideration")
            if isinstance(ofc_text, list):
                ofcs.extend([{"option_text": o, "vulnerability": rec.get("vulnerability", ""), **{k: v for k, v in rec.items() if k not in ["ofc", "option_text", "options_for_consideration"]}} for o in ofc_text])
            elif ofc_text:
                ofcs.append({
                    "option_text": ofc_text if isinstance(ofc_text, str) else str(ofc_text),
                    "vulnerability": rec.get("vulnerability", ""),
                    "discipline_id": rec.get("discipline_id"),
                    "discipline": rec.get("discipline"),
                    "confidence_score": rec.get("confidence_score"),
                    "intent": rec.get("intent"),
                    "audit_status": rec.get("audit_status", "accepted" if rec in accepted else "needs_review" if rec in needs_review else "pending"),
                })
        logger.info(f"[SYNC] Extracted {len(ofcs)} OFCs from Phase3 format")
    
    if not isinstance(ofcs, list):
        ofcs = []
    
    logger.info(f"[SYNC] Found {len(ofcs)} OFCs in result data")
    if len(ofcs) == 0:
        logger.warning(f"[SYNC] No OFCs found in data. Checked keys: 'ofcs', 'options_for_consideration'")
    
    ofc_count = 0
    ofc_records = []  # Store OFC records with their vulnerability references for linking
    
    for o in ofcs:
        if not isinstance(o, dict):
            continue
        
        # Store IDs directly and resolve to names (OFCs don't have sector/subsector columns)
        discipline_id = o.get("discipline_id")
        discipline = o.get("discipline") or o.get("category")
        if not discipline and discipline_id:
            disc_record = supabase.table("disciplines").select("name, category").eq("id", discipline_id).maybe_single().execute()
            if disc_record.data:
                discipline = disc_record.data.get("name") or disc_record.data.get("category")
        
        ofc_id = str(uuid.uuid4())
        ofc_text = o.get("option_text") or o.get("text") or o.get("title") or str(o)
        if not ofc_text or not ofc_text.strip():
            logger.warning(f"Skipping OFC with no text: {o}")
            continue
        
        # Reference to the vulnerability this OFC belongs to
        vuln_ref = o.get("vulnerability") or o.get("vulnerability_text") or o.get("parent_vulnerability")
        if vuln_ref:
            vuln_ref = vuln_ref.strip()
        
        orec = {
            "id": ofc_id,
            "submission_id": submission_id,
            "option_text": ofc_text,
            # Note: vulnerability text reference is NOT stored in this table (column doesn't exist)
            # It's only used for matching/linking purposes
            "discipline_id": discipline_id,  # Store ID directly
            "discipline": discipline,  # Store resolved name
            "confidence_score": float(o.get("confidence_score", 0.8)) if o.get("confidence_score") else None,
            "audit_status": o.get("audit_status", "pending"),  # Track review status
            "source": o.get("source") or data.get("source_file") or None,
            "source_title": o.get("source_title") or data.get("source_file") or None,
            "source_url": o.get("source_url") or None,
            "citations": json.dumps(o.get("citations", [])) if o.get("citations") else None,
            # Additional fields from Phase 2/3 (if present in data)
            "intent": o.get("intent"),  # Intent classification from Phase 2
            "source_context": o.get("source_context"),  # Source context if present
            "review_reason": o.get("review_reason"),  # Review reason if present
            "rejection_reason": o.get("rejection_reason"),  # Rejection reason if present
        }
        
        # Remove None values
        orec = {k: v for k, v in orec.items() if v is not None}
        
        try:
            result = supabase.table("submission_options_for_consideration").insert(orec).execute()
            if result.data:
                # Store OFC record with vulnerability reference for linking
                ofc_records.append({
                    "ofc_id": ofc_id,
                    "vulnerability_ref": vuln_ref,
                    "option_text": ofc_text
                })
                ofc_count += 1
        except Exception as e:
            logger.warning(f"⚠️  Warning: Failed to insert OFC: {str(e)}")
            logger.warning(f"   OFC data: {orec}")
            # Continue processing other OFCs
    
    # 4. Create vulnerability-OFC links in submission_vulnerability_ofc_links table
    # Match OFCs to their vulnerabilities based on the vulnerability reference in the OFC
    # Also update OFC records with linked_vulnerability_id for fast joins
    link_count = 0
    unmatched_ofcs = []
    
    for ofc_record in ofc_records:
        vuln_ref = ofc_record.get("vulnerability_ref")
        if not vuln_ref or not str(vuln_ref).strip():
            logger.debug(f"OFC {ofc_record['ofc_id']} has no vulnerability reference, skipping link")
            unmatched_ofcs.append(ofc_record)
            continue
        
        vuln_ref = str(vuln_ref).strip()
        vuln_ref_normalized = vuln_ref.lower()
        
        logger.info(f"Attempting to match OFC to vulnerability: ref='{vuln_ref[:50] if len(vuln_ref) > 50 else vuln_ref}'")
        logger.info(f"Vulnerability map has {len(vuln_id_map)} entries")
        # Show first few vulnerability texts for debugging
        unique_vuln_texts = [k for k in vuln_id_map.keys() if k != k.lower()]
        if unique_vuln_texts:
            logger.info(f"Sample vulnerability texts: {[t[:50] for t in unique_vuln_texts[:3]]}")
        
        # Find the vulnerability ID that matches this reference
        vuln_id = vuln_id_map.get(vuln_ref)  # Try exact match first
        if vuln_id:
            logger.info(f"Exact match found: '{vuln_ref[:50]}...' -> {vuln_id}")
        else:
            vuln_id = vuln_id_map.get(vuln_ref_normalized)  # Try normalized match
            if vuln_id:
                logger.info(f"Normalized match found: '{vuln_ref_normalized[:50]}...' -> {vuln_id}")
        
        if not vuln_id:
            # Try to find by partial match or substring
            # Get unique vulnerability texts (exclude normalized duplicates)
            for vuln_text in unique_vuln_texts:
                vid = vuln_id_map[vuln_text]
                vuln_text_lower = vuln_text.lower()
                # Try various matching strategies
                if (vuln_ref in vuln_text or 
                    vuln_text in vuln_ref or
                    vuln_ref_normalized in vuln_text_lower or
                    vuln_text_lower in vuln_ref_normalized):
                    vuln_id = vid
                    logger.info(f"Matched OFC to vulnerability via partial match: '{vuln_ref[:50]}...' -> '{vuln_text[:50]}...'")
                    break
        
        if vuln_id:
            link_record = {
                "id": str(uuid.uuid4()),
                "submission_id": submission_id,
                "vulnerability_id": vuln_id,
                "ofc_id": ofc_record["ofc_id"],
                "link_type": "direct",  # Can be "direct", "inferred", etc.
                "confidence_score": None,  # Can be set if available in data
            }
            
            try:
                supabase.table("submission_vulnerability_ofc_links").insert(link_record).execute()
                link_count += 1
                logger.debug(f"Created link: vulnerability {vuln_id} <-> OFC {ofc_record['ofc_id']}")
                
                # Optionally update OFC record with linked_vulnerability_id for fast joins
                try:
                    supabase.table("submission_options_for_consideration").update({
                        "linked_vulnerability_id": vuln_id
                    }).eq("id", ofc_record["ofc_id"]).execute()
                except Exception as update_err:
                    # Non-critical - link table is the source of truth
                    logger.debug(f"Note: Could not update linked_vulnerability_id: {str(update_err)}")
                    
            except Exception as e:
                logger.warning(f"Warning: Failed to insert vulnerability-OFC link: {str(e)}")
        else:
            logger.warning(f"Could not match OFC '{ofc_record.get('option_text', 'unknown')[:50]}...' to vulnerability '{vuln_ref[:50] if vuln_ref else 'none'}...'")
            logger.debug(f"Available vulnerability texts: {list(set([k for k in vuln_id_map.keys() if k != k.lower()]))[:5]}")
            unmatched_ofcs.append(ofc_record)
    
    if unmatched_ofcs:
        logger.info(f"Note: {len(unmatched_ofcs)} OFC(s) could not be linked to vulnerabilities (missing or non-matching vulnerability reference)")
    
    # 5. Extract and insert sources into separate table
    # NOTE: We READ from data but do NOT modify it - data remains complete in the data column
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        sources = []
    
    # Also extract source from source_file if no explicit sources array
    # Create a source record from the document metadata
    source_file = data.get("source_file")
    if source_file and not sources:
        # Create a source record from the document itself
        sources.append({
            "source_title": source_file,
            "source_text": f"Document: {source_file}",
            # "source_type": "guidance_doc",  # Column may not exist
            "content_restriction": "public"
        })
    
    source_count = 0
    for s in sources:
        if not isinstance(s, dict):
            # If source is a string, convert to dict
            if isinstance(s, str):
                s = {"source_text": s, "source_title": s}
            else:
                continue
        
        srec = {
            "id": str(uuid.uuid4()),
            "submission_id": submission_id,
            "source_text": s.get("text") or s.get("citation") or s.get("source_text") or s.get("title") or str(s),
            "source_title": s.get("title") or s.get("source_title") or source_file or None,
            "source_url": s.get("url") or s.get("source_url") or None,
            "author_org": s.get("author_org") or s.get("organization") or s.get("author") or None,
            "publication_year": int(s.get("year")) if s.get("year") else None,
            # "source_type": s.get("source_type") or s.get("type") or "guidance_doc",  # Column may not exist
            "content_restriction": s.get("restriction") or s.get("content_restriction", "public"),
        }
        
        # Remove None values
        srec = {k: v for k, v in srec.items() if v is not None}
        
        try:
            supabase.table("submission_sources").insert(srec).execute()
            source_count += 1
            logger.debug(f"Inserted source: {srec.get('source_title', 'unknown')}")
        except Exception as e:
            logger.warning(f"Warning: Failed to insert source: {str(e)}")
            logger.warning(f"   Source data: {srec}")
            # Continue processing other sources
    
    # 6. Create OFC-source links in submission_ofc_sources table (if table exists)
    # Link OFCs to their source documents
    ofc_source_link_count = 0
    if source_count > 0:
        # Get the source IDs we just created
        try:
            source_records = supabase.table("submission_sources").select("id").eq("submission_id", submission_id).execute()
            source_ids = [s["id"] for s in (source_records.data or [])]
            
            # Link each OFC to the first source (or all sources if multiple)
            for ofc_record in ofc_records:
                ofc_id = ofc_record.get("ofc_id")
                if not ofc_id:
                    continue
                
                # Link to first source (or all if you want many-to-many)
                for source_id in source_ids[:1]:  # Just link to first source for now
                    try:
                        ofc_source_link = {
                            "id": str(uuid.uuid4()),
                            "submission_id": submission_id,
                            "ofc_id": ofc_id,
                            "source_id": source_id,
                        }
                        supabase.table("submission_ofc_sources").insert(ofc_source_link).execute()
                        ofc_source_link_count += 1
                    except Exception as e:
                        # Table might not exist, or column names might differ
                        logger.debug(f"Note: Could not create OFC-source link (table may not exist): {str(e)}")
                        break  # Don't try more if table doesn't exist
        except Exception as e:
            logger.debug(f"Note: Could not query sources for OFC linking: {str(e)}")
    
    logger.info(f"Synced results to Supabase for submission {submission_id}")
    logger.info(f"   - {vuln_count} vulnerabilities inserted into submission_vulnerabilities")
    logger.info(f"   - {ofc_count} OFCs inserted into submission_options_for_consideration")
    logger.info(f"   - {link_count} vulnerability-OFC links inserted into submission_vulnerability_ofc_links")
    logger.info(f"   - {source_count} sources inserted into submission_sources")
    if ofc_source_link_count > 0:
        logger.info(f"   - {ofc_source_link_count} OFC-source links inserted into submission_ofc_sources")
    logger.info(f"   - Full data preserved in submissions.data JSONB column")
    print(f"[OK] Synced results to Supabase for submission {submission_id}")
    print(f"   - {vuln_count} vulnerabilities inserted into submission_vulnerabilities")
    print(f"   - {ofc_count} OFCs inserted into submission_options_for_consideration")
    print(f"   - {link_count} vulnerability-OFC links inserted into submission_vulnerability_ofc_links")
    print(f"   - {source_count} sources inserted into submission_sources")
    if ofc_source_link_count > 0:
        print(f"   - {ofc_source_link_count} OFC-source links inserted into submission_ofc_sources")
    print(f"   - Full data preserved in submissions.data JSONB column")
    return submission_id

