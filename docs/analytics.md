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

Wides do not count as balls faced; no-balls do. A dot ball requires a faced
delivery with zero total runs. A four or six marked `non_boundary` by
Cricsheet (all-run fours or overthrows) is not counted as a boundary.

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

`balls_bowled` counts legal deliveries only (excluding wides and no-balls).
Runs conceded include batter runs plus wide/no-ball extras, but exclude byes,
leg-byes and penalties. Run-outs, retirements, obstruction and timed-out
dismissals, plus handled-ball and hit-the-ball-twice dismissals, are not
credited to the bowler. A bowling dot requires zero total runs, so a bye or
leg-bye delivery is not a dot even though those runs are not charged to the
bowler.

### Phase Metrics

- `powerplay_overs/wickets/economy`
- `middle_overs/wickets/economy`
- `death_overs/wickets/economy`

## Player Impact Score

**Table:** `player_form` (legacy physical name)  
**Scope:** `(player_id, format)`

One role-aware 0–100 metric for meaningful contribution. Recent form is a component of Impact Score, not a separate headline rating.

### Weighting Formula

| Component | Weight | Description |
|-----------|--------|-------------|
| Performance Impact | 35% | Sustained format-relative batting and bowling contribution |
| Recent Form | 30% | Rolling batting and bowling output with sample confidence |
| Pressure Impact | 15% | Contribution in demanding match situations |
| Opposition Quality | 10% | Quality of opposition faced |
| Consistency | 5% | Reliability across innings |
| Efficiency | 5% | Format-relative scoring or bowling efficiency |

Batting and bowling are ranked independently within each format, then combined role-aware using 75% of the stronger discipline and 25% of the secondary discipline. Sample-confidence shrinkage pulls small samples toward 50.

### Requirements

- Three innings are required before a discipline receives a ranked component
- Recent batting and bowling use the rolling recent-performance aggregates

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
- Pace/spin wicket percentages (null until reliable bowling-style data is available)
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
