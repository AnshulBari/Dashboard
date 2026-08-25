# 🏏 Cricket Intelligence Platform

> A data engineering and analytics platform that transforms raw historical cricket ball-by-ball data into actionable intelligence — player form, team strength, venue profiles, batter-bowler matchups, and platform-computed rankings.

**This is NOT a cricket score website.** It is a portfolio-grade data engineering project that demonstrates end-to-end data pipeline design, analytical computing, and full-stack visualization.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [How It Works — End to End](#how-it-works--end-to-end)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Running the Data Pipeline](#running-the-data-pipeline)
- [API Reference](#api-reference)
- [Analytics Methodology](#analytics-methodology)
- [Data Sources](#data-sources)
- [Data Coverage & Limitations](#data-coverage--limitations)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [Development Notes](#development-notes)
- [License](#license)

---

## What It Does

The platform ingests **ball-by-ball cricket data** from [Cricsheet](https://cricsheet.org/), processes it through a data pipeline, computes analytical statistics, stores them in a database, and presents them through a REST API and React dashboard.

### Questions the platform answers

| Category | Example Questions |
|----------|------------------|
| **Player Intelligence** | Who is currently in form? Who performs best against a specific opponent? How does a player perform in the powerplay vs death overs? |
| **Team Intelligence** | Which teams are strongest in particular phases? Which teams chase best? How does a team's bowling economy compare across formats? |
| **Venue Intelligence** | Which venues favor batting? Which venues have a high chasing win rate? What is the average first innings score at a venue? |
| **Matchup Analytics** | Which batters dominate a specific bowler? How does a batter perform against pace vs spin? |
| **Rankings** | Who are the top 10 batters by form score? Who are the leading wicket-takers? |

### Key analytical metrics

- **Player Form Score** — An original weighted composite metric (0–100) measuring current player form across six normalized components
- **Team Strength Score** — An explainable composite of batting strength, bowling strength, and win rate
- **Batter-Bowler Matchups** — Head-to-head statistics derived from actual ball-by-ball data
- **Phase-Specific Performance** — Powerplay, middle overs, and death overs breakdowns
- **Venue Profiles** — Average scores, chasing advantage, pace/spin wicket distribution

---

## Architecture

```
                    ┌─────────────────┐
                    │   DATA SOURCES  │
                    │   (Cricsheet)   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  DATA INGESTION │
                    │  Download &     │
                    │  Extract ZIP    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   RAW DATA      │
                    │  (JSON files)   │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │    PIPELINE (pandas)     │
              │                          │
              │  1. Read JSON            │
              │  2. Validate             │
              │  3. Resolve entities     │
              │  4. Write to database    │
              │  5. Compute analytics    │
              │  6. Write analytics      │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │       PostgreSQL /       │
              │       SQLite             │
              │                          │
              │  • Core entities         │
              │  • Match data            │
              │  • Precomputed analytics │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │    FastAPI REST API      │
              │                          │
              │  /api/players            │
              │  /api/teams              │
              │  /api/venues             │
              │  /api/matches            │
              │  /api/matchups           │
              │  /api/rankings           │
              └────────────┬─────────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │   React Dashboard        │
              │   (Vite + TypeScript)    │
              │                          │
              │  • Dashboard overview    │
              │  • Player intelligence   │
              │  • Team analytics        │
              │  • Venue profiles        │
              │  • Matchup explorer      │
              │  • Match history         │
              └──────────────────────────┘
```

### Separation of concerns

| Layer | Responsibility | Technology |
|-------|---------------|------------|
| **Ingestion** | Download and extract Cricsheet data | Python `requests` + `zipfile` |
| **Pipeline** | Parse, validate, normalize, compute analytics | Python + pandas |
| **Storage** | Persist entities and precomputed analytics | SQLite (dev) / PostgreSQL (prod) |
| **API** | Serve analytical data over REST | FastAPI + SQLAlchemy |
| **Frontend** | Visualize analytics in an interactive dashboard | React + Vite + TypeScript + Tailwind |

**Important design principle:** The pipeline runs **offline** as a batch process. The API and frontend **never** compute expensive statistics at request time — they only query precomputed results. This keeps the application layer fast and lightweight.

---

## How It Works — End to End

### Step 1: Data Ingestion

The pipeline downloads compressed ZIP files from Cricsheet containing one JSON file per match:

```
Cricsheet ZIP → Extract → data/raw/ipl/*.json (1,243 match files)
```

Each JSON file contains:
- `info` — Match metadata (teams, venue, date, toss, result, players, registry IDs)
- `innings` — Ball-by-ball data organized by innings → overs → deliveries

### Step 2: Parse & Flatten

The `reader.py` module reads each JSON file and flattens it into a DataFrame with **one row per delivery**:

```python
# For a typical T20 match, this produces ~300 rows
# Each row contains:
{
  "match_id": "1175338",
  "match_date": "2017-04-05",
  "format": "T20",
  "venue": "M.Chinnaswamy Stadium",
  "batting_team": "Royal Challengers Bangalore",
  "bowling_team": "Sunrisers Hyderabad",
  "innings_number": 1,
  "over_number": 0,
  "ball_in_over": 1,
  "batter": "CH Gayle",
  "bowler": "B Kumar",
  "runs_batter": 0,
  "runs_total": 0,
  "is_wicket": false,
  ...
}
```

### Step 3: Validate

Data quality checks filter out:
- Deliveries with null batter or bowler
- Negative run values
- Impossible over numbers
- Invalid ball-in-over values

### Step 4: Entity Resolution

The pipeline discovers all unique entities from the raw data and maps them to stable UUIDs:

- **Teams** — "Royal Challengers Bangalore" → canonical team with UUID
- **Players** — "V Kohli" → canonical player with UUID, role inferred from batting/bowling appearances
- **Venues** — "M.Chinnaswamy Stadium" → canonical venue with UUID
- **Competitions** — "Indian Premier League" → competition record

This is the critical step that ensures the same entity is never duplicated, regardless of how different data sources spell the name.

### Step 5: Write Core Data

The pipeline writes to the database in order:
1. **Teams** → `teams` table
2. **Players** → `players` table (with role inferred)
3. **Venues** → `venues` table
4. **Competitions** → `competitions` table
5. **Matches** → `matches` table (with foreign keys to teams, venue, competition)
6. **Innings** → `innings` table (with foreign keys to match and batting/bowling teams)
7. **Deliveries** → `deliveries` table (with foreign keys to innings, match, players)

### Step 6: Compute Analytics

Using the delivery-level data, the pipeline computes:

**Player Batting Stats** — Grouped by (player, format):
- Matches, innings, runs, average, strike rate, 4s, 6s, fifties, hundreds
- Phase-specific: powerplay runs/SR, middle runs/SR, death runs/SR
- Situational: chasing runs/SR, first innings runs/SR
- Consistency score (coefficient of variation)

**Player Bowling Stats** — Grouped by (player, format):
- Matches, overs, wickets, economy, bowling average, strike rate
- Phase-specific: powerplay/middle/death overs, wickets, economy

**Player Form Score** — Weighted composite metric (see [Analytics Methodology](#analytics-methodology))

**Team Performance** — Grouped by (team, format):
- Win rate, average scores, phase-wise scoring, strength scores

**Venue Stats** — Grouped by (venue, format):
- Average scores, highest/lowest totals, phase-wise scoring

**Batter-Bowler Matchups** — Grouped by (batter, bowler, format):
- Minimum 10 balls for statistical significance

### Step 7: Serve via API

The FastAPI backend exposes REST endpoints that query the precomputed analytics:

```
GET /api/players?format=T20&sort_by=form_score&limit=10
GET /api/players/{id}?format=T20
GET /api/teams?format=T20
GET /api/venues?format=T20
GET /api/matches?format=T20&limit=10
GET /api/rankings?format=T20&category=batting
GET /api/matchups/{batter_id}/{bowler_id}
```

### Step 8: Visualize

The React dashboard displays the data through:
- **Dashboard** — Overview with stat cards, trending players table, team rankings, recent matches, venue insights
- **Players** — Searchable player list with form scores, filterable by role/country
- **Player Detail** — Full player profile with batting stats, bowling stats, form breakdown
- **Teams** — Team strength rankings with win rates
- **Venues** — Venue profiles with scoring averages
- **Matchups** — Head-to-head batter vs bowler explorer
- **Matches** — Match history with results

---

## Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Data Pipeline** | Python + pandas | Handles Cricsheet data volumes (~5M deliveries) in memory; no Java dependency |
| **Data Ingestion** | Python `requests` | Simple HTTP download with checksum verification |
| **Database (dev)** | SQLite | Zero setup, same SQL schema as PostgreSQL |
| **Database (prod)** | PostgreSQL (Supabase) | Production-grade, free tier available |
| **ORM** | SQLAlchemy | Database-agnostic queries, schema management |
| **API** | FastAPI | Auto-generated docs, async support, Pydantic validation |
| **Frontend** | React + TypeScript | Type-safe, component-based UI |
| **Build Tool** | Vite | Fast dev server and production builds |
| **Styling** | Tailwind CSS | Utility-first CSS, consistent design system |
| **Charts** | Recharts | React-native charting library |
| **Routing** | React Router | Client-side navigation |
| **Deployment** | Vercel (frontend) | Free hosting with automatic deployments |

###为什么不 PySpark?

PySpark is included in the project as a reference implementation in `data_pipeline/spark/`. However, the primary pipeline uses **pandas** because:

1. **No Java dependency** — PySpark 3.5 requires Java 8–17; the available Java 23 is incompatible
2. **Adequate for current data volumes** — Cricsheet's full dataset (~5M deliveries) fits comfortably in pandas memory
3. **Simpler debugging** — No JVM startup, no Spark UI, no serialized closures
4. **Faster iteration** — Direct Python debugging, no `spark-submit`

The PySpark code in `data_pipeline/spark/` demonstrates the same algorithms and can be activated if the data volume grows beyond pandas capacity or if a compatible Java version is installed.

---

## Project Structure

```
cricket-intelligence/
│
├── frontend/                          # React dashboard
│   ├── src/
│   │   ├── pages/                     # Page components
│   │   │   ├── Dashboard.tsx          # Overview with real API data
│   │   │   ├── Players.tsx            # Player list with filters
│   │   │   ├── PlayerDetail.tsx       # Individual player profile
│   │   │   ├── Teams.tsx              # Team strength rankings
│   │   │   ├── TeamDetail.tsx         # Individual team analytics
│   │   │   ├── Venues.tsx             # Venue list
│   │   │   ├── VenueDetail.tsx        # Individual venue profile
│   │   │   ├── Matchups.tsx           # Batter vs bowler explorer
│   │   │   ├── Matches.tsx            # Match history
│   │   │   ├── Rankings.tsx           # Player rankings
│   │   │   ├── Live.tsx               # Live match center (stub)
│   │   │   └── News.tsx               # Cricket news (stub)
│   │   ├── services/api.ts            # API client functions
│   │   ├── types/index.ts             # TypeScript type definitions
│   │   ├── layouts/Layout.tsx         # Sidebar navigation layout
│   │   ├── App.tsx                    # Router configuration
│   │   └── index.css                  # Tailwind + custom styles
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                           # FastAPI REST API
│   ├── main.py                        # App entry point, CORS, router setup
│   ├── routes/
│   │   ├── players.py                 # Player list, detail, form, batting, bowling, matchups
│   │   ├── teams.py                   # Team list, detail, analytics
│   │   ├── venues.py                  # Venue list, analytics
│   │   ├── matches.py                 # Match list, detail
│   │   ├── matchups.py                # Head-to-head matchups
│   │   ├── rankings.py                # Player rankings by format/category
│   │   ├── news.py                    # News (stub)
│   │   └── live.py                    # Live matches (stub)
│   ├── models/entities.py             # SQLAlchemy ORM models
│   ├── schemas/responses.py           # Pydantic response schemas
│   └── utils/database.py              # Database connection management
│
├── data_pipeline/                     # Data engineering pipeline
│   ├── pipeline/                      # ACTIVE pipeline (pandas-based)
│   │   ├── reader.py                  # Cricsheet JSON → flat DataFrame
│   │   ├── db_manager.py              # Entity resolution + DB writes
│   │   ├── analytics.py               # All statistical computations
│   │   └── run.py                     # Main pipeline orchestrator
│   │
│   ├── ingestion/
│   │   └── cricsheet.py              # Cricsheet download + extract
│   │
│   ├── spark/                         # REFERENCE PySpark implementation
│   │   ├── session.py                 # Spark session configuration
│   │   ├── read.py                    # JSON → Spark DataFrame
│   │   ├── normalize.py               # Team/player name canonicalization
│   │   ├── transform.py               # Cumulative stats, phase classification
│   │   ├── player_stats.py            # Career/recent batting & bowling
│   │   ├── team_stats.py              # Team performance metrics
│   │   ├── venue_stats.py             # Venue analytics
│   │   └── matchup_stats.py           # Batter vs bowler matchups
│   │
│   ├── analytics/
│   │   └── form_score.py              # PySpark form score (reference)
│   │
│   ├── database/
│   │   ├── writer.py                  # Spark DataFrame → PostgreSQL writer
│   │   └── seeder.py                  # Demo data seeder for testing
│   │
│   └── jobs/
│       └── run_pipeline.py            # PySpark pipeline runner (reference)
│
├── database/
│   └── schema.sql                     # PostgreSQL schema (20+ tables)
│
├── data/                              # Gitignored
│   ├── raw/                           # Downloaded Cricsheet ZIPs + JSONs
│   ├── processed/                     # Pipeline intermediate output
│   └── analytics/                     # Pipeline analytics output
│
├── docs/                              # Detailed documentation
│   ├── architecture.md
│   ├── data-model.md
│   ├── data-pipeline.md
│   ├── analytics.md
│   └── deployment.md
│
├── setup.py                           # One-command database setup
├── .env.example                       # Environment variable template
└── README.md                          # This file
```

---

## Quick Start

### Prerequisites

- **Python 3.10+** — for the pipeline and backend
- **Node.js 18+** — for the frontend
- **Java** — NOT required for the pandas pipeline (only needed for the PySpark reference implementation)

### 1. Install Dependencies

```bash
# Backend
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### 2. Set Up Database with Real Data

```bash
# Run the pipeline on IPL data (downloads ~5MB from Cricsheet, processes 200 matches)
python -m data_pipeline.pipeline.run --format ipl --sample 200
```

This creates `data/cricket_intelligence.db` with real IPL data including:
- 200 matches, 47,542 deliveries
- 261 players, 11 teams, 20 venues
- Precomputed batting/bowling stats, form scores, matchups

### 3. Start the Backend API

```bash
DATABASE_URL="sqlite:///data/cricket_intelligence.db" \
  uvicorn backend.main:app --reload --port 8000
```

API docs available at http://localhost:8000/docs

### 4. Start the Frontend

```bash
cd frontend
VITE_API_URL="http://localhost:8000/api" npm run dev
```

Dashboard available at http://localhost:5173

---

## Running the Data Pipeline

The pipeline processes Cricsheet data in stages. Each stage can be run independently.

### Available formats

| Format | Cricsheet ID | Command |
|--------|-------------|---------|
| IPL | `ipl` | `--format ipl` |
| T20 International | `t20i` | `--format t20i` |
| ODI | `odi` | `--format odi` |
| Test | `test` | `--format test` |
| All formats | `all` | `--format all` |

### Common commands

```bash
# Process 200 IPL matches (quick test, ~50 seconds)
python -m data_pipeline.pipeline.run --format ipl --sample 200

# Process ALL IPL matches (1,243 matches, ~10 minutes)
python -m data_pipeline.pipeline.run --format ipl

# Process T20I international matches
python -m data_pipeline.pipeline.run --format t20i --sample 100

# Force re-download even if data exists
python -m data_pipeline.pipeline.run --format ipl --force --sample 50
```

### Pipeline stages

```
Stage 1: INGEST   → Download ZIP from Cricsheet, extract JSON files
Stage 2: READ     → Parse JSON into flat delivery-level DataFrame
Stage 3: VALIDATE → Check data quality, reject malformed records
Stage 4: RESOLVE  → Discover entities, map names to UUIDs, infer roles
Stage 5: WRITE    → Write teams, players, venues, matches, innings, deliveries
Stage 6: COMPUTE  → Calculate player stats, team stats, venue stats, matchups, form scores
Stage 7: WRITE    → Write analytical results to database
Stage 8: REPORT   → Print summary statistics
```

### Idempotency

Running the pipeline twice does NOT create duplicate data. The pipeline uses:
- `INSERT OR IGNORE` for core entities (matches have `external_id` UNIQUE constraint)
- Truncate-then-insert for analytical tables (since they're fully recomputed)
- UUID-based entity resolution ensures the same player is never created twice

---

## API Reference

### Base URL
```
http://localhost:8000
```

### Endpoints

#### Players

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/players` | List players with filtering and sorting |
| GET | `/api/players/{id}` | Get detailed player profile |
| GET | `/api/players/{id}/form` | Get form score with component breakdown |
| GET | `/api/players/{id}/batting` | Get batting statistics |
| GET | `/api/players/{id}/bowling` | Get bowling statistics |
| GET | `/api/players/{id}/matchups` | Get matchup data against opponents |

**Query parameters:**
- `format` — T20, T20I, ODI, Test (default: T20)
- `role` — batsman, bowler, allrounder, wicketkeeper
- `country` — Filter by country
- `sort_by` — form_score, runs, wickets, batting_average
- `limit` — Number of results (max 200)
- `offset` — Pagination offset

#### Teams

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/teams` | List all teams with strength ratings |
| GET | `/api/teams/{id}` | Get team details |
| GET | `/api/teams/{id}/analytics` | Get comprehensive team analytics |

#### Venues

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/venues` | List venues with key statistics |
| GET | `/api/venues/{id}/analytics` | Get venue analytics |

#### Matches

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/matches` | List matches with filtering |
| GET | `/api/matches/{id}` | Get match details |

#### Matchups

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/matchups/{batter_id}/{bowler_id}` | Get head-to-head matchup |

#### Rankings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rankings` | Get platform rankings |

**Query parameters:**
- `format` — T20, T20I, ODI, Test
- `category` — batting, bowling, allrounder

#### Other

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/news` | Cricket news (placeholder) |
| GET | `/api/live` | Live matches (placeholder) |
| GET | `/api/health` | Health check |
| GET | `/docs` | Auto-generated Swagger UI |

---

## Analytics Methodology

### Player Form Score

The Form Score is an **original, project-defined metric** (not an official cricket metric). It provides a single 0–100 score representing a player's current form.

**Formula:**

```
Form Score = 0.35 × Recent_Performance
          + 0.20 × Consistency
          + 0.15 × Opposition_Strength
          + 0.10 × Venue_Performance
          + 0.10 × Match_Situation
          + 0.10 × Efficiency
```

**Component definitions:**

| Component | Weight | Calculation |
|-----------|--------|-------------|
| **Recent Performance** | 35% | Average runs in last 10 innings, min-max normalized across all players in format |
| **Consistency** | 20% | 1 − (coefficient of variation), normalized. Lower variance = higher score |
| **Opposition Strength** | 15% | Weighted average performance against all opponents, weighted by balls faced |
| **Venue Performance** | 10% | 1 − (CV of averages across venues). Players who perform well everywhere score higher |
| **Match Situation** | 10% | Ratio of chasing average to overall average. Chasing under pressure = higher score |
| **Efficiency** | 10% | Strike rate × average / 100. Combines speed and reliability of run-scoring |

**Normalization:** Each component is min-max normalized to 0–100 within the same format, so the best player gets 100 and the worst gets 0 for each component.

**Minimum innings:** A player needs at least 3 innings for statistical significance. Players with fewer innings are excluded.

**Limitations:**
- Requires sufficient data (3+ innings)
- Weights are initial estimates, not scientifically validated
- Cold start problem for new players
- Not adjusted for match importance or tournament context

### Team Strength Score

```
Strength = 0.35 × Batting_Score + 0.35 × Bowling_Score + 0.30 × Win_Score
```

Where:
- **Batting Score** = Min-max normalized average total score (0–100)
- **Bowling Score** = Inverse min-max normalized economy rate (0–100, lower economy = higher score)
- **Win Score** = Win rate percentage (0–100)

### Batter-Bowler Matchups

Computed from all deliveries where a specific batter faced a specific bowler:
- **Minimum 10 balls** for statistical significance
- Includes: balls, runs, wickets, strike rate, average, dot balls, boundaries

### Phase Classification

| Phase | Overs | Description |
|-------|-------|-------------|
| Powerplay | 1–6 | Fielding restrictions, aggressive batting |
| Middle | 7–15 | Consolidation, spin dominance |
| Death | 16–20 | High-scoring, yorkers, variations |

---

## Data Sources

### Primary: Cricsheet

[Cricsheet](https://cricsheet.org/) provides freely available ball-by-ball cricket data in JSON format.

- **URL:** https://cricsheet.org/downloads/
- **License:** Free for non-commercial use with attribution
- **Format:** One JSON file per match
- **Coverage:** International and domestic cricket

**Downloaded datasets:**

| Dataset | Typical Size | Matches | Deliveries |
|---------|-------------|---------|------------|
| IPL | ~5 MB | ~1,243 | ~350K |
| T20I | ~10 MB | ~2,000 | ~600K |
| ODI | ~30 MB | ~2,500 | ~1.4M |
| Test | ~50 MB | ~1,200 | ~2.4M |

### What we do NOT do

- ❌ Scrape ESPNcricinfo, Cricbuzz, or CREX
- ❌ Bypass CAPTCHAs, bot protection, or rate limits
- ❌ Copy entire copyrighted articles
- ❌ Make the platform dependent on a single data provider

---

## Data Coverage & Limitations

### Historical coverage

Cricsheet's ball-by-ball data begins approximately at:

| Format | Earliest Data |
|--------|--------------|
| Tests | December 2001 |
| ODIs | June 2002 |
| T20Is | February 2005 |
| IPL | 2008 |

**The platform does NOT represent pre-2001 cricket at the delivery level.** Pre-2001 historical data may be added in the future if a suitable source is found.

### Data quality notes

- Player names use Cricsheet's format (e.g., "V Kohli" not "Virat Kohli")
- Some matches may have incomplete data
- The platform validates data quality but cannot fix source errors
- Team names are normalized to canonical forms (e.g., "Delhi Daredevils" → "Delhi Capitals" for historical matches)

### What's NOT yet implemented

- Win probability machine learning model (planned for later)
- Live match data (requires external API provider)
- News aggregation (requires RSS feed integration)
- Player Impact metric (actual vs expected performance)

---

## Environment Variables

### Backend (`.env`)

```bash
# Database connection
DATABASE_URL=sqlite:///data/cricket_intelligence.db  # Local dev
# DATABASE_URL=postgresql://user:pass@host:5432/cricket_intelligence  # Production

# CORS (comma-separated origins)
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176
```

### Frontend (`.env` or inline)

```bash
# API base URL
VITE_API_URL=http://localhost:8000/api
```

---

## Deployment

### Target architecture

| Component | Platform | Notes |
|-----------|----------|-------|
| Frontend | Vercel | Free tier, automatic deployments from Git |
| Database | Supabase | Free PostgreSQL hosting |
| API | Vercel Serverless / separate host | FastAPI compatible with serverless |
| Pipeline | Local / GitHub Actions | Batch processing, not real-time |

### Frontend deployment (Vercel)

```bash
cd frontend
# Vercel auto-detects Vite projects
# Set VITE_API_URL environment variable in Vercel dashboard
```

### Database setup (Supabase)

1. Create a Supabase project
2. Run `database/schema.sql` in the SQL editor
3. Set `DATABASE_URL` environment variable

---

## Development Notes

### Running tests

```bash
# Backend API smoke test
DATABASE_URL="sqlite:///data/cricket_intelligence.db" python test_api_smoke.py

# Frontend typecheck
cd frontend && npx tsc --noEmit

# Frontend build
cd frontend && npx vite build
```

### Adding a new data source

1. Create a new ingestor in `data_pipeline/ingestion/`
2. Implement the same interface as `CricsheetIngestor` (download, extract, list_matches)
3. The pipeline's `reader.py` expects one JSON file per match with `info` and `innings` fields
4. Entity resolution handles name normalization automatically

### Database schema

The full PostgreSQL schema is in `database/schema.sql`. Key design decisions:
- UUID primary keys for all entities (stable internal IDs, not display names)
- Foreign keys enforced at the database level
- Analytical tables are denormalized for read performance
- Indexes on frequently queried columns (player_id, team_id, format, date)

### Data pipeline design

The pipeline follows the ETL pattern:
- **Extract** — Download from Cricsheet
- **Transform** — Parse, validate, normalize, compute analytics
- **Load** — Write to database

Each stage is independently testable and produces well-defined output.

---

## License

MIT
