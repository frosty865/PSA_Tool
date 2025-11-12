-- ============================================================
-- Phase 1: Core Functionality Migration
-- ============================================================
-- This script adds essential columns for VOFC Processor integration
-- Run this in Supabase SQL Editor
-- ============================================================

BEGIN;

-- ============================================================
-- 1.1 Deduplication Support
-- ============================================================

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

-- ============================================================
-- 1.2 Model Output Metadata
-- ============================================================

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

-- ============================================================
-- 5.1 Deduplication Robustness (Recommended)
-- ============================================================

-- Add constraint to enforce lowercase dedupe_key
ALTER TABLE vulnerabilities 
DROP CONSTRAINT IF EXISTS check_dedupe_key_lowercase;
ALTER TABLE vulnerabilities 
ADD CONSTRAINT check_dedupe_key_lowercase 
CHECK (dedupe_key IS NULL OR dedupe_key = lower(dedupe_key));

-- ============================================================
-- 5.2 Standard Timestamps (Recommended)
-- ============================================================

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

COMMIT;

-- ============================================================
-- Verification Queries
-- ============================================================

-- Check all new columns exist
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'vulnerabilities'
    AND column_name IN (
        'dedupe_key', 'confidence', 'impact_level', 'follow_up', 
        'standard_reference', 'created_at', 'updated_at'
    )
ORDER BY column_name;

-- Check indexes exist
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'vulnerabilities'
    AND indexname LIKE 'idx_vulnerabilities_%'
ORDER BY indexname;

-- Check constraints exist
SELECT 
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'vulnerabilities'
    AND constraint_name LIKE '%dedupe_key%'
ORDER BY constraint_name;

