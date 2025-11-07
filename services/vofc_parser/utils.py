"""
Utility functions for VOFC parser
"""

import re


def clean_text(text):
    """Clean and normalize text for processing."""
    return re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()


def find_section_heading(sentences, idx, section_patterns):
    """Find the nearest section heading before the given sentence index."""
    for j in range(idx, -1, -1):
        for pat in section_patterns:
            if pat.search(sentences[j]):
                return sentences[j][:120]
    return "Unknown Section"


def generate_vuln_inverse(sentence):
    """Convert positive directive to a hypothetical vulnerability."""
    s = sentence.strip()
    s = re.sub(r'^[A-Z].*?\bshall\b', 'If not', s, flags=re.I)
    s = re.sub(r'\bshall\b', 'were not', s, flags=re.I)
    return f"Failure to comply with this standard may result in: {s}"

