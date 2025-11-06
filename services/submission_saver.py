"""
Submission Saver Service
Saves extracted vulnerabilities, OFCs, links, and sources to submission tables
"""

import logging
from typing import List, Dict, Optional
from services.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

def save_extraction_to_submission(
    submission_id: str,
    extraction_results: Dict
) -> Dict[str, any]:
    """
    Save extraction results to submission tables.
    
    Args:
        submission_id: UUID of parent submission
        extraction_results: Dictionary from extract_from_document()
        
    Returns:
        Dictionary with save statistics
    """
    client = get_supabase_client()
    
    stats = {
        'vulnerabilities_saved': 0,
        'ofcs_saved': 0,
        'links_saved': 0,
        'source_saved': False,
        'errors': []
    }
    
    try:
        # PHASE 5: Save source record
        source_record = extraction_results.get('source', {})
        source_record['submission_id'] = submission_id
        
        source_result = client.table('submission_sources').insert([source_record]).execute()
        if source_result.data:
            stats['source_saved'] = True
            source_id = source_result.data[0]['id']
            logger.info(f"Saved source record: {source_id}")
        else:
            stats['errors'].append("Failed to save source record")
        
        # Save vulnerabilities
        vulnerabilities = extraction_results.get('vulnerabilities', [])
        vulnerability_ids = {}
        
        for vuln in vulnerabilities:
            vuln_record = {
                'submission_id': submission_id,
                'vulnerability': vuln.get('vulnerability'),
                'discipline': vuln.get('discipline'),
                'source': vuln.get('source'),
                'source_title': vuln.get('source_title'),
                'source_url': vuln.get('source_url'),
                'sector': vuln.get('sector'),
                'subsector': vuln.get('subsector'),
                'parser_version': vuln.get('parser_version'),
                'enhanced_extraction': vuln.get('enhanced_extraction', {})
            }
            
            try:
                result = client.table('submission_vulnerabilities').insert([vuln_record]).execute()
                if result.data:
                    vuln_id = result.data[0]['id']
                    # Store for linking
                    key = vuln.get('vulnerability', '')[:50]  # Use first 50 chars as key
                    vulnerability_ids[key] = vuln_id
                    stats['vulnerabilities_saved'] += 1
            except Exception as e:
                stats['errors'].append(f"Failed to save vulnerability: {str(e)}")
                logger.error(f"Error saving vulnerability: {e}")
        
        # Save OFCs
        ofcs = extraction_results.get('ofcs', [])
        ofc_ids = {}
        
        for ofc in ofcs:
            ofc_record = {
                'submission_id': submission_id,
                'vulnerability_id': None,  # Will be set via links
                'option_text': ofc.get('option_text'),
                'discipline': ofc.get('discipline'),
                'source': ofc.get('source'),
                'source_title': ofc.get('source_title'),
                'source_url': ofc.get('source_url'),
                'confidence_score': ofc.get('confidence_score'),
                'pattern_matched': ofc.get('pattern_matched'),
                'context': ofc.get('context'),
                'citations': ofc.get('citations', [])
            }
            
            try:
                result = client.table('submission_options_for_consideration').insert([ofc_record]).execute()
                if result.data:
                    ofc_id = result.data[0]['id']
                    # Store for linking
                    key = ofc.get('option_text', '')[:50]
                    ofc_ids[key] = ofc_id
                    stats['ofcs_saved'] += 1
            except Exception as e:
                stats['errors'].append(f"Failed to save OFC: {str(e)}")
                logger.error(f"Error saving OFC: {e}")
        
        # Save links (vulnerability-OFC links)
        # Note: Links need vulnerability_id and ofc_id which we now have
        # We'll create links based on section proximity
        links_created = 0
        
        # Create links between vulnerabilities and OFCs in same sections
        # This is a simplified version - in production, use the actual link data from extraction
        for vuln_key, vuln_id in list(vulnerability_ids.items())[:10]:  # Limit to prevent too many links
            for ofc_key, ofc_id in list(ofc_ids.items())[:5]:  # Limit links per vulnerability
                try:
                    link_record = {
                        'submission_id': submission_id,
                        'vulnerability_id': vuln_id,
                        'ofc_id': ofc_id,
                        'link_type': 'inferred',  # Will be 'direct' if same section
                        'confidence_score': 0.7
                    }
                    client.table('submission_vulnerability_ofc_links').insert([link_record]).execute()
                    links_created += 1
                except Exception as e:
                    logger.warn(f"Failed to create vulnerability-OFC link: {e}")
        
        stats['links_saved'] = links_created
        
        # Save source-OFC links
        if stats['source_saved'] and ofc_ids:
            for ofc_id in ofc_ids.values():
                try:
                    ofc_source_link = {
                        'submission_id': submission_id,
                        'ofc_id': ofc_id,
                        'source_id': source_id
                    }
                    client.table('submission_ofc_sources').insert([ofc_source_link]).execute()
                except Exception as e:
                    logger.warn(f"Failed to link OFC to source: {e}")
        
        logger.info(f"Extraction save complete: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error saving extraction results: {e}")
        stats['errors'].append(str(e))
        return stats

