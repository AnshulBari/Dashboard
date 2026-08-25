# Data Pipeline

## Pipeline Stages

```
Stage 1: INGEST    → Download Cricsheet ZIP → Extract JSON files
Stage 2: READ      → Load JSON into Spark DataFrames
Stage 3: VALIDATE  → Check schema, reject malformed records
Stage 4: NORMALIZE → Map player/team names to canonical IDs
Stage 5: TRANSFORM → Flatten nested data, add computed columns
Stage 6: AGGREGATE → Player/team/venue statistics
Stage 7: FEATURE   → Form scores, matchup computations
Stage 8: WRITE     → Export to PostgreSQL / Parquet
```

## Stage Details

### Stage 1: Ingestion

The `CricsheetIngestor` class manages data downloads:

- Downloads ZIP files from Cricsheet
- Tracks checksums to avoid re-downloading
- Extracts JSON match files
- Supports multiple formats (T20I, ODI, Test, IPL)

```python
ingestor = CricsheetIngestor("data/raw")
ingestor.download("t20i")
ingestor.extract("t20i")
```

### Stage 2: Read

Each Cricsheet JSON file represents one match with nested data:

```json
{
  "info": { "teams": [...], "venue": "...", ... },
  "innings": [
    {
      "team": "India",
      "overs": [
        { "over": 0, "deliveries": [...] }
      ]
    }
  ]
}
```

The `flatten_match_data()` function transforms this into a flat DataFrame with one row per delivery.

### Stage 3: Validation

Checks applied:
- Required fields (batter, bowler) are not null
- Runs are non-negative
- Over numbers are valid (0-50)
- Ball in over is valid (1-9, accounting for extras)

Rejected records are counted and reported in the pipeline summary.

### Stage 4: Normalization

- Team names → canonical names via lookup table
- Player names → player registry (fuzzy matching)
- Format strings → standardized format
- Phase classification (powerplay/middle/death)

### Stage 5: Transform

Adds computed columns:
- `cumulative_runs` — running total per innings (window function)
- `cumulative_wickets` — running wicket count per innings
- `phase` — powerplay/middle/death classification
- `is_chasing` — whether batting team is chasing

### Stage 6: Aggregate

Computes statistics using Spark aggregations:

- `player_batting_stats` — career and period-filtered
- `player_bowling_stats` — career and period-filtered
- `team_performance` — strength ratings
- `venue_stats` — ground analytics

### Stage 7: Feature Engineering

Computes advanced analytics:
- `player_form` — weighted composite form score
- `batter_bowler_matchups` — head-to-head data
- `consistency_score` — coefficient of variation based

### Stage 8: Write

Exports to:
- **Parquet** — for local development (efficient columnar format)
- **PostgreSQL** — for production (via JDBC)

## Running the Pipeline

```bash
# Download and process T20I data (first 100 matches)
python -m data_pipeline.jobs.run_pipeline --format t20i --sample 100

# Full T20I dataset
python -m data_pipeline.jobs.run_pipeline --format t20i

# Force re-download
python -m data_pipeline.jobs.run_pipeline --format odi --force

# Process IPL data
python -m data_pipeline.jobs.run_pipeline --format ipl
```

## Data Quality

The pipeline reports:
- Records processed
- Records rejected (with reasons)
- Records duplicated
- Records missing required fields
- Processing time

The summary is written to `data/processed/pipeline_summary.json`.

## Why PySpark Over Pandas?

| Criterion | PySpark | Pandas |
|-----------|---------|--------|
| Memory efficiency | ✅ Distributed | ❌ Single machine |
| 500K+ deliveries | ✅ Handles easily | ⚠️ Slow, may OOM |
| Window functions | ✅ Native | ⚠️ Available but slower |
| Parallel processing | ✅ Automatic | ❌ Single-threaded |
| Scalability | ✅ Cluster-ready | ❌ Fixed to machine |
| Code complexity | ⚠️ Slightly more | ✅ Simpler |
| Development speed | ⚠️ Slower local | ✅ Faster iteration |

**Decision**: Use PySpark for the main pipeline (production quality), but acknowledge Pandas is sufficient for small prototyping tasks. The pipeline includes Pandas for small local tasks where Spark overhead isn't justified.
