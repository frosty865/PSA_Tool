"""
VOFC Engine — Seed Retrain v1.0

Purpose:

  - Load training_data/annotated_seed.jsonl (vulnerability / OFC seed pairs)

  - Generate a compact few-shot Modelfile tuned for physical security extraction

  - Create a new local Ollama model tag (vofc-engine:vNext)

  - Log retrain event to Supabase

  - Archive the consumed dataset



Notes:

  - This uses a SYSTEM prompt + few-shot exemplars (not gradient fine-tuning).

  - Keeps Modelfile small: up to MAX_EXAMPLES exemplars sampled from the seed set.

  - Safe to run repeatedly; will auto-increment v number.



Run:

  python C:\\Users\\frost\\OneDrive\\Desktop\\Projects\\PSA_Tool\\tools\\seed_retrain.py

"""

import os
import json
import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


# ------------------------------ CONFIG ------------------------------
MODEL_NAME = "vofc-engine"  # base family/tag to version
BASE_FALLBACK = "llama3:instruct"  # used if vofc-engine:latest not present
MAX_EXAMPLES = 40  # keep Modelfile reasonably small
# Training data paths - check new location first, fallback to legacy
from config import Config
TRAIN_DIR = Path(r"C:\Tools\VOFC-Flask\training_data") if Path(r"C:\Tools\VOFC-Flask\training_data").exists() else Path(r"C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\training_data")
SEED_FILE = TRAIN_DIR / "annotated_seed.jsonl"
MODELS_DIR = TRAIN_DIR / "models"
ARCHIVE_DIR = TRAIN_DIR / "archive"
LOGS_DIR = TRAIN_DIR / "logs"

# Ollama path - extract from Config.OLLAMA_URL (remove http:// and port)
OLLAMA_PATH = Path(Config.OLLAMA_URL.replace("http://", "").replace("https://", "").split(":")[0]) if ":" in Config.OLLAMA_URL else Path(r"C:\Tools\Ollama")
OLLAMA_EXE = OLLAMA_PATH / "ollama.exe"

# Supabase logging (optional but recommended)
USE_SUPABASE_LOG = True
SUPABASE_OK = False
try:
    from services.supabase_client import get_supabase_client  # type: ignore
    SUPABASE_OK = True
except Exception:
    SUPABASE_OK = False


# ------------------------------ UTILS ------------------------------
def log(msg: str):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.utcnow().isoformat()} | {msg}"
    print(line)
    with open(LOGS_DIR / "seed_retrain.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_cmd(cmd: str, timeout: int = 1800) -> tuple[int, str, str]:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def list_local_models() -> str:
    if not OLLAMA_EXE.exists():
        return ""
    code, out, err = run_cmd(f'"{OLLAMA_EXE}" list')
    return out if code == 0 else ""


def next_version_tag() -> str:
    # Find existing vofc-engine:vN locally and increment
    out = list_local_models()
    max_v = 0
    for line in out.splitlines():
        # lines look like: "vofc-engine:latest", "vofc-engine:v7", ...
        if line.strip().startswith(f"{MODEL_NAME}:v"):
            try:
                vnum = int(line.strip().split(":v", 1)[1].split()[0])
                max_v = max(max_v, vnum)
            except Exception:
                continue
    return f"v{max_v + 1 or 1}"


def base_from_tag() -> str:
    # Prefer vofc-engine:latest if present, else fallback
    out = list_local_models()
    if any(line.startswith(f"{MODEL_NAME}:latest") for line in out.splitlines()):
        return f"{MODEL_NAME}:latest"
    return BASE_FALLBACK


def load_seed_examples(path: Path, max_examples: int) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                rows.append(obj)
            except Exception:
                continue
    random.shuffle(rows)
    return rows[:max_examples]


def format_few_shots(examples: list[dict]) -> str:
    """
    Build concise few-shot exemplars. Each exemplar shows:

      - Input (sentence/short paragraph)

      - Expected classification (vulnerability vs ofc)

      - Required output JSON keys for VOFC pipeline compatibility

    """
    blocks = []
    for i, ex in enumerate(examples, 1):
        inp = ex.get("input", "")[:600].replace("\n", " ").strip()
        typ = (ex.get("output", {}) or {}).get("type", "vulnerability")
        # Normalize label
        label = "VULNERABILITY" if typ.lower().startswith("vuln") else "OFC"
        block = (
            f"### EXAMPLE {i}\n"
            f"Input:\n{inp}\n"
            f"Label: {label}\n"
            f"Target JSON schema:\n"
            f'{{"type":"{label.lower()}","vulnerability":"<concise vulnerability text if VULNERABILITY>","ofc":"<concise mitigation text if OFC>"}}\n'
        )
        blocks.append(block)
    return "\n".join(blocks)


def write_modelfile(base_from: str, fewshots: str, out_path: Path):
    """
    Construct a compact Modelfile:

      - FROM <base>

      - SYSTEM with domain instructions

      - A FEWSHOTS block (commented) for transparency (some runtimes ignore comments; SYSTEM carries the rules)

    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    system_prompt = f"""You are VOFC-ENGINE, a physical security extraction analyst.
Only produce findings related to PHYSICAL security for facilities (perimeter, access control, lighting, locks, barriers, security operations, guard force, CPTED, emergency planning, surveillance, intrusion detection, visitor management, key control, doors/windows, glazing, bollards, vehicle mitigation, mass notification).

Never produce cyber/CVE/patch/exploit content.



Task:

Given a chunk of text, decide if it can be expressed as either:

 - a VULNERABILITY (deficiency, missing control, inadequate measure), or

 - an OFC (Option for Consideration: a corrective action/mitigation)



Rules:

 - If text describes a problem/gap → output type="vulnerability" and fill 'vulnerability' field (concise).

 - If text describes a mitigation/action → output type="ofc" and fill 'ofc' field (concise).

 - Ignore definitions, headings, citations, or non-physical content.

 - Do not invent cyber issues, CVEs, patches, exploits, software libraries.

 - Keep outputs short, precise, facility-focused; prefer plain language.



Output JSON:

 {{"type":"vulnerability","vulnerability":"<concise text>"}}

 or

 {{"type":"ofc","ofc":"<concise text>"}}

"""

    content = []
    content.append(f"FROM {base_from}")
    content.append("")

    # SYSTEM prompt
    content.append('SYSTEM """')
    content.append(system_prompt)
    content.append('"""')
    content.append("")

    # Keep generation temperature modest for deterministic extraction
    content.append("PARAMETER temperature 0.2")
    content.append("PARAMETER num_ctx 8192")
    content.append("")

    # Commented few-shots for human traceability; SYSTEM carries hard rules
    content.append("### FEW-SHOTS (for reference)")
    content.append("### ---------------------------------------------")
    for line in fewshots.splitlines():
        content.append("### " + line)
    content.append("### ---------------------------------------------")
    content.append("")

    out_path.write_text("\n".join(content), encoding="utf-8")


def create_model(tag: str, modelfile: Path) -> tuple[bool, str]:
    if not OLLAMA_EXE.exists():
        return False, f"Ollama executable not found at {OLLAMA_EXE}"
    cmd = f'"{OLLAMA_EXE}" create {MODEL_NAME}:{tag} -f "{modelfile}"'
    log(f"[ACTION] {cmd}")
    code, out, err = run_cmd(cmd, timeout=3600)
    if code == 0:
        return True, out.strip()
    return False, (err or out).strip()


def log_learning_event(new_tag: str, seed_examples: int, base_from: str):
    if not (USE_SUPABASE_LOG and SUPABASE_OK):
        log("[WARN] Supabase logging disabled or client unavailable.")
        return
    try:
        supabase = get_supabase_client()
        payload = {
            "event_type": "auto_retrain",  # if constrained, fallback to 'auto_parse'
            "model_version": f"{MODEL_NAME}:{new_tag}",
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {
                "reason": "seed_retrain_jsonl",
                "seed_examples_used": seed_examples,
                "base_from": base_from,
                "script": "tools/seed_retrain.py"
            }
        }
        supabase.table("learning_events").insert(payload).execute()
        log(f"[SUCCESS] Logged learning_event for {MODEL_NAME}:{new_tag}")
    except Exception as e:
        log(f"[WARN] Failed to log learning_event: {e}")


# ------------------------------ MAIN ------------------------------
def main():
    log("=== Seed Retrain Start ===")

    # Safety checks
    if not SEED_FILE.exists():
        log(f"[ERROR] Seed file missing: {SEED_FILE}")
        return

    # Load seed examples and build few-shots
    try:
        examples = load_seed_examples(SEED_FILE, MAX_EXAMPLES)
        if not examples:
            log("[ERROR] No examples found in seed file.")
            return
    except Exception as e:
        log(f"[ERROR] Failed to load seed examples: {e}")
        return

    fewshots = format_few_shots(examples)
    new_tag = next_version_tag()
    base_tag = base_from_tag()

    # Write Modelfile
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    modelfile_path = MODELS_DIR / f"{MODEL_NAME}_{new_tag}.Modelfile"
    write_modelfile(base_tag, fewshots, modelfile_path)
    log(f"[INFO] Wrote Modelfile → {modelfile_path}")

    # Create model
    ok, msg = create_model(new_tag, modelfile_path)
    if not ok:
        log(f"[ERROR] Model build failed: {msg}")
        return
    log(f"[SUCCESS] Created model {MODEL_NAME}:{new_tag}")

    # Log to Supabase (optional)
    log_learning_event(new_tag, seed_examples=len(examples), base_from=base_tag)

    # Archive the seed file with timestamp
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    archived = ARCHIVE_DIR / f"annotated_seed_{ts}.jsonl"
    try:
        shutil.copy2(SEED_FILE, archived)
        log(f"[INFO] Archived seed file → {archived}")
    except Exception as e:
        log(f"[WARN] Could not archive seed file: {e}")

    log("=== Seed Retrain End ===")


if __name__ == "__main__":
    main()

