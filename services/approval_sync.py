"""
Auto-Approval Hook

Synchronizes approved submissions with their learning_events
"""

import os
import time
import threading
from datetime import datetime, timedelta

try:
    from supabase import create_client, Client
except ImportError:
    raise ImportError("supabase-py package not installed. Install with: pip install supabase")

# Get Supabase credentials from environment
from config import Config

# Supabase client - lazy loaded (only when needed)
# Don't initialize at module level to avoid startup errors if Supabase is not configured
_supabase_client: Client = None

def get_supabase_client() -> Client:
    """Get Supabase client, creating it if needed."""
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    SUPABASE_URL = Config.SUPABASE_URL or ""
    SUPABASE_SERVICE_ROLE_KEY = Config.SUPABASE_SERVICE_ROLE_KEY
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")
    
    _supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_client


def sync_approvals_once():
    """Check for approved submissions and update learning_events."""
    try:
        # Get submissions with status 'approved' updated in the last 24 hours
        # Calculate time 24 hours ago
        cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        supabase = get_supabase_client()
        res = supabase.table("submissions") \
            .select("id, status, updated_at, reviewed_at") \
            .eq("status", "approved") \
            .gte("updated_at", cutoff_time) \
            .execute()
        
        if not res.data:
            return
        
        for sub in res.data:
            submission_id = sub["id"]
            
            # Check if learning_event exists for this submission
            check = supabase.table("learning_events") \
                .select("id, event_type, approved, metadata") \
                .eq("submission_id", submission_id) \
                .execute()
            
            if check.data:
                # Learning event exists - update it if not already approved
                event = check.data[0]
                if event.get("approved") is True and event.get("event_type") == "approval":
                    continue  # already updated
                
                # Build update payload
                update_payload = {
                    "approved": True,
                    "event_type": "approval",
                }
                
                # Preserve existing metadata if it exists
                existing_metadata = event.get("metadata")
                if isinstance(existing_metadata, dict):
                    existing_metadata["reviewed_at"] = sub.get("reviewed_at") or datetime.utcnow().isoformat()
                    existing_metadata["auto_approved"] = True
                    update_payload["metadata"] = existing_metadata
                else:
                    update_payload["metadata"] = {
                        "reviewed_at": sub.get("reviewed_at") or datetime.utcnow().isoformat(),
                        "auto_approved": True
                    }
                
                supabase.table("learning_events") \
                    .update(update_payload) \
                    .eq("submission_id", submission_id) \
                    .execute()
                
                print(f"[ApprovalSync] ✅ Updated learning_event for submission {submission_id}")
            else:
                # If no learning_event exists, create one
                create_payload = {
                    "submission_id": submission_id,
                    "event_type": "approval",
                    "approved": True,
                    "model_version": "psa-engine:latest",
                    "confidence_score": None,
                    "metadata": {
                        "auto_generated": True,
                        "reviewed_at": sub.get("reviewed_at") or datetime.utcnow().isoformat()
                    },
                    "created_at": datetime.utcnow().isoformat()
                }
                
                supabase.table("learning_events") \
                    .insert(create_payload) \
                    .execute()
                
                print(f"[ApprovalSync] ✅ Created approval learning_event for submission {submission_id}")
    
    except Exception as e:
        print(f"[ApprovalSync] ⚠️  Error syncing approvals: {e}")


def start_approval_monitor(interval_minutes: int = 5):
    """
    Background thread that periodically checks for approvals.
    
    Args:
        interval_minutes: How often to check for approvals (default: 5 minutes)
    """
    def loop():
        while True:
            try:
                sync_approvals_once()
            except Exception as e:
                print(f"[ApprovalSync] ⚠️  Error in approval monitor loop: {e}")
            finally:
                time.sleep(interval_minutes * 60)
    
    t = threading.Thread(target=loop, name="ApprovalMonitor", daemon=True)
    t.start()
    print(f"[ApprovalSync] ✅ Background approval monitor started (checking every {interval_minutes} minutes)")

