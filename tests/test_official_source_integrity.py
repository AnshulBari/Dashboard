"""Regression checks for the official-only historical serving corpus."""

from __future__ import annotations

import sqlite3
from pathlib import Path


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
