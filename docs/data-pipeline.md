# Data Pipeline

## Overview

The data pipeline is the core data engineering component of the Cricket Intelligence Platform. It transforms raw Cricsheet match data into precomputed analytical datasets stored in the database.

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
# Cricsheet download URLs
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
- Automatic extraction

**Output:** Directory of JSON files (one per match)

### Stage 2: READ

**Module:** `pipeline/reader.py`

Reads each JSON file and flattens the nested structure into a DataFrame with **one row per delivery**.

**Input:** `data/raw/ipl/*.json` (one file per match)

**Output:** DataFrame with columns:
- Match context: `match_id`, `match_date`, `format`, `venue`, `team_a`, `team_b`
- Delivery context: `batting_team`, `bowling_team`, `innings_number`, `over_number`
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

1. **Teams** — Extract unique team names from batting/bowling teams, normalize to canonical names
2. **Venues** — Extract unique venue names with city information
3. **Players** — Extract unique player names from batter/bowler/non-striker/dismissed columns
4. **Role Inference** — Players who bowl 30+ balls are classified as bowlers/allrounders
5. **Competitions** — Extract event names from match metadata

**Output:** Entity ID caches (name → UUID mappings)

### Stage 5: WRITE (Core Data)

**Module:** `pipeline/db_manager.py` (write_matches, write_innings, write_deliveries_batch methods)

Writes core entity data to the database in order:

1. **Matches** — One row per match with foreign keys to teams, venue, competition
2. **Innings** — One row per innings with foreign keys to match and teams
3. **Deliveries** — One row per delivery with foreign keys to innings, match, and players

**Key design decisions:**
- Uses `INSERT OR IGNORE` to handle duplicates (matches have `external_id` UNIQUE constraint)
- Foreign keys reference UUIDs, not display names
- Deliveries are written in batches of 5,000 for efficiency

### Stage 6: COMPUTE

**Module:** `pipeline/analytics.py`

Computes all analytical statistics from delivery-level data.

**Player Batting Stats:**
- Career aggregates: matches, innings, runs, average, strike rate, 4s, 6s, fifties, hundreds
- Phase-specific: powerplay/middle/death runs and strike rates
- Situational: chasing vs first innings performance
- Consistency score (coefficient of variation)

**Player Bowling Stats:**
- Career aggregates: matches, overs, wickets, economy, average, strike rate
- Phase-specific: powerplay/middle/death overs, wickets, economy

**Player Form Score:**
- Six weighted components (see Analytics Methodology)
- Min-max normalized within each format
- Minimum 3 innings for statistical significance

**Team Performance:**
- Win rate, average scores, phase-wise scoring
- Strength scores (batting + bowling + win rate)

**Venue Stats:**
- Average scores, highest/lowest totals
- Phase-wise scoring

**Matchups:**
- Head-to-head batter vs bowler statistics
- Minimum 10 balls for statistical significance

### Stage 7: WRITE (Analytics)

**Module:** `pipeline/db_manager.py` (write_analytics_table method)

Writes computed analytics to the database:
- Truncates existing analytical data (since it's fully recomputed)
- Inserts new analytics rows
- Maps player/team/venue names to UUIDs for foreign keys

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
- `data/cricket_intelligence.db` — SQLite database with all data and analytics

## Data Quality

The pipeline includes data quality checks at multiple stages:

1. **Ingestion** — Checksum verification, file format validation
2. **Read** — JSON parsing error handling (malformed files are skipped)
3. **Validate** — Null checks, range checks, consistency checks
4. **Write** — Foreign key constraint enforcement
5. **Report** — Rejection statistics, duplicate detection

## Idempotency

The pipeline is designed to be safely re-runnable:

- **Core entities** use `INSERT OR IGNORE` — duplicates are silently skipped
- **Analytical tables** are truncated before writing — always reflect the latest computation
- **Match data** uses `external_id` UNIQUE constraint — prevents duplicate matches

## Scaling Considerations

### Current (pandas)
- Handles up to ~500K deliveries in memory (~2GB RAM)
- Processes 200 matches in ~50 seconds
- Processes 1,243 IPL matches in ~10 minutes

### Future (PySpark)
- Reference implementation exists in `data_pipeline/spark/`
- Requires Java 8–17
- Can handle millions of deliveries
- Same analytical algorithms, distributed execution

## Troubleshooting

### "No JSON files found"
- Ensure the pipeline has internet access to download from Cricsheet
- Check that `data/raw/{format}/` directory exists after download

### "FOREIGN KEY constraint failed"
- Usually means a player name wasn't discovered during entity resolution
- The pipeline logs all discovered entities — check for name mismatches

### "Memory error"
- For very large datasets, increase available RAM or use `--sample` to limit
- Consider switching to the PySpark implementation for production volumes
