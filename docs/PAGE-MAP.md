# PSA Tool - Page and Function Map

Complete reference of all pages, routes, and available functions in the PSA Tool application.

## 📋 Table of Contents

- [Public Pages](#public-pages)
- [User Pages](#user-pages)
- [Admin Pages](#admin-pages)
- [API Routes](#api-routes)
- [Component Functions](#component-functions)

---

## Public Pages

### `/splash` - Login/Landing Page
**File:** `app/splash/page.jsx`  
**Access:** Public (redirects to `/` if authenticated)

**Functions:**
- User authentication/login
- Session management
- Redirect to dashboard after successful login
- CISA branding and official system notice

**Features:**
- Email/password login form
- Session timeout warnings (5 minutes)
- Automatic redirect if already authenticated
- Error handling for failed login attempts

---

## User Pages

### `/` - PSA Tool Dashboard (Landing Dashboard)
**File:** `app/page.jsx`  
**Access:** Authenticated users only

**Functions:**
- View and search vulnerabilities
- Filter vulnerabilities by:
  - Discipline
  - Sector
  - Subsector
  - Search term
- View vulnerability details
- Quick actions:
  - Submit New Vulnerability
  - Submit Documents
  - View Profile

**Features:**
- Real-time vulnerability search
- Filter combinations
- Vulnerability card display
- Responsive grid layout
- Authentication check with redirect

---

### `/submit` - Submit New Vulnerability
**File:** `app/submit/page.jsx`  
**Access:** Authenticated users with submit permissions

**Functions:**
- Submit new vulnerability submissions
- Add Options for Consideration (OFCs)
- Select discipline and subdiscipline
- Add source citations
- Link vulnerabilities to sectors/subsectors

**Features:**
- Multi-step form
- Discipline/subdiscipline selection
- Citation validation
- OFC management
- Sector/subsector linking
- Form validation

---

### `/submit-psa` - Submit Documents for Processing
**File:** `app/submit-psa/page.jsx`  
**Component:** `PSASubmission`  
**Access:** Authenticated users

**Functions:**
- Upload documents for PSA processing
- Monitor processing status
- View processing results

**Features:**
- File upload interface
- Processing progress tracking
- Document management

---

### `/submit/bulk` - Bulk Submission
**File:** `app/submit/bulk/page.jsx`  
**Access:** Authenticated users

**Functions:**
- Bulk vulnerability submission
- Batch processing
- CSV/Excel import (if implemented)

---

### `/profile` - User Profile
**File:** `app/profile/page.jsx`  
**Access:** Authenticated users

**Functions:**
- View user profile information
- View submission history
- View returned submissions
- Edit profile (if implemented)

**Features:**
- Tabbed interface (Overview, Submissions, Returned)
- User statistics
- Submission tracking
- Profile management

---

### `/assessment` - Generate Vulnerability Assessment
**File:** `app/assessment/page.jsx`  
**Access:** Authenticated users  
**Status:** Under Development

**Planned Functions:**
- Generate vulnerability assessments from templates
- Customize assessment questions
- Export assessment reports

---

## Dashboard Pages

### `/dashboard` - Processing Dashboard
**File:** `app/dashboard/page.jsx`  
**Component:** `VOFCProcessingDashboard`  
**Access:** Authenticated users

**Functions:**
- Real-time document processing monitoring
- Service health monitoring (Flask, Ollama, Supabase)
- Pipeline status tracking
- Active processing job monitoring

**Features:**
- Live status updates
- Service health indicators
- Processing progress visualization
- System metrics

---

### `/dashboard/analytics` - Analytics Dashboard
**File:** `app/dashboard/analytics/page.jsx`  
**Access:** Authenticated users

**Functions:**
- View learning events metrics
- Model performance statistics
- Approval rates
- Confidence scores

**Features:**
- Total events counter
- Approved events counter
- Approval rate percentage
- Average confidence scores
- Latest model information
- Refresh functionality

---

## Admin Pages

### `/admin` - Admin Overview
**File:** `app/admin/page.jsx`  
**Access:** Admin users only

**Functions:**
- System statistics overview
- Service health monitoring (Flask, Ollama, Supabase)
- Database statistics
- User statistics
- Submission statistics
- Soft match statistics
- Processing progress monitoring

**Features:**
- Real-time health checks (20s interval)
- Statistics cards
- System status indicators
- Refresh functionality
- Quick navigation to admin sections

---

### `/admin/review` - Review Submissions
**File:** `app/admin/review/page.jsx`  
**Access:** Admin/Reviewer users

**Functions:**
- Review pending submissions
- Approve/reject submissions
- Check for duplicate vulnerabilities
- Check for duplicate OFCs
- Edit submission data
- View submission details

**Features:**
- Duplicate detection
- Bulk actions
- Submission filtering
- Auto-refresh (30s interval)
- Detailed submission view

---

### `/admin/users` - User Management
**File:** `app/admin/users/page.jsx`  
**Access:** Admin users only

**Functions:**
- View all users
- Create new users
- Edit user information
- Manage user roles
- Activate/deactivate users
- Force password changes
- View user profiles

**Features:**
- User list with filtering
- Role management (psa, admin, reviewer)
- User creation form
- User editing form
- Profile management

---

### `/admin/models` - Model Analytics
**File:** `app/admin/models/page.jsx`  
**Access:** Admin users only

**Functions:**
- View model performance metrics
- Model usage statistics
- Learning event analytics

---

### `/admin/ofc-requests` - OFC Requests Management
**File:** `app/admin/ofc-requests/page.jsx`  
**Access:** Admin users

**Functions:**
- View OFC requests
- Approve OFC requests
- Reject OFC requests
- Implement OFC requests

---

### `/admin/ofcs` - OFCs Management
**File:** `app/admin/ofcs/page.jsx`  
**Access:** Admin users

**Functions:**
- View all OFCs
- Manage OFCs
- OFC statistics

---

### `/admin/softmatches` - Soft Matches
**File:** `app/admin/softmatches/page.jsx`  
**Access:** Admin users

**Functions:**
- View soft matches
- Review potential duplicates
- Manage soft match rules

---

### `/admin/test` - Test Page
**File:** `app/admin/test/page.jsx`  
**Access:** Admin users  
**Purpose:** Testing/debugging

---

### `/admin/test-auth` - Authentication Test
**File:** `app/admin/test-auth/page.jsx`  
**Access:** Admin users  
**Purpose:** Authentication testing

---

## Learning Pages

### `/learning` - Learning Monitor
**File:** `app/learning/page.jsx`  
**Component:** `LearningMonitor`  
**Access:** Admin users only

**Functions:**
- Monitor continuous learning system
- View learning events
- Track model improvements
- Learning analytics

---

## API Routes

### Authentication (`/api/auth/*`)
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `POST /api/auth/register` - User registration
- `GET /api/auth/validate` - Validate session
- `GET /api/auth/permissions` - Get user permissions
- `GET /api/auth/verify` - Verify authentication

### System (`/api/system/*`)
- `GET /api/system/health` - System health check (Flask, Ollama, Supabase)
- `GET /api/dashboard/system` - Dashboard system status

### Submissions (`/api/submissions/*`)
- `GET /api/submissions` - List submissions
- `POST /api/submissions` - Create submission
- `GET /api/submissions/[id]` - Get submission details
- `POST /api/submissions/[id]/approve` - Approve submission
- `POST /api/submissions/[id]/reject` - Reject submission
- `POST /api/submissions/[id]/edit` - Edit submission
- `DELETE /api/submissions/[id]` - Delete submission
- `POST /api/submissions/bulk` - Bulk submission
- `POST /api/submissions/structured` - Structured submission
- `POST /api/submissions/ofc-request` - Create OFC request

### Admin (`/api/admin/*`)
- `GET /api/admin/stats` - Admin statistics
- `GET /api/admin/users` - List users
- `GET /api/admin/submissions` - List submissions
- `GET /api/admin/vulnerabilities` - List vulnerabilities
- `GET /api/admin/ofcs` - List OFCs
- `GET /api/admin/ofc-requests` - List OFC requests
- `POST /api/admin/ofc-requests/[id]/approve` - Approve OFC request
- `POST /api/admin/ofc-requests/[id]/reject` - Reject OFC request
- `POST /api/admin/ofc-requests/[id]/implement` - Implement OFC request
- `POST /api/admin/submissions/[id]/update-data` - Update submission data
- `POST /api/admin/generate-ofcs` - Generate OFCs
- `POST /api/admin/check-duplicates` - Check for duplicates
- `POST /api/admin/check-users-profiles` - Check user profiles
- `POST /api/admin/cleanup-tables` - Cleanup database tables
- `POST /api/admin/disable-rls` - Disable RLS (admin only)

### Dashboard (`/api/dashboard/*`)
- `GET /api/dashboard/overview` - Dashboard overview data
- `GET /api/dashboard/system` - System status for dashboard

### Analytics (`/api/analytics/*`)
- `GET /api/analytics/summary` - Analytics summary

### Files (`/api/files/*`)
- `GET /api/files/list` - List files

### Process (`/api/process/*`)
- `POST /api/process/start` - Start document processing

### Proxy (`/api/proxy/*`)
- `GET /api/proxy/flask/progress` - Flask processing progress

### Library (`/api/library/*`)
- `GET /api/library/search` - Search library
- `POST /api/library/search` - Advanced library search

### Disciplines (`/api/disciplines/*`)
- `GET /api/disciplines` - List disciplines
- `GET /api/disciplines/[id]` - Get discipline details

### Sectors (`/api/sectors/*`)
- `GET /api/sectors` - List sectors

### Subsectors (`/api/subsectors/*`)
- `GET /api/subsectors` - List subsectors

### Sources (`/api/sources/*`)
- `POST /api/sources/assign-citation` - Assign citation to source

---

## Component Functions

### VOFCProcessingDashboard
**Location:** `app/components/components/VOFCProcessingDashboard.jsx`

**Functions:**
- Real-time processing monitoring
- Service health display
- Progress tracking
- System metrics

### PSASubmission
**Location:** `app/components/components/PSASubmission.jsx`

**Functions:**
- Document upload
- Processing initiation
- Status monitoring

### LearningMonitor
**Location:** `app/components/components/LearningMonitor.jsx`

**Functions:**
- Learning event tracking
- Model performance monitoring
- Analytics display

### SubmissionReview
**Location:** `app/components/components/SubmissionReview.jsx`

**Functions:**
- Submission review interface
- Approval/rejection actions
- Duplicate checking

---

## Access Control

### Public Access
- `/splash` - Login page

### Authenticated Users
- `/` - Dashboard
- `/submit` - Submit vulnerability
- `/submit-psa` - Submit documents
- `/submit/bulk` - Bulk submission
- `/profile` - User profile
- `/assessment` - Generate assessment
- `/dashboard` - Processing dashboard
- `/dashboard/analytics` - Analytics dashboard

### Admin Only
- `/admin` - Admin overview
- `/admin/review` - Review submissions
- `/admin/users` - User management
- `/admin/models` - Model analytics
- `/admin/ofc-requests` - OFC requests
- `/admin/ofcs` - OFCs management
- `/admin/softmatches` - Soft matches
- `/admin/test` - Test page
- `/admin/test-auth` - Auth test
- `/learning` - Learning monitor

---

## Navigation Flow

```
/splash (Login)
    ↓ (Authenticated)
/ (Dashboard)
    ├─ /submit (Submit Vulnerability)
    ├─ /submit-psa (Submit Documents)
    ├─ /profile (User Profile)
    ├─ /dashboard (Processing Dashboard)
    ├─ /dashboard/analytics (Analytics)
    └─ /admin/* (Admin Pages - Admin Only)
```

---

## Notes

- All pages check authentication and redirect to `/splash` if not authenticated
- Admin pages require admin role
- Health checks run every 20 seconds on admin/system pages
- Submissions auto-refresh every 30 seconds on review page
- Session timeout: 5 minutes of inactivity
- All API routes require authentication (except `/api/auth/login`)

---

*Last Updated: 2025-11-06*

