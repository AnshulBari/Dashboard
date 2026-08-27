# Phase 5.3A: Historical Dataset Preparation & Ingestion Readiness

## 1. Dataset Inventory

### T20I Historical Dataset (Cricsheet)
| Metric | Value |
|--------|-------|
| Source | Cricsheet `t20s_json.zip` |
| Compressed size | 21.4 MB |
| Uncompressed size | 438.3 MB |
| Total JSON files | 5,646 |
| Men's matches (estimated) | ~2,789 |
| Women's matches (filtered) | ~2,118 (excluded) |
| Date range | 2007-01 to 2024-03 |
| Match type in source | `T20` (remapped to `T20I`) |
| Team type | `international` |

### ODI Historical Dataset
| Metric | Value |
|--------|-------|
| Source | Cricsheet `odis_json.zip` |
| Compressed size | 20.4 MB |
| Total JSON files | 3,176 |
| Men's matches (estimated) | ~2,312 |
| Women's matches (filtered) | ~864 (excluded) |
| Date range | 2016-06 to 2020-03 |

### Test Historical Dataset
| Metric | Value |
|--------|-------|
| Source | Cricsheet `tests_json.zip` |
| Compressed size | 16.4 MB |
| Total JSON files | 916 |
| Men's matches (estimated) | ~886 |
| Women's matches (filtered) | ~30 (excluded) |
| Date range | 2005-04 to 2026-06 |

## 2. Compatibility Report

### Structure Compatibility: PASS
- Cricsheet JSON structure matches existing reader expectations
- Top-level keys: `meta`, `info`, `innings` — all present
- `info` contains: `match_type`, `dates`, `event`, `teams`, `toss`, `outcome`, `venue`, `gender`, `team_type`
- `innings` array with `overs` containing `deliveries` — matches reader

### Critical Finding: Format Remapping Required
Cricsheet uses `match_type: "T20"` for ALL T20 matches (IPL + T20I). The distinction comes from `team_type: "international"`.

**Solution implemented:** `data_pipeline/batch/prepare.py` extracts files with:
- `meta.prepared_format = "T20I"` (for files where `team_type == "international"` and `match_type == "T20"`)
- `match_id` set from filename

Both `reader.py` and `runner.py` now check `meta.prepared_format` before `info.match_type`.

### Gender Filtering Required
Cricsheet ZIPs contain both men's and women's matches (~50/50 split for T20I).

**Solution:** `prepare.py` filters by `gender=male` by default.

### Match ID from Filename
Cricsheet JSON files have no `match_id` field. The `match_id` is the filename stem (e.g., `1001349.json` → match_id `1001349`).

**Solution:** `prepare.py` sets `data["match_id"] = Path(fname).stem`. Batch runner also has fallback.

## 3. Preparation Layer

### `data_pipeline/batch/prepare.py`
```bash
# Dry run - analyze ZIP contents
python -m data_pipeline.batch.prepare --format t20i --dry-run

# Extract men's matches only
python -m data_pipeline.batch.prepare --format t20i --gender male

# Extract all formats
python -m data_pipeline.batch.prepare --format all --gender male

# Validate extracted files
python -m data_pipeline.batch.prepare --format t20i --validate

# Clean up extracted files (keep ZIPs)
python -m data_pipeline.batch.prepare --format t20i --cleanup
```

## 4. Batch Size Recommendation

Based on measurements:
- **250 files/batch** — optimal for Supabase statement timeout
- **200 rows/batch** — for analytics INSERT
- **500 rows/batch** — for analytics DELETE

For 2,789 T20I matches: **12 batches of 250** (last batch: 89 files)

## 5. Estimated Processing Requirements

| Metric | T20I | ODI | Test |
|--------|------|-----|------|
| Matches | ~2,789 | ~2,312 | ~886 |
| Est. deliveries | ~650K | ~1.1M | ~350K |
| Est. processing time | ~15-30 min | ~25-45 min | ~15-25 min |
| Est. DB write time | ~5-10 min | ~8-15 min | ~5-10 min |
| Est. analytics time | ~10-20 min | ~15-25 min | ~10-15 min |

## 6. Blockers Resolved

1. ✅ ZIP extraction + gender filtering
2. ✅ Format remapping (T20 → T20I for international)
3. ✅ Match ID assignment from filename
4. ✅ Batch runner compatibility verified
5. ✅ `.gitignore` verified (ZIPs excluded)
6. ✅ Phase 5.1 tests fixed to use SQLite (prevent production pollution)
7. ✅ Orphaned players/teams cleaned from production database

## 7. Blockers Remaining

None for T20I ingestion. The pipeline is ready.

## 8. Recommended Pilot Command

```bash
# Step 1: Extract historical T20I data
python -m data_pipeline.batch.prepare --format t20i --gender male

# Step 2: Dry run to verify
python -m data_pipeline.batch --format t20i --batch-size 250 --dry-run

# Step 3: Process first batch only (pilot)
python -m data_pipeline.batch --format t20i --batch-size 250 --batch-id 0

# Step 4: Verify
python -m data_pipeline.audit

# Step 5: Process remaining batches
python -m data_pipeline.batch --format t20i --batch-size 250 --resume
```

## 9. Rollback/Recovery Procedure

### If batch fails mid-processing:
```bash
# Check status
python -m data_pipeline.batch --status --formats t20i

# Resume from failed batch
python -m data_pipeline.batch --format t20i --batch-size 250 --resume
```

### If data is corrupted:
```bash
# Delete T20I matches (preserves IPL/ODI/Test)
psql -c "DELETE FROM deliveries WHERE match_id IN (SELECT id FROM matches WHERE format = 'T20I');"
psql -c "DELETE FROM innings WHERE match_id IN (SELECT id FROM matches WHERE format = 'T20I');"
psql -c "DELETE FROM matches WHERE format = 'T20I';"
psql -c "DELETE FROM player_batting_stats WHERE format = 'T20I';"
psql -c "DELETE FROM player_bowling_stats WHERE format = 'T20I';"
psql -c "DELETE FROM player_form WHERE format = 'T20I';"
psql -c "DELETE FROM team_performance WHERE format = 'T20I';"
psql -c "DELETE FROM venue_stats WHERE format = 'T20I';"
psql -c "DELETE FROM batter_bowler_matchups WHERE format = 'T20I';"
```

### If production database is polluted:
The Phase 5.1 tests previously wrote orphaned players/teams to production. This has been cleaned. To prevent recurrence, tests now use SQLite.

## 10. Files Changed in Phase 5.3A

| File | Change |
|------|--------|
| `data_pipeline/batch/prepare.py` | New: ZIP extraction, gender filter, format remapping |
| `data_pipeline/batch/runner.py` | Updated: `_flatten_match` uses `meta.prepared_format` |
| `data_pipeline/pipeline/reader.py` | Updated: `flatten_match` uses `meta.prepared_format` |
| `tests/test_phase5_1.py` | Fixed: Uses SQLite instead of production PostgreSQL |
| `docs/phase-5.3a.md` | This file |

## 11. Current Database State

| Table | Count |
|-------|-------|
| matches | 1,261 |
| deliveries | 298,383 |
| players | 959 |
| teams | 26 |
| T20I matches | 5 |
| ODI matches | 8 |
| Test matches | 5 |
| IPL matches | 1,243 |

**Teams = 26**: 15 IPL franchises + 11 international teams (India, Australia, England, Pakistan, South Africa, Sri Lanka, New Zealand, West Indies, Zimbabwe, Bangladesh, Afghanistan).

**Note**: Previous audit found 87 teams (61 orphaned associate nations). These were created by Phase 5.1 test batch runner writing to production PostgreSQL during test execution. Cleaned up by deleting teams not referenced by any match.
