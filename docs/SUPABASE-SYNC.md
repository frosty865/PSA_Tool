# Supabase Sync Integration

## Overview

The Supabase sync layer automatically uploads processed document results into Supabase submission tables, making them available for review and approval in the PSA Tool dashboard.

## Architecture

```
File Upload → Queue → Worker → Processing → JSON Result → Supabase Sync → Submission Table
```

## Components

### 1. `services/supabase_sync.py`

The sync module handles uploading processed JSON results to Supabase:

- Creates a `submissions` record
- Extracts and inserts `submission_vulnerabilities`
- Extracts and inserts `submission_options_for_consideration` (OFCs)
- Extracts and inserts `submission_sources`

### 2. Queue Worker Integration

The queue worker in `services/queue_manager.py` automatically calls the sync function after successfully processing a file.

## Workflow

### Step-by-Step Process

| Step | Trigger | Action |
|------|---------|--------|
| **1️⃣** | Worker finishes parsing file | Saves `result.json` to `data/processed/` |
| **2️⃣** | Worker calls `sync_processed_result()` | Inserts into `submissions` table |
| **3️⃣** | JSON contents parsed | Populates `submission_vulnerabilities`, `submission_options_for_consideration`, `submission_sources` |
| **4️⃣** | Submission visible in Supabase | Analysts review and promote to production via dashboard |

## Data Flow

### Input: Processed JSON Result

```json
{
  "vulnerabilities": [
    {
      "text": "Vulnerability description",
      "discipline": "Physical Security",
      "sector": "Energy",
      "subsector": "Power Generation"
    }
  ],
  "ofcs": [
    {
      "text": "Option for consideration",
      "discipline": "Physical Security",
      "confidence_score": 0.85
    }
  ],
  "sources": [
    {
      "title": "Source Document",
      "url": "https://example.com/doc.pdf",
      "author_org": "CISA",
      "year": 2024
    }
  ],
  "parser_version": "psa-engine:latest"
}
```

### Output: Supabase Tables

#### `submissions` Table
- Creates a new submission record with `type: "document"`, `status: "pending_review"`
- Stores full JSON result in `data` column
- Source set to `"psa_tool_auto"`

#### `submission_vulnerabilities` Table
- One record per vulnerability found
- Links to submission via `submission_id`
- Includes discipline, sector, subsector metadata

#### `submission_options_for_consideration` Table
- One record per OFC found
- Links to submission via `submission_id`
- Includes confidence scores and citations

#### `submission_sources` Table
- One record per source document
- Links to submission via `submission_id`
- Includes author, publication year, URL

## Configuration

### Required Environment Variables

Add to your `.env` file:

```env
SUPABASE_URL=https://wivohgbuuwxoyfyzntsd.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

**Note:** The service role key is required to bypass Row Level Security (RLS) when inserting submissions.

### Optional Configuration

- `submitter_email`: Default is `"system@psa.local"`. Can be customized per submission if needed.

## Error Handling

The sync process is **non-blocking**:

- If Supabase sync fails, the job is still marked as `"done"` (processing succeeded)
- Sync errors are logged in the job record: `job["supabase_sync_error"]`
- Individual record insertions (vulnerabilities, OFCs, sources) continue even if one fails
- Warnings are printed to console but don't stop the sync process

### Example Error Handling

```python
# In queue_manager.py
try:
    submission_id = sync_processed_result(str(out_path))
    job["supabase_submission_id"] = submission_id
except Exception as sync_err:
    job["supabase_sync_error"] = str(sync_err)
    # Job still marked as "done" - processing succeeded
```

## Job Queue Status

After processing, job records include:

```json
{
  "filename": "document.pdf",
  "status": "done",
  "result_path": "data/processed/document.pdf.json",
  "supabase_submission_id": "uuid-here",
  "supabase_sync_error": null  // or error message if sync failed
}
```

## Testing

### Manual Test

```python
from services.supabase_sync import sync_processed_result

# Sync a processed result
submission_id = sync_processed_result("data/processed/test.pdf.json")
print(f"Created submission: {submission_id}")
```

### Check Queue Status

```bash
# View queue with Supabase sync status
curl http://localhost:8080/api/process/queue
```

### Verify in Supabase

1. Go to Supabase Dashboard → Table Editor
2. Check `submissions` table for new record
3. Check related tables: `submission_vulnerabilities`, `submission_options_for_consideration`, `submission_sources`

## Troubleshooting

### Common Issues

1. **"Supabase credentials not configured"**
   - Check `.env` file has `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
   - Restart Flask service after updating `.env`

2. **"Failed to create submission record"**
   - Verify Supabase URL is correct
   - Check service role key has proper permissions
   - Check RLS policies allow inserts (or use service role key)

3. **"Failed to insert vulnerability/OFC/source"**
   - Check column names match schema (see `docs/SUPABASE-SCHEMA.md`)
   - Verify required fields are present
   - Check data types match (e.g., `confidence_score` must be decimal)

4. **Sync errors don't stop processing**
   - This is intentional - processing succeeds even if sync fails
   - Check job queue for `supabase_sync_error` field
   - Review Flask logs for detailed error messages

## Next Steps

After sync:

1. **Review in Dashboard**: Analysts review submissions in PSA Tool dashboard
2. **Approve**: Approve submissions to promote to production tables
3. **Production Data**: Approved data appears in `vulnerabilities` and `options_for_consideration` tables

See `docs/SUPABASE-SCHEMA.md` for complete schema documentation.

---

**Last Updated:** 2024-01-XX  
**Status:** ✅ Integrated and Ready

