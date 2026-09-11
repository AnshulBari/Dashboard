"""Checked-in authoritative aggregates for ODI World Cup editions.

Cricsheet remains the scorecard source. Its public archive deliberately omits
some matches, so tournament-wide totals cannot always be derived from the
locally indexed scorecards alone. These small snapshots keep aggregate views
accurate while the API reports scorecard coverage separately.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


REFERENCE_PATH = Path(__file__).resolve().parents[2] / "data" / "reference" / "cwc_official_stats.json"
CWC_NAME = "ICC Cricket World Cup"


@lru_cache(maxsize=1)
def load_cwc_reference() -> dict[str, Any]:
    with REFERENCE_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def cwc_edition(competition_name: str | None, season_name: str | None) -> dict[str, Any] | None:
    if str(competition_name or "").casefold() != CWC_NAME.casefold():
        return None
    return load_cwc_reference()["editions"].get(str(season_name or ""))


def expand_rows(kind: str, rows: list[list[Any]]) -> list[dict[str, Any]]:
    schema = load_cwc_reference()["schemas"][kind]
    return [dict(zip(schema, row, strict=True)) for row in rows]


def overs_to_balls(value: str | int | float) -> int:
    overs, _, balls = str(value).partition(".")
    return int(overs) * 6 + int(balls or 0)


def score_value(value: str | int | None) -> int | None:
    if value is None:
        return None
    return int(str(value).replace("*", ""))


def bowling_figures(value: str) -> tuple[int, int]:
    wickets, runs = str(value).split("/", maxsplit=1)
    return int(wickets), int(runs)
