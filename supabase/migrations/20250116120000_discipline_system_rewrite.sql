-- ==========================================================
-- DISCIPLINE SYSTEM REWRITE (HARD MIGRATION)
-- Purpose: Replace existing discipline taxonomy with 10 new CISA-aligned disciplines
--          and add sub-discipline support
-- Date: 2025-01-16
-- ==========================================================

DO $$ 
DECLARE
    v_discipline_id UUID;
    v_subtype_id UUID;
    v_old_discipline_id UUID;
BEGIN
    -- ==========================================================
    -- STEP 0: Ensure disciplines table has required columns
    -- ==========================================================
    
    -- Add code column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'disciplines' 
        AND column_name = 'code'
    ) THEN
        ALTER TABLE public.disciplines 
        ADD COLUMN code TEXT;
        
        CREATE INDEX IF NOT EXISTS idx_disciplines_code ON disciplines(code);
    END IF;
    
    -- ==========================================================
    -- STEP 1: Backup existing disciplines (for rollback support)
    -- ==========================================================
    
    -- Create backup table if it doesn't exist
    CREATE TABLE IF NOT EXISTS disciplines_backup AS 
    SELECT * FROM disciplines WHERE 1=0;
    
    -- Copy existing disciplines to backup
    INSERT INTO disciplines_backup 
    SELECT * FROM disciplines;
    
    -- ==========================================================
    -- STEP 2: Deactivate all existing disciplines
    -- ==========================================================
    
    UPDATE disciplines 
    SET is_active = false, 
        updated_at = NOW()
    WHERE is_active = true;
    
    -- ==========================================================
    -- STEP 3: Insert 10 new master disciplines
    -- ==========================================================
    
    -- 1. Security Management & Governance
    INSERT INTO disciplines (id, name, description, code, category, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'Security Management & Governance',
        'Security policies, procedures, risk management, training, and governance frameworks',
        'SMG',
        'Physical',
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (name) DO UPDATE
    SET description = EXCLUDED.description,
        code = EXCLUDED.code,
        category = EXCLUDED.category,
        is_active = true,
        updated_at = NOW()
    RETURNING id INTO v_discipline_id;
    
    -- 2. Access Control Systems
    INSERT INTO disciplines (id, name, description, code, category, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'Access Control Systems',
        'Physical and electronic access control systems including PACS, visitor management, biometrics, and locking hardware',
        'ACS',
        'Physical',
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (name) DO UPDATE
    SET description = EXCLUDED.description,
        code = EXCLUDED.code,
        category = EXCLUDED.category,
        is_active = true,
        updated_at = NOW()
    RETURNING id INTO v_discipline_id;
    
    -- 3. Video Surveillance Systems
    INSERT INTO disciplines (id, name, description, code, category, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'Video Surveillance Systems',
        'Video surveillance and monitoring systems including IP cameras, analog cameras, hybrid systems, storage, and analytics',
        'VSS',
        'Physical',
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (name) DO UPDATE
    SET description = EXCLUDED.description,
        code = EXCLUDED.code,
        category = EXCLUDED.category,
        is_active = true,
        updated_at = NOW()
    RETURNING id INTO v_discipline_id;
    
    -- 4. Intrusion Detection Systems
    INSERT INTO disciplines (id, name, description, code, category, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'Intrusion Detection Systems',
        'Intrusion detection and alarm systems including door contacts, glass break sensors, motion detectors, and perimeter IDS',
        'IDS',
        'Physical',
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (name) DO UPDATE
    SET description = EXCLUDED.description,
        code = EXCLUDED.code,
        category = EXCLUDED.category,
        is_active = true,
        updated_at = NOW()
    RETURNING id INTO v_discipline_id;
    
    -- 5. Perimeter Security
    INSERT INTO disciplines (id, name, description, code, category, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'Perimeter Security',
        'Perimeter security measures including fencing, clear zones, barriers/bollards, perimeter lighting, and waterside security',
        'PER',
        'Physical',
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (name) DO UPDATE
    SET description = EXCLUDED.description,
        code = EXCLUDED.code,
        category = EXCLUDED.category,
        is_active = true,
        updated_at = NOW()
    RETURNING id INTO v_discipline_id;
    
    -- 6. Interior Security & Physical Barriers
    INSERT INTO disciplines (id, name, description, code, category, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'Interior Security & Physical Barriers',
        'Interior security measures including secure areas, safe rooms, physical barriers, locks, and interior lighting',
        'INT',
        'Physical',
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (name) DO UPDATE
    SET description = EXCLUDED.description,
        code = EXCLUDED.code,
        category = EXCLUDED.category,
        is_active = true,
        updated_at = NOW()
    RETURNING id INTO v_discipline_id;
    
    -- 7. Security Force / Operations
    INSERT INTO disciplines (id, name, description, code, category, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'Security Force / Operations',
        'Security operations including security operations centers (SOC), patrols/posts, radios & communications, and response procedures',
        'SFO',
        'Physical',
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (name) DO UPDATE
    SET description = EXCLUDED.description,
        code = EXCLUDED.code,
        category = EXCLUDED.category,
        is_active = true,
        updated_at = NOW()
    RETURNING id INTO v_discipline_id;
    
    -- 8. Emergency Management & Resilience
    INSERT INTO disciplines (id, name, description, code, category, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'Emergency Management & Resilience',
        'Emergency management and resilience planning including EAP, BCP, drills & exercises, and mass notification systems',
        'EMR',
        'Physical',
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (name) DO UPDATE
    SET description = EXCLUDED.description,
        code = EXCLUDED.code,
        category = EXCLUDED.category,
        is_active = true,
        updated_at = NOW()
    RETURNING id INTO v_discipline_id;
    
    -- 9. Information Sharing & Coordination
    INSERT INTO disciplines (id, name, description, code, category, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'Information Sharing & Coordination',
        'Information sharing and coordination mechanisms including law enforcement liaison, fusion centers, JTTF, HSIN, and ISAC/ISAO',
        'ISC',
        'Physical',
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (name) DO UPDATE
    SET description = EXCLUDED.description,
        code = EXCLUDED.code,
        category = EXCLUDED.category,
        is_active = true,
        updated_at = NOW()
    RETURNING id INTO v_discipline_id;
    
    -- 10. Cyber-Physical Infrastructure Support
    INSERT INTO disciplines (id, name, description, code, category, is_active, created_at, updated_at)
    VALUES (
        gen_random_uuid(),
        'Cyber-Physical Infrastructure Support',
        'Cyber-physical infrastructure support including UPS/power systems, switches & ESS network, server rooms, and cable security',
        'CPI',
        'Converged',
        true,
        NOW(),
        NOW()
    )
    ON CONFLICT (name) DO UPDATE
    SET description = EXCLUDED.description,
        code = EXCLUDED.code,
        category = EXCLUDED.category,
        is_active = true,
        updated_at = NOW()
    RETURNING id INTO v_discipline_id;
    
    -- ==========================================================
    -- STEP 4: Create discipline_subtypes table
    -- ==========================================================
    
    CREATE TABLE IF NOT EXISTS discipline_subtypes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        discipline_id UUID NOT NULL REFERENCES disciplines(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        description TEXT,
        code TEXT,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_discipline_subtypes_discipline_id ON discipline_subtypes(discipline_id);
    CREATE INDEX IF NOT EXISTS idx_discipline_subtypes_code ON discipline_subtypes(code);
    CREATE INDEX IF NOT EXISTS idx_discipline_subtypes_is_active ON discipline_subtypes(is_active);
    
    -- ==========================================================
    -- STEP 5: Populate discipline_subtypes
    -- ==========================================================
    
    -- Access Control Systems subtypes
    SELECT id INTO v_discipline_id FROM disciplines WHERE name = 'Access Control Systems' AND is_active = true;
    
    INSERT INTO discipline_subtypes (discipline_id, name, description, code, is_active) VALUES
    (v_discipline_id, 'PACS', 'Physical Access Control Systems', 'PACS', true),
    (v_discipline_id, 'Visitor Management', 'Visitor management systems and procedures', 'VM', true),
    (v_discipline_id, 'Biometrics', 'Biometric access control systems', 'BIO', true),
    (v_discipline_id, 'Locking Hardware', 'Physical locking mechanisms and hardware', 'LOCK', true),
    (v_discipline_id, 'Screening Ops', 'Screening operations and procedures', 'SCR', true);
    
    -- Video Surveillance Systems subtypes
    SELECT id INTO v_discipline_id FROM disciplines WHERE name = 'Video Surveillance Systems' AND is_active = true;
    
    INSERT INTO discipline_subtypes (discipline_id, name, description, code, is_active) VALUES
    (v_discipline_id, 'IP Cameras', 'IP-based camera systems', 'IPCAM', true),
    (v_discipline_id, 'Analog Cameras', 'Analog camera systems', 'ANALOG', true),
    (v_discipline_id, 'Hybrid Systems', 'Hybrid IP/analog camera systems', 'HYBRID', true),
    (v_discipline_id, 'Storage & Retention', 'Video storage and retention systems', 'STOR', true),
    (v_discipline_id, 'Monitoring / Video Wall', 'Video monitoring and display systems', 'MON', true),
    (v_discipline_id, 'Analytics', 'Video analytics and AI systems', 'ANAL', true);
    
    -- Intrusion Detection Systems subtypes
    SELECT id INTO v_discipline_id FROM disciplines WHERE name = 'Intrusion Detection Systems' AND is_active = true;
    
    INSERT INTO discipline_subtypes (discipline_id, name, description, code, is_active) VALUES
    (v_discipline_id, 'Door Contacts', 'Door contact sensors', 'DOOR', true),
    (v_discipline_id, 'Glass Break', 'Glass break detection sensors', 'GLASS', true),
    (v_discipline_id, 'Motion', 'Motion detection sensors', 'MOTION', true),
    (v_discipline_id, 'Perimeter IDS', 'Perimeter intrusion detection systems', 'PERIDS', true),
    (v_discipline_id, 'Alarm Monitoring', 'Alarm monitoring and response systems', 'ALARM', true);
    
    -- Perimeter Security subtypes
    SELECT id INTO v_discipline_id FROM disciplines WHERE name = 'Perimeter Security' AND is_active = true;
    
    INSERT INTO discipline_subtypes (discipline_id, name, description, code, is_active) VALUES
    (v_discipline_id, 'Fencing', 'Perimeter fencing systems', 'FENCE', true),
    (v_discipline_id, 'Clear Zones', 'Clear zone maintenance and management', 'CLEAR', true),
    (v_discipline_id, 'Barriers/Bollards', 'Physical barriers and bollards', 'BARR', true),
    (v_discipline_id, 'Perimeter Lighting', 'Perimeter lighting systems', 'LIGHT', true),
    (v_discipline_id, 'Waterside Security', 'Waterside security measures', 'WATER', true),
    (v_discipline_id, 'CPTED Elements', 'Crime Prevention Through Environmental Design elements', 'CPTED', true);
    
    -- Interior Security & Physical Barriers subtypes
    SELECT id INTO v_discipline_id FROM disciplines WHERE name = 'Interior Security & Physical Barriers' AND is_active = true;
    
    INSERT INTO discipline_subtypes (discipline_id, name, description, code, is_active) VALUES
    (v_discipline_id, 'Secure Areas', 'Secure area designation and management', 'SEC', true),
    (v_discipline_id, 'Safe Rooms', 'Safe room design and implementation', 'SAFE', true),
    (v_discipline_id, 'Physical Barriers', 'Interior physical barriers', 'PHYS', true),
    (v_discipline_id, 'Locks', 'Interior locking systems', 'LOCKS', true),
    (v_discipline_id, 'Interior Lighting', 'Interior security lighting', 'ILIGHT', true);
    
    -- Security Force / Operations subtypes
    SELECT id INTO v_discipline_id FROM disciplines WHERE name = 'Security Force / Operations' AND is_active = true;
    
    INSERT INTO discipline_subtypes (discipline_id, name, description, code, is_active) VALUES
    (v_discipline_id, 'SOC', 'Security Operations Center', 'SOC', true),
    (v_discipline_id, 'Patrol / Posts', 'Security patrols and post assignments', 'PATROL', true),
    (v_discipline_id, 'Radios & Comms', 'Security radio and communication systems', 'COMM', true),
    (v_discipline_id, 'Response Procedures', 'Security response procedures and protocols', 'RESP', true);
    
    -- Emergency Management & Resilience subtypes
    SELECT id INTO v_discipline_id FROM disciplines WHERE name = 'Emergency Management & Resilience' AND is_active = true;
    
    INSERT INTO discipline_subtypes (discipline_id, name, description, code, is_active) VALUES
    (v_discipline_id, 'EAP', 'Emergency Action Plans', 'EAP', true),
    (v_discipline_id, 'BCP', 'Business Continuity Planning', 'BCP', true),
    (v_discipline_id, 'Drills & Exercises', 'Emergency drills and exercises', 'DRILL', true),
    (v_discipline_id, 'Mass Notification', 'Mass notification systems', 'NOTIF', true);
    
    -- Information Sharing & Coordination subtypes
    SELECT id INTO v_discipline_id FROM disciplines WHERE name = 'Information Sharing & Coordination' AND is_active = true;
    
    INSERT INTO discipline_subtypes (discipline_id, name, description, code, is_active) VALUES
    (v_discipline_id, 'Law Enforcement Liaison', 'Law enforcement liaison programs', 'LEL', true),
    (v_discipline_id, 'Fusion Center', 'Fusion center coordination', 'FUSION', true),
    (v_discipline_id, 'JTTF', 'Joint Terrorism Task Force coordination', 'JTTF', true),
    (v_discipline_id, 'HSIN', 'Homeland Security Information Network', 'HSIN', true),
    (v_discipline_id, 'ISAC/ISAO', 'Information Sharing and Analysis Centers/Organizations', 'ISAC', true);
    
    -- Cyber-Physical Infrastructure Support subtypes
    SELECT id INTO v_discipline_id FROM disciplines WHERE name = 'Cyber-Physical Infrastructure Support' AND is_active = true;
    
    INSERT INTO discipline_subtypes (discipline_id, name, description, code, is_active) VALUES
    (v_discipline_id, 'UPS/Power', 'Uninterruptible power supply and power systems', 'UPS', true),
    (v_discipline_id, 'Switches & ESS Network', 'Network switches and Electronic Security Systems network infrastructure', 'NET', true),
    (v_discipline_id, 'Server Rooms', 'Server room security and management', 'SERVER', true),
    (v_discipline_id, 'Cable Security', 'Cable security and protection', 'CABLE', true);
    
    -- ==========================================================
    -- STEP 6: Add discipline_subtype_id columns to affected tables
    -- ==========================================================
    
    -- submission_vulnerabilities
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_vulnerabilities' 
        AND column_name = 'discipline_subtype_id'
    ) THEN
        ALTER TABLE public.submission_vulnerabilities 
        ADD COLUMN discipline_subtype_id UUID REFERENCES discipline_subtypes(id);
        
        CREATE INDEX IF NOT EXISTS idx_submission_vuln_discipline_subtype_id 
        ON submission_vulnerabilities(discipline_subtype_id);
    END IF;
    
    -- submission_options_for_consideration
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'submission_options_for_consideration' 
        AND column_name = 'discipline_subtype_id'
    ) THEN
        ALTER TABLE public.submission_options_for_consideration 
        ADD COLUMN discipline_subtype_id UUID REFERENCES discipline_subtypes(id);
        
        CREATE INDEX IF NOT EXISTS idx_submission_ofc_discipline_subtype_id 
        ON submission_options_for_consideration(discipline_subtype_id);
    END IF;
    
    -- vulnerabilities
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'vulnerabilities' 
        AND column_name = 'discipline_subtype_id'
    ) THEN
        ALTER TABLE public.vulnerabilities 
        ADD COLUMN discipline_subtype_id UUID REFERENCES discipline_subtypes(id);
        
        CREATE INDEX IF NOT EXISTS idx_vulnerabilities_discipline_subtype_id 
        ON vulnerabilities(discipline_subtype_id);
    END IF;
    
    -- options_for_consideration
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'options_for_consideration' 
        AND column_name = 'discipline_subtype_id'
    ) THEN
        ALTER TABLE public.options_for_consideration 
        ADD COLUMN discipline_subtype_id UUID REFERENCES discipline_subtypes(id);
        
        CREATE INDEX IF NOT EXISTS idx_options_discipline_subtype_id 
        ON options_for_consideration(discipline_subtype_id);
    END IF;
    
    -- phase3_records
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'phase3_records' 
        AND column_name = 'discipline_subtype_id'
    ) THEN
        ALTER TABLE public.phase3_records 
        ADD COLUMN discipline_subtype_id UUID REFERENCES discipline_subtypes(id);
        
        CREATE INDEX IF NOT EXISTS idx_phase3_records_discipline_subtype_id 
        ON phase3_records(discipline_subtype_id);
    END IF;
    
    -- ofc_requests
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'ofc_requests' 
        AND column_name = 'discipline_subtype_id'
    ) THEN
        ALTER TABLE public.ofc_requests 
        ADD COLUMN discipline_subtype_id UUID REFERENCES discipline_subtypes(id);
        
        CREATE INDEX IF NOT EXISTS idx_ofc_requests_discipline_subtype_id 
        ON ofc_requests(discipline_subtype_id);
    END IF;
    
    -- ==========================================================
    -- STEP 7: Update legacy discipline text values
    -- ==========================================================
    
    -- Mapping: Access Control → Access Control Systems
    UPDATE submission_vulnerabilities
    SET discipline = 'Access Control Systems'
    WHERE discipline IN ('Access Control', 'Visitor Management', 'Identity Management');
    
    UPDATE submission_options_for_consideration
    SET discipline = 'Access Control Systems'
    WHERE discipline IN ('Access Control', 'Visitor Management', 'Identity Management');
    
    UPDATE vulnerabilities
    SET discipline = 'Access Control Systems'
    WHERE discipline IN ('Access Control', 'Visitor Management', 'Identity Management');
    
    UPDATE options_for_consideration
    SET discipline = 'Access Control Systems'
    WHERE discipline IN ('Access Control', 'Visitor Management', 'Identity Management');
    
    UPDATE phase3_records
    SET discipline = 'Access Control Systems'
    WHERE discipline IN ('Access Control', 'Visitor Management', 'Identity Management');
    
    UPDATE ofc_requests
    SET discipline = 'Access Control Systems'
    WHERE discipline IN ('Access Control', 'Visitor Management', 'Identity Management');
    
    -- Mapping: VSS → Video Surveillance Systems
    UPDATE submission_vulnerabilities
    SET discipline = 'Video Surveillance Systems'
    WHERE discipline IN ('VSS', 'Video Security Systems', 'Video Surveillance');
    
    UPDATE submission_options_for_consideration
    SET discipline = 'Video Surveillance Systems'
    WHERE discipline IN ('VSS', 'Video Security Systems', 'Video Surveillance');
    
    UPDATE vulnerabilities
    SET discipline = 'Video Surveillance Systems'
    WHERE discipline IN ('VSS', 'Video Security Systems', 'Video Surveillance');
    
    UPDATE options_for_consideration
    SET discipline = 'Video Surveillance Systems'
    WHERE discipline IN ('VSS', 'Video Security Systems', 'Video Surveillance');
    
    UPDATE phase3_records
    SET discipline = 'Video Surveillance Systems'
    WHERE discipline IN ('VSS', 'Video Security Systems', 'Video Surveillance');
    
    UPDATE ofc_requests
    SET discipline = 'Video Surveillance Systems'
    WHERE discipline IN ('VSS', 'Video Security Systems', 'Video Surveillance');
    
    -- Mapping: Physical Security → Interior Security & Physical Barriers
    UPDATE submission_vulnerabilities
    SET discipline = 'Interior Security & Physical Barriers'
    WHERE discipline IN ('Physical Security', 'Asset Protection');
    
    UPDATE submission_options_for_consideration
    SET discipline = 'Interior Security & Physical Barriers'
    WHERE discipline IN ('Physical Security', 'Asset Protection');
    
    UPDATE vulnerabilities
    SET discipline = 'Interior Security & Physical Barriers'
    WHERE discipline IN ('Physical Security', 'Asset Protection');
    
    UPDATE options_for_consideration
    SET discipline = 'Interior Security & Physical Barriers'
    WHERE discipline IN ('Physical Security', 'Asset Protection');
    
    UPDATE phase3_records
    SET discipline = 'Interior Security & Physical Barriers'
    WHERE discipline IN ('Physical Security', 'Asset Protection');
    
    UPDATE ofc_requests
    SET discipline = 'Interior Security & Physical Barriers'
    WHERE discipline IN ('Physical Security', 'Asset Protection');
    
    -- Mapping: Security Force → Security Force / Operations
    UPDATE submission_vulnerabilities
    SET discipline = 'Security Force / Operations'
    WHERE discipline IN ('Security Force', 'Security Operations');
    
    UPDATE submission_options_for_consideration
    SET discipline = 'Security Force / Operations'
    WHERE discipline IN ('Security Force', 'Security Operations');
    
    UPDATE vulnerabilities
    SET discipline = 'Security Force / Operations'
    WHERE discipline IN ('Security Force', 'Security Operations');
    
    UPDATE options_for_consideration
    SET discipline = 'Security Force / Operations'
    WHERE discipline IN ('Security Force', 'Security Operations');
    
    UPDATE phase3_records
    SET discipline = 'Security Force / Operations'
    WHERE discipline IN ('Security Force', 'Security Operations');
    
    UPDATE ofc_requests
    SET discipline = 'Security Force / Operations'
    WHERE discipline IN ('Security Force', 'Security Operations');
    
    -- Mapping: Emergency Response → Emergency Management & Resilience
    UPDATE submission_vulnerabilities
    SET discipline = 'Emergency Management & Resilience'
    WHERE discipline IN ('Emergency Response', 'Business Continuity');
    
    UPDATE submission_options_for_consideration
    SET discipline = 'Emergency Management & Resilience'
    WHERE discipline IN ('Emergency Response', 'Business Continuity');
    
    UPDATE vulnerabilities
    SET discipline = 'Emergency Management & Resilience'
    WHERE discipline IN ('Emergency Response', 'Business Continuity');
    
    UPDATE options_for_consideration
    SET discipline = 'Emergency Management & Resilience'
    WHERE discipline IN ('Emergency Response', 'Business Continuity');
    
    UPDATE phase3_records
    SET discipline = 'Emergency Management & Resilience'
    WHERE discipline IN ('Emergency Response', 'Business Continuity');
    
    UPDATE ofc_requests
    SET discipline = 'Emergency Management & Resilience'
    WHERE discipline IN ('Emergency Response', 'Business Continuity');
    
    -- Mapping: Data Protection → Cyber-Physical Infrastructure Support
    UPDATE submission_vulnerabilities
    SET discipline = 'Cyber-Physical Infrastructure Support'
    WHERE discipline IN ('Data Protection', 'Network Security');
    
    UPDATE submission_options_for_consideration
    SET discipline = 'Cyber-Physical Infrastructure Support'
    WHERE discipline IN ('Data Protection', 'Network Security');
    
    UPDATE vulnerabilities
    SET discipline = 'Cyber-Physical Infrastructure Support'
    WHERE discipline IN ('Data Protection', 'Network Security');
    
    UPDATE options_for_consideration
    SET discipline = 'Cyber-Physical Infrastructure Support'
    WHERE discipline IN ('Data Protection', 'Network Security');
    
    UPDATE phase3_records
    SET discipline = 'Cyber-Physical Infrastructure Support'
    WHERE discipline IN ('Data Protection', 'Network Security');
    
    UPDATE ofc_requests
    SET discipline = 'Cyber-Physical Infrastructure Support'
    WHERE discipline IN ('Data Protection', 'Network Security');
    
    -- Mapping: Security Policy/Training/Awareness/Assessment/Management/Vulnerability Management → Security Management & Governance
    UPDATE submission_vulnerabilities
    SET discipline = 'Security Management & Governance'
    WHERE discipline IN (
        'Security Policy', 'Security Training', 'Security Awareness', 
        'Security Assessment', 'Security Management', 'Vulnerability Management'
    );
    
    UPDATE submission_options_for_consideration
    SET discipline = 'Security Management & Governance'
    WHERE discipline IN (
        'Security Policy', 'Security Training', 'Security Awareness', 
        'Security Assessment', 'Security Management', 'Vulnerability Management'
    );
    
    UPDATE vulnerabilities
    SET discipline = 'Security Management & Governance'
    WHERE discipline IN (
        'Security Policy', 'Security Training', 'Security Awareness', 
        'Security Assessment', 'Security Management', 'Vulnerability Management'
    );
    
    UPDATE options_for_consideration
    SET discipline = 'Security Management & Governance'
    WHERE discipline IN (
        'Security Policy', 'Security Training', 'Security Awareness', 
        'Security Assessment', 'Security Management', 'Vulnerability Management'
    );
    
    UPDATE phase3_records
    SET discipline = 'Security Management & Governance'
    WHERE discipline IN (
        'Security Policy', 'Security Training', 'Security Awareness', 
        'Security Assessment', 'Security Management', 'Vulnerability Management'
    );
    
    UPDATE ofc_requests
    SET discipline = 'Security Management & Governance'
    WHERE discipline IN (
        'Security Policy', 'Security Training', 'Security Awareness', 
        'Security Assessment', 'Security Management', 'Vulnerability Management'
    );
    
    -- DELETE mappings: Set to NULL for deleted disciplines
    UPDATE submission_vulnerabilities
    SET discipline = NULL
    WHERE discipline IN ('Cybersecurity', 'Incident Response', 'General', 'Other');
    
    UPDATE submission_options_for_consideration
    SET discipline = NULL
    WHERE discipline IN ('Cybersecurity', 'Incident Response', 'General', 'Other');
    
    UPDATE vulnerabilities
    SET discipline = NULL
    WHERE discipline IN ('Cybersecurity', 'Incident Response', 'General', 'Other');
    
    UPDATE options_for_consideration
    SET discipline = NULL
    WHERE discipline IN ('Cybersecurity', 'Incident Response', 'General', 'Other');
    
    UPDATE phase3_records
    SET discipline = NULL
    WHERE discipline IN ('Cybersecurity', 'Incident Response', 'General', 'Other');
    
    UPDATE ofc_requests
    SET discipline = NULL
    WHERE discipline IN ('Cybersecurity', 'Incident Response', 'General', 'Other');
    
    RAISE NOTICE 'Discipline system rewrite completed successfully';
    
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'Error in discipline system rewrite: %', SQLERRM;
END $$;

