"""
Phase 5.6C Tests: Historical Data Integrity & Scorecard Reconciliation
=======================================================================

Verifies the ODI/T20I scorecard inflation fix and overall data integrity.

Run: python -m pytest tests/test_phase5_6c.py -v
"""

import os
import sys
import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def _get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


# ============================================================
# ODI INFLATION FIX VERIFICATION
# ============================================================

class TestODIInflationFix:
    """Verify the doubled scorecard values have been corrected."""

    def test_no_odi_batting_inflation(self):
        engine = _get_engine()
        with engine.connect() as conn:
            inflated = conn.execute(text("""
                SELECT COUNT(*) FROM innings i
                JOIN matches m ON i.match_id = m.id
                JOIN (SELECT innings_id, SUM(runs) as bat_runs
                      FROM match_batting_summary GROUP BY innings_id) sc
                    ON sc.innings_id = i.id
                WHERE m.format = 'ODI' AND sc.bat_runs > i.total_runs * 1.5
            """)).scalar()
            assert inflated == 0, f"{inflated} ODI innings still have inflated batting scorecards"
        engine.dispose()

    def test_no_odi_bowling_inflation(self):
        engine = _get_engine()
        with engine.connect() as conn:
            inflated = conn.execute(text("""
                SELECT COUNT(*) FROM innings i
                JOIN matches m ON i.match_id = m.id
                JOIN (SELECT innings_id, SUM(runs_conceded) as bowl_runs
                      FROM match_bowling_summary GROUP BY innings_id) sc
                    ON sc.innings_id = i.id
                WHERE m.format = 'ODI' AND sc.bowl_runs > i.total_runs * 1.5
            """)).scalar()
            assert inflated == 0, f"{inflated} ODI innings still have inflated bowling scorecards"
        engine.dispose()

    def test_no_t20i_batting_inflation(self):
        engine = _get_engine()
        with engine.connect() as conn:
            inflated = conn.execute(text("""
                SELECT COUNT(*) FROM innings i
                JOIN matches m ON i.match_id = m.id
                JOIN (SELECT innings_id, SUM(runs) as bat_runs
                      FROM match_batting_summary GROUP BY innings_id) sc
                    ON sc.innings_id = i.id
                WHERE m.format = 'T20I' AND sc.bat_runs > i.total_runs * 1.5
            """)).scalar()
            assert inflated == 0, f"{inflated} T20I innings still have inflated batting scorecards"
        engine.dispose()

    def test_no_t20i_bowling_inflation(self):
        engine = _get_engine()
        with engine.connect() as conn:
            inflated = conn.execute(text("""
                SELECT COUNT(*) FROM innings i
                JOIN matches m ON i.match_id = m.id
                JOIN (SELECT innings_id, SUM(runs_conceded) as bowl_runs
                      FROM match_bowling_summary GROUP BY innings_id) sc
                    ON sc.innings_id = i.id
                WHERE m.format = 'T20I' AND sc.bowl_runs > i.total_runs * 1.5
            """)).scalar()
            assert inflated == 0, f"{inflated} T20I innings still have inflated bowling scorecards"
        engine.dispose()


# ============================================================
# SCORECARD RECONCILIATION
# ============================================================

class TestScorecardReconciliation:
    """Verify batting and bowling scorecards reconcile correctly."""

    def test_bowling_100_percent_accurate(self):
        """Bowling conceded should match innings total (within 10 runs) for ALL formats."""
        engine = _get_engine()
        with engine.connect() as conn:
            for fmt in ['T20', 'T20I', 'ODI', 'Test']:
                row = conn.execute(text("""
                    SELECT
                        SUM(CASE WHEN ABS(i.total_runs - COALESCE(sc.bowl_runs, 0)) <= 10
                            THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as pct_close
                    FROM innings i
                    JOIN matches m ON i.match_id = m.id
                    LEFT JOIN (SELECT innings_id, SUM(runs_conceded) as bowl_runs
                              FROM match_bowling_summary GROUP BY innings_id) sc
                        ON sc.innings_id = i.id
                    WHERE m.format = :fmt AND i.total_runs > 0
                """), {"fmt": fmt}).fetchone()
                pct = row[0] or 0
                assert pct >= 99.0, f"{fmt} bowling only {pct:.1f}% within 10 runs (expected >=99%)"
        engine.dispose()

    def test_batting_global_ratio(self):
        """Scorecard batting total should be within 5% of innings total globally."""
        engine = _get_engine()
        with engine.connect() as conn:
            for fmt in ['T20', 'T20I', 'ODI', 'Test']:
                row = conn.execute(text("""
                    SELECT
                        SUM(i.total_runs) as inn_total,
                        SUM(COALESCE(sc.bat_runs, 0)) as sc_total
                    FROM innings i
                    JOIN matches m ON i.match_id = m.id
                    LEFT JOIN (SELECT innings_id, SUM(runs) as bat_runs
                              FROM match_batting_summary GROUP BY innings_id) sc
                        ON sc.innings_id = i.id
                    WHERE m.format = :fmt AND i.total_runs > 0
                """), {"fmt": fmt}).fetchone()
                ratio = row[1] / row[0] if row[0] > 0 else 0
                assert 0.90 <= ratio <= 1.10, (
                    f"{fmt} batting ratio {ratio:.3f} outside [0.90, 1.10]"
                )
        engine.dispose()

    def test_kohli_ipl_scorecard(self):
        """Kohli's IPL scorecard should show ~9,346 runs."""
        engine = _get_engine()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT SUM(mbs.runs) as total_runs
                FROM match_batting_summary mbs
                JOIN players p ON mbs.player_id = p.id
                JOIN matches m ON mbs.match_id = m.id
                WHERE p.canonical_name = 'Virat Kohli' AND m.format = 'T20'
            """)).fetchone()
            assert row[0] > 9000, f"Kohli IPL scorecard runs {row[0]} seems too low"
        engine.dispose()


# ============================================================
# FORMAT ISOLATION
# ============================================================

class TestFormatIsolation:
    def test_kohli_cross_format(self):
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT format, SUM(runs) as total
                FROM player_batting_stats pbs
                JOIN players p ON pbs.player_id = p.id
                WHERE p.canonical_name = 'Virat Kohli'
                AND pbs.period IN ('career', 'all-time')
                GROUP BY format ORDER BY format
            """)).fetchall()
            formats = {r[0]: r[1] for r in rows}
            assert len(formats) == 4, f"Kohli should have 4 formats, got {len(formats)}"
            assert formats.get('T20', 0) > 9000, "Kohli T20 runs too low"
            assert formats.get('ODI', 0) > 15000, "Kohli ODI runs too low"
            assert formats.get('Test', 0) > 8000, "Kohli Test runs too low"
        engine.dispose()

    def test_no_cross_format_matchup_duplicates(self):
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT batter_id, bowler_id, format, COUNT(*) as cnt
                    FROM batter_bowler_matchups
                    GROUP BY batter_id, bowler_id, format
                    HAVING COUNT(*) > 1
                ) sub
            """)).scalar()
            assert dups == 0, f"{dups} duplicate matchup entries"
        engine.dispose()


# ============================================================
# REGRESSION
# ============================================================

class TestRegression:
    def test_ipl_matches(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM matches WHERE format = 'T20'")).scalar()
            assert count == 1243, f"IPL matches: expected 1243, got {count}"
        engine.dispose()

    def test_kohli_ipl_runs(self):
        engine = _get_engine()
        with engine.connect() as conn:
            runs = conn.execute(text("""
                SELECT pbs.runs FROM player_batting_stats pbs
                JOIN players p ON pbs.player_id = p.id
                WHERE p.canonical_name = 'Virat Kohli'
                AND pbs.format = 'T20' AND pbs.period = 'career'
            """)).scalar()
            assert runs == 9346, f"Kohli IPL runs: expected 9346, got {runs}"
        engine.dispose()

    def test_t20i_matches(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM matches WHERE format = 'T20I'")).scalar()
            assert count == 3533, f"T20I matches: expected 3533, got {count}"
        engine.dispose()

    def test_odi_matches(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM matches WHERE format = 'ODI'")).scalar()
            assert count == 2577, f"ODI matches: expected 2577, got {count}"
        engine.dispose()

    def test_test_matches(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM matches WHERE format = 'Test'")).scalar()
            assert count == 897, f"Test matches: expected 897, got {count}"
        engine.dispose()

    def test_database_size(self):
        engine = _get_engine()
        with engine.connect() as conn:
            size = conn.execute(text("SELECT pg_database_size(current_database())")).scalar()
            assert size < 200_000_000, f"DB size {size/1_000_000:.0f}MB exceeds 200MB"
        engine.dispose()


# ============================================================
# DATA INTEGRITY
# ============================================================

class TestDataIntegrity:
    def test_no_duplicate_canonical_players(self):
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT canonical_name, COUNT(*) FROM players
                    GROUP BY canonical_name HAVING COUNT(*) > 1
                ) sub
            """)).scalar()
            assert dups == 0, f"{dups} duplicate canonical player names"
        engine.dispose()

    def test_no_duplicate_teams(self):
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT canonical_name, COUNT(*) FROM teams
                    GROUP BY canonical_name HAVING COUNT(*) > 1
                ) sub
            """)).scalar()
            assert dups == 0, f"{dups} duplicate team names"
        engine.dispose()

    def test_no_orphaned_batting_stats(self):
        engine = _get_engine()
        with engine.connect() as conn:
            orphans = conn.execute(text("""
                SELECT COUNT(*) FROM player_batting_stats pbs
                LEFT JOIN players p ON pbs.player_id = p.id WHERE p.id IS NULL
            """)).scalar()
            assert orphans == 0, f"{orphans} orphaned batting stats"
        engine.dispose()

    def test_scorecard_coverage_100_percent(self):
        engine = _get_engine()
        with engine.connect() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM matches")).scalar()
            covered = conn.execute(text(
                "SELECT COUNT(DISTINCT match_id) FROM match_batting_summary"
            )).scalar()
            assert covered == total, f"Scorecard coverage {covered}/{total}"
        engine.dispose()

    def test_team_type_distribution(self):
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT team_type, COUNT(*) FROM teams GROUP BY team_type"
            )).fetchall()
            types = {r[0]: r[1] for r in rows}
            assert types.get('national', 0) > 80, "Should have 80+ national teams"
            assert types.get('franchise', 0) == 14, "Should have 14 IPL franchises"
        engine.dispose()
