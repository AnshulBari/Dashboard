"""
Player Statistics Aggregation
=============================

Aggregates per-innings player stats into career and period-filtered summaries.

Computes:
- Career batting/bowling stats per format
- Recent form (last N matches/days)
- Phase-specific performance
- Situational performance (chasing, first innings)
- Consistency scores
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import Window
from datetime import datetime, timedelta


def compute_career_batting_stats(
    player_innings_df: DataFrame,
) -> DataFrame:
    """
    Aggregate career batting statistics per player per format.
    
    Uses window functions to compute running aggregates
    ordered by match date for incremental updates.
    """
    career = player_innings_df.groupBy(
        "batter", "format"
    ).agg(
        F.count("match_id").alias("matches"),
        F.count("innings_id").alias("innings"),
        F.sum(F.when(F.col("is_out") == 0, 1).otherwise(0)).alias("not_outs"),
        F.sum("runs").alias("runs"),
        F.max("runs").alias("highest_score"),
        F.sum("balls_faced").alias("balls_faced"),
        F.sum("fours").alias("fours"),
        F.sum("sixes").alias("sixes"),
        F.sum(F.when(F.col("runs") >= 50, 1).otherwise(0)).alias("fifties"),
        F.sum(F.when(F.col("runs") >= 100, 1).otherwise(0)).alias("hundreds"),
        F.first("batting_team").alias("primary_team"),
    )
    
    # Compute derived stats
    career = career.withColumn(
        "batting_average",
        F.when(F.col("innings") - F.col("not_outs") > 0,
               F.round(F.col("runs") / (F.col("innings") - F.col("not_outs")), 2)
        ).otherwise(F.col("runs").cast("double"))
    ).withColumn(
        "strike_rate",
        F.when(F.col("balls_faced") > 0,
               F.round(F.col("runs") * 100.0 / F.col("balls_faced"), 2)
        ).otherwise(F.lit(0.0))
    ).withColumn(
        "boundary_pct",
        F.when(F.col("balls_faced") > 0,
               F.round((F.col("fours") + F.col("sixes")) * 100.0 / F.col("balls_faced"), 2)
        ).otherwise(F.lit(0.0))
    )
    
    return career


def compute_recent_batting_stats(
    player_innings_df: DataFrame,
    days: int = 90,
    min_innings: int = 5,
) -> DataFrame:
    """
    Compute recent batting stats for a rolling window.
    
    Args:
        player_innings_df: Player per-innings DataFrame with match_date
        days: Lookback window in days
        min_innings: Minimum innings for statistical significance
    
    Returns:
        DataFrame with recent period batting stats
    """
    # Filter to recent matches
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent_df = player_innings_df.filter(F.col("match_date") >= cutoff_date)
    
    # Aggregate
    recent = recent_df.groupBy(
        "batter", "format"
    ).agg(
        F.count("match_id").alias("matches"),
        F.count("innings_id").alias("innings"),
        F.sum("runs").alias("runs"),
        F.sum("balls_faced").alias("balls_faced"),
        F.sum("fours").alias("fours"),
        F.sum("sixes").alias("sixes"),
        F.avg("runs").alias("avg_per_innings"),
        F.stddev("runs").alias("runs_stddev"),
        F.expr("percentile_approx(runs, 0.5)").alias("median_score"),
    )
    
    # Compute derived stats
    recent = recent.withColumn(
        "strike_rate",
        F.when(F.col("balls_faced") > 0,
               F.round(F.col("runs") * 100.0 / F.col("balls_faced"), 2)
        ).otherwise(F.lit(0.0))
    ).withColumn(
        "batting_average",
        F.when(
            (F.col("innings") - F.sum("not_outs")) > 0,
            F.round(F.col("runs") / (F.col("innings") - F.lit(0)), 2)
        ).otherwise(F.col("runs").cast("double"))
    )
    
    return recent


def compute_batting_by_phase(
    deliveries_df: DataFrame,
) -> DataFrame:
    """
    Compute batting stats broken down by match phase.
    
    Phases:
    - Powerplay: overs 1-6
    - Middle: overs 7-15
    - Death: overs 16-20
    """
    phase_df = deliveries_df.withColumn(
        "phase",
        F.when(F.col("over_number") <= 6, F.lit("powerplay"))
        .when(F.col("over_number") <= 15, F.lit("middle"))
        .otherwise(F.lit("death"))
    )
    
    phase_stats = phase_df.groupBy(
        "batter", "format", "phase"
    ).agg(
        F.count("*").alias("balls"),
        F.sum("runs_batter").alias("runs"),
        F.sum(F.when(F.col("is_wicket"), 1).otherwise(0)).alias("dismissals"),
        F.sum(F.when(F.col("runs_batter") >= 4, 1).otherwise(0)).alias("boundaries"),
        F.sum(F.when(F.col("runs_batter") == 0, 1).otherwise(0)).alias("dots"),
    )
    
    phase_stats = phase_stats.withColumn(
        "strike_rate",
        F.when(F.col("balls") > 0,
               F.round(F.col("runs") * 100.0 / F.col("balls"), 2)
        ).otherwise(F.lit(0.0))
    )
    
    return phase_stats


def compute_batting_by_situation(
    deliveries_df: DataFrame,
) -> DataFrame:
    """
    Compute batting stats by match situation.
    
    Situations:
    - Chasing (second innings)
    - Setting (first innings)
    """
    situation_df = deliveries_df.withColumn(
        "situation",
        F.when(F.col("innings_idx") == 0, F.lit("setting"))
        .otherwise(F.lit("chasing"))
    )
    
    situation_stats = situation_df.groupBy(
        "batter", "format", "situation"
    ).agg(
        F.count("match_id").alias("matches"),
        F.count("*").alias("balls"),
        F.sum("runs_batter").alias("runs"),
        F.sum(F.when(F.col("is_wicket"), 1).otherwise(0)).alias("dismissals"),
        F.avg("runs_batter").alias("avg_per_ball"),
    )
    
    situation_stats = situation_stats.withColumn(
        "strike_rate",
        F.when(F.col("balls") > 0,
               F.round(F.col("runs") * 100.0 / F.col("balls"), 2)
        ).otherwise(F.lit(0.0))
    ).withColumn(
        "average",
        F.when(F.col("dismissals") > 0,
               F.round(F.col("runs") / F.col("dismissals"), 2)
        ).otherwise(F.col("runs").cast("double"))
    )
    
    return situation_stats


def compute_career_bowling_stats(
    bowler_innings_df: DataFrame,
) -> DataFrame:
    """Aggregate career bowling statistics per player per format."""
    career = bowler_innings_df.groupBy(
        "bowler", "format"
    ).agg(
        F.count("match_id").alias("matches"),
        F.count("innings_id").alias("innings"),
        F.sum("balls_bowled").alias("balls_bowled"),
        F.sum("runs_conceded").alias("runs_conceded"),
        F.sum("wickets").alias("wickets"),
        F.sum("extras_conceded").alias("extras"),
        F.sum("dot_balls").alias("dot_balls"),
        F.sum("boundaries_conceded").alias("boundaries_conceded"),
        F.first("bowling_team").alias("primary_team"),
    )
    
    career = career.withColumn(
        "overs",
        F.floor(F.col("balls_bowled") / 6) + (F.col("balls_bowled") % 6) / 10.0
    ).withColumn(
        "economy",
        F.when(F.col("balls_bowled") > 0,
               F.round(F.col("runs_conceded") * 6.0 / F.col("balls_bowled"), 2)
        ).otherwise(F.lit(999.99))
    ).withColumn(
        "bowling_average",
        F.when(F.col("wickets") > 0,
               F.round(F.col("runs_conceded") / F.col("wickets"), 2)
        ).otherwise(F.lit(999.99))
    ).withColumn(
        "strike_rate",
        F.when(F.col("wickets") > 0,
               F.round(F.col("balls_bowled") / F.col("wickets"), 2)
        ).otherwise(F.lit(999.99))
    ).withColumn(
        "dot_ball_pct",
        F.when(F.col("balls_bowled") > 0,
               F.round(F.col("dot_balls") * 100.0 / F.col("balls_bowled"), 2)
        ).otherwise(F.lit(0.0))
    )
    
    return career


def compute_bowling_by_phase(
    deliveries_df: DataFrame,
) -> DataFrame:
    """Compute bowling stats broken down by match phase."""
    phase_df = deliveries_df.withColumn(
        "phase",
        F.when(F.col("over_number") <= 6, F.lit("powerplay"))
        .when(F.col("over_number") <= 15, F.lit("middle"))
        .otherwise(F.lit("death"))
    )
    
    phase_stats = phase_df.groupBy(
        "bowler", "format", "phase"
    ).agg(
        F.count("*").alias("balls"),
        F.sum("runs_total").alias("runs_conceded"),
        F.sum(F.when(F.col("is_wicket"), 1).otherwise(0)).alias("wickets"),
        F.sum(F.when(F.col("runs_batter") == 0, 1).otherwise(0)).alias("dots"),
    )
    
    phase_stats = phase_stats.withColumn(
        "economy",
        F.when(F.col("balls") > 0,
               F.round(F.col("runs_conceded") * 6.0 / F.col("balls"), 2)
        ).otherwise(F.lit(999.99))
    )
    
    return phase_stats


def compute_consistency_score(
    player_innings_df: DataFrame,
) -> DataFrame:
    """
    Compute a consistency score based on coefficient of variation.
    
    Lower coefficient of variation = more consistent.
    Score is normalized to 0-100 scale.
    
    Consistency = 100 * (1 - CV) where CV = stddev/mean
    Capped at 0 minimum.
    """
    stats = player_innings_df.groupBy(
        "batter", "format"
    ).agg(
        F.avg("runs").alias("mean_runs"),
        F.stddev("runs").alias("stddev_runs"),
        F.count("*").alias("sample_size"),
    )
    
    consistency = stats.withColumn(
        "cv",
        F.when(F.col("mean_runs") > 0,
               F.col("stddev_runs") / F.col("mean_runs")
        ).otherwise(F.lit(1.0))
    ).withColumn(
        "consistency_score",
        F.when(F.col("sample_size") >= 5,
               F.round(F.greatest(
                   F.lit(0.0),
                   (F.lit(1.0) - F.col("cv")) * F.lit(100)
               ), 2)
        ).otherwise(F.lit(None))
    )
    
    return consistency.select("batter", "format", "consistency_score", "sample_size")
