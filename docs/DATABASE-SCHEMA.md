# Database Schema Reference

## Overview

The PSA Tool uses Supabase (PostgreSQL) as its database backend. This document provides a quick reference of all database tables and their primary purposes.

---

## Table Listing by Category

### 1. Submission Management Tables

| Table Name | Purpose |
|------------|---------|
| `submissions` | Main table storing user-submitted documents and data awaiting review. Tracks submission status, reviewer, and metadata. |
| `submission_vulnerabilities` | Vulnerabilities extracted from submission documents. Contains vulnerability descriptions, disciplines, sectors, and extraction metadata. |
| `submission_options_for_consideration` | Options for Consideration (OFCs) extracted from submissions. Links to vulnerabilities and includes confidence scores. |
| `submission_sources` | Source documents and references from submissions. Stores document titles, URLs, authors, and publication information. |
| `submission_vulnerability_ofc_links` | Junction table linking submission vulnerabilities to their associated OFCs. Tracks link types and confidence scores. |
| `submission_ofc_sources` | Junction table linking submission OFCs to their source documents. |

**Purpose**: Manages the workflow from document upload through review and approval. All user-submitted data starts here before being promoted to production tables.

---

### 2. Production Data Tables

| Table Name | Purpose |
|------------|---------|
| `vulnerabilities` | Approved/production vulnerabilities. Finalized vulnerability records available in the library. |
| `options_for_consideration` | Approved/production Options for Consideration. Finalized OFC records linked to vulnerabilities. |
| `vulnerability_ofc_links` | Junction table linking production vulnerabilities to their associated OFCs. Tracks relationship types and confidence. |
| `sources` | Production source documents and references. Authoritative source documents for OFCs. |
| `ofc_sources` | Junction table linking production OFCs to their source documents. |

**Purpose**: Stores approved, production-ready data that is publicly available in the library. Data is promoted from submission tables after review and approval.

---

### 3. Taxonomy Tables

| Table Name | Purpose |
|------------|---------|
| `sectors` | Sector taxonomy for classification (e.g., Energy, Transportation, Information Technology). Used to categorize vulnerabilities and OFCs. |
| `subsectors` | Subsector taxonomy for classification. Hierarchical child of sectors (e.g., "Power Grid" under "Energy"). |
| `disciplines` | Discipline taxonomy for classification (e.g., Cybersecurity, Physical Security, Operational Technology). Includes category field (Cyber, Physical, OT). |

**Purpose**: Provides hierarchical classification system for organizing vulnerabilities and OFCs. Used by the post-processing module to resolve taxonomy IDs.

---

### 4. User Management Tables

| Table Name | Purpose |
|------------|---------|
| `user_profiles` | Extended user profile information. Extends Supabase `auth.users` with role, organization, and profile data. |
| `user_agency_relationships` | Multi-agency support for Row Level Security (RLS). Allows users to belong to multiple agencies with different roles. |

**Purpose**: Manages user authentication, authorization, and multi-tenant access control. Supports role-based permissions (admin, supervisor, user).

---

### 5. Learning System Tables

| Table Name | Purpose |
|------------|---------|
| `learning_events` | Machine learning training events. Tracks approval/rejection events to improve extraction accuracy. Stores model version, confidence scores, and metadata. |

**Purpose**: Feeds the learning algorithm with positive (approved) and negative (rejected) examples to improve document parsing accuracy over time.

---

### 6. OFC Request Workflow Tables

| Table Name | Purpose |
|------------|---------|
| `ofc_requests` | Requests for new Options for Consideration. Tracks user requests for additional OFCs linked to vulnerabilities. Includes review workflow. |

**Purpose**: Manages the workflow for users to request new OFCs for existing vulnerabilities. Supports review and approval process.

---

## Quick Reference: Table Relationships

```
Submission Flow:
  submissions
    ├── submission_vulnerabilities
    │     └── submission_vulnerability_ofc_links → submission_options_for_consideration
    ├── submission_sources
    └── submission_ofc_sources

Production Data:
  vulnerabilities
    └── vulnerability_ofc_links → options_for_consideration
          └── ofc_sources → sources

Taxonomy:
  sectors
    └── subsectors

User Management:
  auth.users (Supabase)
    └── user_profiles
          └── user_agency_relationships
```

---

## Data Flow

### Submission → Production Pipeline

1. **Document Upload**: User uploads document via `/api/process`
2. **Preprocessing**: Document is chunked and normalized
3. **Model Inference**: Ollama extracts vulnerabilities and OFCs
4. **Post-Processing**: Results are cleaned, deduplicated, and taxonomy IDs resolved
5. **Submission Created**: Data saved to `submissions` table with status `'pending'`
6. **Review**: Admin/supervisor reviews submission
7. **Approval**: If approved, data is promoted to production tables:
   - `submission_vulnerabilities` → `vulnerabilities`
   - `submission_options_for_consideration` → `options_for_consideration`
   - Links created in `vulnerability_ofc_links`
   - Sources promoted to `sources` and linked via `ofc_sources`

---

## Key Fields Reference

### Common Status Fields

- **`submissions.status`**: `'pending'`, `'pending_review'`, `'approved'`, `'rejected'`
- **`ofc_requests.status`**: `'pending_review'`, `'approved'`, `'rejected'`
- **`user_profiles.role`**: `'admin'`, `'supervisor'`, `'user'`

### Common Timestamp Fields

- **`created_at`**: Record creation timestamp
- **`updated_at`**: Last update timestamp
- **`reviewed_at`**: Review completion timestamp (submissions, OFC requests)

### Common JSONB Fields

- **`submissions.data`**: Flexible JSON storage for submission data
- **`learning_events.metadata`**: Additional event metadata
- **`submission_vulnerabilities.enhanced_extraction`**: Extraction metadata

---

## Indexes Summary

### High-Traffic Indexes

- `idx_submissions_status` - Fast filtering by submission status
- `idx_submissions_type` - Fast filtering by submission type
- `idx_submissions_submitted_by` - Fast user submission queries
- `idx_vulnerabilities_discipline` - Fast discipline-based queries
- `idx_options_discipline` - Fast discipline-based OFC queries
- `idx_user_profiles_role` - Fast role-based access control

### Foreign Key Indexes

All foreign key columns are indexed for join performance:
- Submission relationships (`submission_id`, `vulnerability_id`, `ofc_id`)
- Production relationships (`vulnerability_id`, `ofc_id`, `sector_id`, `subsector_id`)
- User relationships (`user_id`, `submitted_by`, `reviewed_by`)

---

## Row Level Security (RLS)

### Access Control Model

- **Users**: Can only see their own submissions and approved production data
- **Supervisors**: Can review submissions within their agency
- **Admins**: Can see all submissions and production data
- **Multi-Agency**: Users can belong to multiple agencies via `user_agency_relationships`

### Service Role Access

- Service role key (`SUPABASE_SERVICE_ROLE_KEY`) bypasses RLS for admin operations
- Used by backend services (Flask, processing pipeline)
- Anon key (`NEXT_PUBLIC_SUPABASE_ANON_KEY`) respects RLS policies

---

## Table Count Summary

| Category | Tables | Purpose |
|----------|--------|---------|
| Submission Management | 6 | Document upload and review workflow |
| Production Data | 5 | Approved library content |
| Taxonomy | 3 | Classification system |
| User Management | 2 | Authentication and authorization |
| Learning System | 1 | ML training data |
| OFC Requests | 1 | OFC request workflow |
| **Total** | **18** | |

---

## Related Documentation

- **Full Schema Details**: See `docs/SUPABASE-SCHEMA.md` for complete column definitions, relationships, and query examples
- **API Reference**: See `docs/ROUTE-REFERENCE.md` for API endpoints using these tables
- **Post-Processing**: See `docs/POSTPROCESS-MODULE.md` for how taxonomy tables are used in the processing pipeline

---

**Last Updated**: 2025-01-15  
**Schema Version**: 1.0.0

