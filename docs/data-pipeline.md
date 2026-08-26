# Data Pipeline

## Overview

The data pipeline is the core data engineering component of the Cricket Intelligence Platform. It transforms raw Cricsheet match data into precomputed analytical datasets stored in SQLite (local development) or PostgreSQL (production).

## Pipeline Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   INGEST    │───▶│    READ     │───▶│  VALIDATE   │───▶│   RESOLVE   │
│  Download   │    │  Parse JSON │    │  Quality    │    │  Entities   │
│  Extract    │    │  Flatten    │    │  Checks     │    │  UUIDs      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                │
                                                               ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   REPORT    │◀───│   WRITE     │◀───│  COMPUTE    │◀───│   WRITE     │
│  Summary    │    │  Analytics  │    │  Analytics  │    │  Core Data  │
│  Statistics │    │  to DB      │    │  Stats      │    │  to DB      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Stage Details

### Stage 1: INGEST

**Module:** `ingestion/cricsheet.py`

Downloads compressed ZIP files from Cricsheet and extracts individual JSON match files.

```python
CRICSHEET_MATCHES = {
    "t20i": "https://cricsheet.org/downloads/t20i_json.zip",
    "odi": "https://cricsheet.org/downloads/odi_json.zip",
    "test": "https://cricsheet.org/downloads/test_json.zip",
    "ipl": "https://cricsheet.org/downloads/ipl_json.zip",
}
```

**Features:**
- MD5 checksum verification (avoids re-downloading unchanged files)
- Progress logging
- Automatic extraction to `data/raw/{format}/`

**Output:** Directory of JSON files (one per match)

### Stage 2: READ

**Module:** `pipeline/reader.py`

Reads each JSON file and flattens the nested structure into a DataFrame with **one row per delivery**.

**Input:** `data/raw/{format}/*.json` (one file per match)

**Output:** DataFrame with columns:
- Match context: `match_id`, `match_date`, `format`, `venue`, `team_a`, `team_b`
- Delivery context: `batting_team`, `bowling_team`, `innings_number`, `over_number`, `ball_in_over`
- Delivery details: `batter`, `bowler`, `non_striker`, `runs_batter`, `runs_total`
- Wicket info: `is_wicket`, `wicket_type`, `dismissed_player`
- Event info: `event_name`, `competition`

### Stage 3: VALIDATE

**Module:** `pipeline/run.py` (validate method)

Checks data quality and filters out invalid records.

**Validation rules:**
- Batter must not be null
- Bowler must not be null
- Runs cannot be negative
- Over number must be 0–100
- Ball in over must be 1–9

**Output:** Validated DataFrame + rejection statistics

### Stage 4: RESOLVE

**Module:** `pipeline/db_manager.py` (discover_entities method)

Discovers all unique entities from the raw data and creates/resolves their UUIDs.

**Entity resolution process:**

1. **Teams** — Extract unique team names, normalize to canonical names using hardcoded mapping
2. **Venues** — Extract unique venue names with city information
3. **Players** — Extract unique player names from batter/bowler/non-striker/dismissed columns
4. **Role Inference** — Players who bowl 30+ balls are classified as bowlers/allrounders; others default to batsman
5. **Competitions** — Extract event names from match metadata

**Output:** Entity ID caches (`name → UUID` mappings)

### Stage 5: WRITE (Core Data)

**Module:** `pipeline/db_manager.py` (write_matches, write_innings, write_deliveries_batch methods)

Writes core entity data to the database in dependency order:

1. **Matches** — One row per match with FKs to teams, venue, competition
2. **Innings** — One row per innings with FKs to match and teams
3. **Deliveries** — One row per delivery with FKs to innings, match, and players

**Key design decisions:**
- Uses dialect-appropriate idempotent inserts:
  - SQLite: `INSERT OR IGNORE`
  - PostgreSQL: `INSERT ... ON CONFLICT DO NOTHING`
- Foreign keys reference UUIDs, not display names
- Deliveries are written in batches of 5,000 for efficiency
- Empty string player lookups are treated as NULL (to satisfy FK constraints)

### Stage 6: COMPUTE

**Module:** `pipeline/analytics.py`

Computes all analytical statistics from delivery-level data. See [Analytics Methodology](analytics.md) for formulas.

**Computed tables:**
- `player_batting_stats` — Career and phase-specific batting statistics
- `player_bowling_stats` — Career and phase-specific bowling statistics
- `player_form` — Weighted composite form score (0–100)
- `team_performance` — Win rates, strength scores, phase performance
- `venue_stats` — Average scores, phase-wise statistics, pace/spin distribution
- `batter_bowler_matchups` — Head-to-head batter vs bowler statistics

### Stage 7: WRITE (Analytics)

**Module:** `pipeline/db_manager.py` (write_analytics_table method)

Writes computed analytics to the database:
- **SQLite:** `DELETE FROM table` (truncate)
- **PostgreSQL:** `TRUNCATE TABLE ... RESTART IDENTITY CASCADE`
- Maps player/team/venue names to UUIDs for foreign keys
- Inserts new analytics rows

### Stage 8: REPORT

**Module:** `pipeline/run.py`

Prints summary statistics:
- Matches processed
- Deliveries processed
- Entities discovered
- Processing time
- Database table counts

## Running the Pipeline

### Basic Usage

```bash
# Process 200 IPL matches (quick test)
python -m data_pipeline.pipeline.run --format ipl --sample 200

# Process ALL IPL matches
python -m data_pipeline.pipeline.run --format ipl

# Process T20I international matches
python -m data_pipeline.pipeline.run --format t20i

# Force re-download
python -m data_pipeline.pipeline.run --format ipl --force
```

### Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--format` | `ipl` | Cricket format: ipl, t20i, odi, test, all |
| `--sample` | None | Limit number of matches (for testing) |
| `--force` | False | Force re-download even if data exists |
| `--database-url` | None | Override DATABASE_URL environment variable |

### Output

After running, the pipeline creates:
- `data/raw/{format}/` — Extracted JSON match files
- `data/cricket_intelligence.db` (SQLite) or populates PostgreSQL tables

## Database Support

The pipeline supports both SQLite and PostgreSQL, auto-detected from `DATABASE_URL`:

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Insert (idempotent) | `INSERT OR IGNORE` | `INSERT ... ON CONFLICT DO NOTHING` |
| Truncate analytics | `DELETE FROM table` | `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` |
| Schema creation | `_create_sqlite_schema()` (setup.py) | `database/schema.sql` |
| UUID storage | TEXT column | Native UUID type |
| Connection | File path | Network URL (Supabase pooler) |

### Writing to PostgreSQL directly

```bash
DATABASE_URL="postgresql://postgres.<ref>:<password>@<host>:5432/postgres" \
  python -m data_pipeline.pipeline.run --format ipl --sample 200
```

### Migrating from SQLite to PostgreSQL

A separate migration tool transfers data from an existing SQLite database to PostgreSQL:

```bash
python migrate_sqlite_to_pg.py
```

See the [Deployment Guide](deployment.md) for details.

## Data Quality

The pipeline includes data quality checks at multiple stages:

1. **Ingestion** — Checksum verification, file format validation
2. **Read** — JSON parsing error handling (malformed files are skipped)
3. **Validate** — Null checks, range checks, consistency checks
4. **Write** — Foreign key constraint enforcement (invalid FKs → NULL)
5. **Report** — Rejection statistics, duplicate detection

### Validation rules

| Check | Rule | Action on failure |
|-------|------|-------------------|
| Null batter | `batter IS NOT NULL` | Reject delivery |
| Null bowler | `bowler IS NOT NULL` | Reject delivery |
| Negative runs | `runs_batter >= 0` | Reject delivery |
| Over range | `over_number BETWEEN 0 AND 100` | Reject delivery |
| Ball range | `ball_in_over BETWEEN 1 AND 9` | Reject delivery |
| Unknown player | Player name not in resolution cache | Skip (FK set to NULL) |
| Unknown team | Team name not in resolution cache | Skip (FK set to NULL) |

## Idempotency

The pipeline is designed to be safely re-runnable:

- **Core entities** use idempotent inserts — duplicates are silently skipped
- **Analytical tables** are truncated before writing — always reflect the latest computation
- **Match data** uses `external_id` UNIQUE constraint — prevents duplicate matches
- **UUID-based entity resolution** — the same player is never created twice

## Scaling Considerations

### Current (pandas)

| Dataset | Matches | Deliveries | Time |
|---------|---------|-----------|------|
| Full IPL | 1,243 | ~296K | ~5min |
| Full IPL | 1,243 | ~350K | ~10min |
| Full T20I | ~2,000 | ~600K | ~20min |
| Full ODI | ~2,500 | ~1.4M | ~40min |
| Full Test | ~1,200 | ~2.4M | ~60min |

Memory usage: ~500 MB peak for full IPL.

### Future (PySpark)

Reference implementation exists in `data_pipeline/spark/`:
- Requires Java 8–17 (or Java 17+ with PySpark 4.x)
- Can handle millions of deliveries in distributed mode
- Same analytical algorithms, distributed execution
- Activate when data volumes exceed pandas memory capacity

## Troubleshooting

### "No JSON files found"

- Ensure the pipeline has internet access to download from Cricsheet
- Check that `data/raw/{format}/` directory exists after download
- Try `--force` to re-download

### "FOREIGN KEY constraint failed"

- Usually means a player name wasn't discovered during entity resolution
- The pipeline logs all discovered entities — check for name mismatches
- In PostgreSQL, verify the schema was applied correctly

### "Memory error"

- For very large datasets, increase available RAM or use `--sample` to limit
- Consider switching to the PySpark implementation

### PostgreSQL connection failures

- Verify `DATABASE_URL` is correct in `.env`
- Supabase passwords with `[` or `]` must be URL-encoded (`%5B`, `%5D`)
- Wait 60 seconds if Supabase circuit breaker triggers (too many failed auth attempts)
- Use the Session pooler (port 5432) for reliable connections
