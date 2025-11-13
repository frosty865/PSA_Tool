"""
Taxonomy Inference Module
Infers sector and subsector from document context and validates against Supabase tables.
Prevents disciplines from being incorrectly used as sectors.
"""
import logging
from typing import Dict, Any, Optional, Tuple
from services.supabase_client import get_discipline_record, get_sector_id, get_subsector_id

logger = logging.getLogger(__name__)

# Common discipline names that should NOT be used as sectors
COMMON_DISCIPLINES = [
    "Physical Security", "Cybersecurity", "Operational Technology",
    "Information Security", "Personnel Security", "Emergency Management",
    "Risk Management", "Training and Awareness", "Facility Information"
]

# Sector inference keywords from document titles and content
SECTOR_KEYWORDS = {
    "Education": {
        "keywords": ["school", "education", "student", "campus", "university", "college", "k-12", "k12", "academic", "classroom", "teacher", "faculty"],
        "subsectors": ["K-12 Education", "Higher Education", "Education Facilities"]
    },
    "Energy": {
        "keywords": ["power", "energy", "electric", "grid", "utility", "generation", "transmission", "distribution"],
        "subsectors": ["Power Grid", "Electric Utilities", "Nuclear", "Renewable Energy"]
    },
    "Transportation": {
        "keywords": ["transport", "airport", "rail", "transit", "highway", "bridge", "tunnel", "port", "maritime"],
        "subsectors": ["Aviation", "Rail", "Highway", "Maritime", "Public Transit"]
    },
    "Information Technology": {
        "keywords": ["it", "information technology", "software", "system", "network", "data center", "cloud"],
        "subsectors": ["IT Services", "Cloud Computing", "Data Centers"]
    },
    "Healthcare": {
        "keywords": ["hospital", "healthcare", "medical", "clinic", "health", "patient", "pharmacy"],
        "subsectors": ["Hospitals", "Medical Facilities", "Public Health"]
    },
    "Government Facilities": {
        "keywords": ["government", "federal", "state", "local", "agency", "municipal", "courthouse"],
        "subsectors": ["Federal Facilities", "State Facilities", "Local Facilities"]
    },
    "Commercial Facilities": {
        "keywords": ["commercial", "retail", "shopping", "mall", "office", "business", "corporate"],
        "subsectors": ["Retail", "Office Buildings", "Entertainment"]
    },
    "Critical Manufacturing": {
        "keywords": ["manufacturing", "factory", "industrial", "production", "plant"],
        "subsectors": ["Manufacturing", "Industrial Facilities"]
    }
}

def is_discipline_name(value: str) -> bool:
    """
    Check if a value is actually a discipline name (not a sector).
    
    Args:
        value: Value to check
        
    Returns:
        True if value is a discipline name
    """
    if not value:
        return False
    
    value_lower = value.strip().lower()
    
    # Check against common discipline names
    for disc in COMMON_DISCIPLINES:
        if disc.lower() == value_lower:
            return True
    
    # Check against Supabase disciplines table
    try:
        discipline_record = get_discipline_record(value, fuzzy=True)
        if discipline_record:
            return True
    except Exception as e:
        logger.debug(f"Error checking discipline: {e}")
    
    return False

def infer_sector_subsector(
    document_title: str = "",
    vulnerability_text: str = "",
    existing_sector: str = "",
    existing_subsector: str = ""
) -> Tuple[Optional[str], Optional[str]]:
    """
    Infer sector and subsector from document context.
    
    Args:
        document_title: Document title (e.g., "Safe-Schools-Best-Practices")
        vulnerability_text: Vulnerability description text
        existing_sector: Existing sector value (will be validated)
        existing_subsector: Existing subsector value (will be validated)
        
    Returns:
        Tuple of (sector_name, subsector_name) or (None, None) if cannot infer
    """
    # Combine all text for keyword matching
    combined_text = f"{document_title} {vulnerability_text}".lower()
    
    # If existing sector is provided and valid, use it (but validate it's not a discipline)
    if existing_sector and not is_discipline_name(existing_sector):
        # Validate it exists in Supabase
        sector_id = get_sector_id(existing_sector, fuzzy=True)
        if sector_id:
            # If subsector is also provided and valid, use both
            if existing_subsector:
                subsector_id = get_subsector_id(existing_subsector, fuzzy=True)
                if subsector_id:
                    return existing_sector, existing_subsector
            return existing_sector, None
    
    # Infer from keywords
    best_match = None
    best_score = 0
    
    for sector_name, sector_info in SECTOR_KEYWORDS.items():
        keywords = sector_info["keywords"]
        score = sum(1 for keyword in keywords if keyword in combined_text)
        
        if score > best_score:
            best_score = score
            best_match = sector_name
    
    if best_match and best_score > 0:
        # Try to find a matching subsector
        subsectors = SECTOR_KEYWORDS[best_match]["subsectors"]
        inferred_subsector = None
        
        # Check if any subsector keywords match
        for subsector in subsectors:
            subsector_lower = subsector.lower()
            if any(keyword in combined_text for keyword in subsector_lower.split()):
                inferred_subsector = subsector
                break
        
        # If no specific subsector matched, use first one as default
        if not inferred_subsector and subsectors:
            inferred_subsector = subsectors[0]
        
        return best_match, inferred_subsector
    
    return None, None

def validate_and_correct_taxonomy(
    record: Dict[str, Any],
    document_title: str = ""
) -> Dict[str, Any]:
    """
    Validate and correct discipline, sector, and subsector assignments.
    Ensures values align with Supabase tables and prevents disciplines from being used as sectors.
    
    Args:
        record: Record with discipline, sector, subsector fields
        document_title: Document title for context inference
        
    Returns:
        Record with corrected taxonomy fields
    """
    corrected = record.copy()
    
    discipline = record.get("discipline", "").strip()
    sector = record.get("sector", "").strip()
    subsector = record.get("subsector", "").strip()
    vulnerability = record.get("vulnerability", "").strip()
    
    # Check if sector is actually a discipline name
    if sector and is_discipline_name(sector):
        logger.warning(f"Invalid sector '{sector}' is actually a discipline - moving to discipline field")
        # Move to discipline if discipline is empty
        if not discipline:
            corrected["discipline"] = sector
        # Clear invalid sector
        corrected["sector"] = ""
        sector = ""
    
    # Check if subsector is actually a discipline name
    if subsector and is_discipline_name(subsector):
        logger.warning(f"Invalid subsector '{subsector}' is actually a discipline - moving to discipline field")
        # Move to discipline if discipline is empty
        if not discipline:
            corrected["discipline"] = subsector
        # Clear invalid subsector
        corrected["subsector"] = ""
        subsector = ""
    
    # If sector is missing or invalid, try to infer from context
    if not sector or not get_sector_id(sector, fuzzy=True):
        inferred_sector, inferred_subsector = infer_sector_subsector(
            document_title=document_title,
            vulnerability_text=vulnerability,
            existing_sector=sector,
            existing_subsector=subsector
        )
        
        if inferred_sector:
            logger.info(f"Inferred sector '{inferred_sector}' from context (title: {document_title[:50]}...)")
            corrected["sector"] = inferred_sector
            
            # If subsector is missing, use inferred one
            if not subsector and inferred_subsector:
                corrected["subsector"] = inferred_subsector
    
    # If subsector is missing but sector exists, try to infer subsector
    elif not subsector:
        _, inferred_subsector = infer_sector_subsector(
            document_title=document_title,
            vulnerability_text=vulnerability,
            existing_sector=sector,
            existing_subsector=""
        )
        if inferred_subsector:
            corrected["subsector"] = inferred_subsector
    
    # Validate discipline exists in Supabase (optional - don't fail if not found)
    if discipline:
        try:
            disc_record = get_discipline_record(discipline, fuzzy=True)
            if not disc_record:
                logger.warning(f"Discipline '{discipline}' not found in Supabase - keeping as-is")
        except Exception as e:
            logger.debug(f"Error validating discipline: {e}")
    
    # Validate sector exists in Supabase
    if corrected.get("sector"):
        sector_id = get_sector_id(corrected["sector"], fuzzy=True)
        if not sector_id:
            logger.warning(f"Sector '{corrected['sector']}' not found in Supabase - clearing")
            corrected["sector"] = ""
    
    # Validate subsector exists in Supabase
    if corrected.get("subsector"):
        subsector_id = get_subsector_id(corrected["subsector"], fuzzy=True)
        if not subsector_id:
            logger.warning(f"Subsector '{corrected['subsector']}' not found in Supabase - clearing")
            corrected["subsector"] = ""
    
    return corrected

