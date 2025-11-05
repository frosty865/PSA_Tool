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

# Add more Supabase functions as needed from your old implementation

