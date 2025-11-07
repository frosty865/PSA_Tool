"""
Integration example for VOFC Parser Engine
Shows how to integrate the parser into the document extraction pipeline
"""

import yaml
from pathlib import Path
from .vofc_parser_engine import VOFCParserEngine
from services.preprocess import extract_text


def extract_with_vofc_parser(file_path: str, source_title: str = "Unknown Document"):
    """
    Extract vulnerabilities and OFCs using the VOFC parser engine.
    
    Args:
        file_path: Path to document file (PDF, DOCX, etc.)
        source_title: Title/source identifier for the document
        
    Returns:
        List of extracted records with vulnerability and OFC information
    """
    # Load ruleset
    ruleset_path = Path(__file__).parent / "ruleset_vofc_parser.yaml"
    with open(ruleset_path, 'r', encoding='utf-8') as f:
        rules = yaml.safe_load(f)
    
    # Initialize parser
    parser = VOFCParserEngine(rules)
    
    # Extract text from document
    text = extract_text(file_path)
    
    # Extract vulnerabilities and OFCs
    records = parser.extract(text, source_title=source_title)
    
    return records


def convert_to_submission_format(records, submission_id: str, source_info: dict):
    """
    Convert VOFC parser results to submission table format.
    
    Args:
        records: List of extracted records from parser
        submission_id: UUID of parent submission
        source_info: Dictionary with source metadata
        
    Returns:
        Dictionary formatted for submission_saver.py
    """
    vulnerabilities = []
    ofcs = []
    links = []
    
    for record in records:
        # Create vulnerability if present
        if record.get('vulnerability'):
            vuln = {
                'submission_id': submission_id,
                'vulnerability': record['vulnerability'],
                'discipline': 'Architectural Design',  # Can be inferred from context
                'sector': 'Defense Installations',  # Default
                'subsector': 'Facilities Engineering',  # Default
                'source': record['source_title'],
                'source_title': record['source_title'],
                'parser_version': 'vofc-parser:latest',
                'enhanced_extraction': {
                    'section': record.get('section', 'Unknown'),
                    'context': record.get('context', ''),
                    'pattern_matched': record.get('pattern_matched', '')
                }
            }
            vulnerabilities.append(vuln)
        
        # Create OFC if present
        if record.get('option_text'):
            ofc = {
                'submission_id': submission_id,
                'option_text': record['option_text'],
                'discipline': 'Architectural Design',  # Can be inferred
                'source': record['source_title'],
                'confidence_score': record.get('confidence_score', 0.8),
                'pattern_matched': record.get('pattern_matched', ''),
                'context': record.get('context', '')
            }
            ofcs.append(ofc)
            
            # Create link if both vulnerability and OFC exist
            if record.get('vulnerability') and len(vulnerabilities) > 0:
                links.append({
                    'vulnerability_id': len(vulnerabilities) - 1,  # Index, will be replaced with actual ID
                    'ofc_id': len(ofcs) - 1,  # Index, will be replaced
                })
    
    return {
        'vulnerabilities': vulnerabilities,
        'ofcs': ofcs,
        'links': links
    }


# Example usage in submission_processor.py:
"""
from services.vofc_parser.integration_example import extract_with_vofc_parser, convert_to_submission_format
from services.submission_saver import save_extraction_to_submission

# Extract using VOFC parser
records = extract_with_vofc_parser(file_path, source_title="UFC 4-010-01 (2018 C1)")

# Convert to submission format
extraction_results = convert_to_submission_format(
    records,
    submission_id=submission_id,
    source_info=source_info
)

# Save to submission tables
save_extraction_to_submission(submission_id, extraction_results)
"""

