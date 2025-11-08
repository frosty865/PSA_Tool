-- Update Submission Tables to Match Submitted Data
-- This script adds missing columns and updates constraints to match what's actually being submitted

-- ============================================================================
-- 1. Update submissions table
-- ============================================================================

-- Add missing columns that are being submitted but may not exist
DO $$ 
BEGIN
    -- Add parser_version column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submissions' AND column_name = 'parser_version'
    ) THEN
        ALTER TABLE submissions ADD COLUMN parser_version TEXT;
        COMMENT ON COLUMN submissions.parser_version IS 'Version of the parser used to process this submission';
    END IF;

    -- Add engine_version column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submissions' AND column_name = 'engine_version'
    ) THEN
        ALTER TABLE submissions ADD COLUMN engine_version TEXT;
        COMMENT ON COLUMN submissions.engine_version IS 'Version of the engine used to process this submission';
    END IF;

    -- Add auditor_version column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submissions' AND column_name = 'auditor_version'
    ) THEN
        ALTER TABLE submissions ADD COLUMN auditor_version TEXT;
        COMMENT ON COLUMN submissions.auditor_version IS 'Version of the auditor used to process this submission';
    END IF;

    -- Add file_hash column if it doesn't exist (for deduplication)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submissions' AND column_name = 'file_hash'
    ) THEN
        ALTER TABLE submissions ADD COLUMN file_hash TEXT;
        COMMENT ON COLUMN submissions.file_hash IS 'Hash of the source file for deduplication';
        -- Add index for faster lookups
        CREATE INDEX IF NOT EXISTS idx_submissions_file_hash ON submissions(file_hash) WHERE file_hash IS NOT NULL;
    END IF;

    -- Add document_name column if it doesn't exist (for easier querying)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submissions' AND column_name = 'document_name'
    ) THEN
        ALTER TABLE submissions ADD COLUMN document_name TEXT;
        COMMENT ON COLUMN submissions.document_name IS 'Name of the source document (extracted from data JSONB)';
    END IF;
END $$;

-- Update the type constraint to allow 'document' type
-- First, drop the existing constraint if it exists
DO $$
BEGIN
    -- Check if constraint exists and drop it
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'submissions_type_check'
    ) THEN
        ALTER TABLE submissions DROP CONSTRAINT submissions_type_check;
    END IF;
    
    -- Add new constraint that allows 'document' type
    ALTER TABLE submissions ADD CONSTRAINT submissions_type_check 
        CHECK (type IN ('vulnerability', 'ofc', 'document'));
END $$;

-- Add comments to clarify the type field
COMMENT ON COLUMN submissions.type IS 'Submission type: vulnerability (individual vulnerability), ofc (individual OFC), or document (auto-processed document with multiple vulnerabilities/OFCs)';

-- ============================================================================
-- 2. Update submission_vulnerabilities table
-- ============================================================================

-- Add missing columns that may be in the submitted data
DO $$ 
BEGIN
    -- Add discipline_id column if it doesn't exist (UUID reference)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_vulnerabilities' AND column_name = 'discipline_id'
    ) THEN
        ALTER TABLE submission_vulnerabilities ADD COLUMN discipline_id UUID;
        COMMENT ON COLUMN submission_vulnerabilities.discipline_id IS 'Foreign key to disciplines table (UUID)';
        -- Add index for faster lookups
        CREATE INDEX IF NOT EXISTS idx_submission_vuln_discipline_id ON submission_vulnerabilities(discipline_id) WHERE discipline_id IS NOT NULL;
    END IF;

    -- Add sector_id column if it doesn't exist (UUID reference)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_vulnerabilities' AND column_name = 'sector_id'
    ) THEN
        ALTER TABLE submission_vulnerabilities ADD COLUMN sector_id UUID;
        COMMENT ON COLUMN submission_vulnerabilities.sector_id IS 'Foreign key to sectors table (UUID)';
        -- Add index for faster lookups
        CREATE INDEX IF NOT EXISTS idx_submission_vuln_sector_id ON submission_vulnerabilities(sector_id) WHERE sector_id IS NOT NULL;
    END IF;

    -- Add subsector_id column if it doesn't exist (UUID reference)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_vulnerabilities' AND column_name = 'subsector_id'
    ) THEN
        ALTER TABLE submission_vulnerabilities ADD COLUMN subsector_id UUID;
        COMMENT ON COLUMN submission_vulnerabilities.subsector_id IS 'Foreign key to subsectors table (UUID)';
        -- Add index for faster lookups
        CREATE INDEX IF NOT EXISTS idx_submission_vuln_subsector_id ON submission_vulnerabilities(subsector_id) WHERE subsector_id IS NOT NULL;
    END IF;

    -- Add page_ref column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_vulnerabilities' AND column_name = 'page_ref'
    ) THEN
        ALTER TABLE submission_vulnerabilities ADD COLUMN page_ref TEXT;
        COMMENT ON COLUMN submission_vulnerabilities.page_ref IS 'Page reference in source document (e.g., "1-2")';
    END IF;

    -- Add chunk_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_vulnerabilities' AND column_name = 'chunk_id'
    ) THEN
        ALTER TABLE submission_vulnerabilities ADD COLUMN chunk_id TEXT;
        COMMENT ON COLUMN submission_vulnerabilities.chunk_id IS 'Chunk identifier from document processing';
    END IF;

    -- Add severity_level column if it doesn't exist (for matrix surveys)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_vulnerabilities' AND column_name = 'severity_level'
    ) THEN
        ALTER TABLE submission_vulnerabilities ADD COLUMN severity_level TEXT;
        COMMENT ON COLUMN submission_vulnerabilities.severity_level IS 'Severity level from DHS-style matrix surveys (e.g., "Critical", "High", "Medium", "Low")';
    END IF;
END $$;

-- ============================================================================
-- 3. Update submission_options_for_consideration table
-- ============================================================================

-- Add missing columns that may be in the submitted data
DO $$ 
BEGIN
    -- Add discipline_id column if it doesn't exist (UUID reference)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_options_for_consideration' AND column_name = 'discipline_id'
    ) THEN
        ALTER TABLE submission_options_for_consideration ADD COLUMN discipline_id UUID;
        COMMENT ON COLUMN submission_options_for_consideration.discipline_id IS 'Foreign key to disciplines table (UUID)';
        -- Add index for faster lookups
        CREATE INDEX IF NOT EXISTS idx_submission_ofc_discipline_id ON submission_options_for_consideration(discipline_id) WHERE discipline_id IS NOT NULL;
    END IF;

    -- Add sector_id column if it doesn't exist (UUID reference)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_options_for_consideration' AND column_name = 'sector_id'
    ) THEN
        ALTER TABLE submission_options_for_consideration ADD COLUMN sector_id UUID;
        COMMENT ON COLUMN submission_options_for_consideration.sector_id IS 'Foreign key to sectors table (UUID)';
        -- Add index for faster lookups
        CREATE INDEX IF NOT EXISTS idx_submission_ofc_sector_id ON submission_options_for_consideration(sector_id) WHERE sector_id IS NOT NULL;
    END IF;

    -- Add subsector_id column if it doesn't exist (UUID reference)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_options_for_consideration' AND column_name = 'subsector_id'
    ) THEN
        ALTER TABLE submission_options_for_consideration ADD COLUMN subsector_id UUID;
        COMMENT ON COLUMN submission_options_for_consideration.subsector_id IS 'Foreign key to subsectors table (UUID)';
        -- Add index for faster lookups
        CREATE INDEX IF NOT EXISTS idx_submission_ofc_subsector_id ON submission_options_for_consideration(subsector_id) WHERE subsector_id IS NOT NULL;
    END IF;
END $$;

-- ============================================================================
-- Summary
-- ============================================================================

-- Display what was added
DO $$
DECLARE
    added_columns TEXT[];
BEGIN
    SELECT array_agg(column_name ORDER BY column_name)
    INTO added_columns
    FROM information_schema.columns
    WHERE table_name IN ('submissions', 'submission_vulnerabilities', 'submission_options_for_consideration')
    AND column_name IN (
        'parser_version', 'engine_version', 'auditor_version', 'file_hash', 'document_name',
        'discipline_id', 'sector_id', 'subsector_id', 'page_ref', 'chunk_id', 'severity_level'
    );
    
    RAISE NOTICE 'Migration complete. Columns available: %', array_to_string(added_columns, ', ');
    RAISE NOTICE 'Type constraint updated to allow: vulnerability, ofc, document';
END $$;

