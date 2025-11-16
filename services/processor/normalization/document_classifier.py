"""
document_classifier.py

High-level document classifier integrating SubsectorResolverV2.

This module takes in extracted text from PDF ingestion:
  - title
  - metadata
  - first pages
  - heuristics from filenames, folder paths
  - optional user-selected facility type overrides

Outputs:
  - sector_id
  - sector_name
  - subsector_id
  - subsector_name
  - confidence

This is the ONLY place the pipeline determines sectors/subsectors.
All vulnerabilities inherit this automatically.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .subsector_resolver_v2 import SubsectorResolverV2

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------------
# HELPER: extract useful document-level context
# -----------------------------------------------------------------------------------

def extract_document_context(
    title: str,
    metadata: Dict[str, Any] | None,
    first_pages_text: str,
    full_text: str | None = None,
    max_chars: int = 5000
) -> str:
    """
    Build a document-level context string used for subsector resolution.
    Weighted toward early pages + title + metadata.

    Parameters:
      title (str)              - extracted document title
      metadata (dict | None)  - PDF metadata (author, subject, etc.)
      first_pages_text (str)  - text from first 1–3 pages
      full_text (str | None)  - optional full text for semantic scoring
      max_chars (int)         - safety truncation for full_text

    Returns:
      str - combined context
    """
    parts = []

    # Title is highly informative
    if title:
        parts.append(title)

    # Metadata fields (if any)
    if metadata:
        for key in ("Subject", "Keywords", "Description", "Creator"):
            val = metadata.get(key)
            if val:
                parts.append(str(val))

    # First 2–3 pages contain most facility identifiers
    if first_pages_text:
        parts.append(first_pages_text)

    # Small slice of full doc for semantic cues
    if full_text:
        trimmed = full_text[:max_chars]
        parts.append(trimmed)

    ctx = "\n".join([p.strip() for p in parts if p and p.strip()])
    return ctx


# -----------------------------------------------------------------------------------
# MAIN CLASSIFIER
# -----------------------------------------------------------------------------------

class DocumentClassifier:
    """
    Wrapper around SubsectorResolverV2 providing:
      - context building
      - sector/subsector inference
      - clean return payload
      - optional override (user-specified facility type)
    """

    def __init__(
        self,
        subsector_vocab_path: Optional[str | Path] = None,
        enable_semantic: bool = True,
    ) -> None:
        """
        Initialize document classifier.
        
        Args:
            subsector_vocab_path: Path to subsector_vocabulary.json
                                  If None, uses default location
            enable_semantic: Whether to enable semantic similarity scoring
        """
        # Default vocab path: same directory as this module
        if subsector_vocab_path is None:
            module_dir = Path(__file__).parent
            subsector_vocab_path = module_dir / "subsector_vocabulary.json"
        
        self.resolver = SubsectorResolverV2(
            vocab_source=subsector_vocab_path,
            enable_semantic=enable_semantic
        )

        # Optional manual override
        self.override_subsector: Optional[str] = None
        self.override_sector: Optional[str] = None
        
        # Citation extractor (initialized separately when page data is available)
        self.citation_extractor: Optional[Any] = None

    # -------------------------------------------------------------------
    # Public method
    # -------------------------------------------------------------------

    def classify(
        self,
        title: str,
        metadata: Dict[str, Any] | None = None,
        first_pages_text: str = "",
        full_text: str | None = None,
        known_sector_id: str | None = None,
        return_debug: bool = False,
    ) -> Dict[str, Any]:
        """
        Classify a document into subsector + sector.

        Returns:
          {
            "sector_id": str | None,
            "subsector_id": str | None,
            "subsector_name": str | None,
            "confidence": float,
            "source": "auto" | "override" | "metadata",
            "debug": { ... }  # if return_debug=True
          }
        """
        # ---------------------------------------------------------------
        # OVERRIDE HANDLING
        # ---------------------------------------------------------------
        if self.override_subsector:
            return {
                "sector_id": self.override_sector,
                "subsector_id": self.override_subsector,
                "subsector_name": "OVERRIDE",
                "confidence": 1.0,
                "source": "override",
            }

        # ---------------------------------------------------------------
        # Build context
        # ---------------------------------------------------------------
        context = extract_document_context(
            title=title,
            metadata=metadata,
            first_pages_text=first_pages_text,
            full_text=full_text,
        )

        # ---------------------------------------------------------------
        # Run resolver
        # ---------------------------------------------------------------
        result = self.resolver.resolve_document(
            text=context,
            known_sector_id=known_sector_id,  # boosts same-sector subsectors
            top_k=5,
            return_debug=return_debug
        )

        subsector_id = result.get("subsector_id")
        sector_id = result.get("sector_id")

        # ---------------------------------------------------------------
        # Final response
        # ---------------------------------------------------------------
        output = {
            "sector_id": sector_id,
            "subsector_id": subsector_id,
            "subsector_name": result.get("subsector_name"),
            "confidence": result.get("confidence", 0.0),
            "source": "auto",
        }

        if return_debug:
            output["debug"] = result

        return output

    # -------------------------------------------------------------------
    # Optional methods to force a facility type (e.g., user selection)
    # -------------------------------------------------------------------

    def set_override(self, subsector_id: str, sector_id: str):
        """Manually force subsector/sector (UI override)."""
        self.override_subsector = subsector_id
        self.override_sector = sector_id

    def clear_override(self):
        """Clear manual override."""
        self.override_subsector = None
        self.override_sector = None

