# Development Workflow

## Single Source of Truth: `C:\Tools\*`

**Edit directly in the deployed service directories - no syncing needed.**

## Service Locations

All backend services run from and are edited in:
- `C:\Tools\VOFC-Flask/` - Flask API server
- `C:\Tools\VOFC-Processor/` - Document processor
- `C:\Tools\Ollama/` - Ollama installation
- `C:\Tools\cloudflared/` - Cloudflare tunnel

## Development Workflow

1. **Edit directly in `C:\Tools\*`**
   - Make changes to service code in `C:\Tools\VOFC-Flask/` or `C:\Tools\VOFC-Processor/`
   - No syncing needed - edit where services run

2. **Commit to git (when ready)**
   - Copy changes from `C:\Tools\*` to project folder (`PSA_Tool/`) for version control
   - Commit and push to GitHub
   - Project folder is for git/version control only

3. **Deploy to Vercel (frontend only)**
   - Vercel automatically deploys from GitHub
   - Only Next.js frontend (`app/`, `public/`, etc.) is deployed
   - Backend services remain on Windows server

## Why This Approach?

- **No sync conflicts**: Edit directly where services run
- **Simpler workflow**: One location to edit, one location for git
- **No unnecessary steps**: No syncing from project to Tools
- **Stable paths**: Services always run from fixed `C:\Tools\*` paths

## Project Folder Purpose

The project folder (`PSA_Tool/`) serves as:
- **Version control**: Git repository for code history
- **Vercel deployment**: Frontend code for Next.js deployment
- **Backup/Archive**: Historical record of code changes

**Do not edit in project folder for backend services** - edit directly in `C:\Tools\*`.

## Service Restart

After editing code in `C:\Tools\*`:
```powershell
# Restart Flask
nssm restart vofc-flask

# Restart Processor
nssm restart VOFC-Processor
```

## Git Workflow

When ready to commit changes:
1. Copy modified files from `C:\Tools\*` to project folder
2. Commit to git: `git add . && git commit -m "message"`
3. Push to GitHub: `git push`

**Note**: Sync scripts are not needed for daily development - only for initial setup or major migrations.

