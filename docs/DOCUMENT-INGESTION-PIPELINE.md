# Document Ingestion Pipeline - Complete Specification

## Overview

This document describes the complete 7-phase document ingestion pipeline for processing technical guidance documents (e.g., UFC 4-010-01) into the VOFC Library system.

---

## PHASE 1: Document Ingestion

**Purpose**: Bring a new PDF into the pipeline and create the parent submission.

### Endpoint
- **Route**: `POST /api/documents/submit`
- **Location**: `app/api/documents/submit/route.js`

### Submission Record Structure

| Field | Value | Notes |
|-------|-------|-------|
| `id` | `auto (gen_random_uuid())` | Primary key |
| `type` | `'vulnerability'` | All technical guidance treated as vulnerability sources |
| `status` | `'pending'` | Awaiting extraction |
| `source` | `'document_upload'` | Flags origin |
| `data` | JSONB object | See below |
| `submitter_email` | auto or manual | Optional |
| `submitted_by` | user UUID | Optional |
| `created_at` | `now()` | Auto-generated |
| `updated_at` | `now()` | Auto-generated |

### Data Field Structure

```json
{
  "document_upload": true,
  "filename": "ufc_4_010_01_2018_c1.pdf",
  "source_type": "UFC",
  "publication_date": "2018-10-01",
  "agency": "Department of Defense",
  "url": null,
  "source_title": "UFC 4-010-01",
  "author_org": "Department of Defense",
  "publication_year": 2018,
  "content_restriction": "public",
  "file_size": 1234567,
  "file_type": "application/pdf"
}
```

---

## PHASE 2: Text & Structure Extraction

**Purpose**: Extract text, detect sections, capture tables/figures.

### Service
- **File**: `services/document_extractor.py`
- **Function**: `extract_from_document()`

### Extraction Pipeline

1. **Text Layer Conversion**
   - Uses `services/preprocess.py` → `extract_text()`
   - Supports: PyMuPDF, pdfplumber, PyPDF2

2. **Section Detection**
   - **Pattern**: `^(\d+(\.\d+)*)(\s+)([A-Z].+)`
   - **Captures**: section number, section title, paragraph text
   - **Example**: `"2-3.5 Glazing and Windows"` → section `"2-3.5"`, title `"Glazing and Windows"`

3. **Table & Figure Capture**
   - **Pattern**: `Table \d+[: ]+([^\n]{10,200})`
   - **Pattern**: `Figure \d+[: ]+([^\n]{10,200})`
   - Stored in `enhanced_extraction` metadata

4. **Contextual Block Grouping**
   - Each section becomes a potential `submission_vulnerability` candidate
   - Paragraphs grouped by section hierarchy

---

## PHASE 3: Vulnerability Extraction

**Purpose**: Identify "what can go wrong" clauses using heuristic pattern matching.

### Service
- **File**: `services/document_extractor.py`
- **Function**: `extract_vulnerabilities()`

### Heuristic Rules

| Pattern | Example Match | Action |
|---------|---------------|--------|
| `"shall not"`, `"should not"`, `"must not"` | "Windows shall not face vehicle approach zones." | Create vulnerability |
| `"failure to"`, `"lack of"`, `"absence of"` | "Lack of stand-off distance…" | Create vulnerability |
| `"if X is not Y"` | "If glazing is not laminated…" | Create vulnerability |
| `"is required to"` (negated) | "When not required to meet…" | Contextual vulnerability |
| `"non-compliant"`, `"non-conforming"` | "Non-compliant installations…" | Create vulnerability |

### submission_vulnerabilities Fields

| Field | Example Value |
|-------|---------------|
| `submission_id` | parent UUID |
| `vulnerability` | "Glazing shall not be used within 10 m of controlled perimeters." |
| `discipline` | "Architectural Design" |
| `sector` | "Defense Installations" |
| `subsector` | "Facilities Engineering" |
| `source` | "UFC 4-010-01 (2018 Change 1)" |
| `source_title` | same as above |
| `source_url` | null or link |
| `parser_version` | "vofc-parser:latest" |
| `enhanced_extraction` | `{ "section": "2-3.5", "heading": "Glazing and Windows", "paragraph": "..." }` |

---

## PHASE 4: Options for Consideration (OFC) Extraction

**Purpose**: Capture mitigation or design compliance measures.

### Service
- **File**: `services/document_extractor.py`
- **Function**: `extract_ofcs()`

### Detection Patterns

| Type | Triggers | Example |
|------|----------|---------|
| **Prescriptive OFC** | `shall`, `must`, `required to` | "All exterior doors shall resist blast loads." |
| **Advisory OFC** | `should`, `recommended`, `ensure`, `consider` | "Consider use of laminated glass to reduce fragmentation." |
| **Conditional OFC** | `when`, `where`, `if possible` | "Where vehicle approach is possible, install bollards." |

### submission_options_for_consideration Fields

| Field | Example Value |
|-------|---------------|
| `submission_id` | parent UUID |
| `vulnerability_id` | linked ID (if paired) |
| `option_text` | "Provide laminated glass to minimize fragmentation risk." |
| `discipline` | "Architectural Design" |
| `source` | "UFC 4-010-01 (2018 Change 1)" |
| `confidence_score` | 0.92 |
| `pattern_matched` | "should" |
| `context` | paragraph excerpt |
| `citations` | `[{"section": "2-3.5", "page": 17}]` |

---

## PHASE 5: Link & Source Association

**Purpose**: Connect vulnerabilities to OFCs and associate sources.

### Service
- **File**: `services/document_extractor.py`
- **Function**: `create_vulnerability_ofc_links()`

### Linking Rules

- **Proximity**: ≤ 3 paragraphs or same section
- **Link Type**: `'direct'` (same section) or `'inferred'` (nearby)
- **Confidence**: 0.9 (direct) or 0.7 (inferred)

### Tables Created

1. **submission_vulnerability_ofc_links**
   - Links vulnerabilities to OFCs
   - Fields: `submission_id`, `vulnerability_id`, `ofc_id`, `link_type`, `confidence_score`

2. **submission_sources**
   - Single entry per document
   - Fields: `source_title`, `author_org`, `publication_year`, `source_url`, `content_restriction`

3. **submission_ofc_sources**
   - Links each OFC to source record
   - Fields: `submission_id`, `ofc_id`, `source_id`

---

## PHASE 6: Review Workflow

**Purpose**: Reviewer validation of extracted data.

### Endpoint
- **Route**: `GET /api/submissions` (filter: `status='pending_review'`)
- **Page**: `/admin/review` or `/review`

### Review Process

1. Reviewer opens review page
2. Loads all submissions with `status='pending_review'`
3. Each extracted vulnerability/OFC pair shown with:
   - Section citation
   - Confidence score
   - Text preview
4. Reviewer actions:
   - **Approve** → `status='approved'`
   - **Reject** → adds `rejection_reason`
   - **Comment** → stored in `review_comments`

---

## PHASE 7: Promotion (Optional)

**Purpose**: Promote approved entries to production VOFC Library tables.

### Supabase Function

```sql
SELECT promote_submission_to_library(submission_id uuid);
```

### Promotion Process

1. Transfers approved vulnerabilities → `vulnerabilities` table
2. Transfers approved OFCs → `options_for_consideration` table
3. Creates links in `vulnerability_ofc_links`
4. Promotes sources to `sources` table
5. Links via `ofc_sources`
6. Marks submission as archived

---

## Complete Workflow Summary

```
PDF Upload
   ↓
[PHASE 1] Submissions Table Entry (status='pending_review')
   ↓
[PHASE 2] Parser → Extract Text, Sections, Rules
   ↓
[PHASE 3] Generate Vulnerability Records
   ↓
[PHASE 4] Generate OFC Records
   ↓
[PHASE 5] Create Links & Source Associations
   ↓
[PHASE 6] Reviewer Validation (status='pending_review' → 'approved')
   ↓
[PHASE 7] Promotion to Library (optional)
```

---

## API Endpoints

### Document Submission
- **POST** `/api/documents/submit` - Upload document and create submission (PHASE 1)

### Extraction
- **POST** `/api/documents/extract/<submission_id>` - Run extraction pipeline (PHASE 2-5)
- **POST** `/api/documents/extract-pending` - Extract all pending submissions

### Review
- **GET** `/api/submissions` - List submissions for review (PHASE 6)
- **POST** `/api/submissions/<id>/approve` - Approve submission
- **POST** `/api/submissions/<id>/reject` - Reject submission

### Promotion
- **POST** `/api/submissions/<id>/promote` - Promote to library (PHASE 7)

---

## Implementation Status

- ✅ **PHASE 1**: Document submission with `status='pending'`
- ✅ **PHASE 2**: Text extraction and section detection
- ✅ **PHASE 3**: Vulnerability extraction with heuristics
- ✅ **PHASE 4**: OFC extraction with pattern matching
- ✅ **PHASE 5**: Link creation and source association
- ✅ **PHASE 6**: Review workflow (existing)
- ⚠️ **PHASE 7**: Promotion function (needs verification)

---

## Usage Example

```bash
# 1. Upload document
curl -X POST https://api.example.com/api/documents/submit \
  -F "file=@ufc_4_010_01_2018_c1.pdf" \
  -F "source_title=UFC 4-010-01" \
  -F "source_type=UFC" \
  -F "publication_year=2018" \
  -F "author_org=Department of Defense"

# Response: { "submission_id": "uuid-here", ... }

# 2. Trigger extraction (auto-triggered, or manual)
curl -X POST https://api.example.com/api/documents/extract/{submission_id}

# 3. Review (via web UI)
# Navigate to /admin/review

# 4. Approve
curl -X POST https://api.example.com/api/submissions/{id}/approve

# 5. Promote (optional)
curl -X POST https://api.example.com/api/submissions/{id}/promote
```

