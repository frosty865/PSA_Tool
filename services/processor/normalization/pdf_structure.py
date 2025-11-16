"""
pdf_structure.py

PDF structural analysis for VOFC Engine:
 - Detects headings and subheadings
 - Builds a hierarchical section tree
 - Provides page → section lookup
 - Supports use by CitationExtractor, classifiers, auditors
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple


# -----------------------------------------------------------------------------
# Patterns
# -----------------------------------------------------------------------------

NUMERIC_HEADER_RE = re.compile(r"^\s*(\d+(?:\.\d+){0,3})\s+(.+?)\s*$")
ALL_CAPS_RE = re.compile(r"^[A-Z0-9\s\-/&]{4,}$")
SHORT_TRASH_RE = re.compile(r"^(table|figure|appendix)\b", re.I)


@dataclass
class SectionNode:
    id: str                      # e.g. "3.2.1" or "INTRO"
    title: str                   # cleaned heading text
    level: int                   # 1,2,3,...
    page_start: int              # first page where it appears
    page_end: int                # updated later
    parent_id: Optional[str]     # None for root-level
    children: List["SectionNode"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "level": self.level,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "parent_id": self.parent_id,
            "children": [c.to_dict() for c in self.children],
        }


# -----------------------------------------------------------------------------
# Heading detection
# -----------------------------------------------------------------------------

def _is_potential_header(line: str) -> bool:
    """Heuristic for whether a line looks like a structural heading."""
    s = line.strip()
    if not s:
        return False
    if SHORT_TRASH_RE.match(s):
        return False

    # Numeric headings: "3.2.1 Perimeter Security"
    if NUMERIC_HEADER_RE.match(s):
        return True

    # ALL CAPS sections: "PERIMETER SECURITY", "EMERGENCY RESPONSE PLAN"
    if ALL_CAPS_RE.match(s) and len(s.split()) <= 8:
        return True

    # Title-case with low punctuation: "Perimeter Security Measures"
    if s[0].isupper() and s.count(" ") <= 8 and ":" not in s:
        # crude heuristic: few words, mostly alphabetic
        alpha_ratio = sum(c.isalpha() for c in s) / max(len(s), 1)
        if alpha_ratio > 0.6:
            return True

    return False


def _extract_header_id_and_title(line: str, default_level: int = 2) -> Tuple[str, str, int]:
    """
    Compute a structural ID ("3.2", "INTRO", etc.) and a nesting level.
    """
    s = line.strip()
    m = NUMERIC_HEADER_RE.match(s)
    if m:
        num = m.group(1)
        title = m.group(2).strip()
        # Level = dot depth + 1 (1 -> L1, 1.1 -> L2, 1.1.1 -> L3)
        level = min(1 + num.count("."), 4)
        return num, title, level

    if ALL_CAPS_RE.match(s):
        title = s.title().strip()
        return title.replace(" ", "_").upper(), title, default_level

    # Fallback: treat as level 2 title-case heading
    return s.replace(" ", "_").lower(), s.strip(), default_level


# -----------------------------------------------------------------------------
# Structure builder
# -----------------------------------------------------------------------------

def build_document_structure(
    page_text: Dict[int, str],
    max_level: int = 4
) -> Dict[str, Any]:
    """
    Build a hierarchical section structure from page_text.

    page_text: page_number → raw text for that page

    Returns:
      {
        "sections": [SectionNode.to_dict(), ...],
        "page_index": {
            "1": {"section_ids": ["1", "1.1"]},
            "2": {"section_ids": ["1.1"]},
            ...
        }
      }
    """
    sections: List[SectionNode] = []
    page_index: Dict[int, Dict[str, Any]] = {}

    # Stack of open sections by level
    stack: List[SectionNode] = []

    sorted_pages = sorted(page_text.keys())

    for page in sorted_pages:
        text = page_text[page] or ""
        lines = [l for l in text.splitlines() if l.strip()]

        for line in lines:
            if not _is_potential_header(line):
                continue

            sec_id, title, level = _extract_header_id_and_title(line)
            level = min(level, max_level)

            # Close any deeper levels
            while stack and stack[-1].level >= level:
                stack.pop()

            parent_id = stack[-1].id if stack else None
            node = SectionNode(
                id=sec_id,
                title=title,
                level=level,
                page_start=page,
                page_end=page,
                parent_id=parent_id,
            )

            sections.append(node)
            if stack:
                stack[-1].children.append(node)
            stack.append(node)

        # Mark page → active sections
        active_ids = [s.id for s in stack]
        page_index[page] = {"section_ids": active_ids}

    # Extend page_end based on where children / later pages appear
    last_seen_for_id: Dict[str, int] = {}
    for page in sorted_pages:
        for sec_id in page_index.get(page, {}).get("section_ids", []):
            last_seen_for_id[sec_id] = page

    for s in sections:
        if s.id in last_seen_for_id:
            s.page_end = last_seen_for_id[s.id]

    # Root-level sections only (parent_id=None)
    roots = [s for s in sections if s.parent_id is None]

    return {
        "sections": [r.to_dict() for r in roots],
        "page_index": {str(k): v for k, v in page_index.items()},
    }


# -----------------------------------------------------------------------------
# Lookup helpers
# -----------------------------------------------------------------------------

def find_section_for_page(
    structure: Dict[str, Any],
    page: int
) -> Optional[Dict[str, Any]]:
    """
    Given the structure and a page number, return the deepest section active on that page.
    """
    pi = structure.get("page_index", {})
    entry = pi.get(str(page))
    if not entry:
        return None

    sec_ids = entry.get("section_ids", [])
    if not sec_ids:
        return None

    # Flatten all sections to map by id
    id_map: Dict[str, Dict[str, Any]] = {}

    def _walk(nodes: List[Dict[str, Any]]):
        for n in nodes:
            id_map[n["id"]] = n
            if n.get("children"):
                _walk(n["children"])

    _walk(structure.get("sections", []))

    # Return the deepest (last) section in the list that we can resolve
    for sec_id in reversed(sec_ids):
        n = id_map.get(sec_id)
        if n:
            return n

    return None

