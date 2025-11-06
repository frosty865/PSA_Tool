"""
Analytics Collector

Aggregates metrics from learning_events for the PSA dashboard.
"""

import os
import json
import threading
import time
import statistics
from datetime import datetime

try:
    from supabase import create_client, Client
except ImportError:
    raise ImportError("supabase-py package not installed. Install with: pip install supabase")

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").rstrip('/')
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

ANALYTICS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "analytics.json")


def collect_metrics():
    try:
        res = supabase.table("learning_events").select("*").execute()
        data = res.data or []
        if not data:
            return

        confidences = [x["confidence_score"] for x in data if x.get("confidence_score") is not None]
        approvals = [x for x in data if x.get("approved")]

        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_events": len(data),
            "approved_events": len(approvals),
            "approval_rate": round(len(approvals) / len(data), 3) if data else 0,
            "avg_confidence": round(statistics.mean(confidences), 3) if confidences else None,
            "latest_model": max((x["model_version"] for x in data if x.get("model_version")), default=None)
        }

        os.makedirs(os.path.dirname(ANALYTICS_PATH), exist_ok=True)
        with open(ANALYTICS_PATH, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print(f"[AnalyticsCollector] Updated metrics: {metrics}")
    except Exception as e:
        print(f"[AnalyticsCollector] Error: {e}")


def start_collector(interval_minutes: int = 10):
    def loop():
        while True:
            collect_metrics()
            time.sleep(interval_minutes * 60)
    
    t = threading.Thread(target=loop, name="AnalyticsCollector", daemon=True)
    t.start()
    print("[AnalyticsCollector] Background metrics collector started")

