"""
Matchup Statistics
==================

Computes batter vs bowler matchup data including:
- Direct matchups (specific player pairs)
- Contextual matchups (batter vs bowling type)
- Batter vs pace/spin breakdown
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def compute_direct_matchups(deliveries_df: DataFrame) -> DataFrame:
    """
    Compute head-to-head batter vs bowler matchups.
    
    Only includes matchups with minimum 10 balls for statistical significance.
    """
    matchups = deliveries_df.groupBy(
        "batter", "bowler", "format"
    ).agg(
        F.count("*").alias("total_balls"),
        F.sum("runs_batter").alias("total_runs"),
        F.sum(F.when(F.col("is_wicket"), 1).otherwise(0)).alias("total_wickets"),
        F.sum(F.when(F.col("runs_batter") == 0, 1).otherwise(0)).alias("dot_balls"),
        F.sum(F.when(F.col("runs_batter") >= 4, 1).otherwise(0)).alias("boundaries"),
        F.sum(F.when(F.col("runs_batter") == 6, 1).otherwise(0)).alias("sixes"),
        F.countDistinct("match_id").alias("matches"),
    )
    
    # Filter for minimum balls
    matchups = matchups.filter(F.col("total_balls") >= 10)
    
    # Compute derived stats
    matchups = matchups.withColumn(
        "strike_rate",
        F.when(F.col("total_balls") > 0,
               F.round(F.col("total_runs") * 100.0 / F.col("total_balls"), 2)
        ).otherwise(F.lit(0.0))
    ).withColumn(
        "batting_average",
        F.when(F.col("total_wickets") > 0,
               F.round(F.col("total_runs") / F.col("total_wickets"), 2)
        ).otherwise(F.lit(None))
    ).withColumn(
        "dot_ball_pct",
        F.when(F.col("total_balls") > 0,
               F.round(F.col("dot_balls") * 100.0 / F.col("total_balls"), 2)
        ).otherwise(F.lit(0.0))
    ).withColumn(
        "boundary_pct",
        F.when(F.col("total_balls") > 0,
               F.round(F.col("boundaries") * 100.0 / F.col("total_balls"), 2)
        ).otherwise(F.lit(0.0))
    )
    
    return matchups


def compute_pace_spin_matchups(
    deliveries_df: DataFrame,
    player_df: DataFrame,
) -> DataFrame:
    """
    Compute batter performance vs pace and spin.
    
    Requires player bowling type classification.
    """
    # Join with player data to get bowling type
    bowler_types = player_df.select(
        F.col("canonical_name").alias("bowler_name"),
        F.col("bowling_type"),
    )
    
    enriched = deliveries_df.join(
        bowler_types,
        deliveries_df["bowler"] == bowler_types["bowler_name"],
        "left"
    )
    
    # Aggregate by bowling type
    pace_spin = enriched.groupBy(
        "batter", "format", "bowling_type"
    ).agg(
        F.count("*").alias("total_balls"),
        F.sum("runs_batter").alias("total_runs"),
        F.sum(F.when(F.col("is_wicket"), 1).otherwise(0)).alias("wickets"),
        F.countDistinct("match_id").alias("matches"),
    ).filter(F.col("bowling_type").isNotNull())
    
    pace_spin = pace_spin.withColumn(
        "strike_rate",
        F.when(F.col("total_balls") > 0,
               F.round(F.col("total_runs") * 100.0 / F.col("total_balls"), 2)
        ).otherwise(F.lit(0.0))
    )
    
    return pace_spin


def compute_arm_matchups(
    deliveries_df: DataFrame,
    player_df: DataFrame,
) -> DataFrame:
    """
    Compute batter performance vs left-arm and right-arm bowling.
    """
    bowler_arms = player_df.select(
        F.col("canonical_name").alias("bowler_name"),
        F.col("bowling_style"),
    ).withColumn(
        "bowling_arm",
        F.when(F.col("bowling_style").startswith("left"), F.lit("left"))
        .otherwise(F.lit("right"))
    )
    
    enriched = deliveries_df.join(
        bowler_arms,
        deliveries_df["bowler"] == bowler_arms["bowler_name"],
        "left"
    )
    
    arm_stats = enriched.groupBy(
        "batter", "format", "bowling_arm"
    ).agg(
        F.count("*").alias("total_balls"),
        F.sum("runs_batter").alias("total_runs"),
        F.sum(F.when(F.col("is_wicket"), 1).otherwise(0)).alias("wickets"),
        F.countDistinct("match_id").alias("matches"),
    ).filter(F.col("bowling_arm").isNotNull())
    
    arm_stats = arm_stats.withColumn(
        "strike_rate",
        F.when(F.col("total_balls") > 0,
               F.round(F.col("total_runs") * 100.0 / F.col("total_balls"), 2)
        ).otherwise(F.lit(0.0))
    )
    
    return arm_stats
