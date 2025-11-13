"""
Classification Logic
Normalizes and validates extracted data fields.
"""
import logging
from typing import Dict, Any, List


def normalize_confidence(value: Any) -> str:
    """
    Normalize confidence values to allowed schema values.
    
    Args:
        value: Confidence value from model
        
    Returns:
        Normalized confidence: 'High', 'Medium', or 'Low'
    """
    if not value:
        return "Medium"
    
    value_str = str(value).strip().title()
    
    # Map common variations
    if value_str in ["High", "H", "High Confidence"]:
        return "High"
    elif value_str in ["Medium", "M", "Medium Confidence", "Moderate"]:
        return "Medium"
    elif value_str in ["Low", "L", "Low Confidence"]:
        return "Low"
    else:
        logging.warning(f"Unknown confidence value: {value}, defaulting to Medium")
        return "Medium"


def normalize_impact_level(value: Any) -> str:
    """
    Normalize impact_level values to allowed schema values.
    
    Args:
        value: Impact level from model
        
    Returns:
        Normalized impact_level: 'High', 'Moderate', or 'Low'
    """
    if not value:
        return "Moderate"
    
    value_str = str(value).strip().title()
    
    # Map common variations
    if value_str in ["High", "H", "Critical", "Severe"]:
        return "High"
    elif value_str in ["Moderate", "M", "Medium", "Moderate Impact"]:
        return "Moderate"
    elif value_str in ["Low", "L", "Minor"]:
        return "Low"
    else:
        logging.warning(f"Unknown impact_level value: {value}, defaulting to Moderate")
        return "Moderate"


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single record to match Supabase schema.
    
    Args:
        record: Raw record from model
        
    Returns:
        Normalized record with validated fields
    """
    normalized = record.copy()
    
    # Normalize confidence if present
    if "confidence" in normalized:
        normalized["confidence"] = normalize_confidence(normalized["confidence"])
    
    # Normalize impact_level if present
    if "impact_level" in normalized:
        normalized["impact_level"] = normalize_impact_level(normalized["impact_level"])
    
    # Ensure required fields exist
    if "vulnerability" not in normalized:
        normalized["vulnerability"] = ""
    if "options" not in normalized:
        normalized["options"] = []
    if not isinstance(normalized["options"], list):
        normalized["options"] = []
    
    return normalized


def normalize_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize all records in a list.
    
    Args:
        records: List of raw records
        
    Returns:
        List of normalized records
    """
    return [normalize_record(r) for r in records]

