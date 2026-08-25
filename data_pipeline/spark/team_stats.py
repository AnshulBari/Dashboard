"""
Team Statistics Aggregation
===========================

Aggregates team-level performance metrics.

Computes:
- Win rates per format/period
- Batting strength indicators
- Bowling strength indicators
- Phase-wise team performance
- Chasing vs defending performance
- Overall strength scores
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def compute_team_match_results(
    matches_df: DataFrame,
) -> DataFrame:
    """
    Compute match results for each team.
    
    Joins match data with innings results to determine
    which team won and by what margin.
    """
    # Get innings totals
    innings_totals = matches_df.groupBy(
        "match_id", "innings_idx", "batting_team"
    ).agg(
        F.sum("total_runs").alias("innings_total")
    )
    
    # Split into first and second innings
    first = innings_totals.filter(F.col("innings_idx") == 0).select(
        "match_id",
        F.col("batting_team").alias("team_a"),
        F.col("innings_total").alias("score_a"),
    )
    
    second = innings_totals.filter(F.col("innings_idx") == 1).select(
        "match_id",
        F.col("batting_team").alias("team_b"),
        F.col("innings_total").alias("score_b"),
    )
    
    results = first.join(second, "match_id", "inner")
    
    # Determine winner
    results = results.withColumn(
        "winner",
        F.when(F.col("score_a") > F.col("score_b"), F.col("team_a"))
        .when(F.col("score_b") > F.col("score_a"), F.col("team_b"))
        .otherwise(F.lit(None))
    ).withColumn(
        "margin",
        F.abs(F.col("score_a") - F.col("score_b"))
    )
    
    return results


def compute_team_performance(
    team_results_df: DataFrame,
) -> DataFrame:
    """
    Compute team performance metrics.
    
    For each team, calculates:
    - Win rate
    - Average score (batting)
    - Average score conceded (bowling)
    - Performance by phase
    """
    # Explode to get per-team perspective
    team_a = team_results_df.select(
        F.col("team_a").alias("team"),
        F.col("score_a").alias("batting_score"),
        F.col("score_b").alias("bowling_score"),
        F.col("winner"),
        F.lit(True).alias("is_first_innings"),
    )
    
    team_b = team_results_df.select(
        F.col("team_b").alias("team"),
        F.col("score_b").alias("batting_score"),
        F.col("score_a").alias("bowling_score"),
        F.col("winner"),
        F.lit(False).alias("is_first_innings"),
    )
    
    all_team_results = team_a.union(team_b)
    
    team_perf = all_team_results.groupBy("team").agg(
        F.count("*").alias("matches"),
        F.sum(F.when(F.col("winner") == F.col("team"), 1).otherwise(0)).alias("wins"),
        F.avg("batting_score").alias("avg_batting_score"),
        F.avg("bowling_score").alias("avg_bowling_score"),
        F.avg(F.when(F.col("is_first_innings"), F.col("batting_score"))).alias("avg_first_innings"),
        F.avg(F.when(~F.col("is_first_innings"), F.col("batting_score"))).alias("avg_second_innings"),
    )
    
    team_perf = team_perf.withColumn(
        "win_rate",
        F.when(F.col("matches") > 0,
               F.round(F.col("wins") * 100.0 / F.col("matches"), 2)
        ).otherwise(F.lit(0.0))
    )
    
    return team_perf


def compute_team_bowling_stats(
    deliveries_df: DataFrame,
) -> DataFrame:
    """
    Compute team-level bowling statistics.
    
    Aggregates all bowlers' stats to team level.
    """
    team_bowling = deliveries_df.groupBy(
        "bowling_team", "format"
    ).agg(
        F.count("*").alias("total_balls"),
        F.sum("runs_total").alias("runs_conceded"),
        F.sum(F.when(F.col("is_wicket"), 1).otherwise(0)).alias("total_wickets"),
        F.sum(F.when(F.col("runs_batter") == 0, 1).otherwise(0)).alias("dots"),
        F.sum(F.when(F.col("runs_batter") >= 4, 1).otherwise(0)).alias("boundaries"),
        F.countDistinct("match_id").alias("matches"),
    )
    
    team_bowling = team_bowling.withColumn(
        "economy",
        F.when(F.col("total_balls") > 0,
               F.round(F.col("runs_conceded") * 6.0 / F.col("total_balls"), 2)
        ).otherwise(F.lit(999.99))
    ).withColumn(
        "dot_ball_pct",
        F.when(F.col("total_balls") > 0,
               F.round(F.col("dots") * 100.0 / F.col("total_balls"), 2)
        ).otherwise(F.lit(0.0))
    )
    
    return team_bowling


def compute_team_phase_stats(
    deliveries_df: DataFrame,
) -> DataFrame:
    """
    Compute team performance by match phase.
    
    Returns batting and bowling metrics for each phase.
    """
    phase_df = deliveries_df.withColumn(
        "phase",
        F.when(F.col("over_number") <= 6, F.lit("powerplay"))
        .when(F.col("over_number") <= 15, F.lit("middle"))
        .otherwise(F.lit("death"))
    )
    
    # Batting phase stats
    batting_phase = phase_df.groupBy(
        "batting_team", "format", "phase"
    ).agg(
        F.count("*").alias("balls"),
        F.sum("runs_batter").alias("runs"),
        F.sum(F.when(F.col("is_wicket"), 1).otherwise(0)).alias("wickets_lost"),
        F.countDistinct("match_id").alias("matches"),
    )
    
    batting_phase = batting_phase.withColumn(
        "avg_runs_per_match",
        F.when(F.col("matches") > 0,
               F.round(F.col("runs") / F.col("matches"), 2)
        ).otherwise(F.lit(0.0))
    )
    
    # Bowling phase stats
    bowling_phase = phase_df.groupBy(
        "bowling_team", "format", "phase"
    ).agg(
        F.count("*").alias("balls"),
        F.sum("runs_total").alias("runs_conceded"),
        F.sum(F.when(F.col("is_wicket"), 1).otherwise(0)).alias("wickets_taken"),
        F.countDistinct("match_id").alias("matches"),
    )
    
    bowling_phase = bowling_phase.withColumn(
        "avg_economy",
        F.when(F.col("balls") > 0,
               F.round(F.col("runs_conceded") * 6.0 / F.col("balls"), 2)
        ).otherwise(F.lit(999.99))
    )
    
    return batting_phase, bowling_phase


def compute_team_strength_score(
    team_perf_df: DataFrame,
    team_bowling_df: DataFrame,
) -> DataFrame:
    """
    Compute an overall team strength score.
    
    Formula (simplified initial model):
    
    Strength = 0.35 * Batting Score + 0.35 * Bowling Score + 0.30 * Win Score
    
    Where:
    - Batting Score = normalized avg_total_score (0-100)
    - Bowling Score = 100 - normalized economy (0-100)
    - Win Score = win_rate (0-100)
    
    All inputs are normalized to 0-100 scale.
    """
    # Join batting and bowling stats
    combined = team_perf_df.join(
        team_bowling_df.select("team", "economy", "dot_ball_pct"),
        "team",
        "left"
    )
    
    # Normalize scores (min-max scaling within the dataset)
    score_range = combined.agg(
        F.min("avg_batting_score").alias("min_bat"),
        F.max("avg_batting_score").alias("max_bat"),
        F.min("economy").alias("min_econ"),
        F.max("economy").alias("max_econ"),
    ).collect()[0]
    
    min_bat = score_range["min_bat"] or 100
    max_bat = score_range["max_bat"] or 300
    min_econ = score_range["min_econ"] or 4
    max_econ = score_range["max_econ"] or 12
    
    bat_range = max_bat - min_bat if max_bat != min_bat else 1
    econ_range = max_econ - min_econ if max_econ != min_econ else 1
    
    combined = combined.withColumn(
        "batting_strength",
        F.round(
            (F.col("avg_batting_score") - F.lit(min_bat)) / F.lit(bat_range) * 100,
            2
        )
    ).withColumn(
        "bowling_strength",
        F.round(
            (F.lit(max_econ) - F.col("economy")) / F.lit(econ_range) * 100,
            2
        )
    ).withColumn(
        "overall_strength",
        F.round(
            F.lit(0.35) * F.greatest(F.lit(0), F.least(F.lit(100), F.col("batting_strength"))) +
            F.lit(0.35) * F.greatest(F.lit(0), F.least(F.lit(100), F.col("bowling_strength"))) +
            F.lit(0.30) * F.greatest(F.lit(0), F.least(F.lit(100), F.col("win_rate"))),
            2
        )
    )
    
    return combined.select(
        "team", "matches", "wins", "win_rate",
        "avg_batting_score", "avg_bowling_score",
        "economy", "batting_strength", "bowling_strength", "overall_strength"
    )
