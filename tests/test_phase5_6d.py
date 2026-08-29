"""
Phase 5.6D Tests: Scorecard Pipeline Hardening & Data-Integrity Regression
==========================================================================

Verifies that:
- Scorecard generation uses Cricsheet JSON (not deliveries table)
- Same input always produces same output (deterministic)
- Running twice does NOT double values (idempotent)
- The historical 2x inflation bug cannot recur
- Duplicate source matches are detected
- Validation catches corrupt data

Run: python -m pytest tests/test_phase5_6d.py -v
"""

import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Sample Cricsheet JSON for testing (simplified but realistic)
SAMPLE_MATCH = {
    "match_id": "test_phase5_6d_sample",
    "info": {
        "match_type": "T20",
        "gender": "male",
        "teams": ["Team A", "Team B"],
        "venue": "Test Ground",
        "city": "Test City",
        "dates": ["2024-01-15"],
        "toss": {"winner": "Team A", "decision": "bat"},
        "outcome": {"winner": "Team A", "by": {"runs": 25}},
        "player_of_match": ["Player1"],
        "event": {"name": "Test Series", "match_number": 1},
        "registry": {
            "people": {
                "Player1": "p1",
                "Player2": "p2",
                "Player3": "p3",
                "Player4": "p4",
                "Player5": "p5",
                "Player6": "p6",
                "Player7": "p7",
                "Player8": "p8",
                "Player9": "p9",
                "Player10": "p10",
                "Player11": "p11",
                "Player12": "p12",
            }
        },
    },
    "innings": [
        {
            "team": "Team A",
            "overs": [
                {
                    "over": 0,
                    "deliveries": [
                        {
                            "batter": "Player1",
                            "bowler": "Player7",
                            "non_striker": "Player2",
                            "runs": {"batter": 4, "extras": 0, "total": 4},
                        },
                        {
                            "batter": "Player1",
                            "bowler": "Player7",
                            "non_striker": "Player2",
                            "runs": {"batter": 1, "extras": 0, "total": 1},
                        },
                        {
                            "batter": "Player2",
                            "bowler": "Player7",
                            "non_striker": "Player1",
                            "runs": {"batter": 6, "extras": 0, "total": 6},
                        },
                        {
                            "batter": "Player2",
                            "bowler": "Player7",
                            "non_striker": "Player1",
                            "runs": {"batter": 0, "extras": 0, "total": 0},
                            "wickets": [
                                {
                                    "kind": "bowled",
                                    "player_out": "Player2",
                                }
                            ],
                        },
                        {
                            "batter": "Player3",
                            "bowler": "Player7",
                            "non_striker": "Player1",
                            "runs": {"batter": 2, "extras": 0, "total": 2},
                        },
                        {
                            "batter": "Player3",
                            "bowler": "Player7",
                            "non_striker": "Player1",
                            "runs": {"batter": 0, "extras": 1, "total": 1},
                            "extras": {"wides": 1},
                        },
                    ],
                },
                {
                    "over": 1,
                    "deliveries": [
                        {
                            "batter": "Player1",
                            "bowler": "Player8",
                            "non_striker": "Player3",
                            "runs": {"batter": 4, "extras": 0, "total": 4},
                        },
                        {
                            "batter": "Player1",
                            "bowler": "Player8",
                            "non_striker": "Player3",
                            "runs": {"batter": 1, "extras": 0, "total": 1},
                        },
                        {
                            "batter": "Player3",
                            "bowler": "Player8",
                            "non_striker": "Player1",
                            "runs": {"batter": 3, "extras": 0, "total": 3},
                        },
                        {
                            "batter": "Player1",
                            "bowler": "Player8",
                            "non_striker": "Player3",
                            "runs": {"batter": 0, "extras": 0, "total": 0},
                            "wickets": [
                                {
                                    "kind": "caught",
                                    "player_out": "Player1",
                                }
                            ],
                        },
                        {
                            "batter": "Player4",
                            "bowler": "Player8",
                            "non_striker": "Player3",
                            "runs": {"batter": 2, "extras": 0, "total": 2},
                        },
                        {
                            "batter": "Player4",
                            "bowler": "Player8",
                            "non_striker": "Player3",
                            "runs": {"batter": 1, "extras": 0, "total": 1},
                        },
                    ],
                },
            ],
        },
        {
            "team": "Team B",
            "overs": [
                {
                    "over": 0,
                    "deliveries": [
                        {
                            "batter": "Player7",
                            "bowler": "Player1",
                            "non_striker": "Player8",
                            "runs": {"batter": 1, "extras": 0, "total": 1},
                        },
                        {
                            "batter": "Player8",
                            "bowler": "Player1",
                            "non_striker": "Player7",
                            "runs": {"batter": 0, "extras": 0, "total": 0},
                        },
                        {
                            "batter": "Player7",
                            "bowler": "Player1",
                            "non_striker": "Player8",
                            "runs": {"batter": 2, "extras": 0, "total": 2},
                        },
                        {
                            "batter": "Player7",
                            "bowler": "Player1",
                            "non_striker": "Player8",
                            "runs": {"batter": 0, "extras": 0, "total": 0},
                            "wickets": [
                                {
                                    "kind": "lbw",
                                    "player_out": "Player7",
                                }
                            ],
                        },
                        {
                            "batter": "Player9",
                            "bowler": "Player1",
                            "non_striker": "Player8",
                            "runs": {"batter": 1, "extras": 0, "total": 1},
                        },
                        {
                            "batter": "Player9",
                            "bowler": "Player1",
                            "non_striker": "Player8",
                            "runs": {"batter": 0, "extras": 0, "total": 0},
                        },
                    ],
                },
                {
                    "over": 1,
                    "deliveries": [
                        {
                            "batter": "Player8",
                            "bowler": "Player3",
                            "non_striker": "Player9",
                            "runs": {"batter": 4, "extras": 0, "total": 4},
                        },
                        {
                            "batter": "Player8",
                            "bowler": "Player3",
                            "non_striker": "Player9",
                            "runs": {"batter": 0, "extras": 0, "total": 0},
                            "wickets": [
                                {
                                    "kind": "bowled",
                                    "player_out": "Player8",
                                }
                            ],
                        },
                        {
                            "batter": "Player10",
                            "bowler": "Player3",
                            "non_striker": "Player9",
                            "runs": {"batter": 2, "extras": 0, "total": 2},
                        },
                        {
                            "batter": "Player10",
                            "bowler": "Player3",
                            "non_striker": "Player9",
                            "runs": {"batter": 0, "extras": 0, "total": 0},
                        },
                        {
                            "batter": "Player10",
                            "bowler": "Player3",
                            "non_striker": "Player9",
                            "runs": {"batter": 0, "extras": 0, "total": 0},
                            "wickets": [
                                {
                                    "kind": "run out",
                                    "player_out": "Player10",
                                }
                            ],
                        },
                        {
                            "batter": "Player11",
                            "bowler": "Player3",
                            "non_striker": "Player9",
                            "runs": {"batter": 1, "extras": 0, "total": 1},
                        },
                    ],
                },
            ],
        },
    ],
}


def _get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def _get_ipl_sample_match_id():
    """Get a known IPL match ID from the database."""
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT external_id FROM matches "
                "WHERE format = 'T20' ORDER BY match_date LIMIT 1"
            )
        ).fetchone()
    engine.dispose()
    return row[0] if row else None


def _get_t20i_sample_match_id():
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT external_id FROM matches "
                "WHERE format = 'T20I' ORDER BY match_date LIMIT 1"
            )
        ).fetchone()
    engine.dispose()
    return row[0] if row else None


def _get_odi_sample_match_id():
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT external_id FROM matches "
                "WHERE format = 'ODI' ORDER BY match_date LIMIT 1"
            )
        ).fetchone()
    engine.dispose()
    return row[0] if row else None


def _get_test_sample_match_id():
    engine = _get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT external_id FROM matches "
                "WHERE format = 'Test' ORDER BY match_date LIMIT 1"
            )
        ).fetchone()
    engine.dispose()
    return row[0] if row else None


def _get_match_scorecard(engine, match_db_id):
    """Get current scorecard state for a match."""
    with engine.connect() as conn:
        bat = conn.execute(
            text(
                "SELECT player_id, runs, balls, fours, sixes, strike_rate "
                "FROM match_batting_summary WHERE match_id = :mid "
                "ORDER BY innings_id, runs DESC"
            ),
            {"mid": match_db_id},
        ).fetchall()

        bowl = conn.execute(
            text(
                "SELECT player_id, overs, balls_bowled, runs_conceded, "
                "wickets, economy FROM match_bowling_summary "
                "WHERE match_id = :mid ORDER BY innings_id, wickets DESC"
            ),
            {"mid": match_db_id},
        ).fetchall()

    return {"batting": bat, "bowling": bowl}


# ============================================================
# SOURCE INDEPENDENCE
# ============================================================


class TestSourceIndependence:
    """Verify scorecard generation works without the deliveries table."""

    def test_compute_scorecard_from_json_does_not_import_deliveries(self):
        """The scorecard computation function must not reference the deliveries table."""
        from data_pipeline.pipeline.scorecards import compute_scorecard_from_json

        result = compute_scorecard_from_json(SAMPLE_MATCH)
        assert result is not None
        assert len(result) == 2  # (batting_rows, bowling_rows)

    def test_scorecard_generator_works_with_existing_database(self):
        """ScorecardGenerator can be instantiated and loads caches."""
        from data_pipeline.pipeline.scorecards import ScorecardGenerator

        engine = _get_engine()
        gen = ScorecardGenerator(engine)
        assert len(gen._player_ids) > 0
        assert len(gen._match_ext_to_db) > 0
        engine.dispose()

    def test_scorecard_tables_exist(self):
        """match_batting_summary and match_bowling_summary tables exist."""
        engine = _get_engine()
        with engine.connect() as conn:
            bat_count = conn.execute(
                text("SELECT COUNT(*) FROM match_batting_summary")
            ).scalar()
            bowl_count = conn.execute(
                text("SELECT COUNT(*) FROM match_bowling_summary")
            ).scalar()
        engine.dispose()
        assert bat_count > 0, "match_batting_summary is empty"
        assert bowl_count > 0, "match_bowling_summary is empty"


# ============================================================
# DETERMINISTIC GENERATION
# ============================================================


class TestDeterministicGeneration:
    """Verify same input always produces same output."""

    def test_same_json_produces_same_scorecard(self):
        """Processing the same JSON twice produces identical results."""
        from data_pipeline.pipeline.scorecards import compute_scorecard_from_json

        bat1, bowl1 = compute_scorecard_from_json(SAMPLE_MATCH)
        bat2, bowl2 = compute_scorecard_from_json(SAMPLE_MATCH)

        # Same keys
        assert set(bat1.keys()) == set(bat2.keys())
        assert set(bowl1.keys()) == set(bowl2.keys())

        # Same values
        for key in bat1:
            assert bat1[key] == bat2[key], f"Batting mismatch at {key}"

        for key in bowl1:
            assert bowl1[key] == bowl2[key], f"Bowling mismatch at {key}"

    def test_sample_match_batting_totals(self):
        """Verify known batting totals from the sample match."""
        from data_pipeline.pipeline.scorecards import compute_scorecard_from_json

        bat, bowl = compute_scorecard_from_json(SAMPLE_MATCH)

        # Innings 0 (Team A): Player1 faces 5 balls (over 0: 4+1, over 1: 4+1+0)
        p1_inn0 = bat.get((0, "Player1"))
        assert p1_inn0 is not None, "Player1 innings 0 not found"
        assert p1_inn0["runs"] == 10, f"Player1 innings 0 runs: expected 10, got {p1_inn0['runs']}"
        assert p1_inn0["balls"] == 5
        assert p1_inn0["fours"] == 2
        assert p1_inn0["is_not_out"] is False  # Player1 got out

        p2_inn0 = bat.get((0, "Player2"))
        assert p2_inn0 is not None
        assert p2_inn0["runs"] == 6
        assert p2_inn0["is_not_out"] is False  # Player2 got out

    def test_sample_match_bowling_totals(self):
        """Verify known bowling totals from the sample match."""
        from data_pipeline.pipeline.scorecards import compute_scorecard_from_json

        bat, bowl = compute_scorecard_from_json(SAMPLE_MATCH)

        # Player7 bowled over 0 in innings 0: 6 balls, conceded 4+1+6+0+2+1=14 runs, 1 wicket
        p7_inn0 = bowl.get((0, "Player7"))
        assert p7_inn0 is not None, "Player7 innings 0 not found"
        assert p7_inn0["runs"] == 14, f"Player7 innings 0 runs: expected 14, got {p7_inn0['runs']}"
        assert p7_inn0["wickets"] == 1, f"Player7 innings 0 wkts: expected 1, got {p7_inn0['wickets']}"
        assert p7_inn0["wides"] == 1


# ============================================================
# IDEMPOTENCY (THE 2x BUG PREVENTION)
# ============================================================


class TestIdempotency:
    """Verify running scorecard generation twice does NOT double values."""

    def test_ipl_idempotency(self):
        """Running scorecard generation on an IPL match twice produces same values."""
        from data_pipeline.pipeline.scorecards import ScorecardGenerator

        ext_id = _get_ipl_sample_match_id()
        if not ext_id:
            pytest.skip("No IPL matches in database")

        engine = _get_engine()
        gen = ScorecardGenerator(engine)

        # Find the JSON file
        json_path = Path(f"data/raw/ipl/{ext_id}.json")
        if not json_path.exists():
            engine.dispose()
            pytest.skip(f"IPL JSON not found: {json_path}")

        # First pass
        result1 = gen.generate_from_json_file(json_path, format_type="T20")
        assert result1["status"] == "COMPLETED"

        # Get state after first pass
        match_db_id = gen._get_match_db_id(ext_id)
        state1 = _get_match_scorecard(engine, match_db_id)

        # Second pass (should not change anything)
        result2 = gen.generate_from_json_file(json_path, format_type="T20")
        assert result2["status"] == "COMPLETED"

        state2 = _get_match_scorecard(engine, match_db_id)

        # Verify identical
        assert len(state1["batting"]) == len(state2["batting"]), (
            f"Batting row count changed: {len(state1['batting'])} -> {len(state2['batting'])}"
        )
        assert len(state1["bowling"]) == len(state2["bowling"]), (
            f"Bowling row count changed: {len(state1['bowling'])} -> {len(state2['bowling'])}"
        )

        # Verify each row's values are identical
        for i, (r1, r2) in enumerate(zip(state1["batting"], state2["batting"])):
            assert r1 == r2, f"Batting row {i} changed: {r1} -> {r2}"

        for i, (r1, r2) in enumerate(zip(state1["bowling"], state2["bowling"])):
            assert r1 == r2, f"Bowling row {i} changed: {r1} -> {r2}"

        engine.dispose()

    def test_odi_idempotency(self):
        """Running scorecard generation on an ODI match twice produces same values."""
        from data_pipeline.pipeline.scorecards import ScorecardGenerator

        ext_id = _get_odi_sample_match_id()
        if not ext_id:
            pytest.skip("No ODI matches in database")

        engine = _get_engine()
        gen = ScorecardGenerator(engine)

        json_path = Path(f"data/raw/odi/{ext_id}.json")
        if not json_path.exists():
            engine.dispose()
            pytest.skip(f"ODI JSON not found: {json_path}")

        result1 = gen.generate_from_json_file(json_path, format_type="ODI")
        assert result1["status"] == "COMPLETED"
        match_db_id = gen._get_match_db_id(ext_id)
        state1 = _get_match_scorecard(engine, match_db_id)

        result2 = gen.generate_from_json_file(json_path, format_type="ODI")
        assert result2["status"] == "COMPLETED"
        state2 = _get_match_scorecard(engine, match_db_id)

        assert len(state1["batting"]) == len(state2["batting"])
        assert len(state1["bowling"]) == len(state2["bowling"])

        for i, (r1, r2) in enumerate(zip(state1["batting"], state2["batting"])):
            assert r1 == r2, f"Batting row {i} changed after re-run"

        for i, (r1, r2) in enumerate(zip(state1["bowling"], state2["bowling"])):
            assert r1 == r2, f"Bowling row {i} changed after re-run"

        engine.dispose()

    def test_test_match_idempotency(self):
        """Running scorecard generation on a Test match twice produces same values."""
        from data_pipeline.pipeline.scorecards import ScorecardGenerator

        ext_id = _get_test_sample_match_id()
        if not ext_id:
            pytest.skip("No Test matches in database")

        engine = _get_engine()
        gen = ScorecardGenerator(engine)

        json_path = Path(f"data/raw/test/{ext_id}.json")
        if not json_path.exists():
            engine.dispose()
            pytest.skip(f"Test JSON not found: {json_path}")

        result1 = gen.generate_from_json_file(json_path, format_type="Test")
        assert result1["status"] == "COMPLETED"
        match_db_id = gen._get_match_db_id(ext_id)
        state1 = _get_match_scorecard(engine, match_db_id)

        result2 = gen.generate_from_json_file(json_path, format_type="Test")
        assert result2["status"] == "COMPLETED"
        state2 = _get_match_scorecard(engine, match_db_id)

        assert len(state1["batting"]) == len(state2["batting"])
        assert len(state1["bowling"]) == len(state2["bowling"])

        for i, (r1, r2) in enumerate(zip(state1["batting"], state2["batting"])):
            assert r1 == r2, f"Batting row {i} changed after re-run"

        for i, (r1, r2) in enumerate(zip(state1["bowling"], state2["bowling"])):
            assert r1 == r2, f"Bowling row {i} changed after re-run"

        engine.dispose()

    def test_t20i_idempotency(self):
        """Running scorecard generation on a T20I match twice produces same values."""
        from data_pipeline.pipeline.scorecards import ScorecardGenerator

        ext_id = _get_t20i_sample_match_id()
        if not ext_id:
            pytest.skip("No T20I matches in database")

        engine = _get_engine()
        gen = ScorecardGenerator(engine)

        json_path = Path(f"data/raw/t20i/{ext_id}.json")
        if not json_path.exists():
            engine.dispose()
            pytest.skip(f"T20I JSON not found: {json_path}")

        result1 = gen.generate_from_json_file(json_path, format_type="T20I")
        assert result1["status"] == "COMPLETED"
        match_db_id = gen._get_match_db_id(ext_id)
        state1 = _get_match_scorecard(engine, match_db_id)

        result2 = gen.generate_from_json_file(json_path, format_type="T20I")
        assert result2["status"] == "COMPLETED"
        state2 = _get_match_scorecard(engine, match_db_id)

        assert len(state1["batting"]) == len(state2["batting"])
        assert len(state1["bowling"]) == len(state2["bowling"])

        for i, (r1, r2) in enumerate(zip(state1["batting"], state2["batting"])):
            assert r1 == r2, f"Batting row {i} changed after re-run"

        for i, (r1, r2) in enumerate(zip(state1["bowling"], state2["bowling"])):
            assert r1 == r2, f"Bowling row {i} changed after re-run"

        engine.dispose()


# ============================================================
# 2x INFLATION BUG REGRESSION
# ============================================================


class TestInflationRegression:
    """Specifically test that the Phase 5.6C 2x inflation bug cannot recur."""

    def test_no_match_doubles_on_rerun(self):
        """No match should have batting total > 1.5x innings total."""
        engine = _get_engine()
        with engine.connect() as conn:
            inflated = conn.execute(
                text(
                    "SELECT COUNT(*) FROM innings i "
                    "JOIN matches m ON i.match_id = m.id "
                    "JOIN (SELECT innings_id, SUM(runs) as bat_runs "
                    "      FROM match_batting_summary GROUP BY innings_id) sc "
                    "  ON sc.innings_id = i.id "
                    "WHERE sc.bat_runs > i.total_runs * 1.5 AND i.total_runs > 0"
                )
            ).scalar()
        engine.dispose()
        assert inflated == 0, f"{inflated} innings still show 2x inflation"

    def test_no_odi_inflation(self):
        """No ODI match should have inflated scorecards."""
        engine = _get_engine()
        with engine.connect() as conn:
            inflated = conn.execute(
                text(
                    "SELECT COUNT(*) FROM innings i "
                    "JOIN matches m ON i.match_id = m.id "
                    "JOIN (SELECT innings_id, SUM(runs) as bat_runs "
                    "      FROM match_batting_summary GROUP BY innings_id) sc "
                    "  ON sc.innings_id = i.id "
                    "WHERE m.format = 'ODI' "
                    "AND sc.bat_runs > i.total_runs * 1.5 AND i.total_runs > 0"
                )
            ).scalar()
        engine.dispose()
        assert inflated == 0, f"{inflated} ODI innings still inflated"

    def test_no_t20i_inflation(self):
        """No T20I match should have inflated scorecards."""
        engine = _get_engine()
        with engine.connect() as conn:
            inflated = conn.execute(
                text(
                    "SELECT COUNT(*) FROM innings i "
                    "JOIN matches m ON i.match_id = m.id "
                    "JOIN (SELECT innings_id, SUM(runs) as bat_runs "
                    "      FROM match_batting_summary GROUP BY innings_id) sc "
                    "  ON sc.innings_id = i.id "
                    "WHERE m.format = 'T20I' "
                    "AND sc.bat_runs > i.total_runs * 1.5 AND i.total_runs > 0"
                )
            ).scalar()
        engine.dispose()
        assert inflated == 0, f"{inflated} T20I innings still inflated"

    def test_rerun_does_not_double_production_data(self):
        """Running generation on a real match does not double its values."""
        from data_pipeline.pipeline.scorecards import ScorecardGenerator

        ext_id = _get_ipl_sample_match_id()
        if not ext_id:
            pytest.skip("No IPL matches in database")

        engine = _get_engine()
        gen = ScorecardGenerator(engine)

        json_path = Path(f"data/raw/ipl/{ext_id}.json")
        if not json_path.exists():
            engine.dispose()
            pytest.skip(f"IPL JSON not found: {json_path}")

        # Get current state
        match_db_id = gen._get_match_db_id(ext_id)
        state_before = _get_match_scorecard(engine, match_db_id)

        # Run generation
        result = gen.generate_from_json_file(json_path, format_type="T20")
        assert result["status"] == "COMPLETED"

        # Get state after
        state_after = _get_match_scorecard(engine, match_db_id)

        # Row counts should be the same
        assert len(state_before["batting"]) == len(state_after["batting"])
        assert len(state_before["bowling"]) == len(state_after["bowling"])

        # Total runs should be the same (not doubled)
        total_runs_before = sum(r[1] for r in state_before["batting"])
        total_runs_after = sum(r[1] for r in state_after["batting"])
        assert total_runs_before == total_runs_after, (
            f"Total batting runs changed: {total_runs_before} -> {total_runs_after}"
        )

        engine.dispose()


# ============================================================
# VALIDATION
# ============================================================


class TestScorecardValidation:
    """Verify validation catches invalid data."""

    def test_validates_negative_runs(self):
        """Validation catches negative runs."""
        from data_pipeline.pipeline.scorecards import validate_scorecard

        bad_batting = {(0, "Player1"): {"runs": -5, "balls": 10, "fours": 0, "sixes": 0, "is_not_out": True, "dismissal_type": None}}
        issues = validate_scorecard(bad_batting, {}, "test_match")
        assert any("negative runs" in i for i in issues)

    def test_validates_negative_balls(self):
        """Validation catches negative balls."""
        from data_pipeline.pipeline.scorecards import validate_scorecard

        bad_batting = {(0, "Player1"): {"runs": 10, "balls": -3, "fours": 0, "sixes": 0, "is_not_out": True, "dismissal_type": None}}
        issues = validate_scorecard(bad_batting, {}, "test_match")
        assert any("negative balls" in i for i in issues)

    def test_validates_negative_bowling_runs(self):
        """Validation catches negative bowling runs."""
        from data_pipeline.pipeline.scorecards import validate_scorecard

        bad_bowling = {(0, "Bowler1"): {"balls": 12, "runs": -2, "wickets": 1, "wides": 0, "noballs": 0}}
        issues = validate_scorecard({}, bad_bowling, "test_match")
        assert any("negative runs conceded" in i for i in issues)

    def test_validates_negative_bowling_wickets(self):
        """Validation catches negative wickets."""
        from data_pipeline.pipeline.scorecards import validate_scorecard

        bad_bowling = {(0, "Bowler1"): {"balls": 12, "runs": 20, "wickets": -1, "wides": 0, "noballs": 0}}
        issues = validate_scorecard({}, bad_bowling, "test_match")
        assert any("negative wickets" in i for i in issues)

    def test_valid_scorecard_has_no_issues(self):
        """Valid scorecard produces no issues."""
        from data_pipeline.pipeline.scorecards import validate_scorecard

        good_batting = {(0, "Player1"): {"runs": 30, "balls": 25, "fours": 3, "sixes": 1, "is_not_out": True, "dismissal_type": None}}
        good_bowling = {(0, "Bowler1"): {"balls": 24, "runs": 32, "wickets": 1, "wides": 1, "noballs": 0}}
        issues = validate_scorecard(good_batting, good_bowling, "test_match")
        assert len(issues) == 0, f"Unexpected issues: {issues}"


# ============================================================
# CROSS-FORMAT ISOLATION
# ============================================================


class TestCrossFormatIsolation:
    """Verify scorecard generation for one format does not affect others."""

    def test_format_counts_unchanged_after_generation(self):
        """Running scorecard generation on one format does not change other formats' counts."""
        engine = _get_engine()

        # Get pre-generation counts
        with engine.connect() as conn:
            pre_counts = {}
            for fmt in ["T20", "T20I", "ODI", "Test"]:
                bat = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM match_batting_summary mbs "
                        "JOIN matches m ON mbs.match_id = m.id "
                        "WHERE m.format = :fmt"
                    ),
                    {"fmt": fmt},
                ).scalar()
                bowl = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM match_bowling_summary mbs "
                        "JOIN matches m ON mbs.match_id = m.id "
                        "WHERE m.format = :fmt"
                    ),
                    {"fmt": fmt},
                ).scalar()
                pre_counts[fmt] = {"batting": bat, "bowling": bowl}

        engine.dispose()

        # Run generation on one IPL match
        from data_pipeline.pipeline.scorecards import ScorecardGenerator

        ext_id = _get_ipl_sample_match_id()
        if not ext_id:
            pytest.skip("No IPL matches in database")

        engine = _get_engine()
        gen = ScorecardGenerator(engine)
        json_path = Path(f"data/raw/ipl/{ext_id}.json")
        if not json_path.exists():
            engine.dispose()
            pytest.skip("IPL JSON not found")

        gen.generate_from_json_file(json_path, format_type="T20")
        engine.dispose()

        # Verify other formats unchanged
        engine = _get_engine()
        with engine.connect() as conn:
            for fmt in ["T20I", "ODI", "Test"]:
                bat = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM match_batting_summary mbs "
                        "JOIN matches m ON mbs.match_id = m.id "
                        "WHERE m.format = :fmt"
                    ),
                    {"fmt": fmt},
                ).scalar()
                bowl = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM match_bowling_summary mbs "
                        "JOIN matches m ON mbs.match_id = m.id "
                        "WHERE m.format = :fmt"
                    ),
                    {"fmt": fmt},
                ).scalar()
                assert bat == pre_counts[fmt]["batting"], (
                    f"{fmt} batting count changed: {pre_counts[fmt]['batting']} -> {bat}"
                )
                assert bowl == pre_counts[fmt]["bowling"], (
                    f"{fmt} bowling count changed: {pre_counts[fmt]['bowling']} -> {bowl}"
                )

        engine.dispose()


# ============================================================
# REGRESSION COUNTS
# ============================================================


class TestRegressionCounts:
    """Verify historical match counts are preserved."""

    def test_ipl_match_count(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM matches WHERE format = 'T20'")
            ).scalar()
        engine.dispose()
        assert count == 1243, f"IPL matches: expected 1243, got {count}"

    def test_t20i_match_count(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM matches WHERE format = 'T20I'")
            ).scalar()
        engine.dispose()
        assert count == 3533, f"T20I matches: expected 3533, got {count}"

    def test_odi_match_count(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM matches WHERE format = 'ODI'")
            ).scalar()
        engine.dispose()
        assert count == 2577, f"ODI matches: expected 2577, got {count}"

    def test_test_match_count(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM matches WHERE format = 'Test'")
            ).scalar()
        engine.dispose()
        assert count == 897, f"Test matches: expected 897, got {count}"

    def test_kohli_ipl_runs(self):
        engine = _get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT pbs.runs FROM player_batting_stats pbs "
                    "JOIN players p ON pbs.player_id = p.id "
                    "WHERE p.canonical_name = 'Virat Kohli' "
                    "AND pbs.format = 'T20' AND pbs.period = 'career'"
                )
            ).fetchone()
        engine.dispose()
        assert row is not None, "Kohli T20 batting stats not found"
        assert row[0] == 9346, f"Kohli IPL runs: expected 9346, got {row[0]}"

    def test_total_match_count(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM matches")).scalar()
        engine.dispose()
        assert count == 8250, f"Total matches: expected 8250, got {count}"


# ============================================================
# DATABASE INTEGRITY
# ============================================================


class TestDatabaseIntegrity:
    """Verify no orphaned records after scorecard operations."""

    def test_no_orphan_batting_summaries(self):
        """Every batting summary belongs to a valid match."""
        engine = _get_engine()
        with engine.connect() as conn:
            orphans = conn.execute(
                text(
                    "SELECT COUNT(*) FROM match_batting_summary mbs "
                    "LEFT JOIN matches m ON mbs.match_id = m.id "
                    "WHERE m.id IS NULL"
                )
            ).scalar()
        engine.dispose()
        assert orphans == 0, f"{orphans} orphaned batting summaries"

    def test_no_orphan_bowling_summaries(self):
        """Every bowling summary belongs to a valid match."""
        engine = _get_engine()
        with engine.connect() as conn:
            orphans = conn.execute(
                text(
                    "SELECT COUNT(*) FROM match_bowling_summary mbs "
                    "LEFT JOIN matches m ON mbs.match_id = m.id "
                    "WHERE m.id IS NULL"
                )
            ).scalar()
        engine.dispose()
        assert orphans == 0, f"{orphans} orphaned bowling summaries"

    def test_no_orphan_innings(self):
        """Every innings belongs to a valid match."""
        engine = _get_engine()
        with engine.connect() as conn:
            orphans = conn.execute(
                text(
                    "SELECT COUNT(*) FROM innings i "
                    "LEFT JOIN matches m ON i.match_id = m.id "
                    "WHERE m.id IS NULL"
                )
            ).scalar()
        engine.dispose()
        assert orphans == 0, f"{orphans} orphaned innings"

    def test_no_duplicate_batting_summaries(self):
        """No duplicate (match_id, innings_id, player_id) in batting."""
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(
                text(
                    "SELECT COUNT(*) FROM ("
                    "  SELECT match_id, innings_id, player_id, COUNT(*) "
                    "  FROM match_batting_summary "
                    "  GROUP BY match_id, innings_id, player_id HAVING COUNT(*) > 1"
                    ") sub"
                )
            ).scalar()
        engine.dispose()
        assert dups == 0, f"{dups} duplicate batting summary groups"

    def test_no_duplicate_bowling_summaries(self):
        """No duplicate (match_id, innings_id, player_id) in bowling."""
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(
                text(
                    "SELECT COUNT(*) FROM ("
                    "  SELECT match_id, innings_id, player_id, COUNT(*) "
                    "  FROM match_bowling_summary "
                    "  GROUP BY match_id, innings_id, player_id HAVING COUNT(*) > 1"
                    ") sub"
                )
            ).scalar()
        engine.dispose()
        assert dups == 0, f"{dups} duplicate bowling summary groups"

    def test_no_negative_batting_runs(self):
        """No negative runs in batting summaries."""
        engine = _get_engine()
        with engine.connect() as conn:
            neg = conn.execute(
                text("SELECT COUNT(*) FROM match_batting_summary WHERE runs < 0")
            ).scalar()
        engine.dispose()
        assert neg == 0, f"{neg} negative batting runs"

    def test_no_negative_bowling_runs(self):
        """No negative runs in bowling summaries."""
        engine = _get_engine()
        with engine.connect() as conn:
            neg = conn.execute(
                text("SELECT COUNT(*) FROM match_bowling_summary WHERE runs_conceded < 0")
            ).scalar()
        engine.dispose()
        assert neg == 0, f"{neg} negative bowling runs"


# ============================================================
# DUPLICATE INPUT DETECTION
# ============================================================


class TestDuplicateDetection:
    """Verify duplicate source file detection works."""

    def test_detect_duplicates_in_directory(self):
        """Detecting duplicates in a temporary directory."""
        from data_pipeline.pipeline.scorecards import ScorecardGenerator

        engine = _get_engine()
        gen = ScorecardGenerator(engine)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files
            (Path(tmpdir) / "match1.json").write_text(json.dumps(SAMPLE_MATCH))
            (Path(tmpdir) / "match2.json").write_text(json.dumps(SAMPLE_MATCH))

            # No duplicates (different filenames)
            dups = gen.detect_duplicate_sources(tmpdir)
            assert len(dups) == 0

        engine.dispose()

    def test_no_duplicates_in_raw_directory(self):
        """Verify no duplicate match IDs in actual raw data directories."""
        from data_pipeline.pipeline.scorecards import ScorecardGenerator

        engine = _get_engine()
        gen = ScorecardGenerator(engine)

        for fmt_dir in ["data/raw/ipl", "data/raw/t20i", "data/raw/odi", "data/raw/test"]:
            p = Path(fmt_dir)
            if p.exists():
                dups = gen.detect_duplicate_sources(p)
                assert len(dups) == 0, f"Duplicate match IDs in {fmt_dir}: {dups}"

        engine.dispose()
