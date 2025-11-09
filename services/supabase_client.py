"""
Supabase client service
Handles all Supabase database operations
"""

import os
import logging
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
# Note: These are read at module import, but get_supabase_client() will re-read them dynamically
SUPABASE_URL = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL', '').rstrip('/')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')

supabase: Client = None

def get_supabase_client():
    """Get or create Supabase client"""
    global supabase
    # Re-read environment variables each time to handle dynamic changes
    supabase_url = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL', '').rstrip('/')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        raise Exception("Supabase credentials not configured")
    
    # Recreate client if credentials changed or client doesn't exist
    if supabase is None or supabase_url != SUPABASE_URL or supabase_key != SUPABASE_KEY:
        supabase = create_client(supabase_url, supabase_key)
    
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

def get_discipline_record(name=None, all=False, fuzzy=False):
    """
    Get discipline record(s) from Supabase.
    
    Args:
        name: Discipline name to search for (case-insensitive)
        all: If True, return all active disciplines
        fuzzy: If True, use first word only for matching (more flexible)
    
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
        
        # Try exact match first (case-insensitive)
        try:
            result = client.table("disciplines").select("id, name, category, is_active").ilike("name", name).eq("is_active", True).maybe_single().execute()
            if result.data:
                return result.data
        except Exception:
            pass
        
        # Try contains match (full name) - PostgREST uses * for wildcards
        try:
            pattern = f"*{name}*"
            result = client.table("disciplines").select("id, name, category, is_active").ilike("name", pattern).eq("is_active", True).maybe_single().execute()
            if result.data:
                return result.data
        except Exception:
            pass
        
        # If fuzzy=True, try first word only
        if fuzzy and name:
            first_word = name.split()[0] if name.split() else name
            try:
                pattern = f"*{first_word}*"
                result = client.table("disciplines").select("id, name, category, is_active").ilike("name", pattern).eq("is_active", True).maybe_single().execute()
                if result.data:
                    return result.data
            except Exception:
                pass
        
        # Last resort: get all and find best match
        try:
            all_discs = client.table("disciplines").select("id, name, category, is_active").eq("is_active", True).execute()
            if all_discs.data:
                name_lower = name.lower()
                for disc in all_discs.data:
                    disc_name = disc.get("name", "").lower()
                    # Check if name is contained in discipline name or vice versa
                    if name_lower in disc_name or disc_name in name_lower:
                        return disc
        except Exception:
            pass
        
        return None
        
    except Exception as e:
        logging.error(f"Failed to get discipline record: {str(e)}")
        return None if not all else []


def get_sector_id(name, fuzzy=False):
    """
    Get sector ID by name from Supabase.
    
    Args:
        name: Sector name to search for (case-insensitive)
        fuzzy: If True, use first word only for matching (more flexible)
    
    Returns:
        Sector ID (UUID) or None if not found
    """
    if not name:
        return None
    
    try:
        client = get_supabase_client()
        
        # Try exact match first (case-insensitive)
        try:
            result = client.table("sectors").select("id").ilike("sector_name", name).maybe_single().execute()
            if result.data:
                return result.data.get('id')
        except Exception:
            pass
        
        # Try contains match (full name) - PostgREST uses * for wildcards
        try:
            pattern = f"*{name}*"
            result = client.table("sectors").select("id").ilike("sector_name", pattern).maybe_single().execute()
            if result.data:
                return result.data.get('id')
        except Exception:
            pass
        
        # If fuzzy=True, try first word only
        if fuzzy and name:
            first_word = name.split()[0] if name.split() else name
            try:
                pattern = f"*{first_word}*"
                result = client.table("sectors").select("id").ilike("sector_name", pattern).maybe_single().execute()
                if result.data:
                    return result.data.get('id')
            except Exception:
                pass
        
        # Fallback to name field
        try:
            pattern = f"*{name}*"
            result = client.table("sectors").select("id").ilike("name", pattern).maybe_single().execute()
            if result.data:
                return result.data.get('id')
        except Exception:
            pass
        
        logging.warning(f"Sector not found: {name}")
        return None
        
    except Exception as e:
        logging.error(f"Failed to get sector ID: {str(e)}")
        return None


def get_subsector_id(name, fuzzy=False):
    """
    Get subsector ID by name from Supabase.
    
    Args:
        name: Subsector name to search for (case-insensitive)
        fuzzy: If True, use first word only for matching (more flexible)
    
    Returns:
        Subsector ID (UUID) or None if not found
    """
    if not name:
        return None
    
    try:
        client = get_supabase_client()
        
        # Try exact match first (case-insensitive)
        try:
            result = client.table("subsectors").select("id").ilike("name", name).maybe_single().execute()
            if result.data:
                return result.data.get('id')
        except Exception:
            pass
        
        # Try contains match (full name) - PostgREST uses * for wildcards
        try:
            pattern = f"*{name}*"
            result = client.table("subsectors").select("id").ilike("name", pattern).maybe_single().execute()
            if result.data:
                return result.data.get('id')
        except Exception:
            pass
        
        # If fuzzy=True, try first word only
        if fuzzy and name:
            first_word = name.split()[0] if name.split() else name
            try:
                pattern = f"*{first_word}*"
                result = client.table("subsectors").select("id").ilike("name", pattern).maybe_single().execute()
                if result.data:
                    return result.data.get('id')
            except Exception:
                pass
        
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


def insert_library_record(data):
    """
    Insert processed results into Supabase production tables (vulnerabilities and OFCs).
    
    This function is used to sync approved review files to production tables.
    
    Args:
        data: Dictionary with 'vulnerabilities' and 'options_for_consideration' arrays
        
    Returns:
        Dictionary with counts of inserted records
    """
    try:
        client = get_supabase_client()
        
        vulnerabilities = data.get('vulnerabilities', [])
        ofcs = data.get('options_for_consideration', [])
        
        inserted_vulns = []
        inserted_ofcs = []
        
        # Insert vulnerabilities
        if vulnerabilities:
            vuln_records = []
            for v in vulnerabilities:
                if not v.get('vulnerability') and not v.get('vulnerability_name'):
                    continue
                
                vuln_record = {
                    'vulnerability_name': v.get('vulnerability') or v.get('vulnerability_name', ''),
                    'description': v.get('description', ''),
                    'discipline': v.get('discipline') or None,
                    'sector_id': v.get('sector_id'),
                    'subsector_id': v.get('subsector_id'),
                    'source': data.get('source_file', 'unknown'),
                    'page_ref': v.get('page_ref', 'N/A')
                }
                vuln_records.append(vuln_record)
            
            if vuln_records:
                result = client.table('vulnerabilities').insert(vuln_records).execute()
                inserted_vulns = result.data if result.data else []
                logger.info(f"Inserted {len(inserted_vulns)} vulnerabilities into production table")
        
        # Insert OFCs
        if ofcs:
            ofc_records = []
            for o in ofcs:
                if not o.get('option_text'):
                    continue
                
                ofc_record = {
                    'option_text': o.get('option_text', ''),
                    'discipline': o.get('discipline') or None,
                    'sector_id': o.get('sector_id'),
                    'subsector_id': o.get('subsector_id')
                }
                ofc_records.append(ofc_record)
            
            if ofc_records:
                result = client.table('options_for_consideration').insert(ofc_records).execute()
                inserted_ofcs = result.data if result.data else []
                logger.info(f"Inserted {len(inserted_ofcs)} OFCs into production table")
        
        return {
            'vulnerabilities_inserted': len(inserted_vulns),
            'ofcs_inserted': len(inserted_ofcs),
            'success': len(inserted_vulns) > 0 or len(inserted_ofcs) > 0
        }
        
    except Exception as e:
        logger.error(f"Error inserting library record: {str(e)}")
        raise Exception(f"Failed to insert library record: {str(e)}")


def check_review_approval(filename):
    """
    Check if a review file has been approved in Supabase.
    
    Checks the submissions table for records matching the filename
    that have status 'approved'.
    
    Args:
        filename: Name of the review file (without extension, may include _vofc suffix)
        
    Returns:
        True if approved, False otherwise
    """
    try:
        client = get_supabase_client()
        
        # Clean filename for matching (remove _vofc suffix if present)
        clean_filename = filename.replace('_vofc', '')
        
        # Check submissions table for approved status
        # Match by source_file in data JSONB column
        # Query recent submissions and filter in Python (more reliable than JSONB queries)
        import json
        all_results = client.table('submissions').select('id, status, data').order('created_at', desc=True).limit(100).execute()
        
        result_data = []
        if all_results.data:
            for sub in all_results.data:
                sub_data = sub.get('data', {})
                if isinstance(sub_data, str):
                    try:
                        sub_data = json.loads(sub_data)
                    except:
                        continue
                source_file = sub_data.get('source_file', '')
                document_name = sub_data.get('document_name', '')
                if clean_filename.lower() in str(source_file).lower() or clean_filename.lower() in str(document_name).lower():
                    result_data = [sub]
                    break
        
        result = type('obj', (object,), {'data': result_data})()
        
        if result.data and len(result.data) > 0:
            submission = result.data[0]
            status = submission.get('status', '').lower()
            is_approved = status == 'approved'
            
            if is_approved:
                logger.info(f"Review file {filename} is approved (submission ID: {submission.get('id')})")
            
            return is_approved
        
        # No matching submission found
        logger.debug(f"No submission found for review file: {filename}")
        return False
        
    except Exception as e:
        logger.warning(f"Error checking review approval for {filename}: {str(e)}")
        return False


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

