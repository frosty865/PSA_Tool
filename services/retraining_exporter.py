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
SUPABASE_URL = Config.SUPABASE_URL or ""
SUPABASE_SERVICE_ROLE_KEY = Config.SUPABASE_SERVICE_ROLE_KEY

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

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
    
    res = supabase.table("learning_events").select("*").eq("approved", True).limit(limit).execute()
    data = res.data or []
    
    filename = f"psa_training_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"
    out_path = os.path.join(EXPORT_PATH, filename)
    
    with open(out_path, "w", encoding="utf-8") as f:
        for row in data:
            f.write(json.dumps(row, default=str) + "\n")
    
    print(f"[RetrainingExporter] Exported {len(data)} approved events → {out_path}")
    return out_path

