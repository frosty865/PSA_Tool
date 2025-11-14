# Python Code Relocation - Quick Start

## Overview

All server-side Python code has been prepared for relocation to `C:\Tools\PSA-Flask`. The codebase has been updated to support the new location while maintaining backward compatibility.

## Quick Migration

1. **Run the migration script:**
   ```powershell
   .\scripts\migrate-python-to-tools.ps1
   ```

2. **Copy environment file:**
   ```powershell
   Copy-Item ".env" "C:\Tools\PSA-Flask\.env"
   ```
   Or use: `.\sync-env.ps1`

3. **Set up and test:**
   ```powershell
   cd C:\Tools\PSA-Flask
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   .\start.ps1
   ```

## What Changed

- ✅ All path references updated to support `C:\Tools\PSA-Flask`
- ✅ Backward compatibility maintained (checks new location first, falls back to legacy)
- ✅ Migration script created
- ✅ Documentation updated

## What Stays in Project

- `app/` - Next.js frontend
- `components/` - React components  
- `package.json` - Node.js dependencies
- `next.config.mjs` - Next.js config
- `.vercelignore` - Vercel deployment config

## What Moves to C:\Tools\PSA-Flask

- `app.py` - Flask entry point
- `routes/` - Route blueprints
- `services/` - Service modules
- `config/` - Configuration files
- `tools/` - Utility scripts
- `requirements.txt` - Python dependencies
- `start.ps1` - Startup script

## Documentation

- **Full Plan**: `docs/PYTHON-RELOCATION-PLAN.md`
- **Summary**: `docs/PYTHON-RELOCATION-SUMMARY.md`
- **Migration Script**: `scripts/migrate-python-to-tools.ps1`

## Need Help?

See `docs/PYTHON-RELOCATION-SUMMARY.md` for detailed troubleshooting and verification steps.

