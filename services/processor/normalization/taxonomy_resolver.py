"""
Canonical Taxonomy Resolver (Production-Ready)
Resolves sector, subsector, and discipline using database relationships.
Deterministic, no guessing, no fallbacks.

Architecture:
- DHS Taxonomy: Subsector → Sector (primary path)
- VOFC Taxonomy: Discipline (independent physical-security taxonomy)
"""
import re
import logging
from typing import Optional, Dict, Any
from services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def normalize(text: str) -> str:
    """
    Normalize input text for matching.
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text (lowercase, stripped, special chars removed)
    """
    if not text:
        return ""
    
    t = text.lower().strip()
    
    # Remove special characters, keep only alphanumeric and spaces
    t = re.sub(r'[^a-z0-9 ]+', '', t)
    
    # Normalize whitespace
    t = re.sub(r'\s+', ' ', t)
    
    return t.strip()


def resolve_subsector(name: str) -> Optional[Dict[str, Any]]:
    """
    Resolve subsector → sector (Primary DHS Path).
    Subsector is authoritative and resolves to its parent sector.
    
    Args:
        name: Subsector name to resolve
        
    Returns:
        Dict with subsector and sector info, or None if not found
    """
    cleaned = normalize(name)
    if not cleaned:
        return None
    
    pattern = f"*{cleaned}*"
    
    try:
        client = get_supabase_client()
        
        # Try with subsector_name first (if column exists), fallback to name
        result = None
        try:
            result = client.table("subsectors") \
                .select("id, subsector_name, sector_id, sectors(id, sector_name)") \
                .ilike("subsector_name", pattern) \
                .maybe_single() \
                .execute()
        except Exception:
            # Fallback to "name" column if subsector_name doesn't exist
            result = client.table("subsectors") \
                .select("id, name, sector_id, sectors(id, sector_name)") \
                .ilike("name", pattern) \
                .maybe_single() \
                .execute()
        
        if not result.data:
            logger.debug(f"Subsector '{name}' not found in database")
            return None
        
        row = result.data
        
        # Get subsector name from either column
        subsector_name = row.get("subsector_name") or row.get("name")
        
        return {
            "subsector": {
                "id": row.get("id"),
                "name": subsector_name
            },
            "sector": row.get("sectors")
        }
    except Exception as e:
        logger.error(f"Error resolving subsector '{name}': {e}", exc_info=True)
        return None


def resolve_sector(name: str) -> Optional[Dict[str, Any]]:
    """
    Resolve sector only (DHS fallback).
    
    Args:
        name: Sector name to resolve
        
    Returns:
        Dict with sector info, or None if not found
    """
    cleaned = normalize(name)
    if not cleaned:
        return None
    
    pattern = f"*{cleaned}*"
    
    try:
        client = get_supabase_client()
        
        result = client.table("sectors") \
            .select("id, sector_name") \
            .ilike("sector_name", pattern) \
            .maybe_single() \
            .execute()
        
        if not result.data:
            logger.debug(f"Sector '{name}' not found in database")
            return None
        
        return result.data
    except Exception as e:
        logger.error(f"Error resolving sector '{name}': {e}", exc_info=True)
        return None


def resolve_discipline(name: str) -> Optional[Dict[str, Any]]:
    """
    Resolve discipline (Independent VOFC Physical-Security Taxonomy).
    Disciplines are independent and don't resolve to subsectors/sectors.
    
    Args:
        name: Discipline name to resolve
        
    Returns:
        Dict with discipline info, or None if not found
    """
    cleaned = normalize(name)
    if not cleaned:
        return None
    
    pattern = f"*{cleaned}*"
    
    try:
        client = get_supabase_client()
        
        result = client.table("disciplines") \
            .select("id, name, category, is_active") \
            .ilike("name", pattern) \
            .maybe_single() \
            .execute()
        
        if not result.data:
            logger.debug(f"Discipline '{name}' not found in database")
            return None
        
        return result.data
    except Exception as e:
        logger.error(f"Error resolving discipline '{name}': {e}", exc_info=True)
        return None


def resolve_taxonomy(
    sector_name: Optional[str] = None,
    subsector_name: Optional[str] = None,
    discipline_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Final Unified Resolver (Correct Architecture).
    
    Priority:
    1. DHS Subsector first (strongest, authoritative) → resolves sector
    2. DHS Sector fallback → sector only
    3. Discipline (independent VOFC taxonomy) → always resolved if provided
    
    Args:
        sector_name: Optional sector name
        subsector_name: Optional subsector name
        discipline_name: Optional discipline name
        
    Returns:
        Dict with resolved sector, subsector, and discipline (or None for each)
    """
    # 1. DHS Subsector first (strongest, authoritative)
    if subsector_name:
        ss = resolve_subsector(subsector_name)
        if ss:
            return {
                "sector": ss.get("sector"),
                "subsector": ss.get("subsector"),
                "discipline": resolve_discipline(discipline_name) if discipline_name else None
            }
    
    # 2. DHS Sector fallback
    if sector_name:
        s = resolve_sector(sector_name)
        if s:
            return {
                "sector": s,
                "subsector": None,
                "discipline": resolve_discipline(discipline_name) if discipline_name else None
            }
    
    # 3. Discipline (independent)
    discipline = resolve_discipline(discipline_name) if discipline_name else None
    
    return {
        "sector": None,
        "subsector": None,
        "discipline": discipline
    }
