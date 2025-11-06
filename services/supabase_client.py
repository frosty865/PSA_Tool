"""
Supabase client service
Handles all Supabase database operations
"""

import os
import requests

try:
    from supabase import create_client, Client
except ImportError:
    # Fallback if supabase-py not installed
    def create_client(url, key):
        raise ImportError("supabase-py package not installed. Install with: pip install supabase")
    Client = None

# Use SUPABASE_URL (primary) or fallback to NEXT_PUBLIC_SUPABASE_URL
SUPABASE_URL = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL', '').rstrip('/')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')

supabase: Client = None

def get_supabase_client():
    """Get or create Supabase client"""
    global supabase
    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise Exception("Supabase credentials not configured")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase

def test_supabase():
    """Test Supabase connection (assumes Supabase is externally configured)"""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return "missing"
        
        # Try to use supabase client if available
        try:
            client = get_supabase_client()
            result = client.table('users').select('id').limit(1).execute()
            return "ok"
        except ImportError:
            # Fallback: just check if URL is configured
            if SUPABASE_URL and SUPABASE_KEY:
                return "ok"
            return "error"
    except Exception:
        return "error"

def push_to_supabase(table, data):
    """Push data to Supabase table"""
    try:
        client = get_supabase_client()
        result = client.table(table).insert(data).execute()
        return result.data
    except Exception as e:
        raise Exception(f"Supabase insert failed: {str(e)}")

def update_in_supabase(table, id, data):
    """Update data in Supabase table"""
    try:
        client = get_supabase_client()
        result = client.table(table).update(data).eq('id', id).execute()
        return result.data
    except Exception as e:
        raise Exception(f"Supabase update failed: {str(e)}")

def query_supabase(table, filters=None, limit=None):
    """Query data from Supabase table"""
    try:
        client = get_supabase_client()
        query = client.table(table).select('*')
        
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data
    except Exception as e:
        raise Exception(f"Supabase query failed: {str(e)}")

def save_results(results, source_file=None):
    """
    Save processing results to Supabase.
    
    Args:
        results: List of result dictionaries from model processing
        source_file: Original source filename (optional)
    
    Returns:
        Dictionary with save statistics
    """
    import logging
    from datetime import datetime
    
    if not results:
        logging.warning("No results to save to Supabase")
        return {"saved": 0, "errors": 0}
    
    saved_count = 0
    error_count = 0
    
    try:
        client = get_supabase_client()
        
        # Prepare records for insertion
        records = []
        for result in results:
            if result.get('status') == 'failed' or 'error' in result:
                error_count += 1
                continue
            
            # Extract vulnerabilities and OFCs from result
            vulnerabilities = result.get('vulnerabilities', [])
            ofcs = result.get('ofcs', [])
            
            # Create submission record if we have data
            if vulnerabilities or ofcs:
                record = {
                    'data': {
                        'vulnerabilities': vulnerabilities,
                        'ofcs': ofcs,
                        'chunk_id': result.get('chunk_id'),
                        'source_file': result.get('source_file', source_file),
                        'page_range': result.get('page_range'),
                        'processed_at': datetime.now().isoformat(),
                        'model_response': result
                    },
                    'status': 'pending',  # Will be reviewed by admin
                    'created_at': datetime.now().isoformat()
                }
                
                # Add submitter_email if available from environment
                submitter_email = os.getenv('SUBMITTER_EMAIL')
                if submitter_email:
                    record['submitter_email'] = submitter_email
                
                records.append(record)
        
        # Batch insert records
        if records:
            try:
                # Insert into submissions table
                response = client.table('submissions').insert(records).execute()
                saved_count = len(response.data) if response.data else len(records)
                logging.info(f"Saved {saved_count} records to Supabase submissions table")
            except Exception as e:
                logging.error(f"Failed to insert records to Supabase: {str(e)}")
                error_count += len(records)
        
        return {
            "saved": saved_count,
            "errors": error_count,
            "total": len(results)
        }
        
    except Exception as e:
        logging.error(f"Failed to save results to Supabase: {str(e)}")
        raise Exception(f"Supabase save failed: {str(e)}")

# Add more Supabase functions as needed from your old implementation

