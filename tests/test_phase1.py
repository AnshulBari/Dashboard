"""
Phase 1 Tests: Universal Cricket Data Model
=============================================

Tests for format-aware analytics, cross-format support,
new database columns, and API compatibility.

Run: python -m pytest tests/test_phase1.py -v
"""

import os
import sys
import json
import pytest
from pathlib import Path
from sqlalchemy import create_engine, text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


# ============================================================
# FORMAT CONFIG TESTS
# ============================================================

class TestFormatConfig:
    """Test format-aware phase classification."""

    def test_t20_phases(self):
        from data_pipeline.pipeline.format_config import classify_phase
        assert classify_phase(0, "T20") == "powerplay"
        assert classify_phase(5, "T20") == "powerplay"
        assert classify_phase(6, "T20") == "middle"
        assert classify_phase(14, "T20") == "middle"
        assert classify_phase(15, "T20") == "death"
        assert classify_phase(19, "T20") == "death"

    def test_t20i_same_as_t20(self):
        from data_pipeline.pipeline.format_config import classify_phase
        assert classify_phase(3, "T20I") == "powerplay"
        assert classify_phase(10, "T20I") == "middle"
        assert classify_phase(18, "T20I") == "death"

    def test_odi_phases(self):
        from data_pipeline.pipeline.format_config import classify_phase
        assert classify_phase(0, "ODI") == "powerplay"
        assert classify_phase(9, "ODI") == "powerplay"
        assert classify_phase(10, "ODI") == "middle"
        assert classify_phase(39, "ODI") == "middle"
        assert classify_phase(40, "ODI") == "death"
        assert classify_phase(49, "ODI") == "death"

    def test_test_has_no_t20_phases(self):
        from data_pipeline.pipeline.format_config import classify_phase
        assert classify_phase(0, "Test") == "general"
        assert classify_phase(50, "Test") == "general"
        assert classify_phase(200, "Test") == "general"

    def test_unknown_format_defaults_to_t20(self):
        from data_pipeline.pipeline.format_config import classify_phase
        assert classify_phase(3, "Unknown") == "powerplay"

    def test_format_rules_properties(self):
        from data_pipeline.pipeline.format_config import get_format_rules
        t20 = get_format_rules("T20")
        assert t20.standard_overs == 20
        assert t20.max_innings == 2
        assert t20.is_multi_day is False

        odi = get_format_rules("ODI")
        assert odi.standard_overs == 50
        assert odi.powerplay_end == 9  # ODI first powerplay is 10 overs

        test = get_format_rules("Test")
        assert test.standard_overs is None
        assert test.max_innings == 4
        assert test.is_multi_day is True
        assert test.is_first_class is True


# ============================================================
# CROSS-FORMAT FIXTURE TESTS
# ============================================================

class TestCrossFormatFixtures:
    """Test that cross-format fixtures can be parsed by the reader."""

    def _load_fixture(self, filename):
        from data_pipeline.pipeline.reader import flatten_match
        # Check fixtures dir first, then data/raw/ for backwards compat
        fixtures_dir = Path("data/raw/fixtures")
        path = fixtures_dir / filename
        if not path.exists():
            path = Path("data/raw") / filename
        with open(path, "r") as f:
            data = json.load(f)
        return flatten_match(data, filename)

    def test_ipl_fixture_parses(self):
        rows = self._load_fixture("test_ipl_match.json")
        assert len(rows) > 0
        assert rows[0]["format"] == "T20"
        assert rows[0]["venue"] == "Wankhede Stadium"
        assert rows[0]["season"] == "2024"
        assert rows[0]["result_type"] == "win"
        # Check both innings exist
        innings_numbers = set(r["innings_number"] for r in rows)
        assert 1 in innings_numbers
        assert 2 in innings_numbers

    def test_t20i_fixture_parses(self):
        rows = self._load_fixture("test_t20i_match.json")
        assert len(rows) > 0
        assert rows[0]["format"] == "T20I"
        assert rows[0]["result_type"] == "win"
        teams = set(r["batting_team"] for r in rows)
        assert "India" in teams
        assert "Australia" in teams

    def test_odi_fixture_parses(self):
        rows = self._load_fixture("test_odi_match.json")
        assert len(rows) > 0
        assert rows[0]["format"] == "ODI"
        innings_numbers = set(r["innings_number"] for r in rows)
        assert 1 in innings_numbers
        assert 2 in innings_numbers

    def test_test_fixture_has_4_innings(self):
        rows = self._load_fixture("test_match.json")
        assert len(rows) > 0
        assert rows[0]["format"] == "Test"
        innings_numbers = set(r["innings_number"] for r in rows)
        assert len(innings_numbers) == 4  # 4 innings

    def test_test_draw_fixture(self):
        rows = self._load_fixture("test_draw_match.json")
        assert len(rows) > 0
        assert rows[0]["format"] == "Test"
        assert rows[0]["result_type"] == "draw"

    def test_extras_detected(self):
        rows = self._load_fixture("test_t20i_match.json")
        extras = [r for r in rows if r["extra_type"]]
        assert len(extras) > 0
        extra_types = set(r["extra_type"] for r in extras)
        assert "wide" in extra_types or "noball" in extra_types


# ============================================================
# DATABASE SCHEMA TESTS
# ============================================================

class TestPhase1Schema:
    """Test Phase 1 schema additions exist in PostgreSQL."""

    def test_format_config_table_exists(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'format_config')")
            ).scalar()
            assert result
        engine.dispose()

    def test_seasons_table_exists(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'seasons')")
            ).scalar()
            assert result
        engine.dispose()

    def test_format_config_has_data(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM format_config")).scalar()
            assert count >= 4  # T20, T20I, ODI, Test
        engine.dispose()

    def test_matches_has_result_type(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'matches' AND column_name = 'result_type')")
            ).scalar()
            assert result
        engine.dispose()

    def test_innings_has_test_columns(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            for col in ["declared", "all_out", "follow_on"]:
                result = conn.execute(
                    text(f"SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'innings' AND column_name = '{col}')")
                ).scalar()
                assert result, f"Column 'innings.{col}' not found"
        engine.dispose()

    def test_teams_has_team_type(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'teams' AND column_name = 'team_type')")
            ).scalar()
            assert result
        engine.dispose()

    def test_matches_has_season_id(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'matches' AND column_name = 'season_id')")
            ).scalar()
            assert result
        engine.dispose()


# ============================================================
# IPL REGRESSION TESTS
# ============================================================

class TestIPLRegression:
    """Verify existing IPL data is intact after Phase 1 migration."""

    def test_match_count(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM matches")).scalar()
            assert count == 1243, f"Expected 1243 matches, got {count}"
        engine.dispose()

    def test_delivery_count(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM deliveries")).scalar()
            assert count == 295732, f"Expected 295732 deliveries, got {count}"
        engine.dispose()

    def test_player_count(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
            assert count == 807, f"Expected 807 players, got {count}"
        engine.dispose()

    def test_batting_stats_count(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM player_batting_stats")).scalar()
            assert count == 738, f"Expected 738 batting stats, got {count}"
        engine.dispose()

    def test_v_kohli_runs(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            runs = conn.execute(
                text("SELECT runs FROM player_batting_stats WHERE player_id = (SELECT id FROM players WHERE canonical_name = 'V Kohli' LIMIT 1) AND format = 'T20' AND period = 'career'")
            ).scalar()
            assert runs == 9346, f"Expected V Kohli to have 9346 runs, got {runs}"
        engine.dispose()

    def test_form_score_exists(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM player_form")).scalar()
            assert count >= 500, f"Expected >= 500 form scores, got {count}"
        engine.dispose()

    def test_no_orphaned_records(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries d "
                "LEFT JOIN innings i ON d.innings_id = i.id "
                "WHERE i.id IS NULL"
            )).scalar()
            assert orphans == 0, f"{orphans} orphaned deliveries"
        engine.dispose()


# ============================================================
# API TESTS
# ============================================================

class TestPhase1API:
    """Test new and modified API endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        self.client = TestClient(app)

    def test_competitions_list(self):
        resp = self.client.get("/api/competitions")
        assert resp.status_code == 200
        data = resp.json()
        assert "competitions" in data
        assert len(data["competitions"]) > 0

    def test_competitions_filter_by_format(self):
        resp = self.client.get("/api/competitions?format=T20")
        assert resp.status_code == 200
        data = resp.json()
        for comp in data["competitions"]:
            assert comp["format"] == "T20"

    def test_competition_detail(self):
        resp = self.client.get("/api/competitions")
        comp_id = resp.json()["competitions"][0]["id"]
        resp = self.client.get(f"/api/competitions/{comp_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == comp_id
        assert "seasons" in data

    def test_format_config_available(self):
        """Test that format config is accessible through the API indirectly."""
        resp = self.client.get("/api/players/?format=ODI&limit=1")
        assert resp.status_code == 200

    def test_existing_endpoints_still_work(self):
        """Regression: all existing endpoints should still work."""
        endpoints = [
            "/api/health",
            "/",
            "/api/players/?format=T20&limit=2",
            "/api/teams/?format=T20&limit=2",
            "/api/venues/?format=T20&limit=2",
            "/api/matches/?format=T20&limit=2",
            "/api/matchups?format=T20&limit=2",
            "/api/rankings?format=T20&category=batting&limit=2",
            "/api/news",
            "/api/live",
        ]
        for endpoint in endpoints:
            resp = self.client.get(endpoint)
            assert resp.status_code == 200, f"Endpoint {endpoint} returned {resp.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
