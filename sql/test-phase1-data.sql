-- ============================================================
-- Phase 1 Data Verification Queries
-- ============================================================
-- Run these queries to verify Phase 1 columns are being populated
-- ============================================================

-- 1. Check recent records have new columns populated
SELECT 
    vulnerability,
    dedupe_key,
    confidence,
    impact_level,
    follow_up,
    standard_reference,
    created_at,
    updated_at
FROM vulnerabilities
WHERE created_at >= NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 10;

-- Expected: Should see records with:
-- - dedupe_key (40-char lowercase hash)
-- - confidence (High/Medium/Low)
-- - impact_level (High/Moderate/Low)
-- - follow_up (true/false)
-- - created_at and updated_at timestamps

-- 2. Check deduplication is working (no duplicate dedupe_keys)
SELECT 
    dedupe_key,
    COUNT(*) as count,
    STRING_AGG(vulnerability, ' | ') as vulnerabilities
FROM vulnerabilities
WHERE dedupe_key IS NOT NULL
GROUP BY dedupe_key
HAVING COUNT(*) > 1
ORDER BY count DESC;

-- Expected: 0 rows (no duplicates)

-- 3. Check lowercase constraint is working
SELECT 
    dedupe_key,
    vulnerability
FROM vulnerabilities
WHERE dedupe_key IS NOT NULL
  AND dedupe_key != lower(dedupe_key)
LIMIT 10;

-- Expected: 0 rows (all dedupe_keys should be lowercase)

-- 4. Check confidence values distribution
SELECT 
    confidence,
    COUNT(*) as count
FROM vulnerabilities
WHERE confidence IS NOT NULL
GROUP BY confidence
ORDER BY count DESC;

-- Expected: Should see High, Medium, Low values

-- 5. Check impact_level values distribution
SELECT 
    impact_level,
    COUNT(*) as count
FROM vulnerabilities
WHERE impact_level IS NOT NULL
GROUP BY impact_level
ORDER BY count DESC;

-- Expected: Should see High, Moderate, Low values

-- 6. Check follow_up flag usage
SELECT 
    follow_up,
    COUNT(*) as count
FROM vulnerabilities
GROUP BY follow_up;

-- Expected: Should see true and false values

-- 7. Check updated_at trigger is working
-- Update a record and check if updated_at changes
SELECT 
    id,
    vulnerability,
    created_at,
    updated_at,
    CASE 
        WHEN created_at = updated_at THEN 'Never updated'
        ELSE 'Has been updated'
    END as update_status
FROM vulnerabilities
ORDER BY updated_at DESC
LIMIT 10;

-- Expected: updated_at should be >= created_at

-- 8. Summary statistics
SELECT 
    COUNT(*) as total_vulnerabilities,
    COUNT(dedupe_key) as with_dedupe_key,
    COUNT(confidence) as with_confidence,
    COUNT(impact_level) as with_impact_level,
    COUNT(CASE WHEN follow_up = TRUE THEN 1 END) as follow_up_count,
    COUNT(standard_reference) as with_reference,
    MIN(created_at) as oldest_record,
    MAX(created_at) as newest_record
FROM vulnerabilities;

-- Expected: Should show counts for each new column

