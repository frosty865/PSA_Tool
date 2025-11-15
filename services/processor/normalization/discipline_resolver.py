"""
Discipline Resolver Module
Normalizes raw discipline text to the 10 new CISA-aligned disciplines
and infers sub-disciplines using keyword heuristics.
"""
import logging
import re
from typing import Dict, Any, Optional, Tuple
from services.supabase_client import get_discipline_record, get_supabase_client

logger = logging.getLogger(__name__)

# The 10 new master disciplines
NEW_DISCIPLINES = [
    'Security Management & Governance',
    'Access Control Systems',
    'Video Surveillance Systems',
    'Intrusion Detection Systems',
    'Perimeter Security',
    'Interior Security & Physical Barriers',
    'Security Force / Operations',
    'Emergency Management & Resilience',
    'Information Sharing & Coordination',
    'Cyber-Physical Infrastructure Support'
]

# Legacy discipline to new discipline mapping
LEGACY_DISCIPLINE_MAP = {
    # Access Control mappings
    'Access Control': 'Access Control Systems',
    'Visitor Management': 'Access Control Systems',
    'Identity Management': 'Access Control Systems',
    
    # Video Surveillance mappings
    'VSS': 'Video Surveillance Systems',
    'Video Security Systems': 'Video Surveillance Systems',
    'Video Surveillance': 'Video Surveillance Systems',
    
    # Physical Security mappings
    'Physical Security': 'Interior Security & Physical Barriers',
    'Asset Protection': 'Interior Security & Physical Barriers',
    
    # Security Force mappings
    'Security Force': 'Security Force / Operations',
    'Security Operations': 'Security Force / Operations',
    
    # Emergency Management mappings
    'Emergency Response': 'Emergency Management & Resilience',
    'Business Continuity': 'Emergency Management & Resilience',
    
    # Cyber-Physical mappings
    'Data Protection': 'Cyber-Physical Infrastructure Support',
    'Network Security': 'Cyber-Physical Infrastructure Support',
    
    # Security Management mappings
    'Security Policy': 'Security Management & Governance',
    'Security Training': 'Security Management & Governance',
    'Security Awareness': 'Security Management & Governance',
    'Security Assessment': 'Security Management & Governance',
    'Security Management': 'Security Management & Governance',
    'Vulnerability Management': 'Security Management & Governance',
}

# Keywords for inferring sub-disciplines
SUBTYPE_KEYWORDS = {
    'Access Control Systems': {
        'PACS': ['pacs', 'physical access control', 'card reader', 'badge', 'access card'],
        'Visitor Management': ['visitor', 'guest', 'visitation', 'visitor log'],
        'Biometrics': ['biometric', 'fingerprint', 'iris', 'facial recognition', 'retina'],
        'Locking Hardware': ['lock', 'deadbolt', 'keypad lock', 'electronic lock', 'smart lock'],
        'Screening Ops': ['screening', 'x-ray', 'metal detector', 'bag check', 'security screening']
    },
    'Video Surveillance Systems': {
        'IP Cameras': ['ip camera', 'network camera', 'ip cam'],
        'Analog Cameras': ['analog camera', 'cctv', 'closed circuit'],
        'Hybrid Systems': ['hybrid', 'ip and analog'],
        'Storage & Retention': ['storage', 'retention', 'video storage', 'dvr', 'nvr'],
        'Monitoring / Video Wall': ['video wall', 'monitoring center', 'control room', 'watch center'],
        'Analytics': ['analytics', 'video analytics', 'ai', 'machine learning', 'facial recognition']
    },
    'Intrusion Detection Systems': {
        'Door Contacts': ['door contact', 'magnetic contact', 'door sensor'],
        'Glass Break': ['glass break', 'glass sensor', 'break glass'],
        'Motion': ['motion sensor', 'motion detector', 'pir', 'passive infrared'],
        'Perimeter IDS': ['perimeter', 'fence sensor', 'buried sensor', 'microwave'],
        'Alarm Monitoring': ['alarm', 'monitoring', 'central station', 'alarm response']
    },
    'Perimeter Security': {
        'Fencing': ['fence', 'fencing', 'barrier fence'],
        'Clear Zones': ['clear zone', 'clearance', 'vegetation', 'line of sight'],
        'Barriers/Bollards': ['bollard', 'barrier', 'vehicle barrier', 'crash barrier'],
        'Perimeter Lighting': ['perimeter light', 'security lighting', 'flood light'],
        'Waterside Security': ['waterside', 'waterfront', 'dock', 'pier', 'marina'],
        'CPTED Elements': ['cpted', 'crime prevention', 'environmental design', 'natural surveillance']
    },
    'Interior Security & Physical Barriers': {
        'Secure Areas': ['secure area', 'restricted area', 'controlled area'],
        'Safe Rooms': ['safe room', 'panic room', 'shelter in place'],
        'Physical Barriers': ['barrier', 'bollard', 'barricade', 'blast barrier'],
        'Locks': ['lock', 'deadbolt', 'keypad', 'electronic lock'],
        'Interior Lighting': ['interior light', 'emergency lighting', 'exit lighting']
    },
    'Security Force / Operations': {
        'SOC': ['soc', 'security operations center', 'operations center'],
        'Patrol / Posts': ['patrol', 'security guard', 'post', 'guard post', 'roving'],
        'Radios & Comms': ['radio', 'communication', 'two-way', 'walkie-talkie'],
        'Response Procedures': ['response procedure', 'emergency response', 'incident response']
    },
    'Emergency Management & Resilience': {
        'EAP': ['eap', 'emergency action plan', 'emergency plan'],
        'BCP': ['bcp', 'business continuity', 'continuity plan'],
        'Drills & Exercises': ['drill', 'exercise', 'tabletop', 'simulation'],
        'Mass Notification': ['mass notification', 'emergency notification', 'alert system']
    },
    'Information Sharing & Coordination': {
        'Law Enforcement Liaison': ['law enforcement', 'police liaison', 'leo'],
        'Fusion Center': ['fusion center', 'fusion'],
        'JTTF': ['jttf', 'joint terrorism task force'],
        'HSIN': ['hsin', 'homeland security information network'],
        'ISAC/ISAO': ['isac', 'isao', 'information sharing', 'analysis center']
    },
    'Cyber-Physical Infrastructure Support': {
        'UPS/Power': ['ups', 'uninterruptible power', 'backup power', 'generator'],
        'Switches & ESS Network': ['switch', 'network', 'ess network', 'ethernet'],
        'Server Rooms': ['server room', 'data center', 'server', 'rack'],
        'Cable Security': ['cable', 'fiber', 'conduit', 'cable management']
    }
}

# Keywords that indicate pure cyber (should be rejected unless ESS-related)
PURE_CYBER_KEYWORDS = [
    'malware', 'phishing', 'ransomware', 'firewall', 'antivirus', 'encryption',
    'ssl', 'tls', 'vpn', 'authentication', 'authorization', 'access control software',
    'siem', 'security information', 'log analysis', 'threat intelligence'
]

# Keywords that indicate ESS infrastructure (acceptable for Cyber-Physical)
ESS_INFRASTRUCTURE_KEYWORDS = [
    'access control system', 'video surveillance', 'intrusion detection',
    'security system', 'ess', 'electronic security', 'security network',
    'camera system', 'alarm system', 'badge reader'
]


def normalize_discipline_name(raw_discipline: str) -> Optional[str]:
    """
    Normalize raw discipline text to one of the 10 new disciplines.
    
    Rules:
    1. Check legacy mapping first
    2. Try exact match against new disciplines
    3. Try fuzzy match against new disciplines
    4. Reject pure cyber inputs unless they relate to ESS infrastructure
    
    Args:
        raw_discipline: Raw discipline text from model or user input
        
    Returns:
        Normalized discipline name or None if cannot be determined
    """
    if not raw_discipline:
        return None
    
    raw_lower = raw_discipline.strip().lower()
    
    # Step 1: Check legacy mapping
    if raw_discipline in LEGACY_DISCIPLINE_MAP:
        normalized = LEGACY_DISCIPLINE_MAP[raw_discipline]
        logger.debug(f"Legacy mapping: '{raw_discipline}' -> '{normalized}'")
        return normalized
    
    # Step 2: Check for pure cyber keywords (reject unless ESS-related)
    has_pure_cyber = any(kw in raw_lower for kw in PURE_CYBER_KEYWORDS)
    has_ess_infrastructure = any(kw in raw_lower for kw in ESS_INFRASTRUCTURE_KEYWORDS)
    
    if has_pure_cyber and not has_ess_infrastructure:
        # Pure cyber - reject unless it's explicitly about ESS infrastructure
        logger.warning(f"Rejecting pure cyber discipline: '{raw_discipline}'")
        return None
    
    # Step 3: Try exact match (case-insensitive)
    for disc in NEW_DISCIPLINES:
        if disc.lower() == raw_lower:
            return disc
    
    # Step 4: Try partial match
    for disc in NEW_DISCIPLINES:
        disc_lower = disc.lower()
        # Check if raw contains discipline or discipline contains raw
        if raw_lower in disc_lower or disc_lower in raw_lower:
            logger.debug(f"Partial match: '{raw_discipline}' -> '{disc}'")
            return disc
    
    # Step 5: Try keyword-based matching
    raw_words = set(raw_lower.split())
    
    # Access Control Systems
    if any(word in ['access', 'control', 'entry', 'badge', 'card'] for word in raw_words):
        if 'video' not in raw_lower and 'surveillance' not in raw_lower:
            return 'Access Control Systems'
    
    # Video Surveillance Systems
    if any(word in ['video', 'camera', 'surveillance', 'cctv', 'monitoring'] for word in raw_words):
        if 'access' not in raw_lower:
            return 'Video Surveillance Systems'
    
    # Intrusion Detection Systems
    if any(word in ['intrusion', 'detection', 'alarm', 'sensor'] for word in raw_words):
        return 'Intrusion Detection Systems'
    
    # Perimeter Security
    if any(word in ['perimeter', 'fence', 'barrier', 'bollard'] for word in raw_words):
        return 'Perimeter Security'
    
    # Interior Security & Physical Barriers
    if any(word in ['interior', 'physical', 'barrier', 'lock', 'secure'] for word in raw_words):
        if 'perimeter' not in raw_lower:
            return 'Interior Security & Physical Barriers'
    
    # Security Force / Operations
    if any(word in ['security', 'force', 'operations', 'guard', 'patrol', 'soc'] for word in raw_words):
        if 'management' not in raw_lower and 'governance' not in raw_lower:
            return 'Security Force / Operations'
    
    # Emergency Management & Resilience
    if any(word in ['emergency', 'resilience', 'continuity', 'drill', 'exercise'] for word in raw_words):
        return 'Emergency Management & Resilience'
    
    # Information Sharing & Coordination
    if any(word in ['information', 'sharing', 'coordination', 'liaison', 'fusion'] for word in raw_words):
        return 'Information Sharing & Coordination'
    
    # Cyber-Physical Infrastructure Support
    if any(word in ['cyber', 'physical', 'infrastructure', 'network', 'server', 'ups'] for word in raw_words):
        if has_ess_infrastructure:
            return 'Cyber-Physical Infrastructure Support'
    
    # Security Management & Governance (catch-all for policy/training/management)
    if any(word in ['management', 'governance', 'policy', 'training', 'awareness'] for word in raw_words):
        return 'Security Management & Governance'
    
    logger.warning(f"Could not normalize discipline: '{raw_discipline}'")
    return None


def infer_subtype(discipline: str, vulnerability_text: str, ofc_text: Optional[str] = None) -> Optional[str]:
    """
    Infer sub-discipline using keyword heuristics.
    
    Args:
        discipline: Normalized discipline name (one of the 10 new disciplines)
        vulnerability_text: Vulnerability description text
        ofc_text: Optional OFC text for additional context
        
    Returns:
        Sub-discipline name or None if cannot be inferred
    """
    if not discipline or discipline not in SUBTYPE_KEYWORDS:
        return None
    
    if not vulnerability_text and not ofc_text:
        return None
    
    # Combine text for analysis
    combined_text = f"{vulnerability_text or ''} {ofc_text or ''}".lower()
    
    # Get subtype keywords for this discipline
    subtype_keywords = SUBTYPE_KEYWORDS.get(discipline, {})
    
    best_subtype = None
    best_score = 0
    
    # Score each subtype based on keyword matches
    for subtype_name, keywords in subtype_keywords.items():
        score = 0
        for keyword in keywords:
            if keyword in combined_text:
                score += 1
        
        if score > best_score:
            best_score = score
            best_subtype = subtype_name
    
    # Only return if we have a confident match (at least 1 keyword)
    if best_score > 0:
        logger.debug(f"Inferred subtype '{best_subtype}' for discipline '{discipline}' (score: {best_score})")
        return best_subtype
    
    return None


def resolve_discipline_and_subtype(
    raw_discipline: str,
    vulnerability_text: str = "",
    ofc_text: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Resolve discipline name to normalized discipline, discipline_id, and subtype.
    
    This is the main entry point for discipline resolution.
    
    Args:
        raw_discipline: Raw discipline text from model or user input
        vulnerability_text: Vulnerability description for subtype inference
        ofc_text: Optional OFC text for subtype inference
        
    Returns:
        Tuple of (normalized_discipline_name, discipline_id, subtype_name) or (None, None, None)
    """
    # Normalize discipline name
    normalized_discipline = normalize_discipline_name(raw_discipline)
    
    if not normalized_discipline:
        return None, None, None
    
    # Get discipline_id from Supabase
    discipline_id = None
    try:
        disc_record = get_discipline_record(normalized_discipline, fuzzy=True)
        if disc_record:
            discipline_id = disc_record.get('id')
    except Exception as e:
        logger.warning(f"Could not get discipline_id for '{normalized_discipline}': {e}")
    
    # Infer subtype
    subtype_name = infer_subtype(normalized_discipline, vulnerability_text, ofc_text)
    
    return normalized_discipline, discipline_id, subtype_name


def get_subtype_id(subtype_name: str, discipline_id: Optional[str] = None) -> Optional[str]:
    """
    Get subtype ID from Supabase.
    
    Args:
        subtype_name: Subtype name
        discipline_id: Optional discipline_id to narrow search
        
    Returns:
        Subtype ID (UUID) or None if not found
    """
    if not subtype_name:
        return None
    
    try:
        client = get_supabase_client()
        query = client.table("discipline_subtypes").select("id").eq("name", subtype_name).eq("is_active", True)
        
        if discipline_id:
            query = query.eq("discipline_id", discipline_id)
        
        result = query.maybe_single().execute()
        
        if result.data:
            return result.data.get('id')
        
        return None
    except Exception as e:
        logger.warning(f"Could not get subtype_id for '{subtype_name}': {e}")
        return None

