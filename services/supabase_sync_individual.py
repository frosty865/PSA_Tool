"""
Individual Submission Sync - Break down large JSONs into individual submissions (one per record)
"""

import json
import logging
import uuid
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from services.supabase_client import get_supabase_client, get_discipline_record, get_sector_id, get_subsector_id
from services.supabase_sync import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

logger = logging.getLogger(__name__)


def sync_individual_records(result_path: str, submitter_email: str = "system@psa.local") -> List[str]:
    """
    Break down a large JSON file into individual submissions (one per record).
    Each record becomes its own submission in the submissions table.
    
    Args:
        result_path: Path to the processed JSON result file
        submitter_email: Email of the submitter (default: system@psa.local)
    
    Returns:
        List of submission IDs created
    """
    logger.info(f"[SYNC-INDIVIDUAL] Starting individual record sync for: {result_path}")
    
    # Verify Supabase client is available
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        error_msg = f"Supabase credentials not configured"
        logger.error(f"[SYNC-INDIVIDUAL] {error_msg}")
        raise ValueError(error_msg)
    
    # Get Supabase client
    try:
        supabase = get_supabase_client()
    except Exception as client_err:
        error_msg = f"Failed to initialize Supabase client: {client_err}"
        logger.error(f"[SYNC-INDIVIDUAL] {error_msg}")
        raise ValueError(error_msg)
    
    # Read the result file
    result_file = Path(result_path)
    if not result_file.exists():
        error_msg = f"Result file not found: {result_path}"
        logger.error(f"[SYNC-INDIVIDUAL] {error_msg}")
        raise FileNotFoundError(error_msg)
    
    file_size = result_file.stat().st_size
    logger.info(f"[SYNC-INDIVIDUAL] Reading result file: {result_file} ({file_size} bytes)")
    
    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    logger.info(f"[SYNC-INDIVIDUAL] Loaded JSON data. Top-level keys: {list(data.keys())}")
    
    # Extract records from Phase 1 parser format
    records = []
    if "records" in data and isinstance(data.get("records"), list):
        records = data.get("records", [])
        logger.info(f"[SYNC-INDIVIDUAL] Found {len(records)} records in Phase 1 parser format")
    else:
        logger.warning(f"[SYNC-INDIVIDUAL] No 'records' array found. Data keys: {list(data.keys())}")
        return []
    
    submission_ids = []
    
    # Process each record as an individual submission
    for idx, record in enumerate(records, start=1):
        try:
            # Extract vulnerabilities and OFCs from this record
            vulnerabilities = []
            ofcs = []
            
            # PRIORITY: Check for direct vulnerability/ofc fields first (Phase 2 format)
            # This is the correct format from Phase 2 Lite Classifier
            if "vulnerability" in record and record.get("vulnerability"):
                vuln_text = record.get("vulnerability", "").strip()
                if vuln_text:
                    # Convert confidence string to float if needed
                    confidence = record.get("confidence") or record.get("confidence_score")
                    if isinstance(confidence, str):
                        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5, "very low": 0.3}
                        confidence_score = confidence_map.get(confidence.lower(), 0.7)
                    else:
                        confidence_score = float(confidence) if confidence is not None else 0.7
                    
                    vulnerabilities.append({
                        "vulnerability": vuln_text,
                        "discipline": record.get("discipline"),
                        "sector": record.get("sector"),
                        "subsector": record.get("subsector"),
                        "source_context": record.get("source_context"),
                        "confidence_score": confidence_score,
                    })
                    
                    # Handle OFC - can be string or array
                    ofc_data = record.get("ofc") or record.get("option_text") or record.get("options_for_consideration")
                    if ofc_data:
                        # If it's a list, process each item (1 vulnerability -> many OFCs)
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
                        # If it's a string, add it directly (1 vulnerability -> 1 OFC)
                        elif isinstance(ofc_data, str) and ofc_data.strip():
                            ofcs.append({
                                "option_text": ofc_data.strip(),
                                "vulnerability": vuln_text,  # Link to parent vulnerability
                                "discipline": record.get("discipline"),
                                "sector": record.get("sector"),
                                "subsector": record.get("subsector"),
                                "confidence_score": confidence_score,
                            })
            
            # FALLBACK: Handle nested vulnerabilities array (Phase 1 format or legacy)
            elif "vulnerabilities" in record and isinstance(record.get("vulnerabilities"), list) and len(record.get("vulnerabilities", [])) > 0:
                for vuln_item in record.get("vulnerabilities", []):
                    # Handle different formats: dict, string (PowerShell object representation), or already parsed
                    vuln_obj = None
                    
                    if isinstance(vuln_item, dict):
                        vuln_obj = vuln_item
                    elif isinstance(vuln_item, str):
                        # Try to parse PowerShell object string format: "@{key=value; key2=value2}"
                        # Or it might be a plain vulnerability text
                        if vuln_item.strip().startswith("@{"):
                            # Parse PowerShell hashtable string
                            try:
                                # Extract key-value pairs from "@{key=value; key2=value2}" format
                                pairs = re.findall(r'(\w+)=([^;]+)', vuln_item)
                                vuln_obj = {}
                                for key, value in pairs:
                                    vuln_obj[key.strip()] = value.strip().strip('"').strip("'")
                            except Exception as parse_err:
                                logger.warning(f"[SYNC-INDIVIDUAL] Failed to parse PowerShell object string: {vuln_item[:100]}")
                                # Treat as plain vulnerability text
                                vuln_obj = {"vulnerability": vuln_item}
                        else:
                            # Plain text vulnerability
                            vuln_obj = {"vulnerability": vuln_item}
                    
                    if not vuln_obj:
                        continue
                    
                    # Extract vulnerability text (may be missing if only OFC is present)
                    vuln_text = vuln_obj.get("vulnerability", "") or vuln_obj.get("text", "")
                    
                    # Convert confidence string to float if needed
                    confidence = vuln_obj.get("confidence") or vuln_obj.get("confidence_score")
                    if isinstance(confidence, str):
                        # Map confidence strings to numeric values
                        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5, "very low": 0.3}
                        confidence_score = confidence_map.get(confidence.lower(), 0.7)
                    else:
                        confidence_score = float(confidence) if confidence is not None else 0.7
                    
                    # Extract OFC from vulnerability object
                    ofc_text = vuln_obj.get("ofc") or vuln_obj.get("option_text")
                    
                    # If we have a vulnerability, add it
                    if vuln_text and vuln_text.strip():
                        vulnerabilities.append({
                            "vulnerability": vuln_text.strip(),
                            "discipline": vuln_obj.get("discipline"),
                            "sector": vuln_obj.get("sector"),
                            "subsector": vuln_obj.get("subsector"),
                            "source_context": vuln_obj.get("source_context"),
                            "confidence_score": confidence_score,
                        })
                        
                        # If OFC exists, link it to this vulnerability
                        if ofc_text and ofc_text.strip():
                            ofcs.append({
                                "option_text": ofc_text.strip() if isinstance(ofc_text, str) else str(ofc_text).strip(),
                                "vulnerability": vuln_text.strip(),
                                "discipline": vuln_obj.get("discipline"),
                                "sector": vuln_obj.get("sector"),
                                "subsector": vuln_obj.get("subsector"),
                                "confidence_score": confidence_score,
                            })
                    # If no vulnerability but we have OFC, add OFC with empty vulnerability
                    elif ofc_text and ofc_text.strip():
                        ofcs.append({
                            "option_text": ofc_text.strip() if isinstance(ofc_text, str) else str(ofc_text).strip(),
                            "vulnerability": "",  # No vulnerability text, just OFC
                            "discipline": vuln_obj.get("discipline"),
                            "sector": vuln_obj.get("sector"),
                            "subsector": vuln_obj.get("subsector"),
                            "confidence_score": confidence_score,
                        })
            
            # Skip records with no vulnerabilities or OFCs
            if not vulnerabilities and not ofcs:
                logger.debug(f"[SYNC-INDIVIDUAL] Skipping record {idx} - no vulnerabilities or OFCs")
                logger.debug(f"[SYNC-INDIVIDUAL] Record keys: {list(record.keys()) if isinstance(record, dict) else 'not a dict'}")
                continue
            
            logger.info(f"[SYNC-INDIVIDUAL] Record {idx}: {len(vulnerabilities)} vulnerabilities, {len(ofcs)} OFCs")
            
            # Create submission for this record
            submission_id = str(uuid.uuid4())
            
            # Build submission data
            # Type must be "vulnerability" or "ofc" per database constraint
            # Use "vulnerability" since records contain both vulnerabilities and OFCs
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
            
            # Add document_name if available
            document_name = record.get("source_file") or data.get("source_file") or data.get("document_name")
            if document_name:
                submission_data["document_name"] = document_name
            
            # Insert submission
            try:
                logger.debug(f"[SYNC-INDIVIDUAL] Inserting submission {submission_id} for record {idx}")
                logger.debug(f"[SYNC-INDIVIDUAL] Submission data keys: {list(submission_data.keys())}")
                logger.debug(f"[SYNC-INDIVIDUAL] Vulnerabilities: {len(vulnerabilities)}, OFCs: {len(ofcs)}")
                
                result = supabase.table("submissions").insert(submission_data).execute()
                if result.data:
                    submission_ids.append(submission_id)
                    logger.info(f"[SYNC-INDIVIDUAL] ✅ Created submission {submission_id} for record {idx}/{len(records)} ({len(vulnerabilities)} vulns, {len(ofcs)} OFCs)")
                else:
                    logger.error(f"[SYNC-INDIVIDUAL] ❌ Insert returned no data for record {idx}")
                    logger.error(f"[SYNC-INDIVIDUAL] Submission data: {json.dumps(submission_data, indent=2, default=str)[:500]}")
            except Exception as e:
                logger.error(f"[SYNC-INDIVIDUAL] ❌ Error creating submission for record {idx}: {e}")
                import traceback
                logger.error(f"[SYNC-INDIVIDUAL] Traceback: {traceback.format_exc()}")
                logger.error(f"[SYNC-INDIVIDUAL] Submission data keys: {list(submission_data.keys())}")
                continue
            
            # Insert into all 6 submission tables
            try:
                # Resolve taxonomy IDs for vulnerabilities
                vuln_id_map = {}  # Map vulnerability text to vulnerability_id for linking
                
                for vuln in vulnerabilities:
                    # Resolve discipline
                    discipline_name = vuln.get("discipline")
                    if discipline_name:
                        disc_record = get_discipline_record(discipline_name)
                        if disc_record:
                            vuln["discipline_id"] = disc_record.get("id")
                            if not vuln.get("category"):
                                vuln["category"] = disc_record.get("category")
                    
                    # Resolve sector
                    sector_name = vuln.get("sector")
                    if sector_name:
                        sector_id = get_sector_id(sector_name)
                        if sector_id:
                            vuln["sector_id"] = sector_id
                    
                    # Resolve subsector
                    subsector_name = vuln.get("subsector")
                    if subsector_name:
                        subsector_id = get_subsector_id(subsector_name)
                        if subsector_id:
                            vuln["subsector_id"] = subsector_id
                
                # 2. Insert vulnerabilities into submission_vulnerabilities
                vuln_records = []
                for vuln in vulnerabilities:
                    vuln_id = str(uuid.uuid4())
                    vuln_text = vuln.get("vulnerability", "").strip()
                    
                    if not vuln_text:
                        continue  # Skip empty vulnerabilities
                    
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
                    # Remove None values
                    vuln_rec = {k: v for k, v in vuln_rec.items() if v is not None}
                    vuln_records.append(vuln_rec)
                    
                    # Store mapping for linking (multiple keys for robust matching)
                    if vuln_text:
                        # Store exact match
                        vuln_id_map[vuln_text] = vuln_id
                        # Store normalized (lowercase) for case-insensitive matching
                        vuln_id_map[vuln_text.lower()] = vuln_id
                        # Store first 100 chars for partial matching
                        if len(vuln_text) > 100:
                            vuln_id_map[vuln_text[:100].lower()] = vuln_id
                
                if vuln_records:
                    try:
                        supabase.table("submission_vulnerabilities").insert(vuln_records).execute()
                        logger.debug(f"[SYNC-INDIVIDUAL] Inserted {len(vuln_records)} vulnerabilities for record {idx}")
                    except Exception as e:
                        logger.warning(f"[SYNC-INDIVIDUAL] Failed to insert vulnerabilities for record {idx}: {e}")
                
                # 3. Insert OFCs into submission_options_for_consideration
                ofc_records = []
                ofc_id_map = {}  # Store OFC IDs for linking
                
                for ofc in ofcs:
                    ofc_id = str(uuid.uuid4())
                    ofc_text = ofc.get("option_text", "").strip()
                    vuln_ref = ofc.get("vulnerability", "").strip()
                    
                    ofc_rec = {
                        "id": ofc_id,
                        "submission_id": submission_id,
                        "option_text": ofc_text,
                        "discipline": ofc.get("discipline"),
                        "confidence_score": ofc.get("confidence_score"),
                        "source_context": ofc.get("source_context") or record.get("source_context"),
                        "page_ref": record.get("source_page") or record.get("page_range"),
                        "chunk_id": record.get("chunk_id"),
                        "source_file": record.get("source_file") or data.get("source_file"),
                        "source_title": record.get("source_file") or data.get("source_file"),
                    }
                    # Remove None values
                    ofc_rec = {k: v for k, v in ofc_rec.items() if v is not None}
                    ofc_records.append(ofc_rec)
                    
                    # Store for linking
                    ofc_id_map[ofc_text] = {
                        "ofc_id": ofc_id,
                        "vulnerability_ref": vuln_ref
                    }
                
                if ofc_records:
                    try:
                        supabase.table("submission_options_for_consideration").insert(ofc_records).execute()
                        logger.debug(f"[SYNC-INDIVIDUAL] Inserted {len(ofc_records)} OFCs for record {idx}")
                    except Exception as e:
                        logger.warning(f"[SYNC-INDIVIDUAL] Failed to insert OFCs for record {idx}: {e}")
                
                # 4. Create vulnerability-OFC links in submission_vulnerability_ofc_links
                # CRITICAL: 1 vulnerability can have many OFCs - each OFC must link to its parent vulnerability
                link_count = 0
                unmatched_ofcs = []
                
                for ofc_text, ofc_info in ofc_id_map.items():
                    vuln_ref = ofc_info["vulnerability_ref"]
                    if not vuln_ref or not vuln_ref.strip():
                        logger.debug(f"[SYNC-INDIVIDUAL] OFC '{ofc_text[:50]}...' has no vulnerability reference, skipping link")
                        unmatched_ofcs.append(ofc_info)
                        continue
                    
                    vuln_ref = vuln_ref.strip()
                    
                    # Find matching vulnerability ID using multiple strategies
                    vuln_id = None
                    
                    # Strategy 1: Exact match (case-sensitive)
                    vuln_id = vuln_id_map.get(vuln_ref)
                    
                    # Strategy 2: Case-insensitive exact match
                    if not vuln_id:
                        vuln_id = vuln_id_map.get(vuln_ref.lower())
                    
                    # Strategy 3: Partial match - check if vulnerability text contains OFC's reference or vice versa
                    if not vuln_id:
                        # Get all unique vulnerability texts (exclude normalized duplicates)
                        unique_vuln_texts = [k for k in vuln_id_map.keys() if k == k.lower() or k.lower() not in vuln_id_map]
                        for vtext in unique_vuln_texts:
                            vid = vuln_id_map.get(vtext) or vuln_id_map.get(vtext.lower())
                            if vid:
                                vtext_lower = vtext.lower()
                                vuln_ref_lower = vuln_ref.lower()
                                # Check if reference is contained in vulnerability text or vice versa
                                if (vuln_ref_lower in vtext_lower or 
                                    vtext_lower in vuln_ref_lower or
                                    # Check first 100 chars for partial match
                                    (len(vuln_ref) > 50 and vuln_ref_lower[:50] in vtext_lower) or
                                    (len(vtext) > 50 and vtext_lower[:50] in vuln_ref_lower)):
                                    vuln_id = vid
                                    logger.debug(f"[SYNC-INDIVIDUAL] Matched OFC to vulnerability via partial match: '{vuln_ref[:50]}...' -> '{vtext[:50]}...'")
                                    break
                    
                    if vuln_id:
                        link_record = {
                            "id": str(uuid.uuid4()),
                            "submission_id": submission_id,
                            "vulnerability_id": vuln_id,
                            "ofc_id": ofc_info["ofc_id"],
                            "link_type": "direct",  # Direct link since OFC explicitly references vulnerability
                            "confidence_score": 0.9,  # High confidence when OFC has explicit vulnerability reference
                        }
                        try:
                            supabase.table("submission_vulnerability_ofc_links").insert(link_record).execute()
                            link_count += 1
                            logger.debug(f"[SYNC-INDIVIDUAL] ✅ Linked OFC '{ofc_text[:50]}...' to vulnerability {vuln_id}")
                        except Exception as e:
                            logger.warning(f"[SYNC-INDIVIDUAL] Failed to insert link for record {idx}: {e}")
                    else:
                        logger.warning(f"[SYNC-INDIVIDUAL] ⚠️  Could not match OFC '{ofc_text[:50]}...' to vulnerability '{vuln_ref[:50]}...'")
                        logger.debug(f"[SYNC-INDIVIDUAL] Available vulnerability texts: {list(set([k for k in vuln_id_map.keys() if k == k.lower() or k.lower() not in vuln_id_map]))[:3]}")
                        unmatched_ofcs.append(ofc_info)
                
                if unmatched_ofcs:
                    logger.warning(f"[SYNC-INDIVIDUAL] {len(unmatched_ofcs)} OFC(s) could not be linked to vulnerabilities")
                else:
                    logger.info(f"[SYNC-INDIVIDUAL] ✅ All {link_count} OFC(s) successfully linked to their vulnerabilities")
                
                # 5. Insert sources into submission_sources
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
                        logger.debug(f"[SYNC-INDIVIDUAL] Inserted source for record {idx}")
                    except Exception as e:
                        logger.warning(f"[SYNC-INDIVIDUAL] Failed to insert source for record {idx}: {e}")
                
                # 6. Create OFC-source links in submission_ofc_sources
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
                            logger.debug(f"[SYNC-INDIVIDUAL] Created OFC-source link for record {idx}")
                        except Exception as e:
                            logger.warning(f"[SYNC-INDIVIDUAL] Failed to insert OFC-source link for record {idx}: {e}")
                
                logger.info(f"[SYNC-INDIVIDUAL] Record {idx}: {len(vuln_records)} vulns, {len(ofc_records)} OFCs, {link_count} links, 1 source")
                        
            except Exception as insert_err:
                logger.warning(f"[SYNC-INDIVIDUAL] Failed to insert into submission tables for record {idx}: {insert_err}")
                import traceback
                logger.warning(f"[SYNC-INDIVIDUAL] Traceback: {traceback.format_exc()}")
                # Continue - submission record was created, that's the important part
            
        except Exception as e:
            logger.error(f"[SYNC-INDIVIDUAL] ❌ Error processing record {idx}: {e}")
            import traceback
            logger.error(f"[SYNC-INDIVIDUAL] Traceback: {traceback.format_exc()}")
            continue
    
    logger.info(f"[SYNC-INDIVIDUAL] ✅ Created {len(submission_ids)} individual submissions from {len(records)} records")
    return submission_ids

