"""
Taxonomy Inference Module
Infers sector and subsector from document context and validates against Supabase tables.
Prevents disciplines from being incorrectly used as sectors.
"""
import logging
from typing import Dict, Any, Optional, Tuple
from services.supabase_client import get_discipline_record, get_sector_id, get_subsector_id

logger = logging.getLogger(__name__)

def _validate_subsector_belongs_to_sector(subsector_id, sector_id):
    """
    Validate that a subsector actually belongs to a specific sector.
    This ensures we only return valid sector/subsector combinations.
    
    Args:
        subsector_id: UUID of the subsector
        sector_id: UUID of the sector
        
    Returns:
        True if subsector belongs to sector, False otherwise
    """
    if not subsector_id or not sector_id:
        return False
    
    try:
        from services.supabase_client import get_supabase_client
        client = get_supabase_client()
        result = client.table("subsectors").select("sector_id").eq("id", subsector_id).maybe_single().execute()
        
        if result.data:
            actual_sector_id = result.data.get("sector_id")
            return actual_sector_id == sector_id
        
        return False
    except Exception as e:
        logger.debug(f"Error validating subsector-sector relationship: {e}")
        return False

# Common discipline names that should NOT be used as sectors
COMMON_DISCIPLINES = [
    "Physical Security", "Cybersecurity", "Operational Technology",
    "Information Security", "Personnel Security", "Emergency Management",
    "Risk Management", "Training and Awareness", "Facility Information"
]

# Sector inference keywords from document titles and content
SECTOR_KEYWORDS = {
    "Education": {
        # Note: Public schools are typically under "Government Facilities" - this is for private/independent educational institutions
        "keywords": ["education", "student", "campus", "university", "college", "academic", "classroom", "teacher", "faculty", "private school", "private education", "independent school"],
        "subsectors": ["Higher Education", "Education Facilities", "Private Education"]
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
        "keywords": ["government", "federal", "state", "local", "agency", "municipal", "courthouse", "school", "schools", "public school", "public schools", "k-12", "k12"],
        "subsectors": ["Federal Facilities", "State Facilities", "Local Facilities", "Schools", "K-12 Schools", "Public Schools"]
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
    Uses context-aware matching to avoid false positives from single-word matches.
    
    Args:
        document_title: Document title (e.g., "Safe-Schools-Best-Practices")
        vulnerability_text: Vulnerability description text
        existing_sector: Existing sector value (will be validated)
        existing_subsector: Existing subsector value (will be validated)
        
    Returns:
        Tuple of (sector_name, subsector_name) or (None, None) if cannot infer
    """
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
    
    # For document-level inference, use title only
    # For record-level inference, use vulnerability text with context-aware matching
    text_to_analyze = document_title.lower() if not vulnerability_text else vulnerability_text.lower()
    combined_text = f"{document_title} {vulnerability_text}".lower()
    
    # Context-aware vulnerability patterns that map to sectors
    # These are more specific than simple keyword matching
    vulnerability_patterns = {
        "Government Facilities": {
            # School-related patterns (public schools are Government Facilities)
            "patterns": [
                r"\bschool\b", r"\bschools\b", r"\bpublic school\b", r"\bk-12\b", r"\bk12\b",
                r"\bteacher\b", r"\bteachers\b", r"\bstudent\b", r"\bstudents\b", r"\bclassroom\b",
                r"\bfirst responder\b", r"\bfirst responders\b", r"\bemergency response\b",
                r"\bblueprint\b", r"\bblueprints\b", r"\bsharing.*first responder\b",
                r"\btrain\b.*teacher\b", r"\btraining.*teacher\b", r"\black.*train\b.*teacher\b",
                r"\bviolence.*awareness\b", r"\bbullying.*awareness\b", r"\bdrug awareness\b",
                r"\bgang.*awareness\b"
            ],
            "subsectors": ["Schools", "K-12 Schools", "Public Schools"]
        },
        "Guard Force Operations": {
            # Security personnel and guard force patterns
            "patterns": [
                r"\bsecurity personnel\b", r"\bsecurity guard\b", r"\bguards\b", r"\bguard force\b",
                r"\bsecurity staff\b", r"\bsecurity officer\b", r"\bsecurity officers\b",
                r"\bnon-commissioned\b", r"\binstruction day\b"
            ],
            "subsectors": ["Security Personnel", "Guard Operations"]
        },
        # Note: "Training" is not a DHS sector - training-related vulnerabilities should be classified
        # under the appropriate sector (e.g., "Government Facilities" for school training)
        "Emergency Response": {
            # Emergency coordination and response patterns
            "patterns": [
                r"\bsharing.*first responder\b", r"\bfirst responder.*blueprint\b",
                r"\bcoordinate.*emergency\b", r"\bemergency.*coordination\b",
                r"\bemergency response\b", r"\bemergency planning\b"
            ],
            "subsectors": ["Emergency Coordination", "Response Planning"]
        },
        "Surveillance": {
            # Surveillance-specific patterns (not just "camera" in any context)
            "patterns": [
                r"\bsurveillance\b", r"\bsecurity camera\b", r"\bcamera.*location\b",
                r"\bmonitoring system\b", r"\bvideo surveillance\b", r"\bcctv\b"
            ],
            "subsectors": ["Video Surveillance", "Monitoring Systems"]
        },
        "Perimeter and Access Control": {
            # Access control and perimeter security patterns
            # These patterns should match even when "school" is in the context
            "patterns": [
                r"\baccess control\b", r"\bperimeter\b", r"\bentry control\b",
                r"\baccess point\b", r"\baccess points\b", r"\bgate\b.*control\b",
                r"\bmonitoring.*perimeter\b", r"\bperimeter.*monitoring\b",
                r"\bmonitoring.*access control\b", r"\baccess control.*monitoring\b",
                r"\bperimeter.*access\b", r"\baccess.*perimeter\b"
            ],
            "subsectors": ["Access Control", "Perimeter Security"]
        }
    }
    
    # First, try context-aware vulnerability pattern matching (more accurate)
    if vulnerability_text:
        import re
        best_match = None
        best_score = 0
        
        for sector_name, sector_info in vulnerability_patterns.items():
            patterns = sector_info.get("patterns", [])
            score = 0
            for pattern in patterns:
                if re.search(pattern, vulnerability_text.lower()):
                    score += 2  # Pattern matches are worth more than simple keywords
            
            if score > best_score:
                best_score = score
                best_match = sector_name
        
        if best_match and best_score > 0:
            # Validate that the inferred sector exists in Supabase
            sector_id = get_sector_id(best_match, fuzzy=True)
            if sector_id:
                # Try to find a matching subsector that ACTUALLY belongs to this sector
                subsectors = vulnerability_patterns[best_match].get("subsectors", [])
                inferred_subsector = None
                
                for subsector in subsectors:
                    subsector_id = get_subsector_id(subsector, fuzzy=True)
                    if subsector_id:
                        # CRITICAL: Validate that this subsector actually belongs to the inferred sector
                        if _validate_subsector_belongs_to_sector(subsector_id, sector_id):
                            inferred_subsector = subsector
                            break
                        else:
                            logger.warning(f"Subsector '{subsector}' does not belong to sector '{best_match}' - skipping")
                
                logger.info(f"Inferred sector '{best_match}' from vulnerability pattern matching (score: {best_score})")
                return best_match, inferred_subsector
    
    # Fallback to document title keyword matching (for document-level inference)
    if document_title:
        best_match = None
        best_score = 0
        
        for sector_name, sector_info in SECTOR_KEYWORDS.items():
            keywords = sector_info["keywords"]
            # Use word boundary matching for better accuracy
            # Normalize text by replacing hyphens/underscores with spaces for matching
            normalized_text = combined_text.replace("-", " ").replace("_", " ")
            score = sum(1 for keyword in keywords if f" {keyword} " in f" {normalized_text} " or normalized_text.startswith(keyword + " ") or normalized_text.endswith(" " + keyword) or normalized_text == keyword)
            
            if score > best_score:
                best_score = score
                best_match = sector_name
        
        if best_match and best_score > 0:
            # Validate that the inferred sector exists in Supabase
            sector_id = get_sector_id(best_match, fuzzy=True)
            if not sector_id:
                logger.warning(f"Inferred sector '{best_match}' not found in Supabase - cannot use")
                return None, None
            
            # Try to find a matching subsector
            subsectors = SECTOR_KEYWORDS[best_match]["subsectors"]
            inferred_subsector = None
            
            # Check if any subsector keywords match
            for subsector in subsectors:
                subsector_lower = subsector.lower()
                if any(f" {kw} " in f" {combined_text} " for kw in subsector_lower.split()):
                    # Validate subsector exists in Supabase AND belongs to the sector
                    subsector_id = get_subsector_id(subsector, fuzzy=True)
                    if subsector_id:
                        # CRITICAL: Validate that this subsector actually belongs to the inferred sector
                        if _validate_subsector_belongs_to_sector(subsector_id, sector_id):
                            inferred_subsector = subsector
                            break
                        else:
                            logger.warning(f"Subsector '{subsector}' does not belong to sector '{best_match}' - skipping")
            
            # If no specific subsector matched, try first one from list (but validate it exists AND belongs to sector)
            if not inferred_subsector and subsectors:
                for subsector in subsectors:
                    subsector_id = get_subsector_id(subsector, fuzzy=True)
                    if subsector_id:
                        # CRITICAL: Validate that this subsector actually belongs to the inferred sector
                        if _validate_subsector_belongs_to_sector(subsector_id, sector_id):
                            inferred_subsector = subsector
                            break
                        else:
                            logger.warning(f"Subsector '{subsector}' does not belong to sector '{best_match}' - skipping")
            
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
    
    # PRIORITY 1: Check vulnerability-specific patterns FIRST (more specific than document title)
    # Vulnerability-specific security terms (perimeter, access control, surveillance, etc.) 
    # should take precedence over generic document title keywords
    inferred_sector = None
    inferred_subsector = None
    
    # Security-specific vulnerability patterns that should override document-level inference
    security_keywords = ["perimeter", "access control", "surveillance", "security personnel", 
                        "guard force", "emergency response", "monitoring", "entry control"]
    
    has_security_context = vulnerability and any(kw in vulnerability.lower() for kw in security_keywords)
    
    if has_security_context:
        # Try vulnerability-specific inference first (more accurate for security-related vulnerabilities)
        inferred_sector, inferred_subsector = infer_sector_subsector(
            document_title="",  # Don't use document title for security-specific vulnerabilities
            vulnerability_text=vulnerability,
            existing_sector="",
            existing_subsector=""
        )
        if inferred_sector:
            logger.info(f"Vulnerability-specific inference (security context): sector='{inferred_sector}', subsector='{inferred_subsector}' - OVERRIDING document-level inference")
    
    # PRIORITY 2: If no vulnerability-specific match, use document-level inference
    # This ensures ALL records from the same document get consistent sector/subsector
    # Document-level inference only applies if vulnerability doesn't have security-specific context
    if not inferred_sector and document_title:
        inferred_sector, inferred_subsector = infer_sector_subsector(
            document_title=document_title,
            vulnerability_text="",  # Don't use vulnerability text for document-level inference
            existing_sector="",
            existing_subsector=""
        )
        if inferred_sector:
            logger.info(f"Document-level inference from title '{document_title[:50]}...': sector='{inferred_sector}', subsector='{inferred_subsector}' - APPLYING TO ALL RECORDS")
    
    # Check if sector is actually a discipline name (before applying document-level inference)
    if sector and is_discipline_name(sector):
        logger.warning(f"Invalid sector '{sector}' is actually a discipline - moving to discipline field")
        # Move to discipline if discipline is empty
        if not discipline:
            corrected["discipline"] = sector
        # Clear invalid sector
        corrected["sector"] = ""
        sector = ""
    
    # Check if subsector is actually a discipline name (before applying document-level inference)
    if subsector and is_discipline_name(subsector):
        logger.warning(f"Invalid subsector '{subsector}' is actually a discipline - moving to discipline field")
        # Move to discipline if discipline is empty
        if not discipline:
            corrected["discipline"] = subsector
        # Clear invalid subsector
        corrected["subsector"] = ""
        subsector = ""
    
    # PRIORITY 2: Apply inferred sector/subsector
    # If we inferred from vulnerability-specific patterns (security context), use that
    # Otherwise, if we inferred from document title, use that for consistency
    if inferred_sector:
        # Apply inferred sector/subsector on this record
        corrected["sector"] = inferred_sector
        if inferred_subsector:
            corrected["subsector"] = inferred_subsector
        else:
            # If no subsector inferred, clear any existing subsector to avoid mismatches
            corrected["subsector"] = ""
        logger.debug(f"Applied inferred taxonomy: sector='{inferred_sector}', subsector='{inferred_subsector or '(none)'}'")
    # If no document-level inference succeeded, validate and correct record-level values
    elif sector:
        # Check if the provided sector actually exists in Supabase
        sector_id = get_sector_id(sector, fuzzy=True)
        if not sector_id:
            # Sector doesn't exist - check if it's actually a subsector
            subsector_id = get_subsector_id(sector, fuzzy=True)
            if subsector_id:
                # It's a subsector, not a sector - find its parent sector
                logger.warning(f"'{sector}' is a subsector, not a sector - finding parent sector")
                try:
                    from services.supabase_client import get_supabase_client
                    client = get_supabase_client()
                    result = client.table("subsectors").select("sector_id, sectors!inner(name)").eq("id", subsector_id).maybe_single().execute()
                    if result.data and result.data.get("sector_id"):
                        parent_sector_id = result.data.get("sector_id")
                        # Get parent sector name
                        sector_result = client.table("sectors").select("name").eq("id", parent_sector_id).maybe_single().execute()
                        if sector_result.data:
                            parent_sector_name = sector_result.data.get("name")
                            logger.info(f"Mapped '{sector}' to sector '{parent_sector_name}' with subsector '{sector}'")
                            corrected["sector"] = parent_sector_name
                            corrected["subsector"] = sector  # Keep the original value as subsector
                            sector = parent_sector_name  # Update for later validation
                        else:
                            # Can't find parent, clear sector
                            logger.warning(f"Could not find parent sector for subsector '{sector}' - clearing")
                            corrected["sector"] = ""
                            sector = ""
                    else:
                        # Can't find parent, clear sector
                        logger.warning(f"Could not find parent sector for subsector '{sector}' - clearing")
                        corrected["sector"] = ""
                        sector = ""
                except Exception as e:
                    logger.debug(f"Error finding parent sector for '{sector}': {e}")
                    corrected["sector"] = ""
                    sector = ""
            else:
                # Not a sector or subsector - reject it
                logger.warning(f"'{sector}' is not a valid sector or subsector in Supabase - rejecting")
                corrected["sector"] = ""
                sector = ""
        else:
            # Sector exists and is valid - keep it
            pass
    
    # If no document-level inference and sector is invalid/missing, try record-level inference
    # OR if sector exists but doesn't match vulnerability content, re-infer
    current_sector = corrected.get("sector", "")
    sector_id = get_sector_id(current_sector, fuzzy=True) if current_sector else None
    
    # Validate that existing sector makes sense for this vulnerability
    # If vulnerability text is available, check if sector matches content
    should_reinfer = False
    if vulnerability and current_sector and sector_id:
        # Re-infer from vulnerability to see if it matches
        inferred_sector, _ = infer_sector_subsector(
            document_title="",
            vulnerability_text=vulnerability,
            existing_sector="",
            existing_subsector=""
        )
        
        # If inferred sector differs from current, and inference is confident, use inferred
        if inferred_sector and inferred_sector != current_sector:
            # Check if inferred sector is more appropriate
            inferred_id = get_sector_id(inferred_sector, fuzzy=True)
            if inferred_id:
                logger.warning(f"Sector mismatch: vulnerability suggests '{inferred_sector}' but record has '{current_sector}' - using inferred sector")
                should_reinfer = True
                corrected["sector"] = ""  # Clear to trigger re-inference
    
    if not corrected.get("sector") or not get_sector_id(corrected.get("sector", ""), fuzzy=True) or should_reinfer:
        inferred_sector, inferred_subsector = infer_sector_subsector(
            document_title=document_title,
            vulnerability_text=vulnerability,
            existing_sector=corrected.get("sector", ""),
            existing_subsector=corrected.get("subsector", "")
        )
        
        if inferred_sector:
            logger.info(f"Inferred sector '{inferred_sector}' from context (title: {document_title[:50]}...)")
            corrected["sector"] = inferred_sector
            
            # If subsector is missing, use inferred one
            if not corrected.get("subsector") and inferred_subsector:
                corrected["subsector"] = inferred_subsector
        else:
            # If inference failed, use "General" as fallback (valid DHS sector for non-sector-specific documents)
            general_sector_id = get_sector_id("General", fuzzy=True)
            if general_sector_id:
                logger.info(f"Could not infer specific sector for document '{document_title[:50]}...' - using 'General' sector")
                corrected["sector"] = "General"
                corrected["subsector"] = ""  # Clear subsector when using General
            else:
                logger.warning(f"Could not infer sector and 'General' sector not found in Supabase - sector_id will be NULL")
    
    # If no document-level inference and sector exists but subsector is missing, try to infer subsector
    if corrected.get("sector") and not corrected.get("subsector"):
        _, inferred_subsector = infer_sector_subsector(
            document_title=document_title,
            vulnerability_text=vulnerability,
            existing_sector=corrected.get("sector", ""),
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
    
    # Validate sector exists in Supabase and get sector_id
    sector_id = None
    if corrected.get("sector"):
        sector_id = get_sector_id(corrected["sector"], fuzzy=True)
        if not sector_id:
            logger.warning(f"Sector '{corrected['sector']}' not found in Supabase - clearing")
            corrected["sector"] = ""
        else:
            # Store sector_id for database insertion
            corrected["sector_id"] = sector_id
            
            # If sector is "General", clear any subsector (General doesn't have subsectors)
            if corrected["sector"].strip().lower() == "general":
                if corrected.get("subsector"):
                    logger.debug(f"Clearing subsector '{corrected['subsector']}' because sector is 'General'")
                    corrected["subsector"] = ""
    
    # Validate subsector exists in Supabase and get subsector_id
    # Only validate if sector is not "General" (General doesn't have subsectors)
    subsector_id = None
    if corrected.get("subsector") and corrected.get("sector", "").strip().lower() != "general":
        subsector_id = get_subsector_id(corrected["subsector"], fuzzy=True)
        if not subsector_id:
            logger.warning(f"Subsector '{corrected['subsector']}' not found in Supabase - clearing")
            corrected["subsector"] = ""
        else:
            # Store subsector_id for database insertion
            corrected["subsector_id"] = subsector_id
            # CRITICAL: Validate that subsector belongs to the sector
            # This is REQUIRED - invalid combinations should be rejected
            if sector_id:
                if not _validate_subsector_belongs_to_sector(subsector_id, sector_id):
                    logger.warning(f"Subsector '{corrected['subsector']}' does not belong to sector '{corrected['sector']}' - clearing subsector")
                    corrected["subsector"] = ""
                    corrected["subsector_id"] = None
    
    return corrected

