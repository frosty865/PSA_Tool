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
    
    log_info(f"[Phase3] Audited {total} records: {len(accepted)} accepted ({accepted_pct}%), "
             f"{len(needs_review)} under review, {len(rejected)} rejected.")
    
    audit_summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_records": total,
        "accepted": len(accepted),
        "needs_review": len(needs_review),
        "rejected": len(rejected),
        "accepted_pct": accepted_pct,
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
    
    return {
        "accepted": accepted,
        "needs_review": needs_review,
        "rejected": rejected,
        "summary": audit_summary
    }


def run_phase3_auditor(phase2_results: List[Dict[str, Any]], use_physical_security: bool = False) -> List[Dict[str, Any]]:
    """
    Entry point for VOFC Engine Phase 3 Auditor.
    
    Args:
        phase2_results: List of records from Phase 2
        use_physical_security: Whether physical security heuristics are enabled
        
    Returns:
        List of accepted records
    """
    log_info("[Phase3] Running Physical Security Confidence Gate Auditor")
    
    try:
        results = audit_records(phase2_results, use_physical_security)
        return results.get("accepted", [])
    except Exception as e:
        log_error(f"[Phase3] Auditor crash: {e}")
        import traceback
        log_error(f"[Phase3] Traceback: {traceback.format_exc()}")
        return []

