# Sector/Subsector Classification Redesign

## Problem
Documents about K-12 schools (e.g., "Safe-Schools-Best-Practices.pdf") were being incorrectly classified as:
- Sector: "Government Facilities"
- Subsector: "Federal Facilities" (or empty)

This is incorrect - K-12 schools should be classified under "Education Facilities" sector.

## Root Cause
1. **Overly broad keyword matching**: "Government Facilities" included generic school keywords ("school", "schools", "k-12", "public school") which matched school documents
2. **No prioritization**: Education Facilities wasn't checked first, so Government Facilities would match first
3. **Vulnerability patterns**: School-related vulnerability patterns were mapped to Government Facilities instead of Education Facilities

## Solution

### 1. Created Dedicated Education Facilities Sector
- Added "Education Facilities" as a priority sector for K-12 schools
- Includes comprehensive school-related keywords: "school", "schools", "k-12", "k12", "safe school", "student", "teacher", "classroom", etc.
- Subsectors: "K-12 Schools", "Education Facilities", "Public Schools"

### 2. Removed School Keywords from Government Facilities
- Removed generic school keywords from Government Facilities
- Now only matches when there's explicit government context: "federal", "state", "local", "agency", "municipal", "courthouse", "federal facility", etc.
- Subsectors: Only "Federal Facilities", "State Facilities", "Local Facilities" (removed school-related subsectors)

### 3. Prioritized Education Facilities in Matching
- **Vulnerability pattern matching**: Education Facilities patterns are checked first, with a +3 score boost for school-related matches
- **Document title matching**: Education Facilities is checked before other sectors, with a +2 score boost for school keywords
- Ensures school documents are classified correctly even if they could match multiple sectors

### 4. Updated Vulnerability Patterns
- Moved all school-related patterns from "Government Facilities" to "Education Facilities"
- Includes: school, schools, k-12, safe school, teacher, student, classroom, elementary, middle school, high school, etc.
- Government Facilities patterns now only match explicit government facility terms

## Changes Made

### File: `services/processor/normalization/taxonomy_inference.py`

1. **SECTOR_KEYWORDS**:
   - Added "Education Facilities" as first entry with comprehensive school keywords
   - Removed school keywords from "Government Facilities"
   - Made Government Facilities keywords more specific (only government context)

2. **vulnerability_patterns**:
   - Created "Education Facilities" pattern group with all school-related patterns
   - Removed school patterns from "Government Facilities"
   - Government Facilities patterns now only match explicit government facility terms

3. **infer_sector_subsector()**:
   - Prioritizes Education Facilities in vulnerability pattern matching (checks first, +3 score boost)
   - Prioritizes Education Facilities in document title matching (checks first, +2 score boost)
   - Ensures school documents are correctly classified

## Expected Behavior

### Before
- Document: "Safe-Schools-Best-Practices.pdf"
- Classification: Sector="Government Facilities", Subsector="Federal Facilities"

### After
- Document: "Safe-Schools-Best-Practices.pdf"
- Classification: Sector="Education Facilities", Subsector="K-12 Schools"

## Validation
The system validates all inferred sectors/subsectors against Supabase:
- Checks that sector exists in `sectors` table
- Checks that subsector exists in `subsectors` table
- Validates that subsector belongs to the sector (prevents invalid combinations)
- Falls back to "General" sector if no match found

## Testing
To verify the fix works:
1. Process a school-related document (e.g., "Safe-Schools-Best-Practices.pdf")
2. Check that records are classified as:
   - Sector: "Education Facilities"
   - Subsector: "K-12 Schools" (or "Education Facilities" or "Public Schools")
3. Verify that Government Facilities is NOT used unless document has explicit government context

## Notes
- "Education" sector (separate from "Education Facilities") is for higher education (universities, colleges)
- "Education Facilities" is specifically for K-12 schools and educational facilities
- Government Facilities should only be used when there's explicit government/federal/state/local context

