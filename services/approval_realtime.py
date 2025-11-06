"""
Realtime Approval Sync

Listens for approved submissions via Supabase Realtime and updates learning_events instantly.
"""

import os
import threading
from datetime import datetime

try:
    from supabase import create_client, Client
    from gotrue import errors as gotrue_errors
except ImportError:
    raise ImportError("supabase-py package not installed. Install with: pip install supabase")

SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").rstrip('/')
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def handle_approval(payload):
    """Triggered whenever a submission is approved in Supabase."""
    try:
        new_record = payload.get("new", {})
        old_record = payload.get("old", {})
        if not new_record or new_record.get("status") != "approved":
            return

        submission_id = new_record["id"]

        # Check if there's already a learning_event
        res = supabase.table("learning_events").select("*").eq("submission_id", submission_id).execute()
        existing = res.data[0] if res.data else None

        if existing:
            supabase.table("learning_events").update({
                "approved": True,
                "event_type": "approval",
                "metadata": {"reviewed_at": datetime.utcnow().isoformat()},
                "updated_at": datetime.utcnow().isoformat()
            }).eq("submission_id", submission_id).execute()
            print(f"[RealtimeApproval] Updated learning_event for {submission_id}")
        else:
            supabase.table("learning_events").insert({
                "submission_id": submission_id,
                "event_type": "approval",
                "approved": True,
                "model_version": "psa-engine:latest",
                "confidence_score": None,
                "metadata": {"reviewed_at": datetime.utcnow().isoformat(), "auto_generated": True},
                "created_at": datetime.utcnow().isoformat()
            }).execute()
            print(f"[RealtimeApproval] Created learning_event for {submission_id}")

    except Exception as e:
        print(f"[RealtimeApproval] Error processing approval event: {e}")


def start_realtime_approval_listener():
    """Start Supabase realtime subscription for submission approvals."""
    def listen():
        try:
            channel = (
                supabase
                .channel("psa-approvals")
                .on(
                    "postgres_changes",
                    {
                        "event": "UPDATE",
                        "schema": "public",
                        "table": "submissions"
                    },
                    handle_approval
                )
                .subscribe()
            )
            print("[RealtimeApproval] Listening for submission approvals...")
            # Keep thread alive
            while True:
                pass
        except gotrue_errors.AuthApiError as e:
            print(f"[RealtimeApproval] Auth error: {e}")
        except Exception as e:
            print(f"[RealtimeApproval] Listener error: {e}")

    t = threading.Thread(target=listen, name="RealtimeApprovalListener", daemon=True)
    t.start()
    print("[RealtimeApproval] Realtime approval listener started")

