"""Build compact per-player statistics for every searchable competition season."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline.pipeline.scorecards import compute_scorecard_from_json
from rebuild_official_player_stats import DEFAULT_DB, FORMAT_DIRS, PlayerResolver


def _empty() -> dict:
    return {
        "match_ids": set(), "batting_innings": 0, "not_outs": 0,
        "runs": 0, "balls_faced": 0, "fours": 0, "sixes": 0,
        "highest_score": None, "fifties": 0, "hundreds": 0,
        "bowling_innings": 0, "balls_bowled": 0, "runs_conceded": 0,
        "wickets": 0, "maidens": 0, "best_wickets": None,
        "best_runs": None,
    }


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS season_player_stats (
            season_id TEXT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
            player_id TEXT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
            matches INTEGER DEFAULT 0,
            batting_innings INTEGER DEFAULT 0,
            not_outs INTEGER DEFAULT 0,
            runs INTEGER DEFAULT 0,
            balls_faced INTEGER DEFAULT 0,
            fours INTEGER DEFAULT 0,
            sixes INTEGER DEFAULT 0,
            highest_score INTEGER,
            fifties INTEGER DEFAULT 0,
            hundreds INTEGER DEFAULT 0,
            bowling_innings INTEGER DEFAULT 0,
            balls_bowled INTEGER DEFAULT 0,
            runs_conceded INTEGER DEFAULT 0,
            wickets INTEGER DEFAULT 0,
            maidens INTEGER DEFAULT 0,
            best_wickets INTEGER,
            best_runs INTEGER,
            PRIMARY KEY (season_id, player_id)
        );
        CREATE INDEX IF NOT EXISTS idx_sps_season_runs
            ON season_player_stats(season_id, runs DESC);
        CREATE INDEX IF NOT EXISTS idx_sps_season_wickets
            ON season_player_stats(season_id, wickets DESC);
    """)


def _ensure_match_seasons(conn: sqlite3.Connection) -> int:
    """Backfill edition rows for legacy competition-linked matches (notably IPL)."""
    groups = conn.execute("""
        SELECT competition_id, SUBSTR(match_date, 1, 4) AS season_name,
               MIN(match_date), MAX(match_date), COUNT(*)
        FROM matches
        WHERE competition_id IS NOT NULL AND season_id IS NULL
        GROUP BY competition_id, SUBSTR(match_date, 1, 4)
    """).fetchall()
    updated = 0
    for competition_id, season_name, start_date, end_date, matches in groups:
        existing = conn.execute(
            "SELECT id FROM seasons WHERE competition_id = ? AND name = ?",
            (competition_id, season_name),
        ).fetchone()
        season_id = existing[0] if existing else str(uuid.uuid4())
        if not existing:
            conn.execute(
                """INSERT INTO seasons
                   (id, competition_id, name, start_date, end_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (season_id, competition_id, season_name, start_date, end_date),
            )
        cursor = conn.execute(
            """UPDATE matches SET season_id = ?
               WHERE competition_id = ? AND season_id IS NULL
                 AND SUBSTR(match_date, 1, 4) = ?""",
            (season_id, competition_id, season_name),
        )
        updated += cursor.rowcount if cursor.rowcount >= 0 else int(matches)
    return updated


def build(conn: sqlite3.Connection, formats: list[str]) -> tuple[list[tuple], dict[str, int]]:
    resolver = PlayerResolver(conn)
    match_seasons = {
        (str(external_id), match_format): (str(match_id), str(season_id))
        for match_id, external_id, match_format, season_id in conn.execute(
            "SELECT id, external_id, format, season_id FROM matches WHERE season_id IS NOT NULL"
        )
    }
    aggregates: dict[tuple[str, str], dict] = defaultdict(_empty)
    scanned = matched = 0
    unresolved: set[str] = set()

    for match_format in formats:
        paths = sorted(
            path for path in FORMAT_DIRS[match_format].glob("*.json")
            if path.stem.isdigit()
        )
        for path in paths:
            scanned += 1
            identity = match_seasons.get((path.stem, match_format))
            if not identity:
                continue
            match_id, season_id = identity
            matched += 1
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
            info = payload.get("info") or {}
            source_names = {
                name for squad in (info.get("players") or {}).values()
                for name in squad if isinstance(name, str) and name.strip()
            }
            resolved = {name: resolver.get(name) for name in source_names}
            for name, player_id in resolved.items():
                if player_id:
                    aggregates[(season_id, player_id)]["match_ids"].add(match_id)
                else:
                    unresolved.add(name)

            batting, bowling = compute_scorecard_from_json(payload)
            for (_, name), values in batting.items():
                player_id = resolved.get(name) or resolver.get(name)
                if not player_id:
                    unresolved.add(name)
                    continue
                item = aggregates[(season_id, player_id)]
                item["match_ids"].add(match_id)
                item["batting_innings"] += 1
                item["not_outs"] += int(bool(values["is_not_out"]))
                score = int(values["runs"])
                item["runs"] += score
                item["balls_faced"] += int(values["balls"])
                item["fours"] += int(values["fours"])
                item["sixes"] += int(values["sixes"])
                item["highest_score"] = score if item["highest_score"] is None else max(item["highest_score"], score)
                item["fifties"] += int(50 <= score < 100)
                item["hundreds"] += int(score >= 100)

            for (_, name), values in bowling.items():
                player_id = resolved.get(name) or resolver.get(name)
                if not player_id:
                    unresolved.add(name)
                    continue
                item = aggregates[(season_id, player_id)]
                item["match_ids"].add(match_id)
                item["bowling_innings"] += 1
                item["balls_bowled"] += int(values["balls"])
                item["runs_conceded"] += int(values["runs"])
                item["wickets"] += int(values["wickets"])
                item["maidens"] += int(values["maidens"])
                wickets, runs = int(values["wickets"]), int(values["runs"])
                previous = (item["best_wickets"], item["best_runs"])
                if previous[0] is None or wickets > previous[0] or (wickets == previous[0] and runs < previous[1]):
                    item["best_wickets"], item["best_runs"] = wickets, runs

    rows = [
        (
            season_id, player_id, len(item["match_ids"]),
            item["batting_innings"], item["not_outs"], item["runs"],
            item["balls_faced"], item["fours"], item["sixes"],
            item["highest_score"], item["fifties"], item["hundreds"],
            item["bowling_innings"], item["balls_bowled"],
            item["runs_conceded"], item["wickets"], item["maidens"],
            item["best_wickets"], item["best_runs"],
        )
        for (season_id, player_id), item in aggregates.items()
    ]
    return rows, {
        "source_files": scanned, "season_matches": matched,
        "rows": len(rows), "unresolved_players": len(unresolved),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--formats", nargs="+", choices=sorted(FORMAT_DIRS), default=list(FORMAT_DIRS))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        backfilled = _ensure_match_seasons(conn)
        rows, report = build(conn, args.formats)
        report["season_links_backfilled"] = backfilled
        print("Tournament aggregate rebuild: " + ", ".join(f"{key}={value:,}" for key, value in report.items()))
        if args.dry_run:
            return
        _ensure_schema(conn)
        conn.execute("DELETE FROM season_player_stats")
        conn.executemany("""
            INSERT INTO season_player_stats (
                season_id, player_id, matches, batting_innings, not_outs,
                runs, balls_faced, fours, sixes, highest_score, fifties,
                hundreds, bowling_innings, balls_bowled, runs_conceded,
                wickets, maidens, best_wickets, best_runs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        print(f"Committed {len(rows):,} season-player rows to {args.db}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
