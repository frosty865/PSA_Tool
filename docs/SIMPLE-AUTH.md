# Simple Authentication Setup

## Overview

This uses **Supabase Auth** + a simple `users_profiles` table with a `role` column. No complex permission tables needed.

## Database Setup

Run `scripts/simple-auth-setup.sql` - that's it. It creates:
- `users_profiles` table with `role` column
- Helper functions for role checks
- Indexes for performance

## Roles

- **`admin`** - Full admin access
- **`spsa`** - Full admin access (same as admin)
- **`psa`** - Standard user (can submit documents, view data)

## How It Works

### In Your Code

```javascript
// Check if user is admin
const user = await getCurrentUser();
const isAdmin = user?.role === 'admin' || user?.role === 'spsa';

// Or use the helper function
const isAdmin = await canAccessAdmin();
```

### Creating Users

When creating a user via `/api/admin/users`:
1. Create user in Supabase Auth
2. Insert into `users_profiles` with `role` set to 'admin', 'spsa', or 'psa'

That's it. No complex permission checks needed.

## Access Control

- **Admin/SPSA**: Can access `/admin/*` routes, manage users, review submissions
- **PSA**: Can submit documents, view approved data, no admin access

## Helper Functions

- `is_admin(user_id)` - Returns true if user is admin or spsa
- `get_user_role(user_id)` - Returns user's role (defaults to 'psa')

## That's It!

No complex tables, no permission matrices, just:
- Supabase Auth (handles login/password)
- `users_profiles.role` (determines access)
- Simple role checks in code

