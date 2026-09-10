"""Role-aware, explainable player Impact Score computation.

The public score is a 0-100 composite. Recent form is deliberately an input to
Impact Score, not a second headline rating.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


IMPACT_WEIGHTS = {
    "performance_impact": 0.35,
    "recent_form": 0.30,
    "pressure_impact": 0.15,
    "opposition_quality": 0.10,
    "consistency": 0.05,
    "efficiency": 0.05,
}


def _career_rows(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["player_id", "format"])
    current = frame.copy()
    if "period" in current.columns:
        current = current[current["period"].fillna("career") == "career"]
    numeric = [
        column for column in current.columns
        if column not in {"id", "player_id", "format", "period", "calculated_at"}
        and pd.api.types.is_numeric_dtype(current[column])
    ]
    aggregations = {column: "sum" for column in numeric}
    for column in ("batting_average", "strike_rate", "economy", "bowling_average"):
        if column in aggregations:
            aggregations[column] = "mean"
    current = current.groupby(["player_id", "format"], as_index=False).agg(aggregations)
    return current.rename(columns={column: f"{prefix}_{column}" for column in numeric})


def _rank_within_format(frame: pd.DataFrame, values: pd.Series, valid: pd.Series, invert: bool = False) -> pd.Series:
    scores = pd.Series(np.nan, index=frame.index, dtype=float)
    for _, indexes in frame[valid].groupby("format").groups.items():
        sample = values.loc[indexes]
        if sample.notna().sum() <= 1:
            scores.loc[indexes] = 50.0
        else:
            scores.loc[indexes] = sample.rank(pct=True, ascending=not invert) * 100.0
    return scores


def _combine_role_scores(primary: pd.Series, secondary: pd.Series) -> pd.Series:
    both = primary.notna() & secondary.notna()
    result = primary.combine_first(secondary)
    result.loc[both] = (
        np.maximum(primary.loc[both], secondary.loc[both]) * 0.75
        + np.minimum(primary.loc[both], secondary.loc[both]) * 0.25
    )
    return result.fillna(50.0)


def compute_impact_scores_from_aggregates(
    prior_components: pd.DataFrame,
    batting_stats: pd.DataFrame,
    bowling_stats: pd.DataFrame,
    recent_stats: pd.DataFrame,
) -> pd.DataFrame:
    """Compute one role-aware Impact Score per player and format.

    Career quality measures meaningful sustained contribution; rolling recent
    aggregates supply current form. Percentile ranking is format-local, while
    confidence shrinkage prevents tiny samples from topping leaderboards.
    """
    # Prior components enrich current players but must never keep an obsolete
    # alias identity alive after a source/identity rebuild. Only current career
    # or rolling aggregates define which player-format rows exist.
    sources = [frame[["player_id", "format"]] for frame in (
        batting_stats, bowling_stats, recent_stats
    ) if not frame.empty]
    if not sources:
        return pd.DataFrame()

    result = pd.concat(sources, ignore_index=True).drop_duplicates()
    batting = _career_rows(batting_stats, "bat")
    bowling = _career_rows(bowling_stats, "bowl")
    result = result.merge(batting, on=["player_id", "format"], how="left")
    result = result.merge(bowling, on=["player_id", "format"], how="left")

    prior_columns = [
        "player_id", "format", "consistency_component",
        "opposition_strength_component", "match_situation_component",
        "efficiency_component", "recent_performance_component",
        "recent_innings_count", "last_match_date",
    ]
    if not prior_components.empty:
        available = [column for column in prior_columns if column in prior_components.columns]
        result = result.merge(
            prior_components[available].drop_duplicates(["player_id", "format"]),
            on=["player_id", "format"], how="left",
        )

    if not recent_stats.empty:
        recent_columns = [
            "player_id", "format", "matches", "batting_innings", "runs",
            "balls_faced", "bowling_innings", "wickets", "balls_bowled",
            "runs_conceded", "last_match_date",
        ]
        recent = recent_stats[[c for c in recent_columns if c in recent_stats.columns]].copy()
        recent = recent.rename(columns={
            column: f"recent_{column}" for column in recent.columns
            if column not in {"player_id", "format"}
        })
        result = result.merge(recent, on=["player_id", "format"], how="left")

    bat_innings = result.get("bat_innings", pd.Series(0, index=result.index)).fillna(0)
    bat_valid = bat_innings >= 3
    bat_average = result.get("bat_batting_average", pd.Series(np.nan, index=result.index))
    bat_strike = result.get("bat_strike_rate", pd.Series(np.nan, index=result.index))
    bat_runs = result.get("bat_runs", pd.Series(0, index=result.index)).fillna(0)
    batting_impact = (
        _rank_within_format(result, bat_average, bat_valid) * 0.45
        + _rank_within_format(result, bat_strike, bat_valid) * 0.25
        + _rank_within_format(result, np.log1p(bat_runs), bat_valid) * 0.30
    )
    batting_impact = 50 + (batting_impact - 50) * (bat_innings / (bat_innings + 8))

    bowl_innings = result.get("bowl_innings", pd.Series(0, index=result.index)).fillna(0)
    bowl_balls = result.get("bowl_balls_bowled", pd.Series(0, index=result.index)).fillna(0)
    bowl_wickets = result.get("bowl_wickets", pd.Series(0, index=result.index)).fillna(0)
    bowl_economy = result.get("bowl_economy", pd.Series(np.nan, index=result.index))
    bowl_valid = (bowl_innings >= 3) & (bowl_balls > 0)
    wickets_per_innings = bowl_wickets / bowl_innings.replace(0, np.nan)
    bowling_impact = (
        _rank_within_format(result, wickets_per_innings, bowl_valid) * 0.45
        + _rank_within_format(result, bowl_economy, bowl_valid, invert=True) * 0.25
        + _rank_within_format(result, np.log1p(bowl_wickets), bowl_valid) * 0.30
    )
    bowling_impact = 50 + (bowling_impact - 50) * (bowl_innings / (bowl_innings + 8))
    result["performance_impact_component"] = _combine_role_scores(batting_impact, bowling_impact)

    recent_bat_innings = result.get("recent_batting_innings", pd.Series(0, index=result.index)).fillna(0)
    recent_runs = result.get("recent_runs", pd.Series(0, index=result.index)).fillna(0)
    recent_balls = result.get("recent_balls_faced", pd.Series(0, index=result.index)).fillna(0)
    recent_bat_valid = recent_bat_innings >= 2
    recent_runs_per_innings = recent_runs / recent_bat_innings.replace(0, np.nan)
    recent_strike = recent_runs * 100 / recent_balls.replace(0, np.nan)
    recent_batting = (
        _rank_within_format(result, recent_runs_per_innings, recent_bat_valid) * 0.65
        + _rank_within_format(result, recent_strike, recent_bat_valid) * 0.35
    )

    recent_bowl_innings = result.get("recent_bowling_innings", pd.Series(0, index=result.index)).fillna(0)
    recent_wickets = result.get("recent_wickets", pd.Series(0, index=result.index)).fillna(0)
    recent_bowl_balls = result.get("recent_balls_bowled", pd.Series(0, index=result.index)).fillna(0)
    recent_conceded = result.get("recent_runs_conceded", pd.Series(0, index=result.index)).fillna(0)
    recent_bowl_valid = (recent_bowl_innings >= 2) & (recent_bowl_balls > 0)
    recent_wicket_rate = recent_wickets / recent_bowl_innings.replace(0, np.nan)
    recent_economy = recent_conceded * 6 / recent_bowl_balls.replace(0, np.nan)
    recent_bowling = (
        _rank_within_format(result, recent_wicket_rate, recent_bowl_valid) * 0.65
        + _rank_within_format(result, recent_economy, recent_bowl_valid, invert=True) * 0.35
    )
    recent_combined = _combine_role_scores(recent_batting, recent_bowling)
    recent_appearances = result.get("recent_matches", pd.Series(0, index=result.index)).fillna(0)
    recent_confidence = (recent_appearances / (recent_appearances + 5)).clip(0, 1)
    old_recent = result.get("recent_performance_component", pd.Series(50, index=result.index)).fillna(50)
    result["recent_form_component"] = np.where(
        recent_appearances > 0,
        50 + (recent_combined - 50) * recent_confidence,
        old_recent,
    )

    result["pressure_impact_component"] = result.get(
        "match_situation_component", pd.Series(50, index=result.index)
    ).fillna(50).clip(0, 100)
    result["opposition_quality_component"] = result.get(
        "opposition_strength_component", pd.Series(50, index=result.index)
    ).fillna(50).clip(0, 100)
    result["consistency_component"] = result.get(
        "consistency_component", pd.Series(50, index=result.index)
    ).fillna(50).clip(0, 100)
    result["efficiency_component"] = result.get(
        "efficiency_component", pd.Series(50, index=result.index)
    ).fillna(50).clip(0, 100)

    result["impact_score"] = sum(
        result[f"{component}_component"] * weight
        for component, weight in IMPACT_WEIGHTS.items()
    ).round(2).clip(0, 100)
    result["recent_innings_count"] = result.get(
        "recent_innings_count", recent_bat_innings + recent_bowl_innings
    ).fillna(recent_bat_innings + recent_bowl_innings).astype(int)
    if "recent_last_match_date" in result:
        if "last_match_date" not in result:
            result["last_match_date"] = pd.NaT
        result["last_match_date"] = result["recent_last_match_date"].combine_first(
            result["last_match_date"]
        )
    elif "last_match_date" not in result:
        result["last_match_date"] = pd.NaT

    return result[[
        "player_id", "format", "impact_score", "performance_impact_component",
        "recent_form_component", "pressure_impact_component",
        "opposition_quality_component", "consistency_component",
        "efficiency_component", "recent_innings_count", "last_match_date",
    ]]
