"""
Analytics Computation
=====================

Computes all analytical statistics from delivery-level data using pandas.

Produces:
- Player batting stats (career, by format)
- Player bowling stats (career, by format)
- Player form scores
- Team performance metrics
- Venue statistics
- Batter-bowler matchups

All computations are based on the same formulas as the PySpark versions,
but implemented in pandas for compatibility with Java-free environments.
"""

import logging
import uuid
from typing import Optional

import numpy as np
import pandas as pd

from data_pipeline.pipeline.format_config import get_format_rules, FormatRules

logger = logging.getLogger(__name__)


# Deliveries that do not count towards a bowler's wicket tally.  Keep this in
# one place so career, phase and matchup figures use the same cricket rules.
NON_BOWLER_DISMISSALS = {
    "run out",
    "retired hurt",
    "retired out",
    "retired not out",
    "obstructing the field",
    "hit the ball twice",
    "handled the ball",
    "timed out",
}


def _normalized_values(df: pd.DataFrame, column: str) -> pd.Series:
    """Return a lower-case, whitespace-normalized string series."""
    if column not in df.columns:
        return pd.Series("", index=df.index, dtype="object")
    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.replace("_", " ", regex=False)
        .str.strip()
        .str.lower()
    )


def _is_ball_faced(df: pd.DataFrame) -> pd.Series:
    """A batter faces a no-ball, but not a wide."""
    return _normalized_values(df, "extra_type") != "wide"


def _is_legal_ball(df: pd.DataFrame) -> pd.Series:
    """Wides and no-balls do not count in a bowler's legal-ball total."""
    return ~_normalized_values(df, "extra_type").isin({"wide", "noball", "no ball"})


def _bowler_runs(df: pd.DataFrame) -> pd.Series:
    """Runs charged to the bowler, excluding byes, leg-byes and penalties."""
    batter_runs = pd.to_numeric(df["runs_batter"], errors="coerce").fillna(0)

    # New flattened data contains the individual extras and is exact even for
    # unusual deliveries containing more than one kind of extra.  The fallback
    # keeps older prepared batches compatible.
    if "extras_wides" in df.columns or "extras_noballs" in df.columns:
        wides = pd.to_numeric(
            df.get("extras_wides", pd.Series(0, index=df.index)), errors="coerce"
        ).fillna(0)
        noballs = pd.to_numeric(
            df.get("extras_noballs", pd.Series(0, index=df.index)), errors="coerce"
        ).fillna(0)
        return batter_runs + wides + noballs

    extras = pd.to_numeric(df["runs_extras"], errors="coerce").fillna(0)
    chargeable = _normalized_values(df, "extra_type").isin({"wide", "noball", "no ball"})
    return batter_runs + extras.where(chargeable, 0)


def _is_bowler_wicket(df: pd.DataFrame) -> pd.Series:
    """Return wickets credited to the bowler under scorecard conventions."""
    return df["is_wicket"].fillna(False).astype(bool) & ~_normalized_values(
        df, "wicket_type"
    ).isin(NON_BOWLER_DISMISSALS)


def _is_batter_dismissal(df: pd.DataFrame) -> pd.Series:
    """Return dismissals that count as an out in a batter's average."""
    non_dismissals = {"retired hurt", "retired not out"}
    return (
        df["is_wicket"].fillna(False).astype(bool)
        & (df["dismissed_player"] == df["batter"])
        & ~_normalized_values(df, "wicket_type").isin(non_dismissals)
    )


def _is_boundary(df: pd.DataFrame, runs: int) -> pd.Series:
    """Identify actual boundaries, excluding all-run/overthrow non-boundaries."""
    scored = pd.to_numeric(df["runs_batter"], errors="coerce").fillna(0) == runs
    if "non_boundary" not in df.columns:
        return scored
    return scored & ~df["non_boundary"].fillna(False).astype(bool)


def _minmax_by_format(df: pd.DataFrame, column: str, invert: bool = False) -> pd.Series:
    """Normalize a metric to 0-100 independently inside each format."""
    grouped = df.groupby("format")[column]
    minimum = grouped.transform("min")
    maximum = grouped.transform("max")
    value_range = maximum - minimum
    score = ((df[column] - minimum) / value_range.where(value_range != 0)) * 100
    score = score.fillna(50.0)
    return (100 - score if invert else score).round(2)


def _classify_phase_format_aware(over_number: int, fmt: str) -> str:
    """
    Classify an over into a phase using format-aware rules.
    
    For Test cricket, returns 'general' (no T20-style phases).
    For limited-overs formats, returns powerplay/middle/death.
    """
    rules = get_format_rules(fmt)
    return rules.classify_phase(over_number)


def _get_phase_over_ranges(fmt: str) -> list[tuple[str, int, int]]:
    """
    Get phase over ranges for a format.
    
    Returns list of (phase_name, start_over, end_over) tuples.
    For Test cricket, returns a single 'general' phase covering all overs.
    """
    rules = get_format_rules(fmt)
    if rules.format == "Test":
        return [("general", 0, 1000)]
    return [
        ("powerplay", 0, rules.powerplay_end),
        ("middle", rules.powerplay_end + 1, rules.middle_end),
        ("death", rules.middle_end + 1, 1000),
    ]


# ============================================================
# Player Batting Statistics
# ============================================================

def compute_player_batting_stats(deliveries_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute career batting statistics per player per format.
    
    Groups deliveries by (batter, format) and aggregates into batting stats.
    """
    logger.info("Computing player batting statistics...")
    
    # Retain wide rows for team totals, but mark them as not faced by the
    # batter.  A no-ball does count as a ball faced in cricket scorecards.
    batting = deliveries_df[deliveries_df["batter"].notna() & (deliveries_df["batter"] != "")].copy()
    batting["ball_faced"] = _is_ball_faced(batting).astype(int)
    batting["is_dot_ball"] = (
        batting["ball_faced"].astype(bool)
        & (pd.to_numeric(batting["runs_total"], errors="coerce").fillna(0) == 0)
    ).astype(int)
    batting["is_four"] = _is_boundary(batting, 4).astype(int)
    batting["is_six"] = _is_boundary(batting, 6).astype(int)
    
    # Determine if each delivery resulted in the batter being out
    batting["is_dismissed"] = _is_batter_dismissal(batting)
    
    # Group by batter and format
    grouped = batting.groupby(["batter", "format"]).agg(
        matches=("match_id", "nunique"),
        innings=("innings_number", "count"),  # Approximate: each delivery row = part of innings
        runs=("runs_batter", "sum"),
        balls_faced=("ball_faced", "sum"),
        highest_score=("runs_batter", "max"),  # Will be replaced with per-innings max
        fours=("is_four", "sum"),
        sixes=("is_six", "sum"),
        dot_balls=("is_dot_ball", "sum"),
        not_outs=("is_dismissed", lambda x: (~x).sum() - 1),  # Approximate
    ).reset_index()
    
    # Calculate per-innings stats for highest score, fifties, hundreds
    innings_scores = batting.groupby(["batter", "format", "match_id", "innings_number"]).agg(
        innings_runs=("runs_batter", "sum"),
    ).reset_index()
    
    career_innings = innings_scores.groupby(["batter", "format"]).agg(
        total_innings=("innings_runs", "count"),
        highest_score=("innings_runs", "max"),
        fifties=("innings_runs", lambda x: ((x >= 50) & (x < 100)).sum()),
        hundreds=("innings_runs", lambda x: (x >= 100).sum()),
    ).reset_index()
    
    # Merge
    result = grouped.merge(career_innings, on=["batter", "format"], how="left")
    
    # Fix innings count
    result["innings"] = result["total_innings"]
    result.drop(columns=["total_innings"], inplace=True, errors="ignore")
    
    # Not outs: innings - dismissals
    dismissals = batting[batting["is_dismissed"]].groupby(["batter", "format"]).size().reset_index(name="dismissals")
    result = result.merge(dismissals, on=["batter", "format"], how="left")
    result["dismissals"] = result["dismissals"].fillna(0)
    result["not_outs"] = result["innings"] - result["dismissals"]
    
    # Derived stats
    result["batting_average"] = np.where(
        result["dismissals"] > 0,
        np.round(result["runs"] / result["dismissals"], 2),
        result["runs"].astype(float)
    )
    result["strike_rate"] = np.where(
        result["balls_faced"] > 0,
        np.round(result["runs"] * 100.0 / result["balls_faced"], 2),
        0.0
    )
    result["boundary_pct"] = np.where(
        result["balls_faced"] > 0,
        np.round((result["fours"] + result["sixes"]) * 100.0 / result["balls_faced"], 2),
        0.0
    )
    result["dot_ball_pct"] = np.where(
        result["balls_faced"] > 0,
        np.round(result["dot_balls"] * 100.0 / result["balls_faced"], 2),
        0.0
    )
    
    # Phase-specific batting — format-aware
    # Use a unified approach: classify each delivery's phase per format
    batting_with_phase = batting.copy()
    batting_with_phase["phase"] = batting_with_phase.apply(
        lambda r: _classify_phase_format_aware(r["over_number"], r["format"]), axis=1
    )
    
    for phase_name in ["powerplay", "middle", "death"]:
        phase_data = batting_with_phase[batting_with_phase["phase"] == phase_name]
        
        phase_agg = phase_data.groupby(["batter", "format"]).agg(
            runs=("runs_batter", "sum"),
            balls=("ball_faced", "sum"),
        ).reset_index()
        
        phase_agg[f"{phase_name}_runs"] = phase_agg["runs"]
        phase_agg[f"{phase_name}_strike_rate"] = np.where(
            phase_agg["balls"] > 0,
            np.round(phase_agg["runs"] * 100.0 / phase_agg["balls"], 2),
            0.0
        )
        
        result = result.merge(
            phase_agg[["batter", "format", f"{phase_name}_runs", f"{phase_name}_strike_rate"]],
            on=["batter", "format"], how="left"
        )
        result[f"{phase_name}_runs"] = result[f"{phase_name}_runs"].fillna(0)
        result[f"{phase_name}_strike_rate"] = result[f"{phase_name}_strike_rate"].fillna(0)
    
    # Chasing vs setting
    for situation, innings_filter in [("chasing", [2]), ("first_innings", [1])]:
        sit_data = batting[batting["innings_number"].isin(innings_filter)]
        sit_agg = sit_data.groupby(["batter", "format"]).agg(
            runs=("runs_batter", "sum"),
            balls=("ball_faced", "sum"),
        ).reset_index()
        
        sit_agg[f"{situation}_runs"] = sit_agg["runs"]
        sit_agg[f"{situation}_strike_rate"] = np.where(
            sit_agg["balls"] > 0,
            np.round(sit_agg["runs"] * 100.0 / sit_agg["balls"], 2),
            0.0
        )
        
        result = result.merge(
            sit_agg[["batter", "format", f"{situation}_runs", f"{situation}_strike_rate"]],
            on=["batter", "format"], how="left"
        )
        result[f"{situation}_runs"] = result[f"{situation}_runs"].fillna(0)
        result[f"{situation}_strike_rate"] = result[f"{situation}_strike_rate"].fillna(0)
    
    # Consistency score (1 - CV, normalized to 0-100)
    innings_stats = batting.groupby(["batter", "format", "match_id", "innings_number"]).agg(
        innings_runs=("runs_batter", "sum"),
    ).reset_index()
    
    consistency = innings_stats.groupby(["batter", "format"]).agg(
        mean_runs=("innings_runs", "mean"),
        stddev_runs=("innings_runs", "std"),
        sample_size=("innings_runs", "count"),
    ).reset_index()
    
    consistency["consistency_score"] = np.where(
        consistency["sample_size"] >= 5,
        np.round(
            np.maximum(0, (1 - consistency["stddev_runs"] / consistency["mean_runs"].clip(lower=0.01)) * 100),
            2
        ),
        np.nan
    )
    
    result = result.merge(
        consistency[["batter", "format", "consistency_score"]],
        on=["batter", "format"], how="left"
    )
    
    # Set period = 'career'
    result["period"] = "career"
    
    # Clean up column names to match DB
    result = result.rename(columns={
        "batter": "player_name",  # Will be resolved to player_id later
    })
    
    logger.info(f"  Computed batting stats for {len(result)} player-format combinations")
    return result


# ============================================================
# Player Bowling Statistics
# ============================================================

def compute_player_bowling_stats(deliveries_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute career bowling statistics per player per format.
    """
    logger.info("Computing player bowling statistics...")
    
    bowling = deliveries_df[deliveries_df["bowler"].notna() & (deliveries_df["bowler"] != "")].copy()
    
    bowling["legal_ball"] = _is_legal_ball(bowling).astype(int)
    bowling["bowler_runs"] = _bowler_runs(bowling)
    bowling["bowler_wicket"] = _is_bowler_wicket(bowling).astype(int)
    bowling["is_dot_ball"] = (
        bowling["legal_ball"].astype(bool)
        & (pd.to_numeric(bowling["runs_total"], errors="coerce").fillna(0) == 0)
    ).astype(int)
    bowling["is_boundary"] = (
        _is_boundary(bowling, 4) | _is_boundary(bowling, 6)
    ).astype(int)

    grouped = bowling.groupby(["bowler", "format"]).agg(
        matches=("match_id", "nunique"),
        balls_bowled=("legal_ball", "sum"),
        runs_conceded=("bowler_runs", "sum"),
        wickets=("bowler_wicket", "sum"),
        dot_balls=("is_dot_ball", "sum"),
        boundaries_conceded=("is_boundary", "sum"),
    ).reset_index()
    
    # Calculate innings count
    bowling_innings = bowling.groupby(["bowler", "format", "match_id", "innings_number"]).size().reset_index(name="balls")
    innings_count = bowling_innings.groupby(["bowler", "format"]).size().reset_index(name="innings")
    result = grouped.merge(innings_count, on=["bowler", "format"], how="left")
    
    # Derived stats
    result["overs"] = np.floor(result["balls_bowled"] / 6) + (result["balls_bowled"] % 6) / 10.0
    result["economy"] = np.where(
        result["balls_bowled"] > 0,
        np.round(result["runs_conceded"] * 6.0 / result["balls_bowled"], 2),
        999.99
    )
    result["bowling_average"] = np.where(
        result["wickets"] > 0,
        np.round(result["runs_conceded"] / result["wickets"], 2),
        999.99
    )
    result["strike_rate"] = np.where(
        result["wickets"] > 0,
        np.round(result["balls_bowled"] / result["wickets"], 2),
        999.99
    )
    result["dot_ball_pct"] = np.where(
        result["balls_bowled"] > 0,
        np.round(result["dot_balls"] * 100.0 / result["balls_bowled"], 2),
        0.0
    )
    result["boundary_conceded_pct"] = np.where(
        result["balls_bowled"] > 0,
        np.round(result["boundaries_conceded"] * 100.0 / result["balls_bowled"], 2),
        0.0
    )
    
    # Phase-specific bowling — format-aware
    bowling_with_phase = bowling.copy()
    bowling_with_phase["phase"] = bowling_with_phase.apply(
        lambda r: _classify_phase_format_aware(r["over_number"], r["format"]), axis=1
    )
    
    for phase_name in ["powerplay", "middle", "death"]:
        phase_data = bowling_with_phase[bowling_with_phase["phase"] == phase_name]
        
        phase_agg = phase_data.groupby(["bowler", "format"]).agg(
            runs=("bowler_runs", "sum"),
            balls=("legal_ball", "sum"),
            wickets=("bowler_wicket", "sum"),
        ).reset_index()
        
        phase_agg[f"{phase_name}_overs"] = np.floor(phase_agg["balls"] / 6) + (phase_agg["balls"] % 6) / 10.0
        phase_agg[f"{phase_name}_wickets"] = phase_agg["wickets"]
        phase_agg[f"{phase_name}_economy"] = np.where(
            phase_agg["balls"] > 0,
            np.round(phase_agg["runs"] * 6.0 / phase_agg["balls"], 2),
            0.0
        )
        
        result = result.merge(
            phase_agg[["bowler", "format", f"{phase_name}_overs", f"{phase_name}_wickets", f"{phase_name}_economy"]],
            on=["bowler", "format"], how="left"
        )
        result[f"{phase_name}_overs"] = result[f"{phase_name}_overs"].fillna(0)
        result[f"{phase_name}_wickets"] = result[f"{phase_name}_wickets"].fillna(0)
        result[f"{phase_name}_economy"] = result[f"{phase_name}_economy"].fillna(0)
    
    result["period"] = "career"
    result = result.rename(columns={"bowler": "player_name"})
    
    logger.info(f"  Computed bowling stats for {len(result)} player-format combinations")
    return result


# ============================================================
# Player Form Score
# ============================================================

def compute_player_form_scores(deliveries_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the Player Form Score (original metric).
    
    Weighted composite:
    - Recent performance (35%)
    - Consistency (20%)
    - Opposition strength (15%)
    - Venue performance (10%)
    - Match situation (10%)
    - Efficiency (10%)
    """
    logger.info("Computing player form scores...")
    
    WEIGHTS = {
        "recent_performance": 0.35,
        "consistency": 0.20,
        "opposition_strength": 0.15,
        "venue_performance": 0.10,
        "match_situation": 0.10,
        "efficiency": 0.10,
    }
    
    MIN_INNINGS = 3
    
    form_deliveries = deliveries_df.copy()
    form_deliveries["ball_faced"] = _is_ball_faced(form_deliveries).astype(int)

    # Estimate actual opposition bowling strength from economy and credited
    # wicket rate, independently per format.
    form_deliveries["legal_ball"] = _is_legal_ball(form_deliveries).astype(int)
    form_deliveries["bowler_runs"] = _bowler_runs(form_deliveries)
    form_deliveries["bowler_wicket"] = _is_bowler_wicket(form_deliveries).astype(int)
    opposition = form_deliveries.groupby(["bowling_team", "format"]).agg(
        legal_balls=("legal_ball", "sum"),
        runs_conceded=("bowler_runs", "sum"),
        wickets=("bowler_wicket", "sum"),
    ).reset_index()
    opposition["economy"] = np.where(
        opposition["legal_balls"] > 0,
        opposition["runs_conceded"] * 6.0 / opposition["legal_balls"],
        np.nan,
    )
    opposition["wicket_rate"] = np.where(
        opposition["legal_balls"] > 0,
        opposition["wickets"] * 6.0 / opposition["legal_balls"],
        0.0,
    )
    opposition["opposition_strength"] = (
        _minmax_by_format(opposition, "economy", invert=True)
        + _minmax_by_format(opposition, "wicket_rate")
    ) / 2.0

    # Get per-player per-innings batting scores.
    innings_scores = form_deliveries[
        form_deliveries["batter"].notna() & (form_deliveries["batter"] != "")
    ].groupby(["batter", "format", "match_id", "innings_number"]).agg(
        innings_runs=("runs_batter", "sum"),
        balls_faced=("ball_faced", "sum"),
        match_date=("match_date", "first"),
        bowling_team=("bowling_team", "first"),
        venue=("venue", "first"),
    ).reset_index()
    innings_scores = innings_scores.merge(
        opposition[["bowling_team", "format", "opposition_strength"]],
        on=["bowling_team", "format"],
        how="left",
    )
    innings_scores["opposition_strength"] = innings_scores["opposition_strength"].fillna(50.0)
    
    # Sort by date for recency
    innings_scores = innings_scores.sort_values(["batter", "format", "match_date"], ascending=[True, True, False])
    
    # Count innings per player
    player_innings_count = innings_scores.groupby(["batter", "format"]).size().reset_index(name="total_innings")
    eligible_players = player_innings_count[player_innings_count["total_innings"] >= MIN_INNINGS]
    
    results = []
    
    for _, player_info in eligible_players.iterrows():
        batter = player_info["batter"]
        fmt = player_info["format"]
        
        player_data = innings_scores[
            (innings_scores["batter"] == batter) & 
            (innings_scores["format"] == fmt)
        ]
        
        # 1. Recent performance (last 10 innings)
        recent = player_data.head(10)
        recent_avg = recent["innings_runs"].mean()
        
        # 2. Consistency (1 - CV)
        mean_runs = player_data["innings_runs"].mean()
        std_runs = player_data["innings_runs"].std()
        cv = std_runs / mean_runs if mean_runs > 0 else 1.0
        consistency = max(0, (1 - cv) * 100)
        
        # 3. Opposition strength (weighted by balls faced)
        if player_data["balls_faced"].sum() > 0:
            opp_weighted = (
                player_data["opposition_strength"] * player_data["balls_faced"]
            ).sum() / player_data["balls_faced"].sum()
        else:
            opp_weighted = player_data["opposition_strength"].mean()
        
        # 4. Venue performance (CV across venues, lower = better)
        venue_perf = player_data.groupby("venue").agg(
            avg_runs=("innings_runs", "mean"),
        )
        if len(venue_perf) > 1 and venue_perf["avg_runs"].mean() > 0:
            venue_cv = venue_perf["avg_runs"].std() / venue_perf["avg_runs"].mean()
            venue_score = max(0, (1 - venue_cv) * 100)
        else:
            venue_score = 50
        
        # 5. Match situation (chasing avg / overall avg ratio)
        # For Test cricket, "chasing" concept is less meaningful — skip it
        if fmt == "Test":
            situation_ratio = 1.0
        else:
            chasing = player_data[player_data["innings_number"] == 2]
            if len(chasing) >= 2 and mean_runs > 0:
                chasing_avg = chasing["innings_runs"].mean()
                situation_ratio = chasing_avg / mean_runs
            else:
                situation_ratio = 1.0
        
        # 6. Efficiency (strike_rate * avg / 100)
        total_runs = player_data["innings_runs"].sum()
        total_balls = player_data["balls_faced"].sum()
        strike_rate = (total_runs * 100.0 / total_balls) if total_balls > 0 else 0
        efficiency = strike_rate * mean_runs / 100.0
        
        results.append({
            "batter": batter,
            "format": fmt,
            "recent_performance": recent_avg,
            "consistency": consistency,
            "opposition_strength": opp_weighted,
            "venue_performance": venue_score,
            "match_situation": situation_ratio,
            "efficiency": efficiency,
            "total_innings": player_info["total_innings"],
            "recent_innings_count": len(recent),
        })
    
    if not results:
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    
    # Min-max normalize each component within format.  Mixing formats in one
    # pipeline invocation must not let (for example) Test scoring ranges alter
    # T20 form scores.
    for col in ["recent_performance", "consistency", "opposition_strength",
                "venue_performance", "match_situation", "efficiency"]:
        df[f"{col}_normalized"] = _minmax_by_format(df, col)
    
    # Compute weighted form score
    df["form_score"] = np.round(
        df["recent_performance_normalized"] * WEIGHTS["recent_performance"] +
        df["consistency_normalized"] * WEIGHTS["consistency"] +
        df["opposition_strength_normalized"] * WEIGHTS["opposition_strength"] +
        df["venue_performance_normalized"] * WEIGHTS["venue_performance"] +
        df["match_situation_normalized"] * WEIGHTS["match_situation"] +
        df["efficiency_normalized"] * WEIGHTS["efficiency"],
        2
    )
    
    # Rename for DB
    df = df.rename(columns={
        "batter": "player_name",
        "recent_performance_normalized": "recent_performance_component",
        "consistency_normalized": "consistency_component",
        "opposition_strength_normalized": "opposition_strength_component",
        "venue_performance_normalized": "venue_performance_component",
        "match_situation_normalized": "match_situation_component",
        "efficiency_normalized": "efficiency_component",
    })
    
    logger.info(f"  Computed form scores for {len(df)} player-format combinations")
    return df


# ============================================================
# Team Performance
# ============================================================

def compute_team_performance(deliveries_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute team performance metrics from delivery data.
    
    Supports both limited-overs (T20/T20I/ODI) and Test cricket.
    For Test cricket, aggregates all innings per team per match.
    """
    logger.info("Computing team performance metrics...")
    
    # Per-innings totals
    innings_totals = deliveries_df.groupby(["match_id", "innings_number"]).agg(
        batting_team=("batting_team", "first"),
        total_runs=("runs_total", "sum"),
        format=("format", "first"),
    ).reset_index()
    
    # Match outcome. A tie, draw or no-result is not a loss for either team.
    outcome_aggregations = {"winner": ("winner", "first")}
    if "result_type" in deliveries_df.columns:
        outcome_aggregations["result_type"] = ("result_type", "first")
    match_winner = deliveries_df.groupby("match_id").agg(
        **outcome_aggregations,
    ).reset_index()
    if "result_type" not in match_winner.columns:
        match_winner["result_type"] = np.where(
            match_winner["winner"].fillna("") != "", "win", "no_result"
        )
    
    # Per-team aggregate score (sum across all innings in a match)
    team_match_scores = innings_totals.groupby(["match_id", "batting_team"]).agg(
        total_score=("total_runs", "sum"),
        innings_count=("innings_number", "count"),
        format=("format", "first"),
    ).reset_index().rename(columns={"batting_team": "team"})
    
    team_perf_raw = team_match_scores.merge(match_winner, on="match_id", how="left")
    team_perf_raw["won"] = team_perf_raw["winner"] == team_perf_raw["team"]
    normalized_result = _normalized_values(team_perf_raw, "result_type")
    team_perf_raw["lost"] = (
        (normalized_result == "win")
        & (team_perf_raw["winner"].fillna("") != "")
        & ~team_perf_raw["won"]
    )
    team_perf_raw["tied"] = normalized_result == "tie"
    team_perf_raw["no_result"] = normalized_result.isin(
        {"draw", "no result", "abandoned"}
    )
    
    # Aggregate by team and format
    team_perf = team_perf_raw.groupby(["team", "format"]).agg(
        matches=("match_id", "nunique"),
        wins=("won", "sum"),
        losses=("lost", "sum"),
        ties=("tied", "sum"),
        no_results=("no_result", "sum"),
        avg_batting_score=("total_score", "mean"),
    ).reset_index()
    team_perf["win_rate"] = np.round(team_perf["wins"] * 100.0 / team_perf["matches"].clip(lower=1), 2)
    
    # First/second innings averages (meaningful for limited-overs)
    first_innings_avg = innings_totals[innings_totals["innings_number"] == 1].groupby(
        ["batting_team", "format"]
    ).agg(avg_first_innings_score=("total_runs", "mean")).reset_index().rename(columns={"batting_team": "team"})
    
    second_innings_avg = innings_totals[innings_totals["innings_number"] == 2].groupby(
        ["batting_team", "format"]
    ).agg(avg_second_innings_score=("total_runs", "mean")).reset_index().rename(columns={"batting_team": "team"})
    
    team_perf = team_perf.merge(first_innings_avg, on=["team", "format"], how="left")
    team_perf = team_perf.merge(second_innings_avg, on=["team", "format"], how="left")
    
    # Chasing vs defending (meaningful for limited-overs)
    second_innings_teams = innings_totals[
        (innings_totals["innings_number"] == 2) & (innings_totals["format"] != "Test")
    ][["match_id", "format", "batting_team"]].rename(
        columns={"batting_team": "chasing_team"}
    )
    first_innings_teams = innings_totals[
        (innings_totals["innings_number"] == 1) & (innings_totals["format"] != "Test")
    ][["match_id", "format", "batting_team"]].rename(columns={"batting_team": "defending_team"})
    match_chasing = match_winner.merge(second_innings_teams, on="match_id", how="left")
    match_chasing = match_chasing.merge(first_innings_teams, on=["match_id", "format"], how="left")
    match_chasing = match_chasing[match_chasing["winner"].fillna("") != ""].copy()
    match_chasing["is_chasing_win"] = match_chasing["winner"] == match_chasing["chasing_team"]

    chasing = match_chasing.groupby(["chasing_team", "format"]).agg(
        chasing_attempts=("match_id", "count"),
        chasing_wins=("is_chasing_win", "sum"),
    ).reset_index().rename(columns={"chasing_team": "team"})
    match_chasing["is_defending_win"] = match_chasing["winner"] == match_chasing["defending_team"]
    defending = match_chasing.groupby(["defending_team", "format"]).agg(
        defending_attempts=("match_id", "count"),
        defending_wins=("is_defending_win", "sum"),
    ).reset_index().rename(columns={"defending_team": "team"})

    team_perf = team_perf.merge(chasing, on=["team", "format"], how="left")
    team_perf = team_perf.merge(defending, on=["team", "format"], how="left")
    team_perf["chasing_win_pct"] = np.where(
        team_perf["chasing_attempts"].fillna(0) > 0,
        np.round(team_perf["chasing_wins"] * 100.0 / team_perf["chasing_attempts"], 2),
        np.nan,
    )
    team_perf["defending_win_pct"] = np.where(
        team_perf["defending_attempts"].fillna(0) > 0,
        np.round(team_perf["defending_wins"] * 100.0 / team_perf["defending_attempts"], 2),
        np.nan,
    )
    
    # Phase stats — format-aware
    phase_data = deliveries_df.copy()
    phase_data["phase"] = phase_data.apply(
        lambda r: _classify_phase_format_aware(r["over_number"], r["format"]), axis=1
    )
    
    batting_phase = phase_data.groupby(["batting_team", "format", "phase"]).agg(
        runs=("runs_total", "sum"),
        matches=("match_id", "nunique"),
    ).reset_index()
    batting_phase["avg_runs_per_match"] = np.round(batting_phase["runs"] / batting_phase["matches"].clip(lower=1), 2)
    
    for phase in ["powerplay", "middle", "death"]:
        phase_rows = batting_phase[batting_phase["phase"] == phase][["batting_team", "format", "avg_runs_per_match"]]
        phase_rows = phase_rows.rename(columns={"batting_team": "team", "avg_runs_per_match": f"avg_{phase}_score"})
        team_perf = team_perf.merge(phase_rows, on=["team", "format"], how="left")
        team_perf[f"avg_{phase}_score"] = team_perf[f"avg_{phase}_score"].fillna(0)
    
    # Bowling strength
    phase_data["legal_ball"] = _is_legal_ball(phase_data).astype(int)
    phase_data["bowler_runs"] = _bowler_runs(phase_data)
    team_bowling = phase_data.groupby(["bowling_team", "format"]).agg(
        total_balls=("legal_ball", "sum"),
        runs_conceded=("bowler_runs", "sum"),
    ).reset_index()
    team_bowling["avg_economy"] = np.where(
        team_bowling["total_balls"] > 0,
        np.round(team_bowling["runs_conceded"] * 6.0 / team_bowling["total_balls"], 2), 0
    )
    team_bowling = team_bowling.rename(columns={"bowling_team": "team"})
    team_perf = team_perf.merge(team_bowling[["team", "format", "avg_economy"]], on=["team", "format"], how="left")
    
    # Strength scores
    if len(team_perf) > 0:
        team_perf["batting_strength_score"] = _minmax_by_format(
            team_perf, "avg_batting_score"
        )
        team_perf["bowling_strength_score"] = _minmax_by_format(
            team_perf, "avg_economy", invert=True
        )
        team_perf["overall_strength_score"] = np.round(
            0.35 * team_perf["batting_strength_score"].clip(0, 100) +
            0.35 * team_perf["bowling_strength_score"].clip(0, 100) +
            0.30 * team_perf["win_rate"].clip(0, 100), 2
        )
    
    team_perf["period"] = "career"
    team_perf = team_perf.rename(columns={"team": "team_name"})
    
    logger.info(f"  Computed team performance for {len(team_perf)} team-format combinations")
    return team_perf


# ============================================================
# Venue Statistics
# ============================================================

def compute_venue_stats(deliveries_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute venue statistics from delivery data.
    """
    logger.info("Computing venue statistics...")
    
    # First innings scores
    first_innings = deliveries_df[deliveries_df["innings_number"] == 1].groupby(
        ["venue", "format", "match_id"]
    ).agg(total_runs=("runs_total", "sum")).reset_index()
    
    venue_first = first_innings.groupby(["venue", "format"]).agg(
        avg_first_innings_score=("total_runs", "mean"),
        highest_total=("total_runs", "max"),
        lowest_total=("total_runs", "min"),
    ).reset_index()
    
    venue_first["avg_first_innings_score"] = np.round(venue_first["avg_first_innings_score"], 2)
    
    # Second innings scores
    second_innings = deliveries_df[deliveries_df["innings_number"] == 2].groupby(
        ["venue", "format", "match_id"]
    ).agg(total_runs=("runs_total", "sum")).reset_index()
    
    venue_second = second_innings.groupby(["venue", "format"]).agg(
        avg_second_innings_score=("total_runs", "mean"),
    ).reset_index()
    
    venue_second["avg_second_innings_score"] = np.round(venue_second["avg_second_innings_score"], 2)
    
    # Total matches
    match_counts = deliveries_df.groupby(["venue", "format"]).agg(
        total_matches=("match_id", "nunique"),
    ).reset_index()
    
    # Chase stats
    match_results = deliveries_df.groupby(["match_id"]).agg(
        venue=("venue", "first"),
        format=("format", "first"),
        innings_number=("innings_number", "max"),
    ).reset_index()
    
    # Phase scoring — format-aware
    phase_data = deliveries_df.copy()
    phase_data["phase"] = phase_data.apply(
        lambda r: _classify_phase_format_aware(r["over_number"], r["format"]), axis=1
    )
    
    venue_phase = phase_data.groupby(["venue", "format", "match_id", "phase"]).agg(
        runs=("runs_total", "sum"),
    ).reset_index()
    
    venue_phase_avg = venue_phase.groupby(["venue", "format", "phase"]).agg(
        avg_runs=("runs", "mean"),
    ).reset_index()
    
    # Pivot
    powerplay = venue_phase_avg[venue_phase_avg["phase"] == "powerplay"][["venue", "format", "avg_runs"]].rename(
        columns={"avg_runs": "avg_powerplay_runs"}
    )
    middle = venue_phase_avg[venue_phase_avg["phase"] == "middle"][["venue", "format", "avg_runs"]].rename(
        columns={"avg_runs": "avg_middle_overs_runs"}
    )
    death = venue_phase_avg[venue_phase_avg["phase"] == "death"][["venue", "format", "avg_runs"]].rename(
        columns={"avg_runs": "avg_death_overs_runs"}
    )
    
    # Boundary frequency
    boundary_data = deliveries_df.copy()
    boundary_data["ball_faced"] = _is_ball_faced(boundary_data).astype(int)
    boundary_data["is_four"] = _is_boundary(boundary_data, 4).astype(int)
    boundary_data["is_six"] = _is_boundary(boundary_data, 6).astype(int)
    venue_boundaries = boundary_data.groupby(["venue", "format"]).agg(
        total_balls=("ball_faced", "sum"),
        fours=("is_four", "sum"),
        sixes=("is_six", "sum"),
    ).reset_index()
    
    venue_boundaries["boundary_frequency"] = np.round(
        (venue_boundaries["fours"] + venue_boundaries["sixes"]) * 100.0 / venue_boundaries["total_balls"].clip(lower=1),
        2
    )
    
    # Combine all
    result = match_counts.merge(venue_first, on=["venue", "format"], how="left")
    result = result.merge(venue_second, on=["venue", "format"], how="left")
    result = result.merge(powerplay, on=["venue", "format"], how="left")
    result = result.merge(middle, on=["venue", "format"], how="left")
    result = result.merge(death, on=["venue", "format"], how="left")
    result = result.merge(
        venue_boundaries[["venue", "format", "fours", "sixes", "boundary_frequency"]],
        on=["venue", "format"], how="left"
    )
    
    # Compute chasing/defending win percentages from match data
    match_winners = deliveries_df.groupby("match_id").agg(
        venue=("venue", "first"),
        format=("format", "first"),
        batting_team_1=("batting_team", "first"),
        winner=("winner", "first"),
    ).reset_index()
    
    # For 2nd innings, the batting team is the chasing team
    second_innings = deliveries_df[
        (deliveries_df["innings_number"] == 2) & (deliveries_df["format"] != "Test")
    ].groupby("match_id").agg(
        chasing_team=("batting_team", "first"),
    ).reset_index()
    
    match_winners = match_winners.merge(second_innings, on="match_id", how="inner")
    match_winners = match_winners[match_winners["winner"].fillna("") != ""].copy()
    match_winners["is_chasing_win"] = match_winners["winner"] == match_winners["chasing_team"]
    
    venue_chase = match_winners.groupby(["venue", "format"]).agg(
        total_matches=('match_id', 'count'),
        chasing_wins=('is_chasing_win', 'sum'),
    ).reset_index()
    
    venue_chase["chasing_win_pct"] = np.round(
        venue_chase["chasing_wins"] * 100.0 / venue_chase["total_matches"].clip(lower=1), 1
    )
    venue_chase["defending_win_pct"] = np.round(100 - venue_chase["chasing_win_pct"], 1)
    
    result = result.merge(
        venue_chase[["venue", "format", "chasing_win_pct", "defending_win_pct"]],
        on=["venue", "format"], how="left"
    )
    # Delivery rows currently have no reliable bowling-style dimension. Null
    # values are preferable to publishing a fabricated fixed 55/45 split.
    result["pace_wickets_pct"] = np.nan
    result["spin_wickets_pct"] = np.nan
    
    # Fill NaN
    for col in ["avg_first_innings_score", "avg_second_innings_score", "avg_powerplay_runs",
                "avg_middle_overs_runs", "avg_death_overs_runs", "fours", "sixes"]:
        if col in result.columns:
            result[col] = result[col].fillna(0)
    
    result = result.rename(columns={"venue": "venue_name"})
    
    logger.info(f"  Computed venue stats for {len(result)} venue-format combinations")
    return result


# ============================================================
# Batter-Bowler Matchups
# ============================================================

def compute_matchups(deliveries_df: pd.DataFrame, min_balls: int = 10) -> pd.DataFrame:
    """
    Compute batter vs bowler matchup statistics.
    """
    logger.info("Computing batter-bowler matchups...")
    
    valid = deliveries_df[
        deliveries_df["batter"].notna() & 
        deliveries_df["bowler"].notna() &
        (deliveries_df["batter"] != "") &
        (deliveries_df["bowler"] != "")
    ].copy()
    valid["ball_faced"] = _is_ball_faced(valid).astype(int)
    valid["is_dot_ball"] = (
        valid["ball_faced"].astype(bool)
        & (pd.to_numeric(valid["runs_total"], errors="coerce").fillna(0) == 0)
    ).astype(int)
    valid["is_four"] = _is_boundary(valid, 4).astype(int)
    valid["is_six"] = _is_boundary(valid, 6).astype(int)
    valid["is_boundary"] = valid["is_four"] + valid["is_six"]
    valid["is_dismissed"] = (
        _is_bowler_wicket(valid) & (valid["dismissed_player"] == valid["batter"])
    )
    
    grouped = valid.groupby(["batter", "bowler", "format"]).agg(
        total_balls=("ball_faced", "sum"),
        total_runs=("runs_batter", "sum"),
        total_wickets=("is_dismissed", "sum"),
        dot_balls=("is_dot_ball", "sum"),
        boundaries=("is_boundary", "sum"),
        sixes=("is_six", "sum"),
        matches=("match_id", "nunique"),
    ).reset_index()
    
    # Filter minimum balls
    grouped = grouped[grouped["total_balls"] >= min_balls]
    
    grouped["strike_rate"] = np.where(
        grouped["total_balls"] > 0,
        np.round(grouped["total_runs"] * 100.0 / grouped["total_balls"], 2),
        0.0
    )
    grouped["batting_average"] = np.where(
        grouped["total_wickets"] > 0,
        np.round(grouped["total_runs"] / grouped["total_wickets"], 2),
        np.nan
    )
    grouped["dot_ball_pct"] = np.where(
        grouped["total_balls"] > 0,
        np.round(grouped["dot_balls"] * 100.0 / grouped["total_balls"], 2),
        0.0
    )
    
    grouped = grouped.rename(columns={"batter": "batter_name", "bowler": "bowler_name"})
    
    logger.info(f"  Computed {len(grouped)} batter-bowler matchups (min {min_balls} balls)")
    return grouped
