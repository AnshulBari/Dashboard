"""Recompute ODI batting aggregates and enforce serving-table invariants."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline.pipeline.analytics import compute_player_batting_stats
from data_pipeline.pipeline.player_identity import normalize_player_names
from data_pipeline.pipeline.reader import read_directory
from data_pipeline.pipeline.run import CricketPipeline

DATABASE_URL = "sqlite:///data/cricket_intelligence.db"


def main() -> None:
    pipeline = CricketPipeline(database_url=DATABASE_URL)
    pipeline.initialize()
    frame = normalize_player_names(read_directory(ROOT / "data" / "raw" / "odi"))
    frame = pipeline.validate(frame)
    batting = compute_player_batting_stats(frame)
    batting = pipeline._resolve_player_ids(batting, "player_name")
    columns = [
        "player_id", "format", "period", "matches", "innings", "not_outs",
        "runs", "highest_score", "batting_average", "strike_rate", "balls_faced",
        "fours", "sixes", "boundary_pct", "dot_ball_pct", "fifties", "hundreds",
        "powerplay_runs", "powerplay_strike_rate", "middle_runs",
        "middle_strike_rate", "death_runs", "death_strike_rate", "chasing_runs",
        "chasing_strike_rate", "first_innings_runs", "first_innings_strike_rate",
        "consistency_score",
    ]
    write_frame = batting[[column for column in columns if column in batting.columns]].copy()
    pipeline.db.write_analytics_table(
        write_frame, "player_batting_stats", format_filter="ODI"
    )
    pipeline.db.close()
    print(f"Rebuilt {len(write_frame)} ODI batting rows from raw match data")


if __name__ == "__main__":
    main()
