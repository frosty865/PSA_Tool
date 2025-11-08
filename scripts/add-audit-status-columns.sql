-- Add audit_status columns to submission_vulnerabilities and submission_options_for_consideration tables
-- These columns are needed for tracking the review status of individual vulnerabilities and OFCs

-- Add audit_status to submission_vulnerabilities
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_vulnerabilities' 
        AND column_name = 'audit_status'
    ) THEN
        ALTER TABLE submission_vulnerabilities 
        ADD COLUMN audit_status text DEFAULT 'pending';
        
        COMMENT ON COLUMN submission_vulnerabilities.audit_status IS 
        'Audit status: pending, accepted, rejected, or review';
    END IF;
END $$;

-- Add audit_status to submission_options_for_consideration
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'submission_options_for_consideration' 
        AND column_name = 'audit_status'
    ) THEN
        ALTER TABLE submission_options_for_consideration 
        ADD COLUMN audit_status text DEFAULT 'pending';
        
        COMMENT ON COLUMN submission_options_for_consideration.audit_status IS 
        'Audit status: pending, accepted, rejected, or review';
    END IF;
END $$;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_submission_vulnerabilities_audit_status 
ON submission_vulnerabilities(audit_status);

CREATE INDEX IF NOT EXISTS idx_submission_ofc_audit_status 
ON submission_options_for_consideration(audit_status);

-- Backfill audit_status for existing records
-- Set default 'pending' for any NULL values (the DEFAULT constraint should handle new records)
UPDATE submission_vulnerabilities 
SET audit_status = 'pending'
WHERE audit_status IS NULL;

UPDATE submission_options_for_consideration 
SET audit_status = 'pending'
WHERE audit_status IS NULL;

-- Note: The sync function (services/supabase_sync.py) will populate audit_status 
-- from the data JSONB for new records going forward

