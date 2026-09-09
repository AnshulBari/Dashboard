"""Recompute the public role-aware Impact Score from serving aggregates."""

from __future__ import annotations

import sqlite3
import sys
import uuid
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline.pipeline.impact import compute_impact_scores_from_aggregates


DB_PATH = ROOT / "data" / "cricket_intelligence.db"


def main() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        prior = pd.read_sql_query("SELECT * FROM player_form", conn)
        batting = pd.read_sql_query("SELECT * FROM player_batting_stats", conn)
        bowling = pd.read_sql_query("SELECT * FROM player_bowling_stats", conn)
        recent = pd.read_sql_query("SELECT * FROM player_recent_stats", conn)
        scores = compute_impact_scores_from_aggregates(prior, batting, bowling, recent)

        rows = []
        for item in scores.to_dict("records"):
            rows.append((
                str(uuid.uuid4()), item["player_id"], item["format"], item["impact_score"],
                item["recent_form_component"], item["consistency_component"],
                item["opposition_quality_component"], item["performance_impact_component"],
                item["pressure_impact_component"], item["efficiency_component"],
                item["recent_innings_count"], item.get("last_match_date"),
            ))

        conn.executemany(
            """INSERT INTO player_form
               (id, player_id, format, form_score, recent_performance_component,
                consistency_component, opposition_strength_component,
                venue_performance_component, match_situation_component,
                efficiency_component, recent_innings_count, last_match_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(player_id, format) DO UPDATE SET
                 form_score=excluded.form_score,
                 recent_performance_component=excluded.recent_performance_component,
                 consistency_component=excluded.consistency_component,
                 opposition_strength_component=excluded.opposition_strength_component,
                 venue_performance_component=excluded.venue_performance_component,
                 match_situation_component=excluded.match_situation_component,
                 efficiency_component=excluded.efficiency_component,
                 recent_innings_count=excluded.recent_innings_count,
                 last_match_date=excluded.last_match_date,
                 last_calculated_at=CURRENT_TIMESTAMP""",
            rows,
        )
        conn.commit()

    print(
        f"Recomputed {len(scores):,} player-format Impact Scores "
        f"(range {scores.impact_score.min():.2f}-{scores.impact_score.max():.2f})."
    )


if __name__ == "__main__":
    main()
