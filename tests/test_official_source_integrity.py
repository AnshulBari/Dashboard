"""Regression checks for the official-only historical serving corpus."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine

from backend.services.analytics import match_detail


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "cricket_intelligence.db"
PRODUCTION_RAW_DIRS = ("ipl", "t20i", "odi", "test")


def test_production_raw_directories_only_contain_cricsheet_ids():
    unexpected = []
    for directory in PRODUCTION_RAW_DIRS:
        unexpected.extend(
            str(path.relative_to(ROOT))
            for path in (ROOT / "data" / "raw" / directory).glob("*.json")
            if not path.stem.isdigit()
        )
    assert unexpected == [], f"Validation fixtures leaked into production: {unexpected}"


def test_serving_database_has_official_match_counts_only():
    with sqlite3.connect(DB_PATH) as conn:
        counts = dict(conn.execute("SELECT format, COUNT(*) FROM matches GROUP BY format"))
        assert counts == {"ODI": 2569, "T20": 1243, "T20I": 3528, "Test": 892}
        external_ids = [row[0] for row in conn.execute("SELECT external_id FROM matches")]
    assert all(str(external_id).isdigit() for external_id in external_ids)


def test_career_count_invariants_hold_for_every_player_and_format():
    with sqlite3.connect(DB_PATH) as conn:
        invalid_batting = conn.execute(
            """SELECT COUNT(*) FROM player_batting_stats
               WHERE matches < 0 OR innings < 0 OR not_outs < 0 OR runs < 0
                  OR balls_faced < 0 OR not_outs > innings OR innings > matches * 2"""
        ).fetchone()[0]
        invalid_bowling = conn.execute(
            """SELECT COUNT(*) FROM player_bowling_stats
               WHERE matches < 0 OR innings < 0 OR wickets < 0
                  OR balls_bowled < 0 OR runs_conceded < 0"""
        ).fetchone()[0]
    assert invalid_batting == 0
    assert invalid_bowling == 0


def test_virat_kohli_test_career_matches_authoritative_scorecard():
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """SELECT s.matches, s.innings, s.not_outs, s.runs,
                      s.highest_score, s.batting_average, s.balls_faced,
                      s.strike_rate, s.fours, s.sixes, s.fifties, s.hundreds
               FROM player_batting_stats s
               JOIN players p ON p.id = s.player_id
               WHERE lower(p.canonical_name) = 'virat kohli'
                 AND s.format = 'Test' AND s.period = 'career'"""
        ).fetchone()
    assert row == (123, 210, 13, 9230, 254, 46.85, 16608, 55.58, 1027, 30, 31, 30)


def test_competition_matches_have_editions_and_valid_player_aggregates():
    with sqlite3.connect(DB_PATH) as conn:
        missing_editions = conn.execute(
            """SELECT COUNT(*) FROM matches
               WHERE competition_id IS NOT NULL AND season_id IS NULL"""
        ).fetchone()[0]
        invalid_stats = conn.execute(
            """SELECT COUNT(*) FROM season_player_stats
               WHERE matches < 0 OR batting_innings < 0 OR not_outs < 0
                  OR not_outs > batting_innings OR runs < 0 OR balls_faced < 0
                  OR bowling_innings < 0 OR wickets < 0 OR balls_bowled < 0
                  OR runs_conceded < 0"""
        ).fetchone()[0]
        cwc = conn.execute(
            """SELECT COUNT(DISTINCT m.id), COUNT(DISTINCT sp.player_id)
               FROM competitions c
               JOIN seasons s ON s.competition_id = c.id
               LEFT JOIN matches m ON m.season_id = s.id
               LEFT JOIN season_player_stats sp ON sp.season_id = s.id
               WHERE c.name = 'ICC Cricket World Cup' AND s.name = '2023'"""
        ).fetchone()

    assert missing_editions == 0
    assert invalid_stats == 0
    assert cwc[0] == 39
    assert cwc[1] > 0


def test_match_scorecards_cover_every_match_and_use_the_innings_teams():
    with sqlite3.connect(DB_PATH) as conn:
        coverage = conn.execute(
            """SELECT
                   (SELECT COUNT(DISTINCT match_id) FROM match_batting_summary),
                   (SELECT COUNT(DISTINCT match_id) FROM match_bowling_summary),
                   (SELECT COUNT(*) FROM matches)"""
        ).fetchone()
        mismatches = conn.execute(
            """SELECT
                 (SELECT COUNT(*) FROM match_batting_summary b
                  JOIN innings i ON i.id = b.innings_id
                  WHERE b.match_id != i.match_id
                     OR b.batting_team_id != i.batting_team_id),
                 (SELECT COUNT(*) FROM match_bowling_summary b
                  JOIN innings i ON i.id = b.innings_id
                  WHERE b.match_id != i.match_id
                     OR b.bowling_team_id != i.bowling_team_id)"""
        ).fetchone()
        missing = conn.execute(
            """SELECT
                 (SELECT COUNT(*) FROM innings i LEFT JOIN match_batting_summary b
                  ON b.innings_id = i.id WHERE b.id IS NULL),
                 (SELECT COUNT(*) FROM innings i LEFT JOIN match_bowling_summary b
                  ON b.innings_id = i.id WHERE b.id IS NULL)"""
        ).fetchone()

    assert coverage == (8232, 8232, 8232)
    assert mismatches == (0, 0)
    assert missing == (0, 0)


def test_world_cup_final_scorecard_contract_is_innings_and_team_correct():
    engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}")
    with engine.connect() as conn:
        match_id = conn.exec_driver_sql(
            "SELECT id FROM matches WHERE external_id = '1384439'"
        ).scalar_one()
        card = match_detail(conn, match_id)

    assert card["competition"] == "ICC Cricket World Cup"
    assert card["season"] == "2023"
    assert card["result"] == "Australia won by 6 wickets"
    assert [
        (item["team"], item["runs"], item["wickets"], item["overs"], item["extras"])
        for item in card["innings"]
    ] == [
        ("India", 240, 10, 50.0, 12),
        ("Australia", 241, 4, 43.0, 18),
    ]
    assert card["innings"][0]["batting"][0]["player_name"] == "Rohit Sharma"
    assert card["innings"][1]["batting"][0]["player_name"] == "David Warner"
    assert card["innings"][1]["batting"][1]["runs"] == 137
