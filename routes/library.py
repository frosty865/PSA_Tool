"""
PSA Library routes
Routes: /api/library/*
"""

from flask import Blueprint, jsonify, request
from services.processor import search_library, get_library_entry
from services.supabase_client import get_supabase_client

library_bp = Blueprint('library', __name__)

@library_bp.route('/api/library/search', methods=['GET', 'POST', 'OPTIONS'])
def search_library_route():
    """Search the PSA library"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if request.method == 'POST':
            data = request.get_json()
            query = data.get('query', '') or data.get('q', '')
        else:
            query = request.args.get('query', '') or request.args.get('q', '')
        
        if not query:
            return jsonify({
                "success": False,
                "error": "query parameter required",
                "results": [],
                "service": "PSA Processing Server"
            }), 400
        
        results = search_library(query)
        return jsonify({
            "success": True,
            **results,
            "service": "PSA Processing Server"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "results": [],
            "service": "PSA Processing Server"
        }), 500

@library_bp.route('/api/library/entry', methods=['GET'])
def get_entry():
    """Get a specific library entry"""
    try:
        entry_id = request.args.get('id')
        if not entry_id:
            return jsonify({
                "success": False,
                "error": "id parameter required",
                "service": "PSA Processing Server"
            }), 400
        
        entry = get_library_entry(entry_id)
        return jsonify({
            "success": True,
            "entry": entry,
            "service": "PSA Processing Server"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500

@library_bp.route('/api/vofc/library', methods=['GET', 'OPTIONS'])
def get_vofc_library():
    """
    Get all vulnerabilities and OFCs for the VOFC Library Viewer
    Returns flat list of vulnerability-OFC pairs with metadata
    """
    if request.method == 'OPTIONS':
        return '', 200
    try:
        supabase = get_supabase_client()
        
        # Get all vulnerabilities
        vuln_res = supabase.table('vulnerabilities').select('*').execute()
        vulnerabilities = vuln_res.data if vuln_res.data else []
        
        # Get all OFCs
        ofc_res = supabase.table('options_for_consideration').select('*').execute()
        ofcs = ofc_res.data if ofc_res.data else []
        
        # Get vulnerability-OFC links
        links_res = supabase.table('vulnerability_ofc_links').select('*').execute()
        links = links_res.data if links_res.data else []
        
        # Get disciplines, sectors, subsectors for lookups
        disc_res = supabase.table('disciplines').select('id, name, category').eq('is_active', True).execute()
        disciplines = {}
        for d in (disc_res.data if disc_res.data else []):
            # Handle both UUID and string IDs, and discipline name lookup
            disc_id = d.get('id')
            disc_name = d.get('name') or d.get('category') or ''
            if disc_id:
                disciplines[disc_id] = disc_name
            # Also handle discipline as text/category matching
            if d.get('category'):
                disciplines[d.get('category')] = disc_name
        
        sect_res = supabase.table('sectors').select('id, sector_name').eq('is_active', True).execute()
        sectors = {}
        for s in (sect_res.data if sect_res.data else []):
            sect_id = s.get('id')
            sect_name = s.get('sector_name') or ''
            if sect_id:
                sectors[sect_id] = sect_name
        
        subsect_res = supabase.table('subsectors').select('id, subsector_name').eq('is_active', True).execute()
        subsectors = {}
        for ss in (subsect_res.data if subsect_res.data else []):
            subsect_id = ss.get('id')
            subsect_name = ss.get('subsector_name') or ''
            if subsect_id:
                subsectors[subsect_id] = subsect_name
        
        # Build flat list: one row per vulnerability-OFC pair
        result = []
        for link in links:
            vuln = next((v for v in vulnerabilities if v['id'] == link['vulnerability_id']), None)
            ofc = next((o for o in ofcs if o['id'] == link['ofc_id']), None)
            
            if not vuln or not ofc:
                continue
            
            disc_value = vuln.get('discipline') or ofc.get('discipline')
            disc_name = ''
            if disc_value:
                # Try to find discipline name by ID or by text/category
                disc_name = disciplines.get(disc_value) or disc_value
            
            result.append({
                'filename': '',  # No filename in production data
                'discipline_id': disc_value,
                'discipline_name': disc_name,
                'sector_id': vuln.get('sector_id'),
                'sector_name': sectors.get(vuln.get('sector_id')) if vuln.get('sector_id') else '',
                'subsector_id': vuln.get('subsector_id'),
                'subsector_name': subsectors.get(vuln.get('subsector_id')) if vuln.get('subsector_id') else '',
                'vulnerability': vuln.get('vulnerability') or vuln.get('vulnerability_name') or vuln.get('title') or '',
                'ofc': ofc.get('option_text') or ''
            })
        
        # Also include vulnerabilities without OFCs
        linked_vuln_ids = {link['vulnerability_id'] for link in links}
        for vuln in vulnerabilities:
            if vuln['id'] not in linked_vuln_ids:
                disc_value = vuln.get('discipline')
                disc_name = ''
                if disc_value:
                    disc_name = disciplines.get(disc_value) or disc_value
                
                result.append({
                    'filename': '',
                    'discipline_id': disc_value,
                    'discipline_name': disc_name,
                    'sector_id': vuln.get('sector_id'),
                    'sector_name': sectors.get(vuln.get('sector_id')) if vuln.get('sector_id') else '',
                    'subsector_id': vuln.get('subsector_id'),
                    'subsector_name': subsectors.get(vuln.get('subsector_id')) if vuln.get('subsector_id') else '',
                    'vulnerability': vuln.get('vulnerability') or vuln.get('vulnerability_name') or vuln.get('title') or '',
                    'ofc': ''
                })
        
        return jsonify(result)
        
    except Exception as e:
        print(f'[VOFC Library] Error: {str(e)}')
        # Return empty array on error to prevent viewer crashes
        return jsonify([]), 200

# Add more library routes as needed from your old server.py

