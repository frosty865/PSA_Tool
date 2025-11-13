"""
Merge Logic
Combines results from multiple chunks into a single list.
"""
import logging
from typing import List, Dict, Any


def merge_all(chunk_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge all records from chunk results into a single list.
    
    Args:
        chunk_results: List of result dictionaries, each with 'records' key
        
    Returns:
        Flat list of all records from all chunks
    """
    merged = []
    for result in chunk_results:
        records = result.get("records", [])
        if isinstance(records, list):
            merged.extend(records)
        else:
            logging.warning(f"Unexpected record format: {type(records)}")
    
    logging.info(f"Merged {len(merged)} records from {len(chunk_results)} chunks")
    return merged

