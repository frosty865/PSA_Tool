"""
Phase 2 Engine — Physical Security Extraction Upgrade v1.0

Purpose: Integrate physical_security_patterns.json for heuristic-driven extraction.

Author: VOFC Engine Ops

Date: 2025-11-08
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Setup logging
logger = logging.getLogger(__name__)

PATTERN_FILE = Path(__file__).parent.parent / "heuristics" / "patterns" / "physical_security_patterns.json"

def log_info(message: str):
    """Log info message."""
    logger.info(message)

def log_warn(message: str):
    """Log warning message."""
    logger.warning(message)

def log_error(message: str):
    """Log error message."""
    logger.error(message)

def load_patterns() -> Dict[str, Any]:
    """Load heuristic pattern definitions from JSON file."""
    try:
        if not PATTERN_FILE.exists():
            log_warn(f"[Phase2] Pattern file not found at {PATTERN_FILE}")
            return {}
        
        with open(PATTERN_FILE, "r", encoding="utf-8") as f:
            text = f.read()
            # auto-handle YAML front matter by stripping comments
            pattern_json = [line for line in text.splitlines() if not line.strip().startswith("#")]
            data = json.loads("\n".join(pattern_json))
            log_info(f"[Phase2] Loaded physical security patterns from {PATTERN_FILE}")
            return data
    except Exception as e:
        log_error(f"[Phase2] Failed to load physical_security_patterns.json: {e}")
        return {}

# Load patterns at module level
patterns_cfg = load_patterns()

def evaluate_confidence(text: str, pattern_dict: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Compute weighted confidence score and matched categories."""
    if not patterns_cfg:
        return 0.0, []
    
    confidence_tuning = patterns_cfg.get("confidence_tuning", {})
    total_weight = confidence_tuning.get("base_weight", 0.4)
    match_weight = confidence_tuning.get("match_weight_per_pattern", 0.05)
    matched_tags = []
    
    # Get patterns from pattern_dict (should be patterns_cfg.get("patterns", {}))
    if not isinstance(pattern_dict, dict):
        return total_weight, []
    
    for section, patterns in pattern_dict.items():
        if section == "mitigation_cues":
            continue  # Skip OFC patterns for vulnerability scoring
        
        if not isinstance(patterns, list):
            continue
        
        for pat in patterns:
            try:
                if re.search(pat, text, re.IGNORECASE):
                    total_weight += match_weight
                    matched_tags.append(section)
                    break  # Only count once per section
            except re.error as e:
                log_warn(f"[Phase2] Invalid regex pattern '{pat}': {e}")
                continue
    
    return min(round(total_weight, 3), 1.0), matched_tags

def detect_physical_security_vulns(text: str, source_file: str = "") -> Dict[str, Any]:
    """Detect vulnerabilities and OFCs within text chunk using loaded patterns."""
    if not patterns_cfg:
        return None
    
    pattern_groups = patterns_cfg.get("patterns", {})
    confidence, tags = evaluate_confidence(text, pattern_groups)
    
    confidence_tuning = patterns_cfg.get("confidence_tuning", {})
    min_accept = confidence_tuning.get("min_confidence_for_accept", 0.8)
    
    # Apply discipline bias
    discipline = "Physical Security"
    if confidence >= 0.6:  # Lower threshold for discipline assignment
        discipline = patterns_cfg.get("discipline_bias", {}).get("default", "Physical Security")
    else:
        discipline = "Unknown"
    
    if discipline == "Physical Security":
        category = patterns_cfg.get("output_mapping", {}).get("category", "Physical")
    else:
        category = "Unclassified"
    
    # Extract OFCs using mitigation cues
    ofcs = []
    mitigation_patterns = pattern_groups.get("mitigation_cues", [])
    text_lower = text.lower()
    
    for pattern in mitigation_patterns:
        if isinstance(pattern, str):
            try:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    # Extract sentence containing the mitigation verb
                    sentences = re.split(r'[.!?]+', text)
                    for sentence in sentences:
                        if re.search(pattern, sentence, re.IGNORECASE):
                            ofc_text = sentence.strip()
                            if ofc_text and len(ofc_text) > 10:
                                ofcs.append(ofc_text[:300])  # Limit length
                                break
            except re.error:
                continue
    
    result = {
        "vulnerability": text.strip()[:600],  # Limit vulnerability text
        "confidence_score": confidence,
        "discipline": discipline,
        "category": category,
        "matched_tags": tags,
        "source_file": source_file,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if ofcs:
        result["options_for_consideration"] = ofcs[:3]  # Limit to 3 OFCs
    
    return result if confidence >= min_accept else None

def process_chunks(chunks: List[Dict[str, Any]], source_file: str = "") -> List[Dict[str, Any]]:
    """Main loop to process document chunks."""
    if not patterns_cfg:
        log_warn("[Phase2] Patterns not loaded, skipping pattern-based extraction")
        return []
    
    results = []
    for chunk in chunks:
        # Extract text from chunk (handle different formats)
        text = chunk.get("text") or chunk.get("content") or chunk.get("vulnerability") or ""
        if not text or len(text.strip()) < 20:
            continue
        
        result = detect_physical_security_vulns(text, source_file)
        if result and result.get("confidence_score", 0) >= 0.8:
            # Add chunk metadata if available
            if "chunk_id" in chunk:
                result["chunk_id"] = chunk["chunk_id"]
            if "page_ref" in chunk:
                result["page_range"] = chunk["page_ref"]
            if "section" in chunk:
                result["citations"] = [chunk["section"]]
            
            results.append(result)
    
    log_info(f"[Phase2] Extracted {len(results)} potential physical-security findings via pattern matching.")
    return results

# Integration Hook for VOFC Engine
def run_phase2_engine(document_chunks: List[Dict[str, Any]], filepath: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Entry point for VOFC Engine Phase 2 pattern-based extraction.
    
    Called automatically by processing pipeline after Phase 1 parser.
    Can be used as alternative or supplement to Ollama-based extraction.
    
    Args:
        document_chunks: List of document chunks from Phase 1
        filepath: Optional path to source document
        
    Returns:
        List of extracted vulnerability records with confidence scores
    """
    log_info("[Phase2] Running Physical Security-Enhanced Pattern Extraction")
    
    source_file = filepath.name if filepath else ""
    
    try:
        return process_chunks(document_chunks, source_file)
    except Exception as e:
        log_error(f"[Phase2] Engine crash: {e}")
        import traceback
        log_error(f"[Phase2] Traceback: {traceback.format_exc()}")
        return []

