"""
Canonical Taxonomy Resolver (Production-Ready)
Resolves sector, subsector, and discipline using database relationships.
Deterministic, no guessing, no fallbacks.
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
        Normalized text (lowercase, stripped, noise words removed)
    """
    if not text:
        return ""
    
    t = text.lower().strip()
    
    # Remove noise words
    t = re.sub(r'\b(sector|subsector|discipline|infrastructure|systems?)\b', '', t)
    
    # Remove special characters, keep only alphanumeric and spaces
    t = re.sub(r'[^a-z0-9 ]+', '', t)
    
    # Normalize whitespace
    t = re.sub(r'\s+', ' ', t)
    
    return t.strip()


def resolve_from_discipline(name: str) -> Optional[Dict[str, Any]]:
    """
    Resolve taxonomy from discipline name.
    NOTE: Disciplines are not directly linked to subsectors/sectors in the current schema.
    This function only returns the discipline information.
    For full taxonomy resolution, use subsector or sector names.
    
    Args:
        name: Discipline name to resolve
        
    Returns:
        Dict with discipline info (sector/subsector will be None since no direct relationship exists)
    """
    cleaned = normalize(name)
    if not cleaned:
        return None
    
    pattern = f"*{cleaned}*"
    
    try:
        client = get_supabase_client()
        
        # Find discipline (no direct relationship to subsectors/sectors in current schema)
        result = client.table("disciplines") \
            .select("id, name, category, code") \
            .ilike("name", pattern) \
            .maybe_single() \
            .execute()
        
        if not result.data:
            logger.debug(f"Discipline '{name}' not found in database")
            return None
        
        row = result.data
        
        # NOTE: Disciplines don't have direct subsector/sector relationships in current schema
        # Return discipline only - caller should use subsector/sector names for full resolution
        return {
            "sector": None,
            "subsector": None,
            "discipline": {
                "id": row.get("id"),
                "name": row.get("name"),
                "category": row.get("category"),
                "code": row.get("code")
            }
        }
    except Exception as e:
        logger.error(f"Error resolving from discipline '{name}': {e}", exc_info=True)
        return None


def resolve_from_subsector(name: str) -> Optional[Dict[str, Any]]:
    """
    Resolve taxonomy from subsector name.
    Subsector → Sector (via database relationships)
    
    Args:
        name: Subsector name to resolve
        
    Returns:
        Dict with sector and subsector info, or None if not found
    """
    cleaned = normalize(name)
    if not cleaned:
        return None
    
    pattern = f"*{cleaned}*"
    
    try:
        client = get_supabase_client()
        
        # Find subsector with its parent sector
        # Note: subsectors table uses "name" column, not "subsector_name"
        result = client.table("subsectors") \
            .select("id, name, sector_id, sectors ( id, sector_name )") \
            .ilike("name", pattern) \
            .maybe_single() \
            .execute()
        
        if not result.data:
            logger.debug(f"Subsector '{name}' not found in database")
            return None
        
        row = result.data
        
        # Extract nested sector data
        sector_data = row.get("sectors")
        
        return {
            "sector": sector_data,
            "subsector": {
                "id": row.get("id"),
                "name": row.get("name")  # Use "name" column, not "subsector_name"
            },
            "discipline": None
        }
    except Exception as e:
        logger.error(f"Error resolving from subsector '{name}': {e}", exc_info=True)
        return None


def resolve_sector(name: str) -> Optional[Dict[str, Any]]:
    """
    Resolve sector only (weakest resolution, used as last resort).
    
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


def resolve_taxonomy(
    sector_name: Optional[str] = None,
    subsector_name: Optional[str] = None,
    discipline_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Unified taxonomy resolver.
    Always resolves bottom-up:
    1. Discipline → subsector → sector (most specific)
    2. Subsector → sector (medium specificity)
    3. Sector only (weakest, last resort)
    
    Args:
        sector_name: Optional sector name
        subsector_name: Optional subsector name
        discipline_name: Optional discipline name
        
    Returns:
        Dict with resolved sector, subsector, and discipline (or None for each)
    """
    # 1. Discipline resolves everything cleanly (highest priority)
    if discipline_name:
        resolved = resolve_from_discipline(discipline_name)
        if resolved:
            logger.info(f"Resolved taxonomy from discipline '{discipline_name}': discipline={resolved.get('discipline', {}).get('name') if resolved.get('discipline') else None}")
            return resolved
    
    # 2. Subsector resolves sector (medium priority)
    if subsector_name:
        resolved = resolve_from_subsector(subsector_name)
        if resolved:
            logger.info(f"Resolved taxonomy from subsector '{subsector_name}': sector={resolved.get('sector', {}).get('sector_name') if resolved.get('sector') else None}")
            return resolved
    
    # 3. Sector as last resort (lowest priority)
    if sector_name:
        sector_data = resolve_sector(sector_name)
        if sector_data:
            logger.info(f"Resolved sector only '{sector_name}'")
            return {
                "sector": sector_data,
                "subsector": None,
                "discipline": None
            }
    
    # 4. Nothing found
    logger.debug(f"No taxonomy resolved from sector='{sector_name}', subsector='{subsector_name}', discipline='{discipline_name}'")
    return {
        "sector": None,
        "subsector": None,
        "discipline": None
    }

