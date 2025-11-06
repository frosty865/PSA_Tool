# Audit Trail System

## Overview

The audit trail system tracks all admin review actions (approve, reject, edit) and links them to the affected submissions and production records.

## Database Schema

### Table: `audit_log`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `submission_id` | UUID | Foreign key → `submissions.id` |
| `reviewer_id` | UUID | Foreign key → `users.id` (reviewer who performed the action) |
| `action` | text | Action type: `"approved"` \| `"rejected"` \| `"edited"` |
| `affected_vuln_ids` | text[] | Array of vulnerability IDs inserted into production |
| `affected_ofc_ids` | text[] | Array of OFC IDs inserted into production |
| `notes` | text | Optional reviewer comments/notes |
| `timestamp` | timestamptz | Default: `now()` |

### SQL Creation Script

```sql
CREATE TABLE IF NOT EXISTS audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id UUID REFERENCES submissions(id),
  reviewer_id UUID REFERENCES auth.users(id),
  action TEXT NOT NULL CHECK (action IN ('approved', 'rejected', 'edited')),
  affected_vuln_ids TEXT[] DEFAULT '{}',
  affected_ofc_ids TEXT[] DEFAULT '{}',
  notes TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_audit_log_submission ON audit_log(submission_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_reviewer ON audit_log(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);
```

## Implementation

### Backend

#### Audit Logger Utility (`app/lib/audit-logger.js`)

- `logAuditEvent()` - Logs audit events to Supabase
- `getReviewerId()` - Extracts reviewer ID from auth token

#### API Routes

- **Approve Route** (`app/api/submissions/[id]/approve/route.js`)
  - Logs audit event with vulnerability and OFC IDs after promotion
  - Non-blocking - approval continues even if audit logging fails

- **Reject Route** (`app/api/submissions/[id]/reject/route.js`)
  - Logs audit event with rejection reason
  - Non-blocking - rejection continues even if audit logging fails

- **Audit API** (`app/api/admin/audit/route.js`)
  - `GET /api/admin/audit` - Fetches audit logs
  - Query parameters:
    - `limit` - Number of entries to return (default: 100)
    - `action` - Filter by action type (`approved`, `rejected`, `edited`)
    - `submission_id` - Filter by submission ID

### Frontend

#### Admin Audit Page (`app/admin/audit/page.jsx`)

- Displays all audit log entries
- Filter by action type (all, approved, rejected, edited)
- Shows reviewer, submission, affected records, and notes
- Auto-refreshes every 60 seconds

## Usage

### Viewing Audit Logs

1. Navigate to `/admin/audit`
2. Use filter buttons to view specific action types
3. Each entry shows:
   - Action type with color-coded badge
   - Timestamp
   - Reviewer ID
   - Submission ID
   - Affected vulnerability IDs (if approved)
   - Affected OFC IDs (if approved)
   - Reviewer notes/comments

### Audit Log Flow

1. **Admin approves submission:**
   - Submission data promoted to production tables
   - Vulnerability IDs and OFC IDs collected
   - Audit event logged with all IDs

2. **Admin rejects submission:**
   - Submission status updated to 'rejected'
   - Audit event logged with rejection reason

3. **Admin edits submission:**
   - (Future feature - not yet implemented)

## Notes

- Audit logging is **non-blocking** - review actions continue even if audit logging fails
- If the `audit_log` table doesn't exist, the system will log warnings but continue functioning
- Reviewer ID is extracted from the authorization token automatically
- All timestamps are stored in UTC

