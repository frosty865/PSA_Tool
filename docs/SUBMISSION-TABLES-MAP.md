# Submission Tables Complete Mapping

## Overview

This document provides a complete mapping of all submission-related tables, their columns, relationships, and constraints.

---

## Table: `submissions`

**Purpose**: Main table storing user-submitted documents and data awaiting review.

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | Primary key |
| `type` | `text` | NO | - | **CHECK CONSTRAINT**: Must be `'vulnerability'` or `'ofc'` |
| `status` | `text` | NO | - | Status: `'pending'`, `'pending_review'`, `'approved'`, `'rejected'` |
| `data` | `jsonb` | YES | - | Flexible JSON storage for submission data |
| `source` | `text` | YES | - | Source identifier (e.g., `'bulk_csv'`, `'manual'`, `'document_upload'`) |
| `submitter_email` | `text` | YES | - | Email of the submitter |
| `submitted_by` | `uuid` | YES | - | Foreign key to `auth.users.id` |
| `reviewed_by` | `uuid` | YES | - | Foreign key to `auth.users.id` (reviewer) |
| `reviewed_at` | `timestamptz` | YES | - | Timestamp when reviewed |
| `review_comments` | `text` | YES | - | Comments from reviewer |
| `rejection_reason` | `text` | YES | - | Reason for rejection (if rejected) |
| `created_at` | `timestamptz` | NO | `now()` | Creation timestamp |
| `updated_at` | `timestamptz` | NO | `now()` | Last update timestamp |

### Constraints

- **Primary Key**: `id`
- **Check Constraint**: `submissions_type_check` - `type IN ('vulnerability', 'ofc')`
- **Foreign Keys**:
  - `submitted_by` → `auth.users.id`
  - `reviewed_by` → `auth.users.id`

### Indexes

- `idx_submissions_status` on `status`
- `idx_submissions_type` on `type`
- `idx_submissions_submitted_by` on `submitted_by`

### Relationships

- **Has Many**: `submission_vulnerabilities` (via `submission_id`)
- **Has Many**: `submission_options_for_consideration` (via `submission_id`)
- **Has Many**: `submission_sources` (via `submission_id`)
- **Belongs To**: `auth.users` (via `submitted_by` and `reviewed_by`)

---

## Table: `submission_vulnerabilities`

**Purpose**: Vulnerabilities extracted from submission documents.

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | Primary key |
| `submission_id` | `uuid` | NO | - | Foreign key to `submissions.id` |
| `vulnerability` | `text` | YES | - | Vulnerability description |
| `discipline` | `text` | YES | - | Discipline/category |
| `source` | `text` | YES | - | Source reference |
| `source_title` | `text` | YES | - | Source document title |
| `source_url` | `text` | YES | - | Source URL |
| `vulnerability_count` | `integer` | YES | - | Number of vulnerabilities found |
| `ofc_count` | `integer` | YES | - | Number of associated OFCs |
| `enhanced_extraction` | `jsonb` | YES | - | Enhanced extraction metadata |
| `parsed_at` | `timestamptz` | YES | - | When parsing occurred |
| `parser_version` | `text` | YES | - | Parser version used |
| `extraction_stats` | `jsonb` | YES | - | Extraction statistics |
| `question` | `text` | YES | - | Structured field: question |
| `what` | `text` | YES | - | Structured field: what |
| `so_what` | `text` | YES | - | Structured field: so what |
| `sector` | `text` | YES | - | Sector classification |
| `subsector` | `text` | YES | - | Subsector classification |
| `created_at` | `timestamptz` | NO | `now()` | Creation timestamp |
| `updated_at` | `timestamptz` | NO | `now()` | Last update timestamp |

### Constraints

- **Primary Key**: `id`
- **Foreign Key**: `submission_id` → `submissions.id` (CASCADE DELETE)

### Indexes

- `idx_submission_vuln_submission_id` on `submission_id`
- `idx_submission_vuln_discipline` on `discipline`

### Relationships

- **Belongs To**: `submissions` (via `submission_id`)
- **Has Many**: `submission_options_for_consideration` (via `vulnerability_id`)
- **Has Many**: `submission_vulnerability_ofc_links` (via `vulnerability_id`)

---

## Table: `submission_options_for_consideration`

**Purpose**: Options for Consideration (OFCs) extracted from submissions.

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | Primary key |
| `submission_id` | `uuid` | NO | - | Foreign key to `submissions.id` |
| `vulnerability_id` | `uuid` | YES | - | Foreign key to `submission_vulnerabilities.id` |
| `option_text` | `text` | YES | - | OFC text content |
| `title` | `text` | YES | - | OFC title (optional) |
| `description` | `text` | YES | - | OFC description (optional) |
| `discipline` | `text` | YES | - | Discipline/category |
| `source` | `text` | YES | - | Source reference |
| `source_title` | `text` | YES | - | Source document title |
| `source_url` | `text` | YES | - | Source URL |
| `confidence_score` | `decimal` | YES | - | Confidence score (0.0-1.0) |
| `pattern_matched` | `text` | YES | - | Pattern that matched (if applicable) |
| `context` | `text` | YES | - | Contextual information |
| `citations` | `jsonb` | YES | - | Array of citations |
| `linked_vulnerability` | `text` | YES | - | Text reference to linked vulnerability |
| `created_at` | `timestamptz` | NO | `now()` | Creation timestamp |
| `updated_at` | `timestamptz` | NO | `now()` | Last update timestamp |

### Constraints

- **Primary Key**: `id`
- **Foreign Keys**:
  - `submission_id` → `submissions.id` (CASCADE DELETE)
  - `vulnerability_id` → `submission_vulnerabilities.id` (SET NULL on delete)

### Indexes

- `idx_submission_ofc_submission_id` on `submission_id`
- `idx_submission_ofc_vulnerability_id` on `vulnerability_id`

### Relationships

- **Belongs To**: `submissions` (via `submission_id`)
- **Belongs To**: `submission_vulnerabilities` (via `vulnerability_id`, nullable)
- **Has Many**: `submission_ofc_sources` (via `ofc_id`)

---

## Table: `submission_sources`

**Purpose**: Source documents/references from submissions.

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | Primary key |
| `submission_id` | `uuid` | NO | - | Foreign key to `submissions.id` |
| `source_text` | `text` | YES | - | Source text/reference |
| `reference_number` | `text` | YES | - | Reference number (e.g., `REF-123456`) |
| `source_title` | `text` | YES | - | Source document title |
| `source_url` | `text` | YES | - | Source URL |
| `author_org` | `text` | YES | - | Author organization |
| `publication_year` | `integer` | YES | - | Publication year |
| `content_restriction` | `text` | YES | - | Content restriction level (e.g., `'public'`, `'restricted'`) |
| `created_at` | `timestamptz` | NO | `now()` | Creation timestamp |
| `updated_at` | `timestamptz` | NO | `now()` | Last update timestamp |

### Constraints

- **Primary Key**: `id`
- **Foreign Key**: `submission_id` → `submissions.id` (CASCADE DELETE)

### Indexes

- `idx_submission_sources_submission_id` on `submission_id`

### Relationships

- **Belongs To**: `submissions` (via `submission_id`)

---

## Table: `submission_vulnerability_ofc_links`

**Purpose**: Junction table linking submission vulnerabilities to OFCs.

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | Primary key |
| `submission_id` | `uuid` | NO | - | Foreign key to `submissions.id` |
| `vulnerability_id` | `uuid` | NO | - | Foreign key to `submission_vulnerabilities.id` |
| `ofc_id` | `uuid` | NO | - | Foreign key to `submission_options_for_consideration.id` |
| `link_type` | `text` | YES | - | Link type (e.g., `'direct'`, `'inferred'`) |
| `confidence_score` | `decimal` | YES | - | Confidence score (0.0-1.0) |
| `created_at` | `timestamptz` | NO | `now()` | Creation timestamp |

### Constraints

- **Primary Key**: `id`
- **Foreign Keys**:
  - `submission_id` → `submissions.id` (CASCADE DELETE)
  - `vulnerability_id` → `submission_vulnerabilities.id` (CASCADE DELETE)
  - `ofc_id` → `submission_options_for_consideration.id` (CASCADE DELETE)

### Indexes

- `idx_submission_vuln_ofc_links_submission_id` on `submission_id`
- `idx_submission_vuln_ofc_links_vuln_id` on `vulnerability_id`
- `idx_submission_vuln_ofc_links_ofc_id` on `ofc_id`

### Relationships

- **Belongs To**: `submissions` (via `submission_id`)
- **Belongs To**: `submission_vulnerabilities` (via `vulnerability_id`)
- **Belongs To**: `submission_options_for_consideration` (via `ofc_id`)

---

## Table: `submission_ofc_sources`

**Purpose**: Junction table linking submission OFCs to sources.

### Columns

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | `uuid` | NO | `gen_random_uuid()` | Primary key |
| `submission_id` | `uuid` | NO | - | Foreign key to `submissions.id` |
| `ofc_id` | `uuid` | NO | - | Foreign key to `submission_options_for_consideration.id` |
| `source_id` | `uuid` | NO | - | Foreign key to `submission_sources.id` |
| `created_at` | `timestamptz` | NO | `now()` | Creation timestamp |

### Constraints

- **Primary Key**: `id`
- **Foreign Keys**:
  - `submission_id` → `submissions.id` (CASCADE DELETE)
  - `ofc_id` → `submission_options_for_consideration.id` (CASCADE DELETE)
  - `source_id` → `submission_sources.id` (CASCADE DELETE)

### Indexes

- `idx_submission_ofc_sources_submission_id` on `submission_id`
- `idx_submission_ofc_sources_ofc_id` on `ofc_id`
- `idx_submission_ofc_sources_source_id` on `source_id`

### Relationships

- **Belongs To**: `submissions` (via `submission_id`)
- **Belongs To**: `submission_options_for_consideration` (via `ofc_id`)
- **Belongs To**: `submission_sources` (via `source_id`)

---

## Complete Relationship Diagram

```
submissions (type: 'vulnerability' | 'ofc')
  ├── submission_vulnerabilities (1:N)
  │     ├── submission_vulnerability_ofc_links (1:N)
  │     │     └── submission_options_for_consideration (N:1)
  │     └── submission_options_for_consideration (1:N via vulnerability_id)
  ├── submission_options_for_consideration (1:N)
  │     └── submission_ofc_sources (1:N)
  │           └── submission_sources (N:1)
  └── submission_sources (1:N)
```

---

## Important Notes

1. **Type Constraint**: The `submissions.type` field has a CHECK constraint that only allows `'vulnerability'` or `'ofc'`. The value `'document'` is NOT allowed.

2. **Document Uploads**: When uploading documents, use `type: 'vulnerability'` and add a `document_upload: true` flag in the `data` JSONB field to indicate it came from a document upload.

3. **Cascade Deletes**: All related tables use CASCADE DELETE, so deleting a submission will automatically delete all related records.

4. **Timestamps**: All tables have `created_at` and `updated_at` timestamps that are automatically managed by the database.

5. **JSONB Data**: The `submissions.data` field is JSONB, so you can store flexible data structures. Use a plain object, not a stringified JSON.

