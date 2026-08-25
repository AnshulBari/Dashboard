# Architecture

## Overview

The Cricket Intelligence Platform follows a layered architecture with clear separation between batch processing and real-time serving:

```
DATA SOURCES (Cricsheet)
        ↓
DATA INGESTION (Python downloaders)
        ↓
RAW DATA (JSON match files)
        ↓
PIPELINE (pandas ETL)
  - Read & Flatten
  - Validate
  - Resolve Entities (names → UUIDs)
  - Write Core Data
  - Compute Analytics
  - Write Analytics
        ↓
DATABASE (SQLite dev / PostgreSQL prod)
        ↓
REST API (FastAPI)
        ↓
REACT DASHBOARD (Vite + TypeScript)
```

## Design Principles

1. **Separation of concerns**: Ingestion, processing, analytics, API, and UI are separate modules
2. **Precomputed analytics**: All heavy computation happens offline in the pipeline; the API serves precomputed results
3. **Canonical entity model**: Display names are never used as keys; stable UUIDs throughout
4. **Explainable metrics**: Every analytical metric has documented methodology and transparent weights
5. **Data quality first**: Validation runs before processing; rejected records are tracked and reported
6. **Idempotent pipeline**: Running twice does not create duplicate data

## Why This Architecture?

### Why pandas for ETL?
- **No Java dependency** — PySpark 3.5 requires Java 8–17, which is not always available
- **Adequate for current volumes** — Cricsheet's full dataset (~5M deliveries) fits in memory
- **Simpler debugging** — Direct Python debugging, no JVM startup overhead
- **Faster iteration** — No spark-submit, no serialized closures

PySpark code is preserved in `data_pipeline/spark/` as a reference implementation for when data volumes grow beyond pandas capacity.

### Why SQLite for local development?
- **Zero setup** — No database server needed
- **Same SQL schema** — Identical table structure as PostgreSQL
- **Portable** — Single file, easy to reset and re-seed
- **Production parity** — SQL queries work identically in PostgreSQL

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
2. Extract to individual JSON match files
3. reader.py parses JSON → flat DataFrame (one row per delivery)
4. Validate data quality (reject malformed records)
5. Resolve entities (discover teams, players, venues from data)
6. Write core data (matches, innings, deliveries with UUIDs)
7. Compute analytics (batting stats, bowling stats, form scores, matchups)
8. Write analytics to database
9. Report summary statistics
```

### API Serving (Real-time — on request)
```
1. Frontend requests data from API
2. FastAPI routes query precomputed analytics from database
3. Return JSON response with analytical data
4. No computation happens at request time
```

## Module Responsibilities

| Module | File | Responsibility |
|--------|------|---------------|
| **Ingestion** | `ingestion/cricsheet.py` | Download Cricsheet ZIP, extract JSON, list matches |
| **Reader** | `pipeline/reader.py` | Parse JSON → flat DataFrame, extract match context |
| **DB Manager** | `pipeline/db_manager.py` | Entity resolution, core data writes, analytics writes |
| **Analytics** | `pipeline/analytics.py` | Compute all statistical metrics |
| **Pipeline Runner** | `pipeline/run.py` | Orchestrate all stages, handle CLI arguments |
| **API Routes** | `routes/*.py` | HTTP endpoints, query database, return JSON |
| **Database Utils** | `utils/database.py` | Connection management, session lifecycle |
| **Frontend Pages** | `pages/*.tsx` | UI components, fetch from API, render charts |

## Entity Resolution

This is the most critical pipeline stage. Different data sources may refer to the same entity differently:

```
"India", "IND", "India Men"  →  canonical team: "India" (UUID: abc-123)
"V Kohli", "Virat Kohli"      →  canonical player: "V Kohli" (UUID: def-456)
"MCG", "Melbourne Cricket Ground"  →  canonical venue: "MCG" (UUID: ghi-789)
```

The resolution uses:
1. **Team normalization** — Hardcoded mapping of known variants
2. **Player discovery** — First occurrence creates the canonical record
3. **Role inference** — Players who bowl 30+ balls are classified as bowlers/allrounders
4. **Venue creation** — First occurrence creates the venue record

## Database Schema

The schema supports the full cricket data model:

**Core entities:**
- `teams` — Canonical team identity with UUID
- `players` — Canonical player identity with role, batting/bowling style
- `venues` — Cricket ground with location
- `competitions` — Tournament/series metadata
- `matches` — Individual match with teams, result, venue, toss
- `innings` — Innings within a match (1-4)
- `deliveries` — Ball-by-ball data (the foundation for all analytics)

**Analytical tables (precomputed):**
- `player_batting_stats` — Career/recent batting statistics by format
- `player_bowling_stats` — Career/recent bowling statistics by format
- `player_form` — Weighted composite form score (0-100)
- `team_performance` — Win rates, strength scores by format
- `venue_stats` — Average scores, phase-wise stats by format
- `batter_bowler_matchups` — Head-to-head statistics

**Identity mapping:**
- `player_name_mappings` — Maps external names to canonical player IDs
- `team_name_mappings` — Maps external team names to canonical team IDs

See `database/schema.sql` for the complete schema with indexes and constraints.

## Scaling Considerations

### Current (Local Development)
- SQLite database (single file)
- pandas pipeline (in-memory processing)
- Single FastAPI process
- Vite dev server

### Future (Production)
- Supabase PostgreSQL (managed, free tier)
- Optional PySpark for larger datasets
- FastAPI behind a load balancer
- Vercel edge functions for frontend
- GitHub Actions for scheduled pipeline runs

## Security

- Environment variables for all secrets
- CORS configured for specific origins
- Input validation on all API endpoints via Pydantic
- No secrets in Git
- Public API keys only in VITE_ prefixed env vars
