# VOFC Engine – Engineering Rules

Purpose: These rules govern ALL work performed in this repository.  
Cursor must treat this document as authoritative.

---

## 1. Core Principles

1. Zero-Error Architecture
   - Errors are prevented, not patched.
   - No “catch and return default” patterns.
   - Fail-fast with explicit, actionable diagnostics.
   - Self-healing is preferred to silent failure.

2. Deterministic Behavior
   - Same inputs and state must produce the same outputs.
   - No hidden side effects.
   - No silent data mutation.

3. Single Source of Truth
   - Configuration lives in `config/`.
   - File-system layout is defined centrally.
   - API contracts are defined once and reused.

4. Observability First
   - Every failure path must log clearly.
   - Logs must be structured enough to analyze.
   - No swallowing stack traces or masking errors.

5. Explicit Over Implicit
   - No magic paths; paths are built via config.
   - No implicit environment assumptions.
   - No auto-creating important resources without logging and validation.

---

## 2. Global Code Rules

These rules apply to all Python, JavaScript/TypeScript, and support scripts.

### 2.1 Error Handling

- Do NOT:
  - Catch broad `Exception` and continue.
  - Return fallback values when something critical fails.
  - Log errors as warnings and proceed as if nothing happened.

- DO:
  - Validate inputs before processing.
  - Raise explicit, domain-specific errors when assumptions are broken.
  - Provide clear, human-readable error messages with context.
  - Fail early rather than corrupt state or save bad data.

Example of forbidden pattern:

```python
try:
    data = json.loads(raw)
except Exception:
    return []
