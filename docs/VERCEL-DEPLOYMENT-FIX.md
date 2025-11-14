# Vercel Deployment Fix - Admin Pages Not Propagating

## Problem
Changes to admin pages were not propagating to Vercel deployments. This was caused by:
1. **Python services being included in Vercel builds** - The Flask app and folder watcher were being processed during Next.js builds
2. **Build cache issues** - Vercel was potentially caching builds that included Python files
3. **Webpack processing Python files** - Next.js webpack was attempting to process Python files during builds

## Solution

### 1. Created `.vercelignore` File
Excludes Python services and related files from Vercel deployments:
- Python files (`*.py`, `*.pyc`, etc.)
- Python services (`app.py`, `routes/`, `services/`)
- Data directories (`data/`, `logs/`, `training_data/`)
- Configuration files that shouldn't be in Vercel
- Tools and scripts directories

### 2. Updated `next.config.mjs`
Added webpack configuration to explicitly ignore Python files:
- Uses webpack's `IgnorePlugin` to prevent processing of `.py` files
- Prevents webpack from attempting to bundle Python modules

## Architecture Recommendation

**The watcher service should remain separate** - it's a Python service that runs on your local machine or a separate server, not on Vercel. This is the correct architecture:

- **Vercel**: Next.js frontend only
- **Separate Server**: Flask backend + folder watcher (runs via Cloudflare tunnel)

## Verification

After deploying these changes:
1. Push to your repository
2. Vercel should automatically rebuild
3. Check Vercel build logs to confirm Python files are excluded
4. Verify admin pages update correctly

## Files Changed
- `.vercelignore` (new)
- `next.config.mjs` (updated)

## Next Steps

If issues persist:
1. Clear Vercel build cache (Vercel dashboard → Settings → Build & Development Settings → Clear Build Cache)
2. Force a new deployment
3. Check Vercel build logs for any remaining Python file references

