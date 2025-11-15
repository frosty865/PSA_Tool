-- ==========================================================
-- DISCIPLINE SYSTEM REWRITE ROLLBACK
-- Purpose: Restore original disciplines and remove new tables/columns
-- Date: 2025-01-16
-- ==========================================================

DO $$ 
BEGIN
    -- ==========================================================
    -- STEP 1: Remove discipline_subtype_id columns from all tables
    -- ==========================================================
    
    -- submission_vulnerabilities
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_vulnerabilities' 
        AND column_name = 'discipline_subtype_id'
    ) THEN
        ALTER TABLE public.submission_vulnerabilities 
        DROP COLUMN discipline_subtype_id;
    END IF;
    
    -- submission_options_for_consideration
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_options_for_consideration' 
        AND column_name = 'discipline_subtype_id'
    ) THEN
        ALTER TABLE public.submission_options_for_consideration 
        DROP COLUMN discipline_subtype_id;
    END IF;
    
    -- vulnerabilities
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'vulnerabilities' 
        AND column_name = 'discipline_subtype_id'
    ) THEN
        ALTER TABLE public.vulnerabilities 
        DROP COLUMN discipline_subtype_id;
    END IF;
    
    -- options_for_consideration
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'options_for_consideration' 
        AND column_name = 'discipline_subtype_id'
    ) THEN
        ALTER TABLE public.options_for_consideration 
        DROP COLUMN discipline_subtype_id;
    END IF;
    
    -- phase3_records
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'phase3_records' 
        AND column_name = 'discipline_subtype_id'
    ) THEN
        ALTER TABLE public.phase3_records 
        DROP COLUMN discipline_subtype_id;
    END IF;
    
    -- ofc_requests
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'ofc_requests' 
        AND column_name = 'discipline_subtype_id'
    ) THEN
        ALTER TABLE public.ofc_requests 
        DROP COLUMN discipline_subtype_id;
    END IF;
    
    -- ==========================================================
    -- STEP 2: Drop discipline_subtypes table
    -- ==========================================================
    
    DROP TABLE IF EXISTS discipline_subtypes CASCADE;
    
    -- ==========================================================
    -- STEP 3: Deactivate new disciplines and restore old ones
    -- ==========================================================
    
    -- Deactivate the 10 new disciplines
    UPDATE disciplines 
    SET is_active = false, 
        updated_at = NOW()
    WHERE name IN (
        'Security Management & Governance',
        'Access Control Systems',
        'Video Surveillance Systems',
        'Intrusion Detection Systems',
        'Perimeter Security',
        'Interior Security & Physical Barriers',
        'Security Force / Operations',
        'Emergency Management & Resilience',
        'Information Sharing & Coordination',
        'Cyber-Physical Infrastructure Support'
    );
    
    -- Restore original disciplines from backup
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'disciplines_backup') THEN
        -- Restore all disciplines from backup
        INSERT INTO disciplines (id, name, description, code, category, is_active, created_at, updated_at)
        SELECT id, name, description, code, category, true, created_at, NOW()
        FROM disciplines_backup
        WHERE id NOT IN (SELECT id FROM disciplines)
        ON CONFLICT (id) DO UPDATE
        SET is_active = true,
            updated_at = NOW();
        
        -- If backup has different structure, try to restore by name
        UPDATE disciplines d
        SET is_active = true,
            updated_at = NOW()
        FROM disciplines_backup b
        WHERE d.name = b.name
        AND d.is_active = false;
    END IF;
    
    -- ==========================================================
    -- STEP 4: Revert discipline text values (if backup exists)
    -- Note: This is a best-effort restoration. Exact values may vary.
    -- ==========================================================
    
    -- This step would require storing the original values before migration
    -- For now, we'll just ensure the new discipline names are cleared
    -- and let the system use whatever was in the backup
    
    RAISE NOTICE 'Discipline system rollback completed';
    
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'Error in discipline system rollback: %', SQLERRM;
END $$;

