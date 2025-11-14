# Project Organization

This document describes the organization of the PSA_Tool project structure.

## Root Directory

The root directory contains only essential project files:

### Core Configuration Files
- `app.py` - Flask application entry point
- `server.py` - Production server entry point (Waitress)
- `package.json` / `package-lock.json` - Node.js dependencies
- `requirements.txt` - Python dependencies
- `next.config.mjs` - Next.js configuration
- `tailwind.config.js` - Tailwind CSS configuration
- `tsconfig.json` - TypeScript configuration
- `postcss.config.js` - PostCSS configuration
- `env.example` - Environment variables template
- `.gitignore` - Git ignore rules
- `.vercelignore` - Vercel ignore rules

### Core Documentation (Root)
- `README.md` - Main project documentation
- `ARCHITECTURE.md` - Zero-Error Architecture standards
- `DESIGN.md` - System design principles
- `RULES.md` - Zero-Error Architecture rules

### Configuration Files
- `cloudflared-config.yml` - Cloudflare tunnel configuration (reference)

## Directory Structure

### `/app` - Next.js Application
Frontend React/Next.js application with pages, components, and API routes.

### `/components` - Shared React Components
Reusable React components used across the application.

### `/config` - Python Configuration Module
Centralized configuration management with validation:
- `__init__.py` - Config class and validation
- `api_contracts.py` - API response contracts
- `dependencies.py` - Dependency verification
- `exceptions.py` - Custom exception classes
- `service_health.py` - Service health checks
- `vofc_config.yaml` - VOFC engine configuration

### `/data` - Data Directory
- `errors/` - Error files
- `incoming/` - Incoming files to process
- `processed/` - Processed files
- `vofc_benchmarks.json` - Benchmark data

### `/docs` - Documentation
- `/debug/` - Debug summaries and fix documentation
- `/phase1/` - Phase 1 implementation plans and summaries
- `/phase2/` - Phase 2 implementation plans
- `/deployment/` - Deployment guides and verification docs
- `/archive/` - Archived/outdated documentation
- Core documentation files (architecture, design, etc.)

### `/heuristics` - Heuristic Patterns
Pattern matching rules and heuristics for document processing.

### `/logs` - Application Logs
Application log files.

### `/public` - Static Assets
Public assets served by Next.js (images, etc.).

### `/routes` - Flask Routes
Flask blueprints for API endpoints:
- `system.py` - System health and control
- `processing.py` - Document processing
- `analytics.py` - Analytics endpoints
- `learning.py` - Learning/ML endpoints
- `models.py` - Model information
- `service_manager.py` - Service management

### `/scripts` - Utility Scripts
PowerShell and shell scripts for:
- Service management
- Deployment
- Migration
- Testing
- Configuration

### `/services` - Backend Services
Python service modules:
- `processor/` - Document processing pipeline
- `ollama_client.py` - Ollama API client
- `supabase_client.py` - Supabase client
- `queue_manager.py` - Queue management

### `/sql` - SQL Scripts
Database scripts and migrations.

### `/styles` - CSS Styles
Custom CSS stylesheets.

### `/supabase` - Supabase Configuration
- `/migrations/` - Database migration scripts

### `/tests` - Test Files
Test scripts and test data.

### `/tools` - Development Tools
Development and utility tools:
- `vofc_processor/` - VOFC processor tool
- Training and evaluation scripts

### `/training_data` - Training Data
Model training data, examples, and configurations.

## File Organization Principles

1. **Root Directory**: Only essential configuration and core documentation
2. **Documentation**: Organized by purpose (debug, deployment, phases)
3. **Scripts**: All utility scripts in `/scripts`
4. **Tests**: All test files in `/tests`
5. **Data**: All data files in `/data` or appropriate subdirectories

## Finding Moved Files

If you're looking for a file that was moved:

- **Debug/Fix Summaries**: `docs/debug/`
- **Phase Plans**: `docs/phase1/` or `docs/phase2/`
- **Deployment Docs**: `docs/deployment/`
- **Test Files**: `tests/`
- **Scripts**: `scripts/`
- **Benchmarks**: `data/vofc_benchmarks.json`

