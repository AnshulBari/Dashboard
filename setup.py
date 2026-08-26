"""
Cricket Intelligence Platform — Setup Script
=============================================

Creates the database schema, seeds it with sample data,
and verifies the backend can query it.

Usage:
    python setup.py

Prerequisites:
    pip install -r backend/requirements.txt
"""

import os
import sys
import logging
import sqlite3

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def setup_database():
    """Create database, run schema, and seed data."""
    db_path = os.path.join(PROJECT_ROOT, "data", "cricket_intelligence.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    database_url = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = database_url
    
    logger.info(f"Database path: {db_path}")
    
    # Step 1: Create tables from schema.sql
    logger.info("Step 1: Creating schema...")
    schema_path = os.path.join(PROJECT_ROOT, "database", "schema.sql")
    
    if os.path.exists(schema_path):
        conn = sqlite3.connect(db_path)
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        
        # SQLite doesn't support PostgreSQL-specific syntax, so we need to adapt
        # For local dev with SQLite, create simplified tables
        _create_sqlite_schema(conn)
        conn.close()
        logger.info("  Schema created (SQLite-compatible)")
    else:
        logger.warning("  schema.sql not found, skipping")
    
    # Step 2: Seed with sample data
    logger.info("Step 2: Seeding database with sample data...")
    from data_pipeline.database.seeder import DatabaseSeeder
    seeder = DatabaseSeeder(database_url=database_url)
    seeder.seed_all()
    
    # Step 3: Verify data
    logger.info("Step 3: Verifying data...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = {
        "teams": "SELECT COUNT(*) FROM teams",
        "players": "SELECT COUNT(*) FROM players",
        "venues": "SELECT COUNT(*) FROM venues",
        "matches": "SELECT COUNT(*) FROM matches",
        "player_batting_stats": "SELECT COUNT(*) FROM player_batting_stats",
        "player_bowling_stats": "SELECT COUNT(*) FROM player_bowling_stats",
        "player_form": "SELECT COUNT(*) FROM player_form",
        "team_performance": "SELECT COUNT(*) FROM team_performance",
        "venue_stats": "SELECT COUNT(*) FROM venue_stats",
    }
    
    for table, query in tables.items():
        try:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            logger.info(f"  {table}: {count} rows")
        except Exception as e:
            logger.warning(f"  {table}: error - {e}")
    
    conn.close()
    logger.info("")
    logger.info("=" * 50)
    logger.info("Setup complete!")
    logger.info("")
    logger.info("To start the backend:")
    logger.info(f"  DATABASE_URL='{database_url}'")
    logger.info(f"  cd backend && uvicorn backend.main:app --reload --port 8000")
    logger.info("")
    logger.info("To start the frontend:")
    logger.info("  cd frontend && npm run dev")
    logger.info("=" * 50)


def _create_sqlite_schema(conn):
    """Create a SQLite-compatible schema."""
    cursor = conn.cursor()
    
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS teams (
        id TEXT PRIMARY KEY,
        canonical_name TEXT NOT NULL UNIQUE,
        short_name TEXT NOT NULL,
        country TEXT,
        team_type TEXT DEFAULT 'franchise',
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS players (
        id TEXT PRIMARY KEY,
        canonical_name TEXT NOT NULL,
        full_name TEXT,
        country TEXT,
        team_id TEXT REFERENCES teams(id),
        role TEXT,
        batting_style TEXT,
        bowling_style TEXT,
        bowling_type TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS venues (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        city TEXT,
        country TEXT,
        capacity INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS competitions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        short_name TEXT,
        format TEXT NOT NULL,
        competition_type TEXT DEFAULT 'league',
        governing_body TEXT,
        season TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS seasons (
        id TEXT PRIMARY KEY,
        competition_id TEXT NOT NULL REFERENCES competitions(id),
        name TEXT NOT NULL,
        start_date DATE,
        end_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS format_config (
        id TEXT PRIMARY KEY,
        format TEXT NOT NULL UNIQUE,
        standard_overs INTEGER,
        powerplay_end INTEGER,
        middle_end INTEGER,
        max_innings INTEGER DEFAULT 2,
        is_multi_day BOOLEAN DEFAULT 0,
        is_first_class BOOLEAN DEFAULT 0,
        description TEXT
    );
    
    CREATE TABLE IF NOT EXISTS matches (
        id TEXT PRIMARY KEY,
        external_id TEXT UNIQUE,
        competition_id TEXT REFERENCES competitions(id),
        season_id TEXT REFERENCES seasons(id),
        venue_id TEXT REFERENCES venues(id),
        match_date DATE NOT NULL,
        format TEXT NOT NULL,
        team_a_id TEXT REFERENCES teams(id),
        team_b_id TEXT REFERENCES teams(id),
        toss_winner_id TEXT,
        toss_decision TEXT,
        winner_id TEXT REFERENCES teams(id),
        win_margin INTEGER,
        win_type TEXT,
        result_type TEXT DEFAULT 'win',
        player_of_match_id TEXT REFERENCES players(id),
        total_innings INTEGER,
        total_deliveries INTEGER,
        day_number INTEGER,
        event_match_number INTEGER,
        is_live BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS innings (
        id TEXT PRIMARY KEY,
        match_id TEXT NOT NULL REFERENCES matches(id),
        innings_number INTEGER NOT NULL,
        batting_team_id TEXT REFERENCES teams(id),
        bowling_team_id TEXT REFERENCES teams(id),
        total_runs INTEGER DEFAULT 0,
        total_wickets INTEGER DEFAULT 0,
        total_overs REAL DEFAULT 0,
        extras_wides INTEGER DEFAULT 0,
        extras_noballs INTEGER DEFAULT 0,
        extras_byes INTEGER DEFAULT 0,
        extras_legbyes INTEGER DEFAULT 0,
        extras_penalty INTEGER DEFAULT 0,
        total_extras INTEGER DEFAULT 0,
        run_rate REAL,
        declared BOOLEAN DEFAULT 0,
        all_out BOOLEAN DEFAULT 0,
        follow_on BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(match_id, innings_number)
    );
    
    CREATE TABLE IF NOT EXISTS deliveries (
        id TEXT PRIMARY KEY,
        innings_id TEXT NOT NULL REFERENCES innings(id),
        match_id TEXT NOT NULL REFERENCES matches(id),
        over_number INTEGER NOT NULL,
        ball_in_over INTEGER NOT NULL,
        striker_id TEXT REFERENCES players(id),
        non_striker_id TEXT REFERENCES players(id),
        bowler_id TEXT REFERENCES players(id),
        runs_bat INTEGER DEFAULT 0,
        runs_extras INTEGER DEFAULT 0,
        total_runs INTEGER DEFAULT 0,
        extra_type TEXT,
        is_wicket BOOLEAN DEFAULT 0,
        wicket_type TEXT,
        dismissed_player_id TEXT REFERENCES players(id),
        fielder_id TEXT REFERENCES players(id),
        cumulative_runs INTEGER,
        cumulative_wickets INTEGER,
        current_over REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS player_batting_stats (
        id TEXT PRIMARY KEY,
        player_id TEXT NOT NULL REFERENCES players(id),
        format TEXT NOT NULL,
        period TEXT NOT NULL,
        matches INTEGER DEFAULT 0,
        innings INTEGER DEFAULT 0,
        not_outs INTEGER DEFAULT 0,
        runs INTEGER DEFAULT 0,
        highest_score INTEGER,
        batting_average REAL,
        strike_rate REAL,
        balls_faced INTEGER DEFAULT 0,
        fours INTEGER DEFAULT 0,
        sixes INTEGER DEFAULT 0,
        boundary_pct REAL,
        dot_ball_pct REAL,
        fifties INTEGER DEFAULT 0,
        hundreds INTEGER DEFAULT 0,
        powerplay_runs INTEGER DEFAULT 0,
        powerplay_strike_rate REAL,
        middle_runs INTEGER DEFAULT 0,
        middle_strike_rate REAL,
        death_runs INTEGER DEFAULT 0,
        death_strike_rate REAL,
        chasing_runs INTEGER DEFAULT 0,
        chasing_strike_rate REAL,
        first_innings_runs INTEGER DEFAULT 0,
        first_innings_strike_rate REAL,
        consistency_score REAL,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(player_id, format, period)
    );
    
    CREATE TABLE IF NOT EXISTS player_bowling_stats (
        id TEXT PRIMARY KEY,
        player_id TEXT NOT NULL REFERENCES players(id),
        format TEXT NOT NULL,
        period TEXT NOT NULL,
        matches INTEGER DEFAULT 0,
        innings INTEGER DEFAULT 0,
        overs REAL DEFAULT 0,
        balls_bowled INTEGER DEFAULT 0,
        wickets INTEGER DEFAULT 0,
        runs_conceded INTEGER DEFAULT 0,
        bowling_average REAL,
        strike_rate REAL,
        economy REAL,
        dot_ball_pct REAL,
        boundary_conceded_pct REAL,
        powerplay_overs REAL DEFAULT 0,
        powerplay_wickets INTEGER DEFAULT 0,
        powerplay_economy REAL,
        middle_overs REAL DEFAULT 0,
        middle_wickets INTEGER DEFAULT 0,
        middle_economy REAL,
        death_overs REAL DEFAULT 0,
        death_wickets INTEGER DEFAULT 0,
        death_economy REAL,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(player_id, format, period)
    );
    
    CREATE TABLE IF NOT EXISTS player_form (
        id TEXT PRIMARY KEY,
        player_id TEXT NOT NULL REFERENCES players(id),
        format TEXT NOT NULL,
        form_score REAL NOT NULL,
        recent_performance_component REAL,
        consistency_component REAL,
        opposition_strength_component REAL,
        venue_performance_component REAL,
        match_situation_component REAL,
        efficiency_component REAL,
        recent_innings_count INTEGER,
        last_calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(player_id, format)
    );
    
    CREATE TABLE IF NOT EXISTS team_performance (
        id TEXT PRIMARY KEY,
        team_id TEXT NOT NULL REFERENCES teams(id),
        format TEXT NOT NULL,
        period TEXT NOT NULL,
        matches INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        win_rate REAL,
        avg_first_innings_score REAL,
        avg_second_innings_score REAL,
        avg_powerplay_score REAL,
        avg_middle_overs_score REAL,
        avg_death_overs_score REAL,
        avg_economy REAL,
        batting_strength_score REAL,
        bowling_strength_score REAL,
        overall_strength_score REAL,
        chasing_win_pct REAL,
        defending_win_pct REAL,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(team_id, format, period)
    );
    
    CREATE TABLE IF NOT EXISTS venue_stats (
        id TEXT PRIMARY KEY,
        venue_id TEXT NOT NULL REFERENCES venues(id),
        format TEXT NOT NULL,
        total_matches INTEGER DEFAULT 0,
        avg_first_innings_score REAL,
        avg_second_innings_score REAL,
        highest_total INTEGER,
        lowest_total INTEGER,
        chasing_wins INTEGER DEFAULT 0,
        defending_wins INTEGER DEFAULT 0,
        chasing_win_pct REAL,
        defending_win_pct REAL,
        pace_wickets_pct REAL,
        spin_wickets_pct REAL,
        avg_powerplay_runs REAL,
        avg_middle_overs_runs REAL,
        avg_death_overs_runs REAL,
        avg_fours_per_match REAL,
        avg_sixes_per_match REAL,
        boundary_frequency REAL,
        toss_bat_first_win_pct REAL,
        toss_field_first_win_pct REAL,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(venue_id, format)
    );
    
    CREATE TABLE IF NOT EXISTS batter_bowler_matchups (
        id TEXT PRIMARY KEY,
        batter_id TEXT NOT NULL REFERENCES players(id),
        bowler_id TEXT NOT NULL REFERENCES players(id),
        format TEXT NOT NULL,
        total_balls INTEGER DEFAULT 0,
        total_runs INTEGER DEFAULT 0,
        total_wickets INTEGER DEFAULT 0,
        strike_rate REAL,
        batting_average REAL,
        dot_balls INTEGER DEFAULT 0,
        boundaries INTEGER DEFAULT 0,
        sixes INTEGER DEFAULT 0,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(batter_id, bowler_id, format)
    );
    """)
    
    conn.commit()


if __name__ == "__main__":
    setup_database()
