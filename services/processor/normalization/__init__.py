"""Normalization Module"""
from .merge import merge_all
from .dedupe import dedupe_records, dedupe_key
from .classify import normalize_records, normalize_record, normalize_confidence, normalize_impact_level
from .supabase_upload import upload_to_supabase, init_supabase, check_existing_vulnerability

__all__ = [
    'merge_all',
    'dedupe_records',
    'dedupe_key',
    'normalize_records',
    'normalize_record',
    'normalize_confidence',
    'normalize_impact_level',
    'upload_to_supabase',
    'init_supabase',
    'check_existing_vulnerability'
]

