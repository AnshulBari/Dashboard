"""
Spark Transform Stage
=====================

Transforms normalized delivery data into structured analytical datasets.

Adds computed columns:
- Cumulative runs/wickets per innings
- Phase classification (powerplay, middle, death)
- Match result flags
- Partnership boundaries
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import Window


def add_cumulative_stats(df: DataFrame) -> DataFrame:
    """
    Add cumulative runs and wickets per innings.
    
    These are essential for win probability and situational analytics.
    Uses window functions to compute running totals ordered by over/ball.
    """
    # Window ordered by over number and ball in over
    innings_window = (
        Window.partitionBy("innings_id")
        .orderBy("over_number", "ball_in_over")
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    )
    
    result = df.withColumn(
        "cumulative_runs",
        F.sum("total_runs").over(innings_window)
    ).withColumn(
        "cumulative_wickets",
        F.sum(F.when(F.col("is_wicket"), 1).otherwise(0)).over(innings_window)
    )
    
    return result


def add_match_context(df: DataFrame, matches_df: DataFrame) -> DataFrame:
    """
    Join delivery data with match-level context.
    
    Adds:
    - Target score (for second innings)
    - Match result
    - Required run rate
    """
    # Compute first innings total for target
    first_innings = (
        matches_df
        .filter(F.col("innings_idx") == 0)
        .groupBy("match_id")
        .agg(
            F.sum("total_runs").alias("first_innings_total")
        )
    )
    
    # Join with deliveries
    result = df.join(
        first_innings,
        df["match_id"] == first_innings["match_id"],
        "left"
    ).drop(first_innings["match_id"])
    
    # Add target for second innings deliveries
    result = result.withColumn(
        "target",
        F.when(
            F.col("innings_idx") == 1,
            F.col("first_innings_total") + 1
        ).otherwise(F.lit(None))
    )
    
    return result


def compute_match_results(innings_df: DataFrame) -> DataFrame:
    """
    Compute match results from innings-level data.
    
    Returns a DataFrame with one row per match and the result.
    """
    # Aggregate innings totals
    innings_totals = innings_df.groupBy(
        "match_id", "innings_idx", "batting_team"
    ).agg(
        F.sum("total_runs").alias("innings_total"),
        F.max("cumulative_wickets").alias("innings_wickets"),
        F.max("over_number").alias("last_over"),
    )
    
    # Pivot to get team A and team B scores
    team_a_scores = (
        innings_totals
        .filter(F.col("innings_idx") == 0)
        .select(
            "match_id",
            F.col("batting_team").alias("team_a"),
            F.col("innings_total").alias("team_a_score"),
            F.col("innings_wickets").alias("team_a_wickets"),
        )
    )
    
    team_b_scores = (
        innings_totals
        .filter(F.col("innings_idx") == 1)
        .select(
            "match_id",
            F.col("batting_team").alias("team_b"),
            F.col("innings_total").alias("team_b_score"),
            F.col("innings_wickets").alias("team_b_wickets"),
        )
    )
    
    results = team_a_scores.join(team_b_scores, "match_id", "inner")
    
    # Determine winner
    results = results.withColumn(
        "winner",
        F.when(F.col("team_a_score") > F.col("team_b_score"), F.col("team_a"))
        .when(F.col("team_b_score") > F.col("team_a_score"), F.col("team_b"))
        .otherwise(F.lit("tie"))
    ).withColumn(
        "win_margin",
        F.when(
            F.col("winner") == F.col("team_a"),
            F.col("team_a_score") - F.col("team_b_score")
        ).when(
            F.col("winner") == F.col("team_b"),
            F.col("team_b_score") - F.col("team_a_score")
        ).otherwise(F.lit(0))
    ).withColumn(
        "win_type",
        F.when(
            F.col("winner").isNotNull() & (F.col("winner") != "tie"),
            F.lit("runs")
        ).otherwise(F.lit("tie"))
    )
    
    return results


def add_phase_stats(df: DataFrame) -> DataFrame:
    """
    Compute per-phase aggregates for innings.
    
    Phases:
    - Powerplay: overs 1-6
    - Middle: overs 7-15
    - Death: overs 16-20
    """
    phase_df = df.withColumn(
        "phase",
        F.when(F.col("over_number") <= 6, F.lit("powerplay"))
        .when(F.col("over_number") <= 15, F.lit("middle"))
        .otherwise(F.lit("death"))
    )
    
    phase_stats = phase_df.groupBy(
        "match_id", "innings_id", "batting_team", "phase"
    ).agg(
        F.sum("total_runs").alias("phase_runs"),
        F.count("*").alias("phase_deliveries"),
        F.sum(F.when(F.col("is_wicket"), 1).otherwise(0)).alias("phase_wickets"),
        F.sum("runs_batter").alias("phase_runs_bat"),
        F.sum(F.when(F.col("runs_batter") >= 4, 1).otherwise(0)).alias("phase_boundaries"),
        F.sum(F.when(F.col("runs_batter") == 0, 1).otherwise(0)).alias("phase_dots"),
    )
    
    return phase_stats


def compute_player_innings_stats(deliveries_df: DataFrame) -> DataFrame:
    """
    Compute per-player per-innings batting statistics.
    
    This is the foundation for all player analytics.
    """
    batting_df = deliveries_df.groupBy(
        "match_id", "innings_id", "batter", "batting_team", "bowling_team"
    ).agg(
        F.count("*").alias("balls_faced"),
        F.sum("runs_batter").alias("runs"),
        F.sum("runs_total").alias("total_runs_with_extras"),
        F.sum(F.when(F.col("is_wicket") & (F.col("wicket_player") == F.col("batter")), 1).otherwise(0)).alias("is_out"),
        F.sum(F.when(F.col("runs_batter") == 0, 1).otherwise(0)).alias("dot_balls"),
        F.sum(F.when(F.col("runs_batter") == 4, 1).otherwise(0)).alias("fours"),
        F.sum(F.when(F.col("runs_batter") == 6, 1).otherwise(0)).alias("sixes"),
        F.first("format").alias("format"),
        F.first("innings_idx").alias("innings_number"),
    )
    
    # Compute derived stats
    batting_df = batting_df.withColumn(
        "strike_rate",
        F.when(F.col("balls_faced") > 0,
               F.round(F.col("runs") * 100.0 / F.col("balls_faced"), 2)
        ).otherwise(F.lit(0))
    ).withColumn(
        "average",
        F.when(F.col("is_out") > 0,
               F.round(F.col("runs") / F.col("is_out"), 2)
        ).otherwise(F.col("runs").cast("double"))
    ).withColumn(
        "boundary_pct",
        F.when(F.col("balls_faced") > 0,
               F.round(F.col("fours") + F.col("sixes") * 100.0 / F.col("balls_faced"), 2)
        ).otherwise(F.lit(0))
    ).withColumn(
        "dot_ball_pct",
        F.when(F.col("balls_faced") > 0,
               F.round(F.col("dot_balls") * 100.0 / F.col("balls_faced"), 2)
        ).otherwise(F.lit(0))
    )
    
    return batting_df


def compute_bowler_innings_stats(deliveries_df: DataFrame) -> DataFrame:
    """
    Compute per-bowler per-innings bowling statistics.
    
    Handles extras carefully — wide and no-ball deliveries count
    as bowling balls but the runs don't count as bowler's runs.
    """
    bowling_df = deliveries_df.filter(
        # Exclude wide-only deliveries from bowling stats
        ~((F.col("extra_type") == "wide") & (F.col("runs_batter") == 0))
    ).groupBy(
        "match_id", "innings_id", "bowler", "bowling_team", "batting_team"
    ).agg(
        F.count("*").alias("balls_bowled"),
        F.sum("runs_total").alias("runs_conceded"),
        F.sum("runs_extras").alias("extras_conceded"),
        F.sum(F.when(F.col("is_wicket"), 1).otherwise(0)).alias("wickets"),
        F.sum(F.when(F.col("runs_batter") == 0, 1).otherwise(0)).alias("dot_balls"),
        F.sum(F.when(F.col("runs_batter") >= 4, 1).otherwise(0)).alias("boundaries_conceded"),
        F.first("format").alias("format"),
        F.first("innings_idx").alias("innings_number"),
    )
    
    # Compute derived stats
    bowling_df = bowling_df.withColumn(
        "overs",
        F.floor(F.col("balls_bowled") / 6) + (F.col("balls_bowled") % 6) / 10.0
    ).withColumn(
        "economy",
        F.when(F.col("balls_bowled") > 0,
               F.round(F.col("runs_conceded") * 6.0 / F.col("balls_bowled"), 2)
        ).otherwise(F.lit(999.99))
    ).withColumn(
        "strike_rate",
        F.when(F.col("wickets") > 0,
               F.round(F.col("balls_bowled") / F.col("wickets"), 2)
        ).otherwise(F.lit(999.99))
    ).withColumn(
        "bowling_average",
        F.when(F.col("wickets") > 0,
               F.round(F.col("runs_conceded") / F.col("wickets"), 2)
        ).otherwise(F.lit(999.99))
    ).withColumn(
        "dot_ball_pct",
        F.when(F.col("balls_bowled") > 0,
               F.round(F.col("dot_balls") * 100.0 / F.col("balls_bowled"), 2)
        ).otherwise(F.lit(0))
    )
    
    return bowling_df


def compute_matchups(deliveries_df: DataFrame) -> DataFrame:
    """
    Compute batter vs bowler matchup statistics.
    
    Returns one row per unique batter-bowler combination per format.
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
    )
    
    # Only include matchups with minimum 10 balls (statistical significance)
    matchups = matchups.filter(F.col("total_balls") >= 10)
    
    # Compute derived stats
    matchups = matchups.withColumn(
        "strike_rate",
        F.when(F.col("total_balls") > 0,
               F.round(F.col("total_runs") * 100.0 / F.col("total_balls"), 2)
        ).otherwise(F.lit(0))
    ).withColumn(
        "batting_average",
        F.when(F.col("total_wickets") > 0,
               F.round(F.col("total_runs") / F.col("total_wickets"), 2)
        ).otherwise(F.lit(None))
    )
    
    return matchups
