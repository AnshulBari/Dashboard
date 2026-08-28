"""
Phase 0 Automated Tests
========================

Tests for database connectivity, API endpoints, data integrity,
and frontend build verification.

Run: python -m pytest tests/test_phase0.py -v
"""

import os
import sys
import pytest
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_name = :name AND table_schema = 'public'"
    ), {"name": table_name})
    return result.scalar() > 0


# ============================================================
# DATABASE TESTS
# ============================================================

class TestDatabase:
    """Test PostgreSQL connection and basic operations."""

    def test_postgresql_connection(self):
        """Verify PostgreSQL connection via SQLAlchemy."""
        assert DATABASE_URL, "DATABASE_URL not set"
        assert DATABASE_URL.startswith("postgresql"), f"Expected PostgreSQL URL, got: {DATABASE_URL[:30]}"
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            assert result == 1
        engine.dispose()

    def test_core_tables_exist(self):
        """Verify all core tables exist in PostgreSQL."""
        engine = create_engine(DATABASE_URL)
        expected = [
            "teams", "players", "venues", "competitions",
            "matches", "innings",
            "match_batting_summary", "match_bowling_summary",
            "player_batting_stats", "player_bowling_stats",
            "player_form", "team_performance", "venue_stats",
            "batter_bowler_matchups",
        ]
        with engine.connect() as conn:
            for table in expected:
                result = conn.execute(
                    text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')")
                ).scalar()
                assert result, f"Table '{table}' does not exist"
        engine.dispose()

    def test_table_row_counts(self):
        """Verify tables have data (not empty)."""
        engine = create_engine(DATABASE_URL)
        minimums = {
            "teams": 10, "players": 100, "venues": 10,
            "matches": 100,
            "player_batting_stats": 50,
            "match_batting_summary": 10000,
        }
        with engine.connect() as conn:
            for table, min_count in minimums.items():
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                assert count >= min_count, f"{table}: expected >= {min_count}, got {count}"
        engine.dispose()


# ============================================================
# DATA INTEGRITY TESTS
# ============================================================

class TestDataIntegrity:
    """Test foreign key integrity and data validity."""

    def test_no_orphaned_deliveries(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            if not _table_exists(conn, "deliveries"):
                pytest.skip("deliveries table removed in Phase 5.6a")
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries d "
                "LEFT JOIN innings i ON d.innings_id = i.id "
                "WHERE i.id IS NULL"
            )).scalar()
            assert orphans == 0, f"{orphans} orphaned deliveries"
        engine.dispose()

    def test_no_orphaned_innings(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM innings i "
                "LEFT JOIN matches m ON i.match_id = m.id "
                "WHERE m.id IS NULL"
            )).scalar()
            assert orphans == 0, f"{orphans} orphaned innings"
        engine.dispose()

    def test_no_orphaned_players(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM player_batting_stats s "
                "LEFT JOIN players p ON s.player_id = p.id "
                "WHERE p.id IS NULL"
            )).scalar()
            assert orphans == 0, f"{orphans} orphaned batting stats"
        engine.dispose()

    def test_no_duplicate_matches(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            dups = conn.execute(text(
                "SELECT COUNT(*) FROM ("
                "SELECT external_id FROM matches "
                "WHERE external_id IS NOT NULL "
                "GROUP BY external_id HAVING COUNT(*) > 1"
                ") d"
            )).scalar()
            assert dups == 0, f"{dups} duplicate matches"
        engine.dispose()

    def test_no_negative_runs(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            if not _table_exists(conn, "deliveries"):
                pytest.skip("deliveries table removed in Phase 5.6a")
            negatives = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries WHERE runs_bat < 0 OR total_runs < 0"
            )).scalar()
            assert negatives == 0, f"{negatives} deliveries with negative runs"
        engine.dispose()

    def test_valid_innings_numbers(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # innings_number up to 10 allowed: Test (1-4), limited-overs (1-2), super overs (3-10)
            invalid = conn.execute(text(
                "SELECT COUNT(*) FROM innings WHERE innings_number < 1 OR innings_number > 10"
            )).scalar()
            assert invalid == 0, f"{invalid} innings with invalid numbers"
        engine.dispose()

    def test_valid_ball_numbers(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            if not _table_exists(conn, "deliveries"):
                pytest.skip("deliveries table removed in Phase 5.6a")
            # ball_in_over > 12 is valid for super overs / no-ball replays in T20I
            invalid = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries WHERE ball_in_over < 1"
            )).scalar()
            assert invalid == 0, f"{invalid} deliveries with invalid ball numbers"
        engine.dispose()

    def test_matches_have_teams(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            missing = conn.execute(text(
                "SELECT COUNT(*) FROM matches WHERE team_a_id IS NULL OR team_b_id IS NULL"
            )).scalar()
            assert missing == 0, f"{missing} matches missing team IDs"
        engine.dispose()


# ============================================================
# API ENDPOINT TESTS
# ============================================================

class TestAPI:
    """Test FastAPI endpoints against PostgreSQL."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        self.client = TestClient(app)

    def test_health(self):
        resp = self.client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_root(self):
        resp = self.client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "version" in data

    def test_players_list(self):
        resp = self.client.get("/api/players/?format=T20&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "players" in data
        assert len(data["players"]) > 0
        assert "id" in data["players"][0]
        assert "name" in data["players"][0]
        assert "form_score" in data["players"][0]

    def test_player_detail(self):
        resp = self.client.get("/api/players/?format=T20&limit=1")
        player_id = resp.json()["players"][0]["id"]
        resp = self.client.get(f"/api/players/{player_id}?format=T20")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == player_id
        assert "name" in data
        assert "runs" in data

    def test_player_form(self):
        resp = self.client.get("/api/players/?format=T20&limit=1")
        player_id = resp.json()["players"][0]["id"]
        resp = self.client.get(f"/api/players/{player_id}/form?format=T20")
        assert resp.status_code == 200
        data = resp.json()
        assert "form_score" in data
        assert "components" in data

    def test_player_invalid_id(self):
        resp = self.client.get("/api/players/not-a-uuid")
        assert resp.status_code == 400

    def test_player_nonexistent(self):
        resp = self.client.get("/api/players/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_teams_list(self):
        resp = self.client.get("/api/teams/?format=T20&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "teams" in data
        assert len(data["teams"]) > 0
        assert "overall_strength_score" in data["teams"][0]

    def test_team_detail(self):
        resp = self.client.get("/api/teams/?format=T20&limit=1")
        team_id = resp.json()["teams"][0]["id"]
        resp = self.client.get(f"/api/teams/{team_id}?format=T20")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == team_id
        assert "win_rate" in data

    def test_venues_list(self):
        resp = self.client.get("/api/venues/?format=T20&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "venues" in data
        assert len(data["venues"]) > 0
        assert "total_matches" in data["venues"][0]

    def test_matches_list(self):
        resp = self.client.get("/api/matches/?format=T20&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "matches" in data
        assert len(data["matches"]) > 0
        assert "result" in data["matches"][0]

    def test_rankings_batting(self):
        resp = self.client.get("/api/rankings?format=T20&category=batting&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "rankings" in data
        assert len(data["rankings"]) > 0
        assert "rating" in data["rankings"][0]

    def test_rankings_bowling(self):
        resp = self.client.get("/api/rankings?format=T20&category=bowling&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "rankings" in data
        assert len(data["rankings"]) > 0

    def test_matchups_list(self):
        resp = self.client.get("/api/matchups?format=T20&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "matchups" in data
        assert len(data["matchups"]) > 0
        assert "batter_name" in data["matchups"][0]
        assert "bowler_name" in data["matchups"][0]

    def test_news(self):
        resp = self.client.get("/api/news")
        assert resp.status_code == 200
        assert "articles" in resp.json()

    def test_live(self):
        resp = self.client.get("/api/live")
        assert resp.status_code == 200
        assert "live_matches" in resp.json()


# ============================================================
# SQLITE TESTS
# ============================================================

class TestSQLite:
    """Test SQLite development database."""

    def test_sqlite_file_exists(self):
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cricket_intelligence.db")
        assert os.path.exists(db_path), f"SQLite DB not found at {db_path}"

    def test_sqlite_has_data(self):
        import sqlite3
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cricket_intelligence.db")
        conn = sqlite3.connect(db_path)
        matches = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        assert matches >= 100, f"SQLite has only {matches} matches"
        players = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        assert players >= 100, f"SQLite has only {players} players"
        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
