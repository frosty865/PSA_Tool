"""
citation_extractor_v2.py

Upgraded citation extractor that:
 - Uses document structure (sections tree + page_index)
 - Anchors excerpts per OFC
 - Provides better confidence
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Any, List

from .pdf_structure import find_section_for_page


SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Citation:
    page_ref: Optional[int]
    section_id: Optional[str]
    section_title: Optional[str]
    excerpt: Optional[str]
    confidence: float
    source_file: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_ref": self.page_ref,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "excerpt": self.excerpt,
            "confidence": self.confidence,
            "source_file": self.source_file,
        }


class CitationExtractorV2:
    def __init__(
        self,
        page_map: Dict[int, int],          # chunk_index → page
        page_text: Dict[int, str],        # page → text
        structure: Dict[str, Any],        # from build_document_structure
        file_name: str,
        sentence_window: int = 1,
    ) -> None:
        self.page_map = page_map
        self.page_text = page_text
        self.structure = structure
        self.file_name = file_name
        self.sentence_window = sentence_window

    # ---------------------------------------------------------------------

    def extract(
        self,
        chunk_index: int,
        chunk_text: str,
        ofc_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        page_ref = self.page_map.get(chunk_index)
        page_raw = self.page_text.get(page_ref, "") if page_ref else ""

        section_node = find_section_for_page(self.structure, page_ref) if page_ref else None
        section_id = section_node["id"] if section_node else None
        section_title = section_node["title"] if section_node else None

        excerpt = self._extract_excerpt(page_raw, ofc_text or chunk_text)

        confidence = self._estimate_confidence(section_node, excerpt)

        c = Citation(
            page_ref=page_ref,
            section_id=section_id,
            section_title=section_title,
            excerpt=excerpt,
            confidence=confidence,
            source_file=self.file_name,
        )
        return c.to_dict()

    # ---------------------------------------------------------------------

    def _extract_excerpt(self, page: str, anchor_text: str) -> Optional[str]:
        if not page:
            return None

        sentences: List[str] = SENTENCE_SPLIT.split(page)
        anchor = (anchor_text or "").strip()
        if not anchor:
            return sentences[0].strip()[:500] if sentences else None

        # Exact substring match
        idx = None
        lower_anchor = anchor.lower()
        for i, s in enumerate(sentences):
            if lower_anchor in s.lower():
                idx = i
                break

        # Fuzzy fallback
        if idx is None:
            anchor_tokens = [t for t in lower_anchor.split() if len(t) > 3]
            for i, s in enumerate(sentences):
                sl = s.lower()
                if any(tok in sl for tok in anchor_tokens):
                    idx = i
                    break

        if idx is None:
            return sentences[0].strip()[:500] if sentences else None

        start = max(0, idx - self.sentence_window)
        end = min(len(sentences), idx + self.sentence_window + 1)
        excerpt = " ".join(sentences[start:end]).strip()
        return excerpt[:500]

    def _estimate_confidence(self, section_node: Optional[Dict[str, Any]], excerpt: Optional[str]) -> float:
        score = 0.0
        if section_node:
            score += 0.4
        if excerpt and len(excerpt) > 40:
            score += 0.4
        if excerpt and any(w in excerpt.lower() for w in ("shall", "should", "must", "recommend", "consider")):
            score += 0.2
        return min(score, 1.0)

