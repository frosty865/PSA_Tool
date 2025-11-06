# API Route to Page Mapping

This document lists all API routes and indicates whether they have associated frontend pages.

## Authentication APIs

| API Route | Method | Has Page? | Page Location | Notes |
|-----------|--------|-----------|---------------|-------|
| `/api/auth/login` | POST | ✅ Yes | `/login` | Login page |
| `/api/auth/logout` | POST | ✅ Yes | Used by navigation | Logout functionality |
| `/api/auth/register` | POST | ✅ Yes | `/login` | Registration form on login page |
| `/api/auth/verify` | GET | ✅ Yes | Used by multiple pages | Session verification |
| `/api/auth/validate` | POST | ❌ No | - | Token validation (internal) |
| `/api/auth/permissions` | GET | ❌ No | - | Permission checking (internal) |

## Admin APIs

| API Route | Method | Has Page? | Page Location | Notes |
|-----------|--------|-----------|---------------|-------|
| `/api/admin/audit` | GET | ✅ Yes | `/admin/audit` | Audit trail page |
| `/api/admin/stats` | GET | ✅ Yes | `/admin` | Admin overview dashboard |
| `/api/admin/submissions` | GET | ✅ Yes | `/admin/review`, `/review` | Submission review page |
| `/api/admin/submissions/[id]/update-data` | POST | ❌ No | - | Internal API for updating submission data |
| `/api/admin/users` | GET, POST | ✅ Yes | `/admin/users` | User management page |
| `/api/admin/vulnerabilities` | GET | ❌ No | - | Vulnerabilities API (used by components) |
| `/api/admin/ofcs` | GET | ✅ Yes | `/admin/ofcs` | OFCs management page |
| `/api/admin/ofc-requests` | GET | ✅ Yes | `/admin/ofc-requests` | OFC requests review page |
| `/api/admin/ofc-requests/[id]/approve` | POST | ✅ Yes | `/admin/ofc-requests` | Used by OFC requests page |
| `/api/admin/ofc-requests/[id]/reject` | POST | ✅ Yes | `/admin/ofc-requests` | Used by OFC requests page |
| `/api/admin/ofc-requests/[id]/implement` | POST | ✅ Yes | `/admin/ofc-requests` | Used by OFC requests page |
| `/api/admin/generate-ofcs` | POST | ❌ No | - | Internal API for OFC generation |
| `/api/admin/check-duplicates` | GET | ❌ No | - | Internal API for duplicate checking |
| `/api/admin/check-users-profiles` | GET | ❌ No | - | Internal API for user profile checking |
| `/api/admin/cleanup-tables` | POST | ❌ No | - | Internal admin utility |
| `/api/admin/disable-rls` | POST | ❌ No | - | Internal admin utility |

## Submissions APIs

| API Route | Method | Has Page? | Page Location | Notes |
|-----------|--------|-----------|---------------|-------|
| `/api/submissions` | GET, POST | ✅ Yes | `/submit`, `/submit-psa` | Submission pages |
| `/api/submissions/[id]` | GET | ❌ No | - | Get single submission (used by components) |
| `/api/submissions/[id]/approve` | POST | ✅ Yes | `/admin/review`, `/review` | Used by review page |
| `/api/submissions/[id]/reject` | POST | ✅ Yes | `/admin/review`, `/review` | Used by review page |
| `/api/submissions/[id]/edit` | POST | ❌ No | - | Edit submission (used by components) |
| `/api/submissions/[id]/delete` | POST | ❌ No | - | Delete submission (used by components) |
| `/api/submissions/[id]/approve-vulnerability` | POST | ❌ No | - | Approve specific vulnerability (used by components) |
| `/api/submissions/bulk` | POST | ✅ Yes | `/submit/bulk` | Bulk submission page |
| `/api/submissions/structured` | GET, POST | ✅ Yes | `/submit-psa` | Structured submission page |
| `/api/submissions/ofc-request` | POST | ❌ No | - | OFC request submission (used by components) |

## Dashboard APIs

| API Route | Method | Has Page? | Page Location | Notes |
|-----------|--------|-----------|---------------|-------|
| `/api/dashboard/overview` | GET | ✅ Yes | `/dashboard` | Dashboard overview page |
| `/api/dashboard/system` | GET | ✅ Yes | `/admin` | System health on admin page |

## Analytics & Learning APIs

| API Route | Method | Has Page? | Page Location | Notes |
|-----------|--------|-----------|---------------|-------|
| `/api/analytics/summary` | GET | ✅ Yes | `/admin`, `/dashboard/analytics` | Analytics summary |
| `/api/learning/stats` | GET | ✅ Yes | `/dashboard/learning` | Learning metrics dashboard |
| `/api/learning/heuristics` | GET | ❌ No | - | Heuristics API (used by components) |
| `/api/learning/retrain-events` | GET | ❌ No | - | Retrain events API (used by components) |

## Library & Search APIs

| API Route | Method | Has Page? | Page Location | Notes |
|-----------|--------|-----------|---------------|-------|
| `/api/library/search` | GET | ❌ No | - | Library search (used by components) |

## Taxonomy APIs

| API Route | Method | Has Page? | Page Location | Notes |
|-----------|--------|-----------|---------------|-------|
| `/api/disciplines` | GET | ✅ Yes | `/admin/disciplines` | Disciplines management |
| `/api/disciplines/[id]` | GET | ✅ Yes | `/admin/disciplines` | Single discipline |
| `/api/sectors` | GET | ✅ Yes | `/` (home page) | Sectors dropdown on home page |
| `/api/subsectors` | GET | ✅ Yes | `/` (home page) | Subsectors dropdown on home page |

## System & Health APIs

| API Route | Method | Has Page? | Page Location | Notes |
|-----------|--------|-----------|---------------|-------|
| `/api/system/health` | GET | ✅ Yes | `/admin` | System health on admin page |
| `/api/health` | GET | ❌ No | - | Basic health check (internal) |

## File & Process APIs

| API Route | Method | Has Page? | Page Location | Notes |
|-----------|--------|-----------|---------------|-------|
| `/api/files/list` | GET | ❌ No | - | File listing (used by components) |
| `/api/process/start` | POST | ❌ No | - | Process start (used by components) |
| `/api/proxy/flask/progress` | GET | ✅ Yes | `/admin` | Processing progress on admin page |

## Sources APIs

| API Route | Method | Has Page? | Page Location | Notes |
|-----------|--------|-----------|---------------|-------|
| `/api/sources/assign-citation` | POST | ❌ No | - | Assign citation (used by components) |

## Summary

### APIs WITH Pages (Frontend UI)
- ✅ **Authentication**: Login, Logout, Register
- ✅ **Admin**: Audit, Stats, Submissions Review, Users, OFCs, OFC Requests
- ✅ **Submissions**: Submit, Submit PSA, Bulk Submit, Review
- ✅ **Dashboard**: Overview, Analytics, Learning Metrics
- ✅ **Taxonomy**: Disciplines, Sectors, Subsectors
- ✅ **System**: Health monitoring

### APIs WITHOUT Pages (Backend/Component Only)
- ❌ **Internal Auth**: Validate, Permissions
- ❌ **Admin Utilities**: Check duplicates, Check users, Cleanup tables, Disable RLS
- ❌ **Submission Details**: Get single submission, Edit, Delete, Approve vulnerability
- ❌ **Learning**: Heuristics, Retrain events
- ❌ **Library**: Search
- ❌ **File/Process**: File list, Process start
- ❌ **Sources**: Assign citation
- ❌ **Health**: Basic health check

### Total Count
- **Total API Routes**: 49
- **APIs with Pages**: 25 (51%)
- **APIs without Pages**: 24 (49%)

## Notes

1. Some APIs are used by multiple pages (e.g., `/api/submissions/[id]/approve` is used by both `/admin/review` and `/review`)
2. Some APIs are internal utilities that don't need frontend pages
3. Component-only APIs are typically used by React components embedded in pages
4. The mapping may change as new pages are added or APIs are refactored

