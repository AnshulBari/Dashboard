"""Rebuild player career aggregates from authoritative Cricsheet match files.

Only numeric Cricsheet IDs are accepted. Local reconstructed fixtures use
descriptive filenames and are intentionally excluded from public statistics.
The rebuild streams one match at a time, so it never restores the multi-million
row deliveries table to the serving database.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sqlite3
import statistics
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline.pipeline.format_config import get_format_rules
from data_pipeline.pipeline.scorecards import (
    NON_BOWLER_DISMISSALS,
    compute_scorecard_from_json,
)


DEFAULT_DB = ROOT / "data" / "cricket_intelligence.db"
FORMAT_DIRS = {
    "T20": ROOT / "data" / "raw" / "ipl",
    "T20I": ROOT / "data" / "raw" / "t20i",
    "ODI": ROOT / "data" / "raw" / "odi",
    "Test": ROOT / "data" / "raw" / "test",
}


def _key(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


class PlayerResolver:
    def __init__(self, conn: sqlite3.Connection):
        candidates: dict[str, set[str]] = defaultdict(set)
        for player_id, canonical, full_name in conn.execute(
            "SELECT id, canonical_name, full_name FROM players"
        ):
            for name in (canonical, full_name):
                if name:
                    candidates[_key(name)].add(player_id)
        aliases: dict[str, set[str]] = defaultdict(set)
        for variant, player_id in conn.execute(
            "SELECT name_variant, player_id FROM player_name_mappings"
        ):
            if variant:
                aliases[_key(variant)].add(player_id)
        self._ids = {
            name: next(iter(ids)) for name, ids in candidates.items() if len(ids) == 1
        }
        # An explicit source-name mapping is more authoritative than a stale
        # duplicate player row left behind by an earlier ingestion pass.
        self._ids.update({
            name: next(iter(ids)) for name, ids in aliases.items() if len(ids) == 1
        })
        self.ambiguous = {
            name for name, ids in aliases.items() if len(ids) > 1
        } | {
            name for name, ids in candidates.items()
            if len(ids) > 1 and name not in self._ids
        }

    def get(self, name: str) -> str | None:
        return self._ids.get(_key(name))


def _bat_row() -> dict:
    return {
        "matches": 0, "innings": 0, "not_outs": 0, "runs": 0,
        "balls": 0, "fours": 0, "sixes": 0, "dots": 0,
        "highest": None, "fifties": 0, "hundreds": 0,
        "powerplay_runs": 0, "powerplay_balls": 0,
        "middle_runs": 0, "middle_balls": 0,
        "death_runs": 0, "death_balls": 0,
        "chasing_runs": 0, "chasing_balls": 0,
        "first_runs": 0, "first_balls": 0, "scores": [],
    }


def _bowl_row() -> dict:
    return {
        "match_ids": set(), "innings": 0, "balls": 0, "runs": 0,
        "wickets": 0, "maidens": 0, "dots": 0, "boundaries": 0,
        "best": None, "four_wickets": 0, "five_wickets": 0,
        "powerplay_balls": 0, "powerplay_runs": 0, "powerplay_wickets": 0,
        "middle_balls": 0, "middle_runs": 0, "middle_wickets": 0,
        "death_balls": 0, "death_runs": 0, "death_wickets": 0,
    }


def _matchup_row() -> dict:
    return {"balls": 0, "runs": 0, "wickets": 0, "dots": 0, "boundaries": 0, "sixes": 0}


def _safe_rate(numerator: float, denominator: float, multiplier: float = 1.0):
    return round(numerator * multiplier / denominator, 2) if denominator else None


def _overs(balls: int) -> float:
    return balls // 6 + (balls % 6) / 10.0


def scan(conn: sqlite3.Connection, formats: list[str]):
    resolver = PlayerResolver(conn)
    batting = defaultdict(_bat_row)
    bowling = defaultdict(_bowl_row)
    matchups = defaultdict(_matchup_row)
    unresolved: set[str] = set()
    file_counts: dict[str, int] = {}

    for match_format in formats:
        paths = sorted(
            path for path in FORMAT_DIRS[match_format].glob("*.json")
            if path.stem.isdigit()
        )
        file_counts[match_format] = len(paths)
        rules = get_format_rules(match_format)

        for index, path in enumerate(paths, 1):
            with path.open(encoding="utf-8") as handle:
                match = json.load(handle)
            info = match.get("info") or {}
            source_names = {
                name for squad in (info.get("players") or {}).values()
                for name in squad if isinstance(name, str) and name.strip()
            }
            resolved = {name: resolver.get(name) for name in source_names}

            # Official match appearances include DNB players in the named XI.
            for player_id in set(filter(None, resolved.values())):
                batting[(player_id, match_format)]["matches"] += 1

            batting_rows, bowling_rows = compute_scorecard_from_json(match)
            for (innings_index, name), values in batting_rows.items():
                player_id = resolved.get(name) or resolver.get(name)
                if not player_id:
                    unresolved.add(name)
                    continue
                item = batting[(player_id, match_format)]
                item["innings"] += 1
                item["not_outs"] += int(values["is_not_out"])
                for field in ("runs", "balls", "fours", "sixes"):
                    item[field] += int(values[field])
                score = int(values["runs"])
                item["scores"].append(score)
                item["highest"] = score if item["highest"] is None else max(item["highest"], score)
                item["fifties"] += int(50 <= score < 100)
                item["hundreds"] += int(score >= 100)
                situation = "first" if innings_index == 0 else "chasing" if innings_index == 1 else None
                if situation:
                    item[f"{situation}_runs"] += score
                    item[f"{situation}_balls"] += int(values["balls"])

            for (innings_index, name), values in bowling_rows.items():
                player_id = resolved.get(name) or resolver.get(name)
                if not player_id:
                    unresolved.add(name)
                    continue
                item = bowling[(player_id, match_format)]
                item["match_ids"].add(path.stem)
                item["innings"] += 1
                item["balls"] += int(values["balls"])
                item["runs"] += int(values["runs"])
                item["wickets"] += int(values["wickets"])
                item["maidens"] += int(values["maidens"])
                figures = (int(values["wickets"]), int(values["runs"]))
                if item["best"] is None or figures[0] > item["best"][0] or (
                    figures[0] == item["best"][0] and figures[1] < item["best"][1]
                ):
                    item["best"] = figures
                item["four_wickets"] += int(figures[0] == 4)
                item["five_wickets"] += int(figures[0] >= 5)

            for innings in match.get("innings", []):
                for over in innings.get("overs", []):
                    phase = rules.classify_phase(int(over.get("over", 0) or 0))
                    for delivery in over.get("deliveries", []):
                        batter_name = delivery.get("batter", "")
                        bowler_name = delivery.get("bowler", "")
                        batter_id = resolved.get(batter_name) or resolver.get(batter_name)
                        bowler_id = resolved.get(bowler_name) or resolver.get(bowler_name)
                        runs = delivery.get("runs") or {}
                        extras = delivery.get("extras") or {}
                        batter_runs = int(runs.get("batter", 0) or 0)
                        total_runs = int(runs.get("total", 0) or 0)
                        wide = "wides" in extras
                        noball = "noballs" in extras
                        faced = not wide
                        legal = not wide and not noball
                        boundary = batter_runs in {4, 6} and not bool(runs.get("non_boundary", False))
                        bowler_runs = batter_runs + int(extras.get("wides", 0) or 0) + int(extras.get("noballs", 0) or 0)
                        wickets = delivery.get("wickets") or []
                        bowler_wickets = sum(
                            1 for wicket in wickets
                            if str(wicket.get("kind", "")).replace("_", " ").strip().lower()
                            not in NON_BOWLER_DISMISSALS
                        )

                        if batter_id:
                            bat = batting[(batter_id, match_format)]
                            bat["dots"] += int(faced and total_runs == 0)
                            if phase in {"powerplay", "middle", "death"}:
                                bat[f"{phase}_runs"] += batter_runs
                                bat[f"{phase}_balls"] += int(faced)
                        if bowler_id:
                            bowl = bowling[(bowler_id, match_format)]
                            bowl["dots"] += int(legal and total_runs == 0)
                            bowl["boundaries"] += int(boundary)
                            if phase in {"powerplay", "middle", "death"}:
                                bowl[f"{phase}_balls"] += int(legal)
                                bowl[f"{phase}_runs"] += bowler_runs
                                bowl[f"{phase}_wickets"] += bowler_wickets
                        if batter_id and bowler_id:
                            matchup = matchups[(batter_id, bowler_id, match_format)]
                            matchup["balls"] += int(faced)
                            matchup["runs"] += batter_runs
                            matchup["dots"] += int(faced and total_runs == 0)
                            matchup["boundaries"] += int(boundary)
                            matchup["sixes"] += int(boundary and batter_runs == 6)
                            matchup["wickets"] += sum(
                                1 for wicket in wickets
                                if wicket.get("player_out") == batter_name
                                and str(wicket.get("kind", "")).replace("_", " ").strip().lower()
                                not in NON_BOWLER_DISMISSALS
                            )

            if index % 500 == 0 or index == len(paths):
                print(f"{match_format}: scanned {index:,}/{len(paths):,}", flush=True)

    if resolver.ambiguous:
        print(f"Resolver ignored {len(resolver.ambiguous)} ambiguous name keys")
    return batting, bowling, matchups, unresolved, file_counts


def write_stats(conn, batting, bowling, matchups, formats):
    placeholders = ",".join("?" for _ in formats)
    conn.execute(f"DELETE FROM player_batting_stats WHERE format IN ({placeholders})", formats)
    conn.execute(f"DELETE FROM player_bowling_stats WHERE format IN ({placeholders})", formats)
    conn.execute(f"DELETE FROM batter_bowler_matchups WHERE format IN ({placeholders})", formats)
    now = datetime.now(timezone.utc).isoformat()

    batting_rows = []
    for (player_id, match_format), item in batting.items():
        dismissals = max(0, item["innings"] - item["not_outs"])
        mean = statistics.mean(item["scores"]) if item["scores"] else 0
        consistency = None
        if len(item["scores"]) >= 5 and mean > 0:
            consistency = round(max(0, (1 - statistics.stdev(item["scores"]) / mean) * 100), 2)
        values = (
            str(uuid.uuid4()), player_id, match_format, "career", item["matches"],
            item["innings"], item["not_outs"], item["runs"], item["highest"],
            _safe_rate(item["runs"], dismissals), _safe_rate(item["runs"], item["balls"], 100),
            item["balls"], item["fours"], item["sixes"],
            _safe_rate(item["fours"] + item["sixes"], item["balls"], 100),
            _safe_rate(item["dots"], item["balls"], 100), item["fifties"], item["hundreds"],
            item["powerplay_runs"], _safe_rate(item["powerplay_runs"], item["powerplay_balls"], 100) or 0,
            item["middle_runs"], _safe_rate(item["middle_runs"], item["middle_balls"], 100) or 0,
            item["death_runs"], _safe_rate(item["death_runs"], item["death_balls"], 100) or 0,
            item["chasing_runs"], _safe_rate(item["chasing_runs"], item["chasing_balls"], 100),
            item["first_runs"], _safe_rate(item["first_runs"], item["first_balls"], 100),
            consistency, now,
        )
        batting_rows.append(values)
    conn.executemany(
        """INSERT INTO player_batting_stats VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        batting_rows,
    )

    bowling_rows = []
    for (player_id, match_format), item in bowling.items():
        best = f"{item['best'][0]}/{item['best'][1]}" if item["best"] else None
        values = (
            str(uuid.uuid4()), player_id, match_format, "career", len(item["match_ids"]),
            item["innings"], _overs(item["balls"]), item["balls"], item["wickets"], item["runs"],
            _safe_rate(item["runs"], item["wickets"]), _safe_rate(item["balls"], item["wickets"]),
            _safe_rate(item["runs"], item["balls"], 6), _safe_rate(item["dots"], item["balls"], 100),
            _safe_rate(item["boundaries"], item["balls"], 100),
            _overs(item["powerplay_balls"]), item["powerplay_wickets"], _safe_rate(item["powerplay_runs"], item["powerplay_balls"], 6),
            _overs(item["middle_balls"]), item["middle_wickets"], _safe_rate(item["middle_runs"], item["middle_balls"], 6),
            _overs(item["death_balls"]), item["death_wickets"], _safe_rate(item["death_runs"], item["death_balls"], 6),
            now, item["maidens"], best, item["four_wickets"], item["five_wickets"],
        )
        bowling_rows.append(values)
    conn.executemany(
        """INSERT INTO player_bowling_stats VALUES
        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        bowling_rows,
    )

    matchup_rows = []
    for (batter_id, bowler_id, match_format), item in matchups.items():
        if item["balls"] < 10:
            continue
        matchup_rows.append((
            str(uuid.uuid4()), batter_id, bowler_id, match_format, item["balls"], item["runs"],
            item["wickets"], _safe_rate(item["runs"], item["balls"], 100),
            _safe_rate(item["runs"], item["wickets"]), item["dots"], item["boundaries"],
            item["sixes"], now,
        ))
    conn.executemany(
        "INSERT INTO batter_bowler_matchups VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        matchup_rows,
    )
    return len(batting_rows), len(bowling_rows), len(matchup_rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--formats", nargs="+", choices=FORMAT_DIRS, default=list(FORMAT_DIRS))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with sqlite3.connect(args.database) as conn:
        batting, bowling, matchups, unresolved, counts = scan(conn, args.formats)
        print("Official match files:", counts)
        if unresolved:
            sample = ", ".join(sorted(unresolved)[:20])
            raise RuntimeError(f"Unresolved source players ({len(unresolved)}): {sample}")
        if not args.apply:
            print(f"Dry run: {len(batting)} batting and {len(bowling)} bowling player-format rows")
            return

    backup = args.database.with_name(args.database.stem + ".pre-official-stats.db")
    shutil.copy2(args.database, backup)
    with sqlite3.connect(args.database) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        rows = write_stats(conn, batting, bowling, matchups, args.formats)
        conn.commit()
    print(f"Wrote batting={rows[0]:,}, bowling={rows[1]:,}, matchups={rows[2]:,}")
    print(f"Backup: {backup}")


if __name__ == "__main__":
    main()
