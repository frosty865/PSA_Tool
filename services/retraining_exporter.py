"""
Retraining Exporter

Exports approved learning events into a JSONL file for model fine-tuning.
"""

import os
import json
from datetime import datetime

try:
    from supabase import create_client, Client
except ImportError:
    raise ImportError("supabase-py package not installed. Install with: pip install supabase")

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

EXPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "exports")


def export_approved_events(limit: int = 1000):
    """
    Export approved learning events to a JSONL file.
    
    Args:
        limit: Maximum number of events to export (default: 1000)
    
    Returns:
        str: Path to the exported JSONL file
    """
    os.makedirs(EXPORT_PATH, exist_ok=True)
    
    supabase = get_supabase_client()
    res = supabase.table("learning_events").select("*").eq("approved", True).limit(limit).execute()
    data = res.data or []
    
    filename = f"psa_training_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"
    out_path = os.path.join(EXPORT_PATH, filename)
    
    with open(out_path, "w", encoding="utf-8") as f:
        for row in data:
            f.write(json.dumps(row, default=str) + "\n")
    
    print(f"[RetrainingExporter] Exported {len(data)} approved events → {out_path}")
    return out_path

