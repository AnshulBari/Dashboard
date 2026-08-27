"""
Phase 4 Tests: Test Cricket Support
=====================================
Tests for Test match ingestion, 4-innings support, draws, declarations,
follow-ons, cross-format identity, and full regression.
"""

import os
import json
import pytest
from pathlib import Path

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
# TEST DATA TESTS
# ============================================================

class TestTestData:
    """Test that Test match data was ingested correctly."""

    def test_test_matches_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text("SELECT COUNT(*) FROM matches WHERE format='Test'")).scalar()
        assert count >= 5, f"Expected >= 5 Test matches, got {count}"

    def test_test_innings_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM innings i JOIN matches m ON i.match_id=m.id WHERE m.format='Test'"
        )).scalar()
        assert count >= 15, f"Expected >= 15 Test innings, got {count}"

    def test_test_deliveries_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM deliveries d JOIN matches m ON d.match_id=m.id WHERE m.format='Test'"
        )).scalar()
        assert count >= 1000, f"Expected >= 1000 Test deliveries, got {count}"

    def test_four_innings_match(self, pg_conn):
        """At least one Test match should have 4 innings."""
        from sqlalchemy import text
        rows = pg_conn.execute(text(
            "SELECT m.external_id, COUNT(*) as inn_count "
            "FROM innings i JOIN matches m ON i.match_id=m.id "
            "WHERE m.format='Test' GROUP BY m.external_id HAVING COUNT(*)=4"
        )).fetchall()
        assert len(rows) >= 1, "No 4-innings Test match found"

    def test_three_innings_match(self, pg_conn):
        """The innings victory fixture should have 3 innings."""
        from sqlalchemy import text
        rows = pg_conn.execute(text(
            "SELECT m.external_id, COUNT(*) as inn_count "
            "FROM innings i JOIN matches m ON i.match_id=m.id "
            "WHERE m.format='Test' GROUP BY m.external_id HAVING COUNT(*)=3"
        )).fetchall()
        assert len(rows) >= 1, "No 3-innings Test match found"

    def test_test_teams_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(DISTINCT t.id) FROM teams t "
            "JOIN team_performance tp ON t.id=tp.team_id WHERE tp.format='Test'"
        )).scalar()
        assert count >= 4, f"Expected >= 4 Test teams, got {count}"

    def test_test_players_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(DISTINCT player_id) FROM player_batting_stats WHERE format='Test'"
        )).scalar()
        assert count >= 20, f"Expected >= 20 Test batting players, got {count}"


# ============================================================
# TEST INNINGS METADATA
# ============================================================

class TestInningsMetadata:
    """Test that declared, all_out, follow_on are populated correctly."""

    def test_declarations_tracked(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM innings i JOIN matches m ON i.match_id=m.id "
            "WHERE m.format='Test' AND i.declared=true"
        )).scalar()
        assert count >= 1, f"Expected >= 1 declared innings, got {count}"

    def test_all_outs_tracked(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM innings i JOIN matches m ON i.match_id=m.id "
            "WHERE m.format='Test' AND i.all_out=true"
        )).scalar()
        assert count >= 3, f"Expected >= 3 all-out innings, got {count}"

    def test_follow_ons_tracked(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM innings i JOIN matches m ON i.match_id=m.id "
            "WHERE m.format='Test' AND i.follow_on=true"
        )).scalar()
        assert count >= 1, f"Expected >= 1 follow-on, got {count}"

    def test_draw_result(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM matches WHERE format='Test' AND result_type='draw'"
        )).scalar()
        assert count >= 1, f"Expected >= 1 drawn Test, got {count}"


# ============================================================
# TEST ANALYTICS
# ============================================================

class TestTestAnalytics:
    """Test that Test analytics are format-scoped."""

    def test_test_batting_stats_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM player_batting_stats WHERE format='Test'"
        )).scalar()
        assert count >= 20, f"Expected >= 20 Test batting stats, got {count}"

    def test_test_bowling_stats_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM player_bowling_stats WHERE format='Test'"
        )).scalar()
        assert count >= 15, f"Expected >= 15 Test bowling stats, got {count}"

    def test_test_team_performance_exists(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM team_performance WHERE format='Test'"
        )).scalar()
        assert count >= 4, f"Expected >= 4 Test team performance, got {count}"

    def test_test_venue_stats_exist(self, pg_conn):
        from sqlalchemy import text
        count = pg_conn.execute(text(
            "SELECT COUNT(*) FROM venue_stats WHERE format='Test'"
        )).scalar()
        assert count >= 4, f"Expected >= 4 Test venue stats, got {count}"

    def test_top_test_batter(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT p.canonical_name, b.runs FROM player_batting_stats b "
            "JOIN players p ON b.player_id=p.id WHERE b.format='Test' "
            "ORDER BY b.runs DESC LIMIT 1"
        )).fetchone()
        assert r is not None, "No Test batting stats"
        assert r[1] > 0, f"Top Test batter has 0 runs: {r[0]}"


# ============================================================
# CROSS-FORMAT IDENTITY
# ============================================================

class TestCrossFormatIdentity:
    """Players appearing in Test + other formats."""

    def test_virat_kohli_four_formats(self, pg_conn):
        """Virat Kohli should have T20 + T20I + ODI + Test stats."""
        from sqlalchemy import text
        formats = pg_conn.execute(text(
            "SELECT DISTINCT b.format FROM player_batting_stats b "
            "JOIN players p ON b.player_id=p.id "
            "WHERE p.canonical_name='Virat Kohli' ORDER BY b.format"
        )).fetchall()
        fmt_list = [r[0] for r in formats]
        assert "T20" in fmt_list, f"Missing T20, got {fmt_list}"
        assert "T20I" in fmt_list, f"Missing T20I, got {fmt_list}"
        assert "ODI" in fmt_list, f"Missing ODI, got {fmt_list}"
        assert "Test" in fmt_list, f"Missing Test, got {fmt_list}"

    def test_kl_rahul_four_formats(self, pg_conn):
        from sqlalchemy import text
        formats = pg_conn.execute(text(
            "SELECT DISTINCT b.format FROM player_batting_stats b "
            "JOIN players p ON b.player_id=p.id "
            "WHERE p.canonical_name='KL Rahul' ORDER BY b.format"
        )).fetchall()
        fmt_list = [r[0] for r in formats]
        assert "Test" in fmt_list, f"Missing Test for KL Rahul, got {fmt_list}"

    def test_rohit_sharma_three_formats(self, pg_conn):
        from sqlalchemy import text
        formats = pg_conn.execute(text(
            "SELECT DISTINCT b.format FROM player_batting_stats b "
            "JOIN players p ON b.player_id=p.id "
            "WHERE p.canonical_name='Rohit Sharma' ORDER BY b.format"
        )).fetchall()
        fmt_list = [r[0] for r in formats]
        assert "Test" in fmt_list, f"Missing Test for Rohit Sharma, got {fmt_list}"
        assert "ODI" in fmt_list, f"Missing ODI for Rohit Sharma"


# ============================================================
# FORMAT ISOLATION
# ============================================================

class TestFormatIsolation:
    """Verify Test stats don't contaminate other formats."""

    def test_ipl_matches_unchanged(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text("SELECT COUNT(*) FROM matches WHERE format='T20'")).scalar()
        assert c == 1243, f"IPL matches changed: {c}"

    def test_ipl_deliveries_unchanged(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text(
            "SELECT COUNT(*) FROM deliveries d JOIN matches m ON d.match_id=m.id WHERE m.format='T20'"
        )).scalar()
        assert c == 295732, f"IPL deliveries changed: {c}"

    def test_virat_kohli_ipl_unchanged(self, pg_conn):
        from sqlalchemy import text
        r = pg_conn.execute(text(
            "SELECT runs FROM player_batting_stats WHERE "
            "player_id=(SELECT id FROM players WHERE canonical_name='Virat Kohli' LIMIT 1) "
            "AND format='T20' LIMIT 1"
        )).fetchone()
        assert r is not None, "Virat Kohli IPL stats not found"
        assert r[0] == 9346, f"V Kohli IPL runs changed: {r[0]}"

    def test_t20i_unchanged(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text("SELECT COUNT(*) FROM matches WHERE format='T20I'")).scalar()
        assert c == 5, f"T20I matches changed: {c}"

    def test_odi_unchanged(self, pg_conn):
        from sqlalchemy import text
        c = pg_conn.execute(text("SELECT COUNT(*) FROM matches WHERE format='ODI'")).scalar()
        assert c == 8, f"ODI matches changed: {c}"

    def test_virat_kohli_test_is_separate(self, pg_conn):
        """Test stats should not equal T20 stats."""
        from sqlalchemy import text
        t20 = pg_conn.execute(text(
            "SELECT runs FROM player_batting_stats WHERE "
            "player_id=(SELECT id FROM players WHERE canonical_name='Virat Kohli' LIMIT 1) "
            "AND format='T20' LIMIT 1"
        )).scalar()
        test = pg_conn.execute(text(
            "SELECT runs FROM player_batting_stats WHERE "
            "player_id=(SELECT id FROM players WHERE canonical_name='Virat Kohli' LIMIT 1) "
            "AND format='Test' LIMIT 1"
        )).scalar()
        assert t20 != test, f"T20 and Test runs should differ, both = {t20}"


# ============================================================
# DATA QUALITY
# ============================================================

class TestDataQuality:
    """Post-Test-ingestion data quality checks."""

    def test_no_duplicate_matches(self, pg_conn):
        from sqlalchemy import text
        dupes = pg_conn.execute(text(
            "SELECT external_id, COUNT(*) FROM matches GROUP BY external_id HAVING COUNT(*)>1"
        )).fetchall()
        assert len(dupes) == 0, f"Found {len(dupes)} duplicate matches"

    def test_no_orphaned_innings(self, pg_conn):
        from sqlalchemy import text
        orphans = pg_conn.execute(text(
            "SELECT COUNT(*) FROM innings i "
            "WHERE NOT EXISTS (SELECT 1 FROM matches m WHERE m.id=i.match_id)"
        )).scalar()
        assert orphans == 0, f"Found {orphans} orphaned innings"

    def test_no_orphaned_deliveries(self, pg_conn):
        from sqlalchemy import text
        orphans = pg_conn.execute(text(
            "SELECT COUNT(*) FROM deliveries d "
            "WHERE NOT EXISTS (SELECT 1 FROM innings i WHERE i.id=d.innings_id)"
        )).scalar()
        assert orphans == 0, f"Found {orphans} orphaned deliveries"

    def test_no_invalid_formats(self, pg_conn):
        from sqlalchemy import text
        bad = pg_conn.execute(text(
            "SELECT DISTINCT format FROM matches WHERE format NOT IN ('T20','T20I','ODI','Test')"
        )).fetchall()
        assert len(bad) == 0, f"Invalid formats: {[r[0] for r in bad]}"


# ============================================================
# TEST FIXTURES
# ============================================================

class TestFixtures:
    """Verify Test fixture files are valid."""

    def test_test_fixture_dir_exists(self):
        assert Path("data/raw/test").exists(), "data/raw/test not found"

    def test_test_fixtures_present(self):
        files = list(Path("data/raw/test").glob("*.json"))
        assert len(files) >= 5, f"Expected >= 5 Test fixtures, got {len(files)}"

    def test_test_fixture_valid_json(self):
        for f in list(Path("data/raw/test").glob("*.json"))[:3]:
            with open(f) as fp:
                data = json.load(fp)
            assert "info" in data, f"{f.name} missing 'info'"
            assert "innings" in data, f"{f.name} missing 'innings'"
            assert data["info"].get("match_type") == "Test", f"{f.name} not Test format"

    def test_test_fixture_has_four_innings(self):
        """At least one fixture should have 4 innings."""
        found = False
        for f in Path("data/raw/test").glob("*.json"):
            with open(f) as fp:
                data = json.load(fp)
            if len(data.get("innings", [])) == 4:
                found = True
                break
        assert found, "No fixture with 4 innings found"

    def test_test_fixture_has_draw(self):
        """At least one fixture should be a draw."""
        found = False
        for f in Path("data/raw/test").glob("*.json"):
            with open(f) as fp:
                data = json.load(fp)
            if data.get("info", {}).get("outcome", {}).get("draw"):
                found = True
                break
        assert found, "No drawn Test fixture found"

    def test_test_fixture_has_declaration(self):
        """At least one fixture should have a declared innings."""
        found = False
        for f in Path("data/raw/test").glob("*.json"):
            with open(f) as fp:
                data = json.load(fp)
            for inn in data.get("innings", []):
                if inn.get("declared"):
                    found = True
                    break
            if found:
                break
        assert found, "No declaration fixture found"

    def test_test_fixture_has_follow_on(self):
        """At least one fixture should have a follow-on."""
        found = False
        for f in Path("data/raw/test").glob("*.json"):
            with open(f) as fp:
                data = json.load(fp)
            for inn in data.get("innings", []):
                if inn.get("follow_on"):
                    found = True
                    break
            if found:
                break
        assert found, "No follow-on fixture found"


# ============================================================
# TEST PHASE CLASSIFICATION
# ============================================================

class TestPhaseClassification:
    """Test that Test cricket uses 'general' phase, not T20 phases."""

    def test_test_returns_general_phase(self):
        from data_pipeline.pipeline.format_config import classify_phase
        assert classify_phase(5, "Test") == "general"
        assert classify_phase(50, "Test") == "general"
        assert classify_phase(0, "Test") == "general"

    def test_t20_still_uses_powerplay(self):
        from data_pipeline.pipeline.format_config import classify_phase
        assert classify_phase(3, "T20") == "powerplay"
        assert classify_phase(10, "T20") == "middle"
        assert classify_phase(18, "T20") == "death"

    def test_odi_still_uses_powerplay(self):
        from data_pipeline.pipeline.format_config import classify_phase
        assert classify_phase(5, "ODI") == "powerplay"
        assert classify_phase(25, "ODI") == "middle"
        assert classify_phase(45, "ODI") == "death"
