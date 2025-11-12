# Submission Tables Schema and Production Translation

## Overview

This document provides a complete reference for:
1. **Submission Tables Schema** - Staging tables for data awaiting review
2. **Production Tables Schema** - Finalized, approved data
3. **Translation Mapping** - How data moves from submission to production tables
4. **Approval Workflow** - The process of promoting submissions to production

---

## Table of Contents

1. [Submission Tables Schema](#submission-tables-schema)
2. [Production Tables Schema](#production-tables-schema)
3. [Translation Mapping](#translation-mapping)
4. [Approval Workflow](#approval-workflow)
5. [Data Flow Diagram](#data-flow-diagram)
6. [Field Mapping Reference](#field-mapping-reference)

---

## Submission Tables Schema

### 1. `submissions` (Main Submission Record)

**Purpose**: Root table storing submission metadata and complete data in JSONB.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `uuid` | NO | Primary key (auto-generated) |
| `type` | `text` | NO | **CHECK CONSTRAINT**: Must be `'vulnerability'` or `'ofc'` |
| `status` | `text` | NO | Status: `'pending'`, `'pending_review'`, `'approved'`, `'rejected'` |
| `data` | `jsonb` | YES | Complete submission data (preserved as-is) |
| `source` | `text` | YES | Source identifier: `'bulk_csv'`, `'manual'`, `'document_upload'`, `'psa_tool_auto'` |
| `submitter_email` | `text` | YES | Email of submitter |
| `submitted_by` | `uuid` | YES | Foreign key to `auth.users.id` |
| `reviewed_by` | `uuid` | YES | Foreign key to `auth.users.id` (reviewer) |
| `reviewed_at` | `timestamptz` | YES | Timestamp when reviewed |
| `review_comments` | `text` | YES | Reviewer comments |
| `rejection_reason` | `text` | YES | Reason for rejection (if rejected) |
| `created_at` | `timestamptz` | NO | Creation timestamp (auto) |
| `updated_at` | `timestamptz` | NO | Last update timestamp (auto) |

**Constraints**:
- Primary Key: `id`
- Check Constraint: `submissions_type_check` - `type IN ('vulnerability', 'ofc')`
- Foreign Keys: `submitted_by` → `auth.users.id`, `reviewed_by` → `auth.users.id`

**Relationships**:
- Has many `submission_vulnerabilities` (via `submission_id`)
- Has many `submission_options_for_consideration` (via `submission_id`)
- Has many `submission_sources` (via `submission_id`)

---

### 2. `submission_vulnerabilities`

**Purpose**: Individual vulnerabilities extracted from submission documents.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `uuid` | NO | Primary key (auto-generated) |
| `submission_id` | `uuid` | NO | Foreign key to `submissions.id` (CASCADE DELETE) |
| `vulnerability` | `text` | YES | Vulnerability description/text |
| `discipline` | `text` | YES | Discipline name (e.g., "Access Control", "Physical Security") |
| `discipline_id` | `uuid` | YES | Foreign key to `disciplines.id` (optional) |
| `sector` | `text` | YES | Sector name (e.g., "Energy", "Transport") |
| `sector_id` | `uuid` | YES | Foreign key to `sectors.id` (optional) |
| `subsector` | `text` | YES | Subsector name |
| `subsector_id` | `uuid` | YES | Foreign key to `subsectors.id` (optional) |
| `source` | `text` | YES | Source reference |
| `source_title` | `text` | YES | Source document title |
| `source_url` | `text` | YES | Source URL |
| `source_context` | `text` | YES | Contextual text from source document |
| `source_page` | `text` | YES | Page reference (e.g., "1-2", "5") |
| `page_ref` | `text` | YES | Alternative page reference field |
| `chunk_id` | `text` | YES | Chunk identifier from document processing |
| `vulnerability_count` | `integer` | YES | Number of vulnerabilities found |
| `ofc_count` | `integer` | YES | Number of associated OFCs |
| `confidence_score` | `decimal` | YES | Confidence score (0.0-1.0) |
| `severity_level` | `text` | YES | Severity: `'Very Low'`, `'Low'`, `'Medium'`, `'High'`, `'Very High'` |
| `question` | `text` | YES | Structured field: assessment question |
| `what` | `text` | YES | Structured field: what |
| `so_what` | `text` | YES | Structured field: so what |
| `enhanced_extraction` | `jsonb` | YES | Enhanced extraction metadata |
| `parsed_at` | `timestamptz` | YES | When parsing occurred |
| `parser_version` | `text` | YES | Parser version used |
| `extraction_stats` | `jsonb` | YES | Extraction statistics |
| `created_at` | `timestamptz` | NO | Creation timestamp (auto) |
| `updated_at` | `timestamptz` | NO | Last update timestamp (auto) |

**Relationships**:
- Belongs to `submissions` (via `submission_id`)
- Has many `submission_options_for_consideration` (via `vulnerability_id`)
- Has many `submission_vulnerability_ofc_links` (via `vulnerability_id`)

---

### 3. `submission_options_for_consideration`

**Purpose**: Options for Consideration (OFCs) extracted from submissions.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `uuid` | NO | Primary key (auto-generated) |
| `submission_id` | `uuid` | NO | Foreign key to `submissions.id` (CASCADE DELETE) |
| `vulnerability_id` | `uuid` | YES | Foreign key to `submission_vulnerabilities.id` (SET NULL on delete) |
| `option_text` | `text` | YES | OFC text content |
| `title` | `text` | YES | OFC title (optional) |
| `description` | `text` | YES | OFC description (optional) |
| `discipline` | `text` | YES | Discipline name |
| `source` | `text` | YES | Source reference |
| `source_title` | `text` | YES | Source document title |
| `source_url` | `text` | YES | Source URL |
| `confidence_score` | `decimal` | YES | Confidence score (0.0-1.0) |
| `pattern_matched` | `text` | YES | Pattern that matched (if applicable) |
| `context` | `text` | YES | Contextual information |
| `citations` | `jsonb` | YES | Array of citations |
| `linked_vulnerability` | `text` | YES | Text reference to linked vulnerability |
| `chunk_id` | `text` | YES | Chunk identifier from document processing |
| `created_at` | `timestamptz` | NO | Creation timestamp (auto) |
| `updated_at` | `timestamptz` | NO | Last update timestamp (auto) |

**Relationships**:
- Belongs to `submissions` (via `submission_id`)
- Belongs to `submission_vulnerabilities` (via `vulnerability_id`, nullable)
- Has many `submission_ofc_sources` (via `ofc_id`)

---

### 4. `submission_sources`

**Purpose**: Source documents/references from submissions.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `uuid` | NO | Primary key (auto-generated) |
| `submission_id` | `uuid` | NO | Foreign key to `submissions.id` (CASCADE DELETE) |
| `source_text` | `text` | YES | Source text/reference |
| `reference_number` | `text` | YES | Reference number (e.g., `REF-123456`) |
| `source_title` | `text` | YES | Source document title |
| `source_url` | `text` | YES | Source URL |
| `author_org` | `text` | YES | Author organization |
| `publication_year` | `integer` | YES | Publication year |
| `content_restriction` | `text` | YES | Content restriction level: `'public'`, `'restricted'` |
| `source_file` | `text` | YES | Source file name |
| `page_ref` | `text` | YES | Page reference |
| `chunk_id` | `text` | YES | Chunk identifier |
| `created_at` | `timestamptz` | NO | Creation timestamp (auto) |
| `updated_at` | `timestamptz` | NO | Last update timestamp (auto) |

**Relationships**:
- Belongs to `submissions` (via `submission_id`)

---

### 5. `submission_vulnerability_ofc_links`

**Purpose**: Junction table linking submission vulnerabilities to OFCs.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `uuid` | NO | Primary key (auto-generated) |
| `submission_id` | `uuid` | NO | Foreign key to `submissions.id` (CASCADE DELETE) |
| `vulnerability_id` | `uuid` | NO | Foreign key to `submission_vulnerabilities.id` (CASCADE DELETE) |
| `ofc_id` | `uuid` | NO | Foreign key to `submission_options_for_consideration.id` (CASCADE DELETE) |
| `link_type` | `text` | YES | Link type: `'direct'`, `'inferred'` |
| `confidence_score` | `decimal` | YES | Confidence score (0.0-1.0) |
| `created_at` | `timestamptz` | NO | Creation timestamp (auto) |

**Relationships**:
- Belongs to `submissions` (via `submission_id`)
- Belongs to `submission_vulnerabilities` (via `vulnerability_id`)
- Belongs to `submission_options_for_consideration` (via `ofc_id`)

---

### 6. `submission_ofc_sources`

**Purpose**: Junction table linking submission OFCs to sources.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `uuid` | NO | Primary key (auto-generated) |
| `submission_id` | `uuid` | NO | Foreign key to `submissions.id` (CASCADE DELETE) |
| `ofc_id` | `uuid` | NO | Foreign key to `submission_options_for_consideration.id` (CASCADE DELETE) |
| `source_id` | `uuid` | NO | Foreign key to `submission_sources.id` (CASCADE DELETE) |
| `created_at` | `timestamptz` | NO | Creation timestamp (auto) |

**Relationships**:
- Belongs to `submissions` (via `submission_id`)
- Belongs to `submission_options_for_consideration` (via `ofc_id`)
- Belongs to `submission_sources` (via `source_id`)

---

## Production Tables Schema

### 1. `vulnerabilities` (Production)

**Purpose**: Approved/production vulnerabilities available in the library.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `uuid` | NO | Primary key (auto-generated) |
| `vulnerability_name` | `text` | YES | Vulnerability name/title |
| `description` | `text` | YES | Vulnerability description (can include structured fields) |
| `discipline` | `text` | YES | Discipline name |
| `sector_id` | `uuid` | YES | Foreign key to `sectors.id` |
| `subsector_id` | `uuid` | YES | Foreign key to `subsectors.id` |
| `severity_level` | `text` | YES | Severity: `'Very Low'`, `'Low'`, `'Medium'`, `'High'`, `'Very High'` |
| `created_at` | `timestamptz` | NO | Creation timestamp (auto) |
| `updated_at` | `timestamptz` | NO | Last update timestamp (auto) |

**Relationships**:
- Belongs to `sectors` (via `sector_id`, nullable)
- Belongs to `subsectors` (via `subsector_id`, nullable)
- Has many `vulnerability_ofc_links` (via `vulnerability_id`)

**Note**: Production table is simplified - only essential fields. Full data preserved in `submissions.data` JSONB.

---

### 2. `options_for_consideration` (Production)

**Purpose**: Approved/production Options for Consideration.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `uuid` | NO | Primary key (auto-generated) |
| `option_text` | `text` | YES | OFC text content |
| `discipline` | `text` | YES | Discipline name |
| `sector_id` | `uuid` | YES | Foreign key to `sectors.id` |
| `subsector_id` | `uuid` | YES | Foreign key to `subsectors.id` |
| `created_at` | `timestamptz` | NO | Creation timestamp (auto) |
| `updated_at` | `timestamptz` | NO | Last update timestamp (auto) |

**Relationships**:
- Belongs to `sectors` (via `sector_id`, nullable)
- Belongs to `subsectors` (via `subsector_id`, nullable)
- Has many `vulnerability_ofc_links` (via `ofc_id`)
- Has many `ofc_sources` (via `ofc_id`)

---

### 3. `vulnerability_ofc_links` (Production)

**Purpose**: Junction table linking production vulnerabilities to OFCs.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `uuid` | NO | Primary key (auto-generated) |
| `vulnerability_id` | `uuid` | NO | Foreign key to `vulnerabilities.id` (CASCADE DELETE) |
| `ofc_id` | `uuid` | NO | Foreign key to `options_for_consideration.id` (CASCADE DELETE) |
| `link_type` | `text` | YES | Link type: `'direct'`, `'inferred'`, `'recommended'` |
| `confidence_score` | `decimal` | YES | Confidence score (0.0-1.0) |
| `created_at` | `timestamptz` | NO | Creation timestamp (auto) |
| `updated_at` | `timestamptz` | NO | Last update timestamp (auto) |

**Relationships**:
- Belongs to `vulnerabilities` (via `vulnerability_id`)
- Belongs to `options_for_consideration` (via `ofc_id`)

---

### 4. `sources` (Production)

**Purpose**: Production source documents/references.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `uuid` | NO | Primary key (auto-generated) |
| `source_title` | `text` | YES | Source document title |
| `source_url` | `text` | YES | Source URL |
| `author_org` | `text` | YES | Author organization |
| `publication_year` | `integer` | YES | Publication year |
| `citation` | `text` | YES | Citation text |
| `content_restriction` | `text` | YES | Content restriction level |
| `created_at` | `timestamptz` | NO | Creation timestamp (auto) |
| `updated_at` | `timestamptz` | NO | Last update timestamp (auto) |

**Relationships**:
- Has many `ofc_sources` (via `source_id`)

---

### 5. `ofc_sources` (Production)

**Purpose**: Junction table linking production OFCs to sources.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `uuid` | NO | Primary key (auto-generated) |
| `ofc_id` | `uuid` | NO | Foreign key to `options_for_consideration.id` (CASCADE DELETE) |
| `source_id` | `uuid` | NO | Foreign key to `sources.id` (CASCADE DELETE) |
| `created_at` | `timestamptz` | NO | Creation timestamp (auto) |
| `updated_at` | `timestamptz` | NO | Last update timestamp (auto) |

**Relationships**:
- Belongs to `options_for_consideration` (via `ofc_id`)
- Belongs to `sources` (via `source_id`)

---

## Translation Mapping

### Overview

When a submission is **approved**, data is translated from submission tables to production tables. The translation process:

1. **Extracts** data from submission tables
2. **Resolves** taxonomy IDs (sector, subsector, discipline)
3. **Transforms** field names and structures
4. **Inserts** into production tables
5. **Creates** links between vulnerabilities and OFCs
6. **Preserves** original data in `submissions.data` JSONB

---

### Field-by-Field Translation

#### `submission_vulnerabilities` → `vulnerabilities`

| Submission Field | Production Field | Transformation Notes |
|-----------------|------------------|----------------------|
| `vulnerability` | `vulnerability_name` | Direct copy (or from `title` if `vulnerability` is empty) |
| `vulnerability` + `question` + `what` + `so_what` | `description` | Combined into structured description |
| `discipline` | `discipline` | Direct copy (text name, not ID) |
| `sector_id` | `sector_id` | Resolved via `resolveSectorId()` if missing |
| `subsector_id` | `subsector_id` | Resolved via `resolveSubsectorId()` if missing |
| `severity_level` | `severity_level` | Direct copy (if present) |
| - | `id` | New UUID generated |

**Description Building Logic**:
```javascript
// If structured fields exist, combine them:
if (v.question || v.what || v.so_what || vulnStatement) {
  const parts = [];
  if (v.question) parts.push(`Assessment Question: ${v.question}`);
  if (vulnStatement) parts.push(`Vulnerability Statement: ${vulnStatement}`);
  if (v.what) parts.push(`What: ${v.what}`);
  if (v.so_what) parts.push(`So What: ${v.so_what}`);
  vulnerabilityText = parts.join('\n\n');
} else {
  vulnerabilityText = v.description || '';
}
```

---

#### `submission_options_for_consideration` → `options_for_consideration`

| Submission Field | Production Field | Transformation Notes |
|-----------------|------------------|----------------------|
| `option_text` | `option_text` | Direct copy (or from `option` or `title` if `option_text` is empty) |
| `discipline` | `discipline` | Direct copy (text name, not ID) |
| `sector_id` | `sector_id` | Resolved via `resolveSectorId()` if missing |
| `subsector_id` | `subsector_id` | Resolved via `resolveSubsectorId()` if missing |
| - | `id` | New UUID generated |

**Note**: Only essential fields are copied. Additional metadata (confidence_score, context, citations) is preserved in `submissions.data` JSONB.

---

#### `submission_vulnerability_ofc_links` → `vulnerability_ofc_links`

| Submission Field | Production Field | Transformation Notes |
|-----------------|------------------|----------------------|
| `vulnerability_id` | `vulnerability_id` | **Mapped to production vulnerability ID** (not direct copy) |
| `ofc_id` | `ofc_id` | **Mapped to production OFC ID** (not direct copy) |
| `link_type` | `link_type` | Direct copy (default: `'direct'`) |
| `confidence_score` | `confidence_score` | Direct copy (default: `1.0` for approved) |
| - | `id` | New UUID generated |

**Link Creation Logic**:
1. Map submission vulnerability keys to production vulnerability IDs
2. Map submission OFC keys to production OFC IDs
3. Match OFCs to vulnerabilities using `linked_vulnerability` text reference
4. Create links with `link_type: 'direct'` and `confidence_score: 1.0`

---

#### `submission_sources` → `sources`

| Submission Field | Production Field | Transformation Notes |
|-----------------|------------------|----------------------|
| `source_title` | `source_title` | Direct copy |
| `source_url` | `source_url` | Direct copy |
| `author_org` | `author_org` | Direct copy |
| `publication_year` | `publication_year` | Direct copy |
| `content_restriction` | `content_restriction` | Direct copy |
| - | `citation` | Generated from other fields (optional) |
| - | `id` | New UUID generated |

**Note**: Sources are created/promoted separately and linked via `ofc_sources` junction table.

---

## Approval Workflow

### Step-by-Step Process

1. **Admin Reviews Submission**
   - Admin views submission in review UI
   - Reviews vulnerabilities, OFCs, and sources
   - Makes approval/rejection decision

2. **Approval API Call**
   - `POST /api/submissions/[id]/approve`
   - Body: `{ "status": "approved", "comments": "..." }`

3. **Data Extraction**
   - Parse `submissions.data` JSONB
   - Extract `vulnerabilities[]` and `ofcs[]` arrays
   - Extract `sources[]` array (if present)

4. **Taxonomy Resolution**
   - For each vulnerability/OFC:
     - Resolve `sector_id` from `sector` name (if missing)
     - Resolve `subsector_id` from `subsector` name (if missing)
     - Keep `discipline` as text (not resolved to ID)

5. **Production Insertion**
   - Insert vulnerabilities into `vulnerabilities` table
   - Insert OFCs into `options_for_consideration` table
   - Create/promote sources to `sources` table (if needed)

6. **Link Creation**
   - Map submission vulnerability IDs to production vulnerability IDs
   - Map submission OFC IDs to production OFC IDs
   - Match OFCs to vulnerabilities using `linked_vulnerability` text
   - Create links in `vulnerability_ofc_links` table

7. **Audit Logging**
   - Log approval event with production IDs
   - Create learning events for ML training

8. **Status Update**
   - Update `submissions.status` to `'approved'`
   - Set `submissions.reviewed_by` and `submissions.reviewed_at`

9. **Cleanup (Optional)**
   - Submission records remain in submission tables (for audit trail)
   - Can be archived or deleted later

---

### Rejection Workflow

1. **Admin Rejects Submission**
   - `POST /api/submissions/[id]/approve`
   - Body: `{ "status": "rejected", "comments": "..." }`

2. **Audit Logging**
   - Log rejection event (before deletion)

3. **Cascade Deletion**
   - Delete `submission_vulnerability_ofc_links`
   - Delete `submission_ofc_sources`
   - Delete `submission_options_for_consideration`
   - Delete `submission_vulnerabilities`
   - Delete `submission_sources`
   - Delete `submissions` record

**Note**: Rejected submissions are completely removed (no production data created).

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Document Processing                          │
│  PDF Upload → Text Extraction → Model Inference → JSON Output  │
└───────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Supabase Sync (services/supabase_sync_*.py)         │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 1. Create submissions record (type: 'vulnerability')     │ │
│  │ 2. Insert submission_vulnerabilities                      │ │
│  │ 3. Insert submission_options_for_consideration            │ │
│  │ 4. Insert submission_sources                             │ │
│  │ 5. Create submission_vulnerability_ofc_links              │ │
│  └───────────────────────────────────────────────────────────┘ │
└───────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Review UI (Admin Dashboard)                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ • View submissions                                         │ │
│  │ • Review vulnerabilities and OFCs                        │ │
│  │ • Approve or Reject                                       │ │
│  └───────────────────────────────────────────────────────────┘ │
└───────────────────────────┬───────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
         ┌──────────────┐    ┌──────────────┐
         │  APPROVED    │    │   REJECTED   │
         └──────┬───────┘    └──────┬───────┘
                │                   │
                │                   ▼
                │          ┌──────────────────┐
                │          │ Cascade Delete  │
                │          │ All submission  │
                │          │ tables          │
                │          └──────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────┐
│         Approval Translation (app/api/submissions/[id]/approve) │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ 1. Extract vulnerabilities[] and ofcs[] from data JSONB  │ │
│  │ 2. Resolve taxonomy IDs (sector_id, subsector_id)        │ │
│  │  │                                                         │ │
│  │  │  submission_vulnerabilities → vulnerabilities          │ │
│  │  │  submission_options_for_consideration →               │ │
│  │  │    options_for_consideration                          │ │
│  │  │  submission_sources → sources                          │ │
│  │  │  submission_vulnerability_ofc_links →                 │ │
│  │  │    vulnerability_ofc_links                            │ │
│  │  │                                                         │ │
│  │ 3. Create vulnerability_ofc_links                         │ │
│  │ 4. Log audit event                                        │ │
│  │ 5. Create learning events                                 │ │
│  └───────────────────────────────────────────────────────────┘ │
└───────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Production Tables                            │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ • vulnerabilities                                         │ │
│  │ • options_for_consideration                               │ │
│  │ • vulnerability_ofc_links                                │ │
│  │ • sources                                                 │ │
│  │ • ofc_sources                                             │ │
│  └───────────────────────────────────────────────────────────┘ │
│                    Available in Library                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Field Mapping Reference

### Quick Reference Table

| Submission Table | Submission Field | Production Table | Production Field | Notes |
|-----------------|------------------|------------------|------------------|-------|
| `submission_vulnerabilities` | `vulnerability` | `vulnerabilities` | `vulnerability_name` | Direct copy |
| `submission_vulnerabilities` | `vulnerability` + `question` + `what` + `so_what` | `vulnerabilities` | `description` | Combined |
| `submission_vulnerabilities` | `discipline` | `vulnerabilities` | `discipline` | Text name |
| `submission_vulnerabilities` | `sector_id` | `vulnerabilities` | `sector_id` | Resolved if missing |
| `submission_vulnerabilities` | `subsector_id` | `vulnerabilities` | `subsector_id` | Resolved if missing |
| `submission_vulnerabilities` | `severity_level` | `vulnerabilities` | `severity_level` | Direct copy |
| `submission_options_for_consideration` | `option_text` | `options_for_consideration` | `option_text` | Direct copy |
| `submission_options_for_consideration` | `discipline` | `options_for_consideration` | `discipline` | Text name |
| `submission_options_for_consideration` | `sector_id` | `options_for_consideration` | `sector_id` | Resolved if missing |
| `submission_options_for_consideration` | `subsector_id` | `options_for_consideration` | `subsector_id` | Resolved if missing |
| `submission_vulnerability_ofc_links` | `vulnerability_id` | `vulnerability_ofc_links` | `vulnerability_id` | **Mapped to production ID** |
| `submission_vulnerability_ofc_links` | `ofc_id` | `vulnerability_ofc_links` | `ofc_id` | **Mapped to production ID** |
| `submission_vulnerability_ofc_links` | `link_type` | `vulnerability_ofc_links` | `link_type` | Direct copy (default: `'direct'`) |
| `submission_vulnerability_ofc_links` | `confidence_score` | `vulnerability_ofc_links` | `confidence_score` | Direct copy (default: `1.0`) |
| `submission_sources` | `source_title` | `sources` | `source_title` | Direct copy |
| `submission_sources` | `source_url` | `sources` | `source_url` | Direct copy |
| `submission_sources` | `author_org` | `sources` | `author_org` | Direct copy |
| `submission_sources` | `publication_year` | `sources` | `publication_year` | Direct copy |

---

## Important Notes

### 1. Data Preservation

- **Complete data preserved**: The entire submission data is stored in `submissions.data` JSONB column
- **Structured extraction**: Key fields are also extracted to normalized tables for efficient querying
- **No data loss**: Even if structured fields are missing, original data remains in JSONB

### 2. ID Mapping

- **New UUIDs generated**: Production tables use new UUIDs (not copied from submission tables)
- **Link mapping**: Submission vulnerability/OFC IDs are mapped to production IDs during approval
- **Text matching**: OFCs are matched to vulnerabilities using `linked_vulnerability` text reference

### 3. Taxonomy Resolution

- **Fuzzy matching**: Sector/subsector names are resolved using fuzzy matching (handles variations)
- **ID storage**: Both IDs and names are stored in submission tables (IDs for referential integrity, names for querying)
- **Production IDs only**: Production tables store only IDs (not names) for taxonomy fields

### 4. Cascade Deletes

- **Submission tables**: All submission tables use CASCADE DELETE (deleting submission deletes all related records)
- **Production tables**: Production tables use CASCADE DELETE for links (deleting vulnerability deletes links)
- **Rejection**: Rejected submissions are completely deleted (cascade delete)

### 5. Type Constraint

- **Submission type**: `submissions.type` must be `'vulnerability'` or `'ofc'` (CHECK constraint)
- **Document uploads**: Use `type: 'vulnerability'` with `document_upload: true` flag in `data` JSONB

---

## Code References

### Approval Route
- **File**: `app/api/submissions/[id]/approve/route.js`
- **Function**: `POST(request, { params })`
- **Key Logic**: Lines 200-425 (vulnerability/OFC insertion and linking)

### Sync Functions
- **File**: `services/supabase_sync_individual_v2.py`
- **Function**: `sync_individual_records(result_file)`
- **Key Logic**: Lines 500-700 (submission table insertion)

### Taxonomy Resolution
- **File**: `services/supabase_client.py`
- **Functions**: `get_discipline_record()`, `get_sector_id()`, `get_subsector_id()`
- **Key Logic**: Fuzzy matching with wildcard patterns (`ilike.*name*`)

---

**Last Updated**: 2025-01-09  
**Schema Version**: 1.0.0

