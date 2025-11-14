\# VOFC Engi# VOFC Engine – Zero-Error Architecture



This document encodes the Zero-Error Architecture Plan into concrete architectural standards.



---



\## 1. Goal



Eliminate errors through prevention, not handling.



In practice, this means:

\- Prevent errors via validation, contracts, and self-healing.

\- Fail-fast with clear diagnostics when assumptions are violated.

\- Avoid “catch and continue” or hidden defaults.

\- Treat bad data as a bug, not an acceptable state.



---



\## 2. Root Problems This Architecture Fixes



The architecture is designed to solve:



1\. Reactive error handling

&nbsp;  - Code catching exceptions and returning defaults.

&nbsp;  - Real problems hidden and never fixed.



2\. Missing validation layer

&nbsp;  - Environment not checked at startup.

&nbsp;  - Paths assumed.

&nbsp;  - External services called without verification.



3\. Unclear contracts between components

&nbsp;  - Flexible JSON shapes.

&nbsp;  - Inconsistent field names and types.

&nbsp;  - Ambiguous error responses.



4\. Silent corruption

&nbsp;  - Incomplete or malformed data written to Supabase.

&nbsp;  - Files moved around without traceable intent.



---



\## 3. Target State: Layered Architecture



The architecture is defined in layers. Cursor must preserve and reinforce these.



\### Layer 1: Startup Validation



Purpose: System must refuse to start if critical assumptions are broken.



Required behavior:



\- Validate environment variables:

&nbsp; - Supabase URL and keys.

&nbsp; - Ollama model name.

&nbsp; - Base data directory.

&nbsp; - Any other required values.



\- Validate filesystem:

&nbsp; - Base data directory exists or can be created.

&nbsp; - Required subdirectories (`incoming`, `processed`, `library`, `errors`, `review`, `logs`) exist or are created.

&nbsp; - On failure, raise a startup error with explicit reasons.



\- Validate services:

&nbsp; - Any critical external service that can be checked at startup should be checked.

&nbsp; - If a required service is unavailable, fail startup with a clear message.



All of this logic belongs in `config.validation` (or an equivalent centralized module), and must be called at startup for backend services.



---



\### Layer 2: API Contracts



Purpose: Make all interaction between frontend and backend predictable and safe.



Required behavior:



\- Define request/response schemas in `config.contracts` or equivalent:

&nbsp; - Use a consistent error envelope.

&nbsp; - Define allowed fields, types, and required properties.



\- Enforce schemas at the Flask boundary:

&nbsp; - Reject bad input with 4xx errors and clear messages.

&nbsp; - Never allow unknown or malformed payloads to reach core logic.



\- Ensure responses are stable:

&nbsp; - Avoid shape changes without a deliberate versioning decision.

&nbsp; - Always include required fields, even if values are null, where appropriate.



---



\### Layer 3: Self-Healing Systems



Purpose: Where possible, fix common problems automatically instead of failing repeatedly.



Examples:



\- Missing data directories:

&nbsp; - Attempt to create them at startup.

&nbsp; - Log exactly what was done.

&nbsp; - If creation fails, report and abort.



\- Stale or stuck processing states:

&nbsp; - Provide utilities that can detect inconsistent file states and repair them, or at least report them clearly.



Constraints:



\- Self-healing must be explicit and logged.

\- Self-healing must not hide persistent bugs; it should make them more visible while minimizing downtime.



Implementation lives in `config.self\_healing` or a dedicated module, and can be used by AutoProcessor and long-running services.



---



\### Layer 4: Dependency Verification



Purpose: No critical operation runs without verifying its dependencies.



Each operation that depends on external state must:



1\. Enumerate its dependencies (directories, services, config items).

2\. Verify those dependencies at the top of the function.

3\. Fail early with a clear error if something is missing.



Examples:



\- Before processing a document:

&nbsp; - Verify incoming directory exists.

&nbsp; - Verify Ollama endpoint is reachable.

&nbsp; - Verify Supabase is reachable (unless operating in offline mode).



\- Before writing to Supabase:

&nbsp; - Verify the connection and credentials.

&nbsp; - Verify the payload matches expected schema.



This logic should be centralized where possible (e.g. a `verify\_dependencies()` helper) and reused.



---



\### Layer 5: Configuration Management



Purpose: All configuration is centralized, validated, and documented.



Requirements:



\- `config/settings.py`:

&nbsp; - Reads environment variables.

&nbsp; - Applies safe defaults where acceptable.

&nbsp; - Does not silently ignore missing required values.



\- `config/paths.py`:

&nbsp; - Defines all key directories as `Path` objects.

&nbsp; - Uses the base `VOFC\_DATA\_DIR`.

&nbsp; - Does not hard-code absolute paths anywhere else in the codebase.



\- `config/validation.py`:

&nbsp; - Implements startup checks.

&nbsp; - Provides a single entrypoint like `run\_startup\_validation()`.



No other part of the system should access environment variables or hard-coded paths directly.



---



\### Layer 6: Data Integrity and Persistence



Purpose: Only valid, coherent data gets stored permanently.



Rules:



\- All model outputs (Phase 1/2/3) must be validated against a schema before being written to Supabase.

\- If validation fails:

&nbsp; - The document is routed to `errors/` with an attached diagnostic summary (log or JSON).

&nbsp; - Nothing is written as “valid output” to primary tables.



\- Supabase writes:

&nbsp; - Must check for HTTP errors and response codes.

&nbsp; - Must log failures with enough context (document ID, operation type, payload summary).



\- No partial writes that appear as success:

&nbsp; - If a multi-step write cannot be made transactional, failures must be clearly reported.

&nbsp; - Consider using staging tables or idempotent upserts for safety.



---



\### Layer 7: Observability



Purpose: Every significant action and failure is observable.



Standards:



\- Logs must be:

&nbsp; - Structured enough for basic parsing (e.g. include tags like `component`, `operation`, `document`).

&nbsp; - Written to a consistent location (`logs/` under the base data directory, unless overridden).



\- Important milestones:

&nbsp; - Startup validation success/failure.

&nbsp; - Each phase of document processing (ingest, chunk, model, post-process, save).

&nbsp; - Self-healing actions.

&nbsp; - Dependency check failures.

&nbsp; - External service outages.



Errors must never be logged as “INFO” or “success”; severity must match reality.



---



\## 4. Immediate Architectural Requirements



Cursor must enforce the following as it works:



1\. Create and maintain a `config/` module if it does not exist.

2\. Add or wire `run\_startup\_validation()` into all backend service entrypoints.

3\. Introduce or strengthen request/response contracts for all Flask endpoints.

4\. Route all environment/paths access through `config`.

5\. Replace “catch and return default” patterns with:

&nbsp;  - Pre-validation.

&nbsp;  - Specific error reporting.

&nbsp;  - Self-healing where justified.

6\. Add dependency verification checks to critical operations in:

&nbsp;  - AutoProcessor.

&nbsp;  - Ollama integration.

&nbsp;  - Supabase integration.

&nbsp;  - File-system watchers.



This architecture is not optional; it defines the target state for this system.

ne – Zero-Error Architecture



This document encodes the Zero-Error Architecture Plan into concrete architectural standards.



---



\## 1. Goal



Eliminate errors through prevention, not handling.



In practice, this means:

\- Prevent errors via validation, contracts, and self-healing.

\- Fail-fast with clear diagnostics when assumptions are violated.

\- Avoid “catch and continue” or hidden defaults.

\- Treat bad data as a bug, not an acceptable state.



---



\## 2. Root Problems This Architecture Fixes



The architecture is designed to solve:



1\. Reactive error handling

&nbsp;  - Code catching exceptions and returning defaults.

&nbsp;  - Real problems hidden and never fixed.



2\. Missing validation layer

&nbsp;  - Environment not checked at startup.

&nbsp;  - Paths assumed.

&nbsp;  - External services called without verification.



3\. Unclear contracts between components

&nbsp;  - Flexible JSON shapes.

&nbsp;  - Inconsistent field names and types.

&nbsp;  - Ambiguous error responses.



4\. Silent corruption

&nbsp;  - Incomplete or malformed data written to Supabase.

&nbsp;  - Files moved around without traceable intent.



---



\## 3. Target State: Layered Architecture



The architecture is defined in layers. Cursor must preserve and reinforce these.



\### Layer 1: Startup Validation



Purpose: System must refuse to start if critical assumptions are broken.



Required behavior:



\- Validate environment variables:

&nbsp; - Supabase URL and keys.

&nbsp; - Ollama model name.

&nbsp; - Base data directory.

&nbsp; - Any other required values.



\- Validate filesystem:

&nbsp; - Base data directory exists or can be created.

&nbsp; - Required subdirectories (`incoming`, `processed`, `library`, `errors`, `review`, `logs`) exist or are created.

&nbsp; - On failure, raise a startup error with explicit reasons.



\- Validate services:

&nbsp; - Any critical external service that can be checked at startup should be checked.

&nbsp; - If a required service is unavailable, fail startup with a clear message.



All of this logic belongs in `config.validation` (or an equivalent centralized module), and must be called at startup for backend services.



---



\### Layer 2: API Contracts



Purpose: Make all interaction between frontend and backend predictable and safe.



Required behavior:



\- Define request/response schemas in `config.contracts` or equivalent:

&nbsp; - Use a consistent error envelope.

&nbsp; - Define allowed fields, types, and required properties.



\- Enforce schemas at the Flask boundary:

&nbsp; - Reject bad input with 4xx errors and clear messages.

&nbsp; - Never allow unknown or malformed payloads to reach core logic.



\- Ensure responses are stable:

&nbsp; - Avoid shape changes without a deliberate versioning decision.

&nbsp; - Always include required fields, even if values are null, where appropriate.



---



\### Layer 3: Self-Healing Systems



Purpose: Where possible, fix common problems automatically instead of failing repeatedly.



Examples:



\- Missing data directories:

&nbsp; - Attempt to create them at startup.

&nbsp; - Log exactly what was done.

&nbsp; - If creation fails, report and abort.



\- Stale or stuck processing states:

&nbsp; - Provide utilities that can detect inconsistent file states and repair them, or at least report them clearly.



Constraints:



\- Self-healing must be explicit and logged.

\- Self-healing must not hide persistent bugs; it should make them more visible while minimizing downtime.



Implementation lives in `config.self\_healing` or a dedicated module, and can be used by AutoProcessor and long-running services.



---



\### Layer 4: Dependency Verification



Purpose: No critical operation runs without verifying its dependencies.



Each operation that depends on external state must:



1\. Enumerate its dependencies (directories, services, config items).

2\. Verify those dependencies at the top of the function.

3\. Fail early with a clear error if something is missing.



Examples:



\- Before processing a document:

&nbsp; - Verify incoming directory exists.

&nbsp; - Verify Ollama endpoint is reachable.

&nbsp; - Verify Supabase is reachable (unless operating in offline mode).



\- Before writing to Supabase:

&nbsp; - Verify the connection and credentials.

&nbsp; - Verify the payload matches expected schema.



This logic should be centralized where possible (e.g. a `verify\_dependencies()` helper) and reused.



---



\### Layer 5: Configuration Management



Purpose: All configuration is centralized, validated, and documented.



Requirements:



\- `config/settings.py`:

&nbsp; - Reads environment variables.

&nbsp; - Applies safe defaults where acceptable.

&nbsp; - Does not silently ignore missing required values.



\- `config/paths.py`:

&nbsp; - Defines all key directories as `Path` objects.

&nbsp; - Uses the base `VOFC\_DATA\_DIR`.

&nbsp; - Does not hard-code absolute paths anywhere else in the codebase.



\- `config/validation.py`:

&nbsp; - Implements startup checks.

&nbsp; - Provides a single entrypoint like `run\_startup\_validation()`.



No other part of the system should access environment variables or hard-coded paths directly.



---



\### Layer 6: Data Integrity and Persistence



Purpose: Only valid, coherent data gets stored permanently.



Rules:



\- All model outputs (Phase 1/2/3) must be validated against a schema before being written to Supabase.

\- If validation fails:

&nbsp; - The document is routed to `errors/` with an attached diagnostic summary (log or JSON).

&nbsp; - Nothing is written as “valid output” to primary tables.



\- Supabase writes:

&nbsp; - Must check for HTTP errors and response codes.

&nbsp; - Must log failures with enough context (document ID, operation type, payload summary).



\- No partial writes that appear as success:

&nbsp; - If a multi-step write cannot be made transactional, failures must be clearly reported.

&nbsp; - Consider using staging tables or idempotent upserts for safety.



---



\### Layer 7: Observability



Purpose: Every significant action and failure is observable.



Standards:



\- Logs must be:

&nbsp; - Structured enough for basic parsing (e.g. include tags like `component`, `operation`, `document`).

&nbsp; - Written to a consistent location (`logs/` under the base data directory, unless overridden).



\- Important milestones:

&nbsp; - Startup validation success/failure.

&nbsp; - Each phase of document processing (ingest, chunk, model, post-process, save).

&nbsp; - Self-healing actions.

&nbsp; - Dependency check failures.

&nbsp; - External service outages.



Errors must never be logged as “INFO” or “success”; severity must match reality.



---



\## 4. Immediate Architectural Requirements



Cursor must enforce the following as it works:



1\. Create and maintain a `config/` module if it does not exist.

2\. Add or wire `run\_startup\_validation()` into all backend service entrypoints.

3\. Introduce or strengthen request/response contracts for all Flask endpoints.

4\. Route all environment/paths access through `config`.

5\. Replace “catch and return default” patterns with:

&nbsp;  - Pre-validation.

&nbsp;  - Specific error reporting.

&nbsp;  - Self-healing where justified.

6\. Add dependency verification checks to critical operations in:

&nbsp;  - AutoProcessor.

&nbsp;  - Ollama integration.

&nbsp;  - Supabase integration.

&nbsp;  - File-system watchers.



This architecture is not optional; it defines the target state for this system.



