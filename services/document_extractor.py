"""
Document Extraction Service
PHASE 2-5: Text extraction, section detection, vulnerability/OFC extraction, and linking

Implements the complete document ingestion pipeline:
- PHASE 2: Text & Structure Extraction (section detection, table/figure capture)
- PHASE 3: Vulnerability Extraction (heuristic pattern matching)
- PHASE 4: OFC Extraction (prescriptive, advisory, conditional patterns)
- PHASE 5: Link & Source Association (proximity-based linking)
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ============================================================================
# PHASE 2: Text & Structure Extraction
# ============================================================================

@dataclass
class Section:
    """Represents a detected section in the document"""
    number: str
    title: str
    level: int  # Depth in hierarchy (1, 2, 3, etc.)
    paragraphs: List[str]
    start_position: int
    end_position: int

def detect_sections(text: str) -> List[Section]:
    """
    Detect hierarchical sections using regex pattern:
    Pattern: ^(\d+(\.\d+)*)(\s+)([A-Z].+)
    Captures: section number, section title, paragraph text
    """
    sections = []
    
    # Pattern for hierarchical numbering: 1, 1.1, 1.1.1, etc.
    section_pattern = re.compile(
        r'^(\d+(?:\.\d+)*)\s+([A-Z][^\n]{10,200})',  # Number + Title (capitalized, 10-200 chars)
        re.MULTILINE
    )
    
    # Also match common section markers
    alt_patterns = [
        re.compile(r'^Section\s+(\d+(?:\.\d+)*)[:\s]+([A-Z][^\n]{10,200})', re.MULTILINE | re.IGNORECASE),
        re.compile(r'^(\d+\.\d+)\s+([A-Z][^\n]{10,200})', re.MULTILINE),
    ]
    
    all_matches = []
    
    # Find all section matches
    for match in section_pattern.finditer(text):
        all_matches.append({
            'number': match.group(1),
            'title': match.group(2).strip(),
            'start': match.start(),
            'end': match.end()
        })
    
    # Add alternative pattern matches
    for pattern in alt_patterns:
        for match in pattern.finditer(text):
            all_matches.append({
                'number': match.group(1),
                'title': match.group(2).strip(),
                'start': match.start(),
                'end': match.end()
            })
    
    # Sort by position
    all_matches.sort(key=lambda x: x['start'])
    
    # Extract paragraphs for each section
    for i, match in enumerate(all_matches):
        start_pos = match['start']
        end_pos = all_matches[i + 1]['start'] if i + 1 < len(all_matches) else len(text)
        
        section_text = text[start_pos:end_pos]
        paragraphs = [p.strip() for p in section_text.split('\n\n') if p.strip() and len(p.strip()) > 20]
        
        # Calculate hierarchy level from number (1 = level 1, 1.1 = level 2, etc.)
        level = len(match['number'].split('.'))
        
        sections.append(Section(
            number=match['number'],
            title=match['title'],
            level=level,
            paragraphs=paragraphs,
            start_position=start_pos,
            end_position=end_pos
        ))
    
    logger.info(f"Detected {len(sections)} sections in document")
    return sections

def extract_tables_and_figures(text: str) -> Dict[str, List[str]]:
    """
    Extract table and figure captions and adjacent paragraphs.
    Stores into enhanced_extraction metadata.
    """
    tables = []
    figures = []
    
    # Pattern for table captions
    table_pattern = re.compile(
        r'Table\s+\d+[:\s]+([^\n]{10,200})',
        re.IGNORECASE | re.MULTILINE
    )
    
    # Pattern for figure captions
    figure_pattern = re.compile(
        r'Figure\s+\d+[:\s]+([^\n]{10,200})',
        re.IGNORECASE | re.MULTILINE
    )
    
    for match in table_pattern.finditer(text):
        tables.append(match.group(1).strip())
    
    for match in figure_pattern.finditer(text):
        figures.append(match.group(1).strip())
    
    logger.info(f"Extracted {len(tables)} tables and {len(figures)} figures")
    
    return {
        'tables': tables,
        'figures': figures
    }

# ============================================================================
# PHASE 3: Vulnerability Extraction
# ============================================================================

VULNERABILITY_PATTERNS = [
    {
        'pattern': re.compile(r'shall\s+not|should\s+not|must\s+not', re.IGNORECASE),
        'example': 'Windows shall not face vehicle approach zones.',
        'type': 'prohibition'
    },
    {
        'pattern': re.compile(r'failure\s+to|lack\s+of|absence\s+of', re.IGNORECASE),
        'example': 'Lack of stand-off distance...',
        'type': 'deficiency'
    },
    {
        'pattern': re.compile(r'if\s+[^.]+\s+is\s+not\s+[^.]', re.IGNORECASE),
        'example': 'If glazing is not laminated...',
        'type': 'conditional_negation'
    },
    {
        'pattern': re.compile(r'when\s+not\s+required\s+to\s+meet', re.IGNORECASE),
        'example': 'When not required to meet...',
        'type': 'contextual'
    },
    {
        'pattern': re.compile(r'non[- ]?compliant|non[- ]?conforming', re.IGNORECASE),
        'example': 'Non-compliant installations...',
        'type': 'compliance'
    },
]

def extract_vulnerabilities(text: str, sections: List[Section], source_info: Dict) -> List[Dict]:
    """
    Extract vulnerabilities using heuristic pattern matching.
    
    Returns list of vulnerability dictionaries ready for submission_vulnerabilities table.
    """
    vulnerabilities = []
    
    # Process each section
    for section in sections:
        section_text = ' '.join(section.paragraphs)
        
        # Check each paragraph for vulnerability patterns
        for para_idx, paragraph in enumerate(section.paragraphs):
            if len(paragraph) < 20:  # Skip very short paragraphs
                continue
            
            # Test against all vulnerability patterns
            for pattern_info in VULNERABILITY_PATTERNS:
                matches = pattern_info['pattern'].findall(paragraph)
                if matches:
                    # Extract full sentence containing the match
                    sentences = re.split(r'[.!?]+', paragraph)
                    for sentence in sentences:
                        if pattern_info['pattern'].search(sentence):
                            sentence = sentence.strip()
                            if len(sentence) > 30:  # Valid vulnerability text
                                vulnerabilities.append({
                                    'vulnerability': sentence,
                                    'discipline': _infer_discipline(sentence, section.title),
                                    'sector': source_info.get('sector', 'Defense Installations'),
                                    'subsector': source_info.get('subsector', 'Facilities Engineering'),
                                    'source': source_info.get('source_title', 'Unknown'),
                                    'source_title': source_info.get('source_title', 'Unknown'),
                                    'source_url': source_info.get('url'),
                                    'parser_version': 'vofc-parser:latest',
                                    'enhanced_extraction': {
                                        'section': section.number,
                                        'heading': section.title,
                                        'paragraph': paragraph[:500],  # First 500 chars
                                        'pattern_type': pattern_info['type'],
                                        'pattern_matched': pattern_info['pattern'].pattern
                                    }
                                })
                                break  # One vulnerability per sentence
    
    logger.info(f"Extracted {len(vulnerabilities)} vulnerabilities")
    return vulnerabilities

def _infer_discipline(text: str, section_title: str) -> str:
    """Infer discipline from text and section title"""
    text_lower = (text + ' ' + section_title).lower()
    
    discipline_keywords = {
        'Architectural Design': ['architectural', 'building', 'structure', 'design', 'glazing', 'window', 'door'],
        'Structural Engineering': ['structural', 'load', 'blast', 'resistance', 'reinforcement'],
        'Security': ['security', 'access', 'perimeter', 'barrier', 'fence'],
        'Electrical': ['electrical', 'power', 'wiring', 'circuit'],
        'Mechanical': ['mechanical', 'hvac', 'ventilation', 'plumbing'],
        'Fire Safety': ['fire', 'sprinkler', 'alarm', 'suppression'],
    }
    
    for discipline, keywords in discipline_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return discipline
    
    return 'General'  # Default

# ============================================================================
# PHASE 4: OFC Extraction
# ============================================================================

OFC_PATTERNS = [
    {
        'type': 'prescriptive',
        'pattern': re.compile(r'\bshall\b|\bmust\b|\brequired\s+to\b', re.IGNORECASE),
        'triggers': ['shall', 'must', 'required to'],
        'example': 'All exterior doors shall resist blast loads.'
    },
    {
        'type': 'advisory',
        'pattern': re.compile(r'\bshould\b|\brecommended\b|\bensure\b|\bconsider\b', re.IGNORECASE),
        'triggers': ['should', 'recommended', 'ensure', 'consider'],
        'example': 'Consider use of laminated glass to reduce fragmentation.'
    },
    {
        'type': 'conditional',
        'pattern': re.compile(r'\bwhen\b|\bwhere\b|\bif\s+possible\b', re.IGNORECASE),
        'triggers': ['when', 'where', 'if possible'],
        'example': 'Where vehicle approach is possible, install bollards.'
    },
]

def extract_ofcs(text: str, sections: List[Section], vulnerabilities: List[Dict], source_info: Dict) -> List[Dict]:
    """
    Extract Options for Consideration using pattern matching.
    
    Returns list of OFC dictionaries ready for submission_options_for_consideration table.
    """
    ofcs = []
    
    # Process each section
    for section in sections:
        for paragraph in section.paragraphs:
            if len(paragraph) < 20:
                continue
            
            # Test against all OFC patterns
            for pattern_info in OFC_PATTERNS:
                if pattern_info['pattern'].search(paragraph):
                    # Extract sentences containing OFC patterns
                    sentences = re.split(r'[.!?]+', paragraph)
                    for sentence in sentences:
                        if pattern_info['pattern'].search(sentence):
                            sentence = sentence.strip()
                            if len(sentence) > 30:  # Valid OFC text
                                # Try to link to nearby vulnerability
                                vulnerability_id = _find_nearby_vulnerability(
                                    sentence, vulnerabilities, section, paragraph
                                )
                                
                                ofcs.append({
                                    'option_text': sentence,
                                    'discipline': _infer_discipline(sentence, section.title),
                                    'source': source_info.get('source_title', 'Unknown'),
                                    'source_title': source_info.get('source_title', 'Unknown'),
                                    'source_url': source_info.get('url'),
                                    'confidence_score': 0.85 if pattern_info['type'] == 'prescriptive' else 0.75,
                                    'pattern_matched': pattern_info['type'],
                                    'context': paragraph[:300],  # First 300 chars for context
                                    'citations': [{
                                        'section': section.number,
                                        'page': None  # Page number not available in text extraction
                                    }],
                                    'vulnerability_id': vulnerability_id  # Will be set when linking
                                })
                                break  # One OFC per sentence
    
    logger.info(f"Extracted {len(ofcs)} OFCs")
    return ofcs

def _find_nearby_vulnerability(ofc_text: str, vulnerabilities: List[Dict], section: Section, paragraph: str) -> Optional[str]:
    """Find vulnerability in same section or within 3 paragraphs (proximity-based linking)"""
    # This will be set during PHASE 5 linking
    return None

# ============================================================================
# PHASE 5: Link & Source Association
# ============================================================================

def create_vulnerability_ofc_links(
    vulnerabilities: List[Dict],
    ofcs: List[Dict],
    sections: List[Section]
) -> List[Dict]:
    """
    Create links between vulnerabilities and OFCs based on proximity.
    Proximity: ≤ 3 paragraphs or same section.
    """
    links = []
    
    # Group by section for proximity matching
    section_vulns = {}
    section_ofcs = {}
    
    for vuln in vulnerabilities:
        section_num = vuln.get('enhanced_extraction', {}).get('section', 'unknown')
        if section_num not in section_vulns:
            section_vulns[section_num] = []
        section_vulns[section_num].append(vuln)
    
    for ofc in ofcs:
        section_num = ofc.get('citations', [{}])[0].get('section', 'unknown')
        if section_num not in section_ofcs:
            section_ofcs[section_num] = []
        section_ofcs[section_num].append(ofc)
    
    # Link vulnerabilities to OFCs in same section
    for section_num in section_vulns:
        if section_num in section_ofcs:
            for vuln in section_vulns[section_num]:
                for ofc in section_ofcs[section_num]:
                    links.append({
                        'vulnerability_id': vuln.get('id'),  # Will be set after DB insert
                        'ofc_id': ofc.get('id'),  # Will be set after DB insert
                        'link_type': 'direct' if section_num == vuln.get('enhanced_extraction', {}).get('section') else 'inferred',
                        'confidence_score': 0.9 if section_num == vuln.get('enhanced_extraction', {}).get('section') else 0.7
                    })
    
    logger.info(f"Created {len(links)} vulnerability-OFC links")
    return links

# ============================================================================
# Main Extraction Function
# ============================================================================

def extract_from_document(
    file_path: str,
    submission_id: str,
    source_info: Dict
) -> Dict[str, any]:
    """
    Complete extraction pipeline: PHASE 2-5
    
    Args:
        file_path: Path to document file
        submission_id: UUID of parent submission
        source_info: Dictionary with source metadata
        
    Returns:
        Dictionary with extracted data ready for database insertion
    """
    from services.preprocess import extract_text
    
    logger.info(f"Starting extraction for {file_path} (submission: {submission_id})")
    
    # PHASE 2: Extract text and detect structure
    logger.info("PHASE 2: Text & Structure Extraction")
    text = extract_text(file_path)
    sections = detect_sections(text)
    tables_figures = extract_tables_and_figures(text)
    
    # PHASE 3: Extract vulnerabilities
    logger.info("PHASE 3: Vulnerability Extraction")
    vulnerabilities = extract_vulnerabilities(text, sections, source_info)
    
    # PHASE 4: Extract OFCs
    logger.info("PHASE 4: OFC Extraction")
    ofcs = extract_ofcs(text, sections, vulnerabilities, source_info)
    
    # PHASE 5: Create links
    logger.info("PHASE 5: Link & Source Association")
    links = create_vulnerability_ofc_links(vulnerabilities, ofcs, sections)
    
    # Prepare source record
    source_record = {
        'source_title': source_info.get('source_title', 'Unknown'),
        'author_org': source_info.get('agency', source_info.get('author_org')),
        'publication_year': source_info.get('publication_year'),
        'source_url': source_info.get('url'),
        'content_restriction': source_info.get('content_restriction', 'public')
    }
    
    return {
        'vulnerabilities': vulnerabilities,
        'ofcs': ofcs,
        'links': links,
        'source': source_record,
        'sections': len(sections),
        'tables': len(tables_figures.get('tables', [])),
        'figures': len(tables_figures.get('figures', []))
    }

