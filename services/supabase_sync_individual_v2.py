"""
Individual Submission Sync V2 - Clean rebuild
Processes Phase 2 output: {vulnerability: str, ofc: str, discipline, sector, subsector, confidence}
"""
import json
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from services.supabase_client import get_supabase_client, get_discipline_record, get_sector_id, get_subsector_id
from services.supabase_sync import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

logger = logging.getLogger(__name__)


def convert_confidence(confidence: Any) -> float:
    """Convert confidence string to float."""
    if isinstance(confidence, str):
        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5, "very low": 0.3}
        return confidence_map.get(confidence.lower(), 0.7)
    elif isinstance(confidence, (int, float)):
        return float(confidence)
    return 0.7


def extract_record_data(record: Dict[str, Any]) -> tuple[List[Dict], List[Dict]]:
    """
    Extract vulnerabilities and OFCs from a Phase 2 record.
    
    Handles two formats:
    1. {vulnerability: "text", ofc: "text"} - single pair
    2. {vulnerabilities: [{vulnerability: "text", ofc: "text"}, ...]} - array of pairs
    
    Returns:
        (vulnerabilities_list, ofcs_list)
    """
    vulnerabilities = []
    ofcs = []
    
    # Handle format: {vulnerabilities: [{vulnerability, ofc}, ...]}
    if "vulnerabilities" in record and isinstance(record.get("vulnerabilities"), list):
        for vuln_item in record["vulnerabilities"]:
            # Get vulnerability text - if missing, derive from source_context or OFC
            vuln_text = vuln_item.get("vulnerability", "").strip()
            
            # If no explicit vulnerability, try to derive from source_context
            if not vuln_text:
                # Handle source_context - could be string or dict
                source_context_raw = vuln_item.get("source_context") or record.get("source_context")
                if isinstance(source_context_raw, dict):
                    source_context = str(source_context_raw).strip()
                else:
                    source_context = str(source_context_raw).strip() if source_context_raw else ""
                
                # Handle ofc - could be string, list, or dict
                ofc_raw = vuln_item.get("ofc") or vuln_item.get("options_for_consideration")
                if isinstance(ofc_raw, dict):
                    ofc_text = str(ofc_raw).strip()
                elif isinstance(ofc_raw, list):
                    ofc_text = " ".join([str(o) for o in ofc_raw if o]).strip()
                else:
                    ofc_text = str(ofc_raw).strip() if ofc_raw else ""
                
                # Do NOT infer or create vulnerabilities - only use what's explicitly provided
                # If no vulnerability text exists, skip this record (don't create one from OFC)
                # The postprocess step should have already handled OFC-only records with "(Implied...)" text
                if not vuln_text:
                    logger.warning(f"[SYNC-V2] Skipping record {idx}: No explicit vulnerability text found (not creating from OFC)")
                    continue
                
                # If still no vulnerability text, skip this item
                # Strict validation: reject placeholder/fake data
                placeholder_patterns = ["placeholder", "dummy", "test", "example", "sample", "fake"]
                vuln_lower = (vuln_text or "").lower()
                
                # Reduced minimum from 7 to 5 chars to capture more valid short vulnerabilities
                if not vuln_text or len(vuln_text.strip()) < 5:
                    logger.warning(f"[SYNC-V2] Skipping record {idx}: vulnerability too short or empty")
                    continue
                
                # Reject placeholder text (unless it's the legitimate "Implied" text)
                if not vuln_text.startswith("(Implied") and any(pattern in vuln_lower for pattern in placeholder_patterns):
                    logger.warning(f"[SYNC-V2] Skipping record {idx}: vulnerability contains placeholder text")
                    continue
            
            # Get confidence from item or parent record
            confidence_score = convert_confidence(
                vuln_item.get("confidence") or 
                vuln_item.get("confidence_score") or
                record.get("confidence") or 
                record.get("confidence_score")
            )
            
            # Ensure vulnerability text is properly formatted as a sentence
            if vuln_text:
                vuln_text = vuln_text.strip()
                if vuln_text and not vuln_text[0].isupper():
                    vuln_text = vuln_text[0].upper() + vuln_text[1:] if len(vuln_text) > 1 else vuln_text.upper()
                if vuln_text and not vuln_text.endswith(('.', '!', '?')):
                    vuln_text = vuln_text + '.'
            
            # Create vulnerability entry (use item taxonomy if available, fallback to parent)
            vuln_entry = {
                "vulnerability": vuln_text,
                "discipline": vuln_item.get("discipline") or record.get("discipline"),
                "sector": vuln_item.get("sector") or record.get("sector"),
                "subsector": vuln_item.get("subsector") or record.get("subsector"),
                "source_context": vuln_item.get("source_context") or record.get("source_context"),
                "confidence_score": confidence_score,
            }
            vulnerabilities.append(vuln_entry)
            
            # Extract OFC(s) from this vulnerability item - prioritize options_for_consideration
            ofc_data = vuln_item.get("options_for_consideration") or vuln_item.get("ofc") or vuln_item.get("option_text")
            
            if ofc_data:
                # Handle array of OFCs
                if isinstance(ofc_data, list):
                    for ofc_item in ofc_data:
                        ofc_text = ofc_item if isinstance(ofc_item, str) else ofc_item.get("text", "") or ofc_item.get("option_text", "")
                        if ofc_text and ofc_text.strip():
                            ofcs.append({
                                "option_text": ofc_text.strip(),
                                "vulnerability": vuln_text,  # Link to parent vulnerability
                                "discipline": vuln_entry.get("discipline"),
                                "sector": vuln_entry.get("sector"),
                                "subsector": vuln_entry.get("subsector"),
                                "confidence_score": confidence_score,
                            })
                # Handle single OFC string
                elif isinstance(ofc_data, str) and ofc_data.strip():
                    ofcs.append({
                        "option_text": ofc_data.strip(),
                        "vulnerability": vuln_text,  # Link to parent vulnerability
                        "discipline": vuln_entry.get("discipline"),
                        "sector": vuln_entry.get("sector"),
                        "subsector": vuln_entry.get("subsector"),
                        "confidence_score": confidence_score,
                    })
    
    # Handle format: {vulnerability: "text" or {title: "text"}, ofc: "text" or [{title: "text"}]} - single pair
    elif "vulnerability" in record and record.get("vulnerability"):
        # Handle normalized format: vulnerability can be dict with "title" or string
        vuln_obj = record.get("vulnerability")
        if isinstance(vuln_obj, dict):
            vuln_text = vuln_obj.get("title") or vuln_obj.get("vulnerability") or ""
        else:
            vuln_text = str(vuln_obj) if vuln_obj else ""
        vuln_text = vuln_text.strip()
        
        # If no explicit vulnerability, try to derive from source_context or OFC
        if not vuln_text:
            # Handle source_context - could be string or dict
            source_context_raw = record.get("source_context")
            if isinstance(source_context_raw, dict):
                source_context = str(source_context_raw).strip()
            else:
                source_context = str(source_context_raw).strip() if source_context_raw else ""
            
            # Handle ofc - could be string, list, or dict
            ofc_raw = record.get("ofc") or record.get("options_for_consideration")
            if isinstance(ofc_raw, dict):
                ofc_text = str(ofc_raw).strip()
            elif isinstance(ofc_raw, list):
                ofc_text = " ".join([str(o) for o in ofc_raw if o]).strip()
            else:
                ofc_text = str(ofc_raw).strip() if ofc_raw else ""
            
                # Do NOT infer or create vulnerabilities - only use what's explicitly provided
                # If no vulnerability text exists, skip this record (don't create one from OFC)
                # The postprocess step should have already handled OFC-only records with "(Implied...)" text
                if not vuln_text:
                    logger.warning(f"[SYNC-V2] Skipping record {idx}: No explicit vulnerability text found (not creating from OFC)")
                    continue
        
        # Ensure vulnerability text is properly formatted as a sentence
        if vuln_text:
            vuln_text = vuln_text.strip()
            if vuln_text and not vuln_text[0].isupper():
                vuln_text = vuln_text[0].upper() + vuln_text[1:] if len(vuln_text) > 1 else vuln_text.upper()
            if vuln_text and not vuln_text.endswith(('.', '!', '?')):
                vuln_text = vuln_text + '.'
        
        # Extract confidence
        confidence_score = convert_confidence(
            record.get("confidence") or record.get("confidence_score")
        )
        
        # Create vulnerability entry
        vuln_entry = {
            "vulnerability": vuln_text,
            "discipline": record.get("discipline"),
            "sector": record.get("sector"),
            "subsector": record.get("subsector"),
            "source_context": record.get("source_context"),
            "confidence_score": confidence_score,
        }
        vulnerabilities.append(vuln_entry)
        
        # Extract OFC(s) - prioritize options_for_consideration (standardized format)
        # Fallback to "ofc" or "option_text" for backward compatibility
        ofc_data = record.get("options_for_consideration") or record.get("ofc") or record.get("option_text")
        
        if ofc_data:
            # Handle array of OFCs (1 vulnerability -> many OFCs)
            if isinstance(ofc_data, list):
                for ofc_item in ofc_data:
                    # Handle normalized format: ofc_item can be dict with "title"/"action" or string
                    if isinstance(ofc_item, dict):
                        ofc_text = ofc_item.get("title") or ofc_item.get("action") or ofc_item.get("text", "") or ofc_item.get("option_text", "")
                    else:
                        ofc_text = str(ofc_item) if ofc_item else ""
                    # Validate OFC: must be meaningful content, not placeholder (reduced from 10 to 5 chars)
                    if ofc_text and ofc_text.strip() and len(ofc_text.strip()) >= 5:
                        ofc_lower = ofc_text.strip().lower()
                        placeholder_patterns = ["placeholder", "dummy", "test", "example", "sample", "fake"]
                        if not any(pattern in ofc_lower for pattern in placeholder_patterns):
                            ofcs.append({
                            "option_text": ofc_text.strip(),
                            "vulnerability": vuln_text,  # Link to parent vulnerability
                            "discipline": record.get("discipline"),
                            "sector": record.get("sector"),
                            "subsector": record.get("subsector"),
                            "confidence_score": confidence_score,
                            })
                        else:
                            logger.warning(f"[SYNC-V2] Skipping OFC with placeholder text: {ofc_text[:50]}...")
                    else:
                        logger.warning(f"[SYNC-V2] Skipping OFC: too short or empty")
            # Handle single OFC dict (normalized format) or string (1 vulnerability -> 1 OFC)
            elif isinstance(ofc_data, dict):
                ofc_text = ofc_data.get("title") or ofc_data.get("action") or ofc_data.get("text", "") or ofc_data.get("option_text", "")
                if ofc_text and ofc_text.strip():
                    ofcs.append({
                        "option_text": ofc_text.strip(),
                        "vulnerability": vuln_text,  # Link to parent vulnerability
                        "discipline": record.get("discipline"),
                        "sector": record.get("sector"),
                        "subsector": record.get("subsector"),
                        "confidence_score": confidence_score,
                    })
            elif isinstance(ofc_data, str) and ofc_data.strip():
                ofcs.append({
                    "option_text": ofc_data.strip(),
                    "vulnerability": vuln_text,  # Link to parent vulnerability
                    "discipline": record.get("discipline"),
                    "sector": record.get("sector"),
                    "subsector": record.get("subsector"),
                    "confidence_score": confidence_score,
                })
    
    return vulnerabilities, ofcs


def sync_individual_records(result_path: str, submitter_email: str = "system@psa.local") -> List[str]:
    """
    Break down Phase 2 JSON into individual submissions.
    Each record becomes one submission with all 6 tables populated.
    """
    logger.info(f"[SYNC-V2] Starting sync for: {result_path}")
    
    # Verify Supabase credentials
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Supabase credentials not configured")
    
    # Get Supabase client
    try:
        supabase = get_supabase_client()
    except Exception as e:
        raise ValueError(f"Failed to initialize Supabase client: {e}")
    
    # Read JSON file
    result_file = Path(result_path)
    if not result_file.exists():
        raise FileNotFoundError(f"Result file not found: {result_path}")
    
    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Extract records - check both possible keys
    raw_records = data.get("records") or data.get("all_phase2_records", [])
    if not raw_records:
        logger.warning(f"[SYNC-V2] No records found in {result_path}")
        return []
    
    # STRICT: only complete pairs (for normalized format with nested vulnerability/ofc objects)
    seen_pairs = set()
    def _canon(s):
        """Canonicalize string for comparison."""
        return (s or "").strip().lower()
    
    filtered = []
    for r in raw_records:
        # Handle normalized format: vulnerability is a dict with "title", or a string
        v_obj = r.get("vulnerability")
        if isinstance(v_obj, dict):
            v = v_obj.get("title") or ""
        else:
            v = str(v_obj) if v_obj else ""
        
        # Handle OFC: can be list of dicts, single dict, or string
        ofc_list = r.get("ofc") or []
        if isinstance(ofc_list, dict):
            ofc_list = [ofc_list]
        elif not isinstance(ofc_list, list):
            ofc_list = [ofc_list] if ofc_list else []
        
        # Skip if no vulnerability or no OFCs
        if not v or not ofc_list:
            continue
        
        # Process each OFC pair
        for ofc in ofc_list:
            # Extract OFC title/action
            if isinstance(ofc, dict):
                ofc_text = ofc.get("title") or ofc.get("action") or ""
            else:
                ofc_text = str(ofc) if ofc else ""
            
            if not ofc_text:
                continue
            
            # Create pair key for deduplication
            key = (_canon(v), _canon(ofc_text))
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            
            # Add to filtered list (only once per record, even if multiple OFCs)
            if r not in filtered:
                filtered.append(r)
    
    records = filtered
    if not records:
        logger.warning(f"[SYNC-V2] No complete Vulnerability–OFC pairs found; nothing to sync.")
        return []
    
    logger.info(f"[SYNC-V2] Filtered to {len(records)} complete pairs from {len(raw_records)} raw records")
    
    # --- Deduplicate repeated records coming from Phase 2 ---
    seen = set()
    unique_records = []
    for r in records:
        # Create a unique key from vulnerability text
        key = (
            r.get("vulnerability")
            or (r.get("vulnerabilities", [{}])[0].get("vulnerability") if r.get("vulnerabilities") else None)
        )
        if key and key not in seen:
            seen.add(key)
            unique_records.append(r)
        elif not key:
            # Records without vulnerability text - keep them but dedupe by other fields
            # Use source_context or chunk_id as fallback key
            fallback_key = (
                r.get("source_context") or
                r.get("chunk_id") or
                str(r.get("source_file", "")) + str(r.get("source_page", ""))
            )
            if fallback_key and fallback_key not in seen:
                seen.add(fallback_key)
                unique_records.append(r)
    
    # Collapse duplicates by vulnerability + ofc text pair (optional: one-to-one mapping)
    pair_seen = set()
    final_unique = []
    for v in unique_records:
        # Extract vulnerability text
        vuln_text = v.get("vulnerability") or ""
        if not vuln_text and v.get("vulnerabilities"):
            first_vuln = v.get("vulnerabilities", [{}])[0]
            vuln_text = first_vuln.get("vulnerability", "")
        
        # Extract OFC text
        ofc_text = (
            v.get("ofc") or
            (v.get("options_for_consideration", [None])[0] if v.get("options_for_consideration") else "")
        )
        if isinstance(ofc_text, list) and ofc_text:
            ofc_text = ofc_text[0]
        if isinstance(ofc_text, dict):
            ofc_text = ofc_text.get("text") or ofc_text.get("option_text") or ""
        ofc_text = str(ofc_text) if ofc_text else ""
        
        # Create pair key (normalize to lowercase for comparison)
        pair = (vuln_text.strip().lower(), ofc_text.strip().lower())
        if pair not in pair_seen:
            pair_seen.add(pair)
            final_unique.append(v)
    
    records = final_unique
    deduped_count = len(data.get("records") or data.get("all_phase2_records", [])) - len(records)
    if deduped_count > 0:
        logger.info(f"[SYNC-V2] Deduplicated {deduped_count} duplicate records, processing {len(records)} unique records")
    else:
        logger.info(f"[SYNC-V2] Processing {len(records)} records (no duplicates found)")
    submission_ids = []
    
    # Track seen pairs to prevent duplicate submissions
    seen_pairs = set()
    
    # Process each vulnerability as individual submission
    # First, extract all vulnerabilities from all records
    all_vulnerability_records = []
    
    for idx, record in enumerate(records, start=1):
        try:
            # Extract vulnerabilities and OFCs from this record
            vulnerabilities, ofcs = extract_record_data(record)
            
            if not vulnerabilities:
                logger.debug(f"[SYNC-V2] Record {idx} has no vulnerabilities, skipping")
                continue
            
            # Create one submission per vulnerability
            for vuln_idx, vuln in enumerate(vulnerabilities):
                vuln_text = vuln.get("vulnerability", "").strip()
                if not vuln_text:
                    continue
                
                # Find OFCs associated with this vulnerability
                # Match OFCs by linked_vulnerability or use all OFCs if no link specified
                linked_ofcs = []
                vuln_ref = vuln_text.lower()
                
                for ofc in ofcs:
                    ofc_vuln_ref = ofc.get("vulnerability", "").strip().lower()
                    # If OFC has no specific vulnerability link, or it matches this vulnerability
                    if not ofc_vuln_ref or ofc_vuln_ref == vuln_ref or vuln_ref in ofc_vuln_ref or ofc_vuln_ref in vuln_ref:
                        linked_ofcs.append(ofc)
                
                # If no linked OFCs found, use all OFCs from the record (fallback)
                if not linked_ofcs and ofcs:
                    linked_ofcs = ofcs
                
                # Skip if no OFCs (must have at least one OFC per vulnerability)
                if not linked_ofcs:
                    logger.debug(f"[SYNC-V2] Vulnerability {vuln_idx+1} in record {idx} has no OFCs, skipping")
                    continue
                
                # De-duplicate by vulnerability text
                pair_key = f"{vuln_text.strip().lower()}"
                if pair_key in seen_pairs:
                    logger.debug(f"[SYNC-V2] Skipping duplicate vulnerability: {vuln_text[:50]}...")
                    continue
                seen_pairs.add(pair_key)
                
                # Store for processing (one submission per vulnerability)
                all_vulnerability_records.append({
                    "vulnerability": vuln,
                    "ofcs": linked_ofcs,
                    "record": record,
                    "record_idx": idx,
                    "vuln_idx": vuln_idx
                })
                
        except Exception as e:
            logger.error(f"[SYNC-V2] Error processing record {idx}: {e}")
            continue
    
    logger.info(f"[SYNC-V2] Processing {len(all_vulnerability_records)} individual vulnerabilities as separate submissions")
    
    # Check for duplicates against database before creating submissions
    try:
        from tools.check_database_duplicates import filter_duplicate_records
        supabase = get_supabase_client()
        
        # Convert to records format for duplicate checking
        records_to_check = []
        for item in all_vulnerability_records:
            vuln = item["vulnerability"]
            ofcs = item["ofcs"]
            record = {
                "vulnerability": vuln.get("vulnerability", ""),
                "options_for_consideration": ofcs,
                "ofc": ofcs[0] if ofcs and isinstance(ofcs[0], str) else (ofcs[0].get("option_text") if ofcs and isinstance(ofcs[0], dict) else None)
            }
            records_to_check.append(record)
        
        # Filter duplicates
        filtered_records, duplicate_count = filter_duplicate_records(
            records_to_check,
            supabase_client=supabase,
            vuln_threshold=0.85,
            ofc_threshold=0.85
        )
        
        if duplicate_count > 0:
            logger.info(f"[SYNC-V2] ⏭️  Filtered out {duplicate_count} duplicate records before submission creation")
        
        # Map filtered records back to items
        filtered_items = []
        filtered_vuln_texts = {r.get("vulnerability", "").strip().lower() for r in filtered_records}
        
        for item in all_vulnerability_records:
            vuln_text = item["vulnerability"].get("vulnerability", "").strip().lower()
            if vuln_text in filtered_vuln_texts:
                filtered_items.append(item)
        
        all_vulnerability_records = filtered_items
        logger.info(f"[SYNC-V2] After duplicate filtering: {len(all_vulnerability_records)} unique vulnerabilities to process")
    except Exception as e:
        logger.warning(f"[SYNC-V2] Duplicate checking failed (non-critical): {e}")
        # Continue without duplicate filtering if it fails
        import traceback
        logger.debug(f"[SYNC-V2] Traceback: {traceback.format_exc()}")
    
    # Now create one submission per vulnerability
    for item_idx, item in enumerate(all_vulnerability_records, start=1):
        try:
            vuln = item["vulnerability"]
            ofcs = item["ofcs"]
            record = item["record"]
            record_idx = item["record_idx"]
            vuln_idx = item["vuln_idx"]
            
            vuln_text = vuln.get("vulnerability", "").strip()
            if not vuln_text:
                continue
            
            # Optional: Filter by confidence score
            confidence_score = convert_confidence(
                vuln.get("confidence_score") or record.get("confidence_score") or 0
            )
            if confidence_score < 0.5:
                logger.debug(f"[SYNC-V2] Skipping vulnerability {item_idx}: low confidence ({confidence_score:.2f} < 0.5)")
                continue
            
            logger.info(f"[SYNC-V2] Processing vulnerability {item_idx}/{len(all_vulnerability_records)}: {vuln_text[:60]}...")
            logger.info(f"[SYNC-V2]   Associated with {len(ofcs)} OFC(s)")
            
            # Create submission - ONE PER VULNERABILITY
            submission_id = str(uuid.uuid4())
            submission_data = {
                "id": submission_id,
                "type": "vulnerability",
                "status": "pending_review",
                "source": "psa_tool_auto",
                "submitter_email": submitter_email,
                "data": {
                    "source_file": record.get("source_file") or data.get("source_file"),
                    "source_page": record.get("source_page") or record.get("page_range"),
                    "chunk_id": record.get("chunk_id"),
                    "processed_at": datetime.utcnow().isoformat(),
                    "vulnerabilities": [vuln],  # Single vulnerability per submission
                    "options_for_consideration": ofcs,
                    "record_index": record_idx,
                    "vuln_index": vuln_idx,
                    "total_vulnerabilities": len(all_vulnerability_records),
                },
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            document_name = record.get("source_file") or data.get("source_file") or data.get("document_name")
            if document_name:
                submission_data["document_name"] = document_name
            
            # Insert submission
            try:
                result = supabase.table("submissions").insert(submission_data).execute()
                if result.data:
                    submission_ids.append(submission_id)
                    logger.info(f"[SYNC-V2] ✅ Created submission {submission_id}")
                else:
                    logger.error(f"[SYNC-V2] ❌ Insert returned no data for record {idx}")
                    continue
            except Exception as e:
                logger.error(f"[SYNC-V2] ❌ Failed to create submission for record {idx}: {e}")
                continue
            
            # Resolve taxonomy IDs for this single vulnerability
            discipline_name = vuln.get("discipline")
            if discipline_name:
                disc_record = get_discipline_record(discipline_name, fuzzy=True)
                if disc_record:
                    vuln["discipline_id"] = disc_record.get("id")
                    if not vuln.get("category"):
                        vuln["category"] = disc_record.get("category")
                else:
                    logger.warning(f"[SYNC-V2] Discipline not found: {discipline_name}")
            
            # Resolve sector (with fuzzy matching)
            sector_name = vuln.get("sector")
            if sector_name:
                sector_id = get_sector_id(sector_name, fuzzy=True)
                if sector_id:
                    vuln["sector_id"] = sector_id
                else:
                    logger.warning(f"[SYNC-V2] Sector not found: {sector_name}")
            
            # Resolve subsector (with fuzzy matching)
            subsector_name = vuln.get("subsector")
            if subsector_name:
                subsector_id = get_subsector_id(subsector_name, fuzzy=True)
                if subsector_id:
                    vuln["subsector_id"] = subsector_id
                else:
                    logger.warning(f"[SYNC-V2] Subsector not found: {subsector_name}")
            
            # Insert single vulnerability (one per submission)
            vuln_id_map = {}  # vulnerability_text -> vulnerability_id
            vuln_id = str(uuid.uuid4())
            vuln_text = vuln.get("vulnerability", "").strip()
            
            if not vuln_text:
                logger.warning(f"[SYNC-V2] Vulnerability {item_idx} has no text, skipping")
                continue
            
            # Ensure vulnerability text is a proper sentence (capitalize first letter, end with period if needed)
            vuln_text = vuln_text.strip()
            if vuln_text and not vuln_text[0].isupper():
                vuln_text = vuln_text[0].upper() + vuln_text[1:] if len(vuln_text) > 1 else vuln_text.upper()
            if vuln_text and not vuln_text.endswith(('.', '!', '?')):
                vuln_text = vuln_text + '.'
            
            # Get description from source_context (don't append to vulnerability_name)
            source_context = vuln.get("source_context", "").strip()
            description = source_context or vuln.get("description") or ""
            
            # Build vulnerability record matching production table structure
            # Production: vulnerability_name, description, discipline, sector_id, subsector_id, severity_level
            vuln_rec = {
                "id": vuln_id,
                "submission_id": submission_id,
                # Mirror production table: vulnerability_name (not "vulnerability")
                "vulnerability_name": vuln_text,
                # Mirror production table: description (use source_context or empty)
                "description": description,
                # Mirror production table: discipline (text, not ID)
                "discipline": vuln.get("discipline"),
                # Mirror production table: sector_id, subsector_id
                "sector_id": vuln.get("sector_id"),
                "subsector_id": vuln.get("subsector_id"),
                # Mirror production table: severity_level (if available)
                "severity_level": vuln.get("severity_level") or record.get("severity_level"),
                # Additional submission-specific fields (preserved for metadata)
                "discipline_id": vuln.get("discipline_id"),  # Keep for reference
                "sector": vuln.get("sector"),  # Keep name for reference
                "subsector": vuln.get("subsector"),  # Keep name for reference
                "source_context": source_context,
                "confidence_score": vuln.get("confidence_score"),
                "page_ref": record.get("source_page") or record.get("page_range"),
                "chunk_id": record.get("chunk_id"),
                "source_file": record.get("source_file") or data.get("source_file"),
                "source_title": record.get("source_file") or data.get("source_file"),
            }
            vuln_rec = {k: v for k, v in vuln_rec.items() if v is not None}
            vuln_records = [vuln_rec]
            
            # Store for linking
            vuln_id_map[vuln_text] = vuln_id
            vuln_id_map[vuln_text.lower()] = vuln_id
            
            if vuln_records:
                try:
                    supabase.table("submission_vulnerabilities").insert(vuln_records).execute()
                    logger.info(f"[SYNC-V2] Inserted {len(vuln_records)} vulnerabilities")
                except Exception as e:
                    logger.warning(f"[SYNC-V2] Failed to insert vulnerabilities: {e}")
            
            # Insert OFCs
            # Deduplicate OFCs by option_text before inserting
            ofc_dedup_map = {}
            for ofc in ofcs:
                ofc_text = ofc.get("option_text", "").strip()
                if ofc_text:
                    # Use option_text as key for deduplication
                    if ofc_text not in ofc_dedup_map:
                        ofc_dedup_map[ofc_text] = ofc
                    else:
                        # If duplicate, merge confidence scores (keep higher)
                        existing = ofc_dedup_map[ofc_text]
                        existing_conf = existing.get("confidence_score", 0)
                        new_conf = ofc.get("confidence_score", 0)
                        if new_conf > existing_conf:
                            existing["confidence_score"] = new_conf
            
            # Convert back to list
            ofcs = list(ofc_dedup_map.values())
            
            ofc_records = []
            ofc_id_map = {}  # ofc_text -> {ofc_id, vulnerability_ref}
            
            for ofc in ofcs:
                ofc_id = str(uuid.uuid4())
                ofc_text = ofc.get("option_text", "").strip()
                vuln_ref = ofc.get("vulnerability", "").strip()
                
                if not ofc_text:
                    continue
                
                # Get source info from record
                source_file = record.get("source_file") or data.get("source_file") or ""
                source_context = ofc.get("source_context") or record.get("source_context") or ""
                
                # Build OFC record matching production table structure
                # Production: option_text, discipline, sector_id, subsector_id
                ofc_rec = {
                    "id": ofc_id,
                    "submission_id": submission_id,
                    # Mirror production table: option_text
                    "option_text": ofc_text,
                    # Mirror production table: discipline (text, not ID)
                    "discipline": ofc.get("discipline") or vuln.get("discipline"),
                    # Mirror production table: sector_id, subsector_id
                    "sector_id": ofc.get("sector_id") or vuln.get("sector_id"),
                    "subsector_id": ofc.get("subsector_id") or vuln.get("subsector_id"),
                    # Additional submission-specific fields (preserved for metadata)
                    "vulnerability_id": vuln_id,  # Link to submission_vulnerabilities
                    "confidence_score": ofc.get("confidence_score"),
                    "source": source_file or source_context,
                    "source_title": source_file,
                    "source_url": record.get("source_url") or data.get("source_url"),
                    "context": source_context,
                    "linked_vulnerability": vuln_ref,  # Text reference to parent vulnerability
                }
                # Only include non-None values
                ofc_rec = {k: v for k, v in ofc_rec.items() if v is not None}
                ofc_records.append(ofc_rec)
                
                # Store for linking
                ofc_id_map[ofc_text] = {
                    "ofc_id": ofc_id,
                    "vulnerability_ref": vuln_ref
                }
            
            if ofc_records:
                try:
                    result = supabase.table("submission_options_for_consideration").insert(ofc_records).execute()
                    if result.data:
                        logger.info(f"[SYNC-V2] ✅ Inserted {len(ofc_records)} OFCs into submission {submission_id}")
                    else:
                        logger.error(f"[SYNC-V2] ❌ OFC insert returned no data for submission {submission_id}")
                except Exception as e:
                    logger.error(f"[SYNC-V2] ❌ Failed to insert OFCs for submission {submission_id}: {e}")
                    import traceback
                    logger.error(f"[SYNC-V2] Traceback: {traceback.format_exc()}")
            else:
                logger.warning(f"[SYNC-V2] No OFC records to insert for submission {submission_id} (extracted {len(ofcs)} OFCs)")
            
            # Create vulnerability-OFC links
            link_count = 0
            for ofc_text, ofc_info in ofc_id_map.items():
                vuln_ref = ofc_info["vulnerability_ref"]
                if not vuln_ref:
                    continue
                
                # Find matching vulnerability ID
                vuln_id = vuln_id_map.get(vuln_ref) or vuln_id_map.get(vuln_ref.lower())
                
                if vuln_id:
                    link_record = {
                        "id": str(uuid.uuid4()),
                        "submission_id": submission_id,
                        "vulnerability_id": vuln_id,
                        "ofc_id": ofc_info["ofc_id"],
                        "link_type": "direct",
                        "confidence_score": 0.9,
                    }
                    try:
                        supabase.table("submission_vulnerability_ofc_links").insert(link_record).execute()
                        link_count += 1
                    except Exception as e:
                        logger.warning(f"[SYNC-V2] Failed to insert link: {e}")
                else:
                    logger.warning(f"[SYNC-V2] Could not match OFC to vulnerability: '{vuln_ref[:50]}...'")
            
            logger.info(f"[SYNC-V2] Created {link_count} vulnerability-OFC links")
            
            # Insert source
            source_file = record.get("source_file") or data.get("source_file")
            source_id = None
            if source_file:
                source_id = str(uuid.uuid4())
                source_rec = {
                    "id": source_id,
                    "submission_id": submission_id,
                    "source_title": source_file,
                    "source_file": source_file,
                    "page_ref": record.get("source_page") or record.get("page_range"),
                    "chunk_id": record.get("chunk_id"),
                }
                try:
                    supabase.table("submission_sources").insert(source_rec).execute()
                    logger.info(f"[SYNC-V2] Inserted source")
                except Exception as e:
                    logger.warning(f"[SYNC-V2] Failed to insert source: {e}")
            
            # Create OFC-source links
            if source_id and ofc_id_map:
                for ofc_text, ofc_info in ofc_id_map.items():
                    ofc_source_link = {
                        "id": str(uuid.uuid4()),
                        "submission_id": submission_id,
                        "ofc_id": ofc_info["ofc_id"],
                        "source_id": source_id,
                        "page_ref": record.get("source_page") or record.get("page_range"),
                        "chunk_id": record.get("chunk_id"),
                    }
                    try:
                        supabase.table("submission_ofc_sources").insert(ofc_source_link).execute()
                    except Exception as e:
                        logger.warning(f"[SYNC-V2] Failed to insert OFC-source link: {e}")
            
            logger.info(f"[SYNC-V2] ✅ Completed record {idx}/{len(records)}")
            
        except Exception as e:
            logger.error(f"[SYNC-V2] ❌ Error processing record {idx}: {e}")
            import traceback
            logger.error(f"[SYNC-V2] Traceback: {traceback.format_exc()}")
            continue
    
    logger.info(f"[SYNC-V2] ✅ Created {len(submission_ids)} submissions total")
    return submission_ids

