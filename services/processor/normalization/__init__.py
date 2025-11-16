"""Normalization Module

⚠️ DEPRECATION NOTICE:
- discipline_resolver (v1) → Use DisciplineResolverV2
- taxonomy_inference.infer_sector_subsector (v1) → Use DocumentClassifier/SubsectorResolverV2
- vofc_discipline.DisciplineResolver (v1) → Use DisciplineResolverV2

All v1 modules are deprecated but remain functional for backwards compatibility.
"""
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
from .vofc_discipline import DisciplineResolver
from .discipline_resolver_v2 import DisciplineResolverV2, create_resolver_from_supabase
from .subsector_resolver_v2 import SubsectorResolverV2
from .document_classifier import DocumentClassifier, extract_document_context
from .classifier_context import get_classifier, reset_classifier
from .citation_extractor import CitationExtractor, Citation
from .citation_extractor_v2 import CitationExtractorV2 as CitationExtractorV2
from .pdf_structure import build_document_structure, find_section_for_page, SectionNode
# taxonomy_resolver is deprecated - use DocumentClassifier instead

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
    'DisciplineResolver',
    'DisciplineResolverV2',
    'create_resolver_from_supabase',
    'SubsectorResolverV2',
    'DocumentClassifier',
    'extract_document_context',
    'get_classifier',
    'reset_classifier',
    'CitationExtractor',
    'Citation',
    'CitationExtractorV2',
    'build_document_structure',
    'find_section_for_page',
    'SectionNode'
]

