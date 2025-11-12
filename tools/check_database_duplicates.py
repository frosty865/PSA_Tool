"""
Check for duplicate vulnerabilities and OFCs against production database.
Used to filter out records that already exist before insertion.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    from difflib import SequenceMatcher


def normalize_text_for_comparison(text: str) -> str:
    """Normalize text for duplicate comparison."""
    if not text:
        return ""
    import re
    # Lowercase and strip
    text = str(text).strip().lower()
    # Remove articles
    text = re.sub(r'\b(a|an|the)\s+', '', text)
    # Remove punctuation
    text = re.sub(r'[^\w\s]', ' ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts (0.0-1.0)."""
    if not text1 or not text2:
        return 0.0
    
    norm1 = normalize_text_for_comparison(text1)
    norm2 = normalize_text_for_comparison(text2)
    
    if not norm1 or not norm2:
        return 0.0
    
    if RAPIDFUZZ_AVAILABLE:
        # Use token_sort_ratio for better matching (handles word order differences)
        score = fuzz.token_sort_ratio(norm1, norm2) / 100.0
    else:
        # Fallback to SequenceMatcher
        from difflib import SequenceMatcher
        score = SequenceMatcher(None, norm1, norm2).ratio()
    
    return score


def check_vulnerability_duplicate(
    vuln_text: str,
    existing_vulns: List[Dict[str, Any]],
    threshold: float = 0.85
) -> Optional[Dict[str, Any]]:
    """
    Check if a vulnerability already exists in the database.
    
    Args:
        vuln_text: Vulnerability text to check
        existing_vulns: List of existing vulnerabilities from database
        threshold: Similarity threshold (default 0.85 = 85%)
        
    Returns:
        Existing vulnerability dict if duplicate found, None otherwise
    """
    if not vuln_text or not existing_vulns:
        return None
    
    for existing in existing_vulns:
        # Check both vulnerability_name and description fields
        existing_text = existing.get("vulnerability_name") or existing.get("vulnerability") or ""
        existing_desc = existing.get("description") or ""
        
        # Combine for comparison
        existing_combined = f"{existing_text} {existing_desc}".strip()
        
        if not existing_combined:
            continue
        
        similarity = calculate_similarity(vuln_text, existing_combined)
        
        if similarity >= threshold:
            logger.debug(f"Found duplicate vulnerability: '{vuln_text[:50]}...' matches '{existing_text[:50]}...' (similarity: {similarity:.2f})")
            return existing
    
    return None


def check_ofc_duplicate(
    ofc_text: str,
    existing_ofcs: List[Dict[str, Any]],
    threshold: float = 0.85
) -> Optional[Dict[str, Any]]:
    """
    Check if an OFC already exists in the database.
    
    Args:
        ofc_text: OFC text to check
        existing_ofcs: List of existing OFCs from database
        threshold: Similarity threshold (default 0.85 = 85%)
        
    Returns:
        Existing OFC dict if duplicate found, None otherwise
    """
    if not ofc_text or not existing_ofcs:
        return None
    
    for existing in existing_ofcs:
        existing_text = existing.get("option_text") or existing.get("title") or ""
        
        if not existing_text:
            continue
        
        similarity = calculate_similarity(ofc_text, existing_text)
        
        if similarity >= threshold:
            logger.debug(f"Found duplicate OFC: '{ofc_text[:50]}...' matches '{existing_text[:50]}...' (similarity: {similarity:.2f})")
            return existing
    
    return None


def fetch_existing_vulnerabilities(supabase_client=None) -> List[Dict[str, Any]]:
    """Fetch all existing vulnerabilities from production and submission tables."""
    if not supabase_client:
        supabase_client = get_supabase_client()
    
    if not supabase_client:
        logger.warning("Could not get Supabase client for duplicate checking")
        return []
    
    existing_vulns = []
    
    try:
        # Fetch from production vulnerabilities table
        prod_response = supabase_client.table("vulnerabilities").select("id, vulnerability_name, description").execute()
        if prod_response.data:
            existing_vulns.extend(prod_response.data)
            logger.debug(f"Fetched {len(prod_response.data)} production vulnerabilities")
    except Exception as e:
        logger.warning(f"Could not fetch production vulnerabilities: {e}")
    
    try:
        # Also fetch from submission_vulnerabilities (recent submissions)
        sub_response = supabase_client.table("submission_vulnerabilities").select("id, vulnerability, title, description").limit(1000).order("created_at", desc=True).execute()
        if sub_response.data:
            # Convert submission format to match production format
            for sub_vuln in sub_response.data:
                existing_vulns.append({
                    "id": sub_vuln.get("id"),
                    "vulnerability_name": sub_vuln.get("vulnerability") or sub_vuln.get("title"),
                    "description": sub_vuln.get("description", "")
                })
            logger.debug(f"Fetched {len(sub_response.data)} submission vulnerabilities")
    except Exception as e:
        logger.warning(f"Could not fetch submission vulnerabilities: {e}")
    
    return existing_vulns


def fetch_existing_ofcs(supabase_client=None) -> List[Dict[str, Any]]:
    """Fetch all existing OFCs from production and submission tables."""
    if not supabase_client:
        supabase_client = get_supabase_client()
    
    if not supabase_client:
        logger.warning("Could not get Supabase client for duplicate checking")
        return []
    
    existing_ofcs = []
    
    try:
        # Fetch from production options_for_consideration table
        prod_response = supabase_client.table("options_for_consideration").select("id, option_text, title").execute()
        if prod_response.data:
            existing_ofcs.extend(prod_response.data)
            logger.debug(f"Fetched {len(prod_response.data)} production OFCs")
    except Exception as e:
        logger.warning(f"Could not fetch production OFCs: {e}")
    
    try:
        # Also fetch from submission_options_for_consideration (recent submissions)
        sub_response = supabase_client.table("submission_options_for_consideration").select("id, option_text, title").limit(1000).order("created_at", desc=True).execute()
        if sub_response.data:
            existing_ofcs.extend(sub_response.data)
            logger.debug(f"Fetched {len(sub_response.data)} submission OFCs")
    except Exception as e:
        logger.warning(f"Could not fetch submission OFCs: {e}")
    
    return existing_ofcs


def filter_duplicate_records(
    records: List[Dict[str, Any]],
    supabase_client=None,
    vuln_threshold: float = 0.85,
    ofc_threshold: float = 0.85
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Filter out records that are duplicates of existing database records.
    
    Args:
        records: List of vulnerability/OFC records to check
        supabase_client: Supabase client (optional, will fetch if not provided)
        vuln_threshold: Similarity threshold for vulnerabilities (default 0.85)
        ofc_threshold: Similarity threshold for OFCs (default 0.85)
        
    Returns:
        (filtered_records, duplicate_count)
    """
    if not records:
        return [], 0
    
    # Fetch existing records from database
    logger.info("Fetching existing vulnerabilities and OFCs from database for duplicate checking...")
    existing_vulns = fetch_existing_vulnerabilities(supabase_client)
    existing_ofcs = fetch_existing_ofcs(supabase_client)
    
    logger.info(f"Checking {len(records)} records against {len(existing_vulns)} existing vulnerabilities and {len(existing_ofcs)} existing OFCs")
    
    filtered_records = []
    duplicate_count = 0
    
    for record in records:
        vuln_text = record.get("vulnerability") or record.get("vulnerability_name") or ""
        
        # Check if vulnerability is a duplicate
        if vuln_text:
            duplicate_vuln = check_vulnerability_duplicate(vuln_text, existing_vulns, vuln_threshold)
            if duplicate_vuln:
                logger.info(f"⏭️  Skipping duplicate vulnerability: '{vuln_text[:60]}...'")
                duplicate_count += 1
                continue
        
        # Check OFCs for duplicates
        ofcs = record.get("options_for_consideration", [])
        if not ofcs and record.get("ofc"):
            ofcs = [record.get("ofc")]
        
        if ofcs:
            # Check if all OFCs are duplicates
            all_ofcs_duplicate = True
            for ofc in ofcs:
                ofc_text = ofc if isinstance(ofc, str) else ofc.get("option_text") or ofc.get("ofc") or ""
                if ofc_text:
                    duplicate_ofc = check_ofc_duplicate(ofc_text, existing_ofcs, ofc_threshold)
                    if not duplicate_ofc:
                        all_ofcs_duplicate = False
                        break
            
            if all_ofcs_duplicate and ofcs:
                logger.info(f"⏭️  Skipping record with duplicate OFCs: '{vuln_text[:60] if vuln_text else 'N/A'}...'")
                duplicate_count += 1
                continue
        
        # Record is not a duplicate, keep it
        filtered_records.append(record)
    
    if duplicate_count > 0:
        logger.info(f"✅ Filtered out {duplicate_count} duplicate records, {len(filtered_records)} unique records remaining")
    
    return filtered_records, duplicate_count

