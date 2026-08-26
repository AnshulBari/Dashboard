# Cricket Intelligence — Deployment Guide

## Architecture

```
Frontend (React + Vercel)
        ↓
Backend (FastAPI)
        ↓
PostgreSQL (Supabase)
        ↑
Data Pipeline (pandas + PySpark)
        ↑
Cricsheet (External Data)
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (Supabase or local)
- Java 8+ (for PySpark, optional)

## Environment Variables

### Backend

```bash
DATABASE_URL=postgresql://...         # Required for production
CORS_ORIGINS=http://localhost:5173    # Comma-separated allowed origins
```

### Frontend

```bash
VITE_API_URL=/api                     # API base URL (proxied in dev)
```

## Local Development

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Database

The backend automatically falls back to SQLite when `DATABASE_URL` is not set or points to a SQLite path.

For PostgreSQL (recommended):
1. Create a Supabase project
2. Set `DATABASE_URL` in `.env`
3. Run `database/schema.sql` in the Supabase SQL Editor
4. Run `python migration_phase1.py` to add Phase 1 tables

### 4. Data Pipeline

```bash
cd data_pipeline
pip install -r requirements.txt

# Download and process IPL data (sample)
python -m data_pipeline.pipeline.run --format ipl --sample 50

# Process full IPL dataset
python -m data_pipeline.pipeline.run --format ipl

# Process all formats
python -m data_pipeline.pipeline.run --format all
```

## Supabase Setup

### 1. Create Project

1. Go to https://supabase.com
2. Create a new project
3. Note the connection string from Settings → Database

### 2. Apply Schema

1. Open Supabase SQL Editor
2. Paste contents of `database/schema.sql`
3. Run the query

### 3. Apply Phase 1 Migration

```bash
# From project root
python migration_phase1.py
python migration_phase1.py --verify
```

### 4. Migrate Data from SQLite

```bash
# If you have an existing SQLite database with IPL data
python migrate_sqlite_to_pg.py
```

### 5. Process Full Dataset

```bash
# Download and process all IPL data into PostgreSQL
python -m data_pipeline.pipeline.run --format ipl --database-url "$DATABASE_URL"
```

## Production Deployment

### Vercel (Frontend)

1. Connect GitHub repo to Vercel
2. Set framework preset: Vite
3. Build command: `cd frontend && npm run build`
4. Output directory: `frontend/dist`
5. Add env vars: `VITE_API_URL`

### Backend

Deploy FastAPI to any Python-compatible platform:
- Railway
- Render
- Fly.io
- DigitalOcean App Platform

Set `DATABASE_URL` to your Supabase connection string.

## Schema Migration

### Phase 1 (Universal Cricket Data Model)

Non-destructive migration that adds:

- `format_config` table (format-specific rules)
- `seasons` table (season/edition modeling)
- `result_type`, `day_number`, `event_match_number` to `matches`
- `declared`, `all_out`, `follow_on` to `innings`
- `team_type` to `teams`
- `competition_type` to `competitions`
- `season_id` to `matches`
- New composite indexes

Run with:
```bash
python migration_phase1.py          # Apply migration
python migration_phase1.py --verify # Verify migration
python migration_phase1.py --dry-run # Preview changes
```

## Data Pipeline

### Architecture

```
Cricsheet ZIP → Extract JSON → Parse → Validate → Normalize → Write DB → Compute Analytics
```

### Running

```bash
# Full pipeline (IPL)
python -m data_pipeline.pipeline.run --format ipl

# With sample limit
python -m data_pipeline.pipeline.run --format ipl --sample 100

# Force re-download
python -m data_pipeline.pipeline.run --format ipl --force

# Target PostgreSQL
python -m data_pipeline.pipeline.run --format ipl --database-url "postgresql://..."
```

### Idempotency

The pipeline is idempotent:
- Running twice does not duplicate matches (checks `external_id`)
- Analytics tables are truncated and rebuilt
- Entity resolution caches existing IDs

### Supported Formats

| Format | Cricsheet Dataset | Coverage |
|--------|------------------|----------|
| IPL | `ipl_json.zip` | 2008-present |
| T20I | `t20i_json.zip` | Feb 2005-present |
| ODI | `odi_json.zip` | Jun 2002-present |
| Test | `test_json.zip` | Dec 2001-present |
