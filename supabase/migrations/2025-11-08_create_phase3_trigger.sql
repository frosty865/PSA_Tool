-- ==========================================================
-- VOFC Engine: Auto-Insert Trigger for Accepted Records
-- Purpose:
--   Automatically copy accepted vulnerabilities from
--   submission_vulnerabilities → phase3_records
--   whenever audit_status transitions to 'accepted'.
-- ==========================================================

-- 1. Ensure phase3_records table exists
CREATE TABLE IF NOT EXISTS phase3_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID,
    model_version TEXT,
    vulnerability TEXT,
    options_for_consideration TEXT,
    discipline TEXT,
    category TEXT,
    sector TEXT,
    subsector TEXT,
    confidence NUMERIC(4,3),
    audit_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_phase3_records_created_at ON phase3_records(created_at);
CREATE INDEX IF NOT EXISTS idx_phase3_records_audit_status ON phase3_records(audit_status);
CREATE INDEX IF NOT EXISTS idx_phase3_records_submission_id ON phase3_records(submission_id);

-- 2. Create trigger function
CREATE OR REPLACE FUNCTION fn_insert_phase3_record()
RETURNS TRIGGER AS $$
BEGIN
    -- Only act when audit_status becomes 'accepted'
    IF NEW.audit_status = 'accepted' AND (OLD.audit_status IS NULL OR OLD.audit_status != 'accepted') THEN
        INSERT INTO phase3_records (
            submission_id,
            model_version,
            vulnerability,
            options_for_consideration,
            discipline,
            category,
            sector,
            subsector,
            confidence,
            audit_status,
            created_at,
            updated_at
        )
        VALUES (
            NEW.submission_id,
            -- Get model_version from submissions table if available
            (SELECT engine_version FROM submissions WHERE id = NEW.submission_id LIMIT 1),
            NEW.vulnerability,
            -- Get options_for_consideration from linked OFCs if available
            (SELECT string_agg(option_text, '; ' ORDER BY created_at)
             FROM submission_options_for_consideration
             WHERE submission_id = NEW.submission_id
             AND audit_status = 'accepted'
             LIMIT 10),
            NEW.discipline,
            NEW.category,
            NEW.sector,
            NEW.subsector,
            COALESCE(NEW.confidence_score, 0),
            'accepted',
            NOW(),
            NOW()
        )
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Attach trigger to submission_vulnerabilities updates
DROP TRIGGER IF EXISTS trg_insert_phase3_record ON submission_vulnerabilities;

CREATE TRIGGER trg_insert_phase3_record
AFTER INSERT OR UPDATE OF audit_status
ON submission_vulnerabilities
FOR EACH ROW
EXECUTE FUNCTION fn_insert_phase3_record();

COMMENT ON TRIGGER trg_insert_phase3_record ON submission_vulnerabilities IS
'Automatically mirrors accepted vulnerabilities into phase3_records for training data collection.';

COMMENT ON TABLE phase3_records IS
'Stores accepted Phase 3 records for model retraining. Populated automatically via trigger when vulnerabilities are marked as accepted.';

