# Phase 3.1: ODI Data Hardening & Cross-Format Identity Validation

## Overview

Phase 3.1 fixes the critical player identity issue ("V Kohli" vs "Virat Kohli"), validates cross-format identity, resolves the test suite timing issue, and produces a comprehensive data quality audit.

## 1. Player Identity Fix

### Problem

The database contained two separate player identities for the same person:
- **"V Kohli"** — used by Cricsheet IPL data (9,346 runs, 277 innings in T20)
- **"Virat Kohli"** — used by international fixtures (111 runs ODI, 63 runs T20I)

### Solution

Created a controlled migration that:
1. Updated 15,005 foreign key references from V Kohli to Virat Kohli
2. Removed the V Kohli player record
3. Recorded the alias mapping in `player_name_mappings` table
4. Validated zero orphaned records

### Result

**Virat Kohli** now has a single canonical identity with:
- T20: 9,346 runs (from IPL) 
- T20I: 63 runs (from international)
- ODI: 111 runs (from international)
- Affiliations: Royal Challengers Bangalore (T20), India (T20I, ODI)

## 2. Identity Resolution Architecture

The system now uses `player_name_mappings` to resolve source-specific names:

```
Cricsheet: "V Kohli"
    → player_name_mappings
    → canonical: "Virat Kohli"
    → player_id: 5a8132b8-...
```

The pipeline's `db_manager.py` loads these mappings at startup and uses them during entity resolution. When a Cricsheet name is encountered, it first checks the mappings table before creating a new player record.

## 3. Test Suite Fix

### Problem

Previous phases reported that Phase 1/1.1 tests "appeared to hang." Investigation revealed:

- The tests were **not hanging** — they were **slow** (~110 seconds for 72 tests)
- Each test opens a PostgreSQL connection and runs queries
- The default 30-60 second timeout was insufficient
- All 72 tests pass when given adequate time

### Solution

No code changes needed. The tests are inherently slow because they query a remote PostgreSQL database. Running with sufficient timeout (180+ seconds) allows all tests to complete.

## 4. Data Quality Audit

### Duplicate Checks (all PASS)
- matches.external_id: PASS
- players.canonical_name: PASS
- teams.canonical_name: PASS
- venues.name: PASS
- competitions.name: PASS

### Foreign Key Checks (all PASS)
15/15 FK relationships verified with zero orphans.

### Validity Checks
- Invalid ball_in_over: PASS
- Negative runs: PASS
- Invalid formats: PASS
- Matches without teams: PASS
- 2 innings with number >4: **Legitimate** — MI vs KXIP 2020 had 3 super overs (6 innings total)

## 5. Regression Results

### IPL (post-merge)
| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Matches | 1,243 | 1,243 | ✅ |
| Deliveries | 295,732 | 295,732 | ✅ |
| V Kohli runs | 9,346 | 9,346 (now "Virat Kohli") | ✅ |

### T20I (post-merge)
| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Matches | 5 | 5 | ✅ |
| Deliveries | 518 | 518 | ✅ |

### ODI (post-merge)
| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Matches | 8 | 8 | ✅ |
| Deliveries | 793 | 793 | ✅ |

## 6. ODI Data Source Audit

### Current Coverage
- **8 representative fixtures** based on real historical matches
- Covers: World Cup (2019, 2023), Champions Trophy (2017), Asia Cup (2023), bilateral series
- 11 teams, 58 venues, 8 competitions

### Limitations
- Cricsheet downloads are blocked by Cloudflare protection
- The 8 fixtures validate architecture but are NOT a complete historical ODI dataset
- Full ODI ingestion requires manual Cricsheet download or alternative source

## 7. Test Suite Results

| Suite | Tests | Status |
|-------|-------|--------|
| Phase 0 | 29 | ✅ All pass |
| Phase 1 | 31 | ✅ All pass |
| Phase 1.1 | 41 | ✅ All pass |
| Phase 3 | 43 | ✅ All pass |
| Phase 3.1 | 32 | ✅ All pass |
| **Total** | **176** | **All pass** |

## 8. Files Changed

| File | Change |
|------|--------|
| `migration_phase3_1.py` | New: identity merge migration script |
| `scripts/investigate_identity.py` | New: identity investigation tool |
| `scripts/plan_identity_merge.py` | New: merge planning tool |
| `data_pipeline/pipeline/db_manager.py` | Updated: player name mapping resolution |
| `backend/models/entities.py` | Added: PlayerNameMapping ORM model |
| `tests/test_phase3_1.py` | New: 32 Phase 3.1 tests |
| `tests/test_phase1.py` | Updated: V Kohli → Virat Kohli references |
| `tests/test_phase1_1.py` | Updated: V Kohli → Virat Kohli references |
| `tests/test_phase3.py` | Updated: V Kohli → Virat Kohli references |
| `docs/phase-3.1.md` | New: this documentation |

## 9. Remaining Limitations

1. **Player name disambiguation scope:** Only "V Kohli" → "Virat Kohli" was explicitly merged. Other Cricsheet abbreviations (e.g., "A Nortje" → "Anrich Nortje") exist but were not auto-merged because they could refer to different people.

2. **ODI dataset size:** 8 fixtures validate the architecture but are not historical coverage.

3. **Name mapping coverage:** The `player_name_mappings` table currently has only 2 entries. A comprehensive mapping would require the full Cricsheet registry data.

4. **Test execution time:** 176 tests take ~2.5 minutes due to PostgreSQL round-trips. This is inherent to the integration test design.

## 10. Readiness Assessment

**Is the platform ready for Test cricket ingestion?**

**YES.** The universal data model is verified:
- Format-aware analytics (T20/T20I/ODI) ✅
- Cross-format player identity works ✅
- No format contamination after merge ✅
- 176/176 tests passing ✅
- IPL regression intact ✅
- Data quality audit clean ✅

The remaining concern — comprehensive player name mapping — does not prevent Test ingestion. New Test player names will be discovered from match data and can be mapped incrementally.
