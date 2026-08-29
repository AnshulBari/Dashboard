# Phase 5.6D: Scorecard Pipeline Hardening & Data-Integrity Regression

## 1. Problem Statement

Phase 5.6C discovered that scorecards for ~407 ODI/T20I matches were inflated by exactly 2.00x. The root cause was that the old `generate_scorecard_from_json` script read from the `deliveries` table and could process the same deliveries twice during multi-run generation. The `ON CONFLICT DO NOTHING` clause prevented duplicate rows but not duplicate aggregation.

Phase 5.6D creates a hardened, deterministic scorecard generation architecture that:
- Uses Cricsheet JSON as the authoritative source (not the deliveries table)
- Processes each match exactly once per invocation
- Produces identical output on repeated runs (idempotent)
- Cannot be corrupted by double-processing

## 2. Root Cause of 5.6C Inflation

The old `scripts/generate_scorecards.py`:
1. Read from the `deliveries` table (which was removed in Phase 5.6A)
2. Used `ON CONFLICT DO NOTHING` which silently ignored re-inserts
3. During batch reprocessing, certain deliveries were aggregated twice
4. Every player's batting/bowling values became exactly 2x the correct value

## 3. New Architecture

### `data_pipeline/pipeline/scorecards.py`

A new module providing:

- **`compute_scorecard_from_json(data)`** — Pure function. Same JSON input always produces same output.
- **`validate_scorecard(batting, bowling, match_id)`** — Validates computed scorecards.
- **`ScorecardGenerator`** class:
  - `generate_from_json_data(data, match_id)` — Process one match from JSON
  - `generate_from_json_file(path)` — Process one match from a file
  - `generate_from_directory(path)` — Process all JSON files in a directory
  - `generate_from_zip(path)` — Process all matches from a Cricsheet ZIP
  - `verify_idempotency(path)` — Prove double-processing produces identical results
  - `detect_duplicate_sources(path)` — Find duplicate match IDs

### Key Design Decisions

| Decision | Rationale |
|---|---|
| Cricsheet JSON as source | Deliveries table removed in 5.6A; JSON is authoritative |
| `ON CONFLICT DO UPDATE` | Supabase pooler doesn't hold true transactions; upsert is inherently idempotent |
| Per-match processing | Failed matches don't affect others; minimal blast radius |
| Validation before write | Catches bad data before it enters the database |
| Duplicate detection | Prevents the root cause of the 5.6C incident |

## 4. Idempotency Guarantees

Running the same match twice produces identical database state because:
1. `compute_scorecard_from_json()` is a pure function
2. `ON CONFLICT DO UPDATE` replaces existing rows atomically
3. No aggregation depends on existing database state
4. Each match is processed independently

## 5. Validation Rules

### Batting
- No negative runs
- No negative balls
- No negative boundaries
- Strike rate mathematically consistent
- Player/match/innings uniqueness

### Bowling
- No negative runs conceded
- No negative wickets
- No negative balls
- Economy mathematically consistent
- Bowling total >= batting total (extras)

### Cross-check
- Bowling innings total should be >= batting innings total (extras account for the difference)

## 6. Files Changed

| File | Change |
|---|---|
| `data_pipeline/pipeline/scorecards.py` | **New**: JSON-based deterministic scorecard generator |
| `tests/test_phase5_6d.py` | **New**: 38 validation tests |

## 7. Test Results

### Phase 5.6D Tests (38 total)
- **38 passed, 0 failed**

### Test Categories
| Category | Tests | Status |
|---|---:|---|
| Source Independence | 3 | All pass |
| Deterministic Generation | 3 | All pass |
| Idempotency (all 4 formats) | 4 | All pass |
| Inflation Regression | 4 | All pass |
| Scorecard Validation | 5 | All pass |
| Cross-Format Isolation | 1 | Pass |
| Regression Counts | 6 | All pass |
| Database Integrity | 7 | All pass |
| Duplicate Detection | 2 | All pass |

### Full Suite
- 55 Phase 5.6C + 5.6D tests pass
- Audit: 80 checks, 78 passed, 2 warnings, 0 failures
- Frontend TypeScript: clean
- Vite build: passes

## 8. Regression Results

| Metric | Expected | Actual | Status |
|---|---|---|---|
| IPL matches | 1,243 | 1,243 | ✅ |
| T20I matches | 3,533 | 3,533 | ✅ |
| ODI matches | 2,577 | 2,577 | ✅ |
| Test matches | 897 | 897 | ✅ |
| Total matches | 8,250 | 8,250 | ✅ |
| Kohli IPL runs | 9,346 | 9,346 | ✅ |
| Database size | <500 MB | 149 MB | ✅ |

## 9. Database Size

**149 MB** — unchanged from Phase 5.6C. Comfortably under 500 MB Free Plan limit.

## 10. Known Limitations

1. **Supabase pooler transaction behavior**: `engine.begin()` doesn't hold a true transaction through the pooler. Solved with `ON CONFLICT DO UPDATE` instead of DELETE+INSERT.
2. **Batch-level analytics** still use in-memory DataFrames during ingestion (not affected by this phase).
3. **73 delivery-dependent tests** remain skipped from Phase 5.6A (separate concern).
4. **Network latency**: Each scorecard generation round-trip takes ~25-50ms due to Supabase latency.

## 11. Readiness Assessment

**The scorecard pipeline is now hardened against double-processing.** The historical 2x inflation bug has a dedicated regression test that proves re-running generation on any format produces identical values. The architecture is ready for frontend integration.
