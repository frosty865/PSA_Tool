# VOFC Engine – Zero-Error Architecture

This document encodes the Zero-Error Architecture Plan into concrete architectural standards.

---

## 1. Goal

Eliminate errors through prevention, not handling.

In practice, this means:

- Prevent errors via validation, contracts, and self-healing.
- Fail-fast with clear diagnostics when assumptions are violated.
- Avoid "catch and continue" or hidden defaults.
- Treat bad data as a bug, not an acceptable state.

---

## 2. Root Problems This Architecture Fixes

The architecture is designed to solve:

1. Reactive error handling
   - Code catching exceptions and returning defaults.
   - Real problems hidden and never fixed.

2. Missing validation layer
   - Environment not checked at startup.
   - Paths assumed.
   - External services called without verification.

3. Unclear contracts between components
   - Flexible JSON shapes.
   - Inconsistent field names and types.
   - Ambiguous error responses.

4. Silent corruption
   - Incomplete or malformed data written to Supabase.
   - Files moved around without traceable intent.

---

## 3. Target State: Layered Architecture

The architecture is defined in layers. Cursor must preserve and reinforce these.

### Layer 1: Startup Validation

Purpose: System must refuse to start if critical assumptions are broken.

Required behavior:

- Validate environment variables:
  - Supabase URL and keys.
  - Ollama model name.
  - Base data directory.
  - Any other required values.

- Validate filesystem:
  - Base data directory exists or can be created.
  - Required subdirectories (`incoming`, `processed`, `library`, `errors`, `review`, `logs`) exist or are created.
  - On failure, raise a startup error with explicit reasons.

- Validate services:
  - Any critical external service that can be checked at startup should be checked.
  - If a required service is unavailable, fail startup with a clear message.

All of this logic belongs in `config.validation` (or an equivalent centralized module), and must be called at startup for backend services.

---

### Layer 2: API Contracts

Purpose: Make all interaction between frontend and backend predictable and safe.

Required behavior:

- Define request/response schemas in `config.contracts` or equivalent:
  - Use a consistent error envelope.
  - Define allowed fields, types, and required properties.

- Enforce schemas at the Flask boundary:
  - Reject bad input with 4xx errors and clear messages.
  - Never allow unknown or malformed payloads to reach core logic.

- Ensure responses are stable:
  - Avoid shape changes without a deliberate versioning decision.
  - Always include required fields, even if values are null, where appropriate.

---

### Layer 3: Self-Healing Systems

Purpose: Where possible, fix common problems automatically instead of failing repeatedly.

Examples:

- Missing data directories:
  - Attempt to create them at startup.
  - Log exactly what was done.
  - If creation fails, report and abort.

- Stale or stuck processing states:
  - Provide utilities that can detect inconsistent file states and repair them, or at least report them clearly.

Constraints:

- Self-healing must be explicit and logged.
- Self-healing must not hide persistent bugs; it should make them more visible while minimizing downtime.

Implementation lives in `config.self_healing` or a dedicated module, and can be used by AutoProcessor and long-running services.

---

### Layer 4: Dependency Verification

Purpose: No critical operation runs without verifying its dependencies.

Each operation that depends on external state must:

1. Enumerate its dependencies (directories, services, config items).
2. Verify those dependencies at the top of the function.
3. Fail early with a clear error if something is missing.

Examples:

- Before processing a document:
  - Verify incoming directory exists.
  - Verify Ollama endpoint is reachable.
  - Verify Supabase is reachable (unless operating in offline mode).

- Before writing to Supabase:
  - Verify the connection and credentials.
  - Verify the payload matches expected schema.

This logic should be centralized where possible (e.g. a `verify_dependencies()` helper) and reused.

---

### Layer 5: Configuration Management

Purpose: All configuration is centralized, validated, and documented.

Requirements:

- `config/settings.py`:
  - Reads environment variables.
  - Applies safe defaults where acceptable.
  - Does not silently ignore missing required values.

- `config/paths.py`:
  - Defines all key directories as `Path` objects.
  - Uses the base `VOFC_DATA_DIR`.
  - Does not hard-code absolute paths anywhere else in the codebase.

- `config/validation.py`:
  - Implements startup checks.
  - Provides a single entrypoint like `run_startup_validation()`.

No other part of the system should access environment variables or hard-coded paths directly.

---

### Layer 6: Data Integrity and Persistence

Purpose: Only valid, coherent data gets stored permanently.

Rules:

- All model outputs (Phase 1/2/3) must be validated against a schema before being written to Supabase.
- If validation fails:
  - The document is routed to `errors/` with an attached diagnostic summary (log or JSON).
  - Nothing is written as "valid output" to primary tables.

- Supabase writes:
  - Must check for HTTP errors and response codes.
  - Must log failures with enough context (document ID, operation type, payload summary).

- No partial writes that appear as success:
  - If a multi-step write cannot be made transactional, failures must be clearly reported.
  - Consider using staging tables or idempotent upserts for safety.

---

### Layer 7: Observability

Purpose: Every significant action and failure is observable.

Standards:

- Logs must be:
  - Structured enough for basic parsing (e.g. include tags like `component`, `operation`, `document`).
  - Written to a consistent location (`logs/` under the base data directory, unless overridden).

- Important milestones:
  - Startup validation success/failure.
  - Each phase of document processing (ingest, chunk, model, post-process, save).
  - Self-healing actions.
  - Dependency check failures.
  - External service outages.

Errors must never be logged as "INFO" or "success"; severity must match reality.

---

## 4. Immediate Architectural Requirements

Cursor must enforce the following as it works:

1. Create and maintain a `config/` module if it does not exist.
2. Add or wire `run_startup_validation()` into all backend service entrypoints.
3. Introduce or strengthen request/response contracts for all Flask endpoints.
4. Route all environment/paths access through `config`.
5. Replace "catch and return default" patterns with:
   - Pre-validation.
   - Specific error reporting.
   - Self-healing where justified.
6. Add dependency verification checks to critical operations in:
   - AutoProcessor.
   - Ollama integration.
   - Supabase integration.
   - File-system watchers.

This architecture is not optional; it defines the target state for this system.

