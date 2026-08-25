# Deployment Guide

## Target Architecture

| Component | Platform | Cost | Notes |
|-----------|----------|------|-------|
| Frontend | Vercel | Free | Automatic deployments from Git |
| Database | Supabase | Free | PostgreSQL hosting, 500MB free tier |
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

# Backend dependencies
pip install -r backend/requirements.txt

# Pipeline dependencies (same as backend)
pip install -r data_pipeline/requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Run Pipeline

```bash
# Download and process IPL data
python -m data_pipeline.pipeline.run --format ipl --sample 200
```

### 3. Start Services

```bash
# Backend API (Terminal 1)
DATABASE_URL="sqlite:///data/cricket_intelligence.db" \
  uvicorn backend.main:app --reload --port 8000

# Frontend (Terminal 2)
cd frontend
VITE_API_URL="http://localhost:8000/api" npm run dev
```

### 4. Verify

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

## Production Deployment

### Frontend (Vercel)

1. Push code to GitHub
2. Connect repository to Vercel
3. Set environment variables:
   - `VITE_API_URL` — Your API endpoint URL
4. Deploy

### Database (Supabase)

1. Create a Supabase project
2. Go to SQL Editor
3. Run `database/schema.sql`
4. Note the connection string from Settings → Database
5. Set `DATABASE_URL` environment variable

### API (Vercel Serverless)

Option A: Vercel Serverless Functions
- Convert FastAPI routes to Vercel serverless functions
- Set `DATABASE_URL` environment variable

Option B: Railway / Render
- Deploy FastAPI as a web service
- Set `DATABASE_URL` environment variable
- Update frontend's `VITE_API_URL` to point to the deployed API

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

## Environment Variables

### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `sqlite:///data/cricket_intelligence.db` | Database connection string |
| `CORS_ORIGINS` | No | `http://localhost:5173,...` | Comma-separated allowed origins |

### Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | No | `/api` | Backend API base URL |

## Database Migration

When updating the schema:

1. Back up existing data (if needed)
2. Run the updated `database/schema.sql`
3. Re-run the pipeline to repopulate analytics

The pipeline is idempotent — running it again will not create duplicate data.

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

## Troubleshooting

### CORS errors

Ensure `CORS_ORIGINS` includes your frontend URL:
```bash
CORS_ORIGINS="http://localhost:5173,http://localhost:5176,https://your-app.vercel.app"
```

### Database connection errors

For PostgreSQL, ensure:
- `DATABASE_URL` is correct
- The database exists and schema is applied
- Network access is configured (Supabase requires SSL)

### Pipeline download failures

- Check internet connectivity
- Cricsheet may be temporarily unavailable
- Use `--force` to retry failed downloads
