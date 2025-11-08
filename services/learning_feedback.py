"""
Learning Feedback System
Logs post-audit enrichment events for VOFC feedback loop
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

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

logger = logging.getLogger(__name__)


def log_post_audit_enrichment(
    model_id: str,
    source_file: str,
    detected_vulnerabilities: int,
    expected_vulnerabilities: int,
    expected_ofcs: int,
    correction_payload: Dict[str, Any],
    submission_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Log a post-audit enrichment learning event.
    
    This function records feedback when an analyst corrects or enriches
    model output, providing training data for future improvements.
    
    Args:
        model_id: Model version (e.g., "vofc-engine:latest")
        source_file: Source document filename
        detected_vulnerabilities: Number of vulnerabilities the model detected
        expected_vulnerabilities: Number of vulnerabilities that should have been detected
        expected_ofcs: Number of OFCs that should have been detected
        correction_payload: Dictionary containing:
            - themes: List of themes/topics that should be emphasized
            - examples: List of example vulnerability-OFC pairs
        submission_id: Optional submission ID to link the event
    
    Returns:
        Inserted event data or None on error
    
    Example:
        >>> log_post_audit_enrichment(
        ...     model_id="vofc-engine:latest",
        ...     source_file="USSS Averting Targeted School Violence.2021.03.pdf",
        ...     detected_vulnerabilities=1,
        ...     expected_vulnerabilities=10,
        ...     expected_ofcs=30,
        ...     correction_payload={
        ...         "themes": ["threat assessment", "leakage", "discipline follow-up"],
        ...         "examples": [
        ...             {
        ...                 "vulnerability": "No formal threat-assessment program",
        ...                 "ofcs": [
        ...                     "Establish and train multidisciplinary behavioral threat assessment teams",
        ...                     "Adopt and implement standard operating procedures following REMS/USSS guidelines"
        ...                 ]
        ...             }
        ...         ]
        ...     }
        ... )
    """
    try:
        # Build metadata with correction payload
        metadata = {
            "source_file": source_file,
            "detected_vulnerabilities": detected_vulnerabilities,
            "expected_vulnerabilities": expected_vulnerabilities,
            "expected_ofcs": expected_ofcs,
            "correction_payload": correction_payload,
            "detection_ratio": detected_vulnerabilities / expected_vulnerabilities if expected_vulnerabilities > 0 else 0.0,
            "ofc_ratio": expected_ofcs / expected_vulnerabilities if expected_vulnerabilities > 0 else 0.0
        }
        
        # Create learning event record
        event_data = {
            "submission_id": submission_id,
            "event_type": "post_audit_enrichment",
            "approved": True,  # Enrichment events are positive examples
            "model_version": model_id,
            "confidence_score": None,  # Not applicable for enrichment events
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Remove None values
        event_data = {k: v for k, v in event_data.items() if v is not None}
        
        # Insert into Supabase
        result = supabase.table("learning_events").insert(event_data).execute()
        
        if result.data:
            logger.info(f"✅ Logged post-audit enrichment event for {source_file}")
            logger.info(f"   Model: {model_id}, Detected: {detected_vulnerabilities}, Expected: {expected_vulnerabilities}")
            return result.data[0]
        else:
            logger.warning("Learning event insert returned no data")
            return None
            
    except Exception as e:
        logger.error(f"Failed to log post-audit enrichment event: {e}")
        logger.exception("Full traceback:")
        return None


def get_enrichment_themes(source_file: str, limit: int = 10) -> List[str]:
    """
    Retrieve enrichment themes from recent learning events for a source file.
    
    This can be used to inform model prompts based on past corrections.
    
    Args:
        source_file: Source document filename to search for
        limit: Maximum number of events to retrieve
    
    Returns:
        List of unique themes from correction payloads
    """
    try:
        # Query recent enrichment events for this source file
        result = supabase.table("learning_events") \
            .select("metadata") \
            .eq("event_type", "post_audit_enrichment") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        themes = set()
        for event in result.data or []:
            metadata = event.get("metadata", {})
            correction_payload = metadata.get("correction_payload", {})
            event_themes = correction_payload.get("themes", [])
            themes.update(event_themes)
        
        return sorted(list(themes))
        
    except Exception as e:
        logger.error(f"Failed to retrieve enrichment themes: {e}")
        return []


def get_enrichment_examples(source_file: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve enrichment examples from recent learning events for a source file.
    
    Args:
        source_file: Source document filename to search for
        limit: Maximum number of events to retrieve
    
    Returns:
        List of example dictionaries with vulnerability and OFCs
    """
    try:
        # Query recent enrichment events for this source file
        result = supabase.table("learning_events") \
            .select("metadata") \
            .eq("event_type", "post_audit_enrichment") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        examples = []
        for event in result.data or []:
            metadata = event.get("metadata", {})
            correction_payload = metadata.get("correction_payload", {})
            event_examples = correction_payload.get("examples", [])
            examples.extend(event_examples)
        
        return examples[:limit]
        
    except Exception as e:
        logger.error(f"Failed to retrieve enrichment examples: {e}")
        return []

