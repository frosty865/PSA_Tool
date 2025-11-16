"""
generate_discipline_vocabulary.py

Pulls the real discipline table from Supabase and generates
a production-ready vocabulary JSON file for DisciplineResolverV2.
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import Config
from services.supabase_client import get_supabase_client

# ----------------------------------------------------------
# Configuration
# ----------------------------------------------------------

OUTPUT_FILE = project_root / "services" / "processor" / "normalization" / "disciplines_vocabulary.json"

# ----------------------------------------------------------
# Utility Helpers
# ----------------------------------------------------------

def normalize(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def generate_keywords(name: str, desc: str, code: str):
    base = []

    # base keywords
    base.extend(normalize(name).split())
    base.extend(normalize(desc).split())

    # prefer 3+ character tokens
    base = [w for w in base if len(w) > 2]

    # include code explicitly
    if code:
        base.append(normalize(code))

    return sorted(list(set(base)))


def generate_phrases(text: str):
    words = normalize(text).split()
    phrases = []

    for n in range(2, 5):  # 2–4 word phrases
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i:i+n])
            phrases.append(phrase)

    # unique + keep meaningful
    return sorted(list({p for p in phrases if len(p.split()) > 1}))


def generate_semantic_seeds(name: str, desc: str):
    merged = f"{name} {desc}".strip()
    return [name, desc, merged] if desc else [name]


# ----------------------------------------------------------
# Ingest + Vocabulary Generator
# ----------------------------------------------------------

def fetch_disciplines() -> List[Dict]:
    """Fetch all disciplines from Supabase."""
    try:
        client = get_supabase_client()
        
        response = (
            client
            .table("disciplines")
            .select("*")
            .order("name")
            .execute()
        )

        if not response.data:
            raise RuntimeError("No disciplines returned from Supabase.")

        return response.data
    except Exception as e:
        print(f"[ERROR] Failed to fetch disciplines from Supabase: {e}")
        raise


def build_vocabulary(discipline_rows: List[Dict]) -> Dict:
    """Build vocabulary structure from discipline rows."""
    vocab = {"disciplines": []}

    for row in discipline_rows:
        name = row.get("name", "")
        desc = row.get("description", "") or ""
        code = row.get("code") or ""
        category = row.get("category", "")
        is_active = row.get("is_active", False)

        # Generate fields
        keywords = generate_keywords(name, desc, code)
        phrases = generate_phrases(f"{name} {desc}")
        seeds = generate_semantic_seeds(name, desc)

        vocab["disciplines"].append({
            "id": row["id"],
            "name": name,
            "code": code,
            "category": category,
            "is_active": is_active,
            "keywords": keywords,
            "phrases": phrases,
            "semantic_seeds": seeds,
        })

    return vocab


def save_vocabulary(vocab: Dict):
    """Save vocabulary to JSON file."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(vocab, indent=2, ensure_ascii=False))
    print(f"[OK] Discipline vocabulary written to: {OUTPUT_FILE.resolve()}")


# ----------------------------------------------------------
# Main Entrypoint
# ----------------------------------------------------------

if __name__ == "__main__":
    try:
        print("[INFO] Fetching disciplines from Supabase...")
        rows = fetch_disciplines()

        print(f"[INFO] Received {len(rows)} records. Building vocabulary...")
        vocab = build_vocabulary(rows)

        print("[INFO] Saving JSON vocabulary...")
        save_vocabulary(vocab)

        print(f"[DONE] Discipline vocabulary generation complete.")
        print(f"      Generated {len(vocab['disciplines'])} discipline entries.")
        print(f"      Output: {OUTPUT_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to generate vocabulary: {e}", file=sys.stderr)
        sys.exit(1)

