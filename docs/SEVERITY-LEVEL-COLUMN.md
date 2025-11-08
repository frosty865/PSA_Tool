# Severity Level Column Migration

## Overview

Added optional `severity_level` column to both submission and production vulnerability tables to support DHS-style matrix surveys and other structured documents with explicit severity classifications.

## Changes Made

### 1. Database Schema

**Migration Script**: `scripts/add-severity-level-columns.sql`

- Added `severity_level` column to `submission_vulnerabilities` table
- Added `severity_level` column to `vulnerabilities` (production) table
- Added indexes for performance (filtering/sorting by severity)
- Column is nullable for backward compatibility

**Supported Values**:
- "Very Low"
- "Low"
- "Medium"
- "High"
- "Very High"

### 2. Code Updates

#### `services/supabase_sync.py`
- Updated to include `severity_level` when syncing vulnerabilities to `submission_vulnerabilities`
- Reads from `v.severity_level` in the processed result data

#### `app/api/submissions/[id]/approve/route.js`
- Updated to copy `severity_level` from submission to production when approving
- Includes `severity_level: v.severity_level || null` in production vulnerability insert

#### `app/api/submissions/[id]/approve-vulnerability/route.js`
- Updated to include `severity_level` when inserting individual vulnerabilities
- Falls back to `severity` field if `severity_level` not present (backward compatibility)

#### `ollama_auto_processor.py`
- Matrix survey parser conversion already includes `severity_level` in vulnerability records
- Standard pipeline can also include `severity_level` if present in processed results

## Usage

### Matrix Survey Parser

The matrix survey parser automatically extracts and sets `severity_level` for each vulnerability:

```python
{
    "vulnerability": "Vulnerability description",
    "severity_level": "High",  # From matrix survey
    "options_for_consideration": [...]
}
```

### Manual Submissions

When creating submissions manually, you can include `severity_level`:

```json
{
    "vulnerabilities": [
        {
            "vulnerability": "Description",
            "severity_level": "Medium"
        }
    ]
}
```

## Database Migration

Run the migration script in Supabase SQL Editor:

```sql
-- Run scripts/add-severity-level-columns.sql
```

This will:
1. Add the column to both tables
2. Create indexes for performance
3. Add column comments for documentation

## Verification

After running the migration, verify with:

```sql
SELECT 
    table_name, 
    column_name, 
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name IN ('submission_vulnerabilities', 'vulnerabilities')
AND column_name = 'severity_level';
```

## Backward Compatibility

- Column is nullable - existing records will have `NULL` severity_level
- All code gracefully handles missing `severity_level` values
- No breaking changes to existing functionality

## Future Enhancements

Optional improvements:
- Add CHECK constraint to enforce valid values
- Create views/reports filtered by severity level
- Add severity-based analytics and dashboards

