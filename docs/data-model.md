# Data Model

## Overview

The Cricket Intelligence Platform uses a canonical data model designed for:
- **Stable entity identity** — UUIDs, not display names
- **Relational integrity** — Foreign keys enforced at the database level
- **Analytical efficiency** — Denormalized analytical tables for fast reads
- **Format separation** — Stats computed per format (T20, T20I, ODI, Test)
- **Database portability** — Same schema works on SQLite and PostgreSQL

## Entity Relationship Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────────┐
│  teams   │     │ players  │     │  venues  │     │ competitions │
│----------│     │----------│     │----------│     │--------------│
│ id (PK)  │     │ id (PK)  │     │ id (PK)  │     │ id (PK)      │
│ name     │     │ name     │     │ name     │     │ name         │
│ short    │◄────│ team_id  │     │ city     │     │ format       │
│ country  │     │ role     │     │ country  │     │ governing    │
│ is_active│     │ batting  │     │ capacity │     │ season       │
└────┬─────┘     │ bowling  │     └────┬─────┘     └──────┬───────┘
     │           └──────────┘          │                   │
     │                                 │                   │
     └──────────┬──────────────────────┘                   │
                │              ┌────────────────────────────┘
                ▼              ▼
┌──────────────────────────────────────────────────────────────────┐
│                         matches                                  │
│------------------------------------------------------------------│
│ id (PK)    │ venue_id (FK)    │ team_a_id (FK) │ team_b_id (FK)│
│ external_id│ competition_id(FK)│ winner_id (FK) │ toss_winner_id│
│ match_date │ format           │ toss_decision   │ win_margin    │
│ win_type   │ player_of_match_id│ total_innings  │total_deliveries│
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────┐
│            innings                │
│----------------------------------│
│ id (PK)       │ batting_team_id  │
│ match_id (FK) │ bowling_team_id  │
│ innings_number│ total_runs       │
│               │ total_wickets    │
│               │ total_overs      │
└───────────────┬──────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────┐
│                      deliveries                               │
│--------------------------------------------------------------│
│ id (PK)        │ striker_id (FK)   │ runs_batter             │
│ innings_id(FK) │ non_striker_id(FK)│ runs_total              │
│ match_id (FK)  │ bowler_id (FK)    │ is_wicket               │
│ over_number    │ dismissed_player_id│ wicket_type             │
│ ball_in_over   │                    │ extra_type              │
└──────────────────────────────────────────────────────────────┘
```

## Core Tables

### teams

Canonical team identity. All known variants map to one row.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `canonical_name` | VARCHAR(100) | NO | Unique canonical name (e.g., "India") |
| `short_name` | VARCHAR(20) | YES | Abbreviation (e.g., "IND") |
| `team_type` | VARCHAR(30) | YES | international, franchise, domestic |
| `country` | VARCHAR(100) | YES | Country |
| `is_active` | BOOLEAN | YES | Whether team is currently active (default: true) |
| `created_at` | TIMESTAMP | YES | Record creation time |
| `updated_at` | TIMESTAMP | YES | Last update time (auto-triggered) |

### players

Canonical player identity. Discovered from match data, not hard-coded.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `canonical_name` | VARCHAR(200) | NO | Name as it appears in Cricsheet data |
| `full_name` | VARCHAR(300) | YES | Full name (if available) |
| `country` | VARCHAR(100) | YES | Country |
| `date_of_birth` | DATE | YES | Date of birth (future use) |
| `team_id` | UUID FK | YES | Primary team |
| `role` | VARCHAR(50) | YES | batsman, bowler, allrounder, wicketkeeper |
| `batting_style` | VARCHAR(50) | YES | right_hand, left_hand |
| `bowling_style` | VARCHAR(50) | YES | Bowling action description |
| `bowling_type` | VARCHAR(30) | YES | pace, spin, medium |
| `icc_id` | VARCHAR(50) | YES | ICC player ID (future use) |
| `cricsheet_id` | VARCHAR(50) | YES | Cricsheet registry ID |
| `aliases` | TEXT | YES | JSON array of alternate names (future use) |
| `is_active` | BOOLEAN | YES | Whether player is currently active (default: true) |
| `created_at` | TIMESTAMP | YES | Record creation time |
| `updated_at` | TIMESTAMP | YES | Last update time (auto-triggered) |

**Role inference:** The pipeline infers roles from bowling data:
- 0–29 balls bowled → batsman
- 30+ balls bowled → bowler (if primary role is bowling) or allrounder

### venues

Cricket grounds where matches are played.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `name` | VARCHAR(200) | NO | Venue name |
| `city` | VARCHAR(100) | YES | City |
| `country` | VARCHAR(100) | YES | Country |
| `latitude` | DECIMAL | YES | Latitude (future use) |
| `longitude` | DECIMAL | YES | Longitude (future use) |
| `capacity` | INTEGER | YES | Seating capacity (future use) |
| `created_at` | TIMESTAMP | YES | Record creation time |
| `updated_at` | TIMESTAMP | YES | Last update time (auto-triggered) |

### competitions

Tournaments, series, and events.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `name` | VARCHAR(200) | NO | Competition name (e.g., "Indian Premier League") |
| `competition_type` | VARCHAR(50) | YES | tournament, series, bilateral |
| `format` | VARCHAR(20) | YES | T20, ODI, Test |
| `country` | VARCHAR(100) | YES | Host country |
| `governing_body` | VARCHAR(100) | YES | ICC, BCCI, etc. |
| `season` | VARCHAR(20) | YES | Season/edition |
| `start_date` | DATE | YES | Competition start date |
| `end_date` | DATE | YES | Competition end date |
| `is_active` | BOOLEAN | YES | Whether competition is ongoing |
| `created_at` | TIMESTAMP | YES | Record creation time |
| `updated_at` | TIMESTAMP | YES | Last update time (auto-triggered) |

### matches

Individual match records.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `external_id` | VARCHAR(100) | YES | Cricsheet match ID (UNIQUE) |
| `competition_id` | UUID FK | YES | Competition |
| `venue_id` | UUID FK | YES | Venue |
| `match_date` | DATE | YES | Match date |
| `format` | VARCHAR(20) | YES | T20, ODI, Test |
| `season` | VARCHAR(20) | YES | Season/edition |
| `team_a_id` | UUID FK | YES | First team |
| `team_b_id` | UUID FK | YES | Second team |
| `toss_winner_id` | UUID FK | YES | Toss winner |
| `toss_decision` | VARCHAR(20) | YES | bat, field |
| `winner_id` | UUID FK | YES | Match winner |
| `win_margin` | INTEGER | YES | Margin of victory |
| `win_type` | VARCHAR(30) | YES | runs, wickets, DLS, tie, no_result |
| `player_of_match_id` | UUID FK | YES | Player of the match |
| `event_name` | VARCHAR(200) | YES | Event name (e.g., "Indian Premier League") |
| `stage` | VARCHAR(50) | YES | Group, semi-final, final, etc. |
| `match_number` | INTEGER | YES | Match number in competition |
| `total_innings` | INTEGER | YES | Number of innings |
| `total_deliveries` | INTEGER | YES | Total deliveries bowled |
| `created_at` | TIMESTAMP | YES | Record creation time |

### innings

Innings within a match.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `match_id` | UUID FK | NO | Parent match |
| `innings_number` | INTEGER | NO | 1, 2, 3, or 4 |
| `batting_team_id` | UUID FK | YES | Batting team |
| `bowling_team_id` | UUID FK | YES | Bowling team |
| `total_runs` | INTEGER | YES | Total runs scored |
| `total_wickets` | INTEGER | YES | Total wickets lost |
| `total_overs` | DECIMAL | YES | Overs faced |
| `extras_wides` | INTEGER | YES | Wides (pipeline-written) |
| `extras_noballs` | INTEGER | YES | No-balls (pipeline-written) |
| `extras_byes` | INTEGER | YES | Byes (pipeline-written) |
| `extras_legbyes` | INTEGER | YES | Leg byes (pipeline-written) |
| `extras_penalty` | INTEGER | YES | Penalty runs (pipeline-written) |
| `total_extras` | INTEGER | YES | Total extras (pipeline-written) |
| `run_rate` | DECIMAL | YES | Run rate (pipeline-written) |

### deliveries

Ball-by-ball delivery data — the foundation for all analytics.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `innings_id` | UUID FK | NO | Parent innings |
| `match_id` | UUID FK | NO | Parent match |
| `over_number` | INTEGER | NO | Over number (0-indexed) |
| `ball_in_over` | INTEGER | NO | Ball within over (1–12, normally 1–6, extended by wides) |
| `striker_id` | UUID FK | YES | Batsman on strike |
| `non_striker_id` | UUID FK | YES | Batsman at non-striker end |
| `bowler_id` | UUID FK | YES | Bowler |
| `runs_batter` | INTEGER | YES | Runs scored by batsman |
| `runs_extras` | INTEGER | YES | Extras (wides, no-balls, etc.) |
| `runs_total` | INTEGER | YES | Total runs off this delivery |
| `extra_type` | VARCHAR(20) | YES | wide, noball, bye, legbye, penalty |
| `is_wicket` | BOOLEAN | YES | Whether a wicket fell |
| `wicket_type` | VARCHAR(30) | YES | bowled, caught, lbw, run_out, etc. |
| `dismissed_player_id` | UUID FK | YES | Player dismissed |
| `fielder_id` | UUID FK | YES | Fielder involved (future use) |
| `cumulative_runs` | INTEGER | YES | Cumulative runs at this delivery (future use) |
| `cumulative_wickets` | INTEGER | YES | Cumulative wickets at this delivery (future use) |
| `current_over` | DECIMAL | YES | Decimal over at this delivery (future use) |
| `created_at` | TIMESTAMP | YES | Record creation time |

**Note:** `ball_in_over` uses CHECK constraint `BETWEEN 1 AND 12` (not 1–6) because wides can extend an over beyond the normal 6 balls.

## Analytical Tables

### player_batting_stats

Precomputed career batting statistics per player per format.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `player_id` | UUID FK | NO | Player |
| `format` | VARCHAR(20) | NO | T20, ODI, Test |
| `period` | VARCHAR(20) | NO | career, last_30_days, etc. |
| `matches` | INTEGER | YES | Matches played |
| `innings` | INTEGER | YES | Innings batted |
| `not_outs` | INTEGER | YES | Innings not out |
| `runs` | INTEGER | YES | Total runs |
| `highest_score` | INTEGER | YES | Highest individual score |
| `batting_average` | DECIMAL | YES | Runs / dismissals |
| `strike_rate` | DECIMAL | YES | Runs / balls × 100 |
| `balls_faced` | INTEGER | YES | Total balls faced |
| `fours` | INTEGER | YES | Boundaries (4 runs) |
| `sixes` | INTEGER | YES | Maximums (6 runs) |
| `boundary_pct` | DECIMAL | YES | (4s + 6s) / balls_faced × 100 |
| `dot_ball_pct` | DECIMAL | YES | Dot balls / balls_faced × 100 |
| `fifties` | INTEGER | YES | Scores of 50–99 |
| `hundreds` | INTEGER | YES | Scores of 100+ |
| `powerplay_runs` | INTEGER | YES | Runs in overs 1–6 |
| `powerplay_strike_rate` | DECIMAL | YES | Strike rate in overs 1–6 |
| `middle_runs` | INTEGER | YES | Runs in overs 7–15 |
| `middle_strike_rate` | DECIMAL | YES | Strike rate in overs 7–15 |
| `death_runs` | INTEGER | YES | Runs in overs 16–20 |
| `death_strike_rate` | DECIMAL | YES | Strike rate in overs 16–20 |
| `chasing_runs` | INTEGER | YES | Runs in 2nd innings |
| `chasing_strike_rate` | DECIMAL | YES | Strike rate in 2nd innings |
| `first_innings_runs` | INTEGER | YES | Runs in 1st innings |
| `first_innings_strike_rate` | DECIMAL | YES | Strike rate in 1st innings |
| `consistency_score` | DECIMAL | YES | 1 − CV of innings scores, normalized |
| `calculated_at` | TIMESTAMP | YES | When stats were computed |

### player_bowling_stats

Precomputed career bowling statistics per player per format.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `player_id` | UUID FK | NO | Player |
| `format` | VARCHAR(20) | NO | T20, ODI, Test |
| `period` | VARCHAR(20) | NO | career |
| `matches` | INTEGER | YES | Matches played |
| `innings` | INTEGER | YES | Innings bowled |
| `overs` | DECIMAL | YES | Total overs bowled |
| `balls_bowled` | INTEGER | YES | Total balls bowled |
| `wickets` | INTEGER | YES | Total wickets |
| `runs_conceded` | INTEGER | YES | Total runs conceded |
| `bowling_average` | DECIMAL | YES | Runs conceded / wickets |
| `strike_rate` | DECIMAL | YES | Balls / wickets |
| `economy` | DECIMAL | YES | Runs conceded / overs |
| `dot_ball_pct` | DECIMAL | YES | Dot balls / total balls × 100 |
| `boundary_conceded_pct` | DECIMAL | YES | Boundaries conceded / total balls × 100 |
| `powerplay_overs` | DECIMAL | YES | Overs bowled in overs 1–6 |
| `powerplay_wickets` | INTEGER | YES | Wickets in overs 1–6 |
| `powerplay_economy` | DECIMAL | YES | Economy in overs 1–6 |
| `middle_overs` | DECIMAL | YES | Overs bowled in overs 7–15 |
| `middle_wickets` | INTEGER | YES | Wickets in overs 7–15 |
| `middle_economy` | DECIMAL | YES | Economy in overs 7–15 |
| `death_overs` | DECIMAL | YES | Overs bowled in overs 16–20 |
| `death_wickets` | INTEGER | YES | Wickets in overs 16–20 |
| `death_economy` | DECIMAL | YES | Economy in overs 16–20 |
| `calculated_at` | TIMESTAMP | YES | When stats were computed |

### player_form

Weighted composite form score (0–100).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `player_id` | UUID FK | NO | Player |
| `format` | VARCHAR(20) | NO | T20, ODI, Test |
| `form_score` | DECIMAL | YES | Final weighted score |
| `recent_performance_component` | DECIMAL | YES | Normalized recent performance |
| `consistency_component` | DECIMAL | YES | Normalized consistency |
| `opposition_strength_component` | DECIMAL | YES | Normalized opposition strength |
| `venue_performance_component` | DECIMAL | YES | Normalized venue performance |
| `match_situation_component` | DECIMAL | YES | Normalized match situation |
| `efficiency_component` | DECIMAL | YES | Normalized efficiency |
| `recent_innings_count` | INTEGER | YES | Number of recent innings used |
| `last_calculated_at` | TIMESTAMP | YES | When form was computed |

### team_performance

Precomputed team statistics per format.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `team_id` | UUID FK | NO | Team |
| `format` | VARCHAR(20) | NO | T20, ODI, Test |
| `period` | VARCHAR(20) | NO | career |
| `matches` | INTEGER | YES | Matches played |
| `wins` | INTEGER | YES | Matches won |
| `losses` | INTEGER | YES | Matches lost |
| `win_rate` | DECIMAL | YES | Win percentage |
| `avg_first_innings_score` | DECIMAL | YES | Average 1st innings total |
| `avg_second_innings_score` | DECIMAL | YES | Average 2nd innings total |
| `avg_powerplay_score` | DECIMAL | YES | Average powerplay scoring |
| `avg_middle_overs_score` | DECIMAL | YES | Average middle overs scoring |
| `avg_death_overs_score` | DECIMAL | YES | Average death overs scoring |
| `avg_economy` | DECIMAL | YES | Average bowling economy |
| `batting_strength_score` | DECIMAL | YES | Normalized batting strength (0–100) |
| `bowling_strength_score` | DECIMAL | YES | Normalized bowling strength (0–100) |
| `overall_strength_score` | DECIMAL | YES | Combined strength (0–100) |
| `chasing_win_pct` | DECIMAL | YES | Win rate when chasing |
| `defending_win_pct` | DECIMAL | YES | Win rate when defending |
| `calculated_at` | TIMESTAMP | YES | When stats were computed |

### venue_stats

Precomputed venue statistics per format.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `venue_id` | UUID FK | NO | Venue |
| `format` | VARCHAR(20) | NO | T20, ODI, Test |
| `total_matches` | INTEGER | YES | Matches at venue |
| `avg_first_innings_score` | DECIMAL | YES | Average 1st innings total |
| `avg_second_innings_score` | DECIMAL | YES | Average 2nd innings total |
| `highest_total` | INTEGER | YES | Highest team total |
| `lowest_total` | INTEGER | YES | Lowest team total |
| `chasing_wins` | INTEGER | YES | Matches won by chasing team |
| `defending_wins` | INTEGER | YES | Matches won by defending team |
| `chasing_win_pct` | DECIMAL | YES | Chasing win rate |
| `defending_win_pct` | DECIMAL | YES | Defending win rate |
| `pace_wickets_pct` | DECIMAL | YES | % of wickets by pace bowlers |
| `spin_wickets_pct` | DECIMAL | YES | % of wickets by spin bowlers |
| `avg_powerplay_runs` | DECIMAL | YES | Average powerplay scoring |
| `avg_middle_overs_runs` | DECIMAL | YES | Average middle overs scoring |
| `avg_death_overs_runs` | DECIMAL | YES | Average death overs scoring |
| `avg_fours_per_match` | DECIMAL | YES | Average fours per match |
| `avg_sixes_per_match` | DECIMAL | YES | Average sixes per match |
| `boundary_frequency` | DECIMAL | YES | % of deliveries that are boundaries |
| `toss_bat_first_win_pct` | DECIMAL | YES | Win rate when toss winner bats first |
| `toss_field_first_win_pct` | DECIMAL | YES | Win rate when toss winner fields first |
| `calculated_at` | TIMESTAMP | YES | When stats were computed |

### batter_bowler_matchups

Head-to-head statistics between specific batter-bowler pairs.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | Primary key |
| `batter_id` | UUID FK | NO | Batter |
| `bowler_id` | UUID FK | NO | Bowler |
| `format` | VARCHAR(20) | NO | T20, ODI, Test |
| `total_balls` | INTEGER | YES | Balls faced (minimum 10) |
| `total_runs` | INTEGER | YES | Runs scored |
| `total_wickets` | INTEGER | YES | Times dismissed |
| `strike_rate` | DECIMAL | YES | Runs / balls × 100 |
| `batting_average` | DECIMAL | YES | Runs / dismissals |
| `dot_balls` | INTEGER | YES | Dot balls faced |
| `boundaries` | INTEGER | YES | Boundaries hit (4s) |
| `sixes` | INTEGER | YES | Sixes hit |
| `calculated_at` | TIMESTAMP | YES | When matchup was computed |

## Future Tables (Schema Defined, Not Yet Populated)

### player_impact

Actual vs expected performance per delivery/match.

| Column | Type | Description |
|--------|------|-------------|
| `player_id` | UUID FK | Player |
| `match_id` | UUID FK | Match |
| `format` | VARCHAR(20) | T20, ODI, Test |
| `impact_type` | VARCHAR(30) | batting, bowling |
| `expected_value` | DECIMAL | Expected performance |
| `actual_value` | DECIMAL | Actual performance |
| `impact_score` | DECIMAL | Actual − Expected |

### batter_type_matchups

Aggregate matchups by bowling type (pace vs spin, left vs right arm).

| Column | Type | Description |
|--------|------|-------------|
| `batter_id` | UUID FK | Batter |
| `bowling_type` | VARCHAR(30) | pace, spin, medium |
| `bowling_arm` | VARCHAR(10) | left, right |
| `format` | VARCHAR(20) | T20, ODI, Test |
| `total_balls` | INTEGER | Balls faced |
| `total_runs` | INTEGER | Runs scored |
| `total_wickets` | INTEGER | Times dismissed |
| `strike_rate` | DECIMAL | Runs / balls × 100 |
| `batting_average` | DECIMAL | Runs / dismissals |

### rankings

Platform-computed player rankings.

| Column | Type | Description |
|--------|------|-------------|
| `player_id` | UUID FK | Player |
| `format` | VARCHAR(20) | T20, ODI, Test |
| `category` | VARCHAR(30) | batting, bowling, allrounder |
| `rating_points` | DECIMAL | Rating points |
| `rank_position` | INTEGER | Rank position |

### news_articles

Cricket news from RSS feeds.

| Column | Type | Description |
|--------|------|-------------|
| `title` | VARCHAR(500) | Article headline |
| `source` | VARCHAR(100) | News source |
| `url` | VARCHAR(1000) | Article URL |
| `publication_date` | TIMESTAMP | When published |
| `description` | TEXT | Article excerpt |
| `category` | VARCHAR(50) | Category |

### live_matches

Live match data from external APIs.

| Column | Type | Description |
|--------|------|-------------|
| `external_match_id` | VARCHAR(100) | External match ID |
| `format` | VARCHAR(20) | T20, ODI, Test |
| `status` | VARCHAR(30) | live, completed, upcoming |
| `batting_team` | VARCHAR(100) | Current batting team |
| `bowling_team` | VARCHAR(100) | Current bowling team |
| `current_score` | VARCHAR(20) | Current score (e.g., "142/3") |
| `current_overs` | DECIMAL | Current overs |
| `required_run_rate` | DECIMAL | Required run rate |
| `current_run_rate` | DECIMAL | Current run rate |

## Identity Mapping Tables

### player_name_mappings

Maps external names to canonical player IDs.

| Column | Type | Description |
|--------|------|-------------|
| `player_id` | UUID FK | Canonical player |
| `external_name` | VARCHAR(200) | Name from external source |
| `source` | VARCHAR(50) | cricsheet, icc, manual |

### team_name_mappings

Maps external team names to canonical team IDs.

| Column | Type | Description |
|--------|------|-------------|
| `team_id` | UUID FK | Canonical team |
| `external_name` | VARCHAR(100) | Name from external source |
| `source` | VARCHAR(50) | cricsheet, icc, manual |

## Views

### v_player_summary

Cross-table player summary joining batting stats, bowling stats, and form score for format T20.

```sql
SELECT
    p.id, p.canonical_name, p.role, p.batting_style, p.bowling_style, p.country,
    t.canonical_name AS team_name,
    pbs.runs AS career_runs, pbs.batting_average, pbs.strike_rate, pbs.innings AS career_innings,
    pws.wickets AS career_wickets, pws.economy AS career_economy, pws.bowling_average,
    pf.form_score
FROM players p
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN player_batting_stats pbs ON p.id = pbs.player_id AND pbs.format = 'T20' AND pbs.period = 'career'
LEFT JOIN player_bowling_stats pws ON p.id = pws.player_id AND pws.format = 'T20' AND pws.period = 'career'
LEFT JOIN player_form pf ON p.id = pf.player_id AND pf.format = 'T20';
```

### v_team_summary

Cross-table team summary joining team performance and strength scores for format T20.

```sql
SELECT
    t.id, t.canonical_name, t.short_name, t.country,
    tp.matches, tp.win_rate, tp.batting_strength_score, tp.bowling_strength_score,
    tp.overall_strength_score
FROM teams t
LEFT JOIN team_performance tp ON t.id = tp.team_id AND tp.format = 'T20' AND tp.period = 'career';
```

## Indexes

| Index | Table | Column(s) | Purpose |
|-------|-------|-----------|---------|
| `idx_matches_date` | matches | `match_date DESC` | Date-range queries |
| `idx_matches_format` | matches | `format` | Format filtering |
| `idx_matches_venue` | matches | `venue_id` | Venue-based queries |
| `idx_matches_competition` | matches | `competition_id` | Competition queries |
| `idx_matches_team_a` | matches | `team_a_id` | Team-based queries |
| `idx_matches_team_b` | matches | `team_b_id` | Team-based queries |
| `idx_innings_match` | innings | `match_id` | Match → innings lookup |
| `idx_delivery_match` | deliveries | `match_id` | Match → deliveries lookup |
| `idx_delivery_bowler` | deliveries | `bowler_id` | Bowler analysis |
| `idx_pform_score` | player_form | `form_score DESC` | Top form scores |
| `idx_rankings_rating` | rankings | `format, category, rating_points DESC` | Rankings queries |

## Triggers

| Trigger | Table | Function |
|---------|-------|----------|
| `update_players_updated_at` | players | Auto-set `updated_at` on UPDATE |
| `update_venues_updated_at` | venues | Auto-set `updated_at` on UPDATE |
| `update_competitions_updated_at` | competitions | Auto-set `updated_at` on UPDATE |

## Current Data Summary (SQLite / PostgreSQL)

| Table | Rows | Description |
|-------|------|-------------|
| teams | 15 | IPL franchises (normalized: Daredevils→Capitals, Kings XI→Punjab Kings, etc.) |
| players | 807 | Discovered from 1,243 IPL matches |
| venues | 50 | IPL venues (normalized duplicates merged) |
| competitions | 1 | Indian Premier League |
| matches | 1,243 | IPL matches (all available seasons) |
| innings | 2,514 | ~2 innings per match |
| deliveries | 295,732 | ~238 deliveries per match average |
| player_batting_stats | 738 | Player-format batting records |
| player_bowling_stats | 577 | Player-format bowling records |
| player_form | 571 | Player-format form scores |
| team_performance | 15 | Team-format performance |
| venue_stats | 50 | Venue-format statistics |
| batter_bowler_matchups | 9,502 | Head-to-head pairs (≥10 balls) |
