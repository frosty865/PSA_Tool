-- Add metadata columns to submissions table for better querying and reliability
-- This migration ensures submitter_email, parser_version, engine_version, and auditor_version columns exist

-- ============================================================================
-- Add missing columns to submissions table
-- ============================================================================

DO $$ 
BEGIN
    -- Add submitter_email column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submissions' 
        AND column_name = 'submitter_email'
    ) THEN
        ALTER TABLE public.submissions ADD COLUMN submitter_email TEXT;
        COMMENT ON COLUMN public.submissions.submitter_email IS 'Email of the person who submitted this document';
        CREATE INDEX IF NOT EXISTS idx_submissions_submitter_email ON public.submissions(submitter_email) WHERE submitter_email IS NOT NULL;
    END IF;

    -- Add parser_version column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submissions' 
        AND column_name = 'parser_version'
    ) THEN
        ALTER TABLE public.submissions ADD COLUMN parser_version TEXT;
        COMMENT ON COLUMN public.submissions.parser_version IS 'Version of the parser used to process this submission (e.g., vofc-parser:latest)';
        CREATE INDEX IF NOT EXISTS idx_submissions_parser_version ON public.submissions(parser_version) WHERE parser_version IS NOT NULL;
    END IF;

    -- Add engine_version column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submissions' 
        AND column_name = 'engine_version'
    ) THEN
        ALTER TABLE public.submissions ADD COLUMN engine_version TEXT;
        COMMENT ON COLUMN public.submissions.engine_version IS 'Version of the engine used to process this submission (e.g., vofc-engine:latest)';
        CREATE INDEX IF NOT EXISTS idx_submissions_engine_version ON public.submissions(engine_version) WHERE engine_version IS NOT NULL;
    END IF;

    -- Add auditor_version column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submissions' 
        AND column_name = 'auditor_version'
    ) THEN
        ALTER TABLE public.submissions ADD COLUMN auditor_version TEXT;
        COMMENT ON COLUMN public.submissions.auditor_version IS 'Version of the auditor used to process this submission (e.g., vofc-auditor:latest)';
        CREATE INDEX IF NOT EXISTS idx_submissions_auditor_version ON public.submissions(auditor_version) WHERE auditor_version IS NOT NULL;
    END IF;

    RAISE NOTICE 'Migration completed: Added metadata columns to submissions table';
END $$;

