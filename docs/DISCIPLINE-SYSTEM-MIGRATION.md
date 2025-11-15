# Discipline System Migration Summary

## Overview
This document summarizes the hard migration from the old discipline taxonomy to the new CISA-aligned 10-discipline system with sub-disciplines.

## Migration Date
2025-01-16

## Completed Tasks

### 1. Database Schema Changes ✅
- **Migration File**: `supabase/migrations/2025-01-16_discipline_system_rewrite.sql`
  - Replaced existing disciplines with 10 new CISA-aligned disciplines
  - Created `discipline_subtypes` table
  - Added `discipline_subtype_id` columns to 6 affected tables:
    - `submission_vulnerabilities`
    - `submission_options_for_consideration`
    - `vulnerabilities`
    - `options_for_consideration`
    - `phase3_records`
    - `ofc_requests`
  - Updated legacy discipline text values using mapping
  - Created backup table `disciplines_backup` for rollback support

- **Rollback Migration**: `supabase/migrations/2025-01-16_discipline_system_rewrite_rollback.sql`
  - Removes discipline_subtype_id columns
  - Drops discipline_subtypes table
  - Restores original disciplines from backup

- **Phase3 Trigger Update**: `supabase/migrations/2025-01-16_update_phase3_trigger_for_subtypes.sql`
  - Updated trigger function to include discipline_subtype_id

### 2. Backend Updates ✅
- **New Module**: `services/processor/normalization/discipline_resolver.py`
  - Normalizes raw discipline text to 10 new disciplines
  - Infers sub-disciplines using keyword heuristics
  - Handles legacy discipline mappings
  - Rejects pure cyber inputs unless ESS-related

- **Updated Files**:
  - `services/postprocess.py`: Uses new discipline resolver and includes subtype_id
  - `services/processor/normalization/supabase_upload.py`: Includes discipline_subtype_id in inserts
  - `services/processor/normalization/__init__.py`: Exports new resolver functions

### 3. Frontend Updates (Partial) ✅
- **API Routes**:
  - `app/api/disciplines/route.js`: Updated to include subtypes in response
  - `app/api/disciplines/subtypes/route.js`: New route for fetching subtypes

- **Submission Form**:
  - `app/submit/page.jsx`: Updated to use new discipline system
    - Fetches disciplines from API
    - Shows 10-discipline dropdown
    - Shows subtype dropdown when discipline selected
    - Includes discipline_id and discipline_subtype_id in submissions

## Remaining Tasks

### 1. API Routes (Need Updates)
The following API routes need to be updated to include `discipline_id` and `discipline_subtype_id`:

- [ ] `app/api/submissions/[id]/approve/route.js` - Include subtype_id when approving
- [ ] `app/api/submissions/[id]/vulnerabilities/[vulnId]/route.js` - Include subtype_id in updates
- [ ] `app/api/submissions/[id]/ofcs/[ofcId]/route.js` - Include subtype_id in updates
- [ ] `app/api/admin/vulnerabilities/route.js` - Include subtype_id in responses
- [ ] `app/api/admin/ofcs/route.js` - Include subtype_id in responses
- [ ] `app/api/submissions/[id]/route.js` - Include subtype_id in GET response

### 2. Frontend Pages (Need Updates)
- [ ] `app/admin/review/page.jsx` - Display discipline and subtype, allow editing
- [ ] `app/admin/disciplines/page.jsx` - Create admin page to manage disciplines and subtypes
- [ ] `app/page.jsx` - Update library search to filter by new disciplines
- [ ] `app/components/components/SubmissionReview.jsx` - Display discipline and subtype
- [ ] `app/components/components/OFCRequestsReview.jsx` - Display discipline and subtype

### 3. Backend Pipeline (May Need Updates)
- [ ] Check `parse_engine_results.py` if it exists
- [ ] Check `phase3/collector.py` if it exists
- [ ] Verify all pipeline steps handle normalized disciplines

## New Discipline Taxonomy

### 10 Master Disciplines
1. Security Management & Governance (SMG)
2. Access Control Systems (ACS)
3. Video Surveillance Systems (VSS)
4. Intrusion Detection Systems (IDS)
5. Perimeter Security (PER)
6. Interior Security & Physical Barriers (INT)
7. Security Force / Operations (SFO)
8. Emergency Management & Resilience (EMR)
9. Information Sharing & Coordination (ISC)
10. Cyber-Physical Infrastructure Support (CPI)

### Discipline Subtypes
Each discipline has specific subtypes. See migration SQL for complete list.

## Legacy Discipline Mappings

| Old Discipline | New Discipline |
|---------------|----------------|
| Access Control | Access Control Systems |
| Visitor Management | Access Control Systems |
| Identity Management | Access Control Systems |
| VSS / Video Security Systems | Video Surveillance Systems |
| Physical Security | Interior Security & Physical Barriers |
| Asset Protection | Interior Security & Physical Barriers |
| Security Force | Security Force / Operations |
| Security Operations | Security Force / Operations |
| Emergency Response | Emergency Management & Resilience |
| Business Continuity | Emergency Management & Resilience |
| Data Protection | Cyber-Physical Infrastructure Support |
| Network Security | Cyber-Physical Infrastructure Support |
| Security Policy | Security Management & Governance |
| Security Training | Security Management & Governance |
| Security Awareness | Security Management & Governance |
| Security Assessment | Security Management & Governance |
| Security Management | Security Management & Governance |
| Vulnerability Management | Security Management & Governance |
| Cybersecurity | DELETE (set to NULL) |
| Incident Response | DELETE (set to NULL) |
| General | DELETE (set to NULL) |
| Other | DELETE (set to NULL) |

## Testing Checklist

- [x] Run migration on production database ✅ (2025-01-16)
- [ ] Verify 10 disciplines created (run verification queries)
- [ ] Verify subtypes populated correctly (run verification queries)
- [ ] Test discipline normalization in backend
- [ ] Test subtype inference
- [ ] Test submission form with new disciplines
- [ ] Test API routes return discipline_id and subtype_id
- [ ] Test review pages display correctly
- [ ] Test phase3_records trigger includes subtype_id
- [ ] Test rollback migration (optional - rollback file ready)

## Rollback Procedure

If rollback is needed:
1. Run `supabase/migrations/2025-01-16_discipline_system_rewrite_rollback.sql`
2. Verify disciplines restored from backup
3. Verify subtype columns removed
4. Update frontend to use old discipline system

## Notes

- All migrations are idempotent (safe to run multiple times)
- Backup table `disciplines_backup` is created automatically
- Legacy discipline text values are updated in place
- New columns are nullable to allow gradual migration
- Phase3 trigger automatically includes subtype_id when available

