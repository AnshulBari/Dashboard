# Data Model

## Core Entities

### teams
Canonical team identity. "India", "IND", "India Men" all map to one row.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Stable internal ID |
| canonical_name | VARCHAR(100) | Unique canonical name |
| short_name | VARCHAR(20) | Short code (IND, AUS, etc.) |
| country | VARCHAR(100) | Country name |
| aliases | TEXT[] | Alternative names for matching |

### players
Canonical player identity.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Stable internal ID |
| canonical_name | VARCHAR(200) | Standardized name |
| team_id | UUID FK | Current team |
| role | VARCHAR(50) | batsman, bowler, allrounder, wicketkeeper |
| batting_style | VARCHAR(50) | right_hand, left_hand |
| bowling_style | VARCHAR(50) | Detailed bowling action |
| bowling_type | VARCHAR(30) | pace, spin, medium |

### matches
Individual match records.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Stable internal ID |
| external_id | VARCHAR(100) | Cricsheet match ID |
| format | VARCHAR(20) | T20I, ODI, Test, T20 |
| match_date | DATE | Date of match |
| venue_id | UUID FK | Venue reference |
| team_a_id, team_b_id | UUID FKs | Teams playing |
| winner_id | UUID FK | Winning team |
| win_type | VARCHAR(30) | runs, wickets, DLS, tie |

### deliveries
Ball-by-ball data — the foundation of all analytics.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Stable internal ID |
| innings_id | UUID FK | Innings reference |
| match_id | UUID FK | Match reference |
| over_number | INTEGER | Over number (0-indexed) |
| ball_in_over | INTEGER | Ball number within over |
| striker_id, bowler_id | UUID FKs | Players involved |
| runs_batter | INTEGER | Runs off the bat |
| total_runs | INTEGER | Total runs including extras |
| is_wicket | BOOLEAN | Whether a wicket fell |
| wicket_type | VARCHAR(30) | Type of dismissal |

## Analytical Tables

These are precomputed by the PySpark pipeline and served by the API.

### player_batting_stats
Career and period-filtered batting statistics per player per format.

Key columns: runs, average, strike_rate, fours, sixes, dot_ball_pct, powerplay/middle/death phase stats, chasing vs setting splits.

### player_bowling_stats
Career and period-filtered bowling statistics per player per format.

Key columns: wickets, economy, bowling_average, strike_rate, phase-specific stats.

### player_form
Player Form Score — weighted composite metric.

| Column | Weight | Description |
|--------|--------|-------------|
| recent_performance_component | 35% | Last 10 innings average |
| consistency_component | 20% | 1 - coefficient of variation |
| opposition_strength_component | 15% | Weighted avg vs team strength |
| venue_performance_component | 10% | Cross-venue consistency |
| match_situation_component | 10% | Chasing vs setting ratio |
| efficiency_component | 10% | strike_rate × avg |

### team_performance
Team strength ratings and performance metrics.

Key columns: win_rate, batting_strength_score, bowling_strength_score, overall_strength_score, phase stats.

### venue_stats
Venue analytics.

Key columns: avg_first/second_innings_score, chasing_win_pct, pace/spin_wickets_pct, phase scoring.

### batter_bowler_matchups
Head-to-head matchup data.

Key columns: total_balls, total_runs, total_wickets, strike_rate, dot_balls, boundaries.

## Entity Relationships

```
teams ──────────┐
                ├── matches (team_a_id, team_b_id, winner_id)
players ────────┤
                ├── innings (batting_team_id, bowling_team_id)
                │
venues ─────────┤
                │
competitions ───┘
                │
innings ────────├── deliveries (innings_id, match_id, striker_id, bowler_id)
                │
                ├── player_batting_stats (player_id)
                ├── player_bowling_stats (player_id)
                ├── player_form (player_id)
                ├── team_performance (team_id)
                ├── venue_stats (venue_id)
                └── batter_bowler_matchups (batter_id, bowler_id)
```

## Normalization Strategy

The `player_name_mappings` and `team_name_mappings` tables handle name normalization:

- Cricsheet uses different name formats across years
- External IDs (ICC, Cricsheet) are tracked per mapping
- Confidence scores indicate match certainty
- Manual overrides are supported for ambiguous cases
