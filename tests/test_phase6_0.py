"""
Phase 6.0 Tests: Production Readiness, Data Integrity & Serving-Layer Audit
============================================================================

Comprehensive validation of the cricket analytics platform's serving layer.

Run: python -m pytest tests/test_phase6_0.py -v
"""

import os
import sys
import time
import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
_engine = create_engine(
    DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20, pool_timeout=60
)


def _q(sql, params=None):
    with _engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).fetchall()
        return [dict(r._mapping) for r in rows]


def _scalar(sql, params=None):
    with _engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar()


# Known entities
KOHLI = _scalar("SELECT id FROM players WHERE canonical_name = 'Virat Kohli'")
INDIA = _scalar("SELECT id FROM teams WHERE canonical_name = 'India'")
AUSTRALIA = _scalar("SELECT id FROM teams WHERE canonical_name = 'Australia'")
ENGLAND = _scalar("SELECT id FROM teams WHERE canonical_name = 'England'")
IPL_COMP = _scalar("SELECT id FROM competitions WHERE name = 'Indian Premier League'")
IPL_SAMPLE = _scalar("SELECT id FROM matches WHERE format = 'T20' LIMIT 1")
ODI_SAMPLE = _scalar("SELECT id FROM matches WHERE format = 'ODI' LIMIT 1")
TEST_SAMPLE = _scalar("SELECT id FROM matches WHERE format = 'Test' LIMIT 1")
T20I_SAMPLE = _scalar("SELECT id FROM matches WHERE format = 'T20I' LIMIT 1")


# ============================================================
# OBJECTIVE 1: SERVING-LAYER DEPENDENCY AUDIT
# ============================================================


class TestServingDependencyAudit:
    """Verify no production code depends on deliveries table."""

    def test_backend_no_delivery_table_queries(self):
        """Backend routes/services must not query deliveries table."""
        import subprocess
        result = subprocess.run(
            ["grep", "-rn", "FROM deliveries", "backend/", "--include=*.py"],
            capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__))
        )
        lines = [l for l in result.stdout.strip().split("\n") if l]
        assert len(lines) == 0, f"Backend queries deliveries table: {lines}"

    def test_deliveries_table_absent(self):
        exists = _scalar(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'deliveries' AND table_schema = 'public'"
        )
        assert exists == 0, "deliveries table should not exist in production"

    def test_analytics_service_works_without_deliveries(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.player_career(conn, KOHLI)
            assert "batting" in result
            assert "T20" in result["batting"]
            assert "ODI" in result["batting"]
            assert "Test" in result["batting"]


# ============================================================
# OBJECTIVE 2: ANALYTICAL DIMENSION INTEGRITY
# ============================================================


class TestAnalyticalDimensions:
    """Verify all analytical dimensions work correctly."""

    def test_player_by_format(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            for fmt in ["T20", "T20I", "ODI", "Test"]:
                result = analytics.player_by_year(conn, KOHLI, fmt, batting=True)
                assert isinstance(result, list)

    def test_player_by_competition(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.player_by_competition(conn, KOHLI, "T20", batting=True)
            assert len(result) >= 1

    def test_player_by_season(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.player_by_season(conn, KOHLI, "T20", batting=True)
            assert len(result) >= 1

    def test_player_vs_opponent(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.player_vs_opponent(conn, KOHLI, "ODI", batting=True)
            opponents = [r["opponent"] for r in result]
            assert "Australia" in opponents

    def test_player_at_venue(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.player_at_venue(conn, KOHLI, "ODI")
            assert len(result) >= 5

    def test_team_by_format(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.team_by_format(conn, INDIA)
            formats = [r["format"] for r in result]
            assert "ODI" in formats
            assert "Test" in formats

    def test_team_vs_team(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.team_vs_team(conn, INDIA, AUSTRALIA)
            total = sum(r["matches"] for r in result["by_format"])
            assert total >= 100

    def test_team_vs_team_format_filtered(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.team_vs_team(conn, INDIA, AUSTRALIA, fmt="ODI")
            formats = [r["format"] for r in result["by_format"]]
            assert formats == ["ODI"]

    def test_match_detail(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.match_detail(conn, ODI_SAMPLE)
            assert "innings" in result
            assert "batting" in result
            assert "bowling" in result
            assert len(result["innings"]) >= 2

    def test_match_detail_multi_innings(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.match_detail(conn, TEST_SAMPLE)
            assert len(result["innings"]) >= 2


# ============================================================
# OBJECTIVE 3: PLAYER STATISTICS INTEGRITY
# ============================================================


class TestPlayerStatisticsIntegrity:
    """Verify player career totals across all formats."""

    def test_kohli_career_all_formats(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            career = analytics.player_career(conn, KOHLI)
            assert "T20" in career["batting"]
            assert "T20I" in career["batting"]
            assert "ODI" in career["batting"]
            assert "Test" in career["batting"]

    def test_kohli_ipl_runs_regression(self):
        runs = _scalar(
            "SELECT pbs.runs FROM player_batting_stats pbs "
            "JOIN players p ON pbs.player_id = p.id "
            "WHERE p.canonical_name = 'Virat Kohli' "
            "AND pbs.format = 'T20' AND pbs.period = 'career'"
        )
        assert runs == 9346

    def test_kohli_t20i_runs(self):
        runs = _scalar(
            "SELECT pbs.runs FROM player_batting_stats pbs "
            "JOIN players p ON pbs.player_id = p.id "
            "WHERE p.canonical_name = 'Virat Kohli' "
            "AND pbs.format = 'T20I' AND pbs.period = 'career'"
        )
        assert runs == 4095

    def test_kohli_odi_runs(self):
        runs = _scalar(
            "SELECT pbs.runs FROM player_batting_stats pbs "
            "JOIN players p ON pbs.player_id = p.id "
            "WHERE p.canonical_name = 'Virat Kohli' "
            "AND pbs.format = 'ODI' AND pbs.period = 'career'"
        )
        assert runs == 15484

    def test_kohli_test_runs(self):
        runs = _scalar(
            "SELECT pbs.runs FROM player_batting_stats pbs "
            "JOIN players p ON pbs.player_id = p.id "
            "WHERE p.canonical_name = 'Virat Kohli' "
            "AND pbs.format = 'Test' AND pbs.period = 'career'"
        )
        assert runs == 8817

    def test_no_duplicate_canonical_players(self):
        dupes = _scalar(
            "SELECT COUNT(*) FROM ("
            "SELECT canonical_name FROM players "
            "GROUP BY canonical_name HAVING COUNT(*) > 1"
            ") sub"
        )
        assert dupes == 0, f"Found {dupes} duplicate canonical player names"

    def test_no_null_player_in_scorecards(self):
        null_bat = _scalar("SELECT COUNT(*) FROM match_batting_summary WHERE player_id IS NULL")
        null_bowl = _scalar("SELECT COUNT(*) FROM match_bowling_summary WHERE player_id IS NULL")
        assert null_bat == 0
        assert null_bowl == 0


# ============================================================
# OBJECTIVE 4: TEAM & OPPONENT INTEGRITY
# ============================================================


class TestTeamIntegrity:
    """Verify team entity correctness."""

    def test_no_duplicate_teams(self):
        dupes = _scalar(
            "SELECT COUNT(*) FROM ("
            "SELECT canonical_name FROM teams "
            "GROUP BY canonical_name HAVING COUNT(*) > 1"
            ") sub"
        )
        assert dupes == 0

    def test_national_teams_type(self):
        india_type = _scalar(
            "SELECT team_type FROM teams WHERE canonical_name = 'India'"
        )
        assert india_type == "national"

    def test_franchise_teams_type(self):
        rcb_type = _scalar(
            "SELECT team_type FROM teams WHERE canonical_name = 'Royal Challengers Bangalore'"
        )
        assert rcb_type == "franchise"

    def test_india_vs_australia_has_data(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.team_vs_team(conn, INDIA, AUSTRALIA)
            assert len(result["by_format"]) >= 2

    def test_india_vs_england_head_to_head(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.team_vs_team(conn, INDIA, ENGLAND, fmt="Test")
            assert len(result["by_format"]) == 1
            assert result["by_format"][0]["format"] == "Test"

    def test_team_match_history(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.team_match_history(conn, INDIA, "ODI", limit=5)
            assert len(result) <= 5


# ============================================================
# OBJECTIVE 5: COMPETITION & SEASON INTEGRITY
# ============================================================


class TestCompetitionIntegrity:
    """Verify competition and season data handling."""

    def test_ipl_competition_exists(self):
        assert IPL_COMP is not None

    def test_ipl_seasons_exist(self):
        count = _scalar(
            "SELECT COUNT(*) FROM seasons s "
            "JOIN competitions c ON s.competition_id = c.id "
            "WHERE c.name = 'Indian Premier League'"
        )
        assert count >= 15

    def test_competition_summary(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.competition_summary(conn, IPL_COMP)
            assert result["name"] == "Indian Premier League"
            assert len(result["seasons"]) >= 15

    def test_null_competition_handled(self):
        count = _scalar("SELECT COUNT(*) FROM matches WHERE competition_id IS NULL")
        assert count > 0, "Expected some matches without competition"

    def test_null_competition_matches_accessible(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.player_by_competition(conn, KOHLI, "ODI", batting=True)
            assert any(r["competition"] == "Unknown" for r in result)


# ============================================================
# OBJECTIVE 6: SCORECARD INTEGRITY
# ============================================================


class TestScorecardIntegrity:
    """Verify scorecard correctness and no inflation."""

    def test_no_duplicate_scorecard_rows(self):
        dup_bat = _scalar(
            "SELECT COUNT(*) FROM ("
            "SELECT match_id, innings_id, player_id FROM match_batting_summary "
            "GROUP BY match_id, innings_id, player_id HAVING COUNT(*) > 1"
            ") sub"
        )
        dup_bowl = _scalar(
            "SELECT COUNT(*) FROM ("
            "SELECT match_id, innings_id, player_id FROM match_bowling_summary "
            "GROUP BY match_id, innings_id, player_id HAVING COUNT(*) > 1"
            ") sub"
        )
        assert dup_bat == 0
        assert dup_bowl == 0

    def test_no_negative_values(self):
        assert _scalar("SELECT COUNT(*) FROM match_batting_summary WHERE runs < 0") == 0
        assert _scalar("SELECT COUNT(*) FROM match_batting_summary WHERE balls < 0") == 0
        assert _scalar("SELECT COUNT(*) FROM match_bowling_summary WHERE runs_conceded < 0") == 0
        assert _scalar("SELECT COUNT(*) FROM match_bowling_summary WHERE wickets < 0") == 0



    def test_no_orphan_scorecard_rows(self):
        orph_bat = _scalar(
            "SELECT COUNT(*) FROM match_batting_summary mbs "
            "WHERE NOT EXISTS (SELECT 1 FROM innings i WHERE i.id = mbs.innings_id)"
        )
        orph_bowl = _scalar(
            "SELECT COUNT(*) FROM match_bowling_summary mbs "
            "WHERE NOT EXISTS (SELECT 1 FROM innings i WHERE i.id = mbs.innings_id)"
        )
        assert orph_bat == 0
        assert orph_bowl == 0

    def test_scorecard_batting_sample(self):
        """Spot-check scorecard against innings totals for IPL."""
        result = _q("""
            SELECT i.total_runs as innings_total, SUM(mbs.runs) as scorecard_total
            FROM match_batting_summary mbs
            JOIN innings i ON mbs.innings_id = i.id
            JOIN matches m ON mbs.match_id = m.id
            WHERE m.format = 'T20' AND i.total_runs > 100
            GROUP BY i.id, i.total_runs
            LIMIT 5
        """)
        for r in result:
            diff = abs(r["innings_total"] - r["scorecard_total"])
            assert diff <= 30, f"Innings {r['innings_total']} vs scorecard {r['scorecard_total']}"


# ============================================================
# OBJECTIVE 7: ANALYTICS CORRECTNESS
# ============================================================


class TestAnalyticsCorrectness:
    """Verify analytics endpoints return correct data."""

    def test_player_career_endpoint(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/career")
        assert resp.status_code == 200
        data = resp.json()
        assert "batting" in data
        assert "T20" in data["batting"]
        assert data["batting"]["T20"]["runs"] == 9346

    def test_player_by_year_format_isolation(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/by-year?format=ODI")
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "ODI"
        assert len(data["by_year"]) >= 10

    def test_team_vs_team_format_filter(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/teams/{INDIA}/vs-team/{AUSTRALIA}?format=ODI")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["by_format"]) == 1
        assert data["by_format"][0]["format"] == "ODI"

    def test_match_detail_scorecard(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/matches/{ODI_SAMPLE}/detail")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["innings"]) >= 2
        assert len(data["batting"]) >= 10

    def test_invalid_format_rejected(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/by-year?format=INVALID")
        assert resp.status_code == 400

    def test_unknown_entity_returns_404(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        fake = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/analytics/players/{fake}/career")
        assert resp.status_code == 404


# ============================================================
# OBJECTIVE 8: DATABASE INTEGRITY
# ============================================================


class TestDatabaseIntegrity:
    """Comprehensive database integrity checks."""

    def test_no_orphan_innings(self):
        orph = _scalar(
            "SELECT COUNT(*) FROM innings i "
            "WHERE NOT EXISTS (SELECT 1 FROM matches m WHERE m.id = i.match_id)"
        )
        assert orph == 0

    def test_no_matches_without_innings(self):
        no_inn = _scalar(
            "SELECT COUNT(*) FROM matches m "
            "WHERE NOT EXISTS (SELECT 1 FROM innings i WHERE i.match_id = m.id) "
            "AND m.result_type = 'win'"
        )
        assert no_inn == 0, "Winning matches should have innings"

    def test_format_values_only(self):
        fmts = _q("SELECT DISTINCT format FROM matches ORDER BY format")
        assert [f["format"] for f in fmts] == ["ODI", "T20", "T20I", "Test"]

    def test_result_types_consistent(self):
        types = _q("SELECT DISTINCT result_type FROM matches ORDER BY result_type")
        type_names = [t["result_type"] for t in types]
        assert "no result" not in type_names, "Should be 'no_result' not 'no result'"

    def test_no_null_venue_in_matches(self):
        """Most matches should have a venue (some may be NULL for abandoned)."""
        null_venue = _scalar("SELECT COUNT(*) FROM matches WHERE venue_id IS NULL")
        total = _scalar("SELECT COUNT(*) FROM matches")
        assert null_venue / total < 0.05, f"{null_venue}/{total} matches missing venue"

    def test_innings_total_includes_extras(self):
        """Test innings total_runs should include extras after Phase 6.0 fix."""
        # Sample 10 Test innings and verify they match JSON
        import json
        rows = _q("""
            SELECT m.external_id, i.innings_number, i.total_runs
            FROM matches m
            JOIN innings i ON i.match_id = m.id
            WHERE m.format = 'Test' AND i.total_runs > 100
            ORDER BY RANDOM() LIMIT 5
        """)
        mismatches = 0
        for r in rows:
            json_path = f"data/raw/test/{r['external_id']}.json"
            if not os.path.exists(json_path):
                continue
            with open(json_path, "r") as f:
                data = json.load(f)
            inn_idx = r["innings_number"] - 1
            if inn_idx >= len(data.get("innings", [])):
                continue
            overs = data["innings"][inn_idx].get("overs", [])
            json_total = sum(
                d["runs"]["total"] for o in overs for d in o.get("deliveries", [])
            )
            if json_total != r["total_runs"]:
                mismatches += 1
        assert mismatches == 0, f"{mismatches} Test innings still have wrong total_runs"


# ============================================================
# OBJECTIVE 9: FORMAT ISOLATION
# ============================================================


class TestFormatIsolation:
    """Verify strict format isolation across all dimensions."""

    def test_kohli_format_totals_independent(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            career = analytics.player_career(conn, KOHLI)
            t20 = career["batting"]["T20"]["runs"]
            t20i = career["batting"]["T20I"]["runs"]
            odi = career["batting"]["ODI"]["runs"]
            test = career["batting"]["Test"]["runs"]
            # All should be different (no cross-contamination)
            assert t20 == 9346
            assert t20i == 4095
            assert odi == 15484
            assert test == 8817

    def test_odi_opponents_no_ipl_teams(self):
        from backend.services import analytics
        with _engine.connect() as conn:
            result = analytics.player_vs_opponent(conn, KOHLI, "ODI", batting=True)
            opponents = [r["opponent"] for r in result]
            ipl_teams = ["Mumbai Indians", "Royal Challengers Bangalore",
                         "Chennai Super Kings", "Kolkata Knight Riders"]
            for ipl in ipl_teams:
                assert ipl not in opponents, f"IPL team {ipl} found in ODI opponents"

    def test_match_count_per_format(self):
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format = 'T20'") == 1243
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format = 'T20I'") == 3533
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format = 'ODI'") == 2577
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format = 'Test'") == 897


# ============================================================
# OBJECTIVE 10: DATABASE SIZE
# ============================================================


class TestDatabaseSize:
    """Verify database remains within Supabase Free Plan limits."""

    def test_database_under_500mb(self):
        size = _scalar("SELECT pg_size_pretty(pg_database_size(current_database()))")
        mb = float(size.replace(" MB", ""))
        assert mb < 500, f"Database size: {size}"

    def test_no_delivery_table(self):
        exists = _scalar(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'deliveries' AND table_schema = 'public'"
        )
        assert exists == 0


# ============================================================
# OBJECTIVE 11: TOTAL MATCH COUNT REGRESSION
# ============================================================


class TestTotalRegression:
    """Regression checks for all formats."""

    def test_total_matches(self):
        assert _scalar("SELECT COUNT(*) FROM matches") == 8250

    def test_total_innings(self):
        total = _scalar("SELECT COUNT(*) FROM innings")
        assert total >= 18000

    def test_total_batting_summary(self):
        total = _scalar("SELECT COUNT(*) FROM match_batting_summary")
        assert total >= 150000

    def test_total_bowling_summary(self):
        total = _scalar("SELECT COUNT(*) FROM match_bowling_summary")
        assert total >= 100000

    def test_total_players(self):
        total = _scalar("SELECT COUNT(*) FROM players")
        assert total >= 5000

    def test_total_venues(self):
        total = _scalar("SELECT COUNT(*) FROM venues")
        assert total >= 400

    def test_total_teams(self):
        total = _scalar("SELECT COUNT(*) FROM teams")
        assert total >= 100


# ============================================================
# OBJECTIVE 12: PERFORMANCE
# ============================================================


class TestPerformance:
    """Verify key queries complete within acceptable time."""

    def test_player_career_speed(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        start = time.time()
        resp = client.get(f"/api/analytics/players/{KOHLI}/career")
        elapsed_ms = (time.time() - start) * 1000
        assert resp.status_code == 200
        assert elapsed_ms < 2000, f"Player career: {elapsed_ms:.0f}ms"

    def test_team_vs_team_speed(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        start = time.time()
        resp = client.get(f"/api/analytics/teams/{INDIA}/vs-team/{AUSTRALIA}")
        elapsed_ms = (time.time() - start) * 1000
        assert resp.status_code == 200
        assert elapsed_ms < 2000, f"Team vs team: {elapsed_ms:.0f}ms"

    def test_match_detail_speed(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        start = time.time()
        resp = client.get(f"/api/analytics/matches/{ODI_SAMPLE}/detail")
        elapsed_ms = (time.time() - start) * 1000
        assert resp.status_code == 200
        assert elapsed_ms < 2000, f"Match detail: {elapsed_ms:.0f}ms"
