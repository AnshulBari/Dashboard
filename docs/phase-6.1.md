# Phase 6.1 — External Cricket Intelligence Integration

## Objective

Extend the backend to consume official ICC rankings and live cricket match data, without coupling either system to the historical Cricsheet ingestion pipeline.

## Date

August 2026

---

## 1. Data Providers Investigated

### ICC Rankings Sources

| Source | Type | Free Tier | Status |
|---|---|---|---|
| ICC Website | Web only | No API | ❌ No public API |
| CricketData.org | REST API | 100 hits/day | ✅ Selected |
| Sportmonks | REST API | Trial only | Commercial |
| Sportradar | REST API | Commercial | Official ICC provider |

**Decision:** CricketData.org selected as default provider due to free tier availability and reasonable rate limits.

### Live Cricket Data Sources

| Source | Type | Free Tier | Status |
|---|---|---|---|
| CricketData.org | REST API | 100 hits/day | ✅ Selected |
| CricAPI (legacy) | REST API | 100 hits/day | Rebranded to CricketData.org |
| Sportmonks | REST API | Trial only | Commercial |
| ESPN Cricinfo | Unofficial | N/A | Not recommended |

**Decision:** CricketData.org selected as default provider for both rankings and live data.

---

## 2. Provider Selected and Why

### CricketData.org (formerly CricAPI)

**Pros:**
- Free tier with 100 hits/day
- No credit card required
- Covers live scores, player stats, rankings
- Simple REST API
- Active maintenance

**Cons:**
- Data may be delayed by a few minutes
- Limited historical data
- Rate limits on free tier

**Configuration:**
```bash
CRICKETDATA_API_KEY=your_api_key_here
```

**Sign up:** https://cricketdata.org

---

## 3. Architecture

### Provider Abstraction

```
backend/providers/
├── __init__.py          # Package exports
├── base.py              # Abstract base classes & data models
└── cricketdata.py       # CricketData.org implementation
```

**Key Design Principles:**
1. Provider-agnostic interfaces
2. Clear separation of concerns
3. Easy to swap implementations
4. Graceful failure handling
5. No dependency on external APIs for historical data

### Service Layer

```
backend/services/
├── rankings.py          # Rankings service with caching
└── live.py              # Live data service with 30s cache
```

### API Endpoints

```
/api/rankings/
├── /                    # Backward-compatible endpoint
├── /platform            # Platform-computed rankings
└── /icc                 # External ICC rankings

/api/live/
├── /                    # Live match list
├── /{match_id}          # Live match detail
└── /{match_id}/state    # Legacy endpoint
```

---

## 4. Database/Schema Changes

**No schema changes required.**

Rankings and live data are:
- Cached in memory (not persisted to Supabase)
- Mapped to existing canonical entity IDs
- Completely separate from historical analytics

This preserves:
- 149 MB database size
- No deliveries table
- Historical data integrity

---

## 5. Cache Strategy

### Rankings Cache
- **TTL:** 1 hour (3600 seconds)
- **Storage:** In-memory dictionary
- **Key:** `{type}_{format}_{category}` (e.g., `player_Test_batting`)
- **Invalidation:** Manual via `refresh=true` parameter

### Live Data Cache
- **TTL:** 30 seconds
- **Storage:** In-memory dictionary
- **Key:** `live_matches` or `match_{id}`
- **Invalidation:** Automatic after TTL

### Cache Response Format
```json
{
  "cached": true,
  "stale": false,
  "fetched_at": "2026-08-29T12:00:00Z"
}
```

---

## 6. Entity Resolution

External provider names are mapped to canonical database entities:

### Team Mapping
```python
1. Exact match: canonical_name
2. Short name: short_name
3. Partial match: LIKE '%name%'
```

### Player Mapping
```python
1. Exact match: canonical_name
2. Partial match: LIKE '%name%'
```

**Unresolved entities:**
- Logged for review
- Returned with null IDs
- Never create duplicate entities

---

## 7. API Endpoints Added

### GET /api/rankings/icc

Get official ICC rankings from external provider.

**Parameters:**
- `format`: Test, ODI, T20I
- `category`: batting, bowling, allrounders, teams
- `refresh`: Force refresh from provider

**Response:**
```json
{
  "format": "Test",
  "category": "batting",
  "rankings": [
    {
      "rank": 1,
      "name": "Joe Root",
      "country": "England",
      "rating": 900,
      "player_id": "uuid-if-mapped",
      "source_id": "external-id"
    }
  ],
  "source": "cricketdata.org",
  "fetched_at": "2026-08-29T12:00:00Z",
  "cached": false,
  "provider_available": true
}
```

### GET /api/live/

Get current live/upcoming matches.

**Parameters:**
- `refresh`: Force refresh from provider

**Response:**
```json
{
  "matches": [
    {
      "match_id": "12345",
      "team_a": "India",
      "team_b": "Australia",
      "format": "ODI",
      "status": "live",
      "score_team_a": "245/6 (45.2 overs)",
      "team_a_id": "uuid-if-mapped"
    }
  ],
  "source": "cricketdata.org",
  "cached": false,
  "provider_available": true
}
```

### GET /api/live/{match_id}

Get detailed live match state.

**Response:**
```json
{
  "match_id": "12345",
  "innings": {
    "batting_team": "India",
    "score": "245/6",
    "wickets": 6,
    "overs": 45.2,
    "run_rate": 5.41,
    "target": 280,
    "required_run_rate": 6.25
  },
  "players": {
    "striker": "Virat Kohli",
    "non_striker": "KL Rahul",
    "bowler": "Pat Cummins"
  }
}
```

---

## 8. Security/Configuration

### Environment Variables

```bash
# External Cricket Data Providers
CRICKETDATA_API_KEY=  # Required for ICC rankings and live data
```

### Security Measures
- API keys stored in environment variables
- Never committed to Git
- Not exposed to frontend
- Provider errors converted to safe API responses

---

## 9. Tests Added and Results

### Phase 6.1 Test Suite: 47 tests

| Category | Tests | Status |
|---|---|---|
| Provider Abstraction | 7 | ✅ All pass |
| Rankings Service | 6 | ✅ All pass |
| Live Data Service | 6 | ✅ All pass |
| Rankings API | 8 | ✅ All pass |
| Live Data API | 6 | ✅ All pass |
| Entity Mapping | 4 | ✅ All pass |
| Regression | 10 | ✅ All pass |
| **Total** | **47** | **✅ All pass** |

### Existing Test Suites

| Suite | Tests | Status |
|---|---|---|
| Phase 6.0 | 62 | ✅ All pass |
| Phase 5.9 | 47 | ✅ All pass |
| Phase 5.8 | 42 | ✅ All pass |
| Phase 6.1 | 47 | ✅ All pass |
| **Combined** | **198+** | **✅ All pass** |

---

## 10. Historical Regression Results

| Metric | Expected | Actual | Status |
|---|---|---|---|
| IPL matches | 1,243 | 1,243 | ✅ |
| T20I matches | 3,533 | 3,533 | ✅ |
| ODI matches | 2,577 | 2,577 | ✅ |
| Test matches | 897 | 897 | ✅ |
| Total matches | 8,250 | 8,250 | ✅ |
| Kohli IPL runs | 9,346 | 9,346 | ✅ |
| Deliveries table | Absent | Absent | ✅ |
| Database size | <500 MB | 149 MB | ✅ |

---

## 11. Known Limitations

1. **CricketData.org Free Tier:** 100 API hits/day may be limiting for production use
2. **Data Delay:** Live data may be delayed by a few minutes
3. **Rankings Freshness:** ICC rankings update periodically, not in real-time
4. **Entity Mapping:** Some external names may not map to canonical entities
5. **Provider Dependency:** If CricketData.org is unavailable, rankings/live data unavailable (historical data unaffected)

---

## 12. Environment Variables Required

```bash
# Required for external data
CRICKETDATA_API_KEY=your_api_key_here

# Existing variables (unchanged)
DATABASE_URL=postgresql://...
CORS_ORIGINS=http://localhost:5173,...
```

---

## 13. Example API Responses

### ICC Rankings
```bash
curl "http://localhost:8000/api/rankings/icc?format=Test&category=batting"
```

### Live Matches
```bash
curl "http://localhost:8000/api/live/"
```

### Live Match Detail
```bash
curl "http://localhost:8000/api/live/12345"
```

---

## 14. Recommended Next Phase

**Phase 6.2: Frontend Integration**

With the backend now supporting:
- Historical analytics (Phases 0-6.0)
- ICC rankings (Phase 6.1)
- Live match data (Phase 6.1)

The next phase should focus on:
1. Frontend ranking pages
2. Live match dashboard
3. Real-time score updates
4. Combined historical + live views

---

## 15. Files Changed

| File | Change |
|---|---|
| `backend/providers/__init__.py` | **New:** Package exports |
| `backend/providers/base.py` | **New:** Abstract base classes & data models |
| `backend/providers/cricketdata.py` | **New:** CricketData.org implementation |
| `backend/services/rankings.py` | **New:** Rankings service with caching |
| `backend/services/live.py` | **New:** Live data service with 30s cache |
| `backend/routes/rankings.py` | Updated: Added ICC rankings endpoint |
| `backend/routes/live.py` | Updated: Added real provider integration |
| `.env.example` | Updated: Added CRICKETDATA_API_KEY |
| `tests/test_phase6_1.py` | **New:** 47 comprehensive tests |
| `docs/phase-6.1.md` | **New:** This documentation |
| `README.md` | Updated with Phase 6.1 status |
