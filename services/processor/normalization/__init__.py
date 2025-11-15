"""Normalization Module"""
from .merge import merge_all
from .dedupe import dedupe_records, dedupe_key
from .classify import normalize_records, normalize_record, normalize_confidence, normalize_impact_level
from .supabase_upload import upload_to_supabase, init_supabase, check_existing_vulnerability
from .discipline_resolver import (
    normalize_discipline_name,
    infer_subtype,
    resolve_discipline_and_subtype,
    get_subtype_id
)
from .taxonomy_resolver import (
    normalize as normalize_taxonomy_text,
    resolve_from_discipline,
    resolve_from_subsector,
    resolve_sector,
    resolve_taxonomy
)

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
    'check_existing_vulnerability',
    'normalize_discipline_name',
    'infer_subtype',
    'resolve_discipline_and_subtype',
    'get_subtype_id',
    'normalize_taxonomy_text',
    'resolve_from_discipline',
    'resolve_from_subsector',
    'resolve_sector',
    'resolve_taxonomy'
]

