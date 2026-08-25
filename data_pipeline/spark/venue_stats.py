"""
Venue Statistics Aggregation
============================

Computes per-venue analytics:

- Average scores (first/second innings)
- Chasing vs defending win rates
- Pace/spin wicket distribution
- Phase-wise scoring
- Boundary frequency
- Toss impact
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def compute_venue_match_stats(
    matches_df: DataFrame,
) -> DataFrame:
    """
    Compute per-venue match-level statistics.
    
    Returns aggregate metrics for each venue.
    """
    venue_stats = matches_df.groupBy(
        "venue", "format"
    ).agg(
        F.count("match_id").alias("total_matches"),
        F.avg("total_runs").alias("avg_total_score"),
        F.max("total_runs").alias("highest_total"),
        F.min("total_runs").alias("lowest_total"),
        F.countDistinct(F.col("batting_team")).alias("teams_played"),
    )
    
    return venue_stats


def compute_venue_innings_stats(
    innings_df: DataFrame,
) -> DataFrame:
    """
    Compute per-venue first vs second innings averages.
    """
    venue_innings = innings_df.groupBy(
        "venue", "format", "innings_idx"
    ).agg(
        F.count("match_id").alias("innings_count"),
        F.avg("total_runs").alias("avg_score"),
        F.avg("run_rate").alias("avg_run_rate"),
        F.stddev("total_runs").alias("score_stddev"),
    )
    
    return venue_innings


def compute_venue_chase_stats(
    match_results_df: DataFrame,
) -> DataFrame:
    """
    Compute chasing vs defending statistics for each venue.
    
    Returns win percentages for each scenario.
    """
    venue_chasing = match_results_df.groupBy("venue", "format").agg(
        F.count("match_id").alias("total_matches"),
        F.sum(F.when(F.col("chasing_team_wins"), 1).otherwise(0)).alias("chasing_wins"),
        F.sum(F.when(~F.col("chasing_team_wins"), 1).otherwise(0)).alias("defending_wins"),
    )
    
    venue_chasing = venue_chasing.withColumn(
        "chasing_win_pct",
        F.when(F.col("total_matches") > 0,
               F.round(F.col("chasing_wins") * 100.0 / F.col("total_matches"), 2)
        ).otherwise(F.lit(50.0))
    ).withColumn(
        "defending_win_pct",
        F.when(F.col("total_matches") > 0,
               F.round(F.col("defending_wins") * 100.0 / F.col("total_matches"), 2)
        ).otherwise(F.lit(50.0))
    )
    
    return venue_chasing


def compute_venue_phase_stats(
    deliveries_df: DataFrame,
) -> DataFrame:
    """
    Compute phase-wise scoring for each venue.
    """
    phase_df = deliveries_df.withColumn(
        "phase",
        F.when(F.col("over_number") <= 6, F.lit("powerplay"))
        .when(F.col("over_number") <= 15, F.lit("middle"))
        .otherwise(F.lit("death"))
    )
    
    venue_phase = phase_df.groupBy(
        "venue", "format", "phase"
    ).agg(
        F.count("*").alias("total_balls"),
        F.sum("runs_batter").alias("total_runs"),
        F.sum(F.when(F.col("runs_batter") >= 4, 1).otherwise(0)).alias("boundaries"),
        F.countDistinct("match_id").alias("matches"),
    )
    
    venue_phase = venue_phase.withColumn(
        "avg_runs_per_match",
        F.when(F.col("matches") > 0,
               F.round(F.col("total_runs") / F.col("matches"), 2)
        ).otherwise(F.lit(0.0))
    )
    
    return venue_phase


def compute_venue_wicket_stats(
    deliveries_df: DataFrame,
) -> DataFrame:
    """
    Compute pace vs spin wicket distribution per venue.
    
    Note: This requires bowling style data. In the initial implementation,
    we classify based on bowling type (pace/spin) from player data.
    """
    # For now, return placeholder stats
    # Full implementation requires joining with player bowling styles
    venue_wickets = deliveries_df.filter(
        F.col("is_wicket") & (~F.col("wicket_kind").isin("run_out", "retired_hurt"))
    ).groupBy(
        "venue", "format"
    ).agg(
        F.count("*").alias("total_wickets"),
        F.countDistinct("match_id").alias("matches"),
    )
    
    return venue_wickets


def compute_venue_boundary_stats(
    deliveries_df: DataFrame,
) -> DataFrame:
    """
    Compute boundary frequency for each venue.
    """
    venue_boundaries = deliveries_df.groupBy(
        "venue", "format"
    ).agg(
        F.count("*").alias("total_balls"),
        F.sum(F.when(F.col("runs_batter") == 4, 1).otherwise(0)).alias("fours"),
        F.sum(F.when(F.col("runs_batter") == 6, 1).otherwise(0)).alias("sixes"),
        F.countDistinct("match_id").alias("matches"),
    )
    
    venue_boundaries = venue_boundaries.withColumn(
        "fours_per_match",
        F.when(F.col("matches") > 0,
               F.round(F.col("fours") / F.col("matches"), 2)
        ).otherwise(F.lit(0.0))
    ).withColumn(
        "sixes_per_match",
        F.when(F.col("matches") > 0,
               F.round(F.col("sixes") / F.col("matches"), 2)
        ).otherwise(F.lit(0.0))
    ).withColumn(
        "boundary_frequency",
        F.when(F.col("total_balls") > 0,
               F.round((F.col("fours") + F.col("sixes")) * 100.0 / F.col("total_balls"), 2)
        ).otherwise(F.lit(0.0))
    )
    
    return venue_boundaries


def compute_venue_toss_stats(
    matches_df: DataFrame,
) -> DataFrame:
    """
    Compute toss impact statistics per venue.
    
    Shows whether batting or fielding first has an advantage
    at each venue.
    """
    venue_toss = matches_df.groupBy(
        "venue", "format"
    ).agg(
        F.count("match_id").alias("total_matches"),
        F.sum(F.when(
            (F.col("toss_decision") == "bat") &
            (F.col("toss_winner") == F.col("winner")),
            1
        ).otherwise(0)).alias("toss_bat_wins"),
        F.sum(F.when(
            (F.col("toss_decision") == "field") &
            (F.col("toss_winner") == F.col("winner")),
            1
        ).otherwise(0)).alias("toss_field_wins"),
    )
    
    venue_toss = venue_toss.withColumn(
        "toss_bat_win_pct",
        F.when(F.col("total_matches") > 0,
               F.round(F.col("toss_bat_wins") * 100.0 / F.col("total_matches"), 2)
        ).otherwise(F.lit(50.0))
    ).withColumn(
        "toss_field_win_pct",
        F.when(F.col("total_matches") > 0,
               F.round(F.col("toss_field_wins") * 100.0 / F.col("total_matches"), 2)
        ).otherwise(F.lit(50.0))
    )
    
    return venue_toss


def compute_comprehensive_venue_stats(
    deliveries_df: DataFrame,
    matches_df: DataFrame,
) -> DataFrame:
    """
    Compute comprehensive venue statistics by combining all metrics.
    
    This is the main entry point for venue analytics.
    """
    # First innings average
    first_innings = deliveries_df.filter(
        F.col("innings_idx") == 0
    ).groupBy("venue", "format").agg(
        F.sum("total_runs").alias("total_first_innings_runs"),
        F.countDistinct("match_id").alias("matches"),
    ).withColumn(
        "avg_first_innings_score",
        F.round(F.col("total_first_innings_runs") / F.col("matches"), 2)
    )
    
    # Second innings average
    second_innings = deliveries_df.filter(
        F.col("innings_idx") == 1
    ).groupBy("venue", "format").agg(
        F.sum("total_runs").alias("total_second_innings_runs"),
        F.countDistinct("match_id").alias("matches"),
    ).withColumn(
        "avg_second_innings_score",
        F.round(F.col("total_second_innings_runs") / F.col("matches"), 2)
    )
    
    # Phase-wise stats
    phase_df = deliveries_df.withColumn(
        "phase",
        F.when(F.col("over_number") <= 6, F.lit("powerplay"))
        .when(F.col("over_number") <= 15, F.lit("middle"))
        .otherwise(F.lit("death"))
    )
    
    phase_stats = phase_df.groupBy(
        "venue", "format", "phase"
    ).agg(
        F.sum("runs_batter").alias("phase_runs"),
        F.countDistinct("match_id").alias("matches"),
    )
    
    # Pivot phases
    powerplay = phase_stats.filter(F.col("phase") == "powerplay").select(
        "venue", "format",
        F.round(F.col("phase_runs") / F.col("matches"), 2).alias("avg_powerplay_runs"),
    )
    middle = phase_stats.filter(F.col("phase") == "middle").select(
        "venue", "format",
        F.round(F.col("phase_runs") / F.col("matches"), 2).alias("avg_middle_runs"),
    )
    death = phase_stats.filter(F.col("phase") == "death").select(
        "venue", "format",
        F.round(F.col("phase_runs") / F.col("matches"), 2).alias("avg_death_runs"),
    )
    
    # Combine all
    result = first_innings.select(
        "venue", "format", "matches", "avg_first_innings_score"
    ).join(
        second_innings.select("venue", "format", "avg_second_innings_score"),
        ["venue", "format"],
        "left"
    ).join(
        powerplay.select("venue", "format", "avg_powerplay_runs"),
        ["venue", "format"],
        "left"
    ).join(
        middle.select("venue", "format", "avg_middle_runs"),
        ["venue", "format"],
        "left"
    ).join(
        death.select("venue", "format", "avg_death_runs"),
        ["venue", "format"],
        "left"
    )
    
    return result
