"""
diagnostic.py — VOFC Backend Runtime Diagnostics

------------------------------------------------

This script prints:

1. Absolute path of currently running backend

2. All loaded VOFC modules and where they were imported from

3. Any stale __pycache__ locations

4. Duplicate module names loaded from different directories

5. Import order and sys.path scan

6. Version banners for every V2 module

"""

import os
import sys
import pkgutil
import importlib
import hashlib
from pathlib import Path

# -------------------------------
# Section 1: Print runtime paths
# -------------------------------
print("\n========== VOFC BACKEND RUNTIME DIAGNOSTICS ==========")
print(f"Python Executable : {sys.executable}")
print(f"Current Working Dir: {os.getcwd()}")
print(f"sys.path:")
for p in sys.path:
    print("  -", p)

# -------------------------------
# Section 2: Scan for VOFC modules
# -------------------------------

TARGET_PREFIXES = [
    "document_classifier",
    "taxonomy_resolver",
    "postprocess",
    "engine",
    "processor",
    "phase2_engine",
    "unified_pipeline",
    "normalize",
    "record_normalizer",
    "supabase_upload",
]

print("\n--- Loaded VOFC Modules ---")

loaded = {}

for name, module in sorted(sys.modules.items()):
    for prefix in TARGET_PREFIXES:
        if name.startswith(prefix):
            try:
                filepath = getattr(module, "__file__", None)
            except Exception:
                filepath = "UNKNOWN"

            loaded[name] = filepath
            print(f"MODULE: {name}")
            print(f"  PATH: {filepath}")
            print("-")

# -------------------------------
# Section 3: Detect duplicates
# -------------------------------
print("\n--- Duplicate Modules Check ---")

seen = {}
for mod, path in loaded.items():
    if not path:
        continue
    key = Path(path).stem
    if key not in seen:
        seen[key] = []
    seen[key].append(path)

for key, paths in seen.items():
    if len(paths) > 1:
        print(f"!! DUPLICATION DETECTED FOR MODULE '{key}' !!")
        for p in paths:
            print("    ->", p)

# -------------------------------
# Section 4: Detect stale pycache
# -------------------------------
print("\n--- Pycache Locations ---")

root = Path(os.getcwd())
pycaches = list(root.rglob("__pycache__"))

if pycaches:
    for p in pycaches:
        print("  -", p)
else:
    print("  (none found)")

# -------------------------------
# Section 5: Hash active modules
# -------------------------------
print("\n--- Module Content Hashes (MD5) ---")

def hash_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

for mod, path in loaded.items():
    if path and os.path.exists(path):
        print(f"{mod}: {hash_file(path)}")

print("\n=======================================================\n")

