# Analytics Methodology

## Overview

All analytics in the Cricket Intelligence Platform are computed offline by the pipeline from ball-by-ball data, then stored in PostgreSQL as precomputed results. The API and frontend never compute statistics at request time.

---

## Player Form Score

### Concept

The Form Score is an original, explainable metric that quantifies a player's current form based on multiple statistical dimensions. It is a **project-defined metric**, not an official cricket metric.

### Formula

```
Form_Score = 0.35 × Recent_Performance
           + 0.20 × Consistency
           + 0.15 × Opposition_Strength
           + 0.10 × Venue_Performance
           + 0.10 × Match_Situation
           + 0.10 × Efficiency
```

### Components

| # | Component | Weight | Method |
|---|-----------|--------|--------|
| 1 | Recent Performance | 35% | Average runs in last 10 innings, min-max normalized across all players |
| 2 | Consistency | 20% | 1 − Coefficient of Variation, normalized. Lower variance = higher score |
| 3 | Opposition Strength | 15% | Weighted avg performance by opponent strength (weighted by balls faced) |
| 4 | Venue Performance | 10% | 1 − (CV of averages across venues). Players who perform well everywhere score higher |
| 5 | Match Situation | 10% | Ratio of chasing average to overall average. Chasing under pressure = higher score |
| 6 | Efficiency | 10% | Strike Rate × Average / 100. Combines speed and reliability of run-scoring |

### Normalization

Each component is normalized to 0–100 using min-max scaling within the same format:

```
normalized = (value - min) / (max - min) × 100
```

This means:
- A player with the best value gets 100
- A player with the worst gets 0
- The median player gets roughly 50

### Weight Justification

- **Recent Performance (35%)**: Most heavily weighted because current form is the primary concern
- **Consistency (20%)**: Reliable performers are more valuable than volatile ones
- **Opposition Strength (15%)**: Performance against strong teams is more meaningful
- **Other components (10% each)**: Contextual factors that provide nuance

### Limitations

1. Requires minimum 3 innings for statistical significance
2. Min-max scaling is sensitive to outliers
3. Weights are initial estimates, not empirically validated
4. Cold start problem for players with limited data
5. Does not account for match importance or tournament context

### Database columns

Stored in `player_form` table:

| Column | Description |
|--------|-------------|
| `form_score` | Final weighted score (0–100) |
| `recent_performance_component` | Normalized recent performance component |
| `consistency_component` | Normalized consistency component |
| `opposition_strength_component` | Normalized opposition strength component |
| `venue_performance_component` | Normalized venue performance component |
| `match_situation_component` | Normalized match situation component |
| `efficiency_component` | Normalized efficiency component |
| `recent_innings_count` | Number of recent innings used (up to 10) |

---

## Player Batting Stats

Computed per (player, format) combination. Stored in `player_batting_stats` table.

### Career aggregates

| Stat | Description |
|------|-------------|
| `matches` | Matches played |
| `innings` | Innings batted |
| `not_outs` | Innings not out |
| `runs` | Total runs scored |
| `highest_score` | Highest individual score |
| `batting_average` | Runs / dismissals (runs / (innings - not_outs)) |
| `strike_rate` | Runs / balls_faced × 100 |
| `balls_faced` | Total balls faced |
| `fours` | Boundaries (4 runs) |
| `sixes` | Maximums (6 runs) |
| `boundary_pct` | (fours + sixes) / balls_faced × 100 |
| `dot_ball_pct` | Dot balls / balls_faced × 100 |
| `fifties` | Scores of 50–99 |
| `hundreds` | Scores of 100+ |

### Phase-specific (T20 overs 1–6 / 7–15 / 16–20)

| Stat | Description |
|------|-------------|
| `powerplay_runs` | Runs scored in overs 1–6 |
| `powerplay_strike_rate` | Strike rate in overs 1–6 |
| `middle_runs` | Runs scored in overs 7–15 |
| `middle_strike_rate` | Strike rate in overs 7–15 |
| `death_runs` | Runs scored in overs 16–20 |
| `death_strike_rate` | Strike rate in overs 16–20 |

### Situational

| Stat | Description |
|------|-------------|
| `chasing_runs` | Runs scored in 2nd innings (chasing) |
| `chasing_strike_rate` | Strike rate in 2nd innings |
| `first_innings_runs` | Runs scored in 1st innings (setting) |
| `first_innings_strike_rate` | Strike rate in 1st innings |
| `consistency_score` | 1 − (coefficient of variation of per-innings scores), normalized 0–100 |

---

## Player Bowling Stats

Computed per (player, format) combination. Stored in `player_bowling_stats` table.

### Career aggregates

| Stat | Description |
|------|-------------|
| `matches` | Matches played |
| `innings` | Innings bowled |
| `overs` | Total overs bowled |
| `balls_bowled` | Total balls bowled |
| `wickets` | Total wickets taken |
| `runs_conceded` | Total runs conceded |
| `bowling_average` | Runs conceded / wickets |
| `strike_rate` | Balls / wickets |
| `economy` | Runs conceded / overs |
| `dot_ball_pct` | Dot balls bowled / total balls × 100 |
| `boundary_conceded_pct` | Boundaries conceded / total balls × 100 |

### Phase-specific

| Stat | Description |
|------|-------------|
| `powerplay_overs` | Overs bowled in overs 1–6 |
| `powerplay_wickets` | Wickets in overs 1–6 |
| `powerplay_economy` | Economy in overs 1–6 |
| `middle_overs` | Overs bowled in overs 7–15 |
| `middle_wickets` | Wickets in overs 7–15 |
| `middle_economy` | Economy in overs 7–15 |
| `death_overs` | Overs bowled in overs 16–20 |
| `death_wickets` | Wickets in overs 16–20 |
| `death_economy` | Economy in overs 16–20 |

---

## Team Performance

Computed per (team, format) combination. Stored in `team_performance` table.

| Stat | Description |
|------|-------------|
| `matches` | Matches played |
| `wins` | Matches won |
| `losses` | Matches lost |
| `win_rate` | Wins / matches × 100 |
| `avg_first_innings_score` | Average team total when batting first |
| `avg_second_innings_score` | Average team total when batting second |
| `avg_powerplay_score` | Average runs in powerplay (overs 1–6) |
| `avg_middle_overs_score` | Average runs in middle overs (7–15) |
| `avg_death_overs_score` | Average runs in death overs (16–20) |
| `avg_economy` | Average bowling economy |
| `chasing_win_pct` | Win rate when batting second |
| `defending_win_pct` | Win rate when batting first |

### Team Strength Score

```
Strength = 0.35 × Batting_Score + 0.35 × Bowling_Score + 0.30 × Win_Score
```

Where:
- **Batting_Score** = Min-max normalized average total score (0–100)
- **Bowling_Score** = Inverse min-max normalized economy rate (0–100, lower economy = higher score)
- **Win_Score** = Win rate percentage (0–100)

Stored as:
- `batting_strength_score`
- `bowling_strength_score`
- `overall_strength_score`

---

## Venue Stats

Computed per (venue, format) combination. Stored in `venue_stats` table.

| Stat | Description |
|------|-------------|
| `total_matches` | Matches played at venue |
| `avg_first_innings_score` | Average 1st innings total |
| `avg_second_innings_score` | Average 2nd innings total |
| `highest_total` | Highest team total at venue |
| `lowest_total` | Lowest team total at venue |
| `chasing_wins` | Matches won by chasing team |
| `defending_wins` | Matches won by defending team |
| `chasing_win_pct` | Chasing win rate |
| `defending_win_pct` | Defending win rate |
| `pace_wickets_pct` | % of wickets taken by pace bowlers |
| `spin_wickets_pct` | % of wickets taken by spin bowlers |
| `avg_powerplay_runs` | Average powerplay scoring |
| `avg_middle_overs_runs` | Average middle overs scoring |
| `avg_death_overs_runs` | Average death overs scoring |
| `avg_fours_per_match` | Average fours per match |
| `avg_sixes_per_match` | Average sixes per match |
| `boundary_frequency` | % of deliveries that are boundaries |
| `toss_bat_first_win_pct` | Win rate when toss winner bats first |
| `toss_field_first_win_pct` | Win rate when toss winner fields first |

---

## Batter-Bowler Matchups

Computed from all deliveries where a specific batter faced a specific bowler. Stored in `batter_bowler_matchups` table.

**Minimum 10 balls** for statistical significance (pairs with fewer balls are excluded).

| Stat | Description |
|------|-------------|
| `total_balls` | Balls faced |
| `total_runs` | Runs scored |
| `total_wickets` | Times dismissed |
| `strike_rate` | Runs / balls × 100 |
| `batting_average` | Runs / dismissals |
| `dot_balls` | Dot balls faced |
| `boundaries` | Boundaries hit (4s) |
| `sixes` | Sixes hit |

### Contextual matchups (planned)

- **vs Pace/Spin** — Aggregated by bowling type
- **vs Left/Right Arm** — Aggregated by bowling arm

Schema exists in `batter_type_matchups` table but is not yet populated by the pipeline.

---

## Player Impact (Planned)

### Concept

Measures actual performance vs expected performance:

```
Impact = Actual Performance - Expected Performance
```

### Expected Performance Model

For batting:
```
Expected Runs = f(format, over, wickets_remaining, current_score, venue, opposition, bowling_type)
```

For bowling:
```
Expected Runs_Conceded = f(format, over, batting_strength, venue, match_situation)
```

**Status:** Schema defined in `player_impact` table. Not yet implemented in the pipeline. Requires training data from historical match states.

---

## Consistency Score

### Formula

```
CV = stddev(runs) / mean(runs)
Consistency_Score = (1 - CV) × 100
```

### Interpretation

- Higher score = more consistent (lower variance relative to mean)
- A player who scores 30±5 is more consistent than one who scores 40±20
- Minimum 3 innings required for statistical validity

---

## Phase Classification

| Phase | T20 Overs | ODI Overs | Test | Description |
|-------|-----------|-----------|------|-------------|
| Powerplay | 1–6 | 1–10 | N/A | Fielding restrictions, aggressive batting |
| Middle | 7–15 | 11–40 | N/A | Consolidation, spin dominance |
| Death | 16–20 | 41–50 | N/A | High-scoring, yorkers, variations |

Note: Phase boundaries are currently hardcoded for T20 format (1–6 / 7–15 / 16–20). The same boundaries are used for all formats in the current implementation. ODI and Test-specific phase definitions will be added in a future iteration.

---

## Implementation Notes

### Active implementation (pandas)

All analytics are computed in `data_pipeline/pipeline/analytics.py`:

| Function | Output table |
|----------|-------------|
| `compute_player_batting_stats()` | `player_batting_stats` |
| `compute_player_bowling_stats()` | `player_bowling_stats` |
| `compute_player_form_scores()` | `player_form` |
| `compute_team_performance()` | `team_performance` |
| `compute_venue_stats()` | `venue_stats` |
| `compute_matchups()` | `batter_bowler_matchups` |

### Reference implementation (PySpark)

PySpark implementations exist in `data_pipeline/spark/`:
- `player_stats.py` — Career/recent batting & bowling
- `team_stats.py` — Team performance metrics
- `venue_stats.py` — Venue analytics
- `matchup_stats.py` — Batter vs bowler matchups
- `analytics/form_score.py` — PySpark form score

These can be activated if data volumes grow beyond pandas memory capacity.

### Performance (1,243 IPL matches, ~296K deliveries)

| Operation | Time |
|-----------|------|
| Download + extract | ~15s |
| Read + flatten | ~2s |
| Entity resolution | ~5s |
| Write core data | ~25s |
| Compute analytics | ~3s |
| Write analytics | ~2s |
| **Total** | **~50s** |

For full IPL (1,243 matches, ~350K deliveries): ~10 minutes.
