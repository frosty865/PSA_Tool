# Phase 2: Error Handling - Detailed Implementation Plan

**Objective:** Replace catch-and-default patterns with fail-fast validation, eliminate silent failures, and preserve error context.

**Total Tasks:** ~60 atomic tasks  
**Estimated Time:** 3-4 days  
**Risk Level:** Medium (may break existing error handling assumptions, requires careful testing)

---

## Strategy

Phase 2 focuses on **preventing errors at the source** rather than catching them after they occur. The key principle: **If an operation cannot succeed, fail immediately with clear diagnostics.**

### Core Principles:
1. **Fail-Fast:** If a dependency is missing or invalid, raise an exception immediately
2. **Preserve Context:** Never wrap exceptions in generic `Exception`, preserve original types
3. **Explicit Modes:** If a feature is optional (e.g., Supabase), operate in explicit "offline mode" rather than silently failing
4. **Dependency Verification:** Verify all dependencies before operations, not after they fail

---

## Task Group 1: Create Error Types and Utilities

### Task 1.1: Create Domain-Specific Exception Classes
**File:** `config/exceptions.py` (NEW)  
**Lines:** Create new file  
**Changes:**
- Create `ConfigurationError` (already exists in `config/__init__.py`, move to exceptions.py)
- Create `DependencyError` for missing dependencies
- Create `ValidationError` for data validation failures
- Create `ServiceError` for service-related failures
- Create `FileOperationError` for file system errors
**Estimated Lines:** 50 lines  
**Dependencies:** None

### Task 1.2: Create Dependency Verification Utility
**File:** `config/dependencies.py` (NEW)  
**Lines:** Create new file  
**Changes:**
- Create `verify_dependencies(operation_name, deps)` function
- Support verification of: files, directories, services, environment variables, network endpoints
- Raise `DependencyError` with clear message if any dependency is missing
**Estimated Lines:** 100 lines  
**Dependencies:** Task 1.1

### Task 1.3: Create Service Health Check Utility
**File:** `config/service_health.py` (NEW)  
**Lines:** Create new file  
**Changes:**
- Create `check_service_health(service_name)` function
- Create `check_ollama_health()` function
- Create `check_supabase_health()` function
- Return boolean or raise `ServiceError` with details
**Estimated Lines:** 80 lines  
**Dependencies:** Task 1.1

---

## Task Group 2: Fix routes/system.py (HIGH PRIORITY)

### Task 2.1: Fix `/api/system/health` Endpoint
**File:** `routes/system.py`  
**Lines:** ~50-150  
**Changes:**
- Remove `except Exception` blocks that return default health status
- Add dependency verification before health checks
- Fail-fast if critical services cannot be checked
- Preserve original exception types
**Estimated Lines:** 30 lines changed  
**Dependencies:** Task 1.1, Task 1.2, Task 1.3

### Task 2.2: Fix `/api/system/progress` Endpoint
**File:** `routes/system.py`  
**Lines:** ~200-300  
**Changes:**
- Remove `except Exception` that returns empty progress
- Verify directories exist before counting files
- Raise `DependencyError` if directories cannot be accessed
- Preserve file counting errors with context
**Estimated Lines:** 25 lines changed  
**Dependencies:** Task 1.1, Task 1.2

### Task 2.3: Fix `/api/system/logs` Endpoint
**File:** `routes/system.py`  
**Lines:** ~400-500  
**Changes:**
- Remove `except Exception: pass` that swallows log read errors
- Verify log file exists and is readable before reading
- Raise `FileOperationError` if log file cannot be read
**Estimated Lines:** 20 lines changed  
**Dependencies:** Task 1.1, Task 1.2

### Task 2.4: Fix `/api/system/control` Endpoint
**File:** `routes/system.py`  
**Lines:** ~600-800  
**Changes:**
- Remove `except Exception` blocks that return generic error messages
- Verify service exists before attempting control operations
- Raise `ServiceError` with specific details for each failure mode
**Estimated Lines:** 40 lines changed  
**Dependencies:** Task 1.1, Task 1.2, Task 1.3

### Task 2.5: Fix Tunnel Log Reading
**File:** `routes/system.py`  
**Lines:** ~1600-1650  
**Changes:**
- Remove `except Exception` that catches all tunnel log errors
- Verify tunnel log file exists before reading
- Raise `FileOperationError` if file cannot be read
**Estimated Lines:** 15 lines changed  
**Dependencies:** Task 1.1, Task 1.2

---

## Task Group 3: Fix services/ollama_client.py

### Task 3.1: Fix Model Availability Checks
**File:** `services/ollama_client.py`  
**Lines:** ~200-250  
**Changes:**
- Remove `except Exception` that returns empty model list
- Verify Ollama endpoint is reachable before querying
- Raise `ServiceError` if Ollama is unreachable
- Preserve network error types (ConnectionError, TimeoutError)
**Estimated Lines:** 30 lines changed  
**Dependencies:** Task 1.1, Task 1.3

### Task 3.2: Fix Model Execution Errors
**File:** `services/ollama_client.py`  
**Lines:** ~300-350  
**Changes:**
- Remove `except Exception` that wraps errors in generic Exception
- Preserve original exception types (requests.RequestException, etc.)
- Raise `ServiceError` with original exception as cause
**Estimated Lines:** 25 lines changed  
**Dependencies:** Task 1.1

### Task 3.3: Fix Engine Config Loading
**File:** `services/ollama_client.py`  
**Lines:** ~50-100  
**Changes:**
- Remove silent failure if config file doesn't exist
- Either fail-fast or explicitly return default config with warning
- Raise `FileOperationError` if config file exists but cannot be read
**Estimated Lines:** 20 lines changed  
**Dependencies:** Task 1.1, Task 1.2

---

## Task Group 4: Fix services/supabase_client.py

### Task 4.1: Fix Supabase Initialization
**File:** `services/supabase_client.py`  
**Lines:** ~25-45  
**Changes:**
- Remove silent failure if credentials are missing
- Add explicit "offline mode" if Supabase is not configured
- Raise `ConfigurationError` if Supabase is required but not configured
**Estimated Lines:** 30 lines changed  
**Dependencies:** Task 1.1

### Task 4.2: Fix Database Operation Error Handling
**File:** `services/supabase_client.py`  
**Lines:** ~100-300  
**Changes:**
- Remove `except Exception` blocks that return None or empty results
- Preserve Supabase API error types
- Raise `ServiceError` with Supabase error details
- Add dependency verification before operations
**Estimated Lines:** 50 lines changed  
**Dependencies:** Task 1.1, Task 1.2, Task 1.3

### Task 4.3: Fix Connection Testing
**File:** `services/supabase_client.py`  
**Lines:** ~40-70  
**Changes:**
- Remove `except Exception` that returns False on any error
- Distinguish between configuration errors and connection errors
- Raise appropriate exception types
**Estimated Lines:** 20 lines changed  
**Dependencies:** Task 1.1, Task 1.3

---

## Task Group 5: Fix services/processor/normalization/supabase_upload.py

### Task 5.1: Fix Supabase Initialization
**File:** `services/processor/normalization/supabase_upload.py`  
**Lines:** ~19-45  
**Changes:**
- Remove silent return of None if Supabase is not configured
- Add explicit "offline mode" flag
- Raise `ConfigurationError` if Supabase is required but not configured
**Estimated Lines:** 25 lines changed  
**Dependencies:** Task 1.1

### Task 5.2: Fix Upload Error Handling
**File:** `services/processor/normalization/supabase_upload.py`  
**Lines:** ~100-150  
**Changes:**
- Remove `except Exception` that logs and continues
- Verify Supabase client is initialized before upload
- Raise `ServiceError` with upload failure details
- Preserve Supabase API error types
**Estimated Lines:** 30 lines changed  
**Dependencies:** Task 1.1, Task 1.2

---

## Task Group 6: Fix tools/vofc_processor/vofc_processor.py

### Task 6.1: Fix File Move Error Handling
**File:** `tools/vofc_processor/vofc_processor.py`  
**Lines:** ~220-280  
**Changes:**
- Remove `except Exception` that continues after file move failure
- Verify source file exists and destination directory is writable before move
- Raise `FileOperationError` with specific details
- Implement transactional move (verify after move)
**Estimated Lines:** 40 lines changed  
**Dependencies:** Task 1.1, Task 1.2

### Task 6.2: Fix Processing Error Handling
**File:** `tools/vofc_processor/vofc_processor.py`  
**Lines:** ~160-220  
**Changes:**
- Add dependency verification before processing (Ollama, directories)
- Remove `except Exception` that continues with partial results
- Raise `DependencyError` if dependencies are missing
- Preserve processing errors with context
**Estimated Lines:** 35 lines changed  
**Dependencies:** Task 1.1, Task 1.2, Task 1.3

### Task 6.3: Fix Upload Error Handling
**File:** `tools/vofc_processor/vofc_processor.py`  
**Lines:** ~200-250  
**Changes:**
- Remove `except Exception` that logs and continues after upload failure
- Verify Supabase is available before processing (if required)
- Raise `ServiceError` if upload fails and is required
- Add explicit "offline mode" if Supabase is optional
**Estimated Lines:** 30 lines changed  
**Dependencies:** Task 1.1, Task 1.2, Task 1.3

---

## Task Group 7: Fix services/processor/processor/run_processor.py

### Task 7.1: Enhance Ollama Validation
**File:** `services/processor/processor/run_processor.py`  
**Lines:** ~50-110  
**Changes:**
- Already has early Ollama validation ✅
- Add Supabase verification if required
- Add directory verification
- Use dependency verification utility
**Estimated Lines:** 20 lines changed  
**Dependencies:** Task 1.1, Task 1.2, Task 1.3

### Task 7.2: Fix Processing Error Handling
**File:** `services/processor/processor/run_processor.py`  
**Lines:** ~150-250  
**Changes:**
- Remove `except Exception` blocks that return partial results
- Preserve original exception types
- Raise `ServiceError` with processing context
**Estimated Lines:** 30 lines changed  
**Dependencies:** Task 1.1

---

## Task Group 8: Fix services/queue_manager.py

### Task 8.1: Fix Queue File Reading
**File:** `services/queue_manager.py`  
**Lines:** ~25-35  
**Changes:**
- Remove silent return of empty list on file read error
- Verify queue file exists and is readable before reading
- Raise `FileOperationError` if file cannot be read
- Add retry logic with backoff (self-healing)
**Estimated Lines:** 40 lines changed  
**Dependencies:** Task 1.1, Task 1.2

---

## Task Group 9: Fix services/processor.py

### Task 9.1: Fix Exception Wrapping
**File:** `services/processor.py`  
**Lines:** ~45-50, ~225-230  
**Changes:**
- Remove `except Exception` that raises generic Exception
- Preserve original exception types
- Add context to exceptions (file name, operation)
**Estimated Lines:** 20 lines changed  
**Dependencies:** Task 1.1

---

## Task Group 10: Fix routes/processing.py

### Task 10.1: Fix Analytics Error Handling
**File:** `routes/processing.py`  
**Lines:** ~380-420, ~470-480  
**Changes:**
- Remove silent failure for Supabase analytics operations
- Add explicit "analytics disabled" mode if Supabase is not available
- Raise `ServiceError` if analytics are required but fail
**Estimated Lines:** 30 lines changed  
**Dependencies:** Task 1.1, Task 1.3

---

## Task Group 11: Fix server.py

### Task 11.1: Remove Error Masking in Config Validation
**File:** `server.py`  
**Lines:** ~10-20  
**Changes:**
- Remove outer `except Exception` that catches ConfigurationError
- Let `ConfigurationError` propagate (fail-fast)
- Remove warning and continue logic
**Estimated Lines:** 10 lines changed  
**Dependencies:** None

---

## Task Group 12: Fix app/api/system/progress/route.js (Frontend)

### Task 12.1: Fix Default Progress Return
**File:** `app/api/system/progress/route.js`  
**Lines:** ~100-140  
**Changes:**
- Remove return of default progress data (all zeros) on error
- Return 503 with error details instead
- Let frontend handle error state explicitly
**Estimated Lines:** 20 lines changed  
**Dependencies:** None

---

## Task Group 13: Fix app/lib/server-utils.js (Frontend)

### Task 13.1: Fix safeFetch Error Normalization
**File:** `app/lib/server-utils.js`  
**Lines:** ~150-200  
**Changes:**
- Distinguish between recoverable (timeout) and fatal (config error) failures
- Throw exceptions for fatal errors instead of returning error objects
- Preserve error types for network vs. configuration errors
**Estimated Lines:** 30 lines changed  
**Dependencies:** None

---

## Task Group 14: Add Explicit Offline Modes

### Task 14.1: Add Supabase Offline Mode
**Files:** `services/supabase_client.py`, `services/processor/normalization/supabase_upload.py`  
**Changes:**
- Add `SUPABASE_OFFLINE_MODE` configuration flag
- If offline mode, skip Supabase operations with clear logging
- If not offline mode and Supabase is required, fail-fast if unavailable
**Estimated Lines:** 40 lines changed  
**Dependencies:** Task 1.1

### Task 14.2: Add Analytics Offline Mode
**Files:** `routes/processing.py`  
**Changes:**
- Add `ANALYTICS_OFFLINE_MODE` configuration flag
- Skip analytics operations if offline mode is enabled
- Fail-fast if analytics are required but unavailable
**Estimated Lines:** 20 lines changed  
**Dependencies:** Task 1.1

---

## Testing Strategy

### Unit Tests Required:
1. Test dependency verification with missing dependencies
2. Test service health checks with unreachable services
3. Test error type preservation
4. Test fail-fast behavior

### Integration Tests Required:
1. Test Flask endpoints with missing dependencies
2. Test processor with unreachable Ollama
3. Test upload with unreachable Supabase
4. Test offline modes

### Manual Testing:
1. Start services with missing dependencies (should fail-fast)
2. Disable Supabase and verify offline mode works
3. Disable Ollama and verify error messages are clear
4. Test file operations with permission errors

---

## Risk Mitigation

### Risks:
1. **Breaking Changes:** Existing error handling may be relied upon by frontend
2. **Service Availability:** Fail-fast may cause services to not start if dependencies are temporarily unavailable
3. **Error Propagation:** Unhandled exceptions may crash services

### Mitigation:
1. **Gradual Rollout:** Fix one endpoint/service at a time, test thoroughly
2. **Offline Modes:** Add explicit offline modes for optional dependencies
3. **Error Boundaries:** Ensure Flask error handlers catch and log unhandled exceptions
4. **Monitoring:** Add logging for all fail-fast scenarios to track frequency

---

## Success Criteria

Phase 2 is complete when:
- ✅ No `except Exception: pass` patterns remain
- ✅ No `except Exception` that returns default/empty values without logging
- ✅ All critical operations verify dependencies before execution
- ✅ All exceptions preserve original types and context
- ✅ Explicit offline modes for optional features
- ✅ All services fail-fast with clear error messages if critical dependencies are missing

---

**Ready to begin Phase 2 implementation?**  
**Estimated Completion:** 3-4 days with testing

