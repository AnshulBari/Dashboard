# Architecture

## Overview

The Cricket Intelligence Platform follows a layered architecture with clear separation between batch processing (pipeline) and real-time serving (API + frontend):

```
DATA SOURCES (Cricsheet)
        ↓
DATA INGESTION (Python downloaders)
        ↓
RAW DATA (JSON match files in data/raw/)
        ↓
PIPELINE (pandas ETL)
  - Read & Flatten
  - Validate
  - Resolve Entities (names → UUIDs)
  - Write Core Data
  - Compute Analytics
  - Write Analytics
        ↓
DATABASE
  - SQLite (local dev: data/cricket_intelligence.db)
  - PostgreSQL (production: Supabase)
        ↓
REST API (FastAPI + SQLAlchemy)
        ↓
REACT DASHBOARD (Vite + TypeScript + Tailwind)
```

## Design Principles

1. **Separation of concerns** — Ingestion, processing, analytics, API, and UI are separate modules
2. **Precomputed analytics** — All heavy computation happens offline in the pipeline; the API serves precomputed results
3. **Canonical entity model** — Display names are never used as keys; stable UUIDs throughout
4. **Explainable metrics** — Every analytical metric has documented methodology and transparent weights
5. **Data quality first** — Validation runs before processing; rejected records are tracked and reported
6. **Idempotent pipeline** — Running twice does not create duplicate data
7. **Database portability** — Same schema works on SQLite (dev) and PostgreSQL (prod)

## Why This Architecture?

### Why pandas for ETL?

- **No Java dependency** — Simpler setup than PySpark
- **Adequate for current volumes** — Cricsheet's full dataset (~5M deliveries) fits in memory
- **Simpler debugging** — Direct Python debugging, no JVM startup overhead
- **Faster iteration** — No spark-submit, no serialized closures

PySpark code is preserved in `data_pipeline/spark/` as a reference implementation for when data volumes grow beyond pandas capacity.

### Why SQLite for local development?

- **Zero setup** — No database server needed
- **Same SQL schema** — Identical table structure as PostgreSQL
- **Portable** — Single file, easy to reset and re-seed
- **Production parity** — SQL queries work identically in PostgreSQL
- **Migration path** — `migrate_sqlite_to_pg.py` transfers data to Supabase

### Why Supabase PostgreSQL for production?

- **Free tier** — 500 MB storage, suitable for the analytical dataset
- **Managed service** — No database administration required
- **Connection pooling** — Built-in session/direct poolers
- **SQL Editor** — Apply schema directly from the dashboard
- **Dashboard** — Visual data browsing and management

### Why FastAPI for backend?

- **High performance** — Async support, automatic OpenAPI docs
- **Pydantic integration** — Request/response validation
- **Type hints** — IDE-friendly, self-documenting
- **Lightweight** — Serves precomputed data, no heavy computation

### Why React + Vite for frontend?

- **Fast development** — Hot module replacement, instant feedback
- **TypeScript** — Type-safe component development
- **Tailwind CSS** — Consistent design system without custom CSS
- **Vercel deployment** — One-click deployment from Git

## Data Flow

### Historical Pipeline (Batch — runs offline)

```
1. CricsheetIngestor downloads ZIP from cricsheet.org
2. Extract to individual JSON match files in data/raw/{format}/
3. reader.py parses JSON → flat DataFrame (one row per delivery)
4. Validate data quality (reject malformed records)
5. Resolve entities (discover teams, players, venues from data → UUIDs)
6. Write core data (matches, innings, deliveries with FK-resolved UUIDs)
7. Compute analytics (batting stats, bowling stats, form scores, matchups)
8. Write analytics to database (truncate-then-insert for analytical tables)
9. Report summary statistics
```

### API Serving (Real-time — on request)

```
1. Frontend requests data from API
2. FastAPI routes query precomputed analytics from database
3. Return JSON response with analytical data
4. No computation happens at request time
```

### Database Migration (one-time / periodic)

```
1. Process Cricsheet data → SQLite (local pipeline)
2. migrate_sqlite_to_pg.py reads all tables from SQLite
3. Truncates PostgreSQL tables, writes data preserving UUIDs
4. Verifies row counts and foreign-key integrity
```

## Module Responsibilities

| Module | File | Responsibility |
|--------|------|---------------|
| **Ingestion** | `ingestion/cricsheet.py` | Download Cricsheet ZIP, extract JSON, list matches |
| **Reader** | `pipeline/reader.py` | Parse JSON → flat DataFrame, extract match context |
| **DB Manager** | `pipeline/db_manager.py` | Entity resolution, core data writes, analytics writes |
| **Analytics** | `pipeline/analytics.py` | Compute all statistical metrics |
| **Pipeline Runner** | `pipeline/run.py` | Orchestrate all stages, handle CLI arguments |
| **Migration** | `migrate_sqlite_to_pg.py` | Transfer data from SQLite to PostgreSQL |
| **API Routes** | `routes/*.py` | HTTP endpoints, query database, return JSON |
| **Database Utils** | `utils/database.py` | Connection management, session lifecycle |
| **Frontend Pages** | `pages/*.tsx` | UI components, fetch from API, render charts |

## Entity Resolution

This is the most critical pipeline stage. Different data sources may refer to the same entity differently:

```
"India", "IND", "India Men"  →  canonical team: "India" (UUID)
"V Kohli", "Virat Kohli"      →  canonical player: "V Kohli" (UUID)
"MCG", "Melbourne Cricket Ground"  →  canonical venue: "MCG" (UUID)
```

The resolution process:
1. **Team normalization** — Hardcoded mapping of known variants (e.g., "Delhi Daredevils" → "Delhi Capitals")
2. **Player discovery** — First occurrence creates the canonical record; subsequent occurrences reuse the same UUID
3. **Role inference** — Players who bowl 30+ balls are classified as bowlers/allrounder; others default to batsman
4. **Venue creation** — First occurrence creates the venue record
5. **Competition extraction** — Event names from match metadata (e.g., "Indian Premier League")

## Database Schema

### Core tables (populated by pipeline)

| Table | Rows (current) | Description |
|-------|---------------|-------------|
| `teams` | 15 | Canonical team identity with UUID |
| `players` | 807 | Canonical player identity with role |
| `venues` | 50 | Cricket ground with location |
| `competitions` | 1 | Tournament/series metadata |
| `matches` | 1,243 | Individual match records |
| `innings` | 2,514 | Innings within matches |
| `deliveries` | 295,732 | Ball-by-ball data |

### Analytical tables (precomputed)

| Table | Rows (current) | Description |
|-------|---------------|-------------|
| `player_batting_stats` | 738 | Career batting stats by player/format |
| `player_bowling_stats` | 577 | Career bowling stats by player/format |
| `player_form` | 571 | Weighted composite form score (0–100) |
| `team_performance` | 15 | Win rates, strength scores by format |
| `venue_stats` | 50 | Average scores, phase-wise stats |
| `batter_bowler_matchups` | 9,502 | Head-to-head statistics |

### Identity mapping tables

| Table | Description |
|-------|-------------|
| `player_name_mappings` | Maps external names → canonical player IDs |
| `team_name_mappings` | Maps external team names → canonical team IDs |

### Future tables (schema defined, not yet populated)

| Table | Description |
|-------|-------------|
| `player_impact` | Actual vs expected performance |
| `batter_type_matchups` | Aggregate matchups by bowling type |
| `rankings` | Platform-computed player rankings |
| `news_articles` | Cricket news from RSS feeds |
| `live_matches` | Live match data from external APIs |

### Views

| View | Description |
|------|-------------|
| `v_player_summary` | Cross-table player summary (batting + bowling + form) |
| `v_team_summary` | Cross-table team summary (performance + strength) |

See `database/schema.sql` for the complete schema with indexes, constraints, and triggers.

## Database Portability

The pipeline auto-detects the database dialect from `DATABASE_URL`:

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Insert (idempotent) | `INSERT OR IGNORE` | `INSERT ... ON CONFLICT DO NOTHING` |
| Truncate analytics | `DELETE FROM table` | `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` |
| Schema creation | `_create_sqlite_schema()` from setup.py | `database/schema.sql` |
| UUID storage | TEXT | Native UUID |
| Connection | File path | Network (Supabase pooler) |

## Scaling Considerations

### Current (Local Development)
- SQLite database (single 16 MB file)
- pandas pipeline (in-memory processing)
- Single FastAPI process
- Vite dev server

### Production (Supabase + Vercel)
- Supabase PostgreSQL (managed, free tier)
- FastAPI on Vercel Serverless / Railway
- Vercel-hosted React frontend
- GitHub Actions for scheduled pipeline runs

### Future (if data grows)
- Optional PySpark for distributed processing (reference code exists in `data_pipeline/spark/`)
- Redis caching for frequently accessed endpoints
- Background task queue for pipeline scheduling

## Security

- Environment variables for all secrets (`.env` gitignored)
- CORS configured for specific origins
- Input validation on all API endpoints via Pydantic
- No secrets in Git
- Public API keys only in `VITE_` prefixed env vars
- Supabase connection uses SSL (enforced by Supabase)
