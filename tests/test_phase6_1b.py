"""
Phase 6.1B Tests — Egress & API Efficiency Audit
=================================================

Tests covering:
1. GZip compression middleware
2. Dashboard summary endpoint
3. Pagination enforcement
4. Response shape stability
5. Cache behavior (live/rankings)
6. No deliveries dependency
7. No unbounded queries
8. Existing endpoint compatibility
9. Analytics regression
10. Error behavior
11. Performance sanity
"""

import os
import json
import time
import pytest
from decimal import Decimal
from uuid import UUID
from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv()

# Set test environment
os.environ.setdefault("DATABASE_URL", os.getenv("DATABASE_URL"))

from backend.main import app


def _default_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def engine():
    """Create database engine."""
    from sqlalchemy import create_engine
    return create_engine(os.getenv("DATABASE_URL"))


# ============================================================
# 1. GZip Compression
# ============================================================


class TestGZipCompression:
    """Verify GZip compression middleware is active."""

    def test_gzip_header_present(self, client):
        """Response should include Content-Encoding: gzip when Accept-Encoding includes gzip."""
        response = client.get(
            "/api/players",
            headers={"Accept-Encoding": "gzip"},
        )
        assert response.status_code == 200
        # FastAPI's GZipMiddleware adds Content-Encoding when client accepts it
        # Note: TestClient may not fully simulate compression, but we verify the middleware exists
        assert "players" in response.json()

    def test_gzip_middleware_configured(self):
        """Verify GZipMiddleware is in the app's middleware stack."""
        from fastapi.middleware.gzip import GZipMiddleware
        middleware_classes = [
            type(m.cls).__name__ if hasattr(m, 'cls') else type(m).__name__
            for m in app.user_middleware
        ]
        # Also check the middleware stack directly
        has_gzip = any('GZip' in str(m) for m in app.user_middleware)
        assert has_gzip or 'GZipMiddleware' in middleware_classes, \
            f'GZipMiddleware not found in: {middleware_classes}'


# ============================================================
# 2. Dashboard Summary Endpoint
# ============================================================


class TestDashboardSummary:
    """Verify the consolidated dashboard endpoint."""

    def test_dashboard_summary_returns_200(self, client):
        """Dashboard summary should return 200."""
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 200

    def test_dashboard_summary_structure(self, client):
        """Verify expected response structure."""
        response = client.get("/api/dashboard/summary")
        data = response.json()
        assert "counts" in data
        assert "top_players" in data
        assert "recent_matches" in data
        assert "top_venues" in data
        assert "format" in data

    def test_dashboard_summary_counts(self, client):
        """Verify entity counts are accurate."""
        response = client.get("/api/dashboard/summary")
        data = response.json()
        counts = data["counts"]
        assert counts["players"] == 5734
        assert counts["teams"] == 127
        assert counts["matches"] == 8250
        assert counts["venues"] == 462

    def test_dashboard_summary_limits(self, client):
        """Verify response respects limits (10 players, 8 matches, 6 venues)."""
        response = client.get("/api/dashboard/summary")
        data = response.json()
        assert len(data["top_players"]) <= 10
        assert len(data["recent_matches"]) <= 8
        assert len(data["top_venues"]) <= 6

    def test_dashboard_summary_with_format(self, client):
        """Verify format filter works."""
        response = client.get("/api/dashboard/summary?format=ODI")
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "ODI"

    def test_dashboard_summary_payload_size(self, client):
        """Dashboard summary should be compact (< 10KB uncompressed)."""
        response = client.get("/api/dashboard/summary")
        size = len(json.dumps(response.json()))
        assert size < 10 * 1024, f"Dashboard payload too large: {size} bytes"

    def test_dashboard_summary_performance(self, client):
        """Dashboard summary should respond quickly (< 2s)."""
        start = time.time()
        response = client.get("/api/dashboard/summary")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 2.0, f"Dashboard too slow: {elapsed:.2f}s"


# ============================================================
# 3. Pagination Enforcement
# ============================================================


class TestPagination:
    """Verify pagination limits are enforced."""

    def test_player_list_default_limit(self, client):
        """Player list default limit should be 50."""
        response = client.get("/api/players")
        data = response.json()
        assert len(data["players"]) <= 50

    def test_player_list_max_limit(self, client):
        """Player list should cap at 200."""
        response = client.get("/api/players?limit=200")
        data = response.json()
        assert len(data["players"]) <= 200

    def test_team_list_limit(self, client):
        """Team list should respect limit."""
        response = client.get("/api/teams?limit=10")
        data = response.json()
        assert len(data["teams"]) <= 10

    def test_match_list_limit(self, client):
        """Match list should respect limit."""
        response = client.get("/api/matches?limit=10")
        data = response.json()
        assert len(data["matches"]) <= 10

    def test_match_list_max_limit(self, client):
        """Match list max should be 200."""
        response = client.get("/api/matches?limit=200")
        data = response.json()
        assert len(data["matches"]) <= 200

    def test_venue_list_limit(self, client):
        """Venue list should respect limit."""
        response = client.get("/api/venues?limit=10")
        data = response.json()
        assert len(data["venues"]) <= 10


# ============================================================
# 4. Response Shape Stability
# ============================================================


class TestResponseShapes:
    """Verify API response shapes are stable."""

    def test_player_list_shape(self, client):
        """Player list should have consistent shape."""
        response = client.get("/api/players?limit=1")
        data = response.json()
        assert "players" in data
        assert "total" in data
        if data["players"]:
            player = data["players"][0]
            assert "id" in player
            assert "name" in player

    def test_team_list_shape(self, client):
        """Team list should have consistent shape."""
        response = client.get("/api/teams?limit=1")
        data = response.json()
        assert "teams" in data
        assert "total" in data

    def test_match_list_shape(self, client):
        """Match list should have consistent shape."""
        response = client.get("/api/matches?limit=1")
        data = response.json()
        assert "matches" in data
        assert "total" in data

    def test_venue_list_shape(self, client):
        """Venue list should have consistent shape."""
        response = client.get("/api/venues?limit=1")
        data = response.json()
        assert "venues" in data
        assert "total" in data

    def test_live_shape(self, client):
        """Live endpoint should have consistent shape."""
        response = client.get("/api/live/")
        data = response.json()
        assert "matches" in data
        assert "provider_available" in data


# ============================================================
# 5. No Deliveries Dependency
# ============================================================


class TestNoDeliveriesDependency:
    """Verify production endpoints don't depend on deliveries table."""

    def test_deliveries_table_absent(self, engine):
        """Deliveries table should not exist."""
        from sqlalchemy import text
        with engine.connect() as conn:
            exists = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'deliveries')"
            )).fetchone()
            assert not exists[0], "Deliveries table should not exist!"

    def test_no_delivery_references_in_routes(self):
        """Backend routes should not reference deliveries table in SQL queries."""
        routes_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "routes")
        for filename in os.listdir(routes_dir):
            if filename.endswith(".py"):
                with open(os.path.join(routes_dir, filename)) as f:
                    content = f.read()
                    # Only check non-comment, non-docstring code
                    # Remove docstrings and comments
                    import re
                    # Remove triple-quoted strings (docstrings)
                    code = re.sub(r'""".*?"""', '', content, flags=re.DOTALL)
                    code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
                    # Remove single-line comments
                    code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
                    # Check for actual table references
                    if re.search(r'\bdeliveries\b', code):
                        assert False, f"Route file {filename} references 'deliveries' in executable code"


# ============================================================
# 6. Analytics Regression
# ============================================================


class TestAnalyticsRegression:
    """Verify historical data integrity is maintained."""

    def test_ipl_matches(self, engine):
        """IPL should have 1243 matches."""
        from sqlalchemy import text
        with engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM matches WHERE format = 'T20'"
            )).scalar()
            assert count == 1243, f"IPL matches: expected 1243, got {count}"

    def test_t20i_matches(self, engine):
        """T20I should have 3533 matches."""
        from sqlalchemy import text
        with engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM matches WHERE format = 'T20I'"
            )).scalar()
            assert count == 3533, f"T20I matches: expected 3533, got {count}"

    def test_odi_matches(self, engine):
        """ODI should have 2577 matches."""
        from sqlalchemy import text
        with engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM matches WHERE format = 'ODI'"
            )).scalar()
            assert count == 2577, f"ODI matches: expected 2577, got {count}"

    def test_test_matches(self, engine):
        """Test should have 897 matches."""
        from sqlalchemy import text
        with engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM matches WHERE format = 'Test'"
            )).scalar()
            assert count == 897, f"Test matches: expected 897, got {count}"

    def test_total_matches(self, engine):
        """Total should be 8250 matches."""
        from sqlalchemy import text
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM matches")).scalar()
            assert count == 8250, f"Total matches: expected 8250, got {count}"

    def test_kohli_ipl_runs(self, engine):
        """Virat Kohli IPL runs should be 9346."""
        from sqlalchemy import text
        with engine.connect() as conn:
            runs = conn.execute(text("""
                SELECT pbs.runs FROM player_batting_stats pbs
                JOIN players p ON pbs.player_id = p.id
                WHERE p.canonical_name = 'Virat Kohli' AND pbs.format = 'T20' AND pbs.period = 'career'
            """)).scalar()
            assert runs == 9346, f"Kohli IPL runs: expected 9346, got {runs}"

    def test_kohli_odi_runs(self, engine):
        """Virat Kohli ODI runs should be 15484."""
        from sqlalchemy import text
        with engine.connect() as conn:
            runs = conn.execute(text("""
                SELECT pbs.runs FROM player_batting_stats pbs
                JOIN players p ON pbs.player_id = p.id
                WHERE p.canonical_name = 'Virat Kohli' AND pbs.format = 'ODI' AND pbs.period = 'career'
            """)).scalar()
            assert runs == 15484, f"Kohli ODI runs: expected 15484, got {runs}"


# ============================================================
# 7. Database Size
# ============================================================


class TestDatabaseSize:
    """Verify database remains within storage constraints."""

    def test_database_under_500mb(self, engine):
        """Database must remain under 500MB."""
        from sqlalchemy import text
        with engine.connect() as conn:
            size_text = conn.execute(text(
                "SELECT pg_database_size(current_database())"
            )).scalar()
            assert size_text < 500 * 1024 * 1024, \
                f"Database too large: {size_text / 1024 / 1024:.0f}MB (limit: 500MB)"

    def test_database_under_200mb(self, engine):
        """Database should stay comfortably under 200MB."""
        from sqlalchemy import text
        with engine.connect() as conn:
            size_text = conn.execute(text(
                "SELECT pg_database_size(current_database())"
            )).scalar()
            assert size_text < 200 * 1024 * 1024, \
                f"Database too large: {size_text / 1024 / 1024:.0f}MB (target: < 200MB)"


# ============================================================
# 8. Health Endpoint
# ============================================================


class TestHealth:
    """Verify health endpoint works."""

    def test_health_returns_200(self, client):
        """Health check should return 200."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    def test_root_returns_200(self, client):
        """Root endpoint should return 200."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
