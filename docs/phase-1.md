# Phase 1: Universal Cricket Data Model

## Objective

Evolve the IPL-focused data model into a format-agnostic cricket platform capable of representing T20, T20I, ODI, and Test cricket through a single set of tables.

## Summary

Phase 1 introduced:

1. **Format configuration** — Central module defining phase boundaries, overs, and rules per format
2. **Season/edition modeling** — New `seasons` table for proper competition tracking
3. **Test match support** — Innings can now represent declarations, follow-ons, and all-outs
4. **Match result types** — Draws, ties, no results, and abandoned matches
5. **Format-aware analytics** — Phase definitions (powerplay/middle/death) now respect format rules
6. **Cross-format fixtures** — Test data validating T20, T20I, ODI, and Test parsing
7. **Competitions API** — New endpoint for browsing competitions and seasons
8. **Universal schema** — Non-destructive migration preserving all existing IPL data

## What Changed

### Database

| Change | Type | Impact |
|--------|------|--------|
| `format_config` table | NEW | Format-specific rules (PP/middle/death boundaries) |
| `seasons` table | NEW | Season/edition tracking per competition |
| `matches.result_type` | ADDED | Supports draw/tie/no_result/abandoned |
| `matches.day_number` | ADDED | Multi-day match support |
| `matches.event_match_number` | ADDED | Match number within event |
| `matches.season_id` | ADDED | Links to seasons table |
| `innings.declared` | ADDED | Test declaration tracking |
| `innings.all_out` | ADDED | All-out tracking |
| `innings.follow_on` | ADDED | Follow-on tracking |
| `teams.team_type` | ADDED | national/franchise/domestic |
| `competitions.competition_type` | ADDED | league/tournament/bilateral/test_series |

### Pipeline

- **`format_config.py`** — New module with `FormatRules` dataclass and phase classification
- **`reader.py`** — Now extracts `season`, `result_type`, and `day_count` from Cricsheet data
- **`analytics.py`** — All phase classification replaced with format-aware `_classify_phase_format_aware()`

### API

- **`GET /api/competitions`** — List all competitions
- **`GET /api/competitions/{id}`** — Competition detail with seasons
- **`GET /api/competitions/{id}/seasons`** — List seasons for a competition

### Frontend

No frontend changes in Phase 1 (deferred to Phase 2).

## Format-Aware Phase Classification

**Before (hardcoded):**
```python
if over <= 6: phase = "powerplay"
elif over <= 15: phase = "middle"
else: phase = "death"
```

**After (format-aware):**
```python
from data_pipeline.pipeline.format_config import classify_phase
phase = classify_phase(over, format)
# T20: PP=0-5, mid=6-14, death=15+
# ODI: PP=0-9, mid=10-39, death=40+
# Test: "general" (no T20 phases)
```

## Test Coverage

### New Tests (31 tests)

- **Format config** — Phase classification for T20, T20I, ODI, Test
- **Cross-format fixtures** — IPL, T20I, ODI, Test, Test draw parsing
- **Schema validation** — All new tables and columns exist
- **IPL regression** — All existing data counts and analytics intact
- **API endpoints** — Competitions endpoint, existing endpoint regression

### Existing Tests (29 tests)

All Phase 0 tests continue to pass.

**Total: 60/60 tests passing**

## IPL Regression Results

| Metric | Phase 0 | Phase 1 | Status |
|--------|---------|---------|--------|
| Matches | 1,243 | 1,243 | ✅ |
| Deliveries | 295,732 | 295,732 | ✅ |
| Players | 807 | 807 | ✅ |
| Batting Stats | 738 | 738 | ✅ |
| Bowling Stats | 577 | 577 | ✅ |
| Form Scores | 571 | 571 | ✅ |
| V Kohli Runs | 9,346 | 9,346 | ✅ |
| Orphaned Records | 0 | 0 | ✅ |

## Files Changed

| File | Change |
|------|--------|
| `database/schema.sql` | Added format_config, seasons, new columns, indexes |
| `backend/models/entities.py` | Added Season, FormatConfig, new columns to Match/Innings/Team |
| `backend/routes/competitions.py` | New API route |
| `backend/main.py` | Registered competitions router |
| `data_pipeline/pipeline/format_config.py` | New format-aware rules module |
| `data_pipeline/pipeline/analytics.py` | Replaced hardcoded phases with format-aware classification |
| `data_pipeline/pipeline/reader.py` | Extracts season, result_type from Cricsheet |
| `migration_phase1.py` | Non-destructive migration script |
| `setup.py` | Updated SQLite schema with new columns |
| `tests/test_phase1.py` | 31 new tests |
| `data/raw/fixtures/` | Cross-format test fixtures (T20I, ODI, Test, Test draw) |

## Migration Safety

- **Zero data loss** — All ALTERs are additive (ADD COLUMN, CREATE TABLE)
- **Zero dropped tables** — No DROP statements
- **Zero dropped columns** — No ALTER TABLE DROP
- **Idempotent** — `IF NOT EXISTS` on all new tables and indexes
- **Reversible** — New columns are nullable with sensible defaults

## What Was NOT Changed

- Existing IPL analytics formulas
- Existing API endpoint contracts
- Frontend UI
- PySpark architecture
- SQLite development workflow
- Existing test suite

## Next Phase (Phase 2)

Phase 2 would focus on:
1. **International data ingestion** — Download and process T20I, ODI, Test from Cricsheet
2. **Season population** — Extract and store season data from Cricsheet metadata
3. **Frontend format filters** — Add format/competition/season selectors to all pages
4. **TeamDetail/VenueDetail** — Wire to live API (currently mock data)
5. **Multi-format analytics** — Test cricket-specific analytics
