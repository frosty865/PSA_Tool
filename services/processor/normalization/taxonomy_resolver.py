"""
Canonical Taxonomy Resolver (DEPRECATED - Use DocumentClassifier)

⚠️ DEPRECATED: This module is deprecated. Use DocumentClassifier for sector/subsector resolution.
Discipline resolution is handled by DisciplineResolverV2.

This module is kept for backwards compatibility but should not be used for new code.
"""
import warnings

warnings.warn(
    "taxonomy_resolver module is deprecated. Use DocumentClassifier for sector/subsector resolution.",
    DeprecationWarning,
    stacklevel=2
)

# All .ilike queries removed - use DocumentClassifier instead
# This file is kept for backwards compatibility only
