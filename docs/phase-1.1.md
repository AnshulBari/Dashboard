# Phase 1.1: Universal Model Hardening & Cross-Format Validation

## Overview

Phase 1.1 hardens the universal cricket data model introduced in Phase 1 by:

1. **Adding player-team affiliations** — A player can now belong to multiple teams across formats
2. **Populating seasons** — Competition editions are now tracked
3. **Backfilling result_type** — Test draws and ties are properly represented
4. **Making analytics format-aware** — Phase definitions are centralized in `format_config.py`
5. **Fixing database views** — Views no longer hardcode `format = 'T20'`
6. **Updating the pipeline** — Matches now write `result_type`, `season_id`; affiliations are created

## Database Changes

### New Tables

| Table | Purpose |
|-------|---------|
| `player_team_affiliations` | Links players to teams with format/competition context |

### Modified

| Table | Change |
|-------|--------|
| `matches` | `result_type` backfilled; `season_id` linked |
| `views` | `v_player_summary` and `v_team_summary` no longer hardcode T20 |

### Data Added

| Table | Before | After |
|-------|--------|-------|
| `player_team_affiliations` | 0 | 806 |
| `seasons` | 0 | 19 |
| `format_config` | 4 | 4 (unchanged) |

## Player-Team Affiliations

### Before

```
Player (team_id = 'Royal Challengers Bangalore')
```

A player could only have one team.

### After

```
Player
  ├── Affiliation: Royal Challengers Bangalore, format=T20, competition=IPL
  ├── Affiliation: India, format=T20I
  ├── Affiliation: India, format=ODI
  └── Affiliation: India, format=Test
```

The `players.team_id` column is retained for backward compatibility but is deprecated.
The `player_team_affiliations` table is the authoritative source for player-team relationships.

## Competition-Edition Model

### Before

```
Competition: Indian Premier League (season='2024')
```

Season was a flat string on the competition.

### After

```
Competition: Indian Premier League
  ├── Season: 2024
  ├── Season: 2023
  └── Season: 2008
```

The `seasons` table properly models competition editions.
Matches are linked to seasons via `match.season_id`.

## Format-Aware Analytics

### Phase Classification

| Format | Powerplay | Middle | Death |
|--------|-----------|--------|-------|
| T20/T20I | Overs 0-5 | Overs 6-14 | Overs 15+ |
| ODI | Overs 0-9 | Overs 10-39 | Overs 40+ |
| Test | `general` (no T20 phases) | — | — |

Phase definitions are centralized in `data_pipeline/pipeline/format_config.py`.
The Spark `classify_phase_udf()` is now format-aware.

## API Changes

### New Endpoints

- `GET /api/players/{id}/affiliations` — Player's team affiliations across formats

### Modified Endpoints

- `GET /api/matches` — Now supports `?competition=` and `?season=` filters; includes `result_type` in response
- `GET /api/competitions/{id}` — Includes `seasons` list

## Test Results

- **41 Phase 1.1 tests**: All passing
- **101 total tests**: All passing (29 Phase 0 + 31 Phase 1 + 41 Phase 1.1)
- **IPL regression**: All 1,243 matches, 295,732 deliveries, 807 players intact
- **V Kohli**: 9,346 runs, avg 40.81, SR 131.14 — unchanged
- **Frontend**: TypeScript clean, Vite build passes

## Files Changed

| File | Change |
|------|--------|
| `database/schema.sql` | Added `player_team_affiliations` table; views no longer hardcode T20 |
| `backend/models/entities.py` | Added `PlayerTeamAffiliation` model |
| `backend/routes/players.py` | Added `GET /{id}/affiliations` endpoint |
| `backend/routes/matches.py` | Added competition/season filters; result_type in response |
| `data_pipeline/pipeline/db_manager.py` | Added `write_affiliations()`, `resolve_season()`, writes result_type/season_id |
| `data_pipeline/pipeline/run.py` | Calls `write_affiliations()` in pipeline |
| `data_pipeline/spark/normalize.py` | `classify_phase_udf()` now accepts format_col parameter |
| `setup.py` | Added `player_team_affiliations` to SQLite schema |
| `tests/test_phase1_1.py` | 41 new tests |
| `migration_phase1_1.py` | Non-destructive migration script |

## Migration

The migration (`migration_phase1_1.py`) is:

- **Non-destructive** — All ALTERs are additive; no data loss
- **Idempotent** — Safe to re-run (uses `ON CONFLICT DO NOTHING`)
- **Verified** — All FK integrity checks pass
