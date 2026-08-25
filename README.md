# 🏏 Cricket Intelligence Platform

> A data engineering and analytics platform that transforms raw cricket data into actionable intelligence.

**NOT a cricket score website.** This is a portfolio-grade data engineering project that demonstrates:
- PySpark ETL pipelines for historical ball-by-ball data
- Original analytical metrics (Player Form Score, Player Impact)
- PostgreSQL storage with precomputed analytical datasets
- FastAPI REST API serving analytical results
- React dashboard with interactive visualizations

## Architecture

```
RAW DATA (Cricsheet) → PySpark ETL → PostgreSQL → FastAPI → React Dashboard
```

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Data Pipeline | PySpark | Historical data processing and ETL |
| Database | PostgreSQL | Store precomputed analytical results |
| API | FastAPI | REST endpoints for analytical data |
| Frontend | React + Vite + TypeScript | Interactive analytics dashboard |
| Charts | Recharts | Data visualization |
| Deployment | Vercel (frontend) + Supabase (DB) | Free-tier hosting |

## Analytical Capabilities

- **Player Intelligence**: Batting/bowling stats, form scores, consistency, phase performance
- **Team Intelligence**: Strength ratings, win rates, phase performance, situational analysis
- **Venue Intelligence**: Score profiles, pace/spin balance, chasing advantages
- **Matchup Analytics**: Head-to-head batter vs bowler, pace vs spin breakdowns
- **Player Form Score**: Original weighted composite metric (0-100)
- **Player Impact**: Actual vs Expected performance differential
- **Rankings**: Platform-computed player and team rankings

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- SQLite (for local dev) or PostgreSQL

### One-Command Setup

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Create database, seed with sample data
python setup.py

# Start backend API (in one terminal)
DATABASE_URL='sqlite:///data/cricket_intelligence.db' uvicorn backend.main:app --reload --port 8000

# Start frontend (in another terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 to see the dashboard.
Open http://localhost:8000/docs for API documentation.

### Data Pipeline (Optional — requires Java + Spark)

```bash
pip install -r data_pipeline/requirements.txt
python -m data_pipeline.jobs.run_pipeline --format t20i --sample 100
```

## Project Structure

```
.
├── frontend/          # React + Vite + TypeScript dashboard
├── backend/           # FastAPI REST API (routes, models, schemas)
├── data_pipeline/     # PySpark ETL + analytics
│   ├── ingestion/     # Cricsheet data downloader
│   ├── spark/         # Read, normalize, transform, aggregate
│   ├── analytics/     # Form score, impact, matchups
│   ├── database/      # DB writer and seeder
│   └── jobs/          # Pipeline runner
├── database/          # PostgreSQL schema (schema.sql)
├── data/              # Raw, processed, analytics data (gitignored)
├── docs/              # Architecture and analytics documentation
├── setup.py           # One-command database setup + seeding
└── README.md
```

## Why PySpark?

Cricsheet contains 200K+ T20I deliveries, 500K+ ODI deliveries, and Test data spanning decades. PySpark provides:

1. **Parallel processing** — Window functions over large datasets
2. **Scalability** — Same code works for 1K or 1M matches
3. **DataFrame API** — Clean, declarative ETL
4. **Partitioning** — Efficient memory management
5. **Rich aggregations** — groupBy, joins, window functions natively

For a detailed comparison with Pandas, see [docs/analytics.md](docs/analytics.md).

## Data Sources

- **Cricsheet** (primary): Ball-by-ball historical data in JSON format
- **ICC** (reference): Official rankings and international information
- **RSS feeds**: Cricket news aggregation

**We do NOT scrape** ESPNcricinfo, Cricbuzz, or CREX.

## Analytics Methodology

### Player Form Score

Weighted composite of normalized statistical components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Recent Performance | 35% | Runs/wickets in last 10 innings |
| Consistency | 20% | Coefficient of variation |
| Opposition Strength | 15% | Performance vs ranked opponents |
| Venue Performance | 10% | Cross-venue consistency |
| Match Situation | 10% | Chasing vs setting performance |
| Efficiency | 10% | Strike rate × average composite |

Each component is min-max normalized to 0-100 across all players in the same format.

### Team Strength Score

```
Strength = 0.35 × Batting_Score + 0.35 × Bowling_Score + 0.30 × Win_Score
```

All components normalized to 0-100 using min-max scaling.

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://user:pass@host:5432/cricket_intelligence
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000/api
```

## License

MIT
