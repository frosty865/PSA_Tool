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
                source_context = vuln_item.get("source_context", "").strip() or record.get("source_context", "").strip()
                ofc_text = vuln_item.get("ofc", "").strip() or vuln_item.get("options_for_consideration", "")
                
                # Try to infer vulnerability from context
                if source_context:
                    # If source_context describes a deficiency, use it as vulnerability
                    if any(word in source_context.lower() for word in ["lack", "missing", "does not", "without", "insufficient", "not"]):
                        vuln_text = source_context
                    # Otherwise, create a vulnerability statement from the OFC
                    elif ofc_text:
                        # Convert OFC to vulnerability: "Install X" -> "The facility lacks X" or "X is not installed"
                        vuln_text = f"The facility may benefit from {ofc_text.lower()}"
                    else:
                        # Last resort: use source_context as-is
                        vuln_text = source_context
                
                # If still no vulnerability text, skip this item
                if not vuln_text or len(vuln_text.strip()) < 10:
                    logger.warning(f"[SYNC-V2] Skipping item - no vulnerability text and cannot derive from context")
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
    
    # Handle format: {vulnerability: "text", ofc: "text"} - single pair
    elif "vulnerability" in record and record.get("vulnerability"):
        vuln_text = record.get("vulnerability", "").strip()
        
        # If no explicit vulnerability, try to derive from source_context or OFC
        if not vuln_text:
            source_context = record.get("source_context", "").strip()
            ofc_text = record.get("ofc", "").strip() or record.get("options_for_consideration", "")
            
            # Try to infer vulnerability from context
            if source_context:
                # If source_context describes a deficiency, use it as vulnerability
                if any(word in source_context.lower() for word in ["lack", "missing", "does not", "without", "insufficient", "not"]):
                    vuln_text = source_context
                # Otherwise, create a vulnerability statement from the OFC
                elif ofc_text:
                    # Convert OFC to vulnerability: "Install X" -> "The facility lacks X" or "X is not installed"
                    vuln_text = f"The facility may benefit from {ofc_text.lower()}"
                else:
                    # Last resort: use source_context as-is
                    vuln_text = source_context
        
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
                    ofc_text = ofc_item if isinstance(ofc_item, str) else ofc_item.get("text", "") or ofc_item.get("option_text", "")
                    if ofc_text and ofc_text.strip():
                        ofcs.append({
                            "option_text": ofc_text.strip(),
                            "vulnerability": vuln_text,  # Link to parent vulnerability
                            "discipline": record.get("discipline"),
                            "sector": record.get("sector"),
                            "subsector": record.get("subsector"),
                            "confidence_score": confidence_score,
                        })
            # Handle single OFC string (1 vulnerability -> 1 OFC)
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
    
    # Extract records
    records = data.get("records", [])
    if not records:
        logger.warning(f"[SYNC-V2] No records found in {result_path}")
        return []
    
    logger.info(f"[SYNC-V2] Processing {len(records)} records")
    submission_ids = []
    
    # Process each record as individual submission
    for idx, record in enumerate(records, start=1):
        try:
            logger.info(f"[SYNC-V2] Processing record {idx}/{len(records)}")
            
            # Extract vulnerabilities and OFCs
            vulnerabilities, ofcs = extract_record_data(record)
            
            if not vulnerabilities and not ofcs:
                logger.warning(f"[SYNC-V2] Record {idx} has no vulnerabilities or OFCs, skipping")
                continue
            
            logger.info(f"[SYNC-V2] Record {idx}: {len(vulnerabilities)} vuln(s), {len(ofcs)} OFC(s)")
            if ofcs:
                logger.info(f"[SYNC-V2]   First OFC sample: {ofcs[0].get('option_text', 'NO OPTION_TEXT')[:50]}")
            
            # Create submission
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
                    "vulnerabilities": vulnerabilities,
                    "options_for_consideration": ofcs,
                    "record_index": idx,
                    "total_records": len(records),
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
            
            # Resolve taxonomy IDs for vulnerabilities
            vuln_id_map = {}  # vulnerability_text -> vulnerability_id
            
            for vuln in vulnerabilities:
                # Resolve discipline (with fuzzy matching to handle name variations)
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
            
            # Insert vulnerabilities
            vuln_records = []
            for vuln in vulnerabilities:
                vuln_id = str(uuid.uuid4())
                vuln_text = vuln.get("vulnerability", "").strip()
                
                if not vuln_text:
                    continue
                
                # Ensure vulnerability text is a proper sentence (capitalize first letter, end with period if needed)
                vuln_text = vuln_text.strip()
                if vuln_text and not vuln_text[0].isupper():
                    vuln_text = vuln_text[0].upper() + vuln_text[1:] if len(vuln_text) > 1 else vuln_text.upper()
                if vuln_text and not vuln_text.endswith(('.', '!', '?')):
                    vuln_text = vuln_text + '.'
                
                # Enhance vulnerability text with source_context if available (for better description)
                source_context = vuln.get("source_context", "").strip()
                if source_context and source_context not in vuln_text:
                    # Append context to vulnerability text for richer description
                    vuln_text = f"{vuln_text} {source_context}".strip()
                
                vuln_rec = {
                    "id": vuln_id,
                    "submission_id": submission_id,
                    "vulnerability": vuln_text,
                    "discipline_id": vuln.get("discipline_id"),
                    "discipline": vuln.get("discipline"),
                    "sector_id": vuln.get("sector_id"),
                    "sector": vuln.get("sector"),
                    "subsector_id": vuln.get("subsector_id"),
                    "subsector": vuln.get("subsector"),
                    "source_context": vuln.get("source_context"),
                    "confidence_score": vuln.get("confidence_score"),
                    "page_ref": record.get("source_page") or record.get("page_range"),
                    "chunk_id": record.get("chunk_id"),
                    "source_file": record.get("source_file") or data.get("source_file"),
                    "source_title": record.get("source_file") or data.get("source_file"),
                }
                vuln_rec = {k: v for k, v in vuln_rec.items() if v is not None}
                vuln_records.append(vuln_rec)
                
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
                
                ofc_rec = {
                    "id": ofc_id,
                    "submission_id": submission_id,
                    "option_text": ofc_text,
                    "discipline": ofc.get("discipline"),
                    "confidence_score": ofc.get("confidence_score"),
                    "source": source_file or source_context,  # Use source_file as source
                    "source_title": source_file,  # Use source_file as source_title
                    "source_url": record.get("source_url") or data.get("source_url"),
                    "context": source_context,  # Use source_context as context field
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

