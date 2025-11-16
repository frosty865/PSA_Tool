"""
citation_extractor.py

Extracts structured citation metadata for OFCs and Vulnerabilities:
 - Page reference
 - Section / header name
 - Clean excerpt text (minimal window)
 - Confidence rating

Integrates with VOFC Engine:
 - Uses chunk → page map
 - Section headers identified by heuristics
 - Optional semantic header matching
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Any


# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

HEADER_PATTERN = re.compile(
    r"""(?mx)
    ^[A-Z][A-Z0-9\s\-/]{4,}$         # ALL CAPS HEADERS
    | ^\d+(?:\.\d+)*\s+.+$           # Numbered headers: 1.2, 3.4.6 Overview
    """
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


# -----------------------------------------------------------------------------
# DATA STRUCTURE
# -----------------------------------------------------------------------------

@dataclass
class Citation:
    page_ref: Optional[int]
    section: Optional[str]
    excerpt: Optional[str]
    confidence: float
    source_file: Optional[str]

    def to_dict(self):
        return {
            "page_ref": self.page_ref,
            "section": self.section,
            "excerpt": self.excerpt,
            "confidence": self.confidence,
            "source_file": self.source_file
        }


# -----------------------------------------------------------------------------
# CLASSIFIER
# -----------------------------------------------------------------------------

class CitationExtractor:
    def __init__(
        self,
        page_map: Dict[int, int],
        page_text: Dict[int, str],
        file_name: str,
        sentence_window: int = 1
    ):
        """
        page_map:   chunk_index → page_number
        page_text:  page_number → raw extracted page text
        file_name:  document source file
        """
        self.page_map = page_map
        self.page_text = page_text
        self.file_name = file_name
        self.sentence_window = sentence_window

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def extract(
        self,
        chunk_index: int,
        chunk_text: str,
        ofc_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract citation details for the chunk (and optionally the OFC text).

        ofc_text:
            If provided, we try to anchor the excerpt around the OFC-specific phrase.
        """

        page_ref = self.page_map.get(chunk_index)
        page_raw = self.page_text.get(page_ref, "")

        section = self._find_section_header(page_raw)
        excerpt = self._extract_excerpt(page_raw, ofc_text or chunk_text)
        confidence = self._estimate_confidence(section, excerpt)

        citation = Citation(
            page_ref=page_ref,
            section=section,
            excerpt=excerpt,
            confidence=confidence,
            source_file=self.file_name
        )
        return citation.to_dict()

    # -------------------------------------------------------------------------
    # PRIVATE LOGIC
    # -------------------------------------------------------------------------

    def _find_section_header(self, page: str) -> Optional[str]:
        """
        Find the nearest meaningful section header above the OFC text.
        """
        if not page:
            return None

        lines = page.splitlines()
        candidates = []

        for line in lines:
            clean = line.strip()
            if HEADER_PATTERN.match(clean):
                candidates.append(clean)

        if not candidates:
            return None

        # Use the last header on the page → closest to the OFC location
        return candidates[-1]

    def _extract_excerpt(self, page: str, anchor_text: str) -> Optional[str]:
        """
        Extract a small window of sentences around the OFC-related anchor string.
        """
        if not page:
            return None

        sentences = SENTENCE_SPLIT.split(page)

        # Try exact match first
        idx = None
        for i, s in enumerate(sentences):
            if anchor_text.lower() in s.lower():
                idx = i
                break

        # Fallback: partial fuzzy match
        if idx is None:
            for i, s in enumerate(sentences):
                if any(tok in s.lower() for tok in anchor_text.lower().split()):
                    idx = i
                    break

        # No match found — return first 1–2 sentences as weak context
        if idx is None:
            return sentences[0].strip()[:500]

        start = max(0, idx - self.sentence_window)
        end = min(len(sentences), idx + self.sentence_window + 1)

        excerpt = " ".join(sentences[start:end]).strip()
        return excerpt[:500]  # safety trim

    def _estimate_confidence(self, section: Optional[str], excerpt: Optional[str]) -> float:
        """
        Basic confidence scoring:
         - Section header found → +0.3
         - Excerpt clean and >20 chars → +0.5
        """
        score = 0.0
        if section:
            score += 0.3
        if excerpt and len(excerpt) > 20:
            score += 0.5
        return min(score, 1.0)

