# Cricket Intelligence — Analytics

## Overview

All analytical statistics are precomputed by the data pipeline and stored in PostgreSQL. The frontend and API query precomputed results — no expensive calculations happen at request time.

## Format-Aware Phase Definitions

Phase definitions (powerplay, middle, death) vary by format. The system uses a central `FormatRules` configuration rather than hardcoded over ranges.

| Format | Powerplay | Middle | Death | Notes |
|--------|-----------|--------|-------|-------|
| T20/T20I | 0-5 (6 overs) | 6-14 (9 overs) | 15-19 (5 overs) | Standard T20 phases |
| ODI | 0-9 (10 overs) | 10-39 (30 overs) | 40-49 (10 overs) | First powerplay only |
| Test | n/a | n/a | n/a | Uses `general` phase (no T20-style phases) |

Configuration is stored in the `format_config` table and accessed via `data_pipeline.pipeline.format_config`.

## Player Batting Statistics

**Table:** `player_batting_stats`  
**Scope:** `(player_id, format, period)`  
**Period:** `career` (currently only career period)

### Core Metrics

| Metric | Formula |
|--------|---------|
| Batting Average | `runs / dismissals` |
| Strike Rate | `(runs / balls_faced) * 100` |
| Boundary % | `((fours + sixes) / balls_faced) * 100` |
| Dot Ball % | `(dot_balls / balls_faced) * 100` |

### Phase Metrics

- `powerplay_runs`, `powerplay_strike_rate`
- `middle_runs`, `middle_strike_rate`
- `death_runs`, `death_strike_rate`

Phase boundaries are format-aware (see above).

### Situational Metrics

- `chasing_runs`, `chasing_strike_rate` — Batting in 2nd innings
- `first_innings_runs`, `first_innings_strike_rate` — Batting in 1st innings

### Derived Metrics

- `fifties` — Innings with 50-99 runs
- `hundreds` — Innings with 100+ runs
- `consistency_score` — 100 × (1 - coefficient of variation), NaN if < 5 innings

## Player Bowling Statistics

**Table:** `player_bowling_stats`  
**Scope:** `(player_id, format, period)`

### Core Metrics

| Metric | Formula |
|--------|---------|
| Bowling Average | `runs_conceded / wickets` |
| Economy | `(runs_conceded / balls_bowled) * 6` |
| Strike Rate | `balls_bowled / wickets` |
| Dot Ball % | `(dot_balls / balls_bowled) * 100` |

### Phase Metrics

- `powerplay_overs/wickets/economy`
- `middle_overs/wickets/economy`
- `death_overs/wickets/economy`

## Player Form Score

**Table:** `player_form`  
**Scope:** `(player_id, format)`

An original composite metric measuring recent performance quality.

### Weighting Formula

| Component | Weight | Description |
|-----------|--------|-------------|
| Recent Performance | 35% | Average runs in last 10 innings |
| Consistency | 20% | 1 - coefficient of variation |
| Opposition Strength | 15% | Weighted average against bowling teams |
| Venue Performance | 10% | CV across venues (lower = better) |
| Match Situation | 10% | Chasing avg / overall avg ratio |
| Efficiency | 10% | Strike rate × average / 100 |

All components are min-max normalized within each format before weighting.

### Requirements

- Minimum 3 innings required
- Recent performance uses last 10 innings

## Team Performance

**Table:** `team_performance`  
**Scope:** `(team_id, format, period)`

### Metrics

- Win rate, wins, losses, ties, no results
- Average first/second innings scores
- Phase-wise scoring (powerplay, middle, death)
- Chasing win %, defending win %
- Batting/bowling/overall strength scores

### Strength Score Calculation

```
overall_strength = 0.35 × batting_strength + 0.35 × bowling_strength + 0.30 × win_rate
```

Where:
- `batting_strength` = min-max normalized avg batting score
- `bowling_strength` = min-max normalized inverse economy

## Venue Statistics

**Table:** `venue_stats`  
**Scope:** `(venue_id, format)`

### Metrics

- Average first/second innings scores
- Highest/lowest totals
- Chasing/defending win percentages
- Pace/spin wicket percentages (currently placeholder: 55%/45%)
- Phase-wise scoring averages
- Boundary frequency
- Toss impact percentages

## Batter-Bowler Matchups

**Table:** `batter_bowler_matchups`  
**Scope:** `(batter_id, bowler_id, format)`

### Metrics

- Total balls, runs, wickets
- Strike rate, batting average
- Dot balls, boundaries, sixes

Minimum 10 balls required for matchup to be computed.

## Win Probability (Future)

Not yet implemented. Planned features:
- Logistic Regression baseline
- Random Forest
- XGBoost
- Features: score, wickets, overs, target, RRR, CRR, venue, team strength

## Player Impact (Future)

Planned metric:
```
Impact = Actual Performance - Expected Performance
```

Context-dependent: format, over, wickets remaining, current score, venue, opposition.
