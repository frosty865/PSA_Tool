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
        source_data = extraction_results.get('source', {})
        source_record = {
            'submission_id': submission_id,
            'source_title': source_data.get('source_title'),
            'author_org': source_data.get('author_org'),
            'publication_year': source_data.get('publication_year'),
            'source_url': source_data.get('source_url'),
            'content_restriction': source_data.get('content_restriction', 'public'),
            # Optional fields (nullable)
            'source_text': source_data.get('source_text'),  # Can be null
            'reference_number': source_data.get('reference_number')  # Can be null
        }
        
        source_result = client.table('submission_sources').insert([source_record]).execute()
        if source_result.data:
            stats['source_saved'] = True
            source_id = source_result.data[0]['id']
            logger.info(f"Saved source record: {source_id}")
        else:
            stats['errors'].append("Failed to save source record")
            source_id = None
        
        # Save vulnerabilities
        vulnerabilities = extraction_results.get('vulnerabilities', [])
        vulnerability_ids = {}  # Map: (section, vulnerability_text) -> vuln_id
        
        for idx, vuln in enumerate(vulnerabilities):
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
                    # Store for linking: use section + vulnerability text as key
                    section = vuln.get('enhanced_extraction', {}).get('section', 'unknown')
                    vuln_text = vuln.get('vulnerability', '')[:100]  # First 100 chars
                    key = (section, vuln_text)
                    vulnerability_ids[key] = {
                        'id': vuln_id,
                        'vulnerability': vuln  # Store full vuln for matching
                    }
                    stats['vulnerabilities_saved'] += 1
            except Exception as e:
                stats['errors'].append(f"Failed to save vulnerability: {str(e)}")
                logger.error(f"Error saving vulnerability: {e}")
        
        # Save OFCs
        ofcs = extraction_results.get('ofcs', [])
        ofc_ids = {}  # Map: (section, option_text) -> ofc_id
        
        for ofc in ofcs:
            ofc_record = {
                'submission_id': submission_id,
                'vulnerability_id': None,  # Will be set via links table
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
                    # Store for linking: use section + option text as key
                    section = ofc.get('citations', [{}])[0].get('section', 'unknown')
                    ofc_text = ofc.get('option_text', '')[:100]  # First 100 chars
                    key = (section, ofc_text)
                    ofc_ids[key] = {
                        'id': ofc_id,
                        'ofc': ofc  # Store full ofc for matching
                    }
                    stats['ofcs_saved'] += 1
            except Exception as e:
                stats['errors'].append(f"Failed to save OFC: {str(e)}")
                logger.error(f"Error saving OFC: {e}")
        
        # Save links (vulnerability-OFC links)
        # Use links from extraction results, matching by section
        links_from_extraction = extraction_results.get('links', [])
        links_created = 0
        
        if links_from_extraction:
            # Use links from extraction (they have section info)
            for link in links_from_extraction:
                # Find matching vulnerability and OFC by section and text
                vuln_section = link.get('vulnerability_section', 'unknown')
                ofc_section = link.get('ofc_section', 'unknown')
                vuln_text_match = link.get('vulnerability_text', '')
                ofc_text_match = link.get('ofc_text', '')
                
                # Find vulnerability in this section (prefer text match if available)
                matching_vuln = None
                for (section, vuln_text), vuln_data in vulnerability_ids.items():
                    if section == vuln_section:
                        # If text match provided, prefer exact match
                        if vuln_text_match:
                            if vuln_text_match.lower() in vuln_text.lower() or vuln_text.lower() in vuln_text_match.lower():
                                matching_vuln = vuln_data
                                break
                        else:
                            # No text match, use first in section
                            matching_vuln = vuln_data
                            break
                
                # Find OFC in this section (prefer text match if available)
                matching_ofc = None
                for (section, ofc_text), ofc_data in ofc_ids.items():
                    if section == ofc_section:
                        # If text match provided, prefer exact match
                        if ofc_text_match:
                            if ofc_text_match.lower() in ofc_text.lower() or ofc_text.lower() in ofc_text_match.lower():
                                matching_ofc = ofc_data
                                break
                        else:
                            # No text match, use first in section
                            matching_ofc = ofc_data
                            break
                
                # Create link if both found
                if matching_vuln and matching_ofc:
                    try:
                        link_record = {
                            'submission_id': submission_id,
                            'vulnerability_id': matching_vuln['id'],
                            'ofc_id': matching_ofc['id'],
                            'link_type': link.get('link_type', 'inferred'),
                            'confidence_score': link.get('confidence_score', 0.7)
                        }
                        client.table('submission_vulnerability_ofc_links').insert([link_record]).execute()
                        links_created += 1
                    except Exception as e:
                        logger.warn(f"Failed to create vulnerability-OFC link: {e}")
        else:
            # Fallback: Create links based on same section (simplified)
            # Group by section
            section_vulns = {}
            section_ofcs = {}
            
            for (section, _), vuln_data in vulnerability_ids.items():
                if section not in section_vulns:
                    section_vulns[section] = []
                section_vulns[section].append(vuln_data)
            
            for (section, _), ofc_data in ofc_ids.items():
                if section not in section_ofcs:
                    section_ofcs[section] = []
                section_ofcs[section].append(ofc_data)
            
            # Link vulnerabilities to OFCs in same section
            for section in section_vulns:
                if section in section_ofcs:
                    for vuln_data in section_vulns[section]:
                        for ofc_data in section_ofcs[section]:
                            try:
                                link_record = {
                                    'submission_id': submission_id,
                                    'vulnerability_id': vuln_data['id'],
                                    'ofc_id': ofc_data['id'],
                                    'link_type': 'direct',  # Same section = direct
                                    'confidence_score': 0.9
                                }
                                client.table('submission_vulnerability_ofc_links').insert([link_record]).execute()
                                links_created += 1
                            except Exception as e:
                                logger.warn(f"Failed to create vulnerability-OFC link: {e}")
        
        stats['links_saved'] = links_created
        
        # Save source-OFC links
        if stats['source_saved'] and source_id and ofc_ids:
            for ofc_data in ofc_ids.values():
                try:
                    ofc_source_link = {
                        'submission_id': submission_id,
                        'ofc_id': ofc_data['id'],
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

