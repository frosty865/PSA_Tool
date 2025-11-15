-- ==========================================================
-- Update Phase 3 Trigger to Include discipline_subtype_id
-- Purpose: Update trigger function to copy discipline_subtype_id
--          from submission_vulnerabilities to phase3_records
-- Date: 2025-01-16
-- ==========================================================

-- Update trigger function to include discipline_subtype_id
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
            discipline_subtype_id,
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
            NEW.discipline_subtype_id,  -- Include discipline_subtype_id
            'accepted',
            NOW(),
            NOW()
        )
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION fn_insert_phase3_record() IS
'Automatically mirrors accepted vulnerabilities into phase3_records for training data collection. Updated to include discipline_subtype_id.';

