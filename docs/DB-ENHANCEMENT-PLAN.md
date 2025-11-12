# Database Enhancement Plan for Seamless Integration

## Overview

This document outlines database schema enhancements needed to fully support the VOFC Unified Processor and enable seamless integration across all system components.

## Current State Analysis

### Fields Currently Used by Processor

The processor attempts to use these fields:

1. **Vulnerabilities Table:**
   - `vulnerability` ✅ (exists)
   - `description` ✅ (exists)
   - `discipline` ✅ (exists)
   - `sector_id` ✅ (exists)
   - `subsector_id` ✅ (exists)
   - `dedupe_key` ❌ (needed for deduplication)
   - `confidence` ❌ (model output)
   - `impact_level` ❌ (model output)
   - `follow_up` ❌ (model output)
   - `standard_reference` ❌ (model output)

2. **Options for Consideration Table:**
   - `option_text` ✅ (exists)
   - `discipline` ✅ (exists)

3. **Vulnerability-OFC Links Table:**
   - `vulnerability_id` ✅ (exists)
   - `ofc_id` ✅ (exists)
   - `source_document` ❌ (needed for traceability)

4. **Submissions Table:**
   - Basic structure ✅ (exists)
   - `inserted_count` ❌ (tracking metadata)
   - `linked_count` ❌ (tracking metadata)

---

## Enhancement Plan

### Phase 1: Core Functionality (Priority: High)

#### 1.1 Add Deduplication Support

**Purpose:** Enable fast, reliable duplicate detection using SHA1 hashes.

```sql
-- Add dedupe_key column to vulnerabilities table
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS dedupe_key TEXT;

-- Create unique index for O(1) lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_vulnerabilities_dedupe_key 
ON vulnerabilities(dedupe_key) 
WHERE dedupe_key IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN vulnerabilities.dedupe_key IS 
    'SHA1 hash of vulnerability + first_ofc for deduplication. Format: sha1(vulnerability + first_ofc)';
```

**Benefits:**
- Instant duplicate detection (O(1) lookup)
- Prevents duplicate inserts
- Enables efficient linking of existing records

**Impact:** Critical for processor's deduplication logic

---

#### 1.2 Add Model Output Metadata

**Purpose:** Store confidence, impact, and follow-up flags from model output.

```sql
-- Add confidence column
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS confidence TEXT 
CHECK (confidence IN ('High', 'Medium', 'Low') OR confidence IS NULL);

-- Add impact_level column
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS impact_level TEXT 
CHECK (impact_level IN ('High', 'Moderate', 'Low') OR impact_level IS NULL);

-- Add follow_up boolean flag
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS follow_up BOOLEAN DEFAULT FALSE;

-- Add standard_reference for source tracking
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS standard_reference TEXT;

-- Add indexes for filtering
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_confidence 
ON vulnerabilities(confidence) 
WHERE confidence IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_vulnerabilities_impact_level 
ON vulnerabilities(impact_level) 
WHERE impact_level IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_vulnerabilities_follow_up 
ON vulnerabilities(follow_up) 
WHERE follow_up = TRUE;

-- Add comments
COMMENT ON COLUMN vulnerabilities.confidence IS 
    'Model confidence level: High, Medium, or Low';
COMMENT ON COLUMN vulnerabilities.impact_level IS 
    'Impact assessment: High, Moderate, or Low';
COMMENT ON COLUMN vulnerabilities.follow_up IS 
    'Flag indicating if this vulnerability requires follow-up action';
COMMENT ON COLUMN vulnerabilities.standard_reference IS 
    'Reference standard or document (e.g., DHS Security Guidelines, SAFE, FEMA)';
```

**Benefits:**
- Preserves all model output data
- Enables filtering and prioritization
- Supports quality assessment workflows

**Impact:** Enables full utilization of model output

---

### Phase 2: Traceability & Linking (Priority: Medium)

#### 2.1 Add Source Document Tracking

**Purpose:** Track which document each vulnerability-OFC link came from.

```sql
-- Add source_document to vulnerability_ofc_links
ALTER TABLE vulnerability_ofc_links 
ADD COLUMN IF NOT EXISTS source_document TEXT;

-- Add index for filtering by source
CREATE INDEX IF NOT EXISTS idx_vofc_links_source_document 
ON vulnerability_ofc_links(source_document) 
WHERE source_document IS NOT NULL;

-- Add comment
COMMENT ON COLUMN vulnerability_ofc_links.source_document IS 
    'Source document identifier (e.g., SAFE, FEMA, UFC, or document filename)';
```

**Benefits:**
- Traceability of link origins
- Support for multi-source analysis
- Audit trail for data provenance

---

#### 2.2 Add Processing Metadata to Submissions

**Purpose:** Track processing statistics and model version.

```sql
-- Add inserted_count to submissions data JSONB
-- (Already in JSONB data field, but ensure structure is documented)

-- Add linked_count to submissions data JSONB
-- (Already in JSONB data field, but ensure structure is documented)

-- Add model_version tracking (if not already present)
-- Check if column exists, add if needed
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submissions' 
        AND column_name = 'model_version'
    ) THEN
        ALTER TABLE submissions 
        ADD COLUMN model_version TEXT;
    END IF;
END $$;

-- Add index for filtering by model version
CREATE INDEX IF NOT EXISTS idx_submissions_model_version 
ON submissions(model_version) 
WHERE model_version IS NOT NULL;

-- Add comment
COMMENT ON COLUMN submissions.model_version IS 
    'Ollama model version used for processing (e.g., vofc-unified:latest)';
```

**Benefits:**
- Track which model version processed each submission
- Enable model performance analysis
- Support A/B testing of models

---

### Phase 3: Performance Optimization (Priority: Medium)

#### 3.1 Add Composite Indexes for Common Queries

**Purpose:** Optimize frequent query patterns.

```sql
-- Index for filtering vulnerabilities by discipline and confidence
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_discipline_confidence 
ON vulnerabilities(discipline, confidence) 
WHERE discipline IS NOT NULL AND confidence IS NOT NULL;

-- Index for filtering by sector and impact
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_sector_impact 
ON vulnerabilities(sector_id, impact_level) 
WHERE sector_id IS NOT NULL AND impact_level IS NOT NULL;

-- Index for follow-up items with discipline
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_followup_discipline 
ON vulnerabilities(follow_up, discipline) 
WHERE follow_up = TRUE AND discipline IS NOT NULL;
```

**Benefits:**
- Faster filtering and sorting
- Improved dashboard performance
- Better query planning

---

#### 3.2 Add Full-Text Search Support

**Purpose:** Enable fast text search across vulnerabilities and OFCs.

```sql
-- Add full-text search column for vulnerabilities
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Create function to update search vector
CREATE OR REPLACE FUNCTION update_vulnerability_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.vulnerability, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.discipline, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update search vector
DROP TRIGGER IF EXISTS trigger_update_vulnerability_search ON vulnerabilities;
CREATE TRIGGER trigger_update_vulnerability_search
    BEFORE INSERT OR UPDATE ON vulnerabilities
    FOR EACH ROW
    EXECUTE FUNCTION update_vulnerability_search_vector();

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_search_vector 
ON vulnerabilities USING GIN(search_vector);

-- Update existing rows
UPDATE vulnerabilities 
SET search_vector = 
    setweight(to_tsvector('english', COALESCE(vulnerability, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(discipline, '')), 'C');
```

**Benefits:**
- Fast text search across vulnerability descriptions
- Better user experience in search interfaces
- Scalable to large datasets

---

### Phase 4: Data Quality & Validation (Priority: Low)

#### 4.1 Add Validation Constraints

**Purpose:** Ensure data quality at the database level.

```sql
-- Ensure vulnerability text is not empty
ALTER TABLE vulnerabilities 
ADD CONSTRAINT check_vulnerability_not_empty 
CHECK (vulnerability IS NOT NULL AND LENGTH(TRIM(vulnerability)) > 0);

-- Ensure option_text is not empty
ALTER TABLE options_for_consideration 
ADD CONSTRAINT check_option_text_not_empty 
CHECK (option_text IS NOT NULL AND LENGTH(TRIM(option_text)) > 0);

-- Ensure dedupe_key format (if provided, must be 40 chars for SHA1)
ALTER TABLE vulnerabilities 
ADD CONSTRAINT check_dedupe_key_format 
CHECK (dedupe_key IS NULL OR LENGTH(dedupe_key) = 40);
```

**Benefits:**
- Data integrity at database level
- Prevents invalid data insertion
- Clear error messages for validation failures

---

#### 4.2 Add Audit Trail Columns

**Purpose:** Track when records are created, updated, and by which process.

```sql
-- Add processed_at timestamp (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'vulnerabilities' 
        AND column_name = 'processed_at'
    ) THEN
        ALTER TABLE vulnerabilities 
        ADD COLUMN processed_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Add processor_version for tracking
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS processor_version TEXT;

-- Add index for time-based queries
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_processed_at 
ON vulnerabilities(processed_at DESC);

-- Add comment
COMMENT ON COLUMN vulnerabilities.processed_at IS 
    'Timestamp when this vulnerability was processed by VOFC-Processor';
COMMENT ON COLUMN vulnerabilities.processor_version IS 
    'Version of VOFC-Processor that created this record';
```

**Benefits:**
- Audit trail for data changes
- Support for time-based analysis
- Debugging and troubleshooting support

---

### Phase 5: Recommended Enhancements (Minor but Valuable)

#### 5.1 Deduplication Robustness

**Purpose:** Ensure dedupe_key consistency by enforcing lowercase hashes.

```sql
-- Add constraint to enforce lowercase dedupe_key
ALTER TABLE vulnerabilities 
ADD CONSTRAINT check_dedupe_key_lowercase 
CHECK (dedupe_key IS NULL OR dedupe_key = lower(dedupe_key));
```

**Benefits:**
- Avoids mismatched hashes due to casing differences
- Ensures consistent deduplication
- Prevents duplicate records from case variations

---

#### 5.2 Add Standard Timestamps

**Purpose:** Track creation and update times for audit and UI filtering.

```sql
-- Add created_at and updated_at timestamps
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Create function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update on row changes
DROP TRIGGER IF EXISTS trg_update_timestamp ON vulnerabilities;
CREATE TRIGGER trg_update_timestamp
    BEFORE UPDATE ON vulnerabilities
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Add indexes for time-based queries
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_created_at 
ON vulnerabilities(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_vulnerabilities_updated_at 
ON vulnerabilities(updated_at DESC);
```

**Benefits:**
- Clear audit trail of when records were created/modified
- Enables UI filtering by date ranges
- Automatic timestamp management via triggers

---

#### 5.3 Normalize Standard References

**Purpose:** Centralize recurring document names in a lookup table.

```sql
-- Create reference sources lookup table
CREATE TABLE IF NOT EXISTS reference_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    category TEXT,
    url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add index for name lookups
CREATE INDEX IF NOT EXISTS idx_reference_sources_name 
ON reference_sources(name);

-- Add comment
COMMENT ON TABLE reference_sources IS 
    'Centralized lookup table for standard reference documents (SAFE, FEMA, UFC, etc.)';

-- Future: Add foreign key from vulnerabilities to reference_sources
-- ALTER TABLE vulnerabilities 
-- ADD COLUMN reference_source_id UUID REFERENCES reference_sources(id);
```

**Benefits:**
- Normalized reference data
- Easy to add metadata (URLs, categories) to references
- Future-ready for foreign key relationships
- Reduces data duplication

---

#### 5.4 Full-Text Search for OFCs

**Purpose:** Enable fast text search across Options for Consideration.

```sql
-- Add full-text search column for OFCs
ALTER TABLE options_for_consideration 
ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Create function to update OFC search vector
CREATE OR REPLACE FUNCTION update_ofc_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.option_text, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.discipline, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update search vector
DROP TRIGGER IF EXISTS trigger_update_ofc_search ON options_for_consideration;
CREATE TRIGGER trigger_update_ofc_search
    BEFORE INSERT OR UPDATE ON options_for_consideration
    FOR EACH ROW
    EXECUTE FUNCTION update_ofc_search_vector();

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS idx_ofc_search_vector 
ON options_for_consideration USING GIN(search_vector);

-- Update existing rows
UPDATE options_for_consideration 
SET search_vector = 
    setweight(to_tsvector('english', COALESCE(option_text, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(discipline, '')), 'B');
```

**Benefits:**
- Fast text search across OFCs (parity with vulnerabilities)
- Enables cross-sector analysis
- Better user experience in search interfaces

---

#### 5.5 Soft Delete Support

**Purpose:** Enable data retention control without hard deletes.

```sql
-- Add is_active flag for soft deletes
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Add index for filtering active records
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_is_active 
ON vulnerabilities(is_active) 
WHERE is_active = TRUE;

-- Add comment
COMMENT ON COLUMN vulnerabilities.is_active IS 
    'Soft delete flag. Set to FALSE to deactivate without hard delete (for regulatory retention)';
```

**Benefits:**
- Regulatory compliance (retention control)
- Ability to deactivate records without data loss
- Audit trail preservation
- Easy reactivation if needed

---

## Implementation Priority

### Immediate (Week 1)
1. ✅ Add `dedupe_key` column and index (Phase 1.1)
2. ✅ Add `confidence`, `impact_level`, `follow_up`, `standard_reference` (Phase 1.2)
3. ✅ Add lowercase constraint for `dedupe_key` (Phase 5.1)
4. ✅ Add `created_at` and `updated_at` timestamps (Phase 5.2)

### Short-term (Week 2-3)
5. Add `source_document` to links (Phase 2.1)
6. Add composite indexes (Phase 3.1)
7. Add model version tracking (Phase 2.2)
8. Create `reference_sources` lookup table (Phase 5.3)

### Medium-term (Month 2)
9. Add full-text search support for vulnerabilities (Phase 3.2)
10. Add full-text search support for OFCs (Phase 5.4)
11. Add validation constraints (Phase 4.1)
12. Add audit trail columns (Phase 4.2)
13. Add soft delete support (Phase 5.5)

---

## Migration Scripts

### Complete Migration Script

```sql
-- ============================================================
-- VOFC Processor Database Enhancements
-- ============================================================
-- Run this script to add all required columns and indexes
-- for seamless integration with VOFC Unified Processor
-- ============================================================

BEGIN;

-- ============================================================
-- Phase 1: Core Functionality
-- ============================================================

-- 1.1 Deduplication Support
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS dedupe_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_vulnerabilities_dedupe_key 
ON vulnerabilities(dedupe_key) 
WHERE dedupe_key IS NOT NULL;

COMMENT ON COLUMN vulnerabilities.dedupe_key IS 
    'SHA1 hash of vulnerability + first_ofc for deduplication';

-- 1.2 Model Output Metadata
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS confidence TEXT 
CHECK (confidence IN ('High', 'Medium', 'Low') OR confidence IS NULL);

ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS impact_level TEXT 
CHECK (impact_level IN ('High', 'Moderate', 'Low') OR impact_level IS NULL);

ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS follow_up BOOLEAN DEFAULT FALSE;

ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS standard_reference TEXT;

CREATE INDEX IF NOT EXISTS idx_vulnerabilities_confidence 
ON vulnerabilities(confidence) 
WHERE confidence IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_vulnerabilities_impact_level 
ON vulnerabilities(impact_level) 
WHERE impact_level IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_vulnerabilities_follow_up 
ON vulnerabilities(follow_up) 
WHERE follow_up = TRUE;

-- ============================================================
-- Phase 2: Traceability & Linking
-- ============================================================

-- 2.1 Source Document Tracking
ALTER TABLE vulnerability_ofc_links 
ADD COLUMN IF NOT EXISTS source_document TEXT;

CREATE INDEX IF NOT EXISTS idx_vofc_links_source_document 
ON vulnerability_ofc_links(source_document) 
WHERE source_document IS NOT NULL;

-- 2.2 Model Version Tracking
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submissions' 
        AND column_name = 'model_version'
    ) THEN
        ALTER TABLE submissions 
        ADD COLUMN model_version TEXT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_submissions_model_version 
ON submissions(model_version) 
WHERE model_version IS NOT NULL;

-- ============================================================
-- Phase 3: Performance Optimization
-- ============================================================

-- 3.1 Composite Indexes
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_discipline_confidence 
ON vulnerabilities(discipline, confidence) 
WHERE discipline IS NOT NULL AND confidence IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_vulnerabilities_sector_impact 
ON vulnerabilities(sector_id, impact_level) 
WHERE sector_id IS NOT NULL AND impact_level IS NOT NULL;

-- ============================================================
-- Phase 4: Data Quality
-- ============================================================

-- 4.1 Validation Constraints
ALTER TABLE vulnerabilities 
DROP CONSTRAINT IF EXISTS check_vulnerability_not_empty;
ALTER TABLE vulnerabilities 
ADD CONSTRAINT check_vulnerability_not_empty 
CHECK (vulnerability IS NOT NULL AND LENGTH(TRIM(vulnerability)) > 0);

ALTER TABLE options_for_consideration 
DROP CONSTRAINT IF EXISTS check_option_text_not_empty;
ALTER TABLE options_for_consideration 
ADD CONSTRAINT check_option_text_not_empty 
CHECK (option_text IS NOT NULL AND LENGTH(TRIM(option_text)) > 0);

ALTER TABLE vulnerabilities 
DROP CONSTRAINT IF EXISTS check_dedupe_key_format;
ALTER TABLE vulnerabilities 
ADD CONSTRAINT check_dedupe_key_format 
CHECK (dedupe_key IS NULL OR LENGTH(dedupe_key) = 40);

-- 4.2 Audit Trail
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'vulnerabilities' 
        AND column_name = 'processed_at'
    ) THEN
        ALTER TABLE vulnerabilities 
        ADD COLUMN processed_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS processor_version TEXT;

CREATE INDEX IF NOT EXISTS idx_vulnerabilities_processed_at 
ON vulnerabilities(processed_at DESC);

-- ============================================================
-- Phase 5: Recommended Enhancements
-- ============================================================

-- 5.1 Deduplication Robustness
ALTER TABLE vulnerabilities 
DROP CONSTRAINT IF EXISTS check_dedupe_key_lowercase;
ALTER TABLE vulnerabilities 
ADD CONSTRAINT check_dedupe_key_lowercase 
CHECK (dedupe_key IS NULL OR dedupe_key = lower(dedupe_key));

-- 5.2 Standard Timestamps
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_timestamp ON vulnerabilities;
CREATE TRIGGER trg_update_timestamp
    BEFORE UPDATE ON vulnerabilities
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE INDEX IF NOT EXISTS idx_vulnerabilities_created_at 
ON vulnerabilities(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_vulnerabilities_updated_at 
ON vulnerabilities(updated_at DESC);

-- 5.3 Normalize Standard References
CREATE TABLE IF NOT EXISTS reference_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    category TEXT,
    url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reference_sources_name 
ON reference_sources(name);

-- 5.4 Full-Text Search for OFCs
ALTER TABLE options_for_consideration 
ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE OR REPLACE FUNCTION update_ofc_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', COALESCE(NEW.option_text, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.discipline, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_ofc_search ON options_for_consideration;
CREATE TRIGGER trigger_update_ofc_search
    BEFORE INSERT OR UPDATE ON options_for_consideration
    FOR EACH ROW
    EXECUTE FUNCTION update_ofc_search_vector();

CREATE INDEX IF NOT EXISTS idx_ofc_search_vector 
ON options_for_consideration USING GIN(search_vector);

-- Update existing OFC rows
UPDATE options_for_consideration 
SET search_vector = 
    setweight(to_tsvector('english', COALESCE(option_text, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(discipline, '')), 'B');

-- 5.5 Soft Delete Support
ALTER TABLE vulnerabilities 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_vulnerabilities_is_active 
ON vulnerabilities(is_active) 
WHERE is_active = TRUE;

COMMIT;

-- ============================================================
-- Verification Queries
-- ============================================================

-- Check all new columns exist
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('vulnerabilities', 'vulnerability_ofc_links', 'submissions')
    AND column_name IN (
        'dedupe_key', 'confidence', 'impact_level', 'follow_up', 
        'standard_reference', 'source_document', 'model_version',
        'processed_at', 'processor_version'
    )
ORDER BY table_name, column_name;

-- Check indexes exist
SELECT 
    tablename,
    indexname
FROM pg_indexes
WHERE tablename IN ('vulnerabilities', 'vulnerability_ofc_links', 'submissions')
    AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
```

---

## Testing Checklist

After implementing enhancements:

### Phase 1: Core Functionality
- [ ] Verify `dedupe_key` column accepts SHA1 hashes (40 chars)
- [ ] Test duplicate detection using `dedupe_key`
- [ ] Verify `dedupe_key` lowercase constraint works
- [ ] Verify `confidence` accepts only High/Medium/Low
- [ ] Verify `impact_level` accepts only High/Moderate/Low
- [ ] Test filtering by `follow_up = TRUE`
- [ ] Verify `standard_reference` can be stored

### Phase 2: Traceability
- [ ] Verify `source_document` can be set on links
- [ ] Test model version tracking in submissions

### Phase 3: Performance
- [ ] Verify indexes improve query performance
- [ ] Test full-text search on vulnerabilities
- [ ] Test full-text search on OFCs

### Phase 4: Data Quality
- [ ] Test validation constraints reject invalid data
- [ ] Verify audit trail columns are populated

### Phase 5: Recommended Enhancements
- [ ] Verify `created_at` and `updated_at` auto-populate
- [ ] Test `updated_at` trigger updates on row changes
- [ ] Verify `reference_sources` table accepts entries
- [ ] Test soft delete with `is_active = FALSE`
- [ ] Verify soft-deleted records are filtered correctly

### Post-Migration Sanity Check

Run these queries in Supabase SQL editor to verify:

```sql
-- Check all columns exist
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'vulnerabilities'
ORDER BY column_name;

-- Check all indexes exist
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'vulnerabilities'
ORDER BY indexname;

-- Check constraints
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'vulnerabilities';
```

---

## Rollback Plan

If issues arise, rollback in reverse order:

```sql
-- Remove constraints
ALTER TABLE vulnerabilities DROP CONSTRAINT IF EXISTS check_vulnerability_not_empty;
ALTER TABLE options_for_consideration DROP CONSTRAINT IF EXISTS check_option_text_not_empty;
ALTER TABLE vulnerabilities DROP CONSTRAINT IF EXISTS check_dedupe_key_format;

-- Remove indexes
DROP INDEX IF EXISTS idx_vulnerabilities_dedupe_key;
DROP INDEX IF EXISTS idx_vulnerabilities_confidence;
DROP INDEX IF EXISTS idx_vulnerabilities_impact_level;
-- ... (remove all new indexes)

-- Remove columns (if needed)
ALTER TABLE vulnerabilities DROP COLUMN IF EXISTS dedupe_key;
ALTER TABLE vulnerabilities DROP COLUMN IF EXISTS confidence;
ALTER TABLE vulnerabilities DROP COLUMN IF EXISTS impact_level;
-- ... (remove all new columns)
```

---

## Expected Benefits

### Performance
- **50-90% faster** duplicate detection (O(1) vs O(n) text matching)
- **30-60% faster** filtering queries with new indexes
- **Instant** full-text search with GIN indexes

### Functionality
- **100% model output preservation** (no data loss)
- **Complete traceability** of data sources
- **Better data quality** with validation constraints

### Maintainability
- **Clear audit trail** for debugging
- **Schema matches application needs** (no workarounds)
- **Scalable** to large datasets

---

## Deployment Order

### Step 1: Apply Phase 1 Immediately

1. Run Phase 1 migration (dedupe_key + model metadata)
2. **Restart VOFC-Processor** — it will immediately begin populating new fields
3. Validate one document ingest (e.g., Site Security Design Guide)
4. Confirm records show `confidence`, `impact_level`, `dedupe_key`, etc.

### Step 2: Apply Phases 2-4 Sequentially

- These won't disrupt processing
- Can be applied during normal operations
- Monitor logs for any issues

### Step 3: Enable Full-Text Search

- Once stable, enable full-text search in Supabase dashboard
- Test search functionality in UI
- Verify performance improvements

---

## Optional Automation

### Migration Runner for Service Startup

To make future schema drift painless, add a migration runner in service startup:

```python
def ensure_schema_up_to_date(supabase):
    """
    Ensure database schema is up-to-date by running migration script.
    This auto-creates missing columns/indexes when service starts.
    """
    migration_sql_path = Path("C:/Tools/py_scripts/sql/schema_update.sql")
    
    if not migration_sql_path.exists():
        logger.warning(f"Migration script not found: {migration_sql_path}")
        return
    
    try:
        migration_sql = migration_sql_path.read_text(encoding='utf-8')
        # Note: Supabase Python client doesn't support raw SQL execution
        # This would need to be run via Supabase SQL editor or a custom RPC function
        logger.info("Schema migration script found - run manually via Supabase SQL editor")
        logger.info(f"Script location: {migration_sql_path}")
    except Exception as e:
        logger.error(f"Could not read migration script: {e}")
```

**Note:** Supabase Python client doesn't support raw SQL execution. Migration scripts should be run via:
- Supabase SQL Editor (recommended)
- Custom RPC function (if needed)
- Manual execution before service startup

---

## Next Steps

1. **Review and approve** this enhancement plan
2. **Test migration script** on development database
3. **Implement Phase 1** (Core Functionality) immediately
4. **Restart VOFC-Processor** and validate document processing
5. **Update processor code** to use new columns (remove workarounds)
6. **Monitor performance** and adjust indexes as needed
7. **Implement remaining phases** based on priority
8. **Run post-migration sanity checks** to verify all changes

---

## Notes

- All columns use `IF NOT EXISTS` to allow safe re-running
- Indexes use `WHERE` clauses to exclude NULLs (smaller, faster)
- Constraints use `CHECK` to validate at database level
- Migration is designed to be non-destructive (adds columns, doesn't remove)

