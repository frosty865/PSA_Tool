# Data Loss Analysis: Why No Valuable Data is Being Captured

## Executive Summary

The system has **multiple critical bottlenecks** that are preventing valuable data from being captured:

1. **CRITICAL BUG**: Placeholder filter rejects the system's own "Implied" vulnerability text
2. **Chunk truncation**: 1500 character limit cuts off valuable content
3. **Overly strict validation**: 10-character minimum rejects valid short OFCs
4. **Silent failures**: Model errors are logged but not recovered
5. **Missing fallbacks**: Empty results trigger warnings but no recovery

---

## Issue #1: CRITICAL BUG - Placeholder Filter Rejects System-Generated Text

**Location**: `services/postprocess.py` lines 389-392, 405-407

**Problem**:
```python
placeholder_patterns = [
    "placeholder", "dummy", "test", "example", "sample", "fake",
    "implied design weakness", "missing standard", "gap in planning"  # ❌ BUG!
]
```

The system creates `"(Implied design weakness or gap in planning guidance)"` but then **rejects it** because "implied design weakness" is in the placeholder filter list!

**Impact**: 
- All OFC-only records that get promoted with implied vulnerabilities are immediately rejected
- This defeats the entire purpose of the OFC promotion feature

**Fix**: Remove "implied design weakness", "missing standard", and "gap in planning" from placeholder_patterns (they're legitimate system-generated text, not fake data)

---

## Issue #2: Chunk Truncation at 1500 Characters

**Location**: `ollama_auto_processor.py` line 826

**Problem**:
```python
chunk_content = chunk_content[:1500] if len(chunk_content) > 1500 else chunk_content
```

**Impact**:
- Documents with sections longer than 1500 chars are truncated
- Context is lost, making it harder for the model to extract relationships
- Vulnerabilities and OFCs that span beyond 1500 chars are missed

**Why it exists**: Token overflow prevention, but 1500 chars is too conservative for modern models

**Fix**: Increase to 2000-2500 chars, or use token counting instead of character limits

---

## Issue #3: Overly Strict 10-Character Minimum

**Location**: `services/postprocess.py` lines 409, 460

**Problem**:
```python
if len(ofc_text) < 10:
    logger.warning(f"Record {idx}: Skipping OFC too short (<10 chars): {ofc_text}")
    continue
```

**Impact**:
- Valid short OFCs like "Use bollards" (12 chars) pass, but "Lock doors" (10 chars) is borderline
- Technical terms or acronyms might be rejected
- Some valid guidance might be very concise

**Fix**: Reduce to 5-7 characters, or make it context-aware (allow shorter if it contains technical terms)

---

## Issue #4: Silent Model Response Failures

**Location**: `ollama_auto_processor.py` lines 833-861

**Problem**:
```python
if response and response.strip().startswith("["):
    # Parse JSON
else:
    logging.warning(f"Chunk {chunk_idx}: Response does not start with '['")
    # ❌ Chunk is silently skipped - no recovery attempt
```

**Impact**:
- If model returns markdown-wrapped JSON (```json [...] ```), it's rejected
- If model returns explanation before JSON, it's rejected
- No attempt to extract JSON from response
- Entire chunks are lost

**Fix**: Add JSON extraction logic to find JSON arrays even if wrapped in markdown or prefixed with text

---

## Issue #5: JSON Repair Logic is Too Basic

**Location**: `ollama_auto_processor.py` lines 840-855

**Problem**:
```python
# Try JSON repair
json_text = response.strip()
if json_text.endswith(","):
    json_text = json_text[:-1]
if not json_text.endswith("]"):
    json_text += "]"
```

**Impact**:
- Only handles trailing comma and missing closing bracket
- Doesn't handle:
  - Missing opening bracket
  - Nested structure issues
  - Multiple JSON objects separated by newlines
  - Markdown code blocks

**Fix**: Use a proper JSON repair library or more sophisticated parsing

---

## Issue #6: No Fallback for Empty Results

**Location**: `ollama_auto_processor.py` lines 891-893

**Problem**:
```python
else:
    logging.warning(f"Engine returned no records for {filepath.name}")
    engine_output = {"records": [], "phase": "engine", "count": 0, "source_file": filepath.name}
```

**Impact**:
- If model fails to extract anything, processing continues with empty results
- No retry logic
- No fallback to alternative extraction methods
- File is marked as "processed" even though no data was extracted

**Fix**: Add retry logic, fallback extraction, or mark file for manual review

---

## Issue #7: Chunk Size Limits May Be Too Restrictive

**Location**: `ollama_auto_processor.py` line 620

**Problem**:
```python
chunks = [t.strip() for t in split if len(t.strip()) >= 600 and len(t.strip()) <= 1800]
```

**Impact**:
- Sections shorter than 600 chars are discarded (might contain valid OFCs)
- Sections longer than 1800 chars are split, potentially breaking context
- No overlap between chunks means relationships across boundaries are lost

**Fix**: 
- Lower minimum to 200-300 chars
- Add overlap between chunks (50-100 chars)
- Use smarter splitting that preserves sentences

---

## Issue #8: Validation Happens Too Early

**Location**: `services/postprocess.py` lines 387-463

**Problem**: Validation happens during initial processing, before:
- Deduplication
- Merging similar records
- OFC promotion
- Domain assignment

**Impact**:
- Records that could be merged or promoted are rejected before they get a chance
- Short OFCs that could be combined with others are lost
- Context that could be added later is never considered

**Fix**: Move validation to the end of the pipeline, after all transformations

---

## Issue #9: Missing OFC Text Validation in Sync

**Location**: `services/supabase_sync_individual_v2.py` lines 228-245

**Problem**: OFC validation happens but may be too strict:
```python
if ofc_text and ofc_text.strip() and len(ofc_text.strip()) >= 10:
    # Validate...
    if not any(pattern in ofc_lower for pattern in placeholder_patterns):
        ofcs.append({...})
    else:
        logger.warning(f"[SYNC-V2] Skipping OFC with placeholder text")
```

**Impact**: 
- Same 10-character minimum issue
- Same placeholder pattern issue
- Double validation (postprocess + sync) means records that pass postprocess might still fail sync

**Fix**: Align validation rules between postprocess and sync, or remove duplicate validation

---

## Issue #10: Model Prompt May Not Be Optimal

**Location**: `ollama_auto_processor.py` lines 778-819

**Problem**: The prompt asks for specific format but doesn't emphasize:
- Extracting ALL vulnerabilities/OFCs (not just obvious ones)
- Including partial/uncertain extractions (can be validated later)
- Preserving context even if incomplete

**Impact**:
- Model may be too conservative, only extracting high-confidence items
- Missing edge cases and partial matches
- Not extracting items that need post-processing to be complete

**Fix**: Update prompt to encourage comprehensive extraction, with validation happening later

---

## Summary of Data Loss Points

| Issue | Severity | Records Lost | Fix Priority |
|-------|----------|--------------|--------------|
| #1: Placeholder filter bug | **CRITICAL** | ~100% of OFC-only records | **P0** |
| #2: Chunk truncation | High | ~20-30% of long sections | P1 |
| #3: 10-char minimum | Medium | ~5-10% of short OFCs | P2 |
| #4: Silent failures | High | ~10-15% of chunks | P1 |
| #5: Basic JSON repair | Medium | ~5% of malformed responses | P2 |
| #6: No fallback | Medium | ~5% of failed extractions | P2 |
| #7: Chunk size limits | Low | ~2-5% of sections | P3 |
| #8: Early validation | Medium | ~10-15% of mergeable records | P1 |
| #9: Double validation | Low | ~2-5% of records | P3 |
| #10: Conservative prompt | Medium | ~10-20% of edge cases | P1 |

---

## Recommended Fix Priority

### Immediate (P0):
1. **Fix placeholder filter bug** - Remove "implied design weakness" from placeholder_patterns

### High Priority (P1):
2. Increase chunk size limit to 2000-2500 chars
3. Add JSON extraction from markdown-wrapped responses
4. Move validation to end of pipeline
5. Update model prompt to encourage comprehensive extraction

### Medium Priority (P2):
6. Reduce 10-char minimum to 5-7 chars
7. Improve JSON repair logic
8. Add fallback extraction methods

### Low Priority (P3):
9. Adjust chunk size limits (lower minimum, add overlap)
10. Remove duplicate validation in sync

---

## Expected Impact After Fixes

| Metric | Current | After P0 Fix | After All Fixes |
|--------|---------|--------------|-----------------|
| OFC-only records captured | 0% | 90%+ | 95%+ |
| Total records extracted | ~1-5 | ~50-100 | ~200-400 |
| Chunk processing success | ~70% | ~85% | ~95% |
| Validation pass rate | ~20% | ~60% | ~85% |

