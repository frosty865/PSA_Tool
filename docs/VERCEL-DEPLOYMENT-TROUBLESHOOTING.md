# Vercel Deployment Troubleshooting Guide

## ✅ Python Scripts Status

**The Python scripts in `tools/` are correct and up to date:**
- ✅ Scripts reference correct Windows paths (`C:\Tools\*`)
- ✅ Scripts are properly structured and functional
- ✅ Scripts are correctly excluded from Vercel (via `.vercelignore`)

**Important:** Python scripts in `tools/` are **NOT deployed to Vercel** and should not be. They are server-side utilities that run on your Windows server.

## 🔍 Why Changes Aren't Propagating to Vercel

If frontend changes aren't showing up on Vercel, check these in order:

### 1. **Verify Git Push**
```bash
# Check if changes are committed and pushed
git status
git log --oneline -5

# If not pushed, push to trigger Vercel rebuild
git push origin main
```

### 2. **Check Vercel Build Status**
1. Go to Vercel dashboard
2. Check the latest deployment
3. Verify the commit hash matches your latest push
4. Check if build completed successfully (not failed or cancelled)

### 3. **Clear Vercel Build Cache**
If builds are succeeding but changes aren't appearing:
1. Vercel Dashboard → Your Project → Settings
2. Build & Development Settings
3. Click "Clear Build Cache"
4. Trigger a new deployment

### 4. **Force New Deployment**
```bash
# Make a small change to trigger rebuild
echo "# Trigger rebuild" >> README.md
git add README.md
git commit -m "Trigger Vercel rebuild"
git push origin main
```

Or in Vercel dashboard:
- Go to Deployments
- Click "..." on latest deployment
- Select "Redeploy"

### 5. **Check Browser Cache**
Your browser may be caching the old version:
- Hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
- Or clear browser cache completely
- Or test in incognito/private mode

### 6. **Verify Environment Variables**
Check Vercel environment variables are set correctly:
- Vercel Dashboard → Project → Settings → Environment Variables
- Required: `NEXT_PUBLIC_FLASK_URL` = `https://flask.frostech.site`
- After changing env vars, redeploy

### 7. **Check Build Logs**
1. Vercel Dashboard → Deployments → Latest deployment
2. Click on the deployment to see build logs
3. Look for errors or warnings
4. Verify Python files are being excluded (should see `.vercelignore` working)

## 📋 Deployment Checklist

Before reporting deployment issues, verify:

- [ ] Changes are committed to git
- [ ] Changes are pushed to GitHub (`git push`)
- [ ] Vercel build completed successfully (check dashboard)
- [ ] Build logs show no errors
- [ ] Browser cache cleared (hard refresh)
- [ ] Tested in incognito mode
- [ ] Environment variables are set correctly in Vercel
- [ ] `.vercelignore` includes `tools/` (should not deploy Python scripts)

## 🎯 What Gets Deployed to Vercel

**✅ Deployed (Frontend only):**
- `app/` - Next.js pages and API routes
- `public/` - Static assets
- `components/` - React components
- `package.json` - Dependencies
- `next.config.mjs` - Next.js configuration
- `tailwind.config.js` - Tailwind configuration

**❌ NOT Deployed (Excluded by `.vercelignore`):**
- `tools/` - Python scripts (server-side only)
- `scripts/` - PowerShell scripts (server-side only)
- `routes/` - Flask routes (backend only)
- `services/` - Python services (backend only)
- `*.py` - All Python files
- `data/` - Data directories
- `logs/` - Log files
- `docs/` - Documentation

## 🐛 Common Issues

### Issue: "Changes not showing after push"
**Solution:**
1. Wait 1-2 minutes for Vercel to rebuild
2. Check Vercel dashboard for build status
3. Clear build cache and redeploy
4. Clear browser cache

### Issue: "404 errors on new routes"
**Solution:**
1. Verify route file exists in `app/api/` or `app/`
2. Verify route exports correct function (`GET`, `POST`, etc.)
3. Wait for Vercel rebuild (1-2 minutes)
4. Check build logs for errors

### Issue: "503 errors on API routes"
**Solution:**
1. This is expected if Flask backend is down
2. Check Flask service: `sc query vofc-flask`
3. Check tunnel service: `sc query VOFC-Tunnel`
4. Verify `NEXT_PUBLIC_FLASK_URL` is set in Vercel

## 📝 Notes

- **Python scripts in `tools/` are NOT the issue** - they're correctly excluded
- **Vercel only deploys frontend** - backend runs on Windows server
- **Builds are automatic** - push to GitHub triggers Vercel rebuild
- **Cache can cause issues** - clear both Vercel cache and browser cache

## 🔗 Related Documentation

- `docs/VERCEL-DEPLOYMENT-FIX.md` - Previous deployment fixes
- `docs/WORKFLOW.md` - Development workflow
- `docs/deployment/PRODUCTION-ROUTE-VERIFICATION.md` - Route verification

