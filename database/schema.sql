-- ============================================================
-- Cricket Intelligence Platform — Canonical PostgreSQL Schema
-- ============================================================
-- Audit v2 — fixes applied:
--   1. Views use 'T20' (matches current pipeline output)
--   2. Removed chasing_average from batting_stats (never computed)
--   3. Removed duplicate deliveries(match_id) index
--   4. Added all phase columns the pipeline writes
--   5. ORM-matching: all pipeline-written columns present
--
-- Coverage note:
--   Historical ball-by-ball analytics currently cover the
--   Cricsheet period: Tests from Dec 2001, ODIs from Jun 2002,
--   T20Is from Feb 2005, IPL from 2008.
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for fuzzy text search on names

-- ============================================================
-- CORE ENTITIES
-- ============================================================

CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_name VARCHAR(100) NOT NULL UNIQUE,
    short_name VARCHAR(20) NOT NULL,
    country VARCHAR(100),
    team_type VARCHAR(50) DEFAULT 'franchise',  -- 'national', 'franchise', 'domestic'
    icc_id VARCHAR(50),           -- ICC official identifier (future use)
    aliases TEXT[],               -- alternative names for matching (future use)
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE players (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    canonical_name VARCHAR(200) NOT NULL,
    full_name VARCHAR(300),
    country VARCHAR(100),
    team_id UUID REFERENCES teams(id),
    date_of_birth DATE,           -- future use
    role VARCHAR(50),             -- 'batsman', 'bowler', 'allrounder', 'wicketkeeper'
    batting_style VARCHAR(50),    -- 'right_hand', 'left_hand'
    bowling_style VARCHAR(50),    -- 'right_arm_fast', 'left_arm_orthodox', etc.
    bowling_type VARCHAR(30),     -- 'pace', 'spin', 'medium'
    icc_id VARCHAR(50),           -- future use
    cricsheet_id VARCHAR(50),     -- future use
    aliases TEXT[],               -- future use
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE venues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    city VARCHAR(100),
    country VARCHAR(100),
    capacity INTEGER,
    aliases TEXT[],               -- future use
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE competitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    short_name VARCHAR(50),
    format VARCHAR(20) NOT NULL,  -- 'T20I', 'ODI', 'Test', 'T20', 'T10'
    competition_type VARCHAR(50) DEFAULT 'league',  -- 'league', 'tournament', 'bilateral', 'test_series'
    governing_body VARCHAR(100),
    season VARCHAR(20),           -- '2023-24', '2024'
    aliases TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Season/Edition table (Phase 1: universal model)
CREATE TABLE seasons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competition_id UUID NOT NULL REFERENCES competitions(id),
    name VARCHAR(50) NOT NULL,
    start_date DATE,
    end_date DATE,
    aliases TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(competition_id, name)
);

-- Format-specific configuration (Phase 1: universal model)
CREATE TABLE format_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    format VARCHAR(20) NOT NULL UNIQUE,
    standard_overs INTEGER,
    powerplay_end INTEGER,       -- Last over of powerplay (0-indexed)
    middle_end INTEGER,          -- Last over of middle phase (0-indexed)
    max_innings INTEGER DEFAULT 2,
    is_multi_day BOOLEAN DEFAULT FALSE,
    is_first_class BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed format configurations
INSERT INTO format_config (format, standard_overs, powerplay_end, middle_end, max_innings, is_multi_day, is_first_class, description) VALUES
    ('T20', 20, 6, 15, 2, FALSE, FALSE, 'T20 franchise cricket (IPL, BBL, etc.)'),
    ('T20I', 20, 6, 15, 2, FALSE, FALSE, 'International T20 cricket'),
    ('ODI', 50, 10, 40, 2, FALSE, FALSE, 'One Day International cricket'),
    ('Test', 90, 0, 0, 4, TRUE, TRUE, 'Test cricket (up to 5 days)')
ON CONFLICT (format) DO NOTHING;

-- ============================================================
-- MATCH DATA
-- ============================================================

CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(100) UNIQUE,  -- Cricsheet match ID
    competition_id UUID REFERENCES competitions(id),
    season_id UUID REFERENCES seasons(id),  -- Phase 1: link to season
    venue_id UUID REFERENCES venues(id),
    match_date DATE NOT NULL,
    format VARCHAR(20) NOT NULL,

    team_a_id UUID REFERENCES teams(id),
    team_b_id UUID REFERENCES teams(id),

    toss_winner_id UUID REFERENCES teams(id),
    toss_decision VARCHAR(20),    -- 'bat', 'field'

    winner_id UUID REFERENCES teams(id),
    win_margin INTEGER,
    win_type VARCHAR(30),         -- 'runs', 'wickets', 'innings', 'DLS'
    result_type VARCHAR(30) DEFAULT 'win',  -- 'win', 'tie', 'draw', 'no_result', 'abandoned'

    player_of_match_id UUID REFERENCES players(id),

    total_innings INTEGER,        -- 2, 3, or 4
    total_deliveries INTEGER,

    day_number INTEGER,           -- For multi-day matches
    event_match_number INTEGER,   -- Match number within event/series

    is_live BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE innings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    innings_number INTEGER NOT NULL CHECK (innings_number BETWEEN 1 AND 6),  -- up to 6 for super overs
    batting_team_id UUID NOT NULL REFERENCES teams(id),
    bowling_team_id UUID NOT NULL REFERENCES teams(id),

    total_runs INTEGER DEFAULT 0,
    total_wickets INTEGER DEFAULT 0,
    total_overs DECIMAL(4,1) DEFAULT 0,

    -- Extras (future use — pipeline doesn't compute these yet)
    extras_wides INTEGER DEFAULT 0,
    extras_noballs INTEGER DEFAULT 0,
    extras_byes INTEGER DEFAULT 0,
    extras_legbyes INTEGER DEFAULT 0,
    extras_penalty INTEGER DEFAULT 0,
    total_extras INTEGER DEFAULT 0,

    run_rate DECIMAL(6,2),

    -- Phase 1: Test cricket support
    declared BOOLEAN DEFAULT FALSE,
    all_out BOOLEAN DEFAULT FALSE,
    follow_on BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(match_id, innings_number)
);

-- ============================================================
-- BALL-BY-BALL DATA
-- ============================================================

CREATE TABLE deliveries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    innings_id UUID NOT NULL REFERENCES innings(id) ON DELETE CASCADE,
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,

    over_number INTEGER NOT NULL,
    ball_in_over INTEGER NOT NULL CHECK (ball_in_over BETWEEN 1 AND 12),  -- up to 12 to handle wides in an over

    -- Batsman info
    striker_id UUID REFERENCES players(id),
    non_striker_id UUID REFERENCES players(id),
    bowler_id UUID REFERENCES players(id),

    -- Result
    runs_bat INTEGER DEFAULT 0,
    runs_extras INTEGER DEFAULT 0,
    total_runs INTEGER DEFAULT 0,

    -- Extra details
    extra_type VARCHAR(20),       -- 'wide', 'noball', 'bye', 'legbye', 'penalty'

    -- Dismissal
    is_wicket BOOLEAN DEFAULT FALSE,
    wicket_type VARCHAR(30),      -- 'bowled', 'caught', 'lbw', 'run_out', etc.
    dismissed_player_id UUID REFERENCES players(id),
    fielder_id UUID REFERENCES players(id),  -- future use

    -- Computed (future use — pipeline doesn't populate these yet)
    cumulative_runs INTEGER,
    cumulative_wickets INTEGER,
    current_over DECIMAL(4,1),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_deliveries_innings ON deliveries(innings_id);
CREATE INDEX idx_deliveries_match ON deliveries(match_id);
CREATE INDEX idx_deliveries_striker ON deliveries(striker_id);
CREATE INDEX idx_deliveries_bowler ON deliveries(bowler_id);

-- ============================================================
-- PLAYER IDENTITY MAPPING
-- ============================================================

CREATE TABLE player_name_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,  -- 'cricsheet', 'icc', 'manual'
    source_id VARCHAR(100),
    name_variant VARCHAR(300) NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(source, name_variant)
);

CREATE TABLE team_name_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(100),
    name_variant VARCHAR(300) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(source, name_variant)
);

-- ============================================================
-- ANALYTICAL TABLES (Precomputed by pipeline)
-- ============================================================

-- Player batting statistics
CREATE TABLE player_batting_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    format VARCHAR(20) NOT NULL,
    period VARCHAR(20) NOT NULL,  -- 'career', 'last_30_days', 'last_6_months'

    matches INTEGER DEFAULT 0,
    innings INTEGER DEFAULT 0,
    not_outs INTEGER DEFAULT 0,
    runs INTEGER DEFAULT 0,
    highest_score INTEGER,
    batting_average DECIMAL(8,2),
    strike_rate DECIMAL(8,2),
    balls_faced INTEGER DEFAULT 0,

    fours INTEGER DEFAULT 0,
    sixes INTEGER DEFAULT 0,
    boundary_pct DECIMAL(5,2),
    dot_ball_pct DECIMAL(5,2),

    fifties INTEGER DEFAULT 0,
    hundreds INTEGER DEFAULT 0,

    consistency_score DECIMAL(5,2),

    -- Phase-specific batting
    powerplay_runs INTEGER DEFAULT 0,
    powerplay_strike_rate DECIMAL(8,2),
    middle_runs INTEGER DEFAULT 0,
    middle_strike_rate DECIMAL(8,2),
    death_runs INTEGER DEFAULT 0,
    death_strike_rate DECIMAL(8,2),

    -- Situational
    chasing_runs INTEGER DEFAULT 0,
    chasing_strike_rate DECIMAL(8,2),
    first_innings_runs INTEGER DEFAULT 0,
    first_innings_strike_rate DECIMAL(8,2),

    calculated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(player_id, format, period)
);

CREATE INDEX idx_pbs_player ON player_batting_stats(player_id);
CREATE INDEX idx_pbs_format_period ON player_batting_stats(format, period);

-- Player bowling statistics
CREATE TABLE player_bowling_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    format VARCHAR(20) NOT NULL,
    period VARCHAR(20) NOT NULL,

    matches INTEGER DEFAULT 0,
    innings INTEGER DEFAULT 0,
    overs DECIMAL(8,1) DEFAULT 0,
    balls_bowled INTEGER DEFAULT 0,
    maidens INTEGER DEFAULT 0,
    wickets INTEGER DEFAULT 0,
    runs_conceded INTEGER DEFAULT 0,
    bowling_average DECIMAL(8,2),
    strike_rate DECIMAL(8,2),
    economy DECIMAL(8,2),
    best_bowling VARCHAR(20),

    four_wickets INTEGER DEFAULT 0,
    five_wickets INTEGER DEFAULT 0,

    dot_ball_pct DECIMAL(5,2),
    boundary_conceded_pct DECIMAL(5,2),

    -- Phase-specific bowling
    powerplay_overs DECIMAL(8,1) DEFAULT 0,
    powerplay_wickets INTEGER DEFAULT 0,
    powerplay_economy DECIMAL(8,2),
    middle_overs DECIMAL(8,1) DEFAULT 0,
    middle_wickets INTEGER DEFAULT 0,
    middle_economy DECIMAL(8,2),
    death_overs DECIMAL(8,1) DEFAULT 0,
    death_wickets INTEGER DEFAULT 0,
    death_economy DECIMAL(8,2),

    calculated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(player_id, format, period)
);

CREATE INDEX idx_pws_player ON player_bowling_stats(player_id);
CREATE INDEX idx_pws_format_period ON player_bowling_stats(format, period);

-- Player Form Score (original project metric)
CREATE TABLE player_form (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    format VARCHAR(20) NOT NULL,

    form_score DECIMAL(5,2) NOT NULL,
    recent_performance_component DECIMAL(5,2),  -- weight: 35%
    consistency_component DECIMAL(5,2),          -- weight: 20%
    opposition_strength_component DECIMAL(5,2),  -- weight: 15%
    venue_performance_component DECIMAL(5,2),    -- weight: 10%
    match_situation_component DECIMAL(5,2),      -- weight: 10%
    efficiency_component DECIMAL(5,2),           -- weight: 10%

    recent_innings_count INTEGER,
    last_calculated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(player_id, format)
);

CREATE INDEX idx_pf_player ON player_form(player_id);

-- Player Impact (future: Actual vs Expected performance)
CREATE TABLE player_impact (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    match_id UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,

    format VARCHAR(20) NOT NULL,
    impact_type VARCHAR(20) NOT NULL,  -- 'batting', 'bowling'

    expected_runs DECIMAL(8,2),
    actual_runs INTEGER,
    runs_above_expected DECIMAL(8,2),

    expected_runs_conceded DECIMAL(8,2),
    actual_runs_conceded INTEGER,
    runs_saved DECIMAL(8,2),

    match_situation VARCHAR(50),
    impact_score DECIMAL(8,2),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pi_player ON player_impact(player_id);
CREATE INDEX idx_pi_match ON player_impact(match_id);

-- ============================================================
-- TEAM ANALYTICS
-- ============================================================

CREATE TABLE team_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    format VARCHAR(20) NOT NULL,
    period VARCHAR(20) NOT NULL,

    matches INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    ties INTEGER DEFAULT 0,
    no_results INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2),

    -- Batting strength
    avg_first_innings_score DECIMAL(8,2),
    avg_second_innings_score DECIMAL(8,2),
    avg_powerplay_score DECIMAL(8,2),
    avg_middle_overs_score DECIMAL(8,2),
    avg_death_overs_score DECIMAL(8,2),
    avg_total_score DECIMAL(8,2),

    -- Bowling strength
    avg_runs_conceded_per_innings DECIMAL(8,2),
    avg_wickets_per_innings DECIMAL(8,2),
    avg_economy DECIMAL(8,2),
    avg_powerplay_economy DECIMAL(8,2),
    avg_middle_economy DECIMAL(8,2),
    avg_death_economy DECIMAL(8,2),

    -- Situational
    chasing_win_pct DECIMAL(5,2),
    defending_win_pct DECIMAL(5,2),

    batting_strength_score DECIMAL(5,2),
    bowling_strength_score DECIMAL(5,2),
    overall_strength_score DECIMAL(5,2),

    calculated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(team_id, format, period)
);

CREATE INDEX idx_tp_team ON team_performance(team_id);
CREATE INDEX idx_tp_format_period ON team_performance(format, period);

-- ============================================================
-- VENUE ANALYTICS
-- ============================================================

CREATE TABLE venue_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    venue_id UUID NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
    format VARCHAR(20) NOT NULL,

    total_matches INTEGER DEFAULT 0,
    avg_first_innings_score DECIMAL(8,2),
    avg_second_innings_score DECIMAL(8,2),
    highest_total INTEGER,
    lowest_total INTEGER,

    chasing_wins INTEGER DEFAULT 0,
    defending_wins INTEGER DEFAULT 0,
    chasing_win_pct DECIMAL(5,2),

    -- Wicket distribution
    pace_wickets_pct DECIMAL(5,2),
    spin_wickets_pct DECIMAL(5,2),

    -- Phase-wise scoring
    avg_powerplay_runs DECIMAL(8,2),
    avg_middle_overs_runs DECIMAL(8,2),
    avg_death_overs_runs DECIMAL(8,2),

    -- Boundary frequency
    avg_fours_per_match DECIMAL(8,2),
    avg_sixes_per_match DECIMAL(8,2),
    boundary_frequency DECIMAL(5,2),

    -- Toss impact
    toss_bat_first_win_pct DECIMAL(5,2),
    toss_field_first_win_pct DECIMAL(5,2),

    calculated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(venue_id, format)
);

CREATE INDEX idx_vs_venue ON venue_stats(venue_id);

-- ============================================================
-- MATCHUP DATA
-- ============================================================

CREATE TABLE batter_bowler_matchups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batter_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    bowler_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    format VARCHAR(20) NOT NULL,

    total_balls INTEGER DEFAULT 0,
    total_runs INTEGER DEFAULT 0,
    total_wickets INTEGER DEFAULT 0,
    strike_rate DECIMAL(8,2),
    batting_average DECIMAL(8,2),
    dot_balls INTEGER DEFAULT 0,
    boundaries INTEGER DEFAULT 0,
    sixes INTEGER DEFAULT 0,

    calculated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(batter_id, bowler_id, format)
);

CREATE INDEX idx_bbm_batter ON batter_bowler_matchups(batter_id);
CREATE INDEX idx_bbm_bowler ON batter_bowler_matchups(bowler_id);

-- Contextual matchups (batter vs bowling type) — future use
CREATE TABLE batter_type_matchups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batter_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    bowling_type VARCHAR(50) NOT NULL,
    bowling_arm VARCHAR(20),
    format VARCHAR(20) NOT NULL,

    total_balls INTEGER DEFAULT 0,
    total_runs INTEGER DEFAULT 0,
    total_wickets INTEGER DEFAULT 0,
    strike_rate DECIMAL(8,2),
    dot_balls INTEGER DEFAULT 0,
    boundaries INTEGER DEFAULT 0,

    calculated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(batter_id, bowling_type, bowling_arm, format)
);

-- ============================================================
-- RANKINGS
-- ============================================================

CREATE TABLE rankings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id),

    format VARCHAR(20) NOT NULL,
    category VARCHAR(20) NOT NULL,  -- 'batting', 'bowling', 'allrounder'

    rank_position INTEGER,
    rating_points DECIMAL(8,2),
    career_best_rank INTEGER,
    points_change DECIMAL(8,2),

    period VARCHAR(20),
    source VARCHAR(50),             -- 'platform', 'icc'
    calculated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(player_id, format, category, source, period)
);

CREATE INDEX idx_rankings_format ON rankings(format, category, rank_position);

-- ============================================================
-- NEWS & LIVE DATA
-- ============================================================

CREATE TABLE news_articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    source VARCHAR(100),
    url VARCHAR(1000) NOT NULL,
    publication_date TIMESTAMP,
    description TEXT,
    category VARCHAR(50),
    image_url VARCHAR(1000),
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(url)
);

CREATE INDEX idx_news_date ON news_articles(publication_date DESC);

CREATE TABLE live_matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID REFERENCES matches(id),
    external_match_id VARCHAR(100),

    status VARCHAR(50),
    match_format VARCHAR(20),

    team_a_id UUID REFERENCES teams(id),
    team_b_id UUID REFERENCES teams(id),

    batting_team_id UUID REFERENCES teams(id),
    bowling_team_id UUID REFERENCES teams(id),

    current_score INTEGER,
    current_wickets INTEGER,
    current_overs DECIMAL(5,1),

    target INTEGER,
    required_run_rate DECIMAL(6,2),
    current_run_rate DECIMAL(6,2),
    projected_score INTEGER,

    win_probability_team_a DECIMAL(5,2),
    win_probability_team_b DECIMAL(5,2),

    current_striker_id UUID REFERENCES players(id),
    current_non_striker_id UUID REFERENCES players(id),
    current_bowler_id UUID REFERENCES players(id),

    last_updated TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TRIGGERS
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matches_updated_at BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_venues_updated_at BEFORE UPDATE ON venues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_competitions_updated_at BEFORE UPDATE ON competitions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- VIEWS
-- ============================================================

-- Quick player summary view — uses 'T20' (matches current pipeline output)
CREATE VIEW v_player_summary AS
SELECT
    p.id,
    p.canonical_name,
    p.role,
    p.batting_style,
    p.bowling_style,
    p.country,
    t.canonical_name as team_name,
    pbs.runs as career_runs,
    pbs.batting_average,
    pbs.strike_rate,
    pbs.innings as career_innings,
    pws.wickets as career_wickets,
    pws.economy as career_economy,
    pws.bowling_average,
    pf.form_score
FROM players p
LEFT JOIN teams t ON p.team_id = t.id
LEFT JOIN player_batting_stats pbs ON p.id = pbs.player_id AND pbs.format = 'T20' AND pbs.period = 'career'
LEFT JOIN player_bowling_stats pws ON p.id = pws.player_id AND pws.format = 'T20' AND pws.period = 'career'
LEFT JOIN player_form pf ON p.id = pf.player_id AND pf.format = 'T20';

-- Team summary view — uses 'T20' (matches current pipeline output)
CREATE VIEW v_team_summary AS
SELECT
    t.id,
    t.canonical_name,
    t.short_name,
    t.country,
    tp.matches,
    tp.win_rate,
    tp.batting_strength_score,
    tp.bowling_strength_score,
    tp.overall_strength_score
FROM teams t
LEFT JOIN team_performance tp ON t.id = tp.team_id AND tp.format = 'T20' AND tp.period = 'career';

-- ============================================================
-- INDEXES for common query patterns
-- ============================================================

CREATE INDEX idx_matches_date ON matches(match_date DESC);
CREATE INDEX idx_matches_format ON matches(format);
CREATE INDEX idx_matches_venue ON matches(venue_id);
CREATE INDEX idx_matches_competition ON matches(competition_id);
CREATE INDEX idx_matches_team_a ON matches(team_a_id);
CREATE INDEX idx_matches_team_b ON matches(team_b_id);

CREATE INDEX idx_innings_match ON innings(match_id);

CREATE INDEX idx_delivery_match ON deliveries(match_id);  -- single instance (no duplicate)
CREATE INDEX idx_delivery_bowler ON deliveries(bowler_id);

CREATE INDEX idx_pform_score ON player_form(form_score DESC);
CREATE INDEX idx_rankings_rating ON rankings(format, category, rating_points DESC);

-- Phase 1: Universal model indexes
CREATE INDEX IF NOT EXISTS idx_matches_result_type ON matches(result_type);
CREATE INDEX IF NOT EXISTS idx_matches_season ON matches(season_id);
CREATE INDEX IF NOT EXISTS idx_seasons_competition ON seasons(competition_id);
CREATE INDEX IF NOT EXISTS idx_format_config_format ON format_config(format);
CREATE INDEX IF NOT EXISTS idx_pbs_player_format ON player_batting_stats(player_id, format);
CREATE INDEX IF NOT EXISTS idx_pws_player_format ON player_bowling_stats(player_id, format);
CREATE INDEX IF NOT EXISTS idx_bbm_batter_format ON batter_bowler_matchups(batter_id, format);
CREATE INDEX IF NOT EXISTS idx_bbm_bowler_format ON batter_bowler_matchups(bowler_id, format);
