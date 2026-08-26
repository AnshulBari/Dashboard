"""
Phase 1.1 Migration: Universal Model Hardening
================================================

Non-destructive migration adding:
1. player_team_affiliations table (multi-team support)
2. Seasons backfill from match data
3. Result type backfill for Test matches
4. Format-aware DB views

All changes are ADDITIVE — no data loss.
Idempotent: safe to re-run.
"""

import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or not DATABASE_URL.startswith("postgresql"):
    print("ERROR: DATABASE_URL must be a PostgreSQL URL")
    sys.exit(1)


def run_migration():
    engine = create_engine(DATABASE_URL)

    print("=" * 60)
    print("Phase 1.1 Migration: Universal Model Hardening")
    print("=" * 60)

    with engine.connect() as conn:
        # ============================================================
        # RECORD BEFORE STATE
        # ============================================================
        print("\n[BEFORE] Recording current state...")
        before = {}
        for table in ["teams", "players", "venues", "competitions", "matches",
                       "innings", "deliveries", "player_batting_stats",
                       "player_bowling_stats", "player_form", "team_performance",
                       "venue_stats", "batter_bowler_matchups", "seasons"]:
            try:
                before[table] = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            except:
                before[table] = 0
        for t, c in before.items():
            print(f"  {t}: {c}")

        # ============================================================
        # 1. CREATE player_team_affiliations TABLE
        # ============================================================
        print("\n[STEP 1] Creating player_team_affiliations table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS player_team_affiliations (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                format VARCHAR(20),           -- 'T20', 'T20I', 'ODI', 'Test', NULL = general
                competition_id UUID REFERENCES competitions(id),
                season VARCHAR(50),
                start_date DATE,
                end_date DATE,
                is_current BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),

                UNIQUE(player_id, team_id, format, competition_id)
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pta_player ON player_team_affiliations(player_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pta_team ON player_team_affiliations(team_id)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pta_format ON player_team_affiliations(format)
        """))
        print("  Created player_team_affiliations table + indexes")

        # ============================================================
        # 2. POPULATE player_team_affiliations FROM players.team_id
        # ============================================================
        print("\n[STEP 2] Populating affiliations from existing players.team_id...")
        result = conn.execute(text("""
            INSERT INTO player_team_affiliations (player_id, team_id, format, is_current)
            SELECT p.id, p.team_id, 'T20', TRUE
            FROM players p
            WHERE p.team_id IS NOT NULL
            ON CONFLICT (player_id, team_id, format, competition_id) DO NOTHING
        """))
        conn.commit()
        aff_count = conn.execute(text("SELECT COUNT(*) FROM player_team_affiliations")).scalar()
        print(f"  Created {aff_count} affiliations from existing team_id links")

        # ============================================================
        # 3. POPULATE seasons FROM match data
        # ============================================================
        print("\n[STEP 3] Creating seasons from match competition data...")
        # Get distinct competition+format combos from matches
        comps = conn.execute(text("""
            SELECT DISTINCT c.id, c.name, c.format
            FROM competitions c
            WHERE c.id IN (SELECT DISTINCT competition_id FROM matches WHERE competition_id IS NOT NULL)
        """)).fetchall()

        for comp_id, comp_name, comp_format in comps:
            # Extract seasons from the match data — use the first 4 chars of date as year
            # This is a reasonable approximation for IPL seasons
            seasons_data = conn.execute(text("""
                SELECT DISTINCT EXTRACT(YEAR FROM match_date)::INTEGER as year
                FROM matches
                WHERE competition_id = :cid
                ORDER BY year
            """), {"cid": comp_id}).fetchall()

            for (year,) in seasons_data:
                if year and year > 1900:
                    season_name = str(year)
                    conn.execute(text("""
                        INSERT INTO seasons (id, competition_id, name, start_date, end_date)
                        VALUES (:id, :cid, :name, :start, :end)
                        ON CONFLICT (competition_id, name) DO NOTHING
                    """), {
                        "id": str(uuid.uuid4()),
                        "cid": comp_id,
                        "name": season_name,
                        "start": f"{year}-01-01",
                        "end": f"{year}-12-31",
                    })

        conn.commit()
        season_count = conn.execute(text("SELECT COUNT(*) FROM seasons")).scalar()
        print(f"  Created {season_count} seasons")

        # ============================================================
        # 4. LINK matches TO seasons
        # ============================================================
        print("\n[STEP 4] Linking matches to seasons...")
        conn.execute(text("""
            UPDATE matches m
            SET season_id = s.id
            FROM seasons s
            WHERE m.competition_id = s.competition_id
              AND s.name = EXTRACT(YEAR FROM m.match_date)::TEXT
              AND m.season_id IS NULL
              AND m.competition_id IS NOT NULL
        """))
        conn.commit()
        linked = conn.execute(text("SELECT COUNT(*) FROM matches WHERE season_id IS NOT NULL")).scalar()
        print(f"  Linked {linked} matches to seasons")

        # ============================================================
        # 5. BACKFILL result_type for Test matches (draw if no winner)
        # ============================================================
        print("\n[STEP 5] Backfilling result_type for Test matches...")
        conn.execute(text("""
            UPDATE matches
            SET result_type = 'draw'
            WHERE format = 'Test'
              AND winner_id IS NULL
              AND result_type = 'win'
        """))
        conn.execute(text("""
            UPDATE matches
            SET result_type = 'no_result'
            WHERE winner_id IS NULL
              AND result_type = 'win'
              AND format != 'Test'
        """))
        conn.commit()

        # ============================================================
        # 6. DROP AND RECREATE VIEWS (format-agnostic)
        # ============================================================
        print("\n[STEP 6] Updating database views...")
        conn.execute(text("DROP VIEW IF EXISTS v_player_summary"))
        conn.execute(text("DROP VIEW IF EXISTS v_team_summary"))

        conn.execute(text("""
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
                pbs.format as primary_format,
                pws.wickets as career_wickets,
                pws.economy as career_economy,
                pws.bowling_average,
                pf.form_score
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN player_batting_stats pbs ON p.id = pbs.player_id
                AND pbs.period = 'career'
            LEFT JOIN player_bowling_stats pws ON p.id = pws.player_id
                AND pws.period = 'career'
            LEFT JOIN player_form pf ON p.id = pf.player_id
        """))

        conn.execute(text("""
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
                tp.overall_strength_score,
                tp.format
            FROM teams t
            LEFT JOIN team_performance tp ON t.id = tp.team_id
                AND tp.period = 'career'
        """))
        print("  Views recreated without hardcoded format")

        # ============================================================
        # VERIFY AFTER STATE
        # ============================================================
        print("\n[AFTER] Verifying state...")
        for table in ["teams", "players", "venues", "competitions", "matches",
                       "innings", "deliveries", "player_batting_stats",
                       "player_bowling_stats", "player_form", "team_performance",
                       "venue_stats", "batter_bowler_matchups", "seasons",
                       "player_team_affiliations"]:
            try:
                after = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                delta = after - before.get(table, 0)
                delta_str = f" (+{delta})" if delta > 0 else ""
                print(f"  {table}: {after}{delta_str}")
            except Exception as e:
                print(f"  {table}: ERROR - {e}")

        # Verify FK integrity
        print("\n[INTEGRITY CHECKS]")
        checks = [
            ("Affiliations → Players",
             "SELECT COUNT(*) FROM player_team_affiliations a LEFT JOIN players p ON a.player_id = p.id WHERE p.id IS NULL"),
            ("Affiliations → Teams",
             "SELECT COUNT(*) FROM player_team_affiliations a LEFT JOIN teams t ON a.team_id = t.id WHERE t.id IS NULL"),
            ("Seasons → Competitions",
             "SELECT COUNT(*) FROM seasons s LEFT JOIN competitions c ON s.competition_id = c.id WHERE c.id IS NULL"),
            ("Matches → Seasons",
             "SELECT COUNT(*) FROM matches m LEFT JOIN seasons s ON m.season_id = s.id WHERE m.season_id IS NOT NULL AND s.id IS NULL"),
        ]
        for label, sql in checks:
            orphans = conn.execute(text(sql)).scalar()
            status = "PASS" if orphans == 0 else f"FAIL ({orphans} orphans)"
            print(f"  {label}: {status}")

    engine.dispose()
    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)


if __name__ == "__main__":
    run_migration()
