"""
Migrate SQLite → PostgreSQL
============================
Reads all data from the local SQLite database and writes it to
the Supabase PostgreSQL database. Preserves all UUIDs as-is.

Usage:
    python migrate_sqlite_to_pg.py

Prerequisites:
    - DATABASE_URL set in .env pointing to Supabase
    - schema.sql already applied to Supabase
    - Local SQLite database exists at data/cricket_intelligence.db
"""

import os
import sys
import sqlite3
import logging
import time

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Source: local SQLite
SQLITE_PATH = os.path.join(os.path.dirname(__file__), "data", "cricket_intelligence.db")

# Destination: Supabase PostgreSQL (from .env)
PG_URL = os.getenv("DATABASE_URL")

# Tables in dependency order (parents first)
TABLES = [
    "teams",
    "players",
    "venues",
    "competitions",
    "matches",
    "innings",
    "deliveries",
    "player_batting_stats",
    "player_bowling_stats",
    "player_form",
    "team_performance",
    "venue_stats",
    "batter_bowler_matchups",
]


def migrate():
    if not os.path.exists(SQLITE_PATH):
        logger.error(f"SQLite database not found: {SQLITE_PATH}")
        sys.exit(1)

    if not PG_URL:
        logger.error("DATABASE_URL not set in environment")
        sys.exit(1)

    logger.info(f"Source: {SQLITE_PATH}")
    logger.info(f"Target: PostgreSQL (Supabase)")

    sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}")
    pg_engine = create_engine(PG_URL, pool_pre_ping=True)

    # Verify both connections
    with sqlite_engine.connect() as conn:
        logger.info(f"SQLite: connected")
    with pg_engine.connect() as conn:
        pg_ver = conn.execute(text("SELECT version()")).scalar()
        logger.info(f"PostgreSQL: {pg_ver[:60]}...")

    # Get pre-migration counts from PostgreSQL
    pg_counts_before = {}
    with pg_engine.connect() as conn:
        for table in TABLES:
            try:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                pg_counts_before[table] = count
            except Exception:
                pg_counts_before[table] = -1  # table might not exist yet
    logger.info(f"PostgreSQL tables before migration: {sum(max(0, c) for c in pg_counts_before.values())} total rows")

    # Migrate each table
    results = {}
    total_start = time.time()

    for table in TABLES:
        start = time.time()
        logger.info(f"\n{'─'*50}")
        logger.info(f"Migrating: {table}")

        # Read from SQLite
        try:
            df = pd.read_sql_table(table, sqlite_engine)
        except Exception as e:
            logger.warning(f"  Skipped (table not in SQLite): {e}")
            results[table] = {"status": "skipped", "rows": 0}
            continue

        sqlite_count = len(df)
        logger.info(f"  SQLite rows: {sqlite_count}")

        if sqlite_count == 0:
            logger.info(f"  Empty table, skipping")
            results[table] = {"status": "empty", "rows": 0}
            continue

        # Truncate PostgreSQL table and insert
        try:
            with pg_engine.connect() as conn:
                conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
                conn.commit()

            # Convert DataFrame for PostgreSQL
            # SQLite stores UUIDs as TEXT, PostgreSQL expects native UUID
            # pandas + psycopg2 handles this automatically if the strings are valid UUIDs
            df.to_sql(
                table, pg_engine,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=2000,
            )

            # Verify count
            with pg_engine.connect() as conn:
                pg_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

            elapsed = round(time.time() - start, 2)
            logger.info(f"  Written: {pg_count} rows ({elapsed}s)")

            if pg_count != sqlite_count:
                logger.warning(f"  COUNT MISMATCH: SQLite={sqlite_count}, PG={pg_count}")
                results[table] = {"status": "mismatch", "sqlite": sqlite_count, "pg": pg_count}
            else:
                results[table] = {"status": "ok", "rows": pg_count}

        except Exception as e:
            elapsed = round(time.time() - start, 2)
            logger.error(f"  FAILED ({elapsed}s): {e}")
            results[table] = {"status": "error", "error": str(e)}

    # Summary
    total_elapsed = round(time.time() - total_start, 2)
    logger.info(f"\n{'═'*60}")
    logger.info(f"MIGRATION COMPLETE ({total_elapsed}s)")
    logger.info(f"{'═'*60}")

    all_ok = True
    for table, r in results.items():
        status = r["status"]
        if status == "ok":
            logger.info(f"  ✓ {table}: {r['rows']} rows")
        elif status == "empty":
            logger.info(f"  - {table}: 0 rows (empty)")
        elif status == "skipped":
            logger.info(f"  - {table}: skipped")
        else:
            logger.error(f"  ✗ {table}: {status} — {r}")
            all_ok = False

    # FK integrity check
    logger.info(f"\n{'─'*50}")
    logger.info("Foreign key integrity checks:")

    fk_checks = [
        ("players.team_id → teams.id",
         "SELECT COUNT(*) FROM players p LEFT JOIN teams t ON p.team_id = t.id WHERE p.team_id IS NOT NULL AND t.id IS NULL"),
        ("matches.venue_id → venues.id",
         "SELECT COUNT(*) FROM matches m LEFT JOIN venues v ON m.venue_id = v.id WHERE m.venue_id IS NOT NULL AND v.id IS NULL"),
        ("matches.team_a_id → teams.id",
         "SELECT COUNT(*) FROM matches m LEFT JOIN teams t ON m.team_a_id = t.id WHERE m.team_a_id IS NOT NULL AND t.id IS NULL"),
        ("innings.match_id → matches.id",
         "SELECT COUNT(*) FROM innings i LEFT JOIN matches m ON i.match_id = m.id WHERE m.id IS NULL"),
        ("deliveries.innings_id → innings.id",
         "SELECT COUNT(*) FROM deliveries d LEFT JOIN innings i ON d.innings_id = i.id WHERE i.id IS NULL"),
        ("deliveries.bowler_id → players.id",
         "SELECT COUNT(*) FROM deliveries d LEFT JOIN players p ON d.bowler_id = p.id WHERE d.bowler_id IS NOT NULL AND p.id IS NULL"),
        ("player_batting_stats.player_id → players.id",
         "SELECT COUNT(*) FROM player_batting_stats s LEFT JOIN players p ON s.player_id = p.id WHERE p.id IS NULL"),
        ("player_bowling_stats.player_id → players.id",
         "SELECT COUNT(*) FROM player_bowling_stats s LEFT JOIN players p ON s.player_id = p.id WHERE p.id IS NULL"),
        ("player_form.player_id → players.id",
         "SELECT COUNT(*) FROM player_form f LEFT JOIN players p ON f.player_id = p.id WHERE p.id IS NULL"),
        ("batter_bowler_matchups.batter_id → players.id",
         "SELECT COUNT(*) FROM batter_bowler_matchups b LEFT JOIN players p ON b.batter_id = p.id WHERE p.id IS NULL"),
    ]

    with pg_engine.connect() as conn:
        for label, query in fk_checks:
            orphans = conn.execute(text(query)).scalar()
            if orphans == 0:
                logger.info(f"  ✓ {label} — 0 orphans")
            else:
                logger.error(f"  ✗ {label} — {orphans} orphaned rows!")
                all_ok = False

    sqlite_engine.dispose()
    pg_engine.dispose()

    if all_ok:
        logger.info(f"\n✅ Migration successful — all counts match, all FKs valid")
    else:
        logger.error(f"\n❌ Migration completed with issues — review above")

    return all_ok


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
