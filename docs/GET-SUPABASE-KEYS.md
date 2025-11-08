# How to Get Your Supabase Service Role Key

The service role key is required for server-side operations that bypass Row Level Security (RLS).

## Steps to Get Your Service Role Key

1. **Go to your Supabase Dashboard**
   - Visit: https://supabase.com/dashboard
   - Sign in to your account

2. **Select Your Project**
   - Click on your project (e.g., "PSA Tool")

3. **Go to Settings → API**
   - Click on "Settings" in the left sidebar
   - Click on "API" under the Project Settings section

4. **Find the Service Role Key**
   - Look for the "service_role" key (NOT the "anon" key)
   - It will be labeled as "service_role" and marked as "secret"
   - **WARNING**: This key has full access - never expose it in client-side code!

5. **Copy the Key**
   - Click the "Reveal" button or copy icon
   - The key should be very long (200+ characters)
   - It should start with `eyJ` (JWT format)

## Setting the Key in Your Environment

### PowerShell (Current Session)
```powershell
$env:SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### PowerShell (Permanent - User Level)
```powershell
[System.Environment]::SetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "User")
```

### .env File (For Next.js)
Create or update `.env.local` in your project root:
```env
SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Key Differences

| Key Type | Length | Starts With | Use Case |
|----------|--------|-------------|----------|
| **anon** | ~200 chars | `eyJ` | Client-side, respects RLS |
| **service_role** | ~200 chars | `eyJ` | Server-side only, bypasses RLS |

## Important Notes

- ⚠️ **NEVER** commit the service role key to git
- ⚠️ **NEVER** use the service role key in client-side code
- ✅ The service role key is safe to use in:
  - Python scripts (server-side)
  - Next.js API routes (server-side)
  - Environment variables (not in `.env` files committed to git)

## Verifying Your Key

Run the test script to verify:
```powershell
python scripts\test-supabase-connection.py
```

If you see "Invalid API key", you likely have:
- The wrong key (anon instead of service_role)
- A truncated key
- An old/revoked key

## If You Need to Regenerate the Key

1. Go to Supabase Dashboard → Settings → API
2. Find the "service_role" key section
3. Click "Reset" or "Regenerate"
4. Copy the new key
5. Update your environment variables
6. Restart any services using the key

