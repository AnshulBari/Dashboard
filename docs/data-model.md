# Data Model

## Overview

The Cricket Intelligence Platform uses a canonical data model designed for:
- **Stable entity identity** — UUIDs, not display names
- **Relational integrity** — Foreign keys enforced at the database level
- **Analytical efficiency** — Denormalized analytical tables for fast reads
- **Format separation** — Stats computed per format (T20, ODI, Test)

## Entity Relationship Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  teams   │     │ players  │     │  venues  │
│----------│     │----------│     │----------│
│ id (PK)  │     │ id (PK)  │     │ id (PK)  │
│ name     │     │ name     │     │ name     │
│ short    │◄────│ team_id  │     │ city     │
│ country  │     │ role     │     │ country  │
└────┬─────┘     │ batting  │     └────┬─────┘
     │           │ bowling  │          │
     │           └──────────┘          │
     │                                  │
     ▼                                  ▼
┌──────────────────────────────────────────────┐
│                   matches                    │
│----------------------------------------------│
│ id (PK)          │ venue_id (FK)            │
│ external_id      │ team_a_id (FK)           │
│ competition_id   │ team_b_id (FK)           │
│ match_date       │ winner_id (FK)           │
│ format           │ toss_winner_id (FK)      │
│ toss_decision    │ win_margin               │
│ win_type         │ player_of_match_id (FK)  │
└────────┬─────────────────────────────────────┘
         │
         ▼
┌──────────────┐
│    innings   │
│--------------│
│ id (PK)      │
│ match_id(FK) │
│ innings_num  │
│ batting_team │
│ bowling_team │
│ total_runs   │
│ total_wickets│
│ total_overs  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│            deliveries                │
│--------------------------------------│
│ id (PK)        │ runs_bat           │
│ innings_id(FK) │ runs_extras        │
│ match_id (FK)  │ total_runs         │
│ over_number    │ extra_type         │
│ ball_in_over   │ is_wicket          │
│ striker_id(FK) │ wicket_type        │
│ bowler_id (FK) │ dismissed_player_id│
└──────────────────────────────────────┘
```

## Core Tables

### teams

Canonical team identity. All known variants map to one row.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `canonical_name` | VARCHAR(100) | Unique canonical name (e.g., "India") |
| `short_name` | VARCHAR(20) | Abbreviation (e.g., "IND") |
| `country` | VARCHAR(100) | Country |
| `is_active` | BOOLEAN | Whether team is currently active |

### players

Canonical player identity. Discovered from match data, not hard-coded.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `canonical_name` | VARCHAR(200) | Name as it appears in Cricsheet data |
| `full_name` | VARCHAR(300) | Full name (if available) |
| `country` | VARCHAR(100) | Country |
| `team_id` | UUID FK | Primary team |
| `role` | VARCHAR(50) | batsman, bowler, allrounder, wicketkeeper |
| `batting_style` | VARCHAR(50) | right_hand, left_hand |
| `bowling_style` | VARCHAR(50) | Bowling action description |
| `bowling_type` | VARCHAR(30) | pace, spin, medium |
| `cricsheet_id` | VARCHAR(50) | Cricsheet registry ID |

### venues

Cricket grounds where matches are played.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR(200) | Venue name |
| `city` | VARCHAR(100) | City |
| `country` | VARCHAR(100) | Country |
| `capacity` | INTEGER | Seating capacity |

### competitions

Tournaments, series, and events.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `name` | VARCHAR(200) | Competition name (e.g., "Indian Premier League") |
| `format` | VARCHAR(20) | T20, ODI, Test |
| `governing_body` | VARCHAR(100) | ICC, BCCI, etc. |
| `season` | VARCHAR(20) | Season/edition |

### matches

Individual match records.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `external_id` | VARCHAR(100) | Cricsheet match ID (UNIQUE) |
| `competition_id` | UUID FK | Competition |
| `venue_id` | UUID FK | Venue |
| `match_date` | DATE | Match date |
| `format` | VARCHAR(20) | T20, ODI, Test |
| `team_a_id` | UUID FK | First team |
| `team_b_id` | UUID FK | Second team |
| `toss_winner_id` | UUID FK | Toss winner |
| `toss_decision` | VARCHAR(20) | bat, field |
| `winner_id` | UUID FK | Match winner |
| `win_margin` | INTEGER | Margin of victory |
| `win_type` | VARCHAR(30) | runs, wickets, DLS, tie |
| `player_of_match_id` | UUID FK | Player of the match |
| `total_innings` | INTEGER | Number of innings |
| `total_deliveries` | INTEGER | Total deliveries bowled |

### innings

Innings within a match.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `match_id` | UUID FK | Parent match |
| `innings_number` | INTEGER | 1, 2, 3, or 4 |
| `batting_team_id` | UUID FK | Batting team |
| `bowling_team_id` | UUID FK | Bowling team |
| `total_runs` | INTEGER | Total runs scored |
| `total_wickets` | INTEGER | Total wickets lost |
| `total_overs` | DECIMAL | Overs faced |

### deliveries

Ball-by-ball delivery data — the foundation for all analytics.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `innings_id` | UUID FK | Parent innings |
| `match_id` | UUID FK | Parent match |
| `over_number` | INTEGER | Over number (0-indexed) |
| `ball_in_over` | INTEGER | Ball within over (1-9) |
| `striker_id` | UUID FK | Batsman on strike |
| `non_striker_id` | UUID FK | Batsman at non-striker end |
| `bowler_id` | UUID FK | Bowler |
| `runs_bat` | INTEGER | Runs scored by batsman |
| `runs_extras` | INTEGER | Extras (wides, no-balls, etc.) |
| `total_runs` | INTEGER | Total runs off this delivery |
| `extra_type` | VARCHAR(20) | wide, noball, bye, legbye, penalty |
| `is_wicket` | BOOLEAN | Whether a wicket fell |
| `wicket_type` | VARCHAR(30) | bowled, caught, lbw, run_out, etc. |
| `dismissed_player_id` | UUID FK | Player dismissed |

## Analytical Tables

### player_batting_stats

Precomputed career batting statistics per player per format.

| Column | Type | Description |
|--------|------|-------------|
| `player_id` | UUID FK | Player |
| `format` | VARCHAR(20) | T20, ODI, Test |
| `period` | VARCHAR(20) | career, last_30_days, etc. |
| `matches` | INTEGER | Matches played |
| `innings` | INTEGER | Innings batted |
| `runs` | INTEGER | Total runs |
| `batting_average` | DECIMAL | Runs / dismissals |
| `strike_rate` | DECIMAL | Runs / balls × 100 |
| `fours` | INTEGER | Boundaries (4 runs) |
| `sixes` | INTEGER | Maximums (6 runs) |
| `fifties` | INTEGER | Scores of 50-99 |
| `hundreds` | INTEGER | Scores of 100+ |
| `powerplay_runs` | INTEGER | Runs in overs 1-6 |
| `middle_runs` | INTEGER | Runs in overs 7-15 |
| `death_runs` | INTEGER | Runs in overs 16-20 |
| `chasing_runs` | INTEGER | Runs in second innings |
| `consistency_score` | DECIMAL | 1 - CV of innings scores |

### player_bowling_stats

Precomputed career bowling statistics per player per format.

| Column | Type | Description |
|--------|------|-------------|
| `player_id` | UUID FK | Player |
| `format` | VARCHAR(20) | T20, ODI, Test |
| `period` | VARCHAR(20) | career, last_30_days, etc. |
| `matches` | INTEGER | Matches played |
| `wickets` | INTEGER | Total wickets |
| `economy` | DECIMAL | Runs conceded / overs |
| `bowling_average` | DECIMAL | Runs conceded / wickets |
| `strike_rate` | DECIMAL | Balls / wickets |
| `dot_ball_pct` | DECIMAL | Percentage of dot balls |
| `powerplay_wickets` | INTEGER | Wickets in overs 1-6 |
| `middle_wickets` | INTEGER | Wickets in overs 7-15 |
| `death_wickets` | INTEGER | Wickets in overs 16-20 |

### player_form

Weighted composite form score (0-100).

| Column | Type | Description |
|--------|------|-------------|
| `player_id` | UUID FK | Player |
| `format` | VARCHAR(20) | T20, ODI, Test |
| `form_score` | DECIMAL | Final weighted score |
| `recent_performance_component` | DECIMAL | Normalized recent performance |
| `consistency_component` | DECIMAL | Normalized consistency |
| `opposition_strength_component` | DECIMAL | Normalized opposition strength |
| `venue_performance_component` | DECIMAL | Normalized venue performance |
| `match_situation_component` | DECIMAL | Normalized match situation |
| `efficiency_component` | DECIMAL | Normalized efficiency |
| `recent_innings_count` | INTEGER | Number of recent innings used |

### team_performance

Precomputed team statistics per format.

| Column | Type | Description |
|--------|------|-------------|
| `team_id` | UUID FK | Team |
| `format` | VARCHAR(20) | T20, ODI, Test |
| `period` | VARCHAR(20) | career |
| `matches` | INTEGER | Matches played |
| `wins` | INTEGER | Matches won |
| `win_rate` | DECIMAL | Win percentage |
| `avg_first_innings_score` | DECIMAL | Average 1st innings total |
| `avg_second_innings_score` | DECIMAL | Average 2nd innings total |
| `batting_strength_score` | DECIMAL | Normalized batting strength |
| `bowling_strength_score` | DECIMAL | Normalized bowling strength |
| `overall_strength_score` | DECIMAL | Combined strength (0-100) |
| `chasing_win_pct` | DECIMAL | Win rate when chasing |

### venue_stats

Precomputed venue statistics per format.

| Column | Type | Description |
|--------|------|-------------|
| `venue_id` | UUID FK | Venue |
| `format` | VARCHAR(20) | T20, ODI, Test |
| `total_matches` | INTEGER | Matches at venue |
| `avg_first_innings_score` | DECIMAL | Average 1st innings total |
| `avg_second_innings_score` | DECIMAL | Average 2nd innings total |
| `highest_total` | INTEGER | Highest team total |
| `lowest_total` | INTEGER | Lowest team total |
| `chasing_win_pct` | DECIMAL | Win rate when chasing |
| `avg_powerplay_runs` | DECIMAL | Average powerplay scoring |
| `avg_middle_overs_runs` | DECIMAL | Average middle overs scoring |
| `avg_death_overs_runs` | DECIMAL | Average death overs scoring |
| `boundary_frequency` | DECIMAL | % of deliveries that are boundaries |

### batter_bowler_matchups

Head-to-head statistics between specific batter-bowler pairs.

| Column | Type | Description |
|--------|------|-------------|
| `batter_id` | UUID FK | Batter |
| `bowler_id` | UUID FK | Bowler |
| `format` | VARCHAR(20) | T20, ODI, Test |
| `total_balls` | INTEGER | Balls faced (minimum 10) |
| `total_runs` | INTEGER | Runs scored |
| `total_wickets` | INTEGER | Times dismissed |
| `strike_rate` | DECIMAL | Runs / balls × 100 |
| `batting_average` | DECIMAL | Runs / dismissals |
| `dot_balls` | INTEGER | Dot balls faced |
| `boundaries` | INTEGER | Boundaries hit (4s + 6s) |

## Indexes

The schema includes indexes for common query patterns:

- `idx_deliveries_innings` — Deliveries by innings
- `idx_deliveries_match` — Deliveries by match
- `idx_deliveries_striker` — Deliveries by batter
- `idx_deliveries_bowler` — Deliveries by bowler
- `idx_matches_date` — Matches by date
- `idx_matches_format` — Matches by format
- `idx_pbs_player` — Batting stats by player
- `idx_pf_player` — Form scores by player
- `idx_bbm_batter` — Matchups by batter
- `idx_bbm_bowler` — Matchups by bowler
- `idx_rankings_format` — Rankings by format and category
