-- ============================================================
-- Phase 2: Traceability & Linking Migration
-- ============================================================
-- This script adds traceability features for multi-source analysis
-- Run this in Supabase SQL Editor after Phase 1 is validated
-- ============================================================

BEGIN;

-- ============================================================
-- 2.1 Source Document Tracking
-- ============================================================

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

-- ============================================================
-- 2.2 Model Version Tracking
-- ============================================================

-- Add model_version to submissions table
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

COMMIT;

-- ============================================================
-- Verification Queries
-- ============================================================

-- Check source_document column exists
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'vulnerability_ofc_links'
    AND column_name = 'source_document';

-- Expected: 1 row

-- Check model_version column exists
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'submissions'
    AND column_name = 'model_version';

-- Expected: 1 row

-- Check indexes exist
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('vulnerability_ofc_links', 'submissions')
    AND indexname IN ('idx_vofc_links_source_document', 'idx_submissions_model_version')
ORDER BY tablename, indexname;

-- Expected: 2 rows

