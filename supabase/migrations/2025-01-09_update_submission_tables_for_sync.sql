-- ==========================================================
-- Update Submission Tables for Single-Pass Sync
-- Purpose:
--   Ensure all columns required by sync_submission_to_supabase()
--   exist in submission tables with correct types and constraints
-- ==========================================================

DO $$ 
BEGIN
    -- ==========================================================
    -- 1. submission_vulnerabilities table updates
    -- ==========================================================
    
    -- Add source_page if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_vulnerabilities' 
        AND column_name = 'source_page'
    ) THEN
        ALTER TABLE public.submission_vulnerabilities 
        ADD COLUMN source_page TEXT;
        COMMENT ON COLUMN public.submission_vulnerabilities.source_page IS 'Page reference from source document (e.g., "12", "1-2")';
    END IF;
    
    -- Add source_context if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_vulnerabilities' 
        AND column_name = 'source_context'
    ) THEN
        ALTER TABLE public.submission_vulnerabilities 
        ADD COLUMN source_context TEXT;
        COMMENT ON COLUMN public.submission_vulnerabilities.source_context IS 'Contextual text from source document (max 1000 chars)';
    END IF;
    
    -- Add confidence_score if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_vulnerabilities' 
        AND column_name = 'confidence_score'
    ) THEN
        ALTER TABLE public.submission_vulnerabilities 
        ADD COLUMN confidence_score DECIMAL(4,3);
        COMMENT ON COLUMN public.submission_vulnerabilities.confidence_score IS 'Confidence score (0.0-1.0)';
    END IF;
    
    -- Add parser_version if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_vulnerabilities' 
        AND column_name = 'parser_version'
    ) THEN
        ALTER TABLE public.submission_vulnerabilities 
        ADD COLUMN parser_version TEXT;
        COMMENT ON COLUMN public.submission_vulnerabilities.parser_version IS 'Parser/model version used (e.g., vofc-engine-sp)';
    END IF;
    
    -- Ensure sector and subsector columns exist (text, not just IDs)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_vulnerabilities' 
        AND column_name = 'sector'
    ) THEN
        ALTER TABLE public.submission_vulnerabilities 
        ADD COLUMN sector TEXT;
        COMMENT ON COLUMN public.submission_vulnerabilities.sector IS 'Sector name (text)';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_vulnerabilities' 
        AND column_name = 'subsector'
    ) THEN
        ALTER TABLE public.submission_vulnerabilities 
        ADD COLUMN subsector TEXT;
        COMMENT ON COLUMN public.submission_vulnerabilities.subsector IS 'Subsector name (text)';
    END IF;
    
    -- ==========================================================
    -- 2. submission_options_for_consideration table updates
    -- ==========================================================
    
    -- Add context if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_options_for_consideration' 
        AND column_name = 'context'
    ) THEN
        ALTER TABLE public.submission_options_for_consideration 
        ADD COLUMN context TEXT;
        COMMENT ON COLUMN public.submission_options_for_consideration.context IS 'Contextual information (max 1000 chars)';
    END IF;
    
    -- Add confidence_score if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_options_for_consideration' 
        AND column_name = 'confidence_score'
    ) THEN
        ALTER TABLE public.submission_options_for_consideration 
        ADD COLUMN confidence_score DECIMAL(4,3);
        COMMENT ON COLUMN public.submission_options_for_consideration.confidence_score IS 'Confidence score (0.0-1.0)';
    END IF;
    
    -- Add linked_vulnerability if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_options_for_consideration' 
        AND column_name = 'linked_vulnerability'
    ) THEN
        ALTER TABLE public.submission_options_for_consideration 
        ADD COLUMN linked_vulnerability TEXT;
        COMMENT ON COLUMN public.submission_options_for_consideration.linked_vulnerability IS 'Text reference to linked vulnerability (for matching)';
    END IF;
    
    -- ==========================================================
    -- 3. submission_vulnerability_ofc_links table updates
    -- ==========================================================
    
    -- Ensure table exists with correct structure
    CREATE TABLE IF NOT EXISTS public.submission_vulnerability_ofc_links (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        submission_id UUID NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
        vulnerability_id UUID NOT NULL REFERENCES public.submission_vulnerabilities(id) ON DELETE CASCADE,
        ofc_id UUID NOT NULL REFERENCES public.submission_options_for_consideration(id) ON DELETE CASCADE,
        link_type TEXT DEFAULT 'direct',
        confidence_score DECIMAL(4,3) DEFAULT 1.0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    -- Add indexes for performance
    CREATE INDEX IF NOT EXISTS idx_submission_vuln_ofc_links_submission_id 
        ON public.submission_vulnerability_ofc_links(submission_id);
    CREATE INDEX IF NOT EXISTS idx_submission_vuln_ofc_links_vuln_id 
        ON public.submission_vulnerability_ofc_links(vulnerability_id);
    CREATE INDEX IF NOT EXISTS idx_submission_vuln_ofc_links_ofc_id 
        ON public.submission_vulnerability_ofc_links(ofc_id);
    
    -- ==========================================================
    -- 4. Create indexes for commonly queried fields
    -- ==========================================================
    
    CREATE INDEX IF NOT EXISTS idx_submission_vuln_source_page 
        ON public.submission_vulnerabilities(source_page) 
        WHERE source_page IS NOT NULL;
    
    CREATE INDEX IF NOT EXISTS idx_submission_vuln_confidence_score 
        ON public.submission_vulnerabilities(confidence_score) 
        WHERE confidence_score IS NOT NULL;
    
    CREATE INDEX IF NOT EXISTS idx_submission_ofc_confidence_score 
        ON public.submission_options_for_consideration(confidence_score) 
        WHERE confidence_score IS NOT NULL;
    
    CREATE INDEX IF NOT EXISTS idx_submission_ofc_linked_vuln 
        ON public.submission_options_for_consideration(linked_vulnerability) 
        WHERE linked_vulnerability IS NOT NULL;
    
    RAISE NOTICE 'Migration completed: Updated submission tables for single-pass sync';
END $$;

-- Add comments
COMMENT ON TABLE public.submission_vulnerability_ofc_links IS 
'Junction table linking submission vulnerabilities to their associated OFCs. Created automatically during sync.';

COMMENT ON COLUMN public.submission_vulnerability_ofc_links.link_type IS 
'Type of link: "direct" (explicitly matched), "inferred" (derived from context)';

COMMENT ON COLUMN public.submission_vulnerability_ofc_links.confidence_score IS 
'Confidence score for the link (0.0-1.0). Default 1.0 for direct links.';

