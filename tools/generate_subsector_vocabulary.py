"""
generate_subsector_vocabulary.py

Builds an expanded subsector vocabulary with:
- keywords
- phrases
- synonyms
- semantic seeds

Vocabulary is derived entirely from your Supabase subsectors table.
"""

import json
import re
import sys
from typing import List, Dict
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import Config
from services.supabase_client import get_supabase_client

# ----------------------------------------------------------
# Configuration
# ----------------------------------------------------------

OUTPUT_FILE = project_root / "services" / "processor" / "normalization" / "subsector_vocabulary.json"

# ----------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------

def normalize(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def tokenize(text: str) -> List[str]:
    words = normalize(text).split()
    return [w for w in words if len(w) > 2]


def generate_phrases(text: str) -> List[str]:
    words = normalize(text).split()
    phrases = []
    for n in range(2, 5):  # 2–4 words
        for i in range(len(words) - n + 1):
            phrases.append(" ".join(words[i:i+n]))
    return sorted(list(set(phrases)))


# ----------------------------------------------------------
# Domain-Specific Synonym Expansion
# ----------------------------------------------------------

def subsector_synonyms(name: str) -> List[str]:
    """Rule-based synonym generator for each subsector name."""
    n = name.lower()

    if "educational" in n or "education" in n:
        return [
            "school", "k12", "k-12", "public school", "charter school",
            "private school", "college", "university", "campus", "school district",
            "classroom building", "education facility", "school security"
        ]

    if "religious" in n:
        return [
            "church", "synagogue", "mosque", "temple", "chapel",
            "religious site", "faith center", "worship facility", "ministry"
        ]

    if "hospitals" in n or "hospital" in n:
        return [
            "hospital", "medical center", "clinic", "healthcare facility",
            "emergency department", "er", "icu", "patient wing", "ambulatory care"
        ]

    if "lodging" in n:
        return [
            "hotel", "resort", "hospitality", "guest rooms",
            "hotel lobby", "hotel property", "inn"
        ]

    if "public assembly" in n:
        return [
            "stadium", "arena", "event center", "concert venue",
            "gathering place", "sports arena"
        ]

    if "correctional" in n:
        return [
            "jail", "prison", "detention center", "correctional institution",
            "inmate facility"
        ]

    if "federal" in n:
        return [
            "federal building", "federal office", "us government",
            "federal courthouse", "government facility", "gsa building"
        ]

    if "state" in n and "government" in n:
        return [
            "state building", "state government office", "state courthouse",
            "state agency facility"
        ]

    if "local" in n and "government" in n:
        return [
            "city hall", "municipal building", "county office",
            "local government facility"
        ]

    if "tribal" in n:
        return [
            "tribal government", "tribal building", "reservation facility"
        ]

    return []


# ----------------------------------------------------------
# Supabase Fetch
# ----------------------------------------------------------

def fetch_subsectors() -> List[Dict]:
    """Fetch all subsectors from Supabase."""
    try:
        client = get_supabase_client()
        
        resp = (
            client.table("subsectors")
            .select("*")
            .order("name")
            .execute()
        )

        if not resp.data:
            raise RuntimeError("No subsectors returned from Supabase.")

        return resp.data
    except Exception as e:
        print(f"[ERROR] Failed to fetch subsectors from Supabase: {e}")
        raise


# ----------------------------------------------------------
# Build Vocabulary
# ----------------------------------------------------------

def build_vocabulary(rows: List[Dict]) -> Dict:
    """Build vocabulary structure from subsector rows."""
    result = {"subsectors": []}

    for row in rows:
        name = row.get("name", "")
        desc = row.get("description", "") or ""
        sector_id = row.get("sector_id")
        subsector_id = row.get("id")

        # Generate features
        keywords = tokenize(f"{name} {desc}")
        phrases = generate_phrases(f"{name} {desc}")
        synonyms = subsector_synonyms(name)

        semantic_seeds = [
            name,
            desc if desc else name,
            f"{name} {desc}".strip()
        ]

        result["subsectors"].append({
            "id": subsector_id,
            "name": name,
            "sector_id": sector_id,
            "keywords": sorted(list(set(keywords))),
            "phrases": phrases,
            "synonyms": synonyms,
            "semantic_seeds": semantic_seeds
        })

    return result


def save_vocabulary(vocab: Dict):
    """Save vocabulary to JSON file."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(vocab, indent=2, ensure_ascii=False))
    print(f"[OK] Saved subsector vocabulary to: {OUTPUT_FILE.resolve()}")


# ----------------------------------------------------------
# Main
# ----------------------------------------------------------

if __name__ == "__main__":
    try:
        print("[INFO] Fetching subsectors from Supabase...")
        rows = fetch_subsectors()

        print(f"[INFO] Building vocabulary for {len(rows)} subsectors...")
        vocab = build_vocabulary(rows)

        print("[INFO] Writing JSON...")
        save_vocabulary(vocab)

        print(f"[DONE] Subsector vocabulary generation complete.")
        print(f"      Generated {len(vocab['subsectors'])} subsector entries.")
        print(f"      Output: {OUTPUT_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to generate vocabulary: {e}", file=sys.stderr)
        sys.exit(1)

