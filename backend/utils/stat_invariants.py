"""Shared guards for impossible analytical values at the serving boundary."""

from __future__ import annotations

from numbers import Number

NON_NEGATIVE_FIELDS = {
    "matches", "innings", "not_outs", "runs", "balls_faced", "fours", "sixes",
    "fifties", "hundreds", "wickets", "balls_bowled", "runs_conceded",
    "total_matches", "total_innings", "total_balls", "total_runs", "total_wickets",
    "dot_balls", "boundaries", "maidens", "extras", "wins", "losses", "ties",
    "no_results", "win_margin", "highest_score", "batting_average", "strike_rate",
    "bowling_average", "economy", "runs_per_match", "avg_first_innings_score",
    "average_first_innings_score", "average_runs", "average_wickets",
}

PERCENTAGE_FIELDS = {
    "boundary_pct", "dot_ball_pct", "boundary_conceded_pct", "win_rate",
    "chasing_win_pct", "defending_win_pct", "pace_wickets_pct", "spin_wickets_pct",
    "impact_score", "form_score", "overall_strength_score", "batting_strength_score",
    "bowling_strength_score",
}


def safe_not_outs_sql(innings: str = "innings", not_outs: str = "not_outs") -> str:
    """Return a portable SQL expression bounded to ``0 <= not-outs <= innings``."""
    return (
        f"CASE WHEN SUM({not_outs}) < 0 THEN 0 "
        f"WHEN SUM({not_outs}) > SUM({innings}) THEN SUM({innings}) "
        f"ELSE SUM({not_outs}) END"
    )


def sanitize_stat_record(record: dict) -> dict:
    """Clamp impossible count/rate values and recalculate a dependent average."""
    for field in NON_NEGATIVE_FIELDS:
        value = record.get(field)
        if isinstance(value, Number) and value < 0:
            record[field] = 0

    innings = record.get("innings")
    not_outs = record.get("not_outs")
    if isinstance(innings, Number) and isinstance(not_outs, Number):
        record["not_outs"] = min(max(not_outs, 0), max(innings, 0))
        runs = record.get("runs")
        dismissals = innings - record["not_outs"]
        if isinstance(runs, Number) and "batting_average" in record:
            record["batting_average"] = round(runs / dismissals, 2) if dismissals > 0 else float(runs)

    # A single delivery cannot contribute more than one of each event type. These
    # guards keep legacy/cached aggregates from leaking impossible relationships.
    total_balls = record.get("total_balls")
    if isinstance(total_balls, Number):
        for field in ("dot_balls", "boundaries", "total_wickets"):
            value = record.get(field)
            if isinstance(value, Number):
                record[field] = min(max(value, 0), max(total_balls, 0))

    balls_bowled = record.get("balls_bowled")
    wickets = record.get("wickets")
    if isinstance(balls_bowled, Number) and isinstance(wickets, Number):
        record["wickets"] = min(max(wickets, 0), max(balls_bowled, 0))

    total_matches = record.get("total_matches")
    if isinstance(total_matches, Number):
        for field in ("wins", "losses", "ties", "no_results"):
            value = record.get(field)
            if isinstance(value, Number):
                record[field] = min(max(value, 0), max(total_matches, 0))

    for field in PERCENTAGE_FIELDS:
        value = record.get(field)
        if isinstance(value, Number):
            record[field] = min(max(value, 0), 100)
    return record
