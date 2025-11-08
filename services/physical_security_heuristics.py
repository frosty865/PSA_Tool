"""
Physical Security Heuristics
Loads and applies physical security pattern matching to boost extraction confidence.
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Path to physical security patterns
PATTERNS_PATH = Path(__file__).parent.parent / "heuristics" / "patterns" / "physical_security_patterns.json"

_patterns_cache: Optional[Dict[str, Any]] = None


def load_physical_security_patterns() -> Optional[Dict[str, Any]]:
    """Load physical security patterns from JSON file."""
    global _patterns_cache
    
    if _patterns_cache is not None:
        return _patterns_cache
    
    if not PATTERNS_PATH.exists():
        logger.warning(f"Physical security patterns not found at {PATTERNS_PATH}")
        return None
    
    try:
        with open(PATTERNS_PATH, 'r', encoding='utf-8') as f:
            _patterns_cache = json.load(f)
        logger.info(f"Loaded physical security patterns from {PATTERNS_PATH}")
        return _patterns_cache
    except Exception as e:
        logger.error(f"Failed to load physical security patterns: {e}")
        return None


def should_apply_physical_security_heuristics(filepath: Path, document_title: str = "") -> bool:
    """
    Check if physical security heuristics should be applied based on document triggers.
    
    Args:
        filepath: Path to the document
        document_title: Optional document title
        
    Returns:
        True if heuristics should be applied
    """
    patterns = load_physical_security_patterns()
    if not patterns:
        return False
    
    triggers = patterns.get("document_triggers", [])
    if not triggers:
        return False
    
    # Check filename and title
    file_lower = filepath.name.lower() if filepath else ""
    title_lower = document_title.lower() if document_title else ""
    combined_text = f"{file_lower} {title_lower}".lower()
    
    for trigger in triggers:
        if trigger.lower() in combined_text:
            logger.info(f"Physical security heuristics triggered by: '{trigger}' in document")
            return True
    
    return False


def calculate_physical_security_confidence(text: str, patterns: Dict[str, Any]) -> float:
    """
    Calculate confidence score based on physical security pattern matches.
    
    Args:
        text: Text to analyze
        text_lower: Lowercase version of text
        patterns: Loaded patterns dictionary
        
    Returns:
        Confidence score (0.0 to 1.0)
    """
    if not patterns:
        return 0.0
    
    confidence_tuning = patterns.get("confidence_tuning", {})
    base_weight = confidence_tuning.get("base_weight", 0.4)
    match_weight = confidence_tuning.get("match_weight_per_pattern", 0.05)
    
    pattern_groups = patterns.get("patterns", {})
    text_lower = text.lower()
    
    total_matches = 0
    matched_groups = set()
    
    # Check each pattern group
    for group_name, pattern_list in pattern_groups.items():
        if group_name == "mitigation_cues":
            continue  # Skip OFC patterns for vulnerability scoring
        
        for pattern_str in pattern_list:
            try:
                # Compile regex pattern
                pattern = re.compile(pattern_str, re.IGNORECASE)
                if pattern.search(text_lower):
                    total_matches += 1
                    matched_groups.add(group_name)
                    break  # Only count once per group
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern_str}': {e}")
                continue
    
    # Calculate confidence: base + (matches * weight)
    confidence = base_weight + (total_matches * match_weight)
    
    # Cap at 1.0
    confidence = min(confidence, 1.0)
    
    if total_matches > 0:
        logger.debug(f"Physical security pattern match: {total_matches} groups matched, confidence: {confidence:.2f}")
    
    return confidence


def get_physical_security_prompt_enhancement(patterns: Dict[str, Any]) -> str:
    """
    Generate prompt enhancement text for physical security documents.
    
    Args:
        patterns: Loaded patterns dictionary
        
    Returns:
        Additional prompt instructions
    """
    if not patterns:
        return ""
    
    instructions = patterns.get("instructions", {})
    discipline_bias = patterns.get("discipline_bias", {})
    confidence_tuning = patterns.get("confidence_tuning", {})
    
    enhancement = """
PHYSICAL SECURITY DOCUMENT DETECTED - Apply specialized extraction rules:

1. DISCIPLINE BIAS: Default to "Physical Security" category unless clearly cyber-only.
2. KEYWORD WEIGHTING: Overweight facility, personnel, and physical risk terms. Underweight pure cyber unless mixed with physical.
3. CONFIDENCE TUNING: 
   - Base confidence: {base_weight}
   - Pattern matches boost confidence by {match_weight} each
   - Minimum confidence for acceptance: {min_confidence}
4. FORCE ACCEPT: If discipline is "Physical Security" and confidence >= 0.8, accept automatically.
5. OFC EXTRACTION: Look for mitigation verbs: install, implement, establish, develop, conduct, coordinate, train, upgrade, replace, enhance.

KEY PHYSICAL SECURITY PATTERNS TO RECOGNIZE:
- Facility security (access control, visitor management, security plans)
- Perimeter protection (fences, barriers, gates, standoff)
- Lighting and visibility (illumination, dark areas, blind spots)
- Surveillance and monitoring (cameras, CCTV, video systems)
- Intrusion detection (alarms, sensors, duress systems)
- Security force management (guards, training, SOPs)
- Emergency preparedness (evacuation, drills, coordination)
- Resilience and facility design (blast resistance, standoff distance, protective glazing)

OUTPUT REQUIREMENTS:
- Category: "Physical" (unless clearly cyber-only)
- Discipline: "Physical Security" (default, override only if clearly wrong)
- Confidence: Boost scores for physical security patterns
- Sector priority: Government Facilities, Healthcare, Education, Commercial Facilities, Water/Wastewater
""".format(
        base_weight=confidence_tuning.get("base_weight", 0.4),
        match_weight=confidence_tuning.get("match_weight_per_pattern", 0.05),
        min_confidence=confidence_tuning.get("min_confidence_for_accept", 0.8)
    )
    
    return enhancement.strip()


def apply_physical_security_heuristics(
    records: List[Dict[str, Any]], 
    filepath: Path,
    document_title: str = ""
) -> List[Dict[str, Any]]:
    """
    Apply physical security heuristics to boost confidence scores.
    
    Args:
        records: List of extracted records
        filepath: Path to source document
        document_title: Optional document title
        
    Returns:
        Records with updated confidence scores
    """
    if not should_apply_physical_security_heuristics(filepath, document_title):
        return records
    
    patterns = load_physical_security_patterns()
    if not patterns:
        return records
    
    logger.info(f"Applying physical security heuristics to {len(records)} records")
    
    confidence_tuning = patterns.get("confidence_tuning", {})
    min_confidence = confidence_tuning.get("min_confidence_for_accept", 0.8)
    force_accept = confidence_tuning.get("force_accept_if_discipline_bias", True)
    
    updated_records = []
    for record in records:
        updated_record = record.copy()
        
        # Calculate physical security confidence boost
        vuln_text = record.get("vulnerability", "") or record.get("text", "") or ""
        if vuln_text:
            pattern_confidence = calculate_physical_security_confidence(vuln_text, patterns)
            
            # Boost existing confidence or set new
            existing_confidence = record.get("confidence_score", 0.0) or 0.0
            if isinstance(existing_confidence, str):
                try:
                    existing_confidence = float(existing_confidence)
                except:
                    existing_confidence = 0.0
            
            # Use the higher of existing or pattern-based confidence
            new_confidence = max(existing_confidence, pattern_confidence)
            
            # If pattern confidence is high enough, force accept
            if pattern_confidence >= min_confidence and force_accept:
                new_confidence = max(new_confidence, min_confidence)
                updated_record["category"] = "Physical"
                updated_record["discipline"] = "Physical Security"
                logger.debug(f"Force-accepted record with pattern confidence {pattern_confidence:.2f}")
            
            updated_record["confidence_score"] = new_confidence
            
            # Apply discipline bias if pattern matches
            if pattern_confidence >= 0.6:
                discipline_bias = patterns.get("discipline_bias", {})
                if discipline_bias.get("default") == "Physical Security":
                    if not updated_record.get("discipline") or updated_record.get("discipline") != "Physical Security":
                        updated_record["discipline"] = "Physical Security"
                        updated_record["category"] = "Physical"
                        logger.debug(f"Applied discipline bias: Physical Security")
        
        updated_records.append(updated_record)
    
    logger.info(f"Physical security heuristics applied: {len(updated_records)} records processed")
    return updated_records

