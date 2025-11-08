-- ============================================================================
-- Add Severity Level Columns to Supabase Tables
-- ============================================================================
-- Purpose: Add severity_level column to support DHS-style matrix surveys
--          and other documents with explicit severity classifications
-- Date: 2025-01-XX
-- ============================================================================
-- 
-- Severity levels supported:
-- - "Very Low"
-- - "Low"
-- - "Medium"
-- - "High"
-- - "Very High"
--
-- This column is optional (nullable) to maintain backward compatibility
-- ============================================================================

-- ============================================================================
-- 1. Submission Tables
-- ============================================================================

-- Add severity_level to submission_vulnerabilities
ALTER TABLE submission_vulnerabilities
ADD COLUMN IF NOT EXISTS severity_level text;

-- Add comment
COMMENT ON COLUMN submission_vulnerabilities.severity_level IS 
    'Severity level classification: Very Low, Low, Medium, High, Very High. Used for DHS-style matrix surveys and other structured documents.';

-- ============================================================================
-- 2. Production Tables
-- ============================================================================

-- Add severity_level to vulnerabilities (production)
ALTER TABLE vulnerabilities
ADD COLUMN IF NOT EXISTS severity_level text;

-- Add comment
COMMENT ON COLUMN vulnerabilities.severity_level IS 
    'Severity level classification: Very Low, Low, Medium, High, Very High. Copied from submission when approved.';

-- ============================================================================
-- 3. Add Indexes for Performance (Optional)
-- ============================================================================
-- Indexes allow fast filtering and sorting by severity level

-- Index on submission table
CREATE INDEX IF NOT EXISTS idx_submission_vuln_severity_level 
    ON submission_vulnerabilities(severity_level)
    WHERE severity_level IS NOT NULL;

-- Index on production table
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_severity_level 
    ON vulnerabilities(severity_level)
    WHERE severity_level IS NOT NULL;

-- ============================================================================
-- 4. Optional: Add Check Constraint for Valid Values
-- ============================================================================
-- Uncomment if you want to enforce valid severity levels at the database level

-- ALTER TABLE submission_vulnerabilities
-- ADD CONSTRAINT check_severity_level 
-- CHECK (severity_level IS NULL OR severity_level IN ('Very Low', 'Low', 'Medium', 'High', 'Very High'));

-- ALTER TABLE vulnerabilities
-- ADD CONSTRAINT check_severity_level_production 
-- CHECK (severity_level IS NULL OR severity_level IN ('Very Low', 'Low', 'Medium', 'High', 'Very High'));

-- ============================================================================
-- Verification Query
-- ============================================================================
-- Run this to verify the columns were added:
-- 
-- SELECT 
--     table_name, 
--     column_name, 
--     data_type,
--     is_nullable
-- FROM information_schema.columns 
-- WHERE table_name IN (
--     'submission_vulnerabilities',
--     'vulnerabilities'
-- )
-- AND column_name = 'severity_level'
-- ORDER BY table_name;

