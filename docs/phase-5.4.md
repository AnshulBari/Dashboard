# Phase 5.4 — Historical ODI Dataset Ingestion

## Objective

Ingest the complete historical men's ODI dataset from Cricsheet into PostgreSQL/Supabase using the existing validated batch infrastructure.

## Dataset

| Metric | Value |
|---|---:|
| Source | Cricsheet (men's ODI) |
| ZIP size | ~20 MB |
| Total raw files | 3,176 |
| Men's ODI files | 2,569 |
| Women's ODI files (excluded) | 607 |
| Invalid/malformed files | 0 |
| Existing ODI fixtures retained | 8 |
| **Total ODI matches** | **2,577** |
| **Total ODI deliveries** | **1,477,207** |
| Batches (250 per batch) | 11 |

## Men's Filtering

Cricsheet ODI JSON files include both men's and women's matches. The `prepare.py` layer filters using `gender: "male"` from the match metadata. 607 women's matches were excluded.

## Batch Configuration

- Format: `odi`
- Batch size: 250 matches
- Batches: 11 (10 × 250 + 1 × 77)
- All batches completed successfully

## Canary Results

| Check | Result |
|---|---|
| 250-match batch | PASS |
| PostgreSQL verification | PASS |
| Analytics persistence | PASS |
| Audit (0 failures) | PASS |
| IPL regression (1,243/295,732/9,346) | PASS |
| Format isolation | PASS |
| Identity resolution | PASS |
| Idempotency (zero delta on re-run) | PASS |
| Checkpoint/resume | PASS |

## Full Ingestion Results

| Metric | Delta |
|---|---:|
| Matches added | +2,569 |
| Innings added | +5,090 |
| Deliveries added | +1,476,414 |
| Players added | +4,608 |
| Teams added | +101 |
| Venues added | +394 |
| Competitions added | 0 |
| Batting stats rows (ODI) | 1,984 |
| Bowling stats rows (ODI) | 1,528 |
| Form rows (ODI) | 1,324 |
| Matchup rows (ODI) | 41,946 |

## Database State (Final)

| Table | Count |
|---|---:|
| matches | 7,358 |
| innings | 14,712 |
| deliveries | 2,611,366 |
| players | 5,567 |
| teams | 127 |
| venues | 452 |
| competitions | 12 |
| seasons | 44 |
| player_batting_stats | 6,972 |
| player_bowling_stats | 5,289 |
| player_form | 5,118 |
| team_performance | 152 |
| venue_stats | 659 |
| batter_bowler_matchups | 77,849 |
| player_team_affiliations | 9,198 |

## Format Breakdown

| Format | Matches | Deliveries |
|---|---:|---:|
| T20 (IPL) | 1,243 | 295,732 |
| T20I | 3,533 | 837,087 |
| ODI | 2,577 | 1,477,207 |
| Test | 5 | 1,340 |
| **Total** | **7,358** | **2,611,366** |

## Regression

| Metric | Expected | Actual | Status |
|---|---|---|---|
| IPL matches | 1,243 | 1,243 | ✅ |
| IPL deliveries | 295,732 | 295,732 | ✅ |
| Kohli IPL runs | 9,346 | 9,346 | ✅ |
| T20I matches | 3,533 | 3,533 | ✅ |
| Test matches | 5 | 5 | ✅ |
| ODI matches | ≥8 | 2,577 | ✅ |

## Cross-Format Identity

| Player | ODI | T20 (IPL) | T20I | Test |
|---|---|---|---|---|
| Virat Kohli | 15,484 runs | 9,346 runs | 4,095 runs | 529 runs |
| KL Rahul | ✓ | ✓ | ✓ | ✓ |

Format isolation verified. No cross-format contamination.

## Analytics Results

ODI analytics recomputed from the full 2,577-match corpus using a chunked approach (50 matches per chunk, 52 chunks total).

| Table | ODI Rows |
|---|---:|
| player_batting_stats | 1,984 |
| player_bowling_stats | 1,528 |
| player_form | 1,324 |
| team_performance | 28 |
| venue_stats | 305 |
| batter_bowler_matchups | 41,946 |

**Note:** Analytics recomputation required a checkpoint-based chunked approach due to Supabase's 15-second statement timeout. Each chunk of 50 matches was loaded, computed, and cached to disk, then merged with proper aggregation (SUM for cumulative stats, MAX for highest scores) before final write.

## Identity Resolution

- 34 duplicate canonical player names were merged (FK references updated, orphans deleted)
- 5 duplicate venue names were merged
- 13,835+ FK references migrated during player deduplication
- 236 missing player-team affiliations were created
- 0 unresolved player names in analytics

## Problems Encountered and Fixes

1. **Supabase statement timeout (15s)** — Full-format delivery loading for analytics timed out. Fix: chunked loading (50 matches per chunk) with disk-based checkpointing.

2. **Analytics chunk aggregation** — Initial merge used `drop_duplicates(keep='last')` instead of proper SUM/MAX aggregation across chunks. Fix: groupby player_name+format with SUM for cumulative stats and MAX for highest_score.

3. **DatabaseManager defaulting to SQLite** — The `load_dotenv()` call must precede `DatabaseManager()` initialization. Fix: ensured correct ordering in the recomputation script.

4. **Season/competition unique constraint** — Cricsheet seasons without unique competition+name combinations caused constraint violations during batch processing. Fix: added `ON CONFLICT` handling.

5. **Super-over ball_in_over > 12** — Cricsheet data contains legitimate super-over deliveries with ball numbers exceeding the previous constraint. Fix: constraint relaxed to allow ball_in_over up to 20.

6. **innings_number > 6** — Multi-super-over matches can have 7+ innings. Fix: constraint relaxed to allow 1-10.

7. **Duplicate canonical players** — Each batch created independent player entities for the same name. Fix: post-ingestion merge with FK migration.

8. **Test assertion hardcoded counts** — Multiple tests hardcoded ODI/T20I match counts from the fixture-only era. Fix: updated to use `>=` thresholds.

## Data Quality

- Audit: 78 checks, 74 passed, 4 warnings, **0 failures**
- Warnings: super-over deliveries (20), multi-super-over innings (T20I max=8), bracketed player names (9), duplicate venue names (resolved)

## Performance

| Metric | Value |
|---|---|
| Batch 0 (250 matches) | ~8 min |
| Average batch | ~5 min |
| Full ODI analytics recomputation | ~10 min (52 chunks) |
| Analytics write (78K matchup rows) | ~150s |

## Tests

- Phase 5.4 tests: All pass
- Complete test suite: 278 passed, 13 skipped, 0 failed
- Frontend TypeScript: Clean
- Vite build: Passing

## Known Limitations

1. **Analytics recomputation is slow** — Loading 1.48M deliveries with complex JOINs takes significant time. Apache Spark would materially improve this for the Test dataset (even larger corpus per match).

2. **Player deduplication is manual** — Each batch creates independent player entities. A deterministic identity resolution step should be integrated into the batch runner.

3. **Bilateral series have no competition** — Most T20I and ODI bilateral matches lack an event name, so they have no competition/season assignment. This is a data quality limitation, not a pipeline issue.

## Readiness for Historical Test Ingestion

**YES** — The architecture is ready. The batch pipeline, idempotency, checkpoint/resume, and analytics infrastructure have all been validated at ODI scale (2,577 matches, 1.48M deliveries). The Test dataset (~900 matches) is smaller and should process faster.

## Recommendations for Phase 5.5

1. **Ingest historical Test dataset** — Same process as T20I/ODI
2. **Integrate player deduplication into batch runner** — Automate the post-batch merge
3. **Consider Apache Spark** — For analytics recomputation performance at full historical scale
4. **Add incremental analytics** — Instead of full recomputation per batch, accumulate incrementally
