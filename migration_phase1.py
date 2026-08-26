"""
Phase 1 Migration: Universal Cricket Data Model
=================================================

Non-destructive migration that adds new columns and tables
for format-agnostic cricket representation.

Does NOT drop any existing tables or columns.
Adds backward-compatible extensions.

Usage:
    python migration_phase1.py          # Run migration
    python migration_phase1.py --dry-run # Show what would be done
    python migration_phase1.py --verify  # Verify migration succeeded
"""

import os
import sys
import argparse
import logging
from pathlib import Path

from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ============================================================
# Migration SQL Statements
# ============================================================

MIGRATION_SQL = [
    # ----------------------------------------------------------
    # 1. Add result_type to matches table
    # ----------------------------------------------------------
    ("Add matches.result_type",
     "ALTER TABLE matches ADD COLUMN IF NOT EXISTS result_type VARCHAR(30) "
     "DEFAULT 'win'"),

    # 2. Add day_number to matches for multi-day Test support
    ("Add matches.day_number",
     "ALTER TABLE matches ADD COLUMN IF NOT EXISTS day_number INTEGER"),

    # 3. Add event_match_number to matches
    ("Add matches.event_match_number",
     "ALTER TABLE matches ADD COLUMN IF NOT EXISTS event_match_number INTEGER"),

    # ----------------------------------------------------------
    # 4. Add innings structural columns for Test support
    # ----------------------------------------------------------
    ("Add innings.declared",
     "ALTER TABLE innings ADD COLUMN IF NOT EXISTS declared BOOLEAN DEFAULT FALSE"),

    ("Add innings.all_out",
     "ALTER TABLE innings ADD COLUMN IF NOT EXISTS all_out BOOLEAN DEFAULT FALSE"),

    ("Add innings.follow_on",
     "ALTER TABLE innings ADD COLUMN IF NOT EXISTS follow_on BOOLEAN DEFAULT FALSE"),

    # ----------------------------------------------------------
    # 5. Create seasons table
    # ----------------------------------------------------------
    ("Create seasons table",
     """
     CREATE TABLE IF NOT EXISTS seasons (
         id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
         competition_id UUID NOT NULL REFERENCES competitions(id),
         name VARCHAR(50) NOT NULL,
         start_date DATE,
         end_date DATE,
         aliases TEXT[],
         created_at TIMESTAMP DEFAULT NOW(),
         updated_at TIMESTAMP DEFAULT NOW(),
         UNIQUE(competition_id, name)
     )
     """),

    # 6. Add season_id to matches
    ("Add matches.season_id",
     "ALTER TABLE matches ADD COLUMN IF NOT EXISTS season_id "
     "UUID REFERENCES seasons(id)"),

    # ----------------------------------------------------------
    # 7. Add competition_type and governing_body defaults
    # ----------------------------------------------------------
    ("Add competitions.competition_type",
     "ALTER TABLE competitions ADD COLUMN IF NOT EXISTS competition_type "
     "VARCHAR(50) DEFAULT 'league'"),

    # ----------------------------------------------------------
    # 8. Add team_type to teams
    # ----------------------------------------------------------
    ("Add teams.team_type",
     "ALTER TABLE teams ADD COLUMN IF NOT EXISTS team_type "
     "VARCHAR(50) DEFAULT 'franchise'"),

    # ----------------------------------------------------------
    # 9. Create format_config reference table
    # ----------------------------------------------------------
    ("Create format_config table",
     """
     CREATE TABLE IF NOT EXISTS format_config (
         id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
         format VARCHAR(20) NOT NULL UNIQUE,
         standard_overs INTEGER,
         powerplay_end INTEGER,
         middle_end INTEGER,
         max_innings INTEGER DEFAULT 2,
         is_multi_day BOOLEAN DEFAULT FALSE,
         is_first_class BOOLEAN DEFAULT FALSE,
         description TEXT,
         created_at TIMESTAMP DEFAULT NOW()
     )
     """),

    # ----------------------------------------------------------
    # 10. Insert format configurations
    # ----------------------------------------------------------
    ("Insert T20 format config",
     """
     INSERT INTO format_config (format, standard_overs, powerplay_end, middle_end, max_innings, is_multi_day, is_first_class, description)
     VALUES ('T20', 20, 6, 15, 2, FALSE, FALSE, 'T20 franchise cricket (IPL, BBL, etc.)')
     ON CONFLICT (format) DO NOTHING
     """),

    ("Insert T20I format config",
     """
     INSERT INTO format_config (format, standard_overs, powerplay_end, middle_end, max_innings, is_multi_day, is_first_class, description)
     VALUES ('T20I', 20, 6, 15, 2, FALSE, FALSE, 'International T20 cricket')
     ON CONFLICT (format) DO NOTHING
     """),

    ("Insert ODI format config",
     """
     INSERT INTO format_config (format, standard_overs, powerplay_end, middle_end, max_innings, is_multi_day, is_first_class, description)
     VALUES ('ODI', 50, 10, 40, 2, FALSE, FALSE, 'One Day International cricket')
     ON CONFLICT (format) DO NOTHING
     """),

    ("Insert Test format config",
     """
     INSERT INTO format_config (format, standard_overs, powerplay_end, middle_end, max_innings, is_multi_day, is_first_class, description)
     VALUES ('Test', 90, 0, 0, 4, TRUE, TRUE, 'Test cricket (up to 5 days)')
     ON CONFLICT (format) DO NOTHING
     """),

    # ----------------------------------------------------------
    # 11. Add indexes for new query patterns
    # ----------------------------------------------------------
    ("Create index matches.result_type",
     "CREATE INDEX IF NOT EXISTS idx_matches_result_type ON matches(result_type)"),

    ("Create index matches.season_id",
     "CREATE INDEX IF NOT EXISTS idx_matches_season ON matches(season_id)"),

    ("Create index seasons.competition",
     "CREATE INDEX IF NOT EXISTS idx_seasons_competition ON seasons(competition_id)"),

    ("Create index format_config.format",
     "CREATE INDEX IF NOT EXISTS idx_format_config_format ON format_config(format)"),

    # ----------------------------------------------------------
    # 12. Add index on player_batting_stats for multi-format queries
    # ----------------------------------------------------------
    ("Create composite index pbs_player_format",
     "CREATE INDEX IF NOT EXISTS idx_pbs_player_format ON player_batting_stats(player_id, format)"),

    ("Create composite index pws_player_format",
     "CREATE INDEX IF NOT EXISTS idx_pws_player_format ON player_bowling_stats(player_id, format)"),

    # ----------------------------------------------------------
    # 13. Add composite indexes for matchup queries
    # ----------------------------------------------------------
    ("Create composite index bbm_batter_format",
     "CREATE INDEX IF NOT EXISTS idx_bbm_batter_format ON batter_bowler_matchups(batter_id, format)"),

    ("Create composite index bbm_bowler_format",
     "CREATE INDEX IF NOT EXISTS idx_bbm_bowler_format ON batter_bowler_matchups(bowler_id, format)"),
]


# ============================================================
# Data Migration: Populate new columns from existing data
# ============================================================

DATA_MIGRATION_SQL = [
    # Set result_type for existing matches that have a winner
    ("Set result_type for won matches",
     """
     UPDATE matches SET result_type = 'win'
     WHERE result_type = 'win' AND winner_id IS NOT NULL
     """),

    # Set result_type for matches without a winner
    ("Set result_type for no-result matches",
     """
     UPDATE matches SET result_type = 'no_result'
     WHERE winner_id IS NULL AND result_type = 'win'
     """),

    # Populate team_type from country field
    ("Set team_type for national teams",
     """
     UPDATE teams SET team_type = 'national'
     WHERE country IS NOT NULL
     AND country NOT IN ('')
     AND canonical_name IN (
         'India', 'Australia', 'England', 'South Africa', 'New Zealand',
         'Pakistan', 'Sri Lanka', 'West Indies', 'Bangladesh', 'Afghanistan',
         'Zimbabwe', 'Ireland', 'Netherlands', 'Scotland', 'UAE', 'Nepal', 'Namibia'
     )
     """),
]


# ============================================================
# Migration Runner
# ============================================================


def get_engine():
    """Create SQLAlchemy engine from DATABASE_URL."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set in environment")
    return create_engine(db_url, pool_pre_ping=True)


def get_existing_columns(engine, table_name: str) -> set:
    """Get existing column names for a table."""
    inspector = inspect(engine)
    try:
        columns = {col["name"] for col in inspector.get_columns(table_name)}
    except Exception:
        columns = set()
    return columns


def get_existing_tables(engine) -> set:
    """Get existing table names."""
    inspector = inspect(engine)
    return set(inspector.get_table_names())


def run_migration(dry_run: bool = False):
    """Run the Phase 1 migration."""
    engine = get_engine()

    logger.info("=" * 60)
    logger.info("Phase 1 Migration: Universal Cricket Data Model")
    logger.info("=" * 60)

    # Pre-check: existing state
    existing_tables = get_existing_tables(engine)
    logger.info(f"Existing tables: {len(existing_tables)}")

    results = {"success": 0, "skipped": 0, "failed": 0}

    for description, sql in MIGRATION_SQL:
        if dry_run:
            logger.info(f"  [DRY RUN] {description}")
            results["skipped"] += 1
            continue

        try:
            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            logger.info(f"  ✅ {description}")
            results["success"] += 1
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                logger.info(f"  ⏭️  {description} (already exists)")
                results["skipped"] += 1
            else:
                logger.error(f"  ❌ {description}: {error_msg}")
                results["failed"] += 1

    # Data migration
    logger.info("\n--- Data Migration ---")
    for description, sql in DATA_MIGRATION_SQL:
        if dry_run:
            logger.info(f"  [DRY RUN] {description}")
            continue

        try:
            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            logger.info(f"  ✅ {description}")
        except Exception as e:
            logger.warning(f"  ⚠️  {description}: {str(e)[:100]}")

    # Post-check
    logger.info("\n--- Post-Migration State ---")
    new_tables = get_existing_tables(engine)
    added_tables = new_tables - existing_tables
    if added_tables:
        logger.info(f"New tables: {added_tables}")

    for table in ["matches", "innings", "seasons", "format_config", "teams", "competitions"]:
        cols = get_existing_columns(engine, table)
        logger.info(f"  {table}: {len(cols)} columns")

    engine.dispose()

    logger.info(f"\nMigration complete: {results['success']} succeeded, "
                f"{results['skipped']} skipped, {results['failed']} failed")
    return results["failed"] == 0


def verify_migration():
    """Verify the migration succeeded."""
    engine = get_engine()
    logger.info("Verifying Phase 1 migration...")

    checks = {
        "format_config table": "SELECT COUNT(*) FROM format_config",
        "T20 config": "SELECT COUNT(*) FROM format_config WHERE format = 'T20'",
        "T20I config": "SELECT COUNT(*) FROM format_config WHERE format = 'T20I'",
        "ODI config": "SELECT COUNT(*) FROM format_config WHERE format = 'ODI'",
        "Test config": "SELECT COUNT(*) FROM format_config WHERE format = 'Test'",
        "matches.result_type column": (
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'matches' AND column_name = 'result_type'"
        ),
        "innings.declared column": (
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'innings' AND column_name = 'declared'"
        ),
        "innings.all_out column": (
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'innings' AND column_name = 'all_out'"
        ),
        "seasons table exists": (
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'seasons'"
        ),
        "matches.season_id column": (
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'matches' AND column_name = 'season_id'"
        ),
        "teams.team_type column": (
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'teams' AND column_name = 'team_type'"
        ),
    }

    all_pass = True
    for check_name, sql in checks.items():
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql)).scalar()
                if result and result > 0:
                    logger.info(f"  ✅ {check_name}: {result}")
                else:
                    logger.error(f"  ❌ {check_name}: {result}")
                    all_pass = False
        except Exception as e:
            logger.error(f"  ❌ {check_name}: {e}")
            all_pass = False

    # Regression check: existing IPL data should be intact
    regression = {
        "matches count": "SELECT COUNT(*) FROM matches",
        "deliveries count": "SELECT COUNT(*) FROM deliveries",
        "players count": "SELECT COUNT(*) FROM players",
        "teams count": "SELECT COUNT(*) FROM teams",
    }
    logger.info("\n--- Regression Check ---")
    for check_name, sql in regression.items():
        with engine.connect() as conn:
            result = conn.execute(text(sql)).scalar()
            logger.info(f"  {check_name}: {result}")

    engine.dispose()
    return all_pass


def main():
    parser = argparse.ArgumentParser(description="Phase 1 Database Migration")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--verify", action="store_true", help="Verify migration")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.verify:
        success = verify_migration()
    else:
        success = run_migration(dry_run=args.dry_run)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
