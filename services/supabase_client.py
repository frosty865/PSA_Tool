"""
Supabase client service
Handles all Supabase database operations
"""

import os
import requests
from datetime import datetime

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

def get_discipline_record(name=None, all=False):
    """
    Get discipline record(s) from Supabase.
    
    Args:
        name: Discipline name to search for (case-insensitive)
        all: If True, return all active disciplines
    
    Returns:
        Single discipline record dict, list of records, or None
    """
    try:
        client = get_supabase_client()
        
        if all:
            # Get all active disciplines
            result = client.table("disciplines").select("id, name, category, is_active").eq("is_active", True).execute()
            return result.data if result.data else []
        
        if not name:
            return None
        
        # Search for discipline by name (case-insensitive)
        result = client.table("disciplines").select("id, name, category, is_active").ilike("name", name).eq("is_active", True).maybe_single().execute()
        return result.data if result.data else None
        
    except Exception as e:
        logging.error(f"Failed to get discipline record: {str(e)}")
        return None if not all else []


def get_sector_id(name):
    """
    Get sector ID by name from Supabase.
    
    Args:
        name: Sector name to search for (case-insensitive)
    
    Returns:
        Sector ID (UUID) or None if not found
    """
    if not name:
        return None
    
    try:
        client = get_supabase_client()
        
        # Try sector_name first, then name field
        result = client.table("sectors").select("id").ilike("sector_name", name).maybe_single().execute()
        if result.data:
            return result.data.get('id')
        
        # Fallback to name field
        result = client.table("sectors").select("id").ilike("name", name).maybe_single().execute()
        if result.data:
            return result.data.get('id')
        
        logging.warning(f"Sector not found: {name}")
        return None
        
    except Exception as e:
        logging.error(f"Failed to get sector ID: {str(e)}")
        return None


def get_subsector_id(name):
    """
    Get subsector ID by name from Supabase.
    
    Args:
        name: Subsector name to search for (case-insensitive)
    
    Returns:
        Subsector ID (UUID) or None if not found
    """
    if not name:
        return None
    
    try:
        client = get_supabase_client()
        result = client.table("subsectors").select("id").ilike("name", name).maybe_single().execute()
        
        if result.data:
            return result.data.get('id')
        
        logging.warning(f"Subsector not found: {name}")
        return None
        
    except Exception as e:
        logging.error(f"Failed to get subsector ID: {str(e)}")
        return None


def save_results(results, source_file=None):
    """
    Save post-processed results to Supabase submissions table.
    
    Args:
        results: List of post-processed result dictionaries with taxonomy IDs
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
            
            # Post-processed results have structured format
            vulnerability = result.get('vulnerability', '')
            ofcs = result.get('options_for_consideration', [])
            
            if not vulnerability or not ofcs:
                error_count += 1
                continue
            
            # Create submission record
            record = {
                'data': {
                    'vulnerability': vulnerability,
                    'options_for_consideration': ofcs,
                    'discipline_id': result.get('discipline_id'),
                    'category': result.get('category'),
                    'sector_id': result.get('sector_id'),
                    'subsector_id': result.get('subsector_id'),
                    'source': result.get('source'),
                    'page_ref': result.get('page_ref'),
                    'chunk_id': result.get('chunk_id'),
                    'source_file': result.get('source_file', source_file),
                    'processed_at': datetime.now().isoformat(),
                    'recommendations': result.get('recommendations')
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
                logging.info(f"Saved {saved_count} post-processed records to Supabase submissions table")
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

def get_learning_events(since):
    """
    Return all learning events created since a given timestamp.
    
    Args:
        since: datetime object - events created after this time
    
    Returns:
        List of learning event dictionaries
    """
    try:
        client = get_supabase_client()
        
        # Convert datetime to ISO format string
        since_iso = since.isoformat() if isinstance(since, datetime) else since
        
        # Query learning_events table
        result = client.table("learning_events").select("*").gte("created_at", since_iso).order("created_at", desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        logging.error(f"Failed to get learning events: {str(e)}")
        return []


def insert_learning_event(event_data):
    """
    Insert a learning feedback event into Supabase.
    
    Args:
        event_data: Dictionary with event fields:
            - submission_id (optional): UUID of submission
            - event_type: 'approval', 'rejection', 'correction', 'edited'
            - approved: boolean
            - model_version: string (e.g., 'psa-engine:latest')
            - confidence_score: decimal (0.0-1.0)
            - metadata: JSON object (optional)
    
    Returns:
        Inserted event data or None on error
    """
    try:
        client = get_supabase_client()
        
        # Ensure created_at is set
        if 'created_at' not in event_data:
            event_data['created_at'] = datetime.utcnow().isoformat()
        
        # Insert event
        result = client.table("learning_events").insert(event_data).execute()
        
        if result.data:
            logging.info(f"Learning event recorded: {event_data.get('event_type')}")
            return result.data[0]
        
        return None
        
    except Exception as e:
        logging.error(f"Failed to insert learning event: {str(e)}")
        raise Exception(f"Failed to insert learning event: {str(e)}")


def insert_learning_stats(stats):
    """
    Insert or update learning statistics.
    
    Note: This assumes a 'learning_stats' table exists. If it doesn't,
    this function will fail gracefully (logged as warning).
    
    Args:
        stats: Dictionary with learning statistics
    
    Returns:
        Inserted stats data or None on error
    """
    try:
        client = get_supabase_client()
        
        # Try to insert into learning_stats table
        # If table doesn't exist, this will fail gracefully
        result = client.table("learning_stats").insert(stats).execute()
        
        if result.data:
            logging.info(f"Learning stats recorded: {stats.get('total_events')} events")
            return result.data[0]
        
        return None
        
    except Exception as e:
        # Log as warning since learning_stats table may not exist
        logging.warning(f"Could not insert learning stats (table may not exist): {str(e)}")
        return None


def get_recent_learning_stats(limit=5):
    """
    Get recent learning statistics from Supabase.
    
    Args:
        limit: Number of recent stats to retrieve (default: 5)
    
    Returns:
        List of learning stats dictionaries, ordered by timestamp (most recent first)
    """
    try:
        client = get_supabase_client()
        
        # Query learning_stats table, ordered by timestamp descending
        result = client.table("learning_stats").select("timestamp, accept_rate, total_events, accepted, rejected, edited").order("timestamp", desc=True).limit(limit).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        logging.warning(f"Could not get recent learning stats (table may not exist): {str(e)}")
        return []


def record_retrain_event(avg_accept_rate, stats_window_size):
    """
    Record a model retraining event in Supabase.
    
    Tries to insert into system_events table if it exists.
    Falls back to logging if table doesn't exist.
    
    Args:
        avg_accept_rate: Average accept rate that triggered retraining
        stats_window_size: Number of stats cycles used in evaluation
    
    Returns:
        Inserted event data or None on error
    """
    try:
        client = get_supabase_client()
        
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "model_retrain",
            "notes": f"Triggered automatic retrain. Avg accept rate: {avg_accept_rate:.3f} (threshold: 0.6). Stats window: {stats_window_size} cycles",
            "metadata": {
                "avg_accept_rate": avg_accept_rate,
                "threshold": 0.6,
                "stats_window_size": stats_window_size,
                "triggered_at": datetime.utcnow().isoformat()
            }
        }
        
        # Try to insert into system_events table
        # If table doesn't exist, this will fail gracefully
        try:
            result = client.table("system_events").insert(payload).execute()
            if result.data:
                logging.info(f"Retrain event recorded in system_events: {payload.get('notes')}")
                return result.data[0]
        except Exception as table_error:
            # Table may not exist - log to learning_events as fallback
            logging.warning(f"system_events table not available, logging to learning_events: {table_error}")
            try:
                # Fallback: log as a learning event
                fallback_payload = {
                    "event_type": "model_retrain",
                    "approved": False,  # Retraining is not an approval
                    "model_version": "psa-engine:latest",
                    "metadata": payload.get("metadata", {}),
                    "created_at": payload["timestamp"]
                }
                result = client.table("learning_events").insert(fallback_payload).execute()
                if result.data:
                    logging.info(f"Retrain event recorded in learning_events (fallback)")
                    return result.data[0]
            except Exception as fallback_error:
                logging.error(f"Failed to record retrain event in fallback table: {fallback_error}")
        
        return None
        
    except Exception as e:
        logging.error(f"Failed to record retrain event: {str(e)}")
        # Don't raise - retraining should continue even if logging fails
        return None

