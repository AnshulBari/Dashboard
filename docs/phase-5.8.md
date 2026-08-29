# Phase 5.8: Analytical Query Layer

## 1. Objective

Build and validate a clean analytical query/aggregation layer over the existing database, making all required analytical dimensions first-class and reliable for frontend consumption.

## 2. Architecture

### New Files Created

| File | Purpose |
|---|---|
| `backend/services/__init__.py` | Services package |
| `backend/services/analytics.py` | Analytical query layer — reusable SQL aggregation functions |
| `backend/routes/analytics.py` | New API endpoints exposing analytical dimensions |
| `tests/test_phase5_8.py` | 42 comprehensive analytical dimension tests |
| `docs/phase-5.8.md` | This documentation |

### Modified Files

| File | Change |
|---|---|
| `backend/main.py` | Registered analytics router at `/api/analytics` |

## 3. Supported Dimensions

### Player Analytics (8 endpoints)

| Endpoint | Dimension | Example |
|---|---|---|
| `GET /analytics/players/{id}/career` | Career across formats | Kohli: T20/T20I/ODI/Test |
| `GET /analytics/players/{id}/by-year` | Year-by-year | Kohli ODI: 2008–2026 |
| `GET /analytics/players/{id}/by-competition` | By competition | Kohli: IPL, bilateral |
| `GET /analytics/players/{id}/by-season` | By season | Kohli IPL: 2008–2026 |
| `GET /analytics/players/{id}/vs-opponent` | Vs each opponent | Kohli vs Australia |
| `GET /analytics/players/{id}/at-venue` | At each venue | Kohli at venues |
| `GET /analytics/players/{id}/history` | Match history | Recent matches |
| `GET /analytics/players/{id}/progression` | Career progression | Cumulative by year |

### Team Analytics (7 endpoints)

| Endpoint | Dimension | Example |
|---|---|---|
| `GET /analytics/teams/{id}/by-format` | By format | India: ODI/Test/T20I |
| `GET /analytics/teams/{id}/by-year` | By year | India wins by year |
| `GET /analytics/teams/{id}/vs-team/{opp}` | Head-to-head | India vs Australia |
| `GET /analytics/teams/{id}/at-venue` | At each venue | India at venues |
| `GET /analytics/teams/{id}/by-competition` | By competition | India in ICC events |
| `GET /analytics/teams/{id}/history` | Match history | Recent matches |
| `GET /analytics/teams/{id}/trend` | Win-rate trend | By year |

### Competition Analytics (2 endpoints)

| Endpoint | Dimension | Example |
|---|---|---|
| `GET /analytics/competitions/{id}/summary` | Summary + seasons | IPL with all seasons |
| `GET /analytics/seasons/{id}/matches` | Season matches | IPL 2024 matches |

### Venue Analytics (3 endpoints)

| Endpoint | Dimension | Example |
|---|---|---|
| `GET /analytics/venues/{id}/by-format` | By format | Venue stats by format |
| `GET /analytics/venues/{id}/teams` | Team performance | Teams at venue |
| `GET /analytics/venues/{id}/players` | Top players | Players at venue |

### Match Analytics (1 endpoint)

| Endpoint | Dimension | Example |
|---|---|---|
| `GET /analytics/matches/{id}/detail` | Full match detail | Scorecard + metadata |

### System (2 endpoints)

| Endpoint | Purpose |
|---|---|
| `GET /analytics/data-completeness` | Coverage metrics |
| `GET /analytics/profile/{query}` | Query performance profiling |

## 4. Query Design

### No Deliveries Dependency

All queries operate on:
- `player_batting_stats` / `player_bowling_stats` — career aggregates
- `player_form` — form scores
- `match_batting_summary` / `match_bowling_summary` — per-match scorecards
- `team_performance` — team aggregates
- `venue_stats` — venue aggregates
- `batter_bowler_matchups` — matchup data
- `matches` / `innings` — match metadata
- `players` / `teams` / `venues` / `competitions` / `seasons` — entities

### Filter Composition

Queries support combinations:
- `format` — mandatory for format-scoped queries
- `competition` — via competition_id join
- `season` — via season_id join
- `year` — via EXTRACT(YEAR FROM match_date)
- `opponent` — via innings bowling_team join
- `venue` — via venue_id join

### NULL Competition Handling

When `competition_id` is NULL (80.6% of international matches), the analytics layer uses `COALESCE(c.name, 'Unknown')` and groups NULL competitions together. This preserves the match without inventing a fake competition.

### Format Isolation

Every query is format-scoped. The `WHERE m.format = :fmt` clause ensures:
- T20 queries never include T20I/ODI/Test data
- ODI queries never include T20/T20I/Test data
- Each format's analytics are independent

## 5. Data Completeness

| Dimension | Coverage | Notes |
|---|---|---|
| venue_id | 100% | All 8,250 matches |
| format | 100% | All matches classified |
| competition_id | 19.4% | IPL=100%, T20I=0.9%, ODI=11.2%, Test=4.6% |
| season_id | 19.4% | Follows competition coverage |
| player_id | 100% | All scorecard rows reference valid players |
| team_id | 100% | All matches have valid teams |

**Source-data missing**: 80.6% of international matches lack Cricsheet event names, so competition/season cannot be assigned. This is a source limitation, not a pipeline bug.

## 6. Bug Fix

### SQL Operator Precedence

**Problem**: The `team_vs_team` function's format filter was not applied due to SQL `AND` binding tighter than `OR`.

```sql
-- Before (broken): format filter only applied to second OR branch
WHERE (team_a = :a AND team_b = :b) OR (team_a = :b AND team_b = :a) AND format = :fmt

-- After (fixed): format filter applied to entire expression
WHERE ((team_a = :a AND team_b = :b) OR (team_a = :b AND team_b = :a)) AND format = :fmt
```

## 7. Performance

| Query | Time | Notes |
|---|---|---|
| Player career | ~200ms | Uses indexed player_batting_stats |
| Team vs team | ~150ms | Joins matches + teams |
| Match detail | ~200ms | Joins scorecard + innings tables |
| Player by year | ~200ms | Aggregation on match_batting_summary |

All queries under 1000ms (target). Supabase network latency ~150ms.

## 8. Tests

**42 Phase 5.8 tests: all pass.**

| Category | Tests | Status |
|---|---|---|
| Player career | 4 | All pass |
| Player by year | 3 | All pass |
| Player by competition | 2 | All pass |
| Player by season | 1 | Pass |
| Player vs opponent | 2 | All pass |
| Player at venue | 1 | Pass |
| Player match history | 1 | Pass |
| Team by format | 1 | Pass |
| Team by year | 1 | Pass |
| Team head-to-head | 3 | All pass |
| Team at venue | 1 | Pass |
| Team by competition | 1 | Pass |
| Team match history | 1 | Pass |
| Team trend | 1 | Pass |
| Competition summary | 1 | Pass |
| Season matches | 1 | Pass |
| Venue analytics | 2 | All pass |
| Match detail | 3 | All pass |
| Data completeness | 1 | Pass |
| Format isolation | 3 | All pass |
| Regression | 3 | All pass |
| Performance | 3 | All pass |
| Database size | 1 | Pass |
| No deliveries | 1 | Pass |

**Combined suite**: 100 passed, 3 skipped, 0 failed.

## 9. Database Size

**149 MB** — unchanged. No new tables added.

## 10. Audit

80 checks, 78 passed, 2 warnings, 0 failures.

## 11. Regression

| Metric | Expected | Actual | Status |
|---|---|---|---|
| IPL matches | 1,243 | 1,243 | ✅ |
| Kohli IPL runs | 9,346 | 9,346 | ✅ |
| T20I matches | 3,533 | 3,533 | ✅ |
| ODI matches | 2,577 | 2,577 | ✅ |
| Test matches | 897 | 897 | ✅ |
| Total matches | 8,250 | 8,250 | ✅ |

## 12. Known Limitations

1. **Competition coverage**: 80.6% of international matches lack competition association (Cricsheet source limitation)
2. **Player-by-competition/season**: Requires scorecard-based aggregation at query time (not precomputed)
3. **Team head-to-head**: Derived via match joins (no dedicated materialized table)
4. **73 delivery-dependent tests** remain skipped from Phase 5.6A

## 13. Readiness Assessment

**The analytical layer is ready for frontend consumption.** All 22 endpoints expose complete, format-isolated, correctly filtered analytical data. The 42-test suite validates correctness across all dimensions. No new tables were introduced, and the database remains at 149 MB.
