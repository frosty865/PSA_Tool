# routes/processing.py  (or services/vofc_single_pass.py)

# Single-pass VOFC → flattened JSON → Supabase submissions (+ learning logs)



from flask import Blueprint, request, jsonify

import os, json, time, logging, fitz, requests

from services.supabase_client import get_supabase_client



processing_bp = Blueprint("processing", __name__)

log = logging.getLogger("vofc_single_pass")



# --- Paths / Model ----------------------------------------------------------

DATA_ROOT   = r"C:\Tools\Ollama\Data"

INCOMING    = os.path.join(DATA_ROOT, "incoming")

PROCESSED   = os.path.join(DATA_ROOT, "processed")

LIBRARY     = os.path.join(DATA_ROOT, "library")



OLLAMA_URL    = "http://127.0.0.1:11434/api/generate"

MODEL_NAME    = "vofc-engine-sp"

MODEL_VERSION = "vofc-engine-sp:v1"



# --- Utils ------------------------------------------------------------------

def _s(val):

    """safe string; dict/list → json; None→''"""

    if val is None: return ""

    if isinstance(val, (dict, list)): return json.dumps(val, ensure_ascii=False)

    return str(val)



def extract_text_with_pages(pdf_path):

    doc = fitz.open(pdf_path)

    parts = []

    for i, page in enumerate(doc):

        t = page.get_text("text").strip()

        if t:

            parts.append(f"PAGE {i+1}:\n{t}")

    return "\n\n".join(parts)



def call_model(prompt):

    payload = {"model": MODEL_NAME, "prompt": prompt, "stream": False}

    r = requests.post(OLLAMA_URL, json=payload, timeout=900)

    r.raise_for_status()

    raw = (r.json().get("response") or "").strip()

    # tolerate model wrapping

    i, j = raw.find("["), raw.rfind("]")

    body = raw[i:j+1] if i != -1 and j != -1 else raw

    return json.loads(body)



def flatten_vulnerabilities(phase_json):

    """

    Accepts either:

      - already-flat array (list of dicts), or

      - phase2-style object with .all_phase2_records[*].vulnerabilities[*]

    Returns a flat list of {vulnerability, ofc, discipline, sector, subsector, confidence, source_context, page_ref}

    """

    flat = []

    if isinstance(phase_json, list):

        # already flat

        for v in phase_json:

            if not v: continue

            flat.append({

                "vulnerability": _s(v.get("vulnerability")),

                "ofc": _s(v.get("ofc")),

                "discipline": _s(v.get("discipline") or "General Security"),

                "sector": _s(v.get("sector") or "General"),

                "subsector": _s(v.get("subsector") or "General"),

                "confidence": v.get("confidence", 0.5),

                "source_context": _s(v.get("source_context")),

                "page_ref": v.get("source_page") or v.get("page_ref") or ""

            })

        return flat



    # phase2 object

    for rec in (phase_json or {}).get("all_phase2_records", []):

        page   = rec.get("source_page")

        dflt_d = rec.get("discipline") or "General Security"

        dflt_s = rec.get("sector") or "General"

        dflt_ss= rec.get("subsector") or "General"

        for v in rec.get("vulnerabilities", []):

            flat.append({

                "vulnerability": _s(v.get("vulnerability")),

                "ofc": _s(v.get("ofc")),

                "discipline": _s(v.get("discipline") or dflt_d),

                "sector": _s(v.get("sector") or dflt_s),

                "subsector": _s(v.get("subsector") or dflt_ss),

                "confidence": v.get("confidence", 0.5),

                "source_context": _s(v.get("source_context")),

                "page_ref": page

            })

    return flat



def dedupe(records):

    seen, out = set(), []

    for r in records:

        v = _s(r.get("vulnerability")).strip().lower()

        o = _s(r.get("ofc")).strip().lower()

        p = _s(r.get("page_ref")).strip()

        if not v or not o:  # must have both

            continue

        key = (v, o, p)

        if key in seen: 

            continue

        seen.add(key)

        out.append(r)

    return out



def save_json(obj, base_name):

    os.makedirs(PROCESSED, exist_ok=True)

    path = os.path.join(PROCESSED, base_name)

    with open(path, "w", encoding="utf-8") as f:

        json.dump(obj, f, indent=2, ensure_ascii=False)

    return path



# --- Supabase bridge --------------------------------------------------------

def sync_to_supabase(result_json, filename):

    try:

        supabase = get_supabase_client()

        # --- 1️⃣ Create the parent submission record ---

        sub_payload = {

            "type": "vulnerability",

            "status": "pending_review",

            "source": "psa_tool_auto",

            "submitter_email": "system@zophielgroup.com",

            "data": result_json

        }

        sub = supabase.table("submissions").insert(sub_payload).execute()

        submission_id = sub.data[0]["id"]

        log.info(f"Created submission {submission_id} for {filename}")



        vulns = result_json.get("vulnerabilities", [])

        log.info(f"Inserting {len(vulns)} vulnerabilities into Supabase...")



        # --- 2️⃣ Insert vulnerabilities individually ---

        for idx, item in enumerate(vulns, start=1):

            v_payload = {

                "submission_id": submission_id,

                "vulnerability": item.get("vulnerability"),

                "discipline": item.get("discipline"),

                "sector": item.get("sector"),

                "subsector": item.get("subsector"),

                "source_title": filename,

                "source_page": str(item.get("page_ref") or ""),

                "source_context": item.get("source_context"),

                "confidence_score": float(item.get("confidence") or 0.5),

                "parser_version": MODEL_VERSION

            }

            vres = supabase.table("submission_vulnerabilities").insert(v_payload).execute()



            if not vres.data:

                log.error(f"[{idx}] Vulnerability insert failed: {item.get('vulnerability')[:60]}")

                continue



            vuln_id = vres.data[0]["id"]

            log.info(f"[{idx}] Vulnerability inserted: {vuln_id}")



            # --- 3️⃣ Insert its corresponding OFC ---

            ofc_payload = {

                "submission_id": submission_id,

                "vulnerability_id": vuln_id,

                "option_text": item.get("ofc"),

                "discipline": item.get("discipline"),

                "context": item.get("source_context"),

                "confidence_score": float(item.get("confidence") or 0.5)

            }

            ores = supabase.table("submission_options_for_consideration").insert(ofc_payload).execute()

            if not ores.data:

                log.error(f"[{idx}] OFC insert failed for {vuln_id}")

                continue



            ofc_id = ores.data[0]["id"]



            # --- 4️⃣ Link them ---

            link_payload = {

                "submission_id": submission_id,

                "vulnerability_id": vuln_id,

                "ofc_id": ofc_id,

                "link_type": "direct",

                "confidence_score": float(item.get("confidence") or 0.5)

            }

            supabase.table("submission_vulnerability_ofc_links").insert(link_payload).execute()

            log.info(f"[{idx}] Linked vuln {vuln_id} → ofc {ofc_id}")



        # --- 5️⃣ Record source metadata ---

        src_payload = {

            "submission_id": submission_id,

            "source_title": filename,

            "source_type": "pdf",

            "sector": "General"

        }

        supabase.table("submission_sources").insert(src_payload).execute()

        log.info(f"Completed Supabase sync for submission {submission_id}")



        return submission_id



    except Exception as e:

        log.exception(f"Supabase sync failed: {e}")

        return None



def log_learning_event(submission_id, count, elapsed):

    try:

        supabase = get_supabase_client()

        supabase.table("learning_events").insert({

            "submission_id": submission_id,

            "model_version": MODEL_VERSION,

            "records_extracted": count,

            "elapsed_time_sec": elapsed,

            "event_type": "auto_process",

            "notes": "Single-pass engine upload and ingestion"

        }).execute()

    except Exception as e:

        log.warning(f"learning_events insert failed: {e}")



def update_learning_stats(count, elapsed):

    try:

        supabase = get_supabase_client()

        res = supabase.table("learning_stats").select("*").eq("model_version", MODEL_VERSION).execute()

        if res.data:

            row = res.data[0]

            total_runs    = int(row.get("total_runs") or 0) + 1

            total_records = int(row.get("total_records") or 0) + int(count)

            total_time    = float(row.get("total_time_sec") or 0.0) + float(elapsed)

            supabase.table("learning_stats").update({

                "total_runs": total_runs,

                "total_records": total_records,

                "total_time_sec": total_time,

                "avg_records_per_run": round(total_records / total_runs, 2),

                "avg_time_sec": round(total_time / total_runs, 2),

                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S")

            }).eq("model_version", MODEL_VERSION).execute()

        else:

            supabase.table("learning_stats").insert({

                "model_version": MODEL_VERSION,

                "total_runs": 1,

                "total_records": int(count),

                "total_time_sec": float(elapsed),

                "avg_records_per_run": int(count),

                "avg_time_sec": float(elapsed),

                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S")

            }).execute()

    except Exception as e:

        log.warning(f"learning_stats upsert failed: {e}")



# --- HTTP entrypoint --------------------------------------------------------

@processing_bp.route("/api/process", methods=["POST"])

def process_pdf():

    try:

        # ingest file

        if "file" in request.files:

            f = request.files["file"]

            os.makedirs(INCOMING, exist_ok=True)

            in_path = os.path.join(INCOMING, f.filename)

            f.save(in_path)

        else:

            data = request.get_json(silent=True) or {}

            in_path = data.get("path")

            if not in_path or not os.path.exists(in_path):

                return jsonify({"error": "No valid file provided"}), 400



        base = os.path.basename(in_path)

        t0 = time.time()

        log.info(f"Processing {base}")



        # run model

        text = extract_text_with_pages(in_path)

        raw_results = call_model(text)          # may be flat or phase2-shaped

        flat = flatten_vulnerabilities(raw_results)

        flat = dedupe(flat)



        final = {

            "source_file": base,

            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),

            "model_version": MODEL_VERSION,

            "final_records": len(flat),

            "vulnerabilities": flat

        }



        out_path = save_json(final, f"{os.path.splitext(base)[0]}_vofc.json")



        submission_id = sync_to_supabase(final, base)

        elapsed = round(time.time() - t0, 2)

        if submission_id:

            log_learning_event(submission_id, len(flat), elapsed)

            update_learning_stats(len(flat), elapsed)



        # move source to library (don't crash if watcher moved it)

        try:

            os.makedirs(LIBRARY, exist_ok=True)

            if os.path.exists(in_path):

                os.replace(in_path, os.path.join(LIBRARY, base))

        except Exception as e:

            log.warning(f"Post-move skipped: {e}")



        return jsonify({

            "status": "success",

            "submission_id": submission_id,

            "records": len(flat),

            "elapsed_sec": elapsed,

            "file": base,

            "output": out_path

        })

    except Exception as e:

        log.exception(e)

        return jsonify({"error": str(e)}), 500
