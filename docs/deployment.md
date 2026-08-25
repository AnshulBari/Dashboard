# Deployment Guide

## Target Architecture

```
Vercel (Frontend) → Supabase PostgreSQL (Database)
                 ↕
              FastAPI (Backend)
                 ↕
         GitHub Actions (Pipeline Scheduler)
```

## Frontend (Vercel)

### Setup
1. Connect GitHub repository to Vercel
2. Configure build settings:
   - Root directory: `frontend`
   - Build command: `npm run build`
   - Output directory: `dist`
3. Add environment variable:
   - `VITE_API_URL`: Your backend API URL

### Deploy
```bash
# Automatic deployment on push to main
git push origin main

# Manual deployment
cd frontend && npm run build
vercel deploy --prod
```

## Database (Supabase)

### Setup
1. Create a free Supabase project
2. Run the schema:
   ```bash
   psql -h db.xxx.supabase.co -U postgres -d postgres -f database/schema.sql
   ```
3. Copy the connection string to your backend `.env`:
   ```
   DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
   ```

### Free Tier Limits
- 500MB database
- 50,000 monthly active users
- 500MB file storage
- Enough for development and moderate traffic

## Backend

### Option 1: Vercel Serverless (Recommended)
Convert FastAPI routes to Vercel serverless functions for zero-cost hosting.

### Option 2: Railway / Fly.io
Deploy FastAPI on a free-tier platform:
```bash
# Railway
railway init
railway add --service cricket-api
railway deploy
```

### Option 3: Local Development
```bash
cd backend
uvicorn backend.main:app --reload --port 8000
```

## Data Pipeline

### GitHub Actions (Scheduled)
```yaml
# .github/workflows/pipeline.yml
name: Data Pipeline
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday at 2 AM
  workflow_dispatch:

jobs:
  pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r data-pipeline/requirements.txt
      - run: python -m data_pipeline.jobs.run_pipeline --format t20i
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### Local Development
```bash
# Run pipeline locally
python -m data_pipeline.jobs.run_pipeline --format t20i --sample 100
```

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://user:pass@host:5432/cricket_intelligence
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://your-app.vercel.app
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000/api
# or for production:
# VITE_API_URL=https://your-backend.railway.app/api
```

### GitHub Secrets
```
DATABASE_URL=postgresql://...
```

## CI/CD Pipeline

1. **On Push**: Lint, typecheck, test
2. **On PR**: Build verification
3. **On Merge to Main**: Deploy frontend to Vercel
4. **Weekly**: Run data pipeline via GitHub Actions

## Monitoring

- **Vercel**: Function logs, performance metrics
- **Supabase**: Database metrics, query performance
- **Pipeline**: `pipeline_summary.json` with processing stats

## Cost Estimate

| Service | Tier | Cost |
|---------|------|------|
| Vercel | Hobby | Free |
| Supabase | Free | Free |
| Railway | Starter | $0 (if under usage) |
| GitHub Actions | Free | 2000 min/month |
| Cricsheet | Free | Data is open |

**Total: $0/month** for development and moderate traffic.
