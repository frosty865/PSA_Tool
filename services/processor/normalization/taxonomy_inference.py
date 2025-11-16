"""
Taxonomy Inference Module (DEPRECATED - Use DocumentClassifier/SubsectorResolverV2)

⚠️ DEPRECATED: This module is deprecated. Use DocumentClassifier and SubsectorResolverV2 instead.

Infers sector and subsector from document context and validates against Supabase tables.
Prevents disciplines from being incorrectly used as sectors.
"""
import logging
import warnings
from typing import Dict, Any, Optional, Tuple
from services.supabase_client import get_discipline_record, get_sector_id, get_subsector_id, get_sector_from_subsector

logger = logging.getLogger(__name__)

# Deprecation warning
warnings.warn(
    "taxonomy_inference module is deprecated. Use DocumentClassifier and SubsectorResolverV2 instead.",
    DeprecationWarning,
    stacklevel=2
)

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
        # Higher education and private/independent educational institutions
        "keywords": ["university", "college", "faculty", "private school", "private education", "independent school", "higher education"],
        "subsectors": ["Higher Education", "Private Education"]
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
        # Government facilities including schools (Education Facilities is a subsector)
        # School keywords should match Government Facilities sector, then infer Education Facilities subsector
        "keywords": ["government", "federal", "state", "local", "agency", "municipal", "courthouse", "federal facility", "state facility", "government building", "government agency", "school", "schools", "k-12", "k12", "safe school", "safe schools", "student", "students", "teacher", "teachers", "classroom", "campus", "education", "educational", "academic", "public school", "public schools", "elementary", "middle school", "high school"],
        "subsectors": ["Federal Facilities", "State Facilities", "Local Facilities", "Education Facilities", "Educational Facilities"]
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

# Subsector inference patterns - identify subsectors directly from content
SUBSECTOR_PATTERNS = {
    # Government Facilities subsectors
    "Education Facilities": {
        "keywords": ["school", "schools", "k-12", "k12", "safe school", "safe schools", "student", "students", "teacher", "teachers", "classroom", "classrooms", "elementary", "middle school", "high school", "public school", "public schools", "campus", "academic"],
        "patterns": [
            r"\bschool\b", r"\bschools\b", r"\bk-12\b", r"\bk12\b", r"\bsafe school\b", r"\bsafe schools\b",
            r"\bteacher\b", r"\bteachers\b", r"\bstudent\b", r"\bstudents\b", r"\bclassroom\b", r"\bclassrooms\b",
            r"\belementary\b", r"\bmiddle school\b", r"\bhigh school\b", r"\bpublic school\b", r"\bpublic schools\b",
            r"\bcampus\b", r"\bacademic\b"
        ]
    },
    "Educational Facilities": {
        "keywords": ["school", "schools", "education", "educational", "academic", "campus"],
        "patterns": [r"\beducation\b", r"\beducational\b", r"\bacademic\b", r"\bcampus\b"]
    },
    "Federal Facilities": {
        "keywords": ["federal", "federal facility", "federal building", "federal agency"],
        "patterns": [r"\bfederal facility\b", r"\bfederal building\b", r"\bfederal agency\b", r"\bfederal\b.*facility\b"]
    },
    "State Facilities": {
        "keywords": ["state", "state facility", "state building", "state agency"],
        "patterns": [r"\bstate facility\b", r"\bstate building\b", r"\bstate agency\b", r"\bstate\b.*facility\b"]
    },
    "Local Facilities": {
        "keywords": ["local", "local government", "municipal", "city", "county"],
        "patterns": [r"\blocal government\b", r"\bmunicipal\b", r"\bcity\b.*facility\b", r"\bcounty\b.*facility\b"]
    },
    # Add more subsector patterns as needed
}

def infer_subsector_from_document(
    document_title: str = "",
    document_content: str = ""
) -> Optional[str]:
    """
    Infer subsector directly from document content (backwards approach).
    Identifies the subsector first, then sector can be derived from it.
    
    Args:
        document_title: Document title
        document_content: Combined document content/text
    
    Returns:
        Subsector name or None if cannot infer
    """
    if not document_title and not document_content:
        return None
    
    combined_text = f"{document_title} {document_content}".lower()
    normalized_text = combined_text.replace("-", " ").replace("_", " ")
    
    best_subsector = None
    best_score = 0
    
    import re
    
    # Check all subsector patterns
    for subsector_name, subsector_info in SUBSECTOR_PATTERNS.items():
        score = 0
        
        # Check keyword matches
        keywords = subsector_info.get("keywords", [])
        for keyword in keywords:
            if f" {keyword} " in f" {normalized_text} " or normalized_text.startswith(keyword + " ") or normalized_text.endswith(" " + keyword) or normalized_text == keyword:
                score += 1
        
        # Check pattern matches (more specific, worth more)
        patterns = subsector_info.get("patterns", [])
        for pattern in patterns:
            if re.search(pattern, normalized_text):
                score += 2  # Patterns are worth more than keywords
        
        # Prioritize Education Facilities for school documents
        if subsector_name == "Education Facilities" and score > 0:
            score += 2  # Boost for school-related content
        
        if score > best_score:
            best_score = score
            best_subsector = subsector_name
    
    # Validate subsector exists in database
    if best_subsector and best_score > 0:
        subsector_id = get_subsector_id(best_subsector, fuzzy=True)
        if subsector_id:
            logger.info(f"Inferred subsector '{best_subsector}' from document content (score: {best_score})")
            return best_subsector
        else:
            logger.warning(f"Inferred subsector '{best_subsector}' not found in database")
            return None
    
    return None

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
    existing_subsector: str = "",
    use_backwards_approach: bool = True
) -> Tuple[Optional[str], Optional[str]]:
    """
    ⚠️ REMOVED: This function has been removed. Use DocumentClassifier for sector/subsector resolution.
    
    This function used deprecated get_sector_id/get_subsector_id with .ilike queries which cause 406 errors.
    All code must use DocumentClassifier/SubsectorResolverV2 for sector/subsector resolution.
    """
    raise NotImplementedError(
        "infer_sector_subsector has been removed. Use DocumentClassifier for sector/subsector resolution. "
        "See services.processor.normalization.document_classifier.DocumentClassifier"
    )

def validate_and_correct_taxonomy(
        subsector_id = get_subsector_id(existing_subsector, fuzzy=True)
        if subsector_id:
            sector_id, sector_name = get_sector_from_subsector(subsector_id)
            if sector_name:
                logger.info(f"Using existing subsector '{existing_subsector}' with derived sector '{sector_name}'")
                return sector_name, existing_subsector
    
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
    
    # BACKWARDS APPROACH: Identify subsector first from document content
    if use_backwards_approach and document_title:
        # Combine title and vulnerability text for subsector inference
        combined_content = f"{document_title} {vulnerability_text}".strip()
        
        # Check for school keywords FIRST (before general subsector inference)
        # This ensures school documents get Education Facilities even if other patterns match
        normalized_title = document_title.lower().replace("-", " ").replace("_", " ")
        school_keywords = ["school", "schools", "k-12", "k12", "safe school", "student", "teacher", "classroom", "elementary", "middle school", "high school", "public school"]
        has_school_keywords_in_title = any(kw in normalized_title for kw in school_keywords)
        
        if has_school_keywords_in_title:
            logger.info(f"School keywords detected in document title '{document_title}' - prioritizing Education Facilities subsector")
            # Try Education Facilities subsectors directly
            # NOTE: Database has "Educational Facilities" (with "al"), so try that first
            education_subsectors = ["Educational Facilities", "Education Facilities", "K-12 Schools"]
            for subsector_name in education_subsectors:
                subsector_id = get_subsector_id(subsector_name, fuzzy=True)
                if subsector_id:
                    sector_id, sector_name = get_sector_from_subsector(subsector_id)
                    if sector_name:
                        logger.info(f"Document-level inference (backwards, school priority): identified subsector '{subsector_name}', derived sector '{sector_name}' - APPLYING TO ALL RECORDS")
                        return sector_name, subsector_name
                    else:
                        logger.warning(f"Could not get parent sector for Education Facilities subsector '{subsector_name}'")
            logger.warning(f"School keywords detected but Education Facilities subsector not found in database")
        
        # If no school keywords or Education Facilities not found, use general subsector inference
        inferred_subsector = infer_subsector_from_document(document_title, combined_content)
        
        if inferred_subsector:
            # Get the parent sector from the subsector
            subsector_id = get_subsector_id(inferred_subsector, fuzzy=True)
            if subsector_id:
                sector_id, sector_name = get_sector_from_subsector(subsector_id)
                if sector_name:
                    logger.info(f"Document-level inference (backwards): identified subsector '{inferred_subsector}', derived sector '{sector_name}' - APPLYING TO ALL RECORDS")
                    return sector_name, inferred_subsector
                else:
                    logger.warning(f"Could not get parent sector for subsector '{inferred_subsector}'")
            else:
                logger.warning(f"Inferred subsector '{inferred_subsector}' not found in database")
    
    # For document-level inference, use title only
    # For record-level inference, use vulnerability text with context-aware matching
    text_to_analyze = document_title.lower() if not vulnerability_text else vulnerability_text.lower()
    combined_text = f"{document_title} {vulnerability_text}".lower()
    
    # Context-aware vulnerability patterns that map to sectors
    # These are more specific than simple keyword matching
    vulnerability_patterns = {
        "Government Facilities": {
            # Government facility patterns including schools (Education Facilities is a subsector)
            # School-related patterns should match Government Facilities, then infer Education Facilities subsector
            "patterns": [
                # School-specific patterns (will infer Education Facilities subsector)
                r"\bschool\b", r"\bschools\b", r"\bk-12\b", r"\bk12\b", r"\bsafe school\b", r"\bsafe schools\b",
                r"\bteacher\b", r"\bteachers\b", r"\bstudent\b", r"\bstudents\b", r"\bclassroom\b", r"\bclassrooms\b",
                r"\belementary\b", r"\bmiddle school\b", r"\bhigh school\b", r"\bpublic school\b", r"\bpublic schools\b",
                r"\btrain\b.*teacher\b", r"\btraining.*teacher\b", r"\black.*train\b.*teacher\b",
                r"\bviolence.*awareness\b", r"\bbullying.*awareness\b", r"\bdrug awareness\b",
                r"\bgang.*awareness\b", r"\bcampus\b.*emergency\b", r"\bschool.*emergency\b",
                # Government facility patterns (will infer Federal/State/Local Facilities subsectors)
                r"\bfederal facility\b", r"\bstate facility\b", r"\bgovernment building\b", r"\bgovernment agency\b",
                r"\bfederal.*building\b", r"\bstate.*building\b", r"\blocal.*government\b",
                r"\bcourthouse\b", r"\bmunicipal\b.*facility\b", r"\bagency.*facility\b"
            ],
            "subsectors": ["Federal Facilities", "State Facilities", "Local Facilities", "Education Facilities", "Educational Facilities"]
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
        
        # Check all sectors for pattern matches
        for sector_name, sector_info in vulnerability_patterns.items():
            patterns = sector_info.get("patterns", [])
            score = 0
            school_patterns_matched = 0
            
            for pattern in patterns:
                if re.search(pattern, vulnerability_text.lower()):
                    score += 2  # Pattern matches are worth more than simple keywords
                    # Track school-related patterns for subsector inference
                    if any(school_kw in pattern for school_kw in ["school", "teacher", "student", "classroom", "k-12", "k12"]):
                        school_patterns_matched += 1
            
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
                
                # If school-related patterns matched, prioritize Education Facilities subsector
                if best_match == "Government Facilities" and school_patterns_matched > 0:
                    logger.info(f"School patterns detected in vulnerability text - prioritizing Education Facilities subsector (matched {school_patterns_matched} patterns)")
                    # Try Education Facilities subsectors first
                    # NOTE: Database has "Educational Facilities" (with "al"), so try that first
                    education_subsectors = ["Educational Facilities", "Education Facilities", "K-12 Schools"]
                    for subsector in education_subsectors:
                        subsector_id = get_subsector_id(subsector, fuzzy=True)
                        if subsector_id:
                            if _validate_subsector_belongs_to_sector(subsector_id, sector_id):
                                inferred_subsector = subsector
                                logger.info(f"Successfully inferred Education Facilities subsector: {subsector}")
                                break
                        else:
                            logger.warning(f"Education Facilities subsector '{subsector}' not found in Supabase")
                
                # NO FALLBACK: If no education subsector found, leave it empty (don't try other subsectors)
                # Only use subsectors that are actually inferred from content
                if not inferred_subsector:
                    logger.info(f"No subsector inferred from vulnerability patterns for sector '{best_match}' - leaving empty")
                
                logger.info(f"Inferred sector '{best_match}' from vulnerability pattern matching (score: {best_score})")
                return best_match, inferred_subsector
    
    # Fallback to document title keyword matching (for document-level inference)
    if document_title:
        best_match = None
        best_score = 0
        has_school_keywords = False
        
        # Check all sectors for keyword matches
        for sector_name in SECTOR_KEYWORDS.keys():
            sector_info = SECTOR_KEYWORDS.get(sector_name)
            if not sector_info:
                continue
                
            keywords = sector_info["keywords"]
            # Use word boundary matching for better accuracy
            # Normalize text by replacing hyphens/underscores with spaces for matching
            normalized_text = combined_text.replace("-", " ").replace("_", " ")
            score = sum(1 for keyword in keywords if f" {keyword} " in f" {normalized_text} " or normalized_text.startswith(keyword + " ") or normalized_text.endswith(" " + keyword) or normalized_text == keyword)
            
            # Track if school keywords are present (for subsector inference)
            if any(kw in normalized_text for kw in ["school", "schools", "k-12", "k12", "student", "teacher"]):
                has_school_keywords = True
            
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
            
            # If Government Facilities and school keywords present, prioritize Education Facilities subsector
            if best_match == "Government Facilities" and has_school_keywords:
                logger.info(f"School keywords detected in document title - prioritizing Education Facilities subsector")
                education_subsectors = ["Education Facilities", "Educational Facilities", "K-12 Schools"]
                for subsector in education_subsectors:
                    subsector_id = get_subsector_id(subsector, fuzzy=True)
                    if subsector_id:
                        if _validate_subsector_belongs_to_sector(subsector_id, sector_id):
                            inferred_subsector = subsector
                            logger.info(f"Successfully inferred Education Facilities subsector: {subsector}")
                            break
                    else:
                        logger.warning(f"Education Facilities subsector '{subsector}' not found in Supabase")
            
            # If no education subsector found, check if any subsector keywords match
            if not inferred_subsector:
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
            
            # NO FALLBACK: If no specific subsector matched, leave it empty (don't use first available)
            # This ensures we only use subsectors that are actually inferred from content
            if not inferred_subsector:
                logger.info(f"No subsector inferred for sector '{best_match}' - leaving empty")
            
            return best_match, inferred_subsector
    
    return None, None

def validate_and_correct_taxonomy(
    record: Dict[str, Any],
    document_title: str = "",
    skip_sector_subsector: bool = False
) -> Dict[str, Any]:
    """
    ⚠️ REMOVED: This function has been removed. Use DocumentClassifier for sector/subsector resolution.
    
    This function used deprecated get_sector_id/get_subsector_id with .ilike queries which cause 406 errors.
    All code must use DocumentClassifier/SubsectorResolverV2 for sector/subsector resolution.
    """
    raise NotImplementedError(
        "validate_and_correct_taxonomy has been removed. Use DocumentClassifier for sector/subsector resolution. "
        "See services.processor.normalization.document_classifier.DocumentClassifier"
    )


