"""
Phase 5.9 Tests: Backend Production Hardening & API Validation
===============================================================

Tests API-level correctness, validation, error handling, and production readiness.

Run: python -m pytest tests/test_phase5_9.py -v
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
_engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20, pool_timeout=60)


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
IPL_COMP = _scalar("SELECT id FROM competitions WHERE name = 'Indian Premier League'")
ODI_SAMPLE = _scalar("SELECT id FROM matches WHERE format = 'ODI' LIMIT 1")
TEST_SAMPLE = _scalar("SELECT id FROM matches WHERE format = 'Test' LIMIT 1")
VENUE_SAMPLE = _scalar("SELECT venue_id FROM matches GROUP BY venue_id ORDER BY COUNT(*) DESC LIMIT 1")
SEASON_SAMPLE = _scalar("SELECT id FROM seasons LIMIT 1")


# ============================================================
# HEALTH ENDPOINT
# ============================================================


class TestHealthEndpoint:
    def test_health_returns_200(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"


# ============================================================
# INPUT VALIDATION
# ============================================================


class TestInputValidation:
    def test_invalid_format_returns_400(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/by-year?format=INVALID")
        assert resp.status_code == 400
        assert "Invalid format" in resp.json()["detail"]

    def test_invalid_player_id_returns_400(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/api/analytics/players/not-a-uuid/career")
        assert resp.status_code == 400

    def test_invalid_team_id_returns_400(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/api/analytics/teams/not-a-uuid/by-format")
        assert resp.status_code == 400

    def test_invalid_match_id_returns_400(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/api/analytics/matches/not-a-uuid/detail")
        assert resp.status_code == 400

    def test_valid_formats_accepted(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        for fmt in ["T20", "T20I", "ODI", "Test"]:
            resp = client.get(f"/api/analytics/players/{KOHLI}/by-year?format={fmt}")
            assert resp.status_code == 200, f"Format {fmt} rejected"


# ============================================================
# ERROR HANDLING
# ============================================================


class TestErrorHandling:
    def test_unknown_player_returns_404(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/analytics/players/{fake_id}/career")
        assert resp.status_code == 404

    def test_unknown_match_returns_404(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/analytics/matches/{fake_id}/detail")
        assert resp.status_code == 404

    def test_unknown_competition_returns_404(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/api/analytics/competitions/{fake_id}/summary")
        assert resp.status_code == 404

    def test_invalid_profile_query_returns_400(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/api/analytics/profile/nonexistent")
        assert resp.status_code == 400


# ============================================================
# PLAYER ANALYTICS VIA API
# ============================================================


class TestPlayerAnalyticsAPI:
    def test_player_career(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/career")
        assert resp.status_code == 200
        data = resp.json()
        assert "T20" in data["batting"]
        assert "ODI" in data["batting"]
        assert "Test" in data["batting"]

    def test_player_by_year(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/by-year?format=ODI")
        assert resp.status_code == 200
        assert len(resp.json()["by_year"]) >= 10

    def test_player_by_competition(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/by-competition?format=T20")
        assert resp.status_code == 200
        comps = [r["competition"] for r in resp.json()["by_competition"]]
        assert "Indian Premier League" in comps

    def test_player_by_season(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/by-season?format=T20")
        assert resp.status_code == 200
        assert len(resp.json()["by_season"]) >= 5

    def test_player_vs_opponent(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/vs-opponent?format=ODI")
        assert resp.status_code == 200
        opponents = [r["opponent"] for r in resp.json()["vs_opponent"]]
        assert "Australia" in opponents

    def test_player_at_venue(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/at-venue?format=ODI")
        assert resp.status_code == 200
        assert len(resp.json()["at_venue"]) >= 5

    def test_player_history(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/history?format=ODI&limit=5")
        assert resp.status_code == 200
        assert len(resp.json()["matches"]) <= 5

    def test_player_progression(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/progression?format=ODI")
        assert resp.status_code == 200
        assert len(resp.json()["progression"]) >= 10


# ============================================================
# TEAM ANALYTICS VIA API
# ============================================================


class TestTeamAnalyticsAPI:
    def test_team_by_format(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/teams/{INDIA}/by-format")
        assert resp.status_code == 200
        formats = [r["format"] for r in resp.json()["by_format"]]
        assert "ODI" in formats

    def test_team_by_year(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/teams/{INDIA}/by-year?format=ODI")
        assert resp.status_code == 200
        assert len(resp.json()["by_year"]) >= 10

    def test_team_vs_team_overall(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/teams/{INDIA}/vs-team/{AUSTRALIA}")
        assert resp.status_code == 200
        total = sum(r["matches"] for r in resp.json()["by_format"])
        assert total >= 100

    def test_team_vs_team_filtered(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/teams/{INDIA}/vs-team/{AUSTRALIA}?format=ODI")
        assert resp.status_code == 200
        assert len(resp.json()["by_format"]) == 1
        assert resp.json()["by_format"][0]["format"] == "ODI"

    def test_team_at_venue(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/teams/{INDIA}/at-venue?format=ODI")
        assert resp.status_code == 200
        assert len(resp.json()["at_venue"]) >= 3

    def test_team_by_competition(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/teams/{INDIA}/by-competition")
        assert resp.status_code == 200
        assert len(resp.json()["by_competition"]) >= 1

    def test_team_history(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/teams/{INDIA}/history?format=ODI&limit=5")
        assert resp.status_code == 200
        assert len(resp.json()["matches"]) <= 5

    def test_team_trend(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/teams/{INDIA}/trend?format=ODI")
        assert resp.status_code == 200
        assert len(resp.json()["trend"]) >= 10


# ============================================================
# COMPETITION / SEASON / VENUE / MATCH VIA API
# ============================================================


class TestOtherAnalyticsAPI:
    def test_competition_summary(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/competitions/{IPL_COMP}/summary")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Indian Premier League"

    def test_season_matches(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/seasons/{SEASON_SAMPLE}/matches?limit=5")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_venue_by_format(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/venues/{VENUE_SAMPLE}/by-format")
        assert resp.status_code == 200
        assert len(resp.json()["by_format"]) >= 1

    def test_venue_teams(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/venues/{VENUE_SAMPLE}/teams?format=ODI")
        assert resp.status_code == 200
        assert len(resp.json()["teams"]) >= 1

    def test_venue_players(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/venues/{VENUE_SAMPLE}/players?format=ODI&limit=5")
        assert resp.status_code == 200
        assert len(resp.json()["players"]) <= 5

    def test_match_detail(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/matches/{ODI_SAMPLE}/detail")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["innings"]) >= 1
        assert len(data["batting"]) >= 10

    def test_match_detail_test_multi_innings(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/matches/{TEST_SAMPLE}/detail")
        assert resp.status_code == 200
        assert len(resp.json()["innings"]) >= 2

    def test_data_completeness(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/api/analytics/data-completeness")
        assert resp.status_code == 200
        assert resp.json()["total_matches"] == 8250


# ============================================================
# FORMAT ISOLATION VIA API
# ============================================================


class TestFormatIsolationAPI:
    def test_odi_no_t20_in_opponents(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get(f"/api/analytics/players/{KOHLI}/vs-opponent?format=ODI")
        opponents = [r["opponent"] for r in resp.json()["vs_opponent"]]
        assert "Royal Challengers Bangalore" not in opponents
        assert "Mumbai Indians" not in opponents

    def test_format_filter_enforced(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        for fmt in ["T20", "T20I", "ODI", "Test"]:
            resp = client.get(f"/api/analytics/players/{KOHLI}/by-year?format={fmt}")
            assert resp.status_code == 200


# ============================================================
# REGRESSION VIA API
# ============================================================


class TestRegressionAPI:
    def test_ipl_match_count(self):
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='T20'") == 1243

    def test_kohli_ipl_runs(self):
        runs = _scalar(
            "SELECT pbs.runs FROM player_batting_stats pbs "
            "JOIN players p ON pbs.player_id = p.id "
            "WHERE p.canonical_name = 'Virat Kohli' AND pbs.format = 'T20' AND pbs.period = 'career'"
        )
        assert runs == 9346

    def test_total_matches(self):
        assert _scalar("SELECT COUNT(*) FROM matches") == 8250

    def test_t20i_count(self):
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='T20I'") == 3533

    def test_odi_count(self):
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='ODI'") == 2577

    def test_test_count(self):
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='Test'") == 897


# ============================================================
# PERFORMANCE
# ============================================================


class TestPerformance:
    def test_player_career_speed(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        start = time.time()
        resp = client.get(f"/api/analytics/players/{KOHLI}/career")
        elapsed = (time.time() - start) * 1000
        assert resp.status_code == 200
        assert elapsed < 2000, f"Player career took {elapsed:.0f}ms"

    def test_team_vs_team_speed(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        start = time.time()
        resp = client.get(f"/api/analytics/teams/{INDIA}/vs-team/{AUSTRALIA}")
        elapsed = (time.time() - start) * 1000
        assert resp.status_code == 200
        assert elapsed < 2000, f"Team vs team took {elapsed:.0f}ms"


# ============================================================
# DATABASE / INFRASTRUCTURE
# ============================================================


class TestInfrastructure:
    def test_database_under_500mb(self):
        size = _scalar("SELECT pg_size_pretty(pg_database_size(current_database()))")
        mb = float(size.replace(" MB", ""))
        assert mb < 500, f"Database size: {size}"

    def test_deliveries_table_absent(self):
        exists = _scalar(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'deliveries' AND table_schema = 'public'"
        )
        assert exists == 0

    def test_no_raw_sql_injection_in_player_list(self):
        """Player list sort uses whitelisted columns."""
        from backend.utils.validation import PLAYER_SORT_COLUMNS
        # Verify the whitelist is safe
        for key in PLAYER_SORT_COLUMNS:
            assert "." in PLAYER_SORT_COLUMNS[key], f"Sort column {key} not properly qualified"
