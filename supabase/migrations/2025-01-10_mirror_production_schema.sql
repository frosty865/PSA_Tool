-- ==========================================================
-- Mirror Production Schema in Submission Tables
-- Purpose:
--   Ensure submission tables have the same core structure
--   as production tables for seamless translation
-- ==========================================================

DO $$ 
BEGIN
    -- ==========================================================
    -- 1. submission_vulnerabilities: Add production-mirroring columns
    -- ==========================================================
    
    -- Add vulnerability_name (mirrors production.vulnerabilities.vulnerability_name)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_vulnerabilities' 
        AND column_name = 'vulnerability_name'
    ) THEN
        ALTER TABLE public.submission_vulnerabilities 
        ADD COLUMN vulnerability_name TEXT;
        COMMENT ON COLUMN public.submission_vulnerabilities.vulnerability_name IS 
        'Vulnerability name/title (mirrors production.vulnerabilities.vulnerability_name)';
        
        -- Migrate existing data: copy from "vulnerability" to "vulnerability_name"
        UPDATE public.submission_vulnerabilities 
        SET vulnerability_name = vulnerability 
        WHERE vulnerability_name IS NULL AND vulnerability IS NOT NULL;
    END IF;
    
    -- Add description (mirrors production.vulnerabilities.description)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_vulnerabilities' 
        AND column_name = 'description'
    ) THEN
        ALTER TABLE public.submission_vulnerabilities 
        ADD COLUMN description TEXT;
        COMMENT ON COLUMN public.submission_vulnerabilities.description IS 
        'Vulnerability description (mirrors production.vulnerabilities.description). Can include structured fields.';
        
        -- Migrate existing data: copy from source_context to description if available
        UPDATE public.submission_vulnerabilities 
        SET description = source_context 
        WHERE description IS NULL AND source_context IS NOT NULL;
    END IF;
    
    -- Ensure severity_level exists (mirrors production.vulnerabilities.severity_level)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_vulnerabilities' 
        AND column_name = 'severity_level'
    ) THEN
        ALTER TABLE public.submission_vulnerabilities 
        ADD COLUMN severity_level TEXT;
        COMMENT ON COLUMN public.submission_vulnerabilities.severity_level IS 
        'Severity level: Very Low, Low, Medium, High, Very High (mirrors production.vulnerabilities.severity_level)';
    END IF;
    
    -- ==========================================================
    -- 2. submission_options_for_consideration: Add production-mirroring columns
    -- ==========================================================
    
    -- Ensure sector_id exists (mirrors production.options_for_consideration.sector_id)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_options_for_consideration' 
        AND column_name = 'sector_id'
    ) THEN
        ALTER TABLE public.submission_options_for_consideration 
        ADD COLUMN sector_id UUID;
        COMMENT ON COLUMN public.submission_options_for_consideration.sector_id IS 
        'Foreign key to sectors.id (mirrors production.options_for_consideration.sector_id)';
        
        -- Add foreign key constraint if sectors table exists
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'sectors') THEN
            ALTER TABLE public.submission_options_for_consideration 
            ADD CONSTRAINT fk_submission_ofc_sector_id 
            FOREIGN KEY (sector_id) REFERENCES public.sectors(id);
        END IF;
    END IF;
    
    -- Ensure subsector_id exists (mirrors production.options_for_consideration.subsector_id)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_options_for_consideration' 
        AND column_name = 'subsector_id'
    ) THEN
        ALTER TABLE public.submission_options_for_consideration 
        ADD COLUMN subsector_id UUID;
        COMMENT ON COLUMN public.submission_options_for_consideration.subsector_id IS 
        'Foreign key to subsectors.id (mirrors production.options_for_consideration.subsector_id)';
        
        -- Add foreign key constraint if subsectors table exists
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'subsectors') THEN
            ALTER TABLE public.submission_options_for_consideration 
            ADD CONSTRAINT fk_submission_ofc_subsector_id 
            FOREIGN KEY (subsector_id) REFERENCES public.subsectors(id);
        END IF;
    END IF;
    
    -- ==========================================================
    -- 3. Create indexes for new columns
    -- ==========================================================
    
    CREATE INDEX IF NOT EXISTS idx_submission_vuln_vulnerability_name 
        ON public.submission_vulnerabilities(vulnerability_name) 
        WHERE vulnerability_name IS NOT NULL;
    
    CREATE INDEX IF NOT EXISTS idx_submission_ofc_sector_id 
        ON public.submission_options_for_consideration(sector_id) 
        WHERE sector_id IS NOT NULL;
    
    CREATE INDEX IF NOT EXISTS idx_submission_ofc_subsector_id 
        ON public.submission_options_for_consideration(subsector_id) 
        WHERE subsector_id IS NOT NULL;
    
    RAISE NOTICE 'Migration completed: Submission tables now mirror production table structure';
END $$;

-- Add comments
COMMENT ON TABLE public.submission_vulnerabilities IS 
'Submission vulnerabilities table. Core structure mirrors production.vulnerabilities: vulnerability_name, description, discipline, sector_id, subsector_id, severity_level. Additional metadata fields preserved.';

COMMENT ON TABLE public.submission_options_for_consideration IS 
'Submission OFCs table. Core structure mirrors production.options_for_consideration: option_text, discipline, sector_id, subsector_id. Additional metadata fields preserved.';

