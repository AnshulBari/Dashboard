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
    
    # Filter to valid batting deliveries (exclude wide-only extras)
    batting = deliveries_df[deliveries_df["batter"].notna() & (deliveries_df["batter"] != "")].copy()
    
    # Determine if each delivery resulted in the batter being out
    batting["is_dismissed"] = (
        batting["is_wicket"] & 
        (batting["dismissed_player"] == batting["batter"])
    )
    
    # Group by batter and format
    grouped = batting.groupby(["batter", "format"]).agg(
        matches=("match_id", "nunique"),
        innings=("innings_number", "count"),  # Approximate: each delivery row = part of innings
        runs=("runs_batter", "sum"),
        balls_faced=("ball_in_over", "count"),
        highest_score=("runs_batter", "max"),  # Will be replaced with per-innings max
        fours=("runs_batter", lambda x: (x == 4).sum()),
        sixes=("runs_batter", lambda x: (x == 6).sum()),
        dot_balls=("runs_batter", lambda x: (x == 0).sum()),
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
            balls=("ball_in_over", "count"),
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
            balls=("ball_in_over", "count"),
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
    
    # Exclude wide-only extras from ball count
    valid_balls = bowling[
        ~((bowling["extra_type"] == "wide") & (bowling["runs_batter"] == 0))
    ]
    
    grouped = valid_balls.groupby(["bowler", "format"]).agg(
        matches=("match_id", "nunique"),
        balls_bowled=("ball_in_over", "count"),
        runs_conceded=("runs_total", "sum"),
        wickets=("is_wicket", "sum"),
        dot_balls=("runs_batter", lambda x: (x == 0).sum()),
        boundaries_conceded=("runs_batter", lambda x: (x >= 4).sum()),
    ).reset_index()
    
    # Calculate innings count
    bowling_innings = valid_balls.groupby(["bowler", "format", "match_id"]).size().reset_index(name="balls")
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
    bowling_with_phase = valid_balls.copy()
    bowling_with_phase["phase"] = bowling_with_phase.apply(
        lambda r: _classify_phase_format_aware(r["over_number"], r["format"]), axis=1
    )
    
    for phase_name in ["powerplay", "middle", "death"]:
        phase_data = bowling_with_phase[bowling_with_phase["phase"] == phase_name]
        
        phase_agg = phase_data.groupby(["bowler", "format"]).agg(
            runs=("runs_total", "sum"),
            balls=("ball_in_over", "count"),
            wickets=("is_wicket", "sum"),
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
    
    # Get per-player per-innings batting scores
    innings_scores = deliveries_df[
        deliveries_df["batter"].notna() & (deliveries_df["batter"] != "")
    ].groupby(["batter", "format", "match_id", "innings_number"]).agg(
        innings_runs=("runs_batter", "sum"),
        balls_faced=("ball_in_over", "count"),
        match_date=("match_date", "first"),
        bowling_team=("bowling_team", "first"),
        venue=("venue", "first"),
    ).reset_index()
    
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
        opp_strength = player_data.groupby("bowling_team").agg(
            avg_runs=("innings_runs", "mean"),
            balls=("balls_faced", "sum"),
        )
        if opp_strength["balls"].sum() > 0:
            opp_weighted = (opp_strength["avg_runs"] * opp_strength["balls"]).sum() / opp_strength["balls"].sum()
        else:
            opp_weighted = 0
        
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
    
    # Min-max normalize each component within format
    for col in ["recent_performance", "consistency", "opposition_strength",
                "venue_performance", "match_situation", "efficiency"]:
        min_val = df[col].min()
        max_val = df[col].max()
        range_val = max(max_val - min_val, 0.01)
        df[f"{col}_normalized"] = np.round((df[col] - min_val) / range_val * 100, 2)
    
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
    """
    logger.info("Computing team performance metrics...")
    
    # Get match-level results
    match_results = deliveries_df.groupby(["match_id"]).agg(
        team_a=("team_a", "first"),
        team_b=("team_b", "first"),
        batting_team=("batting_team", "first"),
        batting_team_runs=("runs_total", "sum"),
        format=("format", "first"),
    ).reset_index()
    
    # Compute first and second innings totals
    innings_totals = deliveries_df.groupby(["match_id", "innings_number"]).agg(
        batting_team=("batting_team", "first"),
        total_runs=("runs_total", "sum"),
        total_wickets=("is_wicket", "sum"),
        format=("format", "first"),
    ).reset_index()
    
    first_innings = innings_totals[innings_totals["innings_number"] == 1][
        ["match_id", "batting_team", "total_runs", "format"]
    ].rename(columns={"batting_team": "team_a_name", "total_runs": "team_a_score"})
    
    second_innings = innings_totals[innings_totals["innings_number"] == 2][
        ["match_id", "batting_team", "total_runs", "format"]
    ].rename(columns={"batting_team": "team_b_name", "total_runs": "team_b_score"})
    
    results = first_innings.merge(second_innings, on=["match_id", "format"], how="inner")
    
    # Determine winner
    results["winner"] = np.where(
        results["team_a_score"] > results["team_b_score"],
        results["team_a_name"],
        np.where(
            results["team_b_score"] > results["team_a_score"],
            results["team_b_name"],
            None
        )
    )
    results["is_chasing_win"] = results["winner"] == results["team_b_name"]
    
    # Explode to per-team perspective
    team_a_perspective = results.rename(columns={
        "team_a_name": "team", "team_a_score": "batting_score",
        "team_b_score": "bowling_score",
    })[["match_id", "format", "team", "batting_score", "bowling_score", "winner", "is_chasing_win"]]
    team_a_perspective["is_first_innings"] = True
    
    team_b_perspective = results.rename(columns={
        "team_b_name": "team", "team_b_score": "batting_score",
        "team_a_score": "bowling_score",
    })[["match_id", "format", "team", "batting_score", "bowling_score", "winner", "is_chasing_win"]]
    team_b_perspective["is_first_innings"] = False
    
    all_perspectives = pd.concat([team_a_perspective, team_b_perspective], ignore_index=True)
    
    # Aggregate by team and format
    team_perf = all_perspectives.groupby(["team", "format"]).agg(
        matches=("match_id", "nunique"),
        wins=("winner", lambda x: (x == all_perspectives.loc[x.index, "team"]).sum()),
        avg_batting_score=("batting_score", "mean"),
        avg_bowling_score=("bowling_score", "mean"),
        avg_first_innings=("batting_score", lambda x: x[all_perspectives.loc[x.index, "is_first_innings"]].mean()),
        avg_second_innings=("batting_score", lambda x: x[~all_perspectives.loc[x.index, "is_first_innings"]].mean()),
    ).reset_index()
    
    team_perf["losses"] = team_perf["matches"] - team_perf["wins"]
    team_perf["win_rate"] = np.round(team_perf["wins"] * 100.0 / team_perf["matches"].clip(lower=1), 2)
    
    # Chasing vs defending
    chasing_wins = all_perspectives[
        all_perspectives["is_chasing_win"] & (all_perspectives["team"] == all_perspectives["winner"])
    ].groupby(["team", "format"]).size().reset_index(name="chasing_wins")
    
    chasing_attempts = all_perspectives[~all_perspectives["is_first_innings"]].groupby(
        ["team", "format"]
    ).size().reset_index(name="chasing_attempts")
    
    team_perf = team_perf.merge(chasing_wins, on=["team", "format"], how="left")
    team_perf = team_perf.merge(chasing_attempts, on=["team", "format"], how="left")
    team_perf["chasing_wins"] = team_perf["chasing_wins"].fillna(0)
    team_perf["chasing_attempts"] = team_perf["chasing_attempts"].fillna(0)
    team_perf["chasing_win_pct"] = np.round(
        team_perf["chasing_wins"] * 100.0 / team_perf["chasing_attempts"].clip(lower=1), 2
    )
    team_perf["defending_win_pct"] = np.round(100 - team_perf["chasing_win_pct"], 2)
    
    # Phase stats — format-aware
    phase_data = deliveries_df.copy()
    phase_data["phase"] = phase_data.apply(
        lambda r: _classify_phase_format_aware(r["over_number"], r["format"]), axis=1
    )
    
    batting_phase = phase_data.groupby(["batting_team", "format", "phase"]).agg(
        runs=("runs_batter", "sum"),
        balls=("ball_in_over", "count"),
        matches=("match_id", "nunique"),
    ).reset_index()
    
    batting_phase["avg_runs_per_match"] = np.round(batting_phase["runs"] / batting_phase["matches"].clip(lower=1), 2)
    
    # Pivot phases
    for phase in ["powerplay", "middle", "death"]:
        phase_rows = batting_phase[batting_phase["phase"] == phase][["batting_team", "format", "avg_runs_per_match"]]
        phase_rows = phase_rows.rename(columns={
            "batting_team": "team",
            "avg_runs_per_match": f"avg_{phase}_score"
        })
        team_perf = team_perf.merge(phase_rows, on=["team", "format"], how="left")
        team_perf[f"avg_{phase}_score"] = team_perf[f"avg_{phase}_score"].fillna(0)
    
    # Bowling strength
    team_bowling = phase_data.groupby(["bowling_team", "format"]).agg(
        total_balls=("ball_in_over", "count"),
        runs_conceded=("runs_total", "sum"),
    ).reset_index()
    team_bowling["avg_economy"] = np.where(
        team_bowling["total_balls"] > 0,
        np.round(team_bowling["runs_conceded"] * 6.0 / team_bowling["total_balls"], 2),
        0
    )
    team_bowling = team_bowling.rename(columns={"bowling_team": "team"})
    
    team_perf = team_perf.merge(
        team_bowling[["team", "format", "avg_economy"]],
        on=["team", "format"], how="left"
    )
    
    # Strength scores (min-max normalized)
    if len(team_perf) > 0:
        bat_min, bat_max = team_perf["avg_batting_score"].min(), team_perf["avg_batting_score"].max()
        econ_min, econ_max = team_perf["avg_economy"].min(), team_perf["avg_economy"].max()
        
        bat_range = max(bat_max - bat_min, 1)
        econ_range = max(econ_max - econ_min, 1)
        
        team_perf["batting_strength_score"] = np.round(
            (team_perf["avg_batting_score"] - bat_min) / bat_range * 100, 2
        )
        team_perf["bowling_strength_score"] = np.round(
            (econ_max - team_perf["avg_economy"]) / econ_range * 100, 2
        )
        team_perf["overall_strength_score"] = np.round(
            0.35 * team_perf["batting_strength_score"].clip(0, 100) +
            0.35 * team_perf["bowling_strength_score"].clip(0, 100) +
            0.30 * team_perf["win_rate"].clip(0, 100),
            2
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
        runs=("runs_batter", "sum"),
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
    venue_boundaries = deliveries_df.groupby(["venue", "format"]).agg(
        total_balls=("ball_in_over", "count"),
        fours=("runs_batter", lambda x: (x == 4).sum()),
        sixes=("runs_batter", lambda x: (x == 6).sum()),
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
    second_innings = deliveries_df[deliveries_df["innings_number"] == 2].groupby("match_id").agg(
        chasing_team=("batting_team", "first"),
    ).reset_index()
    
    match_winners = match_winners.merge(second_innings, on="match_id", how="left")
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
    result["chasing_win_pct"] = result["chasing_win_pct"].fillna(50.0)
    result["defending_win_pct"] = result["defending_win_pct"].fillna(50.0)
    
    # Pace/spin wicket percentages (approximate from bowling type)
    result["pace_wickets_pct"] = 55.0  # Placeholder — requires bowling type data
    result["spin_wickets_pct"] = 45.0
    
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
    
    valid["is_dismissed"] = (
        valid["is_wicket"] & 
        (valid["dismissed_player"] == valid["batter"])
    )
    
    grouped = valid.groupby(["batter", "bowler", "format"]).agg(
        total_balls=("ball_in_over", "count"),
        total_runs=("runs_batter", "sum"),
        total_wickets=("is_dismissed", "sum"),
        dot_balls=("runs_batter", lambda x: (x == 0).sum()),
        boundaries=("runs_batter", lambda x: (x >= 4).sum()),
        sixes=("runs_batter", lambda x: (x == 6).sum()),
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
