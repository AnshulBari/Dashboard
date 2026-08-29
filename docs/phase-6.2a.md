# Phase 6.2A — Frontend Architecture & Product Design Audit

## 1. Executive Summary

This document presents a comprehensive audit of the Cricket Intelligence Platform's frontend codebase and backend API contracts, followed by a detailed implementation-ready design specification for Phase 6.2B.

**Key Findings:**
- The frontend has 15 pages, but 3 use mock data (TeamDetail, VenueDetail, News), 1 is a static placeholder (Live), and several critical pages don't exist (MatchDetail, Competitions, Search)
- React Query is installed and configured but **completely unused** — all pages use raw useState/useEffect
- Recharts is installed but **never imported** — no charts exist
- The entire frontend defaults to T20/IPL data only — multi-format is not exposed
- The current design is light/white; the reference design is a dark premium sports dashboard
- The backend has 22+ endpoints covering all analytical dimensions, but the frontend only consumes ~40% of available data

**Decision: The frontend requires a near-complete rebuild to match the product vision.**

---

## 2. Current Frontend Architecture Audit

### 2.1 Technology Stack

| Technology | Version | Status |
|---|---|---|
| React | 18.3.1 | ✅ Current |
| TypeScript | 5.3+ | ✅ Current |
| Vite | 5.0 | ✅ Current |
| React Router | 6.22 | ✅ Current |
| Tailwind CSS | 3.4.1 | ✅ Current |
| TanStack React Query | 5.17 | ⚠️ Installed but UNUSED |
| Recharts | 2.12 | ⚠️ Installed but UNUSED |
| Lucide React | 0.312 | ✅ Used for icons |

### 2.2 File Inventory

| File | Lines | Status | Notes |
|---|---|---|---|
| `App.tsx` | 27 | ✅ | Routes defined, functional |
| `main.tsx` | 24 | ✅ | QueryClient configured but unused |
| `layouts/Layout.tsx` | 72 | ⚠️ | Fixed sidebar, no mobile support |
| `pages/Dashboard.tsx` | 200+ | ⚠️ | T20-only, no charts, no live area |
| `pages/Players.tsx` | ~100 | ⚠️ | Basic list, no multi-format |
| `pages/PlayerDetail.tsx` | ~200 | ⚠️ | No format switcher, no charts, no progression |
| `pages/Teams.tsx` | ~60 | ⚠️ | Basic list, T20-only |
| `pages/TeamDetail.tsx` | ~150 | ❌ | **100% mock data** |
| `pages/Matches.tsx` | ~80 | ⚠️ | Basic list, T20-only |
| `pages/Venues.tsx` | ~80 | ⚠️ | Basic list, T20-only |
| `pages/VenueDetail.tsx` | ~150 | ❌ | **100% mock data** |
| `pages/Matchups.tsx` | ~80 | ⚠️ | Basic table, T20-only |
| `pages/Rankings.tsx` | ~120 | ⚠️ | Has format/category selectors, basic table |
| `pages/Live.tsx` | ~30 | ❌ | **Static placeholder** — no API integration |
| `pages/News.tsx` | ~50 | ❌ | **100% hardcoded mock data** |
| `services/api.ts` | ~100 | ⚠️ | Functional but no React Query integration |
| `types/index.ts` | ~180 | ⚠️ | Types defined but not fully aligned with API |

### 2.3 Critical Issues Found

1. **React Query not used**: Despite `QueryClientProvider` in main.tsx, every page uses raw `useState`/`useEffect` + `fetch`. This means:
   - No automatic caching/deduplication
   - No background refetching
   - No loading/error state management
   - No stale-while-revalidate
   - No optimistic updates

2. **Recharts not used**: Installed but never imported. No charts anywhere.

3. **Three pages are fake**: TeamDetail, VenueDetail, and News use hardcoded mock data.

4. **Live page is static**: No API integration, no 30-second refresh.

5. **No multi-format support**: Every page defaults to T20. No global format selector.

6. **No search**: No global search implementation.

7. **No MatchDetail page**: Clicking a match has nowhere to go.

8. **No Competitions page**: Competition hierarchy not exposed.

9. **No mobile responsive**: Fixed 256px sidebar with no mobile drawer.

10. **No dark theme**: Light design, far from the premium dark dashboard vision.

---

## 3. Backend API Audit

### 3.1 Complete Endpoint Inventory

#### Core Entity Endpoints

| Endpoint | Method | Response Shape | Used by Frontend? |
|---|---|---|---|
| `GET /api/players` | GET | `{players, total, limit, offset}` | ✅ Yes |
| `GET /api/players/{id}` | GET | Player detail object | ✅ Yes |
| `GET /api/players/{id}/form` | GET | `{form_score, components}` | ❌ No |
| `GET /api/players/{id}/batting` | GET | Batting stats object | ✅ Yes (indirect) |
| `GET /api/players/{id}/bowling` | GET | Bowling stats object | ✅ Yes (indirect) |
| `GET /api/players/{id}/matchups` | GET | `{matchups: [...]}` | ❌ No |
| `GET /api/players/{id}/affiliations` | GET | `{affiliations: [...]}` | ❌ No |
| `GET /api/teams` | GET | `{teams, total}` | ✅ Yes |
| `GET /api/teams/{id}` | GET | Team detail object | ❌ (uses mock) |
| `GET /api/teams/{id}/analytics` | GET | Full team analytics | ❌ No |
| `GET /api/matches` | GET | `{matches, total, limit, offset}` | ✅ Yes |
| `GET /api/matches/{id}` | GET | Match detail object | ❌ (no page exists) |
| `GET /api/venues` | GET | `{venues, total}` | ✅ Yes |
| `GET /api/venues/{id}/analytics` | GET | Full venue analytics | ❌ (uses mock) |
| `GET /api/competitions` | GET | `{competitions, total}` | ❌ No |
| `GET /api/competitions/{id}` | GET | Competition detail + seasons | ❌ No |
| `GET /api/competitions/{id}/seasons` | GET | `{seasons, total}` | ❌ No |
| `GET /api/matchups` | GET | `{matchups, total}` | ✅ Yes |
| `GET /api/matchups/{batter}/{bowler}` | GET | Head-to-head detail | ❌ No |

#### Analytics Endpoints

| Endpoint | Method | Response Shape | Used by Frontend? |
|---|---|---|---|
| `GET /api/analytics/player/{id}/career` | GET | Career stats by format | ❌ No |
| `GET /api/analytics/player/{id}/by-format` | GET | Stats per format | ❌ No |
| `GET /api/analytics/player/{id}/by-year` | GET | Stats per year | ❌ No |
| `GET /api/analytics/player/{id}/by-competition` | GET | Stats per competition | ❌ No |
| `GET /api/analytics/player/{id}/by-season` | GET | Stats per season | ❌ No |
| `GET /api/analytics/player/{id}/by-opponent` | GET | Stats per opponent | ❌ No |
| `GET /api/analytics/player/{id}/by-venue` | GET | Stats per venue | ❌ No |
| `GET /api/analytics/player/{id}/history` | GET | Match history | ❌ No |
| `GET /api/analytics/player/{id}/progression` | GET | Career progression | ❌ No |
| `GET /api/analytics/team/{id}/overview` | GET | Team overview | ❌ No |
| `GET /api/analytics/team/{id}/by-format` | GET | Team stats per format | ❌ No |
| `GET /api/analytics/team/{id}/by-year` | GET | Team stats per year | ❌ No |
| `GET /api/analytics/team/{id}/head-to-head` | GET | Head-to-head stats | ❌ No |
| `GET /api/analytics/team/{id}/history` | GET | Team match history | ❌ No |
| `GET /api/analytics/competition/{id}/summary` | GET | Competition summary | ❌ No |
| `GET /api/analytics/competition/{id}/seasons` | GET | Competition seasons | ❌ No |
| `GET /api/analytics/competition/{id}/matches` | GET | Competition matches | ❌ No |
| `GET /api/analytics/venue/{id}` | GET | Venue analytics | ❌ No |
| `GET /api/analytics/match/{id}/scorecard` | GET | Match scorecard | ❌ No |
| `GET /api/analytics/matches/history` | GET | Match history list | ❌ No |
| `GET /api/analytics/career-progression/{id}` | GET | Career progression | ❌ No |

#### Rankings & Live Endpoints

| Endpoint | Method | Response Shape | Used by Frontend? |
|---|---|---|---|
| `GET /api/rankings` | GET | Rankings list | ✅ Yes |
| `GET /api/rankings/platform` | GET | Platform rankings | ❌ No |
| `GET /api/rankings/icc` | GET | ICC rankings | ❌ No |
| `GET /api/live` | GET | Live matches | ❌ (placeholder) |
| `GET /api/live/{id}` | GET | Live match detail | ❌ No |
| `GET /api/live/{id}/state` | GET | Live match state | ❌ (stub) |

#### Utility Endpoints

| Endpoint | Method | Response Shape | Used by Frontend? |
|---|---|---|---|
| `GET /health` | GET | Health status | ❌ No |

### 3.2 API Coverage Summary

| Category | Available Endpoints | Used by Frontend | Coverage |
|---|---|---|---|
| Core Entities | 15 | 7 | 47% |
| Analytics | 21 | 0 | 0% |
| Rankings/Live | 6 | 1 | 17% |
| **Total** | **42** | **8** | **19%** |

**The frontend currently uses only 19% of the available backend API surface.**

---

## 4. Frontend ↔ Backend Data Contract Matrix

### 4.1 Player Features

| UI Feature | Backend Endpoint | Parameters | Response Shape | Status |
|---|---|---|---|---|
| Player List | `GET /api/players` | format, role, country, sort_by, limit, offset | `{players, total, limit, offset}` | ✅ Connected |
| Player Detail | `GET /api/players/{id}` | format | Player object with batting/bowling | ✅ Connected |
| Player Form | `GET /api/players/{id}/form` | format | `{form_score, components}` | ❌ Available |
| Player Batting | `GET /api/players/{id}/batting` | format, period | Batting stats | ⚠️ Indirect |
| Player Bowling | `GET /api/players/{id}/bowling` | format, period | Bowling stats | ⚠️ Indirect |
| Player Matchups | `GET /api/players/{id}/matchups` | type, format | `{matchups}` | ❌ Available |
| Player Affiliations | `GET /api/players/{id}/affiliations` | — | `{affiliations}` | ❌ Available |
| Player Career | `GET /api/analytics/player/{id}/career` | — | Career by format | ❌ Available |
| Player by Year | `GET /api/analytics/player/{id}/by-year` | format | Year-by-year stats | ❌ Available |
| Player by Competition | `GET /api/analytics/player/{id}/by-competition` | format | Competition stats | ❌ Available |
| Player by Season | `GET /api/analytics/player/{id}/by-season` | format | Season stats | ❌ Available |
| Player by Opponent | `GET /api/analytics/player/{id}/by-opponent` | format | Opponent stats | ❌ Available |
| Player by Venue | `GET /api/analytics/player/{id}/by-venue` | format | Venue stats | ❌ Available |
| Player History | `GET /api/analytics/player/{id}/history` | format, limit | Match history | ❌ Available |
| Player Progression | `GET /api/analytics/player/{id}/progression` | format | Career progression | ❌ Available |

### 4.2 Team Features

| UI Feature | Backend Endpoint | Status |
|---|---|---|
| Team List | `GET /api/teams` | ✅ Connected |
| Team Detail | `GET /api/teams/{id}` | ❌ Mock data |
| Team Analytics | `GET /api/teams/{id}/analytics` | ❌ Available |
| Team Overview | `GET /api/analytics/team/{id}/overview` | ❌ Available |
| Team by Format | `GET /api/analytics/team/{id}/by-format` | ❌ Available |
| Team by Year | `GET /api/analytics/team/{id}/by-year` | ❌ Available |
| Team Head-to-Head | `GET /api/analytics/team/{id}/head-to-head` | ❌ Available |
| Team History | `GET /api/analytics/team/{id}/history` | ❌ Available |

### 4.3 Match Features

| UI Feature | Backend Endpoint | Status |
|---|---|---|
| Match List | `GET /api/matches` | ✅ Connected |
| Match Detail | `GET /api/matches/{id}` | ❌ No page |
| Match Scorecard | `GET /api/analytics/match/{id}/scorecard` | ❌ Available |
| Match History | `GET /api/analytics/matches/history` | ❌ Available |

### 4.4 Competition Features

| UI Feature | Backend Endpoint | Status |
|---|---|---|
| Competition List | `GET /api/competitions` | ❌ No page |
| Competition Detail | `GET /api/competitions/{id}` | ❌ Available |
| Competition Seasons | `GET /api/competitions/{id}/seasons` | ❌ Available |
| Competition Summary | `GET /api/analytics/competition/{id}/summary` | ❌ Available |
| Competition Matches | `GET /api/analytics/competition/{id}/matches` | ❌ Available |

### 4.5 Live Features

| UI Feature | Backend Endpoint | Status |
|---|---|---|
| Live Matches | `GET /api/live` | ❌ Placeholder |
| Live Match Detail | `GET /api/live/{id}` | ❌ Available |

---

## 5. Information Architecture

### 5.1 Proposed Navigation Hierarchy

```
DASHBOARD (/)                         ← Intelligence Overview
├── Live Now                          ← Inline widget
├── Top Performers                    ← Inline widget
├── Recent Results                    ← Inline widget
├── Upcoming/Fixtures                 ← Inline widget (if available)
└── Quick Stats                       ← Summary cards

LIVE (/live)                          ← Dedicated Live Center
├── Live Matches                      ← Match cards with scores
├── Upcoming Matches                  ← Fixture list
└── Recently Completed                ← Recent results

PLAYERS (/players)                    ← Player Directory
├── Player List                       ← Searchable/filterable
└── Player Detail (/players/:id)      ← Full intelligence profile
    ├── Header + Format Switcher
    ├── Career Summary
    ├── Batting Statistics
    ├── Bowling Statistics
    ├── Career Progression (chart)
    ├── Recent Form
    ├── By Competition
    ├── By Season
    ├── By Opponent
    ├── By Venue
    ├── Match History
    └── Affiliations

TEAMS (/teams)                        ← Team Directory
├── Team List                         ← Searchable/filterable
└── Team Detail (/teams/:id)          ← Full team profile
    ├── Header + Format Switcher
    ├── Overall Statistics
    ├── Win/Loss/Draw
    ├── Head-to-Head
    ├── Recent Matches
    ├── Key Players
    ├── By Competition
    └── By Venue

MATCHES (/matches)                    ← Match Browser
├── Match List                        ← Filterable by format/date/team
└── Match Detail (/matches/:id)       ← Full match view
    ├── Match Header
    ├── Innings Summary
    ├── Batting Scorecard
    ├── Bowling Scorecard
    └── Key Statistics

COMPETITIONS (/competitions)          ← Competition Explorer
├── Competition List                  ← All competitions
└── Competition Detail (/competitions/:id)
    ├── Seasons
    ├── Matches
    ├── Teams
    └── Top Players

VENUES (/venues)                      ← Venue Intelligence
├── Venue List                        ← Searchable
└── Venue Detail (/venues/:id)        ← Full venue profile
    ├── Venue Statistics
    ├── Score Profile
    ├── Pace vs Spin
    ├── Phase Scoring
    └── Match History

MATCHUPS (/matchups)                  ← Batter vs Bowler Analytics
├── Top Matchups Table
└── Specific Matchup (/matchups/:batter/:bowler)

RANKINGS (/rankings)                  ← Rankings
├── Platform Rankings                 ← Computed from analytics
├── Format Selector
├── Category Selector
└── Rankings Table

SEARCH (global)                       ← Global Search
├── Players
├── Teams
├── Matches
├── Competitions
└── Venues
```

### 5.2 Rationale

- **Dashboard** is the primary landing page — should answer "what's happening now?" and "who's performing?"
- **Live** gets its own page because live data requires 30-second refresh and a distinct UX
- **Players** is the core intelligence dimension — the most detailed page
- **Teams** supports national teams and franchises distinctly
- **Matches** enables browsing historical results and viewing scorecards
- **Competitions** is a new page — currently missing entirely
- **Venues** provides ground intelligence
- **Matchups** is a unique differentiator — batter vs bowler analytics
- **Rankings** separates platform-computed from official rankings
- **News** is REMOVED — it's entirely mock data with no real backend
- **Search** is a global overlay, not a page

---

## 6. Navigation Architecture

### 6.1 Primary Navigation (Sidebar)

```
┌─────────────────────────┐
│  ◉ CricketIQ            │  Logo
│                         │
│  ● Dashboard            │  ← Default/home
│  ◉ Live                 │  ← Pulsing indicator when live matches
│  ─────────────          │  Divider
│  ◉ Players              │
│  ◉ Teams                │
│  ◉ Matches              │
│  ◉ Competitions         │  ← NEW
│  ◉ Venues               │
│  ─────────────          │  Divider
│  ◉ Matchups             │
│  ◉ Rankings             │
│  ─────────────          │  Divider
│  🔍 Search              │  ← Opens search overlay
│                         │
│                         │
│  v1.0 · Data: Cricsheet │  Footer
└─────────────────────────┘
```

### 6.2 Top Bar (within main content area)

```
┌────────────────────────────────────────────────────────────────┐
│  [Format: All ▾]  [Competition: All ▾]  [Season: All ▾]      │
└────────────────────────────────────────────────────────────────┘
```

Global filters persist across page navigation via URL query parameters.

---

## 7. Main Dashboard Wireframe

```
┌────────────────────────────────────────────────────────────────────────┐
│  Intelligence Overview                                    [🔍 Search] │
│  Cricket analytics powered by 8,250+ historical matches               │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                 │
│  │ 5,734    │ │ 127      │ │ 8,250    │ │ 462      │  Summary Cards  │
│  │ Players  │ │ Teams    │ │ Matches  │ │ Venues   │                 │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘                 │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─── LIVE NOW ──────────────┐  ┌─── TOP PERFORMERS ─────────────┐   │
│  │                           │  │                                 │   │
│  │  🏏 IND vs AUS            │  │  Score:  ▸ V Kohli    95.2     │   │
│  │  T20I · 3rd Match        │  │  Bowl:   ▸ J Bumrah   92.8     │   │
│  │  IND 145/3 (16.2 ov)     │  │  AR:     ▸ B Stokes   88.5     │   │
│  │  RR: 8.91 · TGT: 178     │  │                                 │   │
│  │  🟢 LIVE · Updated 5s ago │  │  ─── by Format ───             │   │
│  │                           │  │  T20 │ T20I │ ODI │ Test        │   │
│  │  ─── Upcoming ───         │  │                                 │   │
│  │  ENG vs SA · 2:30 PM      │  └─────────────────────────────────┘   │
│  │  PAK vs NZ · 6:00 PM      │                                        │
│  └───────────────────────────┘  ┌─── RECENT RESULTS ─────────────┐   │
│                                  │  IND beat AUS by 7 wkts (T20I) │   │
│  ┌─── VENUE INSIGHTS ─────────┐ │  ENG beat SA by 120 runs (Test)│   │
│  │  MCG · 85 matches          │  │  AUS beat PAK by 3 wkt (ODI)   │   │
│  │  Avg 1st inn: 168          │  │  NZ beat WI by 5 wkts (T20I)   │   │
│  │  Chase win: 55%            │  └─────────────────────────────────┘   │
│  │  Pace wickets: 58%         │                                        │
│  └────────────────────────────┘                                        │
│                                                                        │
│  ┌─── DATA SOURCE ────────────────────────────────────────────────┐   │
│  │ Historical: Cricsheet · Live: CricketData.org                  │   │
│  │ Platform analytics calculated from 4.13M match deliveries      │   │
│  └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### Dashboard Reasoning

1. **Summary cards** provide immediate scale awareness
2. **Live Now** section is prominent but graceful when no live matches exist
3. **Top Performers** shows form-scored leaders — the platform's unique value
4. **Recent Results** provides recency context
5. **Venue Insights** grounds the analytics in physical spaces
6. **Data Source** transparency builds trust

The dashboard answers the five key questions within seconds:
- What's happening live? → Live Now
- Who's performing? → Top Performers
- What happened recently? → Recent Results
- What's the scale? → Summary Cards
- Where can I drill down? → Everything is clickable

---

## 8. Live Center Wireframe

```
┌────────────────────────────────────────────────────────────────────────┐
│  Live Match Centre                                    🟢 Live · 5s ago│
│  Real-time match data from CricketData.org                            │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─── LIVE NOW ──────────────────────────────────────────────────┐   │
│  │                                                                │   │
│  │  ┌────────────────────────┐  ┌────────────────────────┐       │   │
│  │  │  🏏 IND vs AUS         │  │  🏏 ENG vs SA          │       │   │
│  │  │  T20I · 3rd Match      │  │  Test · 2nd Match      │       │   │
│  │  │                        │  │                        │       │   │
│  │  │  🇮🇳 IND  145/3 (16.2) │  │  🏴󠁧󠁢󠁥󠁮󠁧󠁿 ENG 312/6 (89.0)│       │   │
│  │  │  🇦🇺 AUS  177/8 (20)   │  │  🇿🇦 SA   198/10 (67.3)│       │   │
│  │  │                        │  │                        │       │   │
│  │  │  RR: 8.91              │  │  Day 2 · Stumps         │       │   │
│  │  │  TGT: 178 · RRR: 7.73 │  │  ENG lead by 114        │       │   │
│  │  │  🟢 INNINGS 2          │  │  🟡 STUMPS              │       │   │
│  │  │                        │  │                        │       │   │
│  │  │  [View Details →]      │  │  [View Details →]      │       │   │
│  │  └────────────────────────┘  └────────────────────────┘       │   │
│  │                                                                │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── UPCOMING ──────────────────────────────────────────────────┐   │
│  │  PAK vs NZ · T20I · 2:30 PM · Lahore                         │   │
│  │  WI vs BAN · ODI · 6:00 PM · Bridgetown                      │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── RECENTLY COMPLETED ────────────────────────────────────────┐   │
│  │  AUS beat IND by 12 runs (T20I) · Melbourne · 2 hours ago     │   │
│  │  SA drew with ENG (Test) · Lord's · Day 1 complete            │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  Data: CricketData.org · Auto-refresh: 30s · Source may be delayed    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Player Detail Wireframe

```
┌────────────────────────────────────────────────────────────────────────┐
│  ← Back to Players                                                     │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  VIRAT KOHLI                                                   │   │
│  │  India · Right-hand Bat · Right-arm Medium                     │   │
│  │                                                                 │   │
│  │  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐                          │   │
│  │  │ 59.2│  │ 9346│  │54.0 │  │ 138 │  Form  Runs  Avg   SR   │   │
│  │  │Form │  │Runs │  │ Avg │  │ SR  │                          │   │
│  │  └─────┘  └─────┘  └─────┘  └─────┘                          │   │
│  │                                                                 │   │
│  │  [All] [T20] [T20I] [ODI] [Test]    ← Format Switcher         │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── CAREER SUMMARY ────────────────────────────────────────────┐   │
│  │  Matches │ Innings │ Runs    │ Average │ SR      │ HS         │   │
│  │  523     │ 490     │ 27,745  │ 53.5    │ 93.2    │ 254*       │   │
│  │                                                                │   │
│  │  100s │ 50s  │ 4s    │ 6s   │ Bound% │ Dot%                  │   │
│  │  72   │ 138  │ 2,548 │ 312  │ 58.2%  │ 42.1%                 │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── CAREER PROGRESSION ────────────────────────────────────────┐   │
│  │  ▁▃▅▇█▇▆▅▇█▇▆▅▇█▇▅▇█▇▆▅▇█▇                              │   │
│  │  2008  2010  2012  2014  2016  2018  2020  2022  2024         │   │
│  │  [Recharts Line Chart: Runs per year by format]               │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── BY OPPONENT ─────────────┐  ┌─── BY VENUE ────────────────┐   │
│  │  vs Australia   2,847 runs  │  │  MCG      1,205 runs (avg 62)│   │
│  │  vs England     2,103 runs  │  │  Lord's     892 runs (avg 55)│   │
│  │  vs South Africa 1,876 runs │  │  Eden Gardens 756 runs (avg 48│   │
│  │  vs Pakistan    1,654 runs  │  │  Wankhede    634 runs (avg 58)│   │
│  └─────────────────────────────┘  └──────────────────────────────┘   │
│                                                                        │
│  ┌─── MATCH HISTORY ─────────────────────────────────────────────┐   │
│  │  Date       │ Match              │ Runs │ SR    │ Result       │   │
│  │  2024-01-15 │ IND vs AUS T20I   │ 82   │ 158.4 │ Won by 7wkt │   │
│  │  2024-01-12 │ IND vs ENG ODI    │ 113  │ 98.3  │ Won by 46runs│   │
│  │  ...                                                        │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── AFFILIATIONS ──────────────────────────────────────────────┐   │
│  │  🏏 Royal Challengers Bangalore · IPL · 2008-present          │   │
│  │  🏏 India · T20I/ODI/Test · 2008-present                      │   │
│  └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### Player Detail Key Design Decisions

1. **Format Switcher** at the top — switches ALL statistics below
2. **Career Progression** uses Recharts (already installed)
3. **Cross-format comparison** possible via "All" format view
4. **Click any match** → navigates to Match Detail
5. **Click any opponent** → navigates to Player vs Opponent filtered view
6. **Click any venue** → navigates to Venue Detail

---

## 10. Team Detail Wireframe

```
┌────────────────────────────────────────────────────────────────────────┐
│  ← Back to Teams                                                       │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  🇮🇳 INDIA                          National Team              │   │
│  │  #1 in T20I · #2 in ODI · #1 in Test                          │   │
│  │                                                                 │   │
│  │  [All] [T20I] [ODI] [Test]    ← Format Switcher                │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── OVERALL ─────────┐  ┌─── WIN/LOSS ────────────────────────┐   │
│  │  Matches: 87         │  │  Won: 52  Lost: 28  Draw: 5  NR: 2 │   │
│  │  Win Rate: 63.4%     │  │  ████████████████░░░░  63.4%        │   │
│  │  Avg Score: 172      │  │                                     │   │
│  │  Avg Econ: 7.8       │  │  Chasing: 68.5% win                 │   │
│  └─────────────────────┘  │  Defending: 76.2% win                │   │
│                            └─────────────────────────────────────┘   │
│                                                                        │
│  ┌─── HEAD-TO-HEAD ──────────────────────────────────────────────┐   │
│  │  Opponent    │ Mat │ Won │ Lost │ Draw │ Win%                  │   │
│  │  Australia   │ 49  │ 28  │ 18   │ 3    │ 57.1%                │   │
│  │  England     │ 45  │ 25  │ 17   │ 3    │ 55.6%                │   │
│  │  South Africa│ 38  │ 20  │ 15   │ 3    │ 52.6%                │   │
│  │  Pakistan    │ 35  │ 22  │ 10   │ 3    │ 62.9%                │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── CAREER PROGRESSION ────────────────────────────────────────┐   │
│  │  [Recharts: Win rate by year]                                 │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── RECENT MATCHES ────────────────────────────────────────────┐   │
│  │  IND beat AUS by 7 wkts (T20I) · MCG · 2024-01-15            │   │
│  │  IND beat ENG by 46 runs (ODI) · Oval · 2024-01-12            │   │
│  │  ...                                                          │   │
│  └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Match Detail Wireframe

```
┌────────────────────────────────────────────────────────────────────────┐
│  ← Back to Matches                                                     │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  INDIA vs AUSTRALIA                                            │   │
│  │  T20I · 3rd Match · MCG, Melbourne · 2024-01-15               │   │
│  │                                                                 │   │
│  │  🇮🇳 INDIA won by 7 wickets                                    │   │
│  │  Toss: India elected to bowl                                    │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── INNINGS SUMMARY ───────────────────────────────────────────┐   │
│  │                                                                │   │
│  │  🇦🇺 AUSTRALIA                                                │   │
│  │  177/8 (20 overs) · RR: 8.85                                   │   │
│  │  ──────────────────────────────────────────                   │   │
│  │  Warner 45 (32) · Maxwell 38 (24) · Head 29 (22)             │   │
│  │  Bumrah 3/28 · Siraj 2/34 · Axar 1/22                        │   │
│  │                                                                │   │
│  │  🇮🇳 INDIA                                                     │   │
│  │  178/3 (18.4 overs) · RR: 9.52                                 │   │
│  │  ──────────────────────────────────────────                   │   │
│  │  Kohli 82* (52) · Gill 51 (38) · Rahul 28 (22)              │   │
│  │  Zampa 1/38 · Hazlewood 1/32 · Starc 1/40                    │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── BATTING SCORECARD ─────────────────────────────────────────┐   │
│  │  [Tab: Australia] [Tab: India]                                 │   │
│  │                                                                │   │
│  │  Batter         │ R   │ B  │ 4s │ 6s │ SR     │ Dismissal     │   │
│  │  DA Warner      │ 45  │ 32 │ 5  │ 1  │ 140.6  │ c Rahul b Bumrah│  │
│  │  TM Head        │ 29  │ 22 │ 4  │ 0  │ 131.8  │ b Siraj       │   │
│  │  ...            │     │    │    │    │        │               │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── BOWLING SCORECARD ─────────────────────────────────────────┐   │
│  │  Bowler         │ O   │ M  │ R   │ W  │ Econ  │ SR            │   │
│  │  JJ Bumrah      │ 4.0 │ 0  │ 28  │ 3  │ 7.00  │ 13.3         │   │
│  │  Mohammed Siraj │ 4.0 │ 0  │ 34  │ 2  │ 8.50  │ 20.0         │   │
│  │  ...            │     │    │     │    │       │              │   │
│  └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Competition Detail Wireframe

```
┌────────────────────────────────────────────────────────────────────────┐
│  ← Back to Competitions                                                │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  INDIAN PREMIER LEAGUE                                         │   │
│  │  T20 · BCCI · 17 seasons · 1,243 matches                      │   │
│  │                                                                 │   │
│  │  [2024] [2023] [2022] [2021] ...    ← Season Selector          │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── SEASON 2024 ──────────────────────────────────────────────┐   │
│  │                                                                │   │
│  │  Teams │ Matches │ Top Run Scorer │ Top Wicket Taker           │   │
│  │  10    │ 74      │ V Kohli (741)  │ Bumrah (20)               │   │
│  │                                                                │   │
│  │  ┌─── STANDINGS ─────────────────────────────────────────┐    │   │
│  │  │ # │ Team          │ P  │ W  │ L  │ Pts │ NRR          │    │   │
│  │  │ 1 │ KKR           │ 14 │ 9  │ 5  │ 18  │ +1.428       │    │   │
│  │  │ 2 │ SRH           │ 14 │ 8  │ 6  │ 17  │ +0.415       │    │   │
│  │  │ ...                                                   │    │   │
│  │  └────────────────────────────────────────────────────────┘    │   │
│  │                                                                │   │
│  │  ┌─── TOP PERFORMERS ─────────────────────────────────────┐   │   │
│  │  │  Runs: Kohli 741 · Ruturaj 583 · Abhishek 480          │   │   │
│  │  │  Wkts: Bumrah 20 · Chahal 18 · Varun 17                │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 13. Venue Detail Wireframe

```
┌────────────────────────────────────────────────────────────────────────┐
│  ← Back to Venues                                                      │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  📍 MELBOURNE CRICKET GROUND                                   │   │
│  │  Melbourne, Australia · Capacity: 100,024                      │   │
│  │                                                                 │   │
│  │  [All] [T20] [T20I] [ODI] [Test]    ← Format Switcher         │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── KEY STATS ─────────────────────────────────────────────────┐   │
│  │  85 Matches │ 168 Avg 1st │ 155 Avg 2nd │ 55% Chase Win      │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─── SCORE PROFILE ───────┐  ┌─── PACE vs SPIN ───────────────┐   │
│  │  Highest: 223            │  │  Pace: ██████████░░ 58%         │   │
│  │  Lowest: 78              │  │  Spin: ████████░░░░ 42%         │   │
│  │  Avg 1st inn: 168        │  │                                │   │
│  │  Avg 2nd inn: 155        │  │  ─── Phase Scoring ───         │   │
│  └─────────────────────────┘  │  Powerplay: 42.5 avg            │   │
│                                │  Middle: 58.2 avg               │   │
│  ┌─── MATCH HISTORY ───────┐  │  Death: 67.8 avg                │   │
│  │  Date  │ Match          │  └────────────────────────────────┘   │
│  │  ...   │ ...            │                                        │
│  └─────────────────────────┘                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Rankings Architecture

### 14.1 Two Distinct Ranking Sources

```
┌─────────────────────────────────────────────────┐
│  PLATFORM RANKINGS                              │
│  Source: Computed from 8,250-match analytics     │
│  Method: Weighted avg + SR + form composite      │
│  Always available                                │
│  Clearly labeled "Platform Rating"               │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  OFFICIAL RANKINGS                               │
│  Source: External provider (if available)         │
│  Currently: NOT available (free tier limitation)  │
│  Clearly labeled with source attribution          │
│  Shown only when genuinely sourced externally     │
└─────────────────────────────────────────────────┘
```

### 14.2 Rankings Wireframe

```
┌────────────────────────────────────────────────────────────────────────┐
│  Rankings                                                              │
│  Platform-computed player rankings based on our analytics              │
│                                                                        │
│  Source: [Platform ✓] [ICC ○]     ← Radio toggle (ICC grayed if N/A) │
│                                                                        │
│  Format: [T20] [T20I] [ODI] [Test]                                    │
│  Category: [Batting] [Bowling] [All-rounder]                          │
│                                                                        │
│  ┌─── RANKINGS TABLE ────────────────────────────────────────────┐   │
│  │  #  │ Player         │ Team │ Rating │ Runs/Avg │ SR  │ Form  │   │
│  │  1  │ V Kohli        │ IND  │ 95.2   │ 9,346    │138.4│ 85.3  │   │
│  │  2  │ JP Duminy      │ SA   │ 91.8   │ 2,103    │135.2│ 78.1  │   │
│  │  ...                                                         │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  Note: Platform ratings are computed using weighted composite of       │
│  batting average (40%), strike rate (30%), and form score (30%).       │
│  Minimum 5 innings required for inclusion.                            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 15. Global Filter Architecture

### 15.1 Filter Types

| Filter | Scope | Values | Persistence |
|---|---|---|---|
| Format | Global | All, T20, T20I, ODI, Test | URL query param |
| Competition | Page-specific | Dynamic from API | URL query param |
| Season | Page-specific | Dynamic from API | URL query param |
| Year | Page-specific | Dynamic range | URL query param |
| Team | Page-specific | Dynamic from API | URL query param |
| Player | Search | Dynamic from API | URL query param |
| Category | Rankings | batting, bowling, allrounder | URL query param |

### 15.2 Filter Behavior

- **Format filter persists** across page navigation via URL query params
- **Competition/Season filters** are page-specific and reset on navigation
- **Empty results** show a clear message, not a blank page
- **Invalid combinations** are handled gracefully (e.g., Test + no season)
- **Mobile**: Filters collapse into a drawer/sheet

### 15.3 URL Strategy

```
/players?virat-kohli&format=ODI
/players/:id?format=ODI&year=2024
/teams/:id?format=Test
/teams/:id/head-to-head/:opponent_id?format=ODI
/matches?format=T20I&year=2024
/competitions/:id?season=2024
/rankings?format=ODI&category=batting
/live
```

---

## 16. Search Architecture

### 16.1 Global Search Experience

Triggered by:
- Keyboard shortcut (Ctrl+K / Cmd+K)
- Search icon in header
- Search input in sidebar

### 16.2 Search Features

- **Autocomplete** with debounced API calls
- **Entity type labels** (Player, Team, Match, Venue, Competition)
- **Recent searches** stored in localStorage
- **Keyboard navigation** (arrow keys, Enter to select, Esc to close)
- **Result grouping** by entity type
- **Minimum 2 characters** before search triggers

### 16.3 Search Results Structure

```
┌──────────────────────────────────────────────────┐
│  🔍 Search cricket intelligence...                │
├──────────────────────────────────────────────────┤
│                                                   │
│  PLAYERS                                          │
│  👤 Virat Kohli · India · Batsman                 │
│  👤 KL Rahul · India · Wicketkeeper               │
│                                                   │
│  TEAMS                                            │
│  🛡️ India · National Team                         │
│  🛡️ Royal Challengers Bangalore · Franchise       │
│                                                   │
│  MATCHES                                          │
│  🏏 IND vs AUS · T20I · 2024-01-15               │
│                                                   │
│  VENUES                                           │
│  📍 Melbourne Cricket Ground · Australia           │
│                                                   │
│  No results for "xyz"                             │
└──────────────────────────────────────────────────┘
```

---

## 17. Data Source/Provenance UX

Every data section should show:

```
┌──────────────────────────────────────────┐
│  Data Source                              │
│  Historical: Cricsheet (8,250 matches)   │
│  Live: CricketData.org (when available)  │
│  Analytics: Platform-computed            │
│  Last updated: 2 minutes ago             │
└──────────────────────────────────────────┘
```

For specific sections:
- **Player stats**: "Based on Cricsheet historical data"
- **Live scores**: "Live data: CricketData.org · May be delayed by a few minutes"
- **Rankings**: "Platform Rating · Computed from historical analytics"
- **ICC Rankings** (if available): "Official ICC rankings via CricketData.org"

---

## 18. Responsive Design Strategy

### 18.1 Breakpoints

| Breakpoint | Width | Layout |
|---|---|---|
| Mobile | <768px | Single column, bottom nav or hamburger |
| Tablet | 768-1024px | Two columns, collapsed sidebar |
| Desktop | >1024px | Full sidebar + content |
| Wide | >1440px | Extended content width |

### 18.2 Mobile Behavior

- **Sidebar** → Hamburger menu / bottom navigation
- **Dashboard** → Stack cards vertically
- **Tables** → Horizontal scroll with sticky first column
- **Filters** → Bottom sheet / drawer
- **Player Detail** → Stack sections vertically
- **Live scores** → Compact card format
- **Charts** → Full width, simplified

### 18.3 Desktop Behavior

- **Fixed sidebar** (256px)
- **Content area** max-width 1280px
- **Multi-column layouts** for dashboards
- **Side-by-side comparisons** for head-to-head
- **Sticky headers** for tables

---

## 19. Design System

### 19.1 Color Palette (Dark Theme)

Based on the FIFA reference — premium dark sports dashboard:

```css
/* Background */
--bg-primary: #0a0e17        /* Deep navy-black */
--bg-secondary: #111827      /* Dark card background */
--bg-surface: #1a2235        /* Elevated surface */
--bg-hover: #1f2b42          /* Hover state */

/* Text */
--text-primary: #f1f5f9      /* Primary text */
--text-secondary: #94a3b8    /* Secondary text */
--text-muted: #64748b        /* Muted text */

/* Brand */
--brand-primary: #0ea5e9     /* Sky blue (existing brand-500) */
--brand-secondary: #38bdf8   /* Lighter blue */
--brand-glow: rgba(14, 165, 233, 0.15)  /* Glow effect */

/* Status */
--live-green: #22c55e        /* Live indicator */
--win-green: #10b981         /* Win result */
--loss-red: #ef4444          /* Loss result */
--draw-amber: #f59e0b        /* Draw/tie */

/* Cricket-specific */
--batting-blue: #3b82f6      /* Batting stats */
--bowling-red: #ef4444       /* Bowling stats */
--form-gradient: linear-gradient(135deg, #0ea5e9, #8b5cf6)  /* Form badge */
```

### 19.2 Typography

```css
Font Family: 'Inter', system-ui, sans-serif
Monospace: 'JetBrains Mono', monospace (for statistics)

Heading 1: 2rem / 700 / -0.02em tracking
Heading 2: 1.25rem / 600
Heading 3: 1rem / 600
Body: 0.875rem / 400
Small: 0.75rem / 500
Stat Large: 2rem / 700 (for key metrics)
Stat Medium: 1.25rem / 700
```

### 19.3 Component Styles

```css
/* Cards */
.card {
  background: var(--bg-secondary);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 1.5rem;
}

/* Stat badges */
.stat-badge {
  background: var(--bg-surface);
  border-radius: 8px;
  padding: 0.75rem;
  text-align: center;
}

/* Format chips */
.format-chip {
  padding: 0.375rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

/* Live indicator */
.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--live-green);
  animation: pulse 2s infinite;
}

/* Tables */
table rows alternate with subtle background difference
hover state highlights row
sticky header on scroll
```

### 19.4 Spacing Scale

```
4px  → xs
8px  → sm
12px → md
16px → lg
24px → xl
32px → 2xl
48px → 3xl
```

### 19.5 Shadows

```css
Shadow-sm: 0 1px 2px rgba(0,0,0,0.3)
Shadow-md: 0 4px 6px rgba(0,0,0,0.4)
Shadow-lg: 0 10px 15px rgba(0,0,0,0.5)
Shadow-glow: 0 0 20px rgba(14,165,233,0.15)  /* Brand glow for emphasis */
```

---

## 20. Frontend State Management Strategy

### 20.1 Recommendation: TanStack React Query (Already Installed)

React Query is already installed and configured. Use it.

**Current state**: QueryClientProvider wraps the app but no page uses `useQuery`.

**Target state**: Every data-fetching operation uses React Query.

### 20.2 Data Fetching Architecture

```
┌──────────────────────────────────────────────────┐
│  React Query Cache Layers                         │
├──────────────────────────────────────────────────┤
│                                                    │
│  Static Entities (teams, venues, competitions)     │
│  → staleTime: 1 hour                               │
│  → Cache indefinitely                               │
│                                                    │
│  Historical Analytics (player stats, rankings)     │
│  → staleTime: 5 minutes                            │
│  → refetchOnWindowFocus: false                      │
│                                                    │
│  Live Data                                         │
│  → staleTime: 30 seconds                           │
│  → refetchInterval: 30000                          │
│  → refetchIntervalInBackground: true                │
│                                                    │
│  Rankings (Platform)                               │
│  → staleTime: 1 hour                               │
│  → Manual refresh only                              │
│                                                    │
│  Search                                            │
│  → staleTime: 30 seconds                           │
│  → Debounced (300ms)                                │
│                                                    │
└──────────────────────────────────────────────────┘
```

### 20.3 Standard State Patterns

Every data component should handle:

```typescript
// Using React Query
const { data, isLoading, isError, error, refetch } = useQuery({
  queryKey: ['player', id, format],
  queryFn: () => playerApi.get(id, format),
  staleTime: 5 * 60 * 1000,
})

// States:
// isLoading → Skeleton/spinner
// isError → Error card with retry button
// data === null/empty → Empty state with helpful message
// data → Render content
```

### 20.4 Global State

- **Format selection**: URL query param (`?format=ODI`), read via `useSearchParams`
- **No Redux/Zustand needed**: React Query + URL params + React Context is sufficient
- **Search state**: Local component state + localStorage for recent searches
- **Theme**: CSS variables, no JS state needed

---

## 21. Data Fetching/Caching Strategy

### 21.1 API Client Upgrade

Replace raw `fetch` with React Query hooks:

```typescript
// Current (raw fetch)
useEffect(() => {
  async function load() {
    const data = await playerApi.get(id)
    setPlayer(data)
  }
  load()
}, [id])

// Target (React Query)
const { data: player, isLoading, error } = useQuery({
  queryKey: ['player', id, format],
  queryFn: () => fetchJson(`/players/${id}?format=${format}`),
})
```

### 21.2 Prefetching Strategy

- **Hover on player card** → Prefetch player detail
- **Navigate to team** → Prefetch team analytics
- **Format switch** → Prefetch new format data before switch completes
- **Dashboard load** → Parallel prefetch top players, teams, matches

### 21.3 Cache Invalidation

- **Format change**: Invalidate format-specific queries
- **Manual refresh**: `queryClient.invalidateQueries(['rankings'])`
- **Live data**: Handled by refetchInterval, no manual invalidation needed

---

## 22. URL/Deep Linking Strategy

### 22.1 Route Structure

```
/                                          Dashboard
/live                                      Live Center
/players                                   Player Directory
/players/:id                               Player Detail
/players/:id?format=ODI                    Player Detail (ODI view)
/players/:id?format=Test&year=2024         Player Detail (Test, 2024)
/teams                                     Team Directory
/teams/:id                                 Team Detail
/teams/:id?format=ODI                      Team Detail (ODI view)
/teams/:id/head-to-head/:opponentId        Head-to-Head
/matches                                   Match Browser
/matches/:id                               Match Detail
/competitions                              Competition List
/competitions/:id                          Competition Detail
/competitions/:id?season=2024              Competition Season View
/venues                                    Venue Directory
/venues/:id                                Venue Detail
/venues/:id?format=Test                    Venue Detail (Test view)
/matchups                                  Matchup Analytics
/rankings                                  Rankings
/rankings?format=ODI&category=batting      Rankings (ODI Batting)
```

### 22.2 Query Parameters

| Parameter | Type | Default | Scope |
|---|---|---|---|
| `format` | string | "T20" | Global (persists) |
| `competition` | string | null | Page-specific |
| `season` | string | null | Page-specific |
| `year` | number | null | Page-specific |
| `category` | string | "batting" | Rankings |
| `sort` | string | context-dependent | Tables |
| `q` | string | null | Search |

---

## 23. Loading/Error/Empty/Degraded States

### 23.1 State Matrix

| State | Visual Treatment | Action |
|---|---|---|
| **Loading** | Skeleton placeholder matching layout | None (auto-resolves) |
| **Error** | Red-tinted card with icon + message | Retry button |
| **Empty** | Illustration + helpful message | Suggestion/link |
| **Stale** | Subtle indicator, data still shown | Background refresh |
| **Partial** | Show available data, mark missing | Graceful degradation |
| **Offline** | Banner + cached data | Manual retry |

### 23.2 Live-Specific States

| State | Visual Treatment |
|---|---|
| **Live** | Green pulsing dot + "LIVE" badge |
| **Recently Updated** | Timestamp "Updated 5s ago" |
| **Stale** | Amber indicator "Data may be delayed" |
| **Provider Unavailable** | "Live data temporarily unavailable" |
| **No Live Matches** | Empty state with upcoming fixtures |

### 23.3 Independent Card Degradation

The dashboard should NOT fail entirely if one API call fails:

```
┌─────────────────────────────────────────────┐
│  Dashboard loaded successfully               │
│                                              │
│  ┌─────────────┐  ┌─────────────┐           │
│  │ Top Players  │  │ ⚠️ Teams     │           │
│  │ ✅ Loaded    │  │ Failed to   │           │
│  │              │  │ load.       │           │
│  │              │  │ [Retry]     │           │
│  └─────────────┘  └─────────────┘           │
│                                              │
│  ┌─────────────┐  ┌─────────────┐           │
│  │ Matches ✅   │  │ Venues ✅    │           │
│  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────┘
```

---

## 24. Accessibility Considerations

- **Color contrast**: All text must meet WCAG AA (4.5:1 for body text)
- **Keyboard navigation**: All interactive elements focusable
- **Screen reader**: Meaningful alt text for icons, ARIA labels
- **Focus visible**: Clear focus ring on all interactive elements
- **Semantic HTML**: Proper heading hierarchy, landmarks
- **Motion**: Respect `prefers-reduced-motion`
- **Data tables**: Proper `<th>`, `scope`, caption

---

## 25. Performance Considerations

### 25.1 Frontend Performance Targets

| Metric | Target |
|---|---|
| First Contentful Paint | <1.5s |
| Largest Contentful Paint | <2.5s |
| Time to Interactive | <3s |
| Bundle Size (gzipped) | <200KB |
| Route Transitions | <200ms |

### 25.2 Optimization Strategy

- **Code splitting**: React.lazy for route-level components
- **Image optimization**: Use initials/avatars, not photos
- **Virtual scrolling**: For large lists (5,734 players)
- **Debounced search**: 300ms debounce
- **Parallel API calls**: Use Promise.all for dashboard
- **Skeleton loading**: Better perceived performance than spinners

### 25.3 Bundle Analysis

Current dependencies that add bundle size:
- `recharts` (~200KB) — only use where charts are needed
- `@tanstack/react-query` (~30KB) — essential, worth it
- `lucide-react` — tree-shakeable, minimal impact

---

## 26. Existing Components to Reuse

| Component | Location | Verdict |
|---|---|---|
| `StatCard` | Dashboard.tsx | ✅ Extract and reuse |
| `FormBadge` | Dashboard.tsx | ✅ Extract and reuse |
| `StatBox` | PlayerDetail.tsx | ✅ Extract and reuse |
| `.card` / `.card-hover` | index.css | ✅ Keep |
| `.badge` variants | index.css | ✅ Keep |
| `.btn-primary` / `.btn-secondary` | index.css | ✅ Keep |
| `.stat-value` / `.stat-label` | index.css | ✅ Keep |
| `Layout` | Layout.tsx | ⚠️ Major refactor needed (dark theme, mobile) |
| `api.ts` | services/ | ⚠️ Keep, add React Query wrappers |

---

## 27. Components to Refactor

| Component | Issue | Refactor Needed |
|---|---|---|
| `Layout.tsx` | Light theme, no mobile nav | Dark theme + responsive sidebar |
| `Dashboard.tsx` | T20-only, no live, no charts | Multi-format, live area, charts |
| `PlayerDetail.tsx` | No format switcher, no charts | Format switcher, Recharts integration |
| `Players.tsx` | Basic list, no search | Search, multi-format, better cards |
| `Teams.tsx` | Basic list | Search, format filter, better cards |
| `Matches.tsx` | Basic list | Better filtering, pagination, link to detail |
| `Venues.tsx` | Basic list | Better cards, format filter |
| `Rankings.tsx` | Basic table | Platform vs ICC distinction, better visual |
| `api.ts` | Raw fetch | React Query wrappers |

---

## 28. Components to Create

### 28.1 Layout Components

| Component | Purpose | Data Source |
|---|---|---|
| `AppLayout` | Dark theme layout with responsive sidebar | — |
| `TopBar` | Global filters (format, competition, season) | URL params |
| `SearchOverlay` | Global search modal (Ctrl+K) | Players/Teams/Matches API |
| `FormatSelector` | Reusable format tab bar | URL params |
| `MobileNav` | Bottom navigation for mobile | — |

### 28.2 Dashboard Components

| Component | Purpose | Data Source |
|---|---|---|
| `LiveNowCard` | Live match widget | `GET /api/live` |
| `TopPerformersWidget` | Form-scored leaders | `GET /api/players?sort_by=form_score` |
| `RecentResultsWidget` | Latest match results | `GET /api/matches?limit=5` |
| `VenueInsightsWidget` | Venue summary cards | `GET /api/venues?limit=5` |
| `UpcomingFixturesWidget` | Upcoming matches | `GET /api/live` (filtered) |

### 28.3 Player Components

| Component | Purpose | Data Source |
|---|---|---|
| `PlayerHeader` | Name, role, team, form score | `GET /api/players/{id}` |
| `PlayerCareerStats` | Career batting/bowling grid | `GET /api/players/{id}` |
| `PlayerCareerProgression` | Line chart over years | `GET /api/analytics/player/{id}/by-year` |
| `PlayerByOpponent` | Opponent stats table | `GET /api/analytics/player/{id}/by-opponent` |
| `PlayerByVenue` | Venue stats table | `GET /api/analytics/player/{id}/by-venue` |
| `PlayerByCompetition` | Competition stats | `GET /api/analytics/player/{id}/by-competition` |
| `PlayerMatchHistory` | Match history table | `GET /api/analytics/player/{id}/history` |
| `PlayerAffiliations` | Team affiliations list | `GET /api/players/{id}/affiliations` |

### 28.4 Team Components

| Component | Purpose | Data Source |
|---|---|---|
| `TeamHeader` | Name, type, format stats | `GET /api/teams/{id}` |
| `TeamWinLossChart` | Win/Loss/Draw visualization | `GET /api/analytics/team/{id}/overview` |
| `HeadToHeadTable` | Opponent comparison table | `GET /api/analytics/team/{id}/head-to-head` |
| `TeamMatchHistory` | Recent matches | `GET /api/analytics/team/{id}/history` |

### 28.5 Match Components

| Component | Purpose | Data Source |
|---|---|---|
| `MatchHeader` | Teams, result, venue, date | `GET /api/matches/{id}` |
| `InningsSummary` | Innings overview cards | `GET /api/analytics/match/{id}/scorecard` |
| `BattingScorecard` | Batting table | `GET /api/analytics/match/{id}/scorecard` |
| `BowlingScorecard` | Bowling table | `GET /api/analytics/match/{id}/scorecard` |

### 28.6 Live Components

| Component | Purpose | Data Source |
|---|---|---|
| `LiveMatchCard` | Compact live match card | `GET /api/live` |
| `LiveScoreWidget` | Detailed live score | `GET /api/live/{id}` |
| `LiveIndicator` | Pulsing green dot | — |

### 28.7 Shared UI Components

| Component | Purpose |
|---|---|
| `Skeleton` | Loading skeleton variants |
| `ErrorCard` | Error state with retry |
| `EmptyState` | Empty state with message |
| `DataTable` | Reusable sortable table |
| `StatGrid` | Grid of stat boxes |
| `FormatBadge` | Format-specific colored badge |
| `ResultBadge` | Win/Loss/Draw badge |
| `SearchInput` | Debounced search input |
| `Pagination` | Page navigation |
| `FilterBar` | Reusable filter row |
| `PageHeader` | Consistent page headers |

---

## 29. Features Explicitly Deferred

| Feature | Reason |
|---|---|
| Ball-by-ball viewer | Deliveries table removed from production |
| User authentication | Not required for current product |
| Social features | Out of scope |
| Betting/odds | Out of scope |
| Player photos | Requires image CDN/storage |
| Dark/light theme toggle | Dark only for now |
| Notification system | Future phase |
| Offline PWA | Future phase |
| Internationalization | English only for now |
| Historical ball-by-ball charts | Data not available in serving DB |
| News/RSS feed | No real backend; mock data removed |
| Complex micro-interactions | Focus on data density first |

---

## 30. Backend Gaps Required for Future Frontend Features

### 30.1 CRITICAL (Required for Phase 6.2B)

None — the existing 42 endpoints cover all planned features.

### 30.2 NICE TO HAVE

| Gap | Impact | Work Required |
|---|---|---|
| Player search endpoint | Better search UX | Add `GET /api/search?q=` |
| Team search endpoint | Better search UX | Include in search endpoint |
| Match search endpoint | Better search UX | Include in search endpoint |
| Match list with scorecard summary | Match browser UX | Lightweight scorecard in list response |
| Competition standings endpoint | Competition page | Derive from match data |
| Player photo URLs | Visual richness | External CDN + player photos table |

### 30.3 FUTURE

| Gap | Impact |
|---|---|
| Pagination for match history | Large result sets |
| Year-by-year competition data | Season comparison |
| Partnership data | Advanced scorecards |
| Phase-by-phase team data | Tactical analysis |
| Powerplay/death overs aggregation | T20/ODI analysis |

---

## 31. Component Inventory

### 31.1 Layout Components

| Component | Purpose | Data Source | API | Responsive | Reusable |
|---|---|---|---|---|---|
| AppLayout | Dark sidebar + content | — | — | Mobile drawer | Yes |
| TopBar | Global filters | URL params | — | Collapse on mobile | Yes |
| SearchOverlay | Global search modal | — | `/api/search` | Full screen mobile | Yes |
| Sidebar | Navigation | — | — | Drawer on mobile | Yes |

### 31.2 Dashboard Components

| Component | Purpose | Data Source | API | Responsive | Reusable |
|---|---|---|---|---|---|
| SummaryCards | 4 stat cards | Multiple | players/teams/matches/venues | 2x2 mobile | Yes |
| LiveNowWidget | Live match | Live service | `/api/live` | Stack on mobile | Yes |
| TopPerformersWidget | Form leaders | Players | `/api/players?sort=form` | Full width mobile | Yes |
| RecentResultsWidget | Latest matches | Matches | `/api/matches?limit=5` | Full width mobile | Yes |
| VenueInsightsWidget | Venue summary | Venues | `/api/venues?limit=5` | Full width mobile | Yes |

### 31.3 Player Components

| Component | Purpose | Data Source | API | Responsive | Reusable |
|---|---|---|---|---|---|
| PlayerHeader | Profile header | Player API | `/api/players/{id}` | Stack on mobile | No |
| FormatSwitcher | Format tabs | URL params | — | Scroll on mobile | Yes |
| PlayerCareerStats | Stat grid | Player API | `/api/players/{id}` | 2-col mobile | No |
| PlayerProgression | Line chart | Analytics | `/api/analytics/.../by-year` | Full width | Yes |
| PlayerByOpponent | Opponent table | Analytics | `/api/analytics/.../by-opponent` | Horizontal scroll | No |
| PlayerByVenue | Venue table | Analytics | `/api/analytics/.../by-venue` | Horizontal scroll | No |
| PlayerMatchHistory | History table | Analytics | `/api/analytics/.../history` | Horizontal scroll | No |
| PlayerAffiliations | Affiliations list | Player API | `/api/players/{id}/affiliations` | Stack on mobile | No |

### 31.4 Team Components

| Component | Purpose | Data Source | API | Responsive | Reusable |
|---|---|---|---|---|---|
| TeamHeader | Profile header | Team API | `/api/teams/{id}` | Stack on mobile | No |
| TeamWinLoss | Win/Loss visual | Analytics | `/api/analytics/.../overview` | Simplified mobile | No |
| HeadToHead | Opponent comparison | Analytics | `/api/analytics/.../head-to-head` | Horizontal scroll | No |
| TeamHistory | Match history | Analytics | `/api/analytics/.../history` | Horizontal scroll | No |

### 31.5 Match Components

| Component | Purpose | Data Source | API | Responsive | Reusable |
|---|---|---|---|---|---|
| MatchHeader | Match info | Match API | `/api/matches/{id}` | Stack on mobile | No |
| InningsSummary | Innings cards | Scorecard | `/api/analytics/.../scorecard` | Stack on mobile | No |
| BattingScorecard | Batting table | Scorecard | `/api/analytics/.../scorecard` | Horizontal scroll | Yes |
| BowlingScorecard | Bowling table | Scorecard | `/api/analytics/.../scorecard` | Horizontal scroll | Yes |

### 31.6 Live Components

| Component | Purpose | Data Source | API | Responsive | Reusable |
|---|---|---|---|---|---|
| LiveMatchCard | Compact match card | Live service | `/api/live` | Stack on mobile | Yes |
| LiveScoreDetail | Detailed live score | Live service | `/api/live/{id}` | Simplified mobile | No |
| LiveIndicator | Pulsing dot | — | — | Same on all | Yes |

### 31.7 Shared UI

| Component | Purpose | Responsive | Reusable |
|---|---|---|---|
| Skeleton | Loading states | Yes | Yes |
| ErrorCard | Error + retry | Yes | Yes |
| EmptyState | Empty + message | Yes | Yes |
| DataTable | Sortable table | H-scroll mobile | Yes |
| StatGrid | Metric grid | 2-col mobile | Yes |
| FormatBadge | Colored format chip | Yes | Yes |
| ResultBadge | Win/Loss/Draw chip | Yes | Yes |
| Pagination | Page navigation | Yes | Yes |
| FilterBar | Filter row | Drawer mobile | Yes |

---

## 32. Phase 6.2B Implementation Roadmap

### Phase 6.2B: Dark Theme + Core Layout (Foundation)

**Week 1**
1. Convert Tailwind config to dark theme
2. Rebuild Layout with dark sidebar + responsive mobile nav
3. Create shared UI components (Skeleton, ErrorCard, EmptyState, FormatBadge)
4. Create FormatSwitcher component
5. Update index.css with dark theme tokens

### Phase 6.2B: Dashboard Rebuild

**Week 1-2**
1. Rebuild Dashboard with multi-format support
2. Add TopPerformers widget (real API)
3. Add RecentResults widget (real API)
4. Add VenueInsights widget (real API)
5. Add LiveNow widget (real API with 30s refresh)
6. Add summary cards (real data)

### Phase 6.2B: React Query Integration

**Week 2**
1. Create React Query hooks for all API endpoints
2. Replace all raw fetch in pages with useQuery
3. Add proper loading/error/empty states everywhere
4. Add prefetching on hover/navigation

### Phase 6.2B: Player Experience

**Week 2-3**
1. Rebuild PlayerDetail with format switcher
2. Add PlayerProgression chart (Recharts)
3. Add PlayerByOpponent section
4. Add PlayerByVenue section
5. Add PlayerMatchHistory
6. Add PlayerAffiliations
7. Add search to Players list

### Phase 6.2B: Team & Match Experience

**Week 3**
1. Rebuild TeamDetail with real API data
2. Add HeadToHead section
3. Create MatchDetail page (new)
4. Add scorecard tables (batting + bowling)
5. Improve Matches list with pagination

### Phase 6.2B: Competition, Venue, Live, Rankings

**Week 3-4**
1. Create Competitions page (new)
2. Create CompetitionDetail page (new)
3. Rebuild VenueDetail with real API data
4. Rebuild Live page with real API + 30s refresh
5. Improve Rankings with Platform vs ICC distinction
6. Remove News page (mock data)

### Phase 6.2B: Search & Polish

**Week 4**
1. Implement global search overlay
2. Add deep linking / URL param persistence
3. Mobile responsive testing
4. Performance optimization
5. Accessibility audit
6. Final documentation

---

## 33. Definition of Done

Phase 6.2B is complete when:

- [ ] Dark premium theme is applied across all pages
- [ ] Layout is responsive (mobile, tablet, desktop)
- [ ] React Query is used for all data fetching
- [ ] All pages use real API data (no mock data)
- [ ] Format switcher works on Player, Team, Venue, Match pages
- [ ] Dashboard shows live matches, top performers, recent results
- [ ] Player Detail has career progression chart
- [ ] Match Detail page exists with scorecards
- [ ] Competitions page exists
- [ ] Live page integrates with real API + 30s refresh
- [ ] Rankings distinguish Platform vs ICC
- [ ] Global search works
- [ ] Loading/error/empty states are consistent
- [ ] No hardcoded mock data remains
- [ ] All routes support deep linking
- [ ] Performance targets met
- [ ] Frontend TypeScript passes
- [ ] Vite build passes
- [ ] Existing backend regression unaffected
- [ ] Documentation updated

---

*Document created: Phase 6.2A*
*Status: AUDIT & SPECIFICATION COMPLETE*
*Next Phase: 6.2B — Frontend Implementation*
