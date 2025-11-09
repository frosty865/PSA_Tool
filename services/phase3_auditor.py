"""
Phase 3 Auditor — Physical Security Confidence Gate v1.0

Purpose: Cross-validate Phase2 output, apply confidence thresholds,
auto-reclassify ambiguous records, and log acceptance metrics for retraining.

Author: VOFC Engine Ops

Date: 2025-11-08
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Setup logging
logger = logging.getLogger(__name__)

def log_info(message: str):
    """Log info message."""
    logger.info(message)

def log_warn(message: str):
    """Log warning message."""
    logger.warning(message)

def log_error(message: str):
    """Log error message."""
    logger.error(message)

# Confidence parameters
MIN_ACCEPT_CONFIDENCE = 0.8
REVIEW_RANGE = (0.6, 0.8)

# Pairing parameters
PAIR_DISTANCE = 5  # Max index distance between vuln and ofc to consider a link

# Audit log path
AUDIT_LOG_DIR = Path(r"C:\Tools\VOFC_Logs")
AUDIT_LOG = AUDIT_LOG_DIR / "phase3_auditor.log"

# High-risk phrases that should be accepted even with lower confidence
HIGH_RISK_PHRASES = [
    "no access control",
    "no cctv",
    "no fence",
    "no guard",
    "open perimeter",
    "unauthorized access",
    "no security plan",
    "no surveillance",
    "unsecured entry",
    "no alarm",
    "no lighting",
    "no barrier"
]

# ----------------------------------------------------------------
# Pairing Logic
# ----------------------------------------------------------------

def pair_vulns_and_ofcs(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Link vulnerabilities and OFCs by proximity and context similarity.
    
    Input: list of Phase2-accepted records with 'intent' key.
    Output: list of linked record dictionaries with OFC references.
    """
    vulns = [r for r in records if r.get("intent") in ("vulnerability", "both")]
    ofcs = [r for r in records if r.get("intent") in ("ofc", "both")]
    
    if not vulns or not ofcs:
        log_info(f"[Phase3] No pairs possible: {len(vulns)} vulnerabilities, {len(ofcs)} OFCs")
        return []
    
    links = []
    
    # Use index positions within the accepted records list for proximity
    # This ensures we're pairing based on the order they appear in the document
    for i, v in enumerate(vulns):
        v_text = v.get("vulnerability", "")
        
        # Find nearest OFC within proximity window (based on index in accepted records)
        # Map OFCs to their positions in the original records list
        nearby = []
        for j, o in enumerate(ofcs):
            # Calculate distance based on position in the full records list
            # Find the index of this OFC in the original records
            o_idx_in_records = None
            for idx, r in enumerate(records):
                if r.get("vulnerability", "") == o.get("vulnerability", ""):
                    o_idx_in_records = idx
                    break
            
            # Find the index of this vulnerability in the original records
            v_idx_in_records = None
            for idx, r in enumerate(records):
                if r.get("vulnerability", "") == v_text:
                    v_idx_in_records = idx
                    break
            
            # Check proximity if both indices are found
            if o_idx_in_records is not None and v_idx_in_records is not None:
                if abs(v_idx_in_records - o_idx_in_records) <= PAIR_DISTANCE:
                    nearby.append((o, abs(v_idx_in_records - o_idx_in_records)))
        
        if not nearby:
            continue
        
        # Select the closest OFC (by distance), then by confidence if tied
        best_ofc, best_distance = min(nearby, key=lambda x: (x[1], -(x[0].get("confidence_score") or x[0].get("confidence") or 0)))
        
        link = {
            "vulnerability_text": v_text,
            "vulnerability_conf": v.get("confidence_score") or v.get("confidence") or 0,
            "ofc_text": best_ofc.get("vulnerability", ""),  # OFC stored in same field
            "ofc_conf": best_ofc.get("confidence_score") or best_ofc.get("confidence") or 0,
            "linked_at": datetime.utcnow().isoformat(),
            "source_discipline": v.get("discipline", "Physical Security"),
            "category": v.get("category", "Physical"),
            "proximity_distance": best_distance
        }
        links.append(link)
    
    log_info(f"[Phase3] Created {len(links)} vulnerability–OFC pair(s).")
    return links

# ----------------------------------------------------------------
# Database Persistence
# ----------------------------------------------------------------

def persist_vulnerability_ofc_links(pairs: List[Dict[str, Any]], model_version: str = "vofc-engine:latest", source_submission: Optional[str] = None):
    """Save vulnerability–OFC pairs into Supabase."""
    if not pairs:
        log_info("[Phase3] No vulnerability–OFC pairs to persist.")
        return
    
    try:
        from services.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        payload = [
            {
                "vulnerability_text": p.get("vulnerability_text", ""),
                "ofc_text": p.get("ofc_text", ""),
                "vulnerability_conf": p.get("vulnerability_conf"),
                "ofc_conf": p.get("ofc_conf"),
                "category": p.get("category"),
                "discipline": p.get("source_discipline"),
                "model_version": model_version,
                "source_submission": source_submission
            }
            for p in pairs
        ]
        
        # Filter out any pairs with empty required fields
        payload = [p for p in payload if p.get("vulnerability_text") and p.get("ofc_text")]
        
        if payload:
            supabase.table("vulnerability_ofc_links").insert(payload).execute()
            log_info(f"[Phase3] Persisted {len(payload)} vulnerability–OFC link(s) to Supabase.")
        else:
            log_warn("[Phase3] No valid pairs to persist after filtering.")
    except Exception as e:
        log_error(f"[Phase3] Failed to persist vulnerability–OFC links: {e}")
        import traceback
        log_error(f"[Phase3] Traceback: {traceback.format_exc()}")

def audit_records(records: List[Dict[str, Any]], use_physical_security: bool = False) -> Dict[str, Any]:
    """
    Review Phase2 output.
    - Accepts Physical Security records ≥0.8 confidence.
    - Reflags 0.6–0.8 for manual review.
    - Rejects below 0.6 unless matching high-risk phrases.
    
    Args:
        records: List of records from Phase 2
        use_physical_security: Whether physical security heuristics are enabled
        
    Returns:
        Dictionary with accepted, needs_review, rejected lists and summary
    """
    accepted = []
    needs_review = []
    rejected = []
    
    for rec in records:
        # Get confidence score (handle different field names)
        conf = rec.get("confidence_score") or rec.get("confidence") or 0.0
        if isinstance(conf, str):
            try:
                conf = float(conf)
            except:
                conf = 0.0
        
        discipline = rec.get("discipline", "")
        category = rec.get("category", "")
        text = rec.get("vulnerability", "") or rec.get("text", "") or ""
        text_lower = text.lower()
        
        # Apply physical security rules if enabled
        if use_physical_security and discipline == "Physical Security":
            if conf >= MIN_ACCEPT_CONFIDENCE:
                rec["audit_status"] = "accepted"
                accepted.append(rec)
            elif REVIEW_RANGE[0] <= conf < REVIEW_RANGE[1]:
                rec["audit_status"] = "needs_review"
                rec["review_reason"] = "confidence_in_moderate_range"
                needs_review.append(rec)
            else:
                # Quick rescue: keep some high-value cues
                if any(phrase in text_lower for phrase in HIGH_RISK_PHRASES):
                    rec["audit_status"] = "accepted"
                    rec["audit_confidence_adjusted"] = min(conf + 0.1, 1.0)
                    rec["audit_notes"] = "Accepted due to high-risk phrase match"
                    accepted.append(rec)
                else:
                    rec["audit_status"] = "rejected"
                    rec["rejection_reason"] = f"confidence_too_low ({conf:.2f} < {MIN_ACCEPT_CONFIDENCE})"
                    rejected.append(rec)
        else:
            # Standard audit rules for non-physical security
            if conf >= MIN_ACCEPT_CONFIDENCE:
                rec["audit_status"] = "accepted"
                accepted.append(rec)
            elif REVIEW_RANGE[0] <= conf < REVIEW_RANGE[1]:
                rec["audit_status"] = "needs_review"
                rec["review_reason"] = "confidence_in_moderate_range"
                needs_review.append(rec)
            else:
                rec["audit_status"] = "rejected"
                rec["rejection_reason"] = f"confidence_too_low ({conf:.2f} < {MIN_ACCEPT_CONFIDENCE})"
                rejected.append(rec)
    
    total = len(records)
    accepted_pct = round((len(accepted) / total) * 100, 1) if total else 0
    
    # Pair vulnerabilities and OFCs from accepted records
    pairs = []
    try:
        pairs = pair_vulns_and_ofcs(accepted)
    except Exception as pair_err:
        log_error(f"[Phase3] Failed to pair vulnerabilities and OFCs: {pair_err}")
        pairs = []
    
    log_info(f"[Phase3] Audited {total} records: {len(accepted)} accepted ({accepted_pct}%), "
             f"{len(needs_review)} under review, {len(rejected)} rejected.")
    
    # Calculate mean confidence for accepted records
    mean_confidence = 0.0
    if accepted:
        confidences = [r.get("confidence_score") or r.get("confidence") or 0.0 for r in accepted]
        confidences = [float(c) if isinstance(c, (int, float)) else 0.0 for c in confidences]
        mean_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
    
    audit_summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_records": total,
        "accepted": len(accepted),
        "review": len(needs_review),
        "rejected": len(rejected),
        "accepted_pct": accepted_pct,
        "pairs_created": len(pairs),
        "mean_confidence": mean_confidence,
        "physical_security_mode": use_physical_security
    }
    
    # Write audit log
    try:
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(audit_summary) + "\n")
        log_info(f"[Phase3] Audit summary written to {AUDIT_LOG}")
    except Exception as e:
        log_error(f"[Phase3] Failed to write audit log: {e}")
    
    log_info(f"[Phase3] Audit Summary: {audit_summary}")
    
    return {
        "accepted": accepted,
        "needs_review": needs_review,
        "rejected": rejected,
        "pairs": pairs,
        "summary": audit_summary
    }


def run_phase3_auditor(phase2_results: List[Dict[str, Any]], use_physical_security: bool = False, model_version: str = "vofc-engine:latest", source_submission: Optional[str] = None) -> Dict[str, Any]:
    """
    Entry point for Phase 3 Auditor with auto-pairing.
    
    Args:
        phase2_results: List of records from Phase 2
        use_physical_security: Whether physical security heuristics are enabled
        model_version: Version of the model used for processing
        source_submission: Optional submission ID to link pairs to
        
    Returns:
        Dictionary with accepted, needs_review, rejected, pairs, and summary
    """
    log_info("[Phase3] Running Auditor with Vulnerability–OFC Pairing Extension")
    
    try:
        results = audit_records(phase2_results, use_physical_security)
        
        # Persist vulnerability–OFC pairs to database
        pairs = results.get("pairs", [])
        if pairs:
            persist_vulnerability_ofc_links(pairs, model_version, source_submission)
        
        return results
    except Exception as e:
        log_error(f"[Phase3] Auditor crash: {e}")
        import traceback
        log_error(f"[Phase3] Traceback: {traceback.format_exc()}")
        return {
            "accepted": [],
            "needs_review": [],
            "rejected": [],
            "pairs": [],
            "summary": {}
        }

