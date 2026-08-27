# 🏏 Cricket Intelligence Platform

> A data engineering and analytics platform that transforms raw historical cricket ball-by-ball data into actionable intelligence — player form, team strength, venue profiles, batter-bowler matchups, and platform-computed rankings.

**This is NOT a cricket score website.** It is a portfolio-grade data engineering project demonstrating end-to-end pipeline design, analytical computing, and full-stack visualization.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [How It Works — End to End](#how-it-works--end-to-end)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Running the Data Pipeline](#running-the-data-pipeline)
- [Database Migration (SQLite → PostgreSQL)](#database-migration-sqlite--postgresql)
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

The platform ingests **ball-by-ball cricket data** from [Cricsheet](https://cricsheet.org/), processes it through a data pipeline, computes analytical statistics, stores them in PostgreSQL, and presents them through a REST API and React dashboard.

### Current data loaded

| Metric | Value |
|--------|-------|
| Matches | 4,789 (1,243 IPL + 3,533 T20I + 8 ODI + 5 Test) |
| Deliveries | 1,134,952 |
| Players | 5,084 (discovered from match data) |
| Teams | 125 (IPL franchises + international nations) |
| Venues | 336 |
| Competitions | 12 (IPL, World Cup, Champions Trophy, Ashes, bilateral) |
| Batting stats | 5,089 player-format records |
| Bowling stats | 3,828 player-format records |
| Form scores | 3,798 |
| Batter-bowler matchups | 35,920 |
| Player-team affiliations | 6,903 |

**Formats supported:** IPL T20 · International T20I · ODI · Test

**Datasets loaded:**
- **IPL T20:** 1,243 matches / 295,732 deliveries (full Cricsheet dataset)
- **International T20I:** 5 matches / 518 deliveries (representative fixtures)
- **ODI:** 8 matches / 793 deliveries (World Cup, Champions Trophy, Asia Cup, bilateral)
- **Test:** 5 matches / 1,340 deliveries (4-innings, draws, declarations, follow-ons)

### Questions the platform answers

| Category | Example Questions |
|----------|------------------|
| **Player Intelligence** | Who is currently in form? Who performs best against a specific opponent? How does a player perform in the powerplay vs death overs? |
| **Team Intelligence** | Which teams are strongest in particular phases? Which teams chase best? How does a team's bowling economy compare? |
| **Venue Intelligence** | Which venues favor batting? Which venues have a high chasing win rate? What is the average first innings score? |
| **Matchup Analytics** | Which batters dominate a specific bowler? How does a batter perform against pace vs spin? |
| **Rankings** | Who are the top 10 batters by form score? Who are the leading wicket-takers? |

### Key analytical metrics

- **Player Form Score** — Original weighted composite metric (0–100) across six normalized components
- **Team Strength Score** — Explainable composite of batting strength, bowling strength, and win rate
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
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
    ┌──────────────────┐   ┌──────────────────┐
    │  SQLite (dev)    │   │ PostgreSQL (prod) │
    │  cricket_        │   │  Supabase         │
    │  intelligence.db │   │  (cloud-hosted)   │
    └────────┬─────────┘   └────────┬─────────┘
             │                      │
             └──────────┬───────────┘
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

### Data flow

| Layer | Responsibility | Technology |
|-------|---------------|------------|
| **Ingestion** | Download and extract Cricsheet data | Python `requests` + `zipfile` |
| **Pipeline** | Parse, validate, normalize, compute analytics | Python + pandas |
| **Storage (dev)** | Local development database | SQLite (`data/cricket_intelligence.db`) |
| **Storage (prod)** | Production database | PostgreSQL via Supabase |
| **Migration** | SQLite → PostgreSQL data transfer | `migrate_sqlite_to_pg.py` |
| **API** | Serve analytical data over REST | FastAPI + SQLAlchemy |
| **Frontend** | Visualize analytics in an interactive dashboard | React + Vite + TypeScript + Tailwind |

**Design principle:** The pipeline runs **offline** as a batch process. The API and frontend **never** compute expensive statistics at request time — they only query precomputed results from PostgreSQL.

---

## How It Works — End to End

### Step 1: Data Ingestion

The pipeline downloads compressed ZIP files from Cricsheet containing one JSON file per match:

```
Cricsheet ZIP → Extract → data/raw/ipl/*.json (1,243 match files for IPL)
```

Each JSON file contains:
- `info` — Match metadata (teams, venue, date, toss, result, players, registry IDs)
- `innings` — Ball-by-ball data organized by innings → overs → deliveries

### Step 2: Parse & Flatten

The `reader.py` module reads each JSON file and flattens it into a DataFrame with **one row per delivery**:

```python
# For a typical T20 match, this produces ~240 rows
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
  "non_striker": "V Kohli",
  "runs_batter": 0,
  "runs_total": 0,
  "is_wicket": false,
  "wicket_type": null,
  "dismissed_player": null,
  "event_name": "Indian Premier League",
  ...
}
```

### Step 3: Validate

Data quality checks filter out:
- Deliveries with null batter or bowler
- Negative run values
- Impossible over numbers (>100)
- Invalid ball-in-over values (not 1–9)

### Step 4: Entity Resolution

The pipeline discovers all unique entities from the raw data and maps them to stable UUIDs:

- **Teams** — "Royal Challengers Bangalore" → canonical team with UUID (also normalizes historical names like "Delhi Daredevils" → "Delhi Capitals")
- **Players** — "V Kohli" → canonical player with UUID; role inferred from bowling appearances (30+ balls bowled → bowler/allrounder)
- **Venues** — "M.Chinnaswamy Stadium" → canonical venue with UUID
- **Competitions** — "Indian Premier League" → competition record

This step ensures the same entity is never duplicated, regardless of how different sources spell the name.

### Step 5: Write Core Data

The pipeline writes to the database in dependency order:
1. **Teams** → `teams` table
2. **Players** → `players` table (with role inferred)
3. **Venues** → `venues` table
4. **Competitions** → `competitions` table
5. **Matches** → `matches` table (with FKs to teams, venue, competition)
6. **Innings** → `innings` table (with FKs to match and batting/bowling teams)
7. **Deliveries** → `deliveries` table (with FKs to innings, match, players)

### Step 6: Compute Analytics

Using the delivery-level data, the pipeline computes:

**Player Batting Stats** — Grouped by (player, format):
- Matches, innings, not outs, runs, average, strike rate, highest score
- 4s, 6s, fifties, hundreds, boundary %, dot ball %
- Phase-specific: powerplay/middle/death runs and strike rates
- Situational: chasing runs/SR, first innings runs/SR
- Consistency score (coefficient of variation)

**Player Bowling Stats** — Grouped by (player, format):
- Matches, innings, overs, balls bowled, wickets, runs conceded
- Economy, bowling average, strike rate, dot ball %
- Phase-specific: powerplay/middle/death overs, wickets, economy

**Player Form Score** — Weighted composite metric (see [Analytics Methodology](#analytics-methodology))

**Team Performance** — Grouped by (team, format):
- Wins, losses, win rate, average scores by phase
- Batting strength, bowling strength, overall strength scores
- Chasing win %, defending win %

**Venue Stats** — Grouped by (venue, format):
- Average scores (1st/2nd innings), highest/lowest totals
- Chasing/defending wins and win rates
- Pace/spin wicket percentages, phase-wise scoring
- Boundary frequency, toss decision win rates

**Batter-Bowler Matchups** — Grouped by (batter, bowler, format):
- Minimum 10 balls for statistical significance
- Balls, runs, wickets, strike rate, average, dot balls, boundaries, sixes

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
| **Data Pipeline** | Python + pandas | Handles Cricsheet volumes (~5M deliveries) in memory; no Java dependency |
| **Data Ingestion** | Python `requests` | Simple HTTP download with checksum verification |
| **Database (dev)** | SQLite | Zero setup, same SQL schema as PostgreSQL |
| **Database (prod)** | PostgreSQL (Supabase) | Production-grade, free tier, 500 MB storage |
| **ORM** | SQLAlchemy 2.x | Database-agnostic queries, works with both SQLite and PostgreSQL |
| **API** | FastAPI | Auto-generated docs, async support, Pydantic validation |
| **Frontend** | React + TypeScript | Type-safe, component-based UI |
| **Build Tool** | Vite | Fast dev server and production builds |
| **Styling** | Tailwind CSS | Utility-first CSS, consistent design system |
| **Charts** | Recharts | React-native charting library |
| **Routing** | React Router | Client-side navigation |
| **Deployment** | Vercel (frontend) + Supabase (DB) | Free hosting with automatic deployments |

### Why pandas instead of PySpark?

PySpark is included in the project as a reference implementation in `data_pipeline/spark/`. However, the primary pipeline uses **pandas** because:

1. **No Java dependency** — PySpark historically required Java 8–17; PySpark 4.x now supports Java 23, but pandas remains simpler for current volumes
2. **Adequate for current data volumes** — Cricsheet's full dataset (~5M deliveries) fits in memory
3. **Simpler debugging** — No JVM startup, no Spark UI, no serialized closures
4. **Faster iteration** — Direct Python debugging, no `spark-submit`

The PySpark code in `data_pipeline/spark/` demonstrates the same algorithms and can be activated if data volumes grow or distributed processing is needed.

### Why SQLite for local development?

- **Zero setup** — No database server needed
- **Same SQL schema** — Identical table structure as PostgreSQL
- **Portable** — Single file, easy to reset and re-seed
- **Migration path** — `migrate_sqlite_to_pg.py` transfers data to PostgreSQL

---

## Project Structure

```
cricket-intelligence/
│
├── frontend/                          # React dashboard
│   ├── src/
│   │   ├── pages/                     # Page components
│   │   │   ├── Dashboard.tsx          # Overview — fetches from live API
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
│   ├── utils/database.py              # Database connection (auto-detects SQLite/PostgreSQL)
│   └── requirements.txt               # FastAPI, SQLAlchemy, psycopg2-binary, etc.
│
├── data_pipeline/                     # Data engineering pipeline
│   ├── pipeline/                      # ACTIVE pipeline (pandas-based)
│   │   ├── reader.py                  # Cricsheet JSON → flat DataFrame
│   │   ├── db_manager.py              # Entity resolution + DB writes (SQLite & PostgreSQL)
│   │   ├── analytics.py               # All statistical computations
│   │   └── run.py                     # Main pipeline orchestrator (CLI)
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
│   └── schema.sql                     # PostgreSQL schema (20 tables, 2 views, indexes)
│
├── migrate_sqlite_to_pg.py            # SQLite → PostgreSQL migration tool
│
├── data/                              # Gitignored
│   ├── raw/                           # Downloaded Cricsheet ZIPs + JSONs
│   │   ├── ipl/                       # IPL match JSONs
│   │   ├── t20i/                      # T20I match JSONs (after download)
│   │   ├── odi/                       # ODI match JSONs (after download)
│   │   └── test/                      # Test match JSONs (after download)
│   └── cricket_intelligence.db        # SQLite database with all data
│
├── docs/                              # Detailed documentation
│   ├── architecture.md
│   ├── data-model.md
│   ├── data-pipeline.md
│   ├── analytics.md
│   └── deployment.md
│
├── setup.py                           # SQLite database setup + schema
├── .env                               # Local environment variables (gitignored)
├── .env.example                       # Environment variable template
├── .gitignore                         # Ignores .env, data/, __pycache__, etc.
└── README.md                          # This file
```

---

## Quick Start

### Prerequisites

- **Python 3.10+** — for the pipeline and backend
- **Node.js 18+** — for the frontend
- **Java** — NOT required for the pandas pipeline (only for the PySpark reference implementation)

### 1. Clone and Install

```bash
git clone <repository-url>
cd cricket-intelligence

# Backend + pipeline dependencies
pip install -r backend/requirements.txt
pip install -r data_pipeline/requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Set Up Database (SQLite — zero setup)

```bash
# Download all IPL matches from Cricsheet and process them (~5 min)
python -m data_pipeline.pipeline.run --format ipl
```

This creates `data/cricket_intelligence.db` with real IPL data:
- 1,243 matches, 295,732 deliveries
- 807 players, 15 teams, 50 venues
- Precomputed batting/bowling stats, form scores, matchups

### 3. Start the Backend API

```bash
DATABASE_URL="sqlite:///data/cricket_intelligence.db" \
  uvicorn backend.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 4. Start the Frontend

```bash
cd frontend
VITE_API_URL="http://localhost:8000/api" npm run dev
```

Dashboard: http://localhost:5173

### 5. (Optional) Migrate to PostgreSQL

If you have a Supabase project set up:

```bash
# 1. Apply schema to Supabase (via SQL Editor)
# 2. Set DATABASE_URL in .env
DATABASE_URL="postgresql://postgres.<ref>:<password>@<host>:5432/postgres"

# 3. Run migration
python migrate_sqlite_to_pg.py

# 4. Start backend pointing to PostgreSQL (just use .env)
uvicorn backend.main:app --reload --port 8000
```

---

## Running the Data Pipeline

### Available formats

| Format | Cricsheet ID | Command | Typical Size |
|--------|-------------|---------|-------------|
| IPL | `ipl` | `--format ipl` | ~5 MB (1,243 matches) |
| T20 International | `t20i` | `--format t20i` | ~10 MB (~2,000 matches) |
| ODI | `odi` | `--format odi` | ~30 MB (~2,500 matches) |
| Test | `test` | `--format test` | ~50 MB (~1,200 matches) |
| All formats | `all` | `--format all` | ~95 MB |

### Common commands

```bash
# Process all IPL matches (1,243 matches, ~5 minutes)
python -m data_pipeline.pipeline.run --format ipl

# Process ALL IPL matches (1,243 matches, ~10 minutes)
python -m data_pipeline.pipeline.run --format ipl

# Process T20I international matches
python -m data_pipeline.pipeline.run --format t20i --sample 100

# Force re-download even if data exists
python -m data_pipeline.pipeline.run --format ipl --force --sample 50
```

### Batch processing (for large historical datasets)

```bash
# Process in batches of 250
python -m data_pipeline.batch --format odi --batch-size 250

# Resume from first failed/pending batch
python -m data_pipeline.batch --format odi --resume

# Process specific batch
python -m data_pipeline.batch --format ipl --batch-size 100 --batch-id 3

# Dry run (show batch boundaries without processing)
python -m data_pipeline.batch --format odi --batch-size 250 --dry-run

# Show batch status
python -m data_pipeline.batch --status --formats odi t20i test
```

### Pipeline stages

```
Stage 1: INGEST   → Download ZIP from Cricsheet, extract JSON files
Stage 2: READ     → Parse JSON into flat delivery-level DataFrame
Stage 3: VALIDATE → Check data quality, reject malformed records
Stage 4: RESOLVE  → Discover entities, map names to UUIDs, infer player roles
Stage 5: WRITE    → Write teams, players, venues, matches, innings, deliveries
Stage 6: COMPUTE  → Calculate player stats, team stats, venue stats, matchups, form scores
Stage 7: WRITE    → Write analytical results to database
Stage 8: REPORT   → Print summary statistics
```

### Idempotency

Running the pipeline twice does NOT create duplicate data:
- **Core entities** use `INSERT OR IGNORE` (SQLite) or `ON CONFLICT DO NOTHING` (PostgreSQL)
- **Matches** have a `external_id` UNIQUE constraint (Cricsheet match ID)
- **Analytical tables** are truncated and re-inserted each run (since they're fully recomputed)
- UUID-based entity resolution ensures the same player/team is never created twice

### Writing to PostgreSQL directly

The pipeline can write directly to PostgreSQL. Set `DATABASE_URL` in your `.env` file:

```bash
DATABASE_URL="postgresql://postgres.<ref>:<password>@<host>:5432/postgres" \
  python -m data_pipeline.pipeline.run --format ipl --sample 200
```

The `db_manager.py` automatically detects PostgreSQL and uses dialect-appropriate SQL (`ON CONFLICT DO NOTHING` instead of `INSERT OR IGNORE`).

---

## Database Migration (SQLite → PostgreSQL)

A migration tool is provided to transfer data from the local SQLite database to Supabase PostgreSQL.

### Usage

```bash
# Ensure .env has DATABASE_URL pointing to Supabase
python migrate_sqlite_to_pg.py
```

### What it does

1. Reads all 13 populated tables from SQLite
2. Truncates corresponding PostgreSQL tables (with `RESTART IDENTITY CASCADE`)
3. Writes data preserving all UUIDs
4. Verifies row counts match between source and destination
5. Runs 10 foreign-key integrity checks
6. Reports any orphaned rows or count mismatches

### Verified migration results

| Table | SQLite | PostgreSQL |
|-------|--------|------------|
| teams | 15 | 15 |
| players | 807 | 807 |
| venues | 50 | 50 |
| competitions | 1 | 1 |
| matches | 1,243 | 1,243 |
| innings | 2,514 | 2,514 |
| deliveries | 295,732 | 295,732 |
| player_batting_stats | 738 | 738 |
| player_bowling_stats | 577 | 577 |
| player_form | 571 | 571 |
| team_performance | 15 | 15 |
| venue_stats | 50 | 50 |
| batter_bowler_matchups | 9,502 | 9,502 |

All foreign-key integrity checks pass with zero orphaned rows.

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
- `sort_order` — asc, desc (default: desc)
- `limit` — Number of results (1–200, default: 50)
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

**Normalization:** Each component is min-max normalized to 0–100 within the same format. The best player gets 100, the worst gets 0 for each component.

**Minimum innings:** A player needs at least 3 innings for statistical significance. Players with fewer are excluded.

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
- Metrics: balls, runs, wickets, strike rate, average, dot balls, boundaries, sixes

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
- Team names are normalized to canonical forms where possible

### What's currently loaded

The **full IPL dataset** (1,243 matches) has been processed. The pipeline supports loading all formats:

```bash
# Full IPL
python -m data_pipeline.pipeline.run --format ipl

# T20I international
python -m data_pipeline.pipeline.run --format t20i

# ODI
python -m data_pipeline.pipeline.run --format odi

# Test
python -m data_pipeline.pipeline.run --format test
```

### What's NOT yet implemented

- Win probability machine learning model (planned)
- Live match data (requires external API provider)
- News aggregation (requires RSS feed integration)
- Player Impact metric (actual vs expected performance)
- Tournament-specific analytics filtering

---

## Environment Variables

### Backend (`.env`)

```bash
# Database connection
DATABASE_URL=sqlite:///data/cricket_intelligence.db              # Local dev (SQLite)
DATABASE_URL=postgresql://postgres.<ref>:<pass>@<host>:5432/postgres  # Production (Supabase)

# CORS (comma-separated origins)
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:3000,http://localhost:8080
```

### Frontend (`.env` or inline)

```bash
# API base URL
VITE_API_URL=http://localhost:8000/api
```

### Note on Supabase connection strings

Supabase passwords may contain special characters (like `[` and `]`) that break URL parsing. If you encounter connection errors:

1. URL-encode special characters: `[` → `%5B`, `]` → `%5D`
2. Or use the **Session pooler** connection string (port `5432`) instead of the direct connection

---

## Deployment

### Target architecture

| Component | Platform | Cost | Notes |
|-----------|----------|------|-------|
| Frontend | Vercel | Free | Automatic deployments from Git |
| Database | Supabase | Free | PostgreSQL hosting, 500 MB free tier |
| API | Vercel Serverless / Railway | Free tier | FastAPI compatible |
| Pipeline | Local / GitHub Actions | Free | Batch processing, not real-time |

### Frontend deployment (Vercel)

1. Push code to GitHub
2. Connect repository to Vercel
3. Set environment variable: `VITE_API_URL` → your API endpoint
4. Deploy

### Database setup (Supabase)

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Go to SQL Editor
3. Run the contents of `database/schema.sql`
4. Copy the connection string from Settings → Database
5. Set `DATABASE_URL` in `.env`

### Migrating data to Supabase

```bash
# 1. Process data locally (SQLite)
python -m data_pipeline.pipeline.run --format ipl --sample 200

# 2. Migrate to PostgreSQL
python migrate_sqlite_to_pg.py

# 3. Verify
DATABASE_URL="postgresql://..." uvicorn backend.main:app --port 8000
curl http://localhost:8000/api/players?limit=5
```

---

## Development Notes

### Running tests

```bash
# Frontend typecheck
cd frontend && npx tsc --noEmit

# Frontend build
cd frontend && npx vite build

# Backend API smoke test (with SQLite)
DATABASE_URL="sqlite:///data/cricket_intelligence.db" python test_api_smoke.py
```

### Adding a new data source

1. Create a new ingestor in `data_pipeline/ingestion/`
2. Implement the same interface as `CricsheetIngestor` (download, extract, list_matches)
3. The pipeline's `reader.py` expects one JSON file per match with `info` and `innings` fields
4. Entity resolution handles name normalization automatically

### Database schema

The full PostgreSQL schema is in `database/schema.sql`. Key design decisions:
- **UUID primary keys** for all entities (stable internal IDs, not display names)
- **Foreign keys** enforced at the database level
- **Analytical tables** are denormalized for read performance
- **Indexes** on frequently queried columns (player_id, team_id, format, date)
- **Views** (`v_player_summary`, `v_team_summary`) for quick cross-table queries
- **Triggers** auto-update `updated_at` timestamps

### SQLite ↔ PostgreSQL parity

The pipeline uses dialect-aware SQL:
- **SQLite:** `INSERT OR IGNORE` for idempotent inserts
- **PostgreSQL:** `INSERT ... ON CONFLICT DO NOTHING`
- **PostgreSQL only:** `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` for analytical tables

The `db_manager.py` auto-detects the dialect from the `DATABASE_URL`.

### Known data artifacts

- `data/raw/ipl/` — 1,243 extracted IPL match JSON files (~5 MB)
- `data/cricket_intelligence.db` — SQLite database with all 1,243 IPL matches processed (local dev copy)
- Supabase PostgreSQL — Production database with the same 1,243 matches (migrated via `migrate_sqlite_to_pg.py`)
- `.env` — Contains DATABASE_URL for Supabase PostgreSQL (gitignored)

---

## Phase Status

### Phase 0: Stabilize IPL Foundation ✅

Verified PostgreSQL/Supabase as production database, wired all frontend pages to live API, added 29 automated tests.

### Phase 1: Universal Cricket Data Model ✅

Format-agnostic data model for T20/T20I/ODI/Test. Added `format_config`, `seasons`, match result types, Test innings support.

### Phase 1.1: Model Hardening ✅

Added `player_team_affiliations` table, competition edition/season separation, format-aware Spark UDF, 41 new tests.

### Phase 2: International T20I ✅

Men's T20I data ingestion pipeline validated with representative fixtures. Cross-format player identity working.

### Phase 3: Men's ODI ✅

Men's ODI cricket data with World Cup, Champions Trophy, Asia Cup, and bilateral fixtures. 8 matches / 793 deliveries across 11 teams. 43 new tests. Full IPL regression verified.

### Phase 3.1: Identity Hardening ✅

Merged "V Kohli" → "Virat Kohli" (15,005 FK updates, 0 orphans). Player name mapping system. Data quality audit. 176/176 tests passing.

### Phase 4: Test Cricket ✅

Test cricket support validated with 5 fixtures (19 innings, 5,430 deliveries). 4-innings matches, draws, declarations, all-outs, follow-ons all working. Cross-format identity: Virat Kohli has T20 + T20I + ODI + Test stats. 215/215 tests passing.

### Phase 5.1: Batch Processing Infrastructure ✅

Production-grade batch ingestion infrastructure. PostgreSQL-backed batch manifest with checkpoint/resume. Deterministic batch splitting. Format-wide analytics. CLI with dry-run support.

### Phase 5.2: Analytics Write Fix & Pipeline Hardening ✅

Fixed critical analytics data loss bug where `to_sql()` silently failed on Supabase due to cross-connection transaction isolation. Rewrote `write_analytics_table` to use psycopg2 with small-batch DELETE/INSERT compatible with Supabase's statement timeout.

### Phase 5.2.1: Data Integrity & Player Identity Hardening ✅

Hardened player identity pipeline with multi-step resolution (direct lookup + name mapping fallback). Created reusable data-quality audit (`python -m data_pipeline.audit`) with 78 integrity checks. Verified all analytics have zero NULL player IDs and zero orphaned records. Measured Supabase timeout behavior (INSERT ~1000 rows/s at batch=1000, DELETE ~8 rows/s).

### Phase 5.3A: Historical Dataset Preparation ✅

Prepared the Cricsheet historical T20I dataset for ingestion. Created `prepare.py` to extract, filter (men's only), and remap T20I format codes. Validated 3,533 men's T20I match files.

### Phase 5.3B: T20I Historical Pilot + Controlled Batch Ingestion ✅

Successfully ingested 3,533 historical T20I matches (837,087 deliveries) through controlled batches of 250 matches. Resolved: innings_number constraint (super overs), analytics query timeout (chunked loading), 38 duplicate player identities, 236 missing affiliations. Full audit: 78 checks, 0 failures. 278/278 tests passing (+ 13 skipped). IPL regression preserved (1,243 matches / 295,732 deliveries / Kohli 9,346 runs).

### Not yet implemented (Phase 5.4+)

- Historical ODI dataset ingestion
- Historical Test dataset ingestion
- Full IPL historical expansion
- Win probability model
- Player impact metric
- Advanced frontend filters (format/competition/season selectors)

See `docs/phase-5.1.md`, `docs/phase-5.2.md`, `docs/phase-5.3a.md`, and `docs/phase-5.3b.md` for details.

---

## License

MIT
