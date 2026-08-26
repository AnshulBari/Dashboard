"""
Phase 3.1 Tests: Player Identity & Data Quality Hardening
===========================================================
Tests for player identity merge, name mappings, cross-format validation,
data quality, and full regression.
"""

import os
import pytest

if "DATABASE_URL" not in os.environ:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


@pytest.fixture(scope="module")
def pg_engine():
    from sqlalchemy import create_engine
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or db_url.startswith("sqlite"):
        pytest.skip("PostgreSQL DATABASE_URL not set")
    engine = create_engine(db_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def pg_conn(pg_engine):
    from sqlalchemy import text
    with pg_engine.connect() as conn:
        yield conn


# ============================================================
# PLAYER IDENTITY TESTS
# ============================================================

class TestPlayerIdentity:
    """Tests for player identity merge."""

    def test_v_kohli_removed(self, pg_conn):
        """V Kohli should no longer exist as a separate player."""
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM players WHERE canonical_name = 'V Kohli'"
        )).scalar()
        assert count == 0, f"V Kohli still exists: {count} records"

    def test_virat_kohli_exists(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM players WHERE canonical_name = 'Virat Kohli'"
        )).scalar()
        assert count == 1, f"Expected 1 Virat Kohli, got {count}"

    def test_virat_kohli_has_t20_stats(self, pg_conn):
        """After merge, Virat Kohli should have IPL/T20 stats (from V Kohli)."""
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT runs, innings, batting_average FROM player_batting_stats "
            "WHERE player_id = (SELECT id FROM players WHERE canonical_name = 'Virat Kohli') "
            "AND format = 'T20' LIMIT 1"
        )).fetchone()
        assert r is not None, "Virat Kohli missing T20 batting stats"
        assert r[0] == 9346, f"Expected 9346 T20 runs, got {r[0]}"
        assert r[1] == 277, f"Expected 277 T20 innings, got {r[1]}"

    def test_virat_kohli_has_odi_stats(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT runs, innings FROM player_batting_stats "
            "WHERE player_id = (SELECT id FROM players WHERE canonical_name = 'Virat Kohli') "
            "AND format = 'ODI' LIMIT 1"
        )).fetchone()
        assert r is not None, "Virat Kohli missing ODI batting stats"
        assert r[0] == 111, f"Expected 111 ODI runs, got {r[0]}"

    def test_virat_kohli_has_t20i_stats(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT runs, innings FROM player_batting_stats "
            "WHERE player_id = (SELECT id FROM players WHERE canonical_name = 'Virat Kohli') "
            "AND format = 'T20I' LIMIT 1"
        )).fetchone()
        assert r is not None, "Virat Kohli missing T20I batting stats"
        assert r[0] == 63, f"Expected 63 T20I runs, got {r[0]}"

    def test_virat_kohli_multi_format(self, pg_conn):
        """Virat Kohli should have stats in 3 formats."""
        from sqlalchemy import text
        formats = pg_conn.execute(text(
            "SELECT DISTINCT format FROM player_batting_stats "
            "WHERE player_id = (SELECT id FROM players WHERE canonical_name = 'Virat Kohli') "
            "ORDER BY format"
        )).fetchall()
        fmt_list = [r[0] for r in formats]
        assert "ODI" in fmt_list, f"Missing ODI, got {fmt_list}"
        assert "T20" in fmt_list, f"Missing T20, got {fmt_list}"
        assert "T20I" in fmt_list, f"Missing T20I, got {fmt_list}"

    def test_virat_kohli_affiliations(self, pg_conn):
        """Virat Kohli should have RCB (T20) and India (T20I/ODI) affiliations."""
        from sqlalchemy import text
        rows = pg_conn.execute(text(
            "SELECT t.canonical_name, a.format "
            "FROM player_team_affiliations a "
            "JOIN teams t ON a.team_id = t.id "
            "WHERE a.player_id = (SELECT id FROM players WHERE canonical_name = 'Virat Kohli') "
            "ORDER BY a.format"
        )).fetchall()
        affs = {(r[0], r[1]) for r in rows}
        assert ("Royal Challengers Bangalore", "T20") in affs, f"Missing RCB affiliation, got {affs}"
        assert any(f == "T20I" for _, f in affs), f"Missing T20I affiliation, got {affs}"
        assert any(f == "ODI" for _, f in affs), f"Missing ODI affiliation, got {affs}"

    def test_name_mappings_exist(self, pg_conn):
        """player_name_mappings should have the V Kohli mapping."""
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT COUNT(*) FROM player_name_mappings WHERE name_variant = 'V Kohli'"
        )).scalar()
        assert r >= 1, f"Expected V Kohli mapping, got {r}"

    def test_no_orphaned_records(self, pg_conn):
        """No orphaned records after merge."""
        from sqlalchemy import text
        tables = [
            ("deliveries", "striker_id"),
            ("deliveries", "bowler_id"),
            ("player_batting_stats", "player_id"),
            ("player_bowling_stats", "player_id"),
            ("player_form", "player_id"),
            ("batter_bowler_matchups", "batter_id"),
            ("player_team_affiliations", "player_id"),
        ]
        for table, col in tables:
            orphans = pg_conn.execute(text(
                f"SELECT COUNT(*) FROM {table} t "
                f"WHERE t.{col} IS NOT NULL "
                f"AND NOT EXISTS (SELECT 1 FROM players p WHERE p.id = t.{col})"
            )).scalar()
            assert orphans == 0, f"{table}.{col} has {orphans} orphans"

    def test_player_count_after_merge(self, pg_conn):
        """Player count should be 948 (was 949, minus 1 for V Kohli merge)."""
        from sqlalchemy import text
        count = pg_conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
        assert count == 948, f"Expected 948 players, got {count}"


# ============================================================
# FORMAT ISOLATION TESTS
# ============================================================

class TestFormatIsolationAfterMerge:
    """Verify format isolation is maintained after identity merge."""

    def test_odi_runs_not_contaminated(self, pg_conn):
        """ODI runs for Virat Kohli should be 111, not 9346+111."""
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT runs FROM player_batting_stats "
            "WHERE player_id = (SELECT id FROM players WHERE canonical_name = 'Virat Kohli') "
            "AND format = 'ODI' LIMIT 1"
        )).fetchone()
        assert r is not None, "No ODI stats"
        assert r[0] == 111, f"ODI runs contaminated: expected 111, got {r[0]}"

    def test_t20i_runs_not_contaminated(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT runs FROM player_batting_stats "
            "WHERE player_id = (SELECT id FROM players WHERE canonical_name = 'Virat Kohli') "
            "AND format = 'T20I' LIMIT 1"
        )).fetchone()
        assert r is not None, "No T20I stats"
        assert r[0] == 63, f"T20I runs contaminated: expected 63, got {r[0]}"

    def test_t20_runs_unchanged(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT runs FROM player_batting_stats "
            "WHERE player_id = (SELECT id FROM players WHERE canonical_name = 'Virat Kohli') "
            "AND format = 'T20' LIMIT 1"
        )).fetchone()
        assert r is not None, "No T20 stats"
        assert r[0] == 9346, f"T20 runs changed: expected 9346, got {r[0]}"


# ============================================================
# DATA QUALITY TESTS
# ============================================================

class TestDataQuality:
    """Comprehensive data quality checks."""

    def test_no_duplicate_matches(self, pg_conn):
        from sqlalchemy import text
        dupes = pg_conn.execute(text(
            "SELECT external_id, COUNT(*) FROM matches "
            "GROUP BY external_id HAVING COUNT(*) > 1"
        )).fetchall()
        assert len(dupes) == 0, f"Found {len(dupes)} duplicate matches"

    def test_no_duplicate_players(self, pg_conn):
        from sqlalchemy import text
        dupes = pg_conn.execute(text(
            "SELECT canonical_name, COUNT(*) FROM players "
            "GROUP BY canonical_name HAVING COUNT(*) > 1"
        )).fetchall()
        assert len(dupes) == 0, f"Found {len(dupes)} duplicate players: {[d[0] for d in dupes]}"

    def test_no_duplicate_teams(self, pg_conn):
        from sqlalchemy import text
        dupes = pg_conn.execute(text(
            "SELECT canonical_name, COUNT(*) FROM teams "
            "GROUP BY canonical_name HAVING COUNT(*) > 1"
        )).fetchall()
        assert len(dupes) == 0, f"Found {len(dupes)} duplicate teams"

    def test_no_duplicate_venues(self, pg_conn):
        from sqlalchemy import text
        dupes = pg_conn.execute(text(
            "SELECT name, COUNT(*) FROM venues "
            "GROUP BY name HAVING COUNT(*) > 1"
        )).fetchall()
        assert len(dupes) == 0, f"Found {len(dupes)} duplicate venues"

    def test_no_invalid_formats(self, pg_conn):
        from sqlalchemy import text
        bad = pg_conn.execute(text(
            "SELECT DISTINCT format FROM matches "
            "WHERE format NOT IN ('T20','T20I','ODI','Test')"
        )).fetchall()
        assert len(bad) == 0, f"Invalid formats: {[r[0] for r in bad]}"

    def test_no_matches_without_teams(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM matches WHERE team_a_id IS NULL OR team_b_id IS NULL"
        )).scalar()
        assert count == 0, f"{count} matches without teams"

    def test_all_deliveries_have_valid_runs(self, pg_conn):
        from sqlalchemy import text
        bad = pg_conn.execute(text(
            "SELECT COUNT(*) FROM deliveries WHERE runs_bat < 0 OR total_runs < 0"
        )).scalar()
        assert bad == 0, f"{bad} deliveries with negative runs"

    def test_all_balls_in_over_valid(self, pg_conn):
        from sqlalchemy import text
        bad = pg_conn.execute(text(
            "SELECT COUNT(*) FROM deliveries WHERE ball_in_over < 1 OR ball_in_over > 12"
        )).scalar()
        assert bad == 0, f"{bad} invalid ball_in_over values"


# ============================================================
# IPL REGRESSION (post-merge)
# ============================================================

class TestIPLRegressionPostMerge:
    """IPL regression must hold after identity merge."""

    def test_ipl_match_count(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text("SELECT COUNT(*) FROM matches WHERE format='T20'")).scalar()
        assert c == 1243, f"IPL matches changed: {c}"

    def test_ipl_delivery_count(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text(
            "SELECT COUNT(*) FROM deliveries d JOIN matches m ON d.match_id=m.id WHERE m.format='T20'"
        )).scalar()
        assert c == 295732, f"IPL deliveries changed: {c}"

    def test_ipl_batting_stats_count(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text(
            "SELECT COUNT(*) FROM player_batting_stats WHERE format='T20'"
        )).scalar()
        assert c == 738, f"IPL batting stats changed: {c}"

    def test_ipl_bowling_stats_count(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text(
            "SELECT COUNT(*) FROM player_bowling_stats WHERE format='T20'"
        )).scalar()
        assert c == 577, f"IPL bowling stats changed: {c}"

    def test_ipl_matchups_count(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text(
            "SELECT COUNT(*) FROM batter_bowler_matchups WHERE format='T20'"
        )).scalar()
        assert c == 9502, f"IPL matchups changed: {c}"


# ============================================================
# T20I REGRESSION (post-merge)
# ============================================================

class TestT20IRegressionPostMerge:
    """T20I regression must hold after identity merge."""

    def test_t20i_match_count(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text("SELECT COUNT(*) FROM matches WHERE format='T20I'")).scalar()
        assert c == 5, f"T20I matches changed: {c}"

    def test_t20i_delivery_count(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text(
            "SELECT COUNT(*) FROM deliveries d JOIN matches m ON d.match_id=m.id WHERE m.format='T20I'"
        )).scalar()
        assert c == 518, f"T20I deliveries changed: {c}"


# ============================================================
# ODI REGRESSION (post-merge)
# ============================================================

class TestODIRegressionPostMerge:
    """ODI regression must hold after identity merge."""

    def test_odi_match_count(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text("SELECT COUNT(*) FROM matches WHERE format='ODI'")).scalar()
        assert c == 8, f"ODI matches changed: {c}"

    def test_odi_delivery_count(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text(
            "SELECT COUNT(*) FROM deliveries d JOIN matches m ON d.match_id=m.id WHERE m.format='ODI'"
        )).scalar()
        assert c == 793, f"ODI deliveries changed: {c}"


# ============================================================
# CROSS-FORMAT IDENTITY TESTS
# ============================================================

class TestCrossFormatIdentity:
    """Players appearing across multiple formats."""

    def test_kl_rahul_three_formats(self, pg_conn):
        from sqlalchemy import text
        formats = pg_conn.execute(text(
            "SELECT DISTINCT b.format FROM player_batting_stats b "
            "JOIN players p ON b.player_id = p.id "
            "WHERE p.canonical_name = 'KL Rahul' ORDER BY b.format"
        )).fetchall()
        fmt_list = [r[0] for r in formats]
        assert "T20" in fmt_list, f"KL Rahul missing T20"
        assert "T20I" in fmt_list, f"KL Rahul missing T20I"
        assert "ODI" in fmt_list, f"KL Rahul missing ODI"

    def test_babar_azam_two_formats(self, pg_conn):
        from sqlalchemy import text
        formats = pg_conn.execute(text(
            "SELECT DISTINCT b.format FROM player_batting_stats b "
            "JOIN players p ON b.player_id = p.id "
            "WHERE p.canonical_name = 'Babar Azam' ORDER BY b.format"
        )).fetchall()
        fmt_list = [r[0] for r in formats]
        assert "ODI" in fmt_list
        assert "T20I" in fmt_list
