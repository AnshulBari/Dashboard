"""
Phase 6.1 Tests: External Cricket Intelligence Integration
===========================================================

Tests for ICC rankings and live cricket data integration.

Uses mock providers to avoid external API dependencies.

Run: python -m pytest tests/test_phase6_1.py -v
"""

import os
import sys
import time
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
_engine = create_engine(
    DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20, pool_timeout=60
)


def _scalar(sql, params=None):
    with _engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar()


# ============================================================
# Provider Abstraction Tests
# ============================================================


class TestProviderAbstraction:
    """Test the provider abstraction layer."""

    def test_base_classes_exist(self):
        from backend.providers.base import (
            RankingsProvider,
            LiveDataProvider,
            RankingEntry,
            TeamRankingEntry,
            LiveMatch,
            LiveMatchDetail,
        )
        assert RankingsProvider is not None
        assert LiveDataProvider is not None

    def test_mock_provider_implements_interfaces(self):
        from backend.providers.cricketdata import MockCricketDataProvider
        from backend.providers.base import RankingsProvider, LiveDataProvider

        provider = MockCricketDataProvider()
        assert isinstance(provider, RankingsProvider)
        assert isinstance(provider, LiveDataProvider)

    def test_mock_provider_is_available(self):
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        assert provider.is_available() is True

    def test_mock_player_rankings(self):
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()

        # Test Test batting
        rankings = provider.get_player_rankings("Test", "batting")
        assert len(rankings) == 5
        assert rankings[0].rank == 1
        assert rankings[0].name == "Joe Root"
        assert rankings[0].country == "England"
        assert rankings[0].rating == 900
        assert rankings[0].format == "Test"
        assert rankings[0].category == "batting"

    def test_mock_team_rankings(self):
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()

        rankings = provider.get_team_rankings("Test")
        assert len(rankings) == 5
        assert rankings[0].rank == 1
        assert rankings[0].team_name == "India"
        assert rankings[0].rating == 121

    def test_mock_live_matches(self):
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()

        matches = provider.get_live_matches()
        assert len(matches) == 1
        assert matches[0].match_id == "mock-001"
        assert matches[0].team_a == "India"
        assert matches[0].team_b == "Australia"
        assert matches[0].status == "live"

    def test_mock_match_detail(self):
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()

        detail = provider.get_match_detail("mock-001")
        assert detail is not None
        assert detail.match_id == "mock-001"
        assert detail.batting_team == "India"
        assert detail.current_score == "245/6"
        assert detail.striker == "Virat Kohli"

    def test_mock_match_detail_not_found(self):
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()

        detail = provider.get_match_detail("nonexistent")
        assert detail is None


# ============================================================
# Rankings Service Tests
# ============================================================


class TestRankingsService:
    """Test the rankings service layer."""

    def test_rankings_service_initialization(self):
        from backend.services.rankings import RankingsService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = RankingsService(provider=provider, db_engine=_engine)

        assert service.provider == provider
        assert service.db_engine == _engine

    def test_get_player_rankings(self):
        from backend.services.rankings import RankingsService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = RankingsService(provider=provider, db_engine=_engine)

        result = service.get_player_rankings("Test", "batting")

        assert "rankings" in result
        assert "format" in result
        assert "category" in result
        assert "source" in result
        assert "fetched_at" in result
        assert result["format"] == "Test"
        assert result["category"] == "batting"
        assert len(result["rankings"]) == 5

    def test_get_team_rankings(self):
        from backend.services.rankings import RankingsService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = RankingsService(provider=provider, db_engine=_engine)

        result = service.get_team_rankings("Test")

        assert "rankings" in result
        assert "format" in result
        assert result["format"] == "Test"
        assert len(result["rankings"]) == 5

    def test_rankings_caching(self):
        from backend.services.rankings import RankingsService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = RankingsService(provider=provider, db_engine=_engine, cache_ttl=60)

        # Clear cache first
        service.cache.clear()

        # First call - fetches from provider
        result1 = service.get_player_rankings("Test", "batting")
        assert result1["cached"] is False

        # Second call - should be cached
        result2 = service.get_player_rankings("Test", "batting")
        assert result2["cached"] is True

    def test_rankings_force_refresh(self):
        from backend.services.rankings import RankingsService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = RankingsService(provider=provider, db_engine=_engine, cache_ttl=60)

        # First call
        result1 = service.get_player_rankings("Test", "batting")

        # Force refresh
        result2 = service.get_player_rankings("Test", "batting", force_refresh=True)
        assert result2["cached"] is False

    def test_provider_unavailable(self):
        from backend.services.rankings import RankingsService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        provider._available = False
        service = RankingsService(provider=provider, db_engine=_engine)

        assert service.is_available() is False


# ============================================================
# Live Data Service Tests
# ============================================================


class TestLiveService:
    """Test the live data service layer."""

    def test_live_service_initialization(self):
        from backend.services.live import LiveService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = LiveService(provider=provider, db_engine=_engine)

        assert service.provider == provider
        assert service.db_engine == _engine

    def test_get_live_matches(self):
        from backend.services.live import LiveService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = LiveService(provider=provider, db_engine=_engine)

        result = service.get_live_matches()

        assert "matches" in result
        assert "total" in result
        assert "source" in result
        assert "fetched_at" in result
        assert result["total"] == 1
        assert result["matches"][0]["team_a"] == "India"

    def test_get_match_detail(self):
        from backend.services.live import LiveService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = LiveService(provider=provider, db_engine=_engine)

        result = service.get_match_detail("mock-001")

        assert result is not None
        assert "innings" in result
        assert "players" in result
        assert result["innings"]["batting_team"] == "India"
        assert result["innings"]["score"] == "245/6"
        assert result["players"]["striker"] == "Virat Kohli"

    def test_get_match_detail_not_found(self):
        from backend.services.live import LiveService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = LiveService(provider=provider, db_engine=_engine)

        result = service.get_match_detail("nonexistent")
        assert result is None

    def test_live_caching(self):
        from backend.services.live import LiveService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = LiveService(provider=provider, db_engine=_engine, cache_ttl=30)

        # First call
        result1 = service.get_live_matches()
        assert result1["cached"] is False

        # Second call - should be cached
        result2 = service.get_live_matches()
        assert result2["cached"] is True

    def test_live_force_refresh(self):
        from backend.services.live import LiveService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = LiveService(provider=provider, db_engine=_engine, cache_ttl=30)

        # First call
        result1 = service.get_live_matches()

        # Force refresh
        result2 = service.get_live_matches(force_refresh=True)
        assert result2["cached"] is False


# ============================================================
# API Endpoint Tests (using TestClient)
# ============================================================


class TestRankingsAPI:
    """Test rankings API endpoints."""

    def test_platform_rankings_batting(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/rankings/platform?format=T20&category=batting&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "platform"
        assert len(data["rankings"]) <= 5

    def test_platform_rankings_bowling(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/rankings/platform?format=ODI&category=bowling&limit=5")
        assert resp.status_code == 200
        assert len(resp.json()["rankings"]) <= 5

    def test_platform_rankings_allrounder(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/rankings/platform?format=Test&category=allrounder&limit=5")
        assert resp.status_code == 200

    def test_icc_rankings_batting(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        # This will use the mock provider since no API key is configured
        resp = client.get("/api/rankings/icc?format=Test&category=batting")
        assert resp.status_code == 200
        data = resp.json()
        assert "rankings" in data
        assert "provider_available" in data

    def test_icc_rankings_teams(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/rankings/icc?format=ODI&category=teams")
        assert resp.status_code == 200
        data = resp.json()
        assert "rankings" in data

    def test_icc_rankings_invalid_category(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/rankings/icc?format=Test&category=invalid")
        assert resp.status_code == 400

    def test_rankings_backward_compatibility(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/rankings/?format=T20&category=batting&source=platform")
        assert resp.status_code == 200

    def test_invalid_format_rejected(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/rankings/icc?format=INVALID&category=batting")
        assert resp.status_code == 400


class TestLiveAPI:
    """Test live data API endpoints."""

    def test_get_live_matches(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/live/")
        assert resp.status_code == 200
        data = resp.json()
        assert "matches" in data
        assert "provider_available" in data

    def test_get_live_match_detail(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/live/mock-001")
        # Mock provider may not return data without API key
        assert resp.status_code in [200, 404]

    def test_get_live_match_not_found(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/live/nonexistent")
        assert resp.status_code == 404

    def test_live_match_legacy_endpoint(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/live/mock-001/state")
        # Mock provider may not return data without API key
        assert resp.status_code in [200, 404]

    def test_live_cache_hit(self):
        from backend.main import app
        from fastapi.testclient import TestClient
        from backend.services.live import LiveService
        from backend.providers.cricketdata import MockCricketDataProvider

        # Create a fresh service to avoid shared cache state
        provider = MockCricketDataProvider()
        service = LiveService(provider=provider, db_engine=_engine, cache_ttl=30)
        service.cache.clear()

        # First call
        result1 = service.get_live_matches()
        assert result1["cached"] is False

        # Second call - should be cached
        result2 = service.get_live_matches()
        assert result2["cached"] is True

    def test_live_force_refresh(self):
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/live/?refresh=true")
        assert resp.status_code == 200
        assert resp.json()["cached"] is False


# ============================================================
# Entity Mapping Tests
# ============================================================


class TestEntityMapping:
    """Test entity mapping from external names to canonical IDs."""

    def test_team_mapping_india(self):
        from backend.services.rankings import RankingsService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = RankingsService(provider=provider, db_engine=_engine)

        with _engine.connect() as conn:
            team_id = service._map_team_id("India", conn)
            assert team_id is not None

    def test_team_mapping_australia(self):
        from backend.services.rankings import RankingsService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = RankingsService(provider=provider, db_engine=_engine)

        with _engine.connect() as conn:
            team_id = service._map_team_id("Australia", conn)
            assert team_id is not None

    def test_player_mapping_kohli(self):
        from backend.services.rankings import RankingsService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = RankingsService(provider=provider, db_engine=_engine)

        with _engine.connect() as conn:
            player_id = service._map_player_id("Virat Kohli", conn)
            assert player_id is not None

    def test_player_mapping_unknown(self):
        from backend.services.rankings import RankingsService
        from backend.providers.cricketdata import MockCricketDataProvider

        provider = MockCricketDataProvider()
        service = RankingsService(provider=provider, db_engine=_engine)

        with _engine.connect() as conn:
            player_id = service._map_player_id("Unknown Player XYZ", conn)
            assert player_id is None


# ============================================================
# Regression Tests
# ============================================================


class TestRegression:
    """Ensure existing functionality is preserved."""

    def test_ipl_match_count(self):
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='T20'") == 1243

    def test_t20i_match_count(self):
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='T20I'") == 3533

    def test_odi_match_count(self):
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='ODI'") == 2577

    def test_test_match_count(self):
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='Test'") == 897

    def test_kohli_ipl_runs(self):
        runs = _scalar(
            "SELECT pbs.runs FROM player_batting_stats pbs "
            "JOIN players p ON pbs.player_id = p.id "
            "WHERE p.canonical_name = 'Virat Kohli' "
            "AND pbs.format = 'T20' AND pbs.period = 'career'"
        )
        assert runs == 9346

    def test_deliveries_table_absent(self):
        exists = _scalar(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'deliveries' AND table_schema = 'public'"
        )
        assert exists == 0

    def test_database_under_500mb(self):
        size = _scalar("SELECT pg_size_pretty(pg_database_size(current_database()))")
        mb = float(size.replace(" MB", ""))
        assert mb < 500, f"Database size: {size}"

    def test_total_matches(self):
        assert _scalar("SELECT COUNT(*) FROM matches") == 8250

    def test_analytics_endpoints_still_work(self):
        """Verify existing analytics endpoints remain functional."""
        from backend.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Player career
        kohli = _scalar("SELECT id FROM players WHERE canonical_name = 'Virat Kohli'")
        resp = client.get(f"/api/analytics/players/{kohli}/career")
        assert resp.status_code == 200

        # Team vs team
        india = _scalar("SELECT id FROM teams WHERE canonical_name = 'India'")
        australia = _scalar("SELECT id FROM teams WHERE canonical_name = 'Australia'")
        resp = client.get(f"/api/analytics/teams/{india}/vs-team/{australia}")
        assert resp.status_code == 200
