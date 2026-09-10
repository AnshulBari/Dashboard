"""Backfill the real last appearance date used by recent-form leaderboards."""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline.pipeline.player_identity import canonical_player_name


DB_PATH = ROOT / "data" / "cricket_intelligence.db"
RAW_ROOT = ROOT / "data" / "raw"
FORMAT_DIRS = {"ipl": "T20", "t20i": "T20I", "odi": "ODI", "test": "Test"}


def main() -> None:
    cutoff = (date.today() - timedelta(days=548)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(player_form)")}
        if "last_match_date" not in columns:
            conn.execute("ALTER TABLE player_form ADD COLUMN last_match_date DATE")

        player_ids = {
            str(name).strip().casefold(): player_id
            for player_id, name in conn.execute("SELECT id, canonical_name FROM players")
            if name
        }
        aliases = {
            str(alias).strip().casefold(): player_id
            for alias, player_id in conn.execute(
                "SELECT name_variant, player_id FROM player_name_mappings"
            )
            if alias
        }

        latest: dict[tuple[str, str], str] = {}
        recent = defaultdict(lambda: {
            "matches": 0, "batting_innings": 0, "runs": 0, "balls_faced": 0,
            "bowling_innings": 0, "wickets": 0, "balls_bowled": 0,
            "runs_conceded": 0, "last_match_date": "",
        })
        files_read = 0
        for directory, match_format in FORMAT_DIRS.items():
            for path in (RAW_ROOT / directory).glob("*.json"):
                # Official Cricsheet match files use numeric identifiers.
                # Non-numeric files are local test fixtures and must never
                # influence public recency or Impact Score calculations.
                if not path.stem.isdigit():
                    continue
                try:
                    with path.open(encoding="utf-8") as handle:
                        match = json.load(handle)
                    info = match.get("info", {})
                except (OSError, json.JSONDecodeError):
                    continue

                dates = info.get("dates") or []
                if not dates:
                    continue
                match_date = str(max(dates))
                players = {
                    name
                    for squad in (info.get("players") or {}).values()
                    for name in squad
                    if isinstance(name, str) and name.strip()
                }
                for source_name in players:
                    canonical = canonical_player_name(source_name)
                    player_id = player_ids.get(canonical.casefold()) or aliases.get(
                        source_name.strip().casefold()
                    )
                    if not player_id:
                        continue
                    key = (player_id, match_format)
                    if match_date > latest.get(key, ""):
                        latest[key] = match_date

                if match_date >= cutoff:
                    source_ids = {}
                    for source_name in players:
                        canonical = canonical_player_name(source_name)
                        player_id = player_ids.get(canonical.casefold()) or aliases.get(
                            source_name.strip().casefold()
                        )
                        if player_id:
                            source_ids[source_name] = player_id
                    for player_id in set(source_ids.values()):
                        item = recent[(player_id, match_format)]
                        item["matches"] += 1
                        item["last_match_date"] = max(item["last_match_date"], match_date)

                    for innings in match.get("innings", []):
                        batters, bowlers = set(), set()
                        for over in innings.get("overs", []):
                            for delivery in over.get("deliveries", []):
                                batter_id = source_ids.get(delivery.get("batter", ""))
                                bowler_id = source_ids.get(delivery.get("bowler", ""))
                                runs = delivery.get("runs") or {}
                                extras = delivery.get("extras") or {}
                                if batter_id:
                                    batters.add(batter_id)
                                    item = recent[(batter_id, match_format)]
                                    item["runs"] += int(runs.get("batter", 0) or 0)
                                    if "wides" not in extras:
                                        item["balls_faced"] += 1
                                if bowler_id:
                                    bowlers.add(bowler_id)
                                    item = recent[(bowler_id, match_format)]
                                    if "wides" not in extras and "noballs" not in extras:
                                        item["balls_bowled"] += 1
                                    item["runs_conceded"] += int(runs.get("batter", 0) or 0)
                                    item["runs_conceded"] += int(extras.get("wides", 0) or 0)
                                    item["runs_conceded"] += int(extras.get("noballs", 0) or 0)
                                    for wicket in delivery.get("wickets", []):
                                        if wicket.get("kind", "").lower() not in {
                                            "run out", "retired hurt", "retired out",
                                            "obstructing the field", "timed out",
                                        }:
                                            item["wickets"] += 1
                        for player_id in batters:
                            recent[(player_id, match_format)]["batting_innings"] += 1
                        for player_id in bowlers:
                            recent[(player_id, match_format)]["bowling_innings"] += 1
                files_read += 1

        updated = 0
        for (player_id, match_format), match_date in latest.items():
            cursor = conn.execute(
                "UPDATE player_form SET last_match_date = ? "
                "WHERE player_id = ? AND format = ?",
                (match_date, player_id, match_format),
            )
            updated += cursor.rowcount

        conn.execute("DELETE FROM player_recent_stats")
        conn.executemany(
            """INSERT INTO player_recent_stats
               (player_id, format, window_start, last_match_date, matches,
                batting_innings, runs, balls_faced, bowling_innings, wickets,
                balls_bowled, runs_conceded)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    player_id, match_format, cutoff, values["last_match_date"],
                    values["matches"], values["batting_innings"], values["runs"],
                    values["balls_faced"], values["bowling_innings"], values["wickets"],
                    values["balls_bowled"], values["runs_conceded"],
                )
                for (player_id, match_format), values in recent.items()
            ],
        )
        conn.commit()

    print(
        f"Backfilled {updated} recency dates and {len(recent)} recent-stat rows "
        f"from {files_read} matches"
    )


if __name__ == "__main__":
    main()
