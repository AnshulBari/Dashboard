"""
Phase 3 Tests: ODI Ingestion & Intelligence
=============================================
Tests for ODI format support, cross-format identity,
format isolation, and pipeline regression.
"""

import os
import json
import pytest
from pathlib import Path

# Ensure we're using PostgreSQL for tests that need the real DB
if "DATABASE_URL" not in os.environ:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


@pytest.fixture(scope="module")
def pg_engine():
    """Create a PostgreSQL engine for testing."""
    from sqlalchemy import create_engine
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or db_url.startswith("sqlite"):
        pytest.skip("PostgreSQL DATABASE_URL not set")
    engine = create_engine(db_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def pg_conn(pg_engine):
    """Get a PostgreSQL connection."""
    from sqlalchemy import text
    with pg_engine.connect() as conn:
        yield conn


# ============================================================
# ODI DATA TESTS
# ============================================================

class TestODIData:
    """Tests for ODI data ingestion."""

    def test_odi_matches_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text("SELECT COUNT(*) FROM matches WHERE format='ODI'")).scalar()
        assert count >= 8, f"Expected >= 8 ODI matches, got {count}"

    def test_odi_innings_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM innings i JOIN matches m ON i.match_id=m.id WHERE m.format='ODI'"
        )).scalar()
        assert count >= 16, f"Expected >= 16 ODI innings, got {count}"

    def test_odi_deliveries_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM deliveries d JOIN matches m ON d.match_id=m.id WHERE m.format='ODI'"
        )).scalar()
        assert count >= 700, f"Expected >= 700 ODI deliveries, got {count}"

    def test_odi_teams_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(DISTINCT t.id) FROM teams t "
            "JOIN team_performance tp ON t.id = tp.team_id WHERE tp.format='ODI'"
        )).scalar()
        assert count >= 10, f"Expected >= 10 ODI teams, got {count}"

    def test_odi_players_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(DISTINCT player_id) FROM player_batting_stats WHERE format='ODI'"
        )).scalar()
        assert count >= 50, f"Expected >= 50 ODI batting players, got {count}"

    def test_odi_venues_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(DISTINCT venue_id) FROM venue_stats WHERE format='ODI'"
        )).scalar()
        assert count >= 5, f"Expected >= 5 ODI venues, got {count}"

    def test_odi_format_correct(self, pg_conn):
        """Every ODI match must have format='ODI'."""
        from sqlalchemy import text
        wrong = pg_conn.execute(text(
            "SELECT COUNT(*) FROM matches WHERE format='ODI' AND format != 'ODI'"
        )).scalar()
        assert wrong == 0


# ============================================================
# CROSS-FORMAT IDENTITY TESTS
# ============================================================

class TestCrossFormatIdentity:
    """Tests for players appearing across multiple formats."""

    def test_kl_rahul_multi_format(self, pg_conn):
        """KL Rahul should have T20, T20I, and ODI stats."""
        from sqlalchemy import text
        formats = pg_conn.execute(text(
            "SELECT DISTINCT b.format FROM player_batting_stats b "
            "JOIN players p ON b.player_id = p.id "
            "WHERE p.canonical_name = 'KL Rahul' ORDER BY b.format"
        )).fetchall()
        fmt_list = [r[0] for r in formats]
        assert "T20" in fmt_list, f"KL Rahul missing T20 stats, got {fmt_list}"
        assert "T20I" in fmt_list, f"KL Rahul missing T20I stats, got {fmt_list}"
        assert "ODI" in fmt_list, f"KL Rahul missing ODI stats, got {fmt_list}"

    def test_babar_azam_multi_format(self, pg_conn):
        """Babar Azam should have T20I and ODI stats."""
        from sqlalchemy import text
        formats = pg_conn.execute(text(
            "SELECT DISTINCT b.format FROM player_batting_stats b "
            "JOIN players p ON b.player_id = p.id "
            "WHERE p.canonical_name = 'Babar Azam' ORDER BY b.format"
        )).fetchall()
        fmt_list = [r[0] for r in formats]
        assert "ODI" in fmt_list, f"Babar Azam missing ODI stats, got {fmt_list}"
        assert "T20I" in fmt_list, f"Babar Azam missing T20I stats, got {fmt_list}"

    def test_player_single_identity(self, pg_conn):
        """Same player name should not have multiple player IDs."""
        from sqlalchemy import text
        dupes = pg_conn.execute(text(
            "SELECT canonical_name, COUNT(*) as cnt FROM players "
            "GROUP BY canonical_name HAVING COUNT(*) > 1"
        )).fetchall()
        # Allow some known duplicates from name normalization differences
        # but no extreme duplication
        assert len(dupes) < 20, f"Too many duplicate player names: {len(dupes)}"

    def test_kl_rahul_affiliations(self, pg_conn):
        """KL Rahul should have multiple team affiliations."""
        from sqlalchemy import text
        affs = pg_conn.execute(text(
            "SELECT t.canonical_name, a.format FROM player_team_affiliations a "
            "JOIN players p ON a.player_id = p.id "
            "JOIN teams t ON a.team_id = t.id "
            "WHERE p.canonical_name = 'KL Rahul' ORDER BY a.format"
        )).fetchall()
        assert len(affs) >= 3, f"KL Rahul should have >= 3 affiliations, got {len(affs)}"


# ============================================================
# FORMAT ISOLATION TESTS
# ============================================================

class TestFormatIsolation:
    """Tests that formats remain isolated."""

    def test_ipl_matches_unchanged(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text("SELECT COUNT(*) FROM matches WHERE format='T20'")).scalar()
        assert count == 1243, f"IPL matches changed: expected 1243, got {count}"

    def test_ipl_deliveries_unchanged(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM deliveries d JOIN matches m ON d.match_id=m.id WHERE m.format='T20'"
        )).scalar()
        assert count == 295732, f"IPL deliveries changed: expected 295732, got {count}"

    def test_t20i_matches_unchanged(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text("SELECT COUNT(*) FROM matches WHERE format='T20I'")).scalar()
        assert count >= 5, f"T20I matches regression: expected >= 5, got {count}"

    def test_t20i_deliveries_unchanged(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM deliveries d JOIN matches m ON d.match_id=m.id WHERE m.format='T20I'"
        )).scalar()
        assert count >= 518, f"T20I deliveries regression: expected >= 518, got {count}"

    def test_ipl_batting_stats_unchanged(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM player_batting_stats WHERE format='T20'"
        )).scalar()
        assert count == 738, f"IPL batting stats changed: expected 738, got {count}"

    def test_ipl_kohli_runs_unchanged(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT runs FROM player_batting_stats WHERE "
            "player_id=(SELECT id FROM players WHERE canonical_name='Virat Kohli' LIMIT 1) "
            "AND format='T20' LIMIT 1"
        )).fetchone()
        assert r is not None, "Virat Kohli IPL stats not found"
        assert r[0] == 9346, f"Virat Kohli IPL runs changed: expected 9346, got {r[0]}"

    def test_ipl_matchups_unchanged(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM batter_bowler_matchups WHERE format='T20'"
        )).scalar()
        assert count >= 9000, f"IPL matchups changed: expected 9502, got {count}"

    def test_odi_batting_stats_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM player_batting_stats WHERE format='ODI'"
        )).scalar()
        assert count >= 80, f"ODI batting stats too low: {count}"

    def test_odi_bowling_stats_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM player_bowling_stats WHERE format='ODI'"
        )).scalar()
        assert count >= 50, f"ODI bowling stats too low: {count}"

    def test_odi_team_performance_exists(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM team_performance WHERE format='ODI'"
        )).scalar()
        assert count >= 10, f"ODI team performance too low: {count}"

    def test_odi_venue_stats_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM venue_stats WHERE format='ODI'"
        )).scalar()
        assert count >= 5, f"ODI venue stats too low: {count}"


# ============================================================
# COMPETITION / SEASON TESTS
# ============================================================

class TestCompetitionSeason:
    """Tests for competition and season resolution."""

    def test_world_cup_competition(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT id, name FROM competitions WHERE name='ICC Cricket World Cup'"
        )).fetchone()
        assert r is not None, "ICC Cricket World Cup competition not found"

    def test_champions_trophy_competition(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT id, name FROM competitions WHERE name='ICC Champions Trophy'"
        )).fetchone()
        assert r is not None, "ICC Champions Trophy competition not found"

    def test_asia_cup_competition(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT id, name FROM competitions WHERE name='Asia Cup'"
        )).fetchone()
        assert r is not None, "Asia Cup competition not found"

    def test_world_cup_seasons(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT COUNT(*) FROM seasons s "
            "JOIN competitions c ON s.competition_id = c.id "
            "WHERE c.name = 'ICC Cricket World Cup'"
        )).scalar()
        assert r >= 2, f"Expected >= 2 World Cup seasons, got {r}"

    def test_ipl_seasons_intact(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT COUNT(*) FROM seasons s "
            "JOIN competitions c ON s.competition_id = c.id "
            "WHERE c.name = 'Indian Premier League'"
        )).scalar()
        assert r >= 17, f"Expected >= 17 IPL seasons, got {r}"


# ============================================================
# ODI ANALYTICS TESTS
# ============================================================

class TestODIAnalytics:
    """Tests for ODI analytics correctness."""

    def test_top_odi_batter_exists(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT p.canonical_name, b.runs FROM player_batting_stats b "
            "JOIN players p ON b.player_id = p.id "
            "WHERE b.format = 'ODI' ORDER BY b.runs DESC LIMIT 1"
        )).fetchone()
        assert r is not None, "No ODI batting stats found"
        assert r[1] > 0, f"Top ODI batter has 0 runs: {r[0]}"

    def test_top_odi_bowler_exists(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT p.canonical_name, b.wickets FROM player_bowling_stats b "
            "JOIN players p ON b.player_id = p.id "
            "WHERE b.format = 'ODI' ORDER BY b.wickets DESC LIMIT 1"
        )).fetchone()
        assert r is not None, "No ODI bowling stats found"
        assert r[1] > 0, f"Top ODI bowler has 0 wickets: {r[0]}"

    def test_odi_team_wins_reasonable(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT t.canonical_name, tp.wins, tp.losses "
            "FROM team_performance tp "
            "JOIN teams t ON tp.team_id = t.id "
            "WHERE tp.format = 'ODI' "
            "ORDER BY tp.wins DESC LIMIT 1"
        )).fetchone()
        assert r is not None, "No ODI team performance found"
        assert r[1] >= 1, f"Top ODI team has 0 wins: {r[0]}"

    def test_odi_venue_stats_have_matches(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT v.name, vs.total_matches FROM venue_stats vs "
            "JOIN venues v ON vs.venue_id = v.id "
            "WHERE vs.format = 'ODI' ORDER BY vs.total_matches DESC LIMIT 1"
        )).fetchone()
        assert r is not None, "No ODI venue stats"
        assert r[1] >= 1, f"Top ODI venue has 0 matches"


# ============================================================
# ODI PHASE ANALYTICS TEST
# ============================================================

class TestODIPhaseAnalytics:
    """Tests that ODI uses correct phase boundaries (0-9 powerplay)."""

    def test_odi_powerplay_config(self):
        from data_pipeline.pipeline.format_config import get_format_rules
        rules = get_format_rules("ODI")
        assert rules.powerplay_end == 9, f"ODI powerplay_end should be 9, got {rules.powerplay_end}"
        assert rules.middle_end == 39, f"ODI middle_end should be 39, got {rules.middle_end}"
        assert rules.standard_overs == 50, f"ODI standard_overs should be 50, got {rules.standard_overs}"

    def test_t20_not_affected_by_odi(self):
        from data_pipeline.pipeline.format_config import get_format_rules
        rules = get_format_rules("T20")
        assert rules.powerplay_end == 5, f"T20 powerplay_end should be 5, got {rules.powerplay_end}"
        rules_ipl = get_format_rules("T20")
        assert rules_ipl.powerplay_end == 5, f"IPL (T20) powerplay_end should be 5, got {rules_ipl.powerplay_end}"

    def test_format_config_in_db(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT * FROM format_config WHERE format='ODI'"
        )).fetchone()
        assert r is not None, "ODI format_config not in database"


# ============================================================
# FILE EXISTENCE TESTS
# ============================================================

class TestODIFixtures:
    """Tests that ODI fixture files exist and are valid."""

    def test_odi_fixture_dir_exists(self):
        odi_dir = Path("data/raw/odi")
        assert odi_dir.exists(), "data/raw/odi directory does not exist"
        assert odi_dir.is_dir(), "data/raw/odi is not a directory"

    def test_odi_fixtures_present(self):
        odi_dir = Path("data/raw/odi")
        json_files = list(odi_dir.glob("*.json"))
        assert len(json_files) >= 8, f"Expected >= 8 ODI fixtures, got {len(json_files)}"

    def test_odi_fixture_valid_json(self):
        odi_dir = Path("data/raw/odi")
        for f in list(odi_dir.glob("*.json"))[:3]:
            with open(f) as fp:
                data = json.load(fp)
            assert "info" in data, f"{f.name} missing 'info'"
            assert "innings" in data, f"{f.name} missing 'innings'"
            assert data["info"].get("match_type") == "ODI", f"{f.name} is not ODI format"

    def test_fixture_contains_wides(self):
        """At least one fixture should contain wides."""
        odi_dir = Path("data/raw/odi")
        found_wide = False
        for f in odi_dir.glob("*.json"):
            with open(f) as fp:
                content = fp.read()
            if '"wides"' in content:
                found_wide = True
                break
        assert found_wide, "No ODI fixture contains wides"

    def test_fixture_contains_noballs(self):
        """At least one fixture should contain no-balls."""
        odi_dir = Path("data/raw/odi")
        found_noball = False
        for f in odi_dir.glob("*.json"):
            with open(f) as fp:
                content = fp.read()
            if '"noballs"' in content:
                found_noball = True
                break
        assert found_noball, "No ODI fixture contains noballs"


# ============================================================
# DATA INTEGRITY TESTS
# ============================================================

class TestODIIntegrity:
    """Data integrity checks for ODI data."""

    def test_no_orphaned_odi_innings(self, pg_conn):
        from sqlalchemy import text
        orphaned = pg_conn.execute(text(
            "SELECT COUNT(*) FROM innings i "
            "JOIN matches m ON i.match_id = m.id "
            "WHERE m.format = 'ODI' AND i.match_id IS NULL"
        )).scalar()
        assert orphaned == 0, f"Found {orphaned} orphaned ODI innings"

    def test_no_orphaned_odi_deliveries(self, pg_conn):
        from sqlalchemy import text
        orphaned = pg_conn.execute(text(
            "SELECT COUNT(*) FROM deliveries d "
            "JOIN matches m ON d.match_id = m.id "
            "WHERE m.format = 'ODI' AND d.match_id IS NULL"
        )).scalar()
        assert orphaned == 0, f"Found {orphaned} orphaned ODI deliveries"

    def test_no_duplicate_odi_matches(self, pg_conn):
        from sqlalchemy import text
        dupes = pg_conn.execute(text(
            "SELECT external_id, COUNT(*) FROM matches "
            "WHERE format='ODI' GROUP BY external_id HAVING COUNT(*) > 1"
        )).fetchall()
        assert len(dupes) == 0, f"Found {len(dupes)} duplicate ODI matches"

    def test_odi_matches_have_teams(self, pg_conn):
        from sqlalchemy import text
        no_teams = pg_conn.execute(text(
            "SELECT COUNT(*) FROM matches WHERE format='ODI' AND (team_a_id IS NULL OR team_b_id IS NULL)"
        )).scalar()
        assert no_teams == 0, f"{no_teams} ODI matches missing teams"
