-- ============================================================================
-- Add Source Metadata Columns to Supabase Tables
-- ============================================================================
-- Purpose: Add source_file, source_page, and source_excerpt columns to
--          support page-based extraction with full traceability
-- Date: 2025-11-07
-- ============================================================================

-- ============================================================================
-- 1. Submission Tables (Primary - Required for new processing)
-- ============================================================================

-- Add columns to submission_vulnerabilities
ALTER TABLE submission_vulnerabilities
ADD COLUMN IF NOT EXISTS source_file text,
ADD COLUMN IF NOT EXISTS source_page integer,
ADD COLUMN IF NOT EXISTS source_excerpt text;

-- Add columns to submission_options_for_consideration
ALTER TABLE submission_options_for_consideration
ADD COLUMN IF NOT EXISTS source_file text,
ADD COLUMN IF NOT EXISTS source_page integer,
ADD COLUMN IF NOT EXISTS source_excerpt text;

-- ============================================================================
-- 2. Production Tables (Optional - For promoted records)
-- ============================================================================

-- Add columns to vulnerabilities (production)
ALTER TABLE vulnerabilities
ADD COLUMN IF NOT EXISTS source_file text,
ADD COLUMN IF NOT EXISTS source_page integer,
ADD COLUMN IF NOT EXISTS source_excerpt text;

-- Add columns to options_for_consideration (production)
ALTER TABLE options_for_consideration
ADD COLUMN IF NOT EXISTS source_file text,
ADD COLUMN IF NOT EXISTS source_page integer,
ADD COLUMN IF NOT EXISTS source_excerpt text;

-- ============================================================================
-- 3. Add Indexes for Performance
-- ============================================================================

-- Indexes on submission tables for filtering by source
CREATE INDEX IF NOT EXISTS idx_submission_vuln_source_file 
    ON submission_vulnerabilities(source_file);
CREATE INDEX IF NOT EXISTS idx_submission_vuln_source_page 
    ON submission_vulnerabilities(source_page);

CREATE INDEX IF NOT EXISTS idx_submission_ofc_source_file 
    ON submission_options_for_consideration(source_file);
CREATE INDEX IF NOT EXISTS idx_submission_ofc_source_page 
    ON submission_options_for_consideration(source_page);

-- Indexes on production tables
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_source_file 
    ON vulnerabilities(source_file);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_source_page 
    ON vulnerabilities(source_page);

CREATE INDEX IF NOT EXISTS idx_options_source_file 
    ON options_for_consideration(source_file);
CREATE INDEX IF NOT EXISTS idx_options_source_page 
    ON options_for_consideration(source_page);

-- ============================================================================
-- 4. Add Comments for Documentation
-- ============================================================================

COMMENT ON COLUMN submission_vulnerabilities.source_file IS 
    'Filename of the source document (e.g., ufc_4_010_01_2018_c1.pdf)';
COMMENT ON COLUMN submission_vulnerabilities.source_page IS 
    'Page number in the source document where this vulnerability was found';
COMMENT ON COLUMN submission_vulnerabilities.source_excerpt IS 
    'First 300 characters of the chunk containing this vulnerability';

COMMENT ON COLUMN submission_options_for_consideration.source_file IS 
    'Filename of the source document (e.g., ufc_4_010_01_2018_c1.pdf)';
COMMENT ON COLUMN submission_options_for_consideration.source_page IS 
    'Page number in the source document where this OFC was found';
COMMENT ON COLUMN submission_options_for_consideration.source_excerpt IS 
    'First 300 characters of the chunk containing this OFC';

COMMENT ON COLUMN vulnerabilities.source_file IS 
    'Filename of the source document (for production records)';
COMMENT ON COLUMN vulnerabilities.source_page IS 
    'Page number in the source document (for production records)';
COMMENT ON COLUMN vulnerabilities.source_excerpt IS 
    'Source excerpt (for production records)';

COMMENT ON COLUMN options_for_consideration.source_file IS 
    'Filename of the source document (for production records)';
COMMENT ON COLUMN options_for_consideration.source_page IS 
    'Page number in the source document (for production records)';
COMMENT ON COLUMN options_for_consideration.source_excerpt IS 
    'Source excerpt (for production records)';

-- ============================================================================
-- Verification Query
-- ============================================================================
-- Run this to verify the columns were added:
-- 
-- SELECT 
--     table_name, 
--     column_name, 
--     data_type 
-- FROM information_schema.columns 
-- WHERE table_name IN (
--     'submission_vulnerabilities',
--     'submission_options_for_consideration',
--     'vulnerabilities',
--     'options_for_consideration'
-- )
-- AND column_name IN ('source_file', 'source_page', 'source_excerpt')
-- ORDER BY table_name, column_name;

