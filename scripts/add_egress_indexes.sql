-- Phase 6.1B: Egress optimization indexes
-- 
-- These indexes optimize the most common analytical query patterns
-- identified during the egress audit. Each index is justified by
-- specific query patterns in the backend.
--
-- Storage impact: ~2-5 MB estimated

-- 1. Composite index for player history queries
-- Query: WHERE player_id = :pid AND format = :fmt ORDER BY match_date DESC
-- Currently does: Index Scan on matches (by date) then filters by format
-- This index allows: direct lookup by player without scanning matches
CREATE INDEX IF NOT EXISTS idx_mbs_player_format_date 
ON match_batting_summary (player_id, match_id)
INCLUDE (runs, balls, fours, sixes, strike_rate, is_not_out, dismissal_type);

-- 2. Composite index for player bowling history
CREATE INDEX IF NOT EXISTS idx_mbsb_player_format_date 
ON match_bowling_summary (player_id, match_id)
INCLUDE (overs, balls_bowled, runs_conceded, wickets, economy, wides, noballs);

-- 3. Composite index for venue player performance
-- Query: WHERE venue_id = :vid AND format = :fmt GROUP BY player
-- Uses: match_batting_summary -> matches -> venues
CREATE INDEX IF NOT EXISTS idx_matches_venue_format 
ON matches (venue_id, format, match_date);

-- 4. Composite index for team match history
-- Query: WHERE (team_a_id = :tid OR team_b_id = :tid) AND format = :fmt
CREATE INDEX IF NOT EXISTS idx_matches_team_format_date 
ON matches (format, match_date DESC)
INCLUDE (team_a_id, team_b_id, winner_id, venue_id, competition_id, season_id, win_margin, win_type, result_type);

-- 5. Composite index for dashboard summary
-- Query: COUNT(*) on players/teams/matches/venues
-- Already efficient with sequential scan on small tables
-- No additional index needed

-- 6. Index for player_form sorted by score
-- Query: ORDER BY form_score DESC (already exists: idx_pform_score)
-- No additional index needed

-- 7. Composite index for match batting summary player lookups
-- Used by: player_by_year, player_by_competition, player_by_season, player_vs_opponent
-- These join match_batting_summary -> matches -> (competitions|seasons|teams)
-- The existing idx_mbs_player + idx_mbs_match indexes work well for these
-- No additional index needed
