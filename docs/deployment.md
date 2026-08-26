# Deployment Guide

## Target Architecture

| Component | Platform | Cost | Notes |
|-----------|----------|------|-------|
| Frontend | Vercel | Free | Automatic deployments from Git |
| Database | Supabase | Free | PostgreSQL hosting, 500 MB free tier |
| API | Vercel Serverless / Railway | Free tier | FastAPI compatible |
| Pipeline | Local / GitHub Actions | Free | Batch processing, not real-time |

## Prerequisites

- Python 3.10+
- Node.js 18+
- Git
- Vercel CLI (for frontend deployment)
- Supabase account (for production database)

## Local Development

### 1. Clone and Install

```bash
git clone <repository-url>
cd cricket-intelligence

# Backend dependencies (includes psycopg2-binary, python-dotenv, SQLAlchemy, etc.)
pip install -r backend/requirements.txt

# Pipeline dependencies
pip install -r data_pipeline/requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Set Up Database

**Option A: SQLite (zero setup)**

```bash
# Download and process IPL data from Cricsheet
python -m data_pipeline.pipeline.run --format ipl
```

This creates `data/cricket_intelligence.db` with real data.

**Option B: Supabase PostgreSQL**

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Go to SQL Editor and run `database/schema.sql`
3. Copy the connection string from Settings → Database
4. Create `.env` at the project root:

```bash
DATABASE_URL=postgresql://postgres.<ref>:<password>@<host>:5432/postgres
```

5. Run the pipeline (writes directly to PostgreSQL):

```bash
python -m data_pipeline.pipeline.run --format ipl
```

**Option C: Migrate existing SQLite to PostgreSQL**

```bash
# 1. Process data locally first
python -m data_pipeline.pipeline.run --format ipl

# 2. Migrate to Supabase
python migrate_sqlite_to_pg.py
```

### 3. Start Services

```bash
# Backend API (Terminal 1)
DATABASE_URL="sqlite:///data/cricket_intelligence.db" \
  uvicorn backend.main:app --reload --port 8000

# Or if using .env with PostgreSQL:
uvicorn backend.main:app --reload --port 8000

# Frontend (Terminal 2)
cd frontend
VITE_API_URL="http://localhost:8000/api" npm run dev
```

### 4. Verify

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

---

## Production Deployment

### Frontend (Vercel)

1. Push code to GitHub
2. Connect repository to Vercel
3. Set environment variable:
   - `VITE_API_URL` — Your deployed API endpoint URL
4. Deploy

### Database (Supabase)

1. Create a Supabase project
2. Go to **SQL Editor**
3. Run the contents of `database/schema.sql`
4. Copy the connection string from **Settings → Database**
5. Set `DATABASE_URL` environment variable in your API deployment

**Important:** Supabase passwords may contain special characters (like `[` and `]`). If you encounter connection errors:
- URL-encode the brackets: `[` → `%5B`, `]` → `%5D`
- Use the Session pooler (port `5432`) for reliable connections
- If Supabase circuit breaker triggers, wait 60 seconds before retrying

### API Deployment

**Option A: Vercel Serverless Functions**

Convert FastAPI routes to Vercel serverless functions. Set `DATABASE_URL` environment variable.

**Option B: Railway / Render**

Deploy FastAPI as a web service:
1. Connect GitHub repository
2. Set `DATABASE_URL` environment variable
3. Update frontend's `VITE_API_URL` to point to the deployed API

### Pipeline (GitHub Actions)

The pipeline runs offline and doesn't need to be deployed as a service. Options:

1. **Manual execution** — Run locally when data refresh is needed
2. **GitHub Actions** — Schedule periodic pipeline runs
3. **Cron job** — Run on a server

Example GitHub Actions workflow:

```yaml
name: Refresh Cricket Data
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday at 2 AM
  workflow_dispatch:

jobs:
  pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r data_pipeline/requirements.txt
      - run: python -m data_pipeline.pipeline.run --format all
      - uses: actions/upload-artifact@v3
        with:
          name: cricket-data
          path: data/cricket_intelligence.db
```

---

## Environment Variables

### Backend (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `sqlite:///data/cricket_intelligence.db` | Database connection string |
| `CORS_ORIGINS` | No | `http://localhost:5173,...` | Comma-separated allowed origins |

### Frontend (`.env` or inline)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | No | `/api` | Backend API base URL |

---

## Database Migration

### SQLite → PostgreSQL (`migrate_sqlite_to_pg.py`)

Transfers all data from the local SQLite database to Supabase PostgreSQL.

```bash
python migrate_sqlite_to_pg.py
```

**What it does:**
1. Reads all 13 populated tables from SQLite
2. Truncates corresponding PostgreSQL tables (with `RESTART IDENTITY CASCADE`)
3. Writes data preserving all UUIDs
4. Verifies row counts match
5. Runs 10 foreign-key integrity checks
6. Reports any orphaned rows or count mismatches

**Verified results:**

| Table | SQLite | PostgreSQL | Status |
|-------|--------|------------|--------|
| teams | 11 | 11 | ✅ |
| players | 807 | 807 | ✅ |
| venues | 50 | 50 | ✅ |
| competitions | 1 | 1 | ✅ |
| matches | 1,243 | 1,243 | ✅ |
| innings | 2,514 | 2,514 | ✅ |
| deliveries | 295,732 | 295,732 | ✅ |
| player_batting_stats | 738 | 738 | ✅ |
| player_bowling_stats | 577 | 577 | ✅ |
| player_form | 571 | 571 | ✅ |
| team_performance | 11 | 11 | ✅ |
| venue_stats | 20 | 20 | ✅ |
| batter_bowler_matchups | 9,502 | 9,502 | ✅ |

All 10 foreign-key integrity checks pass with zero orphaned rows.

### Schema updates

When updating the schema:
1. Back up existing data (if needed)
2. Run the updated `database/schema.sql` in Supabase SQL Editor
3. Re-run the pipeline to repopulate analytics

The pipeline is idempotent — running it again will not create duplicate data.

---

## Monitoring

### Health Check

```bash
curl http://localhost:8000/api/health
# {"status": "healthy"}
```

### Database Stats

```bash
python -c "
from data_pipeline.pipeline.db_manager import DatabaseManager
db = DatabaseManager()
counts = db.get_table_counts()
for table, count in counts.items():
    print(f'{table}: {count}')
db.close()
"
```

### Pipeline Logs

The pipeline logs to stdout with timestamps:
```
2026-08-26 01:58:15 [INFO] [Stage 1] Downloading ipl data from Cricsheet...
2026-08-26 01:58:20 [INFO] [Stage 2] Read 200 matches, 47542 deliveries
2026-08-26 01:58:55 [INFO] [Stage 7] Wrote 237 rows to player_batting_stats
```

---

## Troubleshooting

### CORS errors

Ensure `CORS_ORIGINS` includes your frontend URL:
```bash
CORS_ORIGINS="http://localhost:5173,http://localhost:5176,https://your-app.vercel.app"
```

### Database connection errors

For PostgreSQL, ensure:
- `DATABASE_URL` is correct in `.env`
- The database exists and schema is applied
- Network access is configured (Supabase requires SSL)
- Password special characters are URL-encoded

### Supabase circuit breaker

If you see `ECIRCUITBREAKER`:
1. Wait 60 seconds
2. Verify the password is correct (copy fresh from Supabase dashboard)
3. URL-encode special characters in the password
4. Try the Session pooler connection (port 5432)

### Pipeline download failures

- Check internet connectivity
- Cricsheet may be temporarily unavailable
- Use `--force` to retry failed downloads

### Frontend shows no data

1. Verify backend is running: `curl http://localhost:8000/api/health`
2. Check `VITE_API_URL` matches the backend URL
3. Check browser console for CORS errors
4. Verify `CORS_ORIGINS` includes the frontend origin
