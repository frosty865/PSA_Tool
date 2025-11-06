# Supabase Database Schema Documentation

## Overview

The PSA Tool uses Supabase (PostgreSQL) as its database backend. The schema is organized into several logical groups:

1. **Submission Management** - User-submitted data awaiting review
2. **Production Data** - Approved vulnerabilities and OFCs
3. **Taxonomy** - Sectors, subsectors, and disciplines
4. **User Management** - Authentication and authorization
5. **Learning System** - ML training events
6. **OFC Requests** - Workflow for requesting new OFCs

---

## Table Relationships Diagram

```
submissions
  ├── submission_vulnerabilities (1:N)
  │     ├── submission_vulnerability_ofc_links (1:N)
  │     └── submission_options_for_consideration (N:M)
  ├── submission_sources (1:N)
  └── submission_ofc_sources (1:N)

vulnerabilities (production)
  ├── vulnerability_ofc_links (1:N)
  └── options_for_consideration (N:M via links)
        └── ofc_sources (1:N)
              └── sources (N:1)

sectors
  └── subsectors (1:N)

user_profiles
  └── user_agency_relationships (1:N)
```

---

## 1. Submission Management Tables

### `submissions`

Main submission table storing user-submitted documents and data.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `type` | `text` | Submission type: `'vulnerability'`, `'ofc'`, `'document'` |
| `status` | `text` | Status: `'pending'`, `'pending_review'`, `'approved'`, `'rejected'` |
| `data` | `jsonb` | Flexible JSON storage for submission data |
| `source` | `text` | Source identifier (e.g., `'bulk_csv'`, `'manual'`, `'document_upload'`) |
| `submitter_email` | `text` | Email of the submitter |
| `submitted_by` | `uuid` | Foreign key to `auth.users.id` |
| `reviewed_by` | `uuid` | Foreign key to `auth.users.id` (reviewer) |
| `reviewed_at` | `timestamptz` | Timestamp when reviewed |
| `review_comments` | `text` | Comments from reviewer |
| `rejection_reason` | `text` | Reason for rejection (if rejected) |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- `submitted_by` → `auth.users.id`
- `reviewed_by` → `auth.users.id`
- Has many `submission_vulnerabilities`
- Has many `submission_options_for_consideration`
- Has many `submission_sources`

**Indexes:**
- `idx_submissions_status` on `status`
- `idx_submissions_type` on `type`
- `idx_submissions_submitted_by` on `submitted_by`

---

### `submission_vulnerabilities`

Vulnerabilities extracted from submission documents.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `submission_id` | `uuid` | Foreign key to `submissions.id` |
| `vulnerability` | `text` | Vulnerability description |
| `discipline` | `text` | Discipline/category |
| `source` | `text` | Source reference |
| `source_title` | `text` | Source document title |
| `source_url` | `text` | Source URL |
| `vulnerability_count` | `integer` | Number of vulnerabilities found |
| `ofc_count` | `integer` | Number of associated OFCs |
| `enhanced_extraction` | `jsonb` | Enhanced extraction metadata |
| `parsed_at` | `timestamptz` | When parsing occurred |
| `parser_version` | `text` | Parser version used |
| `extraction_stats` | `jsonb` | Extraction statistics |
| `question` | `text` | Structured field: question |
| `what` | `text` | Structured field: what |
| `so_what` | `text` | Structured field: so what |
| `sector` | `text` | Sector classification |
| `subsector` | `text` | Subsector classification |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- `submission_id` → `submissions.id` (CASCADE DELETE)
- Has many `submission_options_for_consideration` (via `vulnerability_id`)
- Has many `submission_vulnerability_ofc_links`

**Indexes:**
- `idx_submission_vuln_submission_id` on `submission_id`
- `idx_submission_vuln_discipline` on `discipline`

---

### `submission_options_for_consideration`

Options for Consideration (OFCs) extracted from submissions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `submission_id` | `uuid` | Foreign key to `submissions.id` |
| `vulnerability_id` | `uuid` | Foreign key to `submission_vulnerabilities.id` (nullable) |
| `option_text` | `text` | OFC text content |
| `title` | `text` | OFC title (optional) |
| `description` | `text` | OFC description (optional) |
| `discipline` | `text` | Discipline/category |
| `source` | `text` | Source reference |
| `source_title` | `text` | Source document title |
| `source_url` | `text` | Source URL |
| `confidence_score` | `decimal` | Confidence score (0.0-1.0) |
| `pattern_matched` | `text` | Pattern that matched (if applicable) |
| `context` | `text` | Contextual information |
| `citations` | `jsonb` | Array of citations |
| `linked_vulnerability` | `text` | Text reference to linked vulnerability |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- `submission_id` → `submissions.id` (CASCADE DELETE)
- `vulnerability_id` → `submission_vulnerabilities.id` (nullable, SET NULL on delete)
- Has many `submission_ofc_sources`

**Indexes:**
- `idx_submission_ofc_submission_id` on `submission_id`
- `idx_submission_ofc_vulnerability_id` on `vulnerability_id`

---

### `submission_sources`

Source documents/references from submissions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `submission_id` | `uuid` | Foreign key to `submissions.id` |
| `source_text` | `text` | Source text/reference |
| `reference_number` | `text` | Reference number (e.g., `REF-123456`) |
| `source_title` | `text` | Source document title |
| `source_url` | `text` | Source URL |
| `author_org` | `text` | Author organization |
| `publication_year` | `integer` | Publication year |
| `content_restriction` | `text` | Content restriction level (e.g., `'public'`, `'restricted'`) |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- `submission_id` → `submissions.id` (CASCADE DELETE)

**Indexes:**
- `idx_submission_sources_submission_id` on `submission_id`

---

### `submission_vulnerability_ofc_links`

Junction table linking submission vulnerabilities to OFCs.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `submission_id` | `uuid` | Foreign key to `submissions.id` |
| `vulnerability_id` | `uuid` | Foreign key to `submission_vulnerabilities.id` |
| `ofc_id` | `uuid` | Foreign key to `submission_options_for_consideration.id` |
| `link_type` | `text` | Link type (e.g., `'direct'`, `'inferred'`) |
| `confidence_score` | `decimal` | Confidence score (0.0-1.0) |
| `created_at` | `timestamptz` | Creation timestamp |

**Relationships:**
- `submission_id` → `submissions.id` (CASCADE DELETE)
- `vulnerability_id` → `submission_vulnerabilities.id` (CASCADE DELETE)
- `ofc_id` → `submission_options_for_consideration.id` (CASCADE DELETE)

**Indexes:**
- `idx_submission_vuln_ofc_links_submission_id` on `submission_id`
- `idx_submission_vuln_ofc_links_vuln_id` on `vulnerability_id`
- `idx_submission_vuln_ofc_links_ofc_id` on `ofc_id`

---

### `submission_ofc_sources`

Junction table linking submission OFCs to sources.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `submission_id` | `uuid` | Foreign key to `submissions.id` |
| `ofc_id` | `uuid` | Foreign key to `submission_options_for_consideration.id` |
| `source_id` | `uuid` | Foreign key to `submission_sources.id` |
| `created_at` | `timestamptz` | Creation timestamp |

**Relationships:**
- `submission_id` → `submissions.id` (CASCADE DELETE)
- `ofc_id` → `submission_options_for_consideration.id` (CASCADE DELETE)
- `source_id` → `submission_sources.id` (CASCADE DELETE)

**Indexes:**
- `idx_submission_ofc_sources_submission_id` on `submission_id`
- `idx_submission_ofc_sources_ofc_id` on `ofc_id`
- `idx_submission_ofc_sources_source_id` on `source_id`

---

## 2. Production Data Tables

### `vulnerabilities`

Approved/production vulnerabilities.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `vulnerability_name` | `text` | Vulnerability name/title |
| `description` | `text` | Vulnerability description |
| `discipline` | `text` | Discipline/category |
| `sector_id` | `uuid` | Foreign key to `sectors.id` (nullable) |
| `subsector_id` | `uuid` | Foreign key to `subsectors.id` (nullable) |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- `sector_id` → `sectors.id` (nullable)
- `subsector_id` → `subsectors.id` (nullable)
- Has many `vulnerability_ofc_links`

**Indexes:**
- `idx_vulnerabilities_sector_id` on `sector_id`
- `idx_vulnerabilities_subsector_id` on `subsector_id`
- `idx_vulnerabilities_discipline` on `discipline`

---

### `options_for_consideration`

Approved/production Options for Consideration.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `option_text` | `text` | OFC text content |
| `discipline` | `text` | Discipline/category |
| `sector_id` | `uuid` | Foreign key to `sectors.id` (nullable) |
| `subsector_id` | `uuid` | Foreign key to `subsectors.id` (nullable) |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- `sector_id` → `sectors.id` (nullable)
- `subsector_id` → `subsectors.id` (nullable)
- Has many `vulnerability_ofc_links`
- Has many `ofc_sources`

**Indexes:**
- `idx_options_sector_id` on `sector_id`
- `idx_options_subsector_id` on `subsector_id`
- `idx_options_discipline` on `discipline`

---

### `vulnerability_ofc_links`

Junction table linking production vulnerabilities to OFCs.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `vulnerability_id` | `uuid` | Foreign key to `vulnerabilities.id` |
| `ofc_id` | `uuid` | Foreign key to `options_for_consideration.id` |
| `link_type` | `text` | Link type (e.g., `'direct'`, `'inferred'`, `'recommended'`) |
| `confidence_score` | `decimal` | Confidence score (0.0-1.0) |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- `vulnerability_id` → `vulnerabilities.id` (CASCADE DELETE)
- `ofc_id` → `options_for_consideration.id` (CASCADE DELETE)

**Indexes:**
- `idx_vuln_ofc_links_vuln_id` on `vulnerability_id`
- `idx_vuln_ofc_links_ofc_id` on `ofc_id`

---

### `sources`

Production source documents/references.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `source_title` | `text` | Source document title |
| `source_url` | `text` | Source URL |
| `author_org` | `text` | Author organization |
| `publication_year` | `integer` | Publication year |
| `citation` | `text` | Citation text |
| `content_restriction` | `text` | Content restriction level |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- Has many `ofc_sources`

**Indexes:**
- `idx_sources_author_org` on `author_org`
- `idx_sources_publication_year` on `publication_year`

---

### `ofc_sources`

Junction table linking production OFCs to sources.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `ofc_id` | `uuid` | Foreign key to `options_for_consideration.id` |
| `source_id` | `uuid` | Foreign key to `sources.id` |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- `ofc_id` → `options_for_consideration.id` (CASCADE DELETE)
- `source_id` → `sources.id` (CASCADE DELETE)

**Indexes:**
- `idx_ofc_sources_ofc_id` on `ofc_id`
- `idx_ofc_sources_source_id` on `source_id`

---

## 3. Taxonomy Tables

### `sectors`

Sector taxonomy for classification.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `name` | `text` | Sector name |
| `description` | `text` | Sector description |
| `code` | `text` | Sector code (e.g., `'ENERGY'`, `'TRANSPORT'`) |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- Has many `subsectors`
- Has many `vulnerabilities`
- Has many `options_for_consideration`

**Indexes:**
- `idx_sectors_code` on `code` (unique)

---

### `subsectors`

Subsector taxonomy for classification.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `sector_id` | `uuid` | Foreign key to `sectors.id` |
| `name` | `text` | Subsector name |
| `description` | `text` | Subsector description |
| `code` | `text` | Subsector code |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- `sector_id` → `sectors.id` (CASCADE DELETE)
- Has many `vulnerabilities`
- Has many `options_for_consideration`

**Indexes:**
- `idx_subsectors_sector_id` on `sector_id`
- `idx_subsectors_code` on `code`

---

### `disciplines`

Discipline taxonomy for classification.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `name` | `text` | Discipline name |
| `description` | `text` | Discipline description |
| `code` | `text` | Discipline code |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Indexes:**
- `idx_disciplines_code` on `code` (unique)

---

## 4. User Management Tables

### `user_profiles`

Extended user profile information (extends Supabase `auth.users`).

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | `uuid` | Primary key, foreign key to `auth.users.id` |
| `username` | `text` | Username |
| `first_name` | `text` | First name |
| `last_name` | `text` | Last name |
| `role` | `text` | User role: `'admin'`, `'supervisor'`, `'user'` |
| `organization` | `text` | Organization/agency (e.g., `'CISA'`) |
| `is_active` | `boolean` | Whether user is active |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- `user_id` → `auth.users.id` (CASCADE DELETE)
- Has many `user_agency_relationships`

**Indexes:**
- `idx_user_profiles_user_id` on `user_id` (unique)
- `idx_user_profiles_role` on `role`
- `idx_user_profiles_organization` on `organization`

---

### `user_agency_relationships`

Multi-agency support for Row Level Security (RLS).

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `user_id` | `uuid` | Foreign key to `auth.users.id` |
| `agency_id` | `uuid` | Agency identifier (can reference `sectors.id` or separate agency table) |
| `role_id` | `uuid` | Role identifier within agency |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- `user_id` → `auth.users.id` (CASCADE DELETE)

**Indexes:**
- `idx_user_agency_relationships_user_id` on `user_id`
- `idx_user_agency_relationships_agency_id` on `agency_id`

**Note:** This table supports multi-agency RLS where users can belong to multiple agencies with different roles.

---

## 5. Learning System Tables

### `learning_events`

Machine learning training events for improving extraction accuracy.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `submission_id` | `uuid` | Foreign key to `submissions.id` (nullable) |
| `event_type` | `text` | Event type: `'approval'`, `'rejection'`, `'correction'` |
| `approved` | `boolean` | Whether the event represents an approved example |
| `model_version` | `text` | Model version (e.g., `'psa-engine:latest'`) |
| `confidence_score` | `decimal` | Confidence score (0.0-1.0) |
| `metadata` | `jsonb` | Additional event metadata (vulnerability_id, ofc_count, etc.) |
| `created_at` | `timestamptz` | Creation timestamp |

**Relationships:**
- `submission_id` → `submissions.id` (nullable, SET NULL on delete)

**Indexes:**
- `idx_learning_events_submission_id` on `submission_id`
- `idx_learning_events_event_type` on `event_type`
- `idx_learning_events_approved` on `approved`
- `idx_learning_events_created_at` on `created_at`

**Note:** This table feeds the learning algorithm with positive (approved) and negative (rejected) examples to improve extraction accuracy.

---

## 6. OFC Request Workflow Tables

### `ofc_requests`

Requests for new Options for Consideration.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` | Primary key |
| `vulnerability_id` | `uuid` | Foreign key to `vulnerabilities.id` (nullable) |
| `vulnerability_text` | `text` | Vulnerability text (if not linked to production vulnerability) |
| `ofc_text` | `text` | Requested OFC text |
| `discipline` | `text` | Discipline/category |
| `submitter` | `text` | Email/identifier of submitter |
| `status` | `text` | Status: `'pending_review'`, `'approved'`, `'rejected'` |
| `reviewed_by` | `uuid` | Foreign key to `auth.users.id` (nullable) |
| `reviewed_at` | `timestamptz` | Review timestamp (nullable) |
| `review_comments` | `text` | Review comments (nullable) |
| `created_at` | `timestamptz` | Creation timestamp |
| `updated_at` | `timestamptz` | Last update timestamp |

**Relationships:**
- `vulnerability_id` → `vulnerabilities.id` (nullable)
- `reviewed_by` → `auth.users.id` (nullable)

**Indexes:**
- `idx_ofc_requests_vulnerability_id` on `vulnerability_id`
- `idx_ofc_requests_status` on `status`
- `idx_ofc_requests_submitter` on `submitter`

---

## Row Level Security (RLS)

### RLS Policies

The database uses Row Level Security (RLS) to enforce multi-tenant access control:

1. **User Access**: Users can only see their own submissions and approved production data
2. **Admin Access**: Admins can see all submissions and production data
3. **Supervisor Access**: Supervisors can review submissions within their agency
4. **Multi-Agency**: Users can belong to multiple agencies via `user_agency_relationships`

### RLS Notes

- Some tables may have RLS disabled for service role access (e.g., `submissions` table can be configured with RLS disabled)
- Service role key (`SUPABASE_SERVICE_ROLE_KEY`) bypasses RLS for admin operations
- Anon key (`NEXT_PUBLIC_SUPABASE_ANON_KEY`) respects RLS policies

---

## Common Query Patterns

### Get Submission with All Related Data

```sql
SELECT 
  s.*,
  json_agg(DISTINCT sv.*) as vulnerabilities,
  json_agg(DISTINCT sofc.*) as ofcs,
  json_agg(DISTINCT ss.*) as sources
FROM submissions s
LEFT JOIN submission_vulnerabilities sv ON sv.submission_id = s.id
LEFT JOIN submission_options_for_consideration sofc ON sofc.submission_id = s.id
LEFT JOIN submission_sources ss ON ss.submission_id = s.id
WHERE s.id = $1
GROUP BY s.id;
```

### Get Production Vulnerability with OFCs

```sql
SELECT 
  v.*,
  json_agg(DISTINCT jsonb_build_object(
    'ofc', ofc.*,
    'sources', json_agg(DISTINCT s.*)
  )) as ofcs
FROM vulnerabilities v
LEFT JOIN vulnerability_ofc_links vol ON vol.vulnerability_id = v.id
LEFT JOIN options_for_consideration ofc ON ofc.id = vol.ofc_id
LEFT JOIN ofc_sources os ON os.ofc_id = ofc.id
LEFT JOIN sources s ON s.id = os.source_id
WHERE v.id = $1
GROUP BY v.id;
```

### Get User Submissions

```sql
SELECT s.*
FROM submissions s
WHERE s.submitted_by = $1
ORDER BY s.created_at DESC;
```

---

## Migration Notes

### Schema Evolution

- The schema has evolved to support both flexible JSON storage (`data` JSONB column) and structured columns
- New structured columns are added gradually (e.g., `question`, `what`, `so_what` in `submission_vulnerabilities`)
- Fallback to JSON storage is used when structured columns don't exist

### Data Migration

When approving submissions:
1. Data from `submission_vulnerabilities` → `vulnerabilities`
2. Data from `submission_options_for_consideration` → `options_for_consideration`
3. Links created in `vulnerability_ofc_links`
4. Sources created/promoted to `sources` and linked via `ofc_sources`

---

## Environment Variables

Required Supabase environment variables:

```env
NEXT_PUBLIC_SUPABASE_URL=https://xyz.supabase.co
SUPABASE_URL=https://xyz.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

---

## API Endpoints Using This Schema

### Submission Endpoints
- `POST /api/submissions` - Create submission
- `GET /api/submissions` - List submissions
- `GET /api/submissions/[id]` - Get submission
- `POST /api/submissions/[id]/approve` - Approve submission (promotes to production)
- `POST /api/submissions/[id]/reject` - Reject submission
- `POST /api/submissions/structured` - Create structured submission data

### Production Data Endpoints
- `GET /api/admin/vulnerabilities` - List production vulnerabilities
- `GET /api/library/search` - Search production library

### User Management Endpoints
- `GET /api/admin/users` - List users (admin)
- `POST /api/admin/users` - Create user (admin)
- `PUT /api/admin/users` - Update user (admin)

### OFC Request Endpoints
- `POST /api/submissions/ofc-request` - Create OFC request
- `GET /api/admin/ofc-requests` - List OFC requests (admin)

---

**Last Updated:** 2024-01-XX  
**Schema Version:** 1.0.0

