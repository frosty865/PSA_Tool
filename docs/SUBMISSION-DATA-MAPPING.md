# Submission Data Mapping

This document maps the data structure from processed results to the Supabase submission tables.

## Overview

When a document is processed, the result data is:
1. **Preserved completely** in `submissions.data` JSONB column (nothing removed)
2. **Extracted and normalized** into separate tables for efficient querying and relationships

---

## Source Data Structure

The processed result from `ollama_auto_processor.py` has this structure:

```json
{
  "source_file": "document.pdf",
  "processed_at": "2025-11-07T17:50:16",
  "chunks_processed": 150,
  "phase1_parser_count": 25,
  "phase2_engine_count": 20,
  "phase3_auditor_count": 18,
  "final_records": 18,
  "audit_metadata": {...},
  "vulnerabilities": [
    {
      "vulnerability": "Vulnerability text...",
      "discipline_id": "uuid-here",
      "category": "Physical",
      "sector_id": "uuid-here",
      "subsector_id": "uuid-here",
      "page_ref": "1-2",
      "chunk_id": "doc_001_chunk_01",
      "audit_status": "accepted"
    }
  ],
  "options_for_consideration": [
    {
      "option_text": "OFC text...",
      "vulnerability": "Vulnerability text...",  // Reference to parent vulnerability
      "discipline_id": "uuid-here",
      "sector_id": "uuid-here",
      "subsector_id": "uuid-here",
      "audit_status": "accepted"
    }
  ],
  "summary": "Processed document.pdf: 18 vulnerabilities, 45 OFCs"
}
```

---

## Table Mappings

### 1. `submissions` Table

**Purpose**: Main submission record with complete data preserved

| Field | Source | Notes |
|-------|--------|-------|
| `id` | Generated UUID | Primary key |
| `type` | `"document"` | Fixed value for auto-processed documents |
| `status` | `"pending_review"` | Initial status |
| `source` | `"psa_tool_auto"` | Source identifier |
| `submitter_email` | Parameter | Default: "system@psa.local" |
| `submitted_by` | `null` | No user ID for auto-processed |
| `file_hash` | Optional | For deduplication (if provided) |
| `parser_version` | `data.parser_version` | Default: "vofc-parser:latest" |
| `engine_version` | `data.engine_version` | Default: "vofc-engine:latest" |
| `auditor_version` | `data.auditor_version` | Default: "vofc-auditor:latest" |
| `created_at` | Current timestamp | |
| `updated_at` | Current timestamp | |
| `data` | **ENTIRE result object** | Complete JSON structure - nothing removed |

**Key Point**: The `data` column contains the **complete original structure** with all IDs, metadata, and nested data preserved.

---

### 2. `submission_vulnerabilities` Table

**Purpose**: Individual vulnerabilities extracted from the document

| Field | Source | Notes |
|-------|--------|-------|
| `id` | Generated UUID | Primary key |
| `submission_id` | From `submissions.id` | Foreign key |
| `vulnerability` | `data.vulnerabilities[].vulnerability` | Vulnerability text |
| `discipline_id` | `data.vulnerabilities[].discipline_id` | **UUID stored directly** |
| `discipline` | Resolved from `discipline_id` | Name from `disciplines` table |
| `category` | Resolved from `discipline_id` | Category from `disciplines.category` |
| `sector_id` | `data.vulnerabilities[].sector_id` | **UUID stored directly** |
| `sector` | Resolved from `sector_id` | Name from `sectors` table |
| `subsector_id` | `data.vulnerabilities[].subsector_id` | **UUID stored directly** |
| `subsector` | Resolved from `subsector_id` | Name from `subsectors` table |
| `page_ref` | `data.vulnerabilities[].page_ref` | Page reference |
| `chunk_id` | `data.vulnerabilities[].chunk_id` | Chunk identifier |
| `audit_status` | `data.vulnerabilities[].audit_status` | Default: "pending" |
| `source` | `vulnerability.source` or `data.source_file` | Source reference |
| `source_title` | `vulnerability.source_title` or `data.source_file` | Document title |
| `source_url` | `vulnerability.source_url` | URL if available |
| `parser_version` | `data.parser_version` | Default: "vofc-parser:latest" |
| `parsed_at` | Current timestamp | |

**Data Source**: `data.vulnerabilities[]` array

**ID Resolution**: 
- `discipline_id` → Query `disciplines` table → Get `name` and `category`
- `sector_id` → Query `sectors` table → Get `sector_name`
- `subsector_id` → Query `subsectors` table → Get `subsector_name`

**Note**: **Both IDs and names are stored** - IDs for referential integrity, names for easy querying. Original data also remains in `submissions.data` JSONB column.

---

### 3. `submission_options_for_consideration` Table

**Purpose**: Options for Consideration (OFCs) extracted from the document

| Field | Source | Notes |
|-------|--------|-------|
| `id` | Generated UUID | Primary key |
| `submission_id` | From `submissions.id` | Foreign key |
| `option_text` | `data.options_for_consideration[].option_text` | OFC text content |
| `vulnerability` | `data.options_for_consideration[].vulnerability` | Text reference to parent vulnerability |
| `linked_vulnerability_id` | Matched from `vulnerability` text | Optional fast join link (set after linking) |
| `discipline_id` | `data.options_for_consideration[].discipline_id` | **UUID stored directly** |
| `discipline` | Resolved from `discipline_id` | Name from `disciplines` table |
| `confidence_score` | `ofc.confidence_score` | Default: 0.8 if not provided |
| `audit_status` | `data.options_for_consideration[].audit_status` | Default: "pending" |
| `source` | `ofc.source` or `data.source_file` | Source reference |
| `source_title` | `ofc.source_title` or `data.source_file` | Document title |
| `source_url` | `ofc.source_url` | URL if available |
| `citations` | `ofc.citations` | JSON array |

**Data Source**: `data.options_for_consideration[]` array

**ID Resolution**:
- `discipline_id` → Query `disciplines` table → Get `name` or `category`

**Note**: 
- OFCs table does NOT have `sector` or `subsector` columns
- **Both `discipline_id` and `discipline` name are stored** - ID for referential integrity, name for easy querying
- Each OFC has a `vulnerability` text field that references its parent vulnerability
- `linked_vulnerability_id` can be set after creating links for fast joins

---

### 4. `submission_vulnerability_ofc_links` Table

**Purpose**: Junction table linking vulnerabilities to their associated OFCs

| Field | Source | Notes |
|-------|--------|-------|
| `id` | Generated UUID | Primary key |
| `submission_id` | From `submissions.id` | Foreign key |
| `vulnerability_id` | From `submission_vulnerabilities.id` | Matched by vulnerability text |
| `ofc_id` | From `submission_options_for_consideration.id` | OFC ID |
| `link_type` | `"direct"` | Default link type |
| `confidence_score` | `null` | Can be set if available in data |
| `created_at` | Current timestamp | |

**Matching Logic**:
1. Each OFC in `options_for_consideration[]` has a `vulnerability` field
2. Match this field to the `vulnerability` text in `vulnerabilities[]`
3. Use the stored `vulnerability_id` and `ofc_id` to create the link
4. If exact match fails, try partial matching
5. **UNIQUE constraint** on `(submission_id, vulnerability_id, ofc_id)` prevents duplicates

**Data Source**: Relationship between `data.vulnerabilities[]` and `data.options_for_consideration[]`

---

### 5. `submission_sources` Table

**Purpose**: Source documents and references

| Field | Source | Notes |
|-------|--------|-------|
| `id` | Generated UUID | Primary key |
| `submission_id` | From `submissions.id` | Foreign key |
| `source_text` | `data.sources[].text` or `citation` or `title` | Source text |
| `source_title` | `data.sources[].title` | Document title |
| `source_url` | `data.sources[].url` or `source_url` | URL |
| `author_org` | `data.sources[].author_org` or `organization` | Author organization |
| `publication_year` | `data.sources[].year` | Converted to integer |
| `source_type` | `data.sources[].source_type` | Default: "guidance_doc" |
| `content_restriction` | `data.sources[].restriction` or `content_restriction` | Default: "public" |

**Data Source**: `data.sources[]` array (if present)

**Note**: If `sources` array is empty or missing, no source records are created.

---

## Data Flow Diagram

```
Processed Result (JSON)
│
├── submissions.data (JSONB)
│   └── COMPLETE original structure preserved
│       ├── All vulnerabilities with IDs
│       ├── All OFCs with IDs and references
│       ├── All sources
│       └── All metadata
│
├── submission_vulnerabilities
│   └── Extracted from data.vulnerabilities[]
│       ├── Store discipline_id (UUID) + resolve → discipline name
│       ├── Store sector_id (UUID) + resolve → sector name
│       ├── Store subsector_id (UUID) + resolve → subsector name
│       └── Store category, page_ref, chunk_id, audit_status
│
├── submission_options_for_consideration
│   └── Extracted from data.options_for_consideration[]
│       ├── Store discipline_id (UUID) + resolve → discipline name
│       └── Store vulnerability text reference
│
├── submission_vulnerability_ofc_links
│   └── Created by matching:
│       ├── OFC.vulnerability field
│       └── Vulnerability.vulnerability text
│
└── submission_sources
    └── Extracted from data.sources[] (if present)
```

---

## Key Principles

1. **Data Preservation**: The `submissions.data` column contains the **complete, unmodified** original data structure
2. **Dual Storage**: **Both IDs and names are stored** in normalized tables:
   - `discipline_id` + `discipline` (both stored)
   - `sector_id` + `sector` (both stored)
   - `subsector_id` + `subsector` (both stored)
   - IDs enable referential integrity and joins
   - Names enable easy querying and display
3. **No Data Loss**: Nothing is removed from the original data - it's only read and copied to separate tables
4. **Relationship Mapping**: OFCs are linked to vulnerabilities via the `submission_vulnerability_ofc_links` table using the `vulnerability` reference field
5. **Unique Constraints**: The link table has a UNIQUE constraint to prevent duplicate vulnerability-OFC links

---

## Example Mapping

### Input Data:
```json
{
  "source_file": "security_guide.pdf",
  "vulnerabilities": [
    {
      "vulnerability": "Inadequate access controls",
      "discipline_id": "abc-123",
      "sector_id": "def-456",
      "subsector_id": "ghi-789"
    }
  ],
  "options_for_consideration": [
    {
      "option_text": "Implement multi-factor authentication",
      "vulnerability": "Inadequate access controls",
      "discipline_id": "abc-123"
    }
  ]
}
```

### Result:

**submissions.data**: Contains the complete JSON above (unchanged)

**submission_vulnerabilities**:
- `vulnerability`: "Inadequate access controls"
- `discipline_id`: "abc-123" (UUID stored)
- `discipline`: "Access Control" (resolved from discipline_id)
- `category`: "Physical" (resolved from discipline)
- `sector_id`: "def-456" (UUID stored)
- `sector`: "Energy" (resolved from sector_id)
- `subsector_id`: "ghi-789" (UUID stored)
- `subsector`: "Power Grid" (resolved from subsector_id)

**submission_options_for_consideration**:
- `option_text`: "Implement multi-factor authentication"
- `vulnerability`: "Inadequate access controls" (text reference)
- `discipline_id`: "abc-123" (UUID stored)
- `discipline`: "Access Control" (resolved from discipline_id)

**submission_vulnerability_ofc_links**:
- Links the vulnerability to the OFC using their IDs

---

## Notes

- All original IDs and metadata remain in `submissions.data`
- The normalized tables use resolved names for easier querying
- The junction table (`submission_vulnerability_ofc_links`) maintains the many-to-many relationship between vulnerabilities and OFCs
- Sources are optional - if not present in the data, no source records are created

