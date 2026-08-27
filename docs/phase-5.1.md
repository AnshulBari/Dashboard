# Phase 5.1: Apache Spark Historical Batch Ingestion Infrastructure

## Overview

Phase 5.1 introduces a production-grade batch processing layer around the existing data pipeline. This infrastructure enables controlled, resumable ingestion of large historical cricket datasets.

## Architecture

```
Cricsheet JSON files (data/raw/{format}/)
  |
  v
Batch Discovery (discovery.py)
  |-- Discover files in format directory
  |-- Split into deterministic batches
  |
  v
Batch Runner (runner.py)
  |-- Read JSON files into DataFrame
  |-- Validate data quality
  |-- Normalize names (venue, team, format)
  |-- Resolve entities (teams, players, venues)
  |-- Write matches, innings, deliveries, affiliations
  |-- Compute format-wide analytics
  |-- Write analytics (format-scoped)
  |
  v
Batch Manifest (manifest.py)
  |-- Track batch status (PENDING/RUNNING/COMPLETED/FAILED)
  |-- Record timing and statistics
  |-- Enable checkpoint/resume
  |
  v
PostgreSQL (batch_manifest table)
```

## Key Design Decisions

### 1. Analytics Are Format-Wide, Not Per-Batch

When processing a batch, analytics are computed for ALL deliveries of that format in the database, not just the batch's deliveries. This ensures analytics remain correct after processing partial datasets.

Example: Processing IPL batch 0 (100 matches) recomputes analytics from ALL 1,243 IPL matches in the database.

### 2. Deterministic Batch Splitting

Files are sorted alphabetically and split into contiguous slices. The same files always produce the same batch membership, enabling safe checkpoint/resume.

### 3. Format-Scope Analytics Writes

Analytics are written with `DELETE WHERE format = :fmt`, preserving analytics for other formats. Processing T20I never destroys IPL analytics.

### 4. Idempotent Delivery Writes

The existing idempotent delivery writer skips deliveries that already exist (matched by innings_id + over + ball), preventing duplicates on re-run.

## Files

| File | Purpose |
|------|---------|
| `data_pipeline/batch/__init__.py` | Package init |
| `data_pipeline/batch/__main__.py` | CLI entry point |
| `data_pipeline/batch/discovery.py` | File discovery and batch splitting |
| `data_pipeline/batch/manifest.py` | PostgreSQL-backed batch manifest |
| `data_pipeline/batch/runner.py` | Batch processing runner |
| `data_pipeline/batch/cli.py` | CLI interface |
| `tests/test_phase5_1.py` | 21 automated tests |

## CLI Commands

```bash
# Process all files in batches of 250
python -m data_pipeline.batch --format odi --batch-size 250

# Process specific batch
python -m data_pipeline.batch --format ipl --batch-size 100 --batch-id 0

# Resume from first pending/failed batch
python -m data_pipeline.batch --format odi --resume

# Resume specific batch
python -m data_pipeline.batch --format odi --batch-id 3 --resume

# Dry run (show batch boundaries without processing)
python -m data_pipeline.batch --format odi --batch-size 250 --dry-run

# Show batch status
python -m data_pipeline.batch --status --formats odi t20i test
```

## Batch Manifest Table

```sql
CREATE TABLE batch_manifest (
    id UUID PRIMARY KEY,
    dataset VARCHAR(20) NOT NULL,      -- 't20i', 'odi', 'test', 'ipl'
    batch_id INTEGER NOT NULL,
    batch_size INTEGER NOT NULL,
    file_count INTEGER DEFAULT 0,
    match_count INTEGER DEFAULT 0,
    delivery_count INTEGER DEFAULT 0,
    innings_count INTEGER DEFAULT 0,
    player_count INTEGER DEFAULT 0,
    team_count INTEGER DEFAULT 0,
    venue_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PENDING',
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    processing_duration_seconds DECIMAL(10,2),
    UNIQUE(dataset, batch_id)
);
```

## Checkpoint/Resume Behavior

- `PENDING` batches will be processed on `--resume`
- `FAILED` batches will be retried on `--resume`
- `COMPLETED` batches are skipped
- `RUNNING` batches indicate an interrupted process

## Performance

Processing times on existing validation dataset:

| Format | Files | Matches | Deliveries | Time |
|--------|-------|---------|------------|------|
| T20I | 5 | 5 | 518 | ~26s |
| ODI | 8 | 8 | 793 | ~25s |
| Test | 5 | 5 | 1,340 | ~26s |
| IPL (batch 0) | 100 | 100 | 23,606 | ~217s |

Note: Most time is spent on analytics recomputation for the full format, not on ingestion.

## Idempotency

Running the same batch twice produces no duplicates:
- Matches: skipped (external_id already exists)
- Innings: skipped (match_id + innings_number already exists)
- Deliveries: skipped (innings_id + over + ball already exists)
- Affiliations: skipped (player + team + format already exists)
- Analytics: deleted for format, then re-inserted

## Future Scaling

For large historical backfills (Phase 5.2+), consider:
1. Processing all batches in sequence with `--resume`
2. Analytics optimization: only recompute changed format's analytics once at the end
3. Parallel batch processing for independent formats
