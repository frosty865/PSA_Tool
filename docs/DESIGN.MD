
---

## 2. `DESIGN.md`

```md
# VOFC Engine – System Design

This document describes the intended design of the VOFC Engine ecosystem.  
Cursor must use this as the reference model when modifying or extending the system.

---

## 1. High-Level Overview

The VOFC Engine is a multi-component system for processing security-related documents into structured vulnerabilities and Options for Consideration (OFCs), and loading them into a VOFC Library backed by Supabase.

Core components:

1. Frontend (Next.js, Vercel-hosted)
   - Admin panel (system health, model analytics, review workflows).
   - Submission interface for assessments/documents.
   - Viewer/VOFC Library interfaces.

2. Backend API (Flask)
   - Provides REST endpoints for:
     - Document submission.
     - System health checks.
     - Progress tracking.
     - Review and approval workflows.
     - Model analytics.
   - Acts as a broker between frontend, Supabase, and AutoProcessor/Ollama.

3. AutoProcessor Service
   - Watches `incoming/` for new documents.
   - Extracts and chunks content.
   - Calls Ollama models (Phase 1/2/3).
   - Produces structured JSON output to `processed/`.
   - Moves original PDF to `library/`.
   - On failure, moves file to `errors/` with diagnostic metadata.

4. Ollama Model Server
   - Hosts custom models (e.g. `vofc-engine`, `vofc-parser`, `vofc-auditor`).
   - Accepts local HTTP requests from AutoProcessor.
   - Returns model output for vulnerabilities and OFCs.

5. Supabase (PostgreSQL)
   - Persists:
     - Submissions and raw processed data.
     - Normalized vulnerabilities and OFCs.
     - Sector / subsector / discipline taxonomy.
     - Learning events and model analytics.
   - Exposes views for the frontend (e.g. `vw_assessment_clean`, `vw_findings`).

6. File-System Layout (Windows host)
   - Base directory: `VOFC_DATA_DIR` (e.g. `C:\Tools\Ollama\Data`).
   - Required subdirectories:
     - `incoming/`
     - `processed/`
     - `library/`
     - `review/`
     - `errors/`
     - `logs/`

---

## 2. Data Flow: Document Lifecycle

1. **Submission**
   - A document is submitted via the web UI or copied into `incoming/`.
   - Flask or a watcher acknowledges the submission and logs an entry.

2. **Ingestion and Chunking**
   - AutoProcessor detects the new file in `incoming/`.
   - Text is extracted from the PDF (with page references).
   - Text is normalized and chunked.

3. **Model Phases**
   - Phase 1: Parser
     - Identifies candidate vulnerabilities and OFCs from chunks.
   - Phase 2: Engine/Classifier
     - Normalizes, deduplicates, and assigns sector/subsector/discipline.
   - Phase 3: Auditor (optional layer)
     - Validates and scores vulnerabilities and OFCs, checks consistency.

4. **Post-Processing**
   - Model output is validated against strict JSON schemas.
   - Any violations cause the document to be flagged and moved to `errors/` with diagnostics.
   - Valid output is stored:
     - Raw result JSON in `processed/`.
     - Normalized records posted to Supabase via API.

5. **Library Integration**
   - Normalized vulnerabilities and OFCs are:
     - Linked to source documents.
     - Mapped to sector / subsector / discipline.
     - Available to the VOFC Library and SAFE-style output.

6. **Review and Feedback**
   - Admin panel shows:
     - New processed documents in `review/`.
     - Per-document vulnerabilities and OFCs.
   - User can:
     - Approve, edit, or reject items.
     - Trigger learning events to refine models.

---

## 3. Health and Observability

1. System Health Endpoint (Flask)
   - Reports:
     - Flask API status.
     - Supabase connectivity.
     - Ollama server availability.
     - AutoProcessor state (if exposed).
     - Tunnel status (if applicable).

2. Logging
   - All components must log to `VOFC_DATA_DIR/logs` (or a configured path).
   - Logs must capture:
     - Startup validation results.
     - Document processing stages.
     - Model invocation success/failure.
     - Supabase write results.
     - Self-healing actions and their outcomes.

3. Model Analytics
   - Capture:
     - Vulnerability/OFC yield per document.
     - Error rates.
     - Rejected vs accepted findings.
     - Learning events.

---

## 4. Configuration Model

- All config values (paths, URLs, keys, model names) must be loaded through `config/`:
  - `config.settings` – environment-derived settings, with defaults where safe.
  - `config.paths` – resolved and validated `Path` objects for all data directories.
  - `config.contracts` – schemas for API payloads and persistent objects.
  - `config.validation` – startup checks for environment, directories, and services.
  - `config.self_healing` – helpers for repairing common failures (missing dirs, stuck states).

---

## 5. Interaction Patterns Between Components

1. Frontend ↔ Flask
   - JSON over HTTPS.
   - Strict request and response contracts.
   - Health checks, status pages, admin operations.

2. Flask ↔ AutoProcessor
   - If coupled:
     - Flask can enqueue work or push files into `incoming/`.
     - Flask may expose endpoints that reflect AutoProcessor state.
   - If decoupled:
     - AutoProcessor is file-system driven but still exposes logs and status.

3. AutoProcessor ↔ Ollama
   - HTTP calls to local Ollama server.
   - Timeouts, retries, and failure logging required.
   - Model config (name, temperature, etc.) sourced from `config.settings`.

4. AutoProcessor ↔ Supabase
   - HTTP/REST calls via Supabase client.
   - Strict error checking; no partial writes without logging.
   - Use transactions or staging tables where appropriate.

---

## 6. Design Constraints

- No component should assume “happy path only”; every external dependency must be checked.
- Processing must be robust to:
  - Invalid PDFs.
  - Missing text.
  - Model timeouts.
  - Supabase outages.
- Under failure conditions:
  - Never lose the document.
  - Never write corrupted or incomplete data as if it were valid.
  - Always produce actionable logs.

Cursor must treat this design as the intended target state and gradually move the implementation toward it while preserving working behavior.
