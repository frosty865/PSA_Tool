# Table-Code Alignment Analysis

## Overview

This document analyzes the alignment between the database table schemas and the code that inserts data into them, ensuring all fields are properly mapped.

---

## Table: `submission_sources`

### Schema Fields
- `id` (uuid, auto)
- `submission_id` (uuid, NOT NULL)
- `source_text` (text, nullable)
- `reference_number` (text, nullable)
- `source_title` (text, nullable)
- `source_url` (text, nullable)
- `author_org` (text, nullable)
- `publication_year` (integer, nullable)
- `content_restriction` (text, nullable)
- `created_at` (timestamptz, auto)
- `updated_at` (timestamptz, auto)

### Code Mapping (services/submission_saver.py)
✅ **All fields properly mapped:**
- `submission_id` - Set from parameter
- `source_title` - From `source_data.get('source_title')`
- `author_org` - From `source_data.get('author_org')`
- `publication_year` - From `source_data.get('publication_year')`
- `source_url` - From `source_data.get('source_url')`
- `content_restriction` - From `source_data.get('content_restriction', 'public')`
- `source_text` - From `source_data.get('source_text')` (nullable)
- `reference_number` - From `source_data.get('reference_number')` (nullable)

**Status**: ✅ Aligned

---

## Table: `submission_vulnerabilities`

### Schema Fields
- `id` (uuid, auto)
- `submission_id` (uuid, NOT NULL)
- `vulnerability` (text, nullable)
- `discipline` (text, nullable)
- `source` (text, nullable)
- `source_title` (text, nullable)
- `source_url` (text, nullable)
- `vulnerability_count` (integer, nullable)
- `ofc_count` (integer, nullable)
- `enhanced_extraction` (jsonb, nullable)
- `parsed_at` (timestamptz, nullable)
- `parser_version` (text, nullable)
- `extraction_stats` (jsonb, nullable)
- `question` (text, nullable)
- `what` (text, nullable)
- `so_what` (text, nullable)
- `sector` (text, nullable)
- `subsector` (text, nullable)
- `created_at` (timestamptz, auto)
- `updated_at` (timestamptz, auto)

### Code Mapping (services/submission_saver.py)
✅ **All required fields mapped:**
- `submission_id` - Set from parameter
- `vulnerability` - From `vuln.get('vulnerability')`
- `discipline` - From `vuln.get('discipline')`
- `source` - From `vuln.get('source')`
- `source_title` - From `vuln.get('source_title')`
- `source_url` - From `vuln.get('source_url')`
- `sector` - From `vuln.get('sector')`
- `subsector` - From `vuln.get('subsector')`
- `parser_version` - From `vuln.get('parser_version')`
- `enhanced_extraction` - From `vuln.get('enhanced_extraction', {})`

**Optional fields not set** (nullable, OK to omit):
- `vulnerability_count`, `ofc_count`, `parsed_at`, `extraction_stats`, `question`, `what`, `so_what`

**Status**: ✅ Aligned

---

## Table: `submission_options_for_consideration`

### Schema Fields
- `id` (uuid, auto)
- `submission_id` (uuid, NOT NULL)
- `vulnerability_id` (uuid, nullable)
- `option_text` (text, nullable)
- `title` (text, nullable)
- `description` (text, nullable)
- `discipline` (text, nullable)
- `source` (text, nullable)
- `source_title` (text, nullable)
- `source_url` (text, nullable)
- `confidence_score` (decimal, nullable)
- `pattern_matched` (text, nullable)
- `context` (text, nullable)
- `citations` (jsonb, nullable)
- `linked_vulnerability` (text, nullable)
- `created_at` (timestamptz, auto)
- `updated_at` (timestamptz, auto)

### Code Mapping (services/submission_saver.py)
✅ **All required fields mapped:**
- `submission_id` - Set from parameter
- `vulnerability_id` - Set to `None` (links created via junction table)
- `option_text` - From `ofc.get('option_text')`
- `discipline` - From `ofc.get('discipline')`
- `source` - From `ofc.get('source')`
- `source_title` - From `ofc.get('source_title')`
- `source_url` - From `ofc.get('source_url')`
- `confidence_score` - From `ofc.get('confidence_score')`
- `pattern_matched` - From `ofc.get('pattern_matched')`
- `context` - From `ofc.get('context')`
- `citations` - From `ofc.get('citations', [])`

**Optional fields not set** (nullable, OK to omit):
- `title`, `description`, `linked_vulnerability`

**Status**: ✅ Aligned

---

## Table: `submission_vulnerability_ofc_links`

### Schema Fields
- `id` (uuid, auto)
- `submission_id` (uuid, NOT NULL)
- `vulnerability_id` (uuid, NOT NULL)
- `ofc_id` (uuid, NOT NULL)
- `link_type` (text, nullable)
- `confidence_score` (decimal, nullable)
- `created_at` (timestamptz, auto)

### Code Mapping (services/submission_saver.py)
✅ **All required fields mapped:**
- `submission_id` - Set from parameter
- `vulnerability_id` - Matched from saved vulnerabilities by section
- `ofc_id` - Matched from saved OFCs by section
- `link_type` - From `link.get('link_type', 'inferred')` or `'direct'` for same section
- `confidence_score` - From `link.get('confidence_score', 0.7)` or `0.9` for same section

**Matching Logic:**
1. Uses links from extraction results (with section info)
2. Matches vulnerabilities and OFCs by section number
3. Falls back to same-section linking if no extraction links provided

**Status**: ✅ Aligned (improved matching logic)

---

## Table: `submission_ofc_sources`

### Schema Fields
- `id` (uuid, auto)
- `submission_id` (uuid, NOT NULL)
- `ofc_id` (uuid, NOT NULL)
- `source_id` (uuid, NOT NULL)
- `created_at` (timestamptz, auto)

### Code Mapping (services/submission_saver.py)
✅ **All required fields mapped:**
- `submission_id` - Set from parameter
- `ofc_id` - From saved OFCs
- `source_id` - From saved source record

**Status**: ✅ Aligned

---

## Key Improvements Made

1. **Source Record Structure**: Fixed to include all table fields (including nullable `source_text` and `reference_number`)

2. **Link Matching**: Improved to use extraction results with section-based matching:
   - Uses `vulnerability_section` and `ofc_section` from extraction links
   - Matches by section number after vulnerabilities/OFCs are saved
   - Falls back to same-section linking if no extraction links provided

3. **ID Tracking**: Changed from simple text keys to `(section, text)` tuples for better matching:
   - Vulnerabilities: `(section, vulnerability_text)` → `vuln_id`
   - OFCs: `(section, option_text)` → `ofc_id`

4. **Error Handling**: Added null checks for `source_id` before creating source-OFC links

---

## Testing Checklist

- [ ] Test submission creation with all fields
- [ ] Test vulnerability extraction and saving
- [ ] Test OFC extraction and saving
- [ ] Test link creation (same section)
- [ ] Test link creation (cross-section, if implemented)
- [ ] Test source-OFC link creation
- [ ] Verify all foreign key constraints are satisfied
- [ ] Verify cascade deletes work correctly

---

## Notes

- All nullable fields are properly handled (not set if not provided)
- Foreign key relationships are maintained
- Timestamps are auto-generated by database
- UUIDs are auto-generated by database
- Link matching uses section-based proximity (same section = direct link, confidence 0.9)

