"""
Deduplication Logic
Removes duplicate vulnerabilities and merges OFCs.
"""
import hashlib
import logging
from typing import List, Dict, Any


def dedupe_key(vuln: str) -> str:
    """
    Generate a hash key for deduplication.
    
    Args:
        vuln: Vulnerability text
        
    Returns:
        SHA1 hash of normalized vulnerability text
    """
    return hashlib.sha1(vuln.strip().lower().encode()).hexdigest()


def dedupe_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate records by vulnerability text, merging OFCs.
    
    Args:
        records: List of record dictionaries
        
    Returns:
        Deduplicated list of records with merged OFCs
    """
    out = {}
    duplicates = 0
    
    for r in records:
        vuln_text = r.get("vulnerability", "").strip()
        if not vuln_text:
            continue
            
        key = dedupe_key(vuln_text)
        
        if key not in out:
            out[key] = r.copy()
        else:
            # Merge OFCs from duplicate
            duplicates += 1
            existing_options = out[key].get("options", [])
            new_options = r.get("options", [])
            
            # Combine and dedupe options
            if isinstance(existing_options, list) and isinstance(new_options, list):
                merged_options = list(set(existing_options + new_options))
            elif isinstance(new_options, list):
                merged_options = new_options
            else:
                merged_options = existing_options
            
            out[key]["options"] = merged_options
            
            # Update other fields if new record has more complete data
            for field in ["discipline", "sector", "subsector"]:
                if not out[key].get(field) and r.get(field):
                    out[key][field] = r[field]
    
    result = list(out.values())
    if duplicates > 0:
        logging.info(f"Deduplicated {duplicates} duplicate records, {len(result)} unique remaining")
    
    return result

