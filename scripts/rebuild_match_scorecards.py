"""Rebuild compact, API-ready match scorecards from official Cricsheet JSON."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline.pipeline.db_manager import DatabaseManager
from data_pipeline.pipeline.scorecards import ScorecardGenerator
from rebuild_official_player_stats import DEFAULT_DB, FORMAT_DIRS


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def _verify(engine) -> dict[str, int]:
    with engine.connect() as conn:
        values = {
            "matches": conn.execute(text("SELECT COUNT(*) FROM matches")).scalar_one(),
            "innings": conn.execute(text("SELECT COUNT(*) FROM innings")).scalar_one(),
            "batting_rows": conn.execute(text("SELECT COUNT(*) FROM match_batting_summary")).scalar_one(),
            "bowling_rows": conn.execute(text("SELECT COUNT(*) FROM match_bowling_summary")).scalar_one(),
            "matches_with_batting": conn.execute(text("SELECT COUNT(DISTINCT match_id) FROM match_batting_summary")).scalar_one(),
            "matches_with_bowling": conn.execute(text("SELECT COUNT(DISTINCT match_id) FROM match_bowling_summary")).scalar_one(),
            "invalid_batting": conn.execute(text("""
                SELECT COUNT(*) FROM match_batting_summary
                WHERE runs < 0 OR balls < 0 OR fours < 0 OR sixes < 0
                   OR batting_position IS NULL OR batting_position < 1
            """)).scalar_one(),
            "invalid_bowling": conn.execute(text("""
                SELECT COUNT(*) FROM match_bowling_summary
                WHERE balls_bowled < 0 OR maidens < 0 OR runs_conceded < 0
                   OR wickets < 0 OR bowling_position IS NULL OR bowling_position < 1
            """)).scalar_one(),
        }
    if not values["batting_rows"] or not values["bowling_rows"]:
        raise RuntimeError("Scorecard rebuild produced empty serving tables")
    if values["invalid_batting"] or values["invalid_bowling"]:
        raise RuntimeError(f"Scorecard invariant failure: {values}")
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--format", choices=tuple(FORMAT_DIRS), action="append")
    parser.add_argument("--match", help="Rebuild one numeric Cricsheet match ID")
    args = parser.parse_args()

    database_url = _sqlite_url(args.database)
    manager = DatabaseManager(database_url)
    manager.initialize()
    generator = ScorecardGenerator(manager.engine)
    formats = args.format or list(FORMAT_DIRS)

    totals = {"processed": 0, "skipped": 0, "failed": 0, "batting": 0, "bowling": 0}
    for match_format in formats:
        directory = FORMAT_DIRS[match_format]
        if args.match:
            path = directory / f"{args.match}.json"
            if not path.exists():
                continue
            result = generator.generate_from_json_file(path, match_format)
            totals["processed"] += int(result.get("status") == "COMPLETED")
            totals["skipped"] += int(result.get("status") == "SKIPPED")
            totals["failed"] += int(result.get("status") not in {"COMPLETED", "SKIPPED"})
            totals["batting"] += result.get("batting_rows", 0)
            totals["bowling"] += result.get("bowling_rows", 0)
            print(f"{match_format} {args.match}: {result}", flush=True)
            break

        result = generator.generate_from_directory(directory, match_format)
        totals["processed"] += result.get("processed", 0)
        totals["skipped"] += result.get("skipped", 0)
        totals["failed"] += result.get("failed", 0)
        totals["batting"] += result.get("total_batting_rows", 0)
        totals["bowling"] += result.get("total_bowling_rows", 0)
        print(f"{match_format}: {result['processed']:,} matches", flush=True)

    if args.match and totals["processed"] == 0:
        raise SystemExit(f"Official match {args.match} was not found in {formats}")
    if totals["failed"]:
        raise RuntimeError(f"Scorecard rebuild failures: {totals}")

    verification = _verify(manager.engine)
    print(f"Rebuild totals: {totals}", flush=True)
    print(f"Serving verification: {verification}", flush=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
