# Architecture

## Overview

The Cricket Intelligence Platform follows a layered architecture:

```
DATA SOURCES (Cricsheet, ICC, RSS)
        ↓
DATA INGESTION (Python downloaders)
        ↓
RAW DATA (JSON files)
        ↓
PySpark ETL PIPELINE
  - Read & Validate
  - Normalize (canonical entities)
  - Transform (computed columns)
  - Aggregate (statistics)
  - Feature Engineering (form scores)
        ↓
ANALYTICAL DATASETS (Parquet → PostgreSQL)
        ↓
REST API (FastAPI)
        ↓
REACT DASHBOARD (Vite + TypeScript)
```

## Design Principles

1. **Separation of concerns**: Ingestion, processing, analytics, API, and UI are separate modules
2. **Precomputed analytics**: All heavy computation happens offline; the API serves precomputed results
3. **Canonical entity model**: Display names are never used as keys; stable internal IDs throughout
4. **Explainable metrics**: Every analytical metric has documented methodology and transparent weights
5. **Data quality first**: Validation runs before processing; rejected records are tracked and reported

## Why This Architecture?

### Why Spark for ETL?
- Cricsheet contains 200K+ deliveries per format
- Window functions for rolling averages require ordered processing
- Parallel processing enables faster batch jobs
- DataFrame API provides clean, maintainable ETL code
- Same code scales from local development to cluster processing

### Why PostgreSQL for Storage?
- JSON support for flexible analytical schemas
- Materialized views for precomputed queries
- Excellent ecosystem and tooling
- Supabase provides free PostgreSQL hosting

### Why FastAPI for Backend?
- High performance with async support
- Auto-generated OpenAPI docs
- Pydantic integration for validation
- Type hints throughout

### Why React + Vite for Frontend?
- Fast development and HMR
- TypeScript for type safety
- Rich ecosystem (Recharts, TanStack Query)
- Vercel deployment is straightforward

## Data Flow

### Historical Pipeline (Batch)
```
1. CricsheetIngestor downloads ZIP files
2. Extract to JSON match files
3. Spark reads and flattens delivery data
4. Validates data quality
5. Normalizes to canonical entities
6. Adds computed columns (cumulative stats, phases)
7. Aggregates into player/team/venue statistics
8. Computes advanced analytics (form scores, matchups)
9. Writes to PostgreSQL / Parquet
```

### Live Data (Real-time)
```
1. External cricket API provides live scores
2. Live ingestion module normalizes data
3. Updated to PostgreSQL / in-memory cache
4. Frontend polls for updates (short cache TTL)
5. Historical intelligence continues independently
```

## Scaling Considerations

### Current (Local Development)
- SQLite or local PostgreSQL
- PySpark running in local mode
- Single FastAPI process
- Vite dev server

### Future (Production)
- Supabase PostgreSQL (managed)
- Spark cluster for large-scale processing
- FastAPI behind a load balancer
- Vercel edge functions for frontend

## Security

- Environment variables for all secrets
- CORS configured for specific origins
- Input validation on all API endpoints
- No secrets in Git
- Public API keys only in VITE_ prefixed env vars
