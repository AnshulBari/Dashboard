# Cricket Intelligence — Data Model

## Overview

The Cricket Intelligence Platform uses a universal cricket data model that supports **all major men's cricket formats** through a single set of tables. The model is format-agnostic — the same `matches` table represents T20 franchise cricket (IPL), T20 Internationals, ODIs, and Test matches.

## Entity Relationship Diagram

```
competitions ──────── seasons
     │                    │
     └──────── matches ───┘
              │    │
         ┌────┘    └────┐
     innings          deliveries
         │                │
    ┌────┴────┐      ┌────┴────┐
  teams    teams   players   players
  (bat)    (bowl)  (bat/bowl)

players ──── player_batting_stats
          ├─ player_bowling_stats
          ├─ player_form
          └─ batter_bowler_matchups

teams ───── team_performance
venues ──── venue_stats
```

## Core Entities

### teams

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| canonical_name | VARCHAR(100) | Normalized name (unique) |
| short_name | VARCHAR(20) | Abbreviation (e.g., "MI", "IND") |
| country | VARCHAR(100) | Country for national teams |
| team_type | VARCHAR(50) | `national`, `franchise`, `domestic` |
| is_active | BOOLEAN | Currently active |

### players

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| canonical_name | VARCHAR(200) | Normalized name |
| full_name | VARCHAR(300) | Full legal name |
| country | VARCHAR(100) | Nationality |
| team_id | UUID FK | Primary team |
| role | VARCHAR(50) | batsman, bowler, allrounder, wicketkeeper |
| batting_style | VARCHAR(50) | right_hand, left_hand |
| bowling_style | VARCHAR(50) | Bowling action |
| bowling_type | VARCHAR(30) | pace, spin, medium |

Players are **format-independent** — the same player identity appears across all formats via separate analytics records.

### venues

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR(200) | Normalized venue name |
| city | VARCHAR(100) | City |
| country | VARCHAR(100) | Country |

### competitions

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR(200) | Competition name |
| format | VARCHAR(20) | T20, T20I, ODI, Test |
| competition_type | VARCHAR(50) | league, tournament, bilateral, test_series |
| governing_body | VARCHAR(100) | ICC, BCCI, etc. |

### seasons

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| competition_id | UUID FK | Parent competition |
| name | VARCHAR(50) | Season/edition (e.g., "2024", "2023-24") |
| start_date | DATE | Season start |
| end_date | DATE | Season end |

### format_config

| Column | Type | Description |
|--------|------|-------------|
| format | VARCHAR(20) | Unique format identifier |
| standard_overs | INTEGER | Overs per innings (NULL for Test) |
| powerplay_end | INTEGER | Last over of powerplay (0-indexed) |
| middle_end | INTEGER | Last over of middle phase |
| max_innings | INTEGER | Maximum innings (2 for LOI, 4 for Test) |
| is_multi_day | BOOLEAN | Multi-day format |
| is_first_class | BOOLEAN | First-class cricket |

Pre-seeded configurations:

| Format | Overs | Powerplay | Middle | Death | Max Innings | Multi-day |
|--------|-------|-----------|--------|-------|-------------|-----------|
| T20 | 20 | 0-5 | 6-14 | 15+ | 2 | No |
| T20I | 20 | 0-5 | 6-14 | 15+ | 2 | No |
| ODI | 50 | 0-9 | 10-39 | 40+ | 2 | No |
| Test | ∞ | n/a | n/a | n/a | 4 | Yes |

## Match Data

### matches

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| external_id | VARCHAR(100) | Cricsheet match ID |
| competition_id | UUID FK | Competition |
| season_id | UUID FK | Season/edition |
| venue_id | UUID FK | Venue |
| match_date | DATE | Match date |
| format | VARCHAR(20) | T20, T20I, ODI, Test |
| team_a_id | UUID FK | First team |
| team_b_id | UUID FK | Second team |
| toss_winner_id | UUID FK | Toss winner |
| toss_decision | VARCHAR(20) | bat, field |
| winner_id | UUID FK | Match winner (NULL for draw/no result) |
| win_margin | INTEGER | Margin of victory |
| win_type | VARCHAR(30) | runs, wickets, innings, DLS |
| result_type | VARCHAR(30) | win, tie, draw, no_result, abandoned |
| total_innings | INTEGER | 2, 3, or 4 |
| day_number | INTEGER | For multi-day matches |
| event_match_number | INTEGER | Match number within event |

### innings

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| match_id | UUID FK | Parent match |
| innings_number | INTEGER | 1-6 (CHECK: BETWEEN 1 AND 6) |
| batting_team_id | UUID FK | Batting team |
| bowling_team_id | UUID FK | Bowling team |
| total_runs | INTEGER | Total runs scored |
| total_wickets | INTEGER | Wickets lost |
| total_overs | DECIMAL(4,1) | Overs faced |
| declared | BOOLEAN | Test: innings declared |
| all_out | BOOLEAN | All batters out |
| follow_on | BOOLEAN | Team was enforced to follow-on |

### deliveries

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| innings_id | UUID FK | Parent innings |
| match_id | UUID FK | Parent match |
| over_number | INTEGER | 0-indexed over |
| ball_in_over | INTEGER | Ball position (CHECK: 1-12 for wides) |
| striker_id | UUID FK | Current striker |
| non_striker_id | UUID FK | Non-striker |
| bowler_id | UUID FK | Current bowler |
| runs_bat | INTEGER | Runs off the bat |
| runs_extras | INTEGER | Extras |
| total_runs | INTEGER | Total runs |
| extra_type | VARCHAR(20) | wide, noball, bye, legbye, penalty |
| is_wicket | BOOLEAN | Was a wicket taken |
| wicket_type | VARCHAR(30) | bowled, caught, lbw, run_out, etc. |
| dismissed_player_id | UUID FK | Player dismissed |

## Analytical Tables

All analytical tables scope by **format** to ensure format-specific statistics:

### player_batting_stats

Scoped by `(player_id, format, period)`. Contains career and phase-specific batting metrics.

### player_bowling_stats

Scoped by `(player_id, format, period)`. Contains career and phase-specific bowling metrics.

### player_form

Scoped by `(player_id, format)`. Contains the original Player Form Score.

### team_performance

Scoped by `(team_id, format, period)`. Contains team strength metrics.

### venue_stats

Scoped by `(venue_id, format)`. Contains venue analytics by format.

### batter_bowler_matchups

Scoped by `(batter_id, bowler_id, format)`. Contains head-to-head matchup data.

### rankings

Scoped by `(player_id, format, category, source, period)`. Supports multiple ranking sources.

## Indexes

Key indexes for common query patterns:

- `idx_deliveries_match` — match lookups
- `idx_deliveries_striker` / `idx_deliveries_bowler` — player delivery lookups
- `idx_pbs_player` / `idx_pbs_format_period` — batting stats queries
- `idx_pws_player` / `idx_pws_format_period` — bowling stats queries
- `idx_tp_team` / `idx_tp_format_period` — team performance
- `idx_bbm_batter` / `idx_bbm_bowler` — matchup queries
- `idx_matches_date` / `idx_matches_format` — match filtering
- `idx_pform_score` — form score leaderboard

## Current Data (IPL)

| Table | Row Count |
|-------|-----------|
| teams | 15 |
| players | 807 |
| venues | 50 |
| competitions | 1 |
| matches | 1,243 |
| innings | 2,514 |
| deliveries | 295,732 |
| player_batting_stats | 738 |
| player_bowling_stats | 577 |
| player_form | 571 |
| team_performance | 15 |
| venue_stats | 50 |
| batter_bowler_matchups | 9,502 |
| format_config | 4 |

## Views

- `v_player_summary` — Player overview with T20 career stats
- `v_team_summary` — Team overview with T20 career stats
