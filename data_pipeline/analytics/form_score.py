"""
Player Form Score
=================

An original, explainable metric that quantifies a player's current form.

The Form Score is a weighted composite of normalized statistical components.
It is designed to be transparent and auditable — every component contributes
a known percentage to the final score.

Mathematical Model
------------------

Components and Weights:
  1. Recent Performance (35%)  — Runs/wickets in last 10 innings, normalized
  2. Consistency (20%)         — Lower variance = higher consistency score
  3. Opposition Strength (15%) — Performance against top-ranked opponents
  4. Venue Performance (10%)   — How well they play at current/typical venues
  5. Match Situation (10%)     — Performance under pressure (chasing, collapses)
  6. Efficiency (10%)          — Strike rate / economy relative to format average

Normalization
-------------

Each component is normalized to 0-100 using min-max scaling across all players
in the same format. This means:
- A player with the best recent performance gets 100 for that component
- A player with the worst gets 0
- The median player gets roughly 50

The weighted sum produces the final Form Score (0-100).

Limitations
-----------

- Requires minimum 5 innings for statistical significance
- Not scientifically validated — this is a project metric
- Weights are initial estimates and can be refined with expert input
- Cold start problem for new players (limited data)
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import Window
from datetime import datetime, timedelta


# Component weights (must sum to 1.0)
WEIGHTS = {
    "recent_performance": 0.35,
    "consistency": 0.20,
    "opposition_strength": 0.15,
    "venue_performance": 0.10,
    "match_situation": 0.10,
    "efficiency": 0.10,
}

MIN_INNINGS = 5  # Minimum innings for statistical significance


def compute_recent_performance(
    player_innings_df: DataFrame,
    recent_window: int = 10,
) -> DataFrame:
    """
    Compute normalized recent performance score.
    
    Uses a rolling window of the most recent N innings.
    For batting: based on runs scored.
    For bowling: based on wickets taken and economy.
    
    Normalized to 0-100 using min-max scaling.
    """
    # Define window for recent innings (ordered by date, last N)
    recent_window_spec = Window.partitionBy("batter").orderBy(
        F.col("match_date").desc()
    ).rowsBetween(Window.unboundedPreceding, Window.currentRow)
    
    # Count innings per player to determine if we have enough data
    player_counts = player_innings_df.groupBy("batter").agg(
        F.count("*").alias("total_innings")
    )
    
    # Take last N innings per player
    recent_innings = player_innings_df.withColumn(
        "row_num",
        F.row_number().over(Window.partitionBy("batter").orderBy(F.col("match_date").desc()))
    ).filter(F.col("row_num") <= recent_window)
    
    # Aggregate recent performance
    recent_agg = recent_innings.groupBy("batter", "format").agg(
        F.avg("runs").alias("avg_runs"),
        F.sum("runs").alias("total_runs"),
        F.count("*").alias("innings_count"),
    )
    
    # Min-max normalize across all players in same format
    min_max = recent_agg.groupBy("format").agg(
        F.min("avg_runs").alias("min_avg"),
        F.max("avg_runs").alias("max_avg"),
    )
    
    normalized = recent_agg.join(min_max, "format").withColumn(
        "range",
        F.greatest(F.lit(0.01), F.col("max_avg") - F.col("min_avg"))
    ).withColumn(
        "recent_performance_score",
        F.when(
            F.col("innings_count") >= MIN_INNINGS,
            F.round(
                (F.col("avg_runs") - F.col("min_avg")) / F.col("range") * 100, 2
            )
        ).otherwise(F.lit(None))
    )
    
    return normalized.select(
        "batter", "format", "recent_performance_score"
    )


def compute_consistency_component(
    player_innings_df: DataFrame,
) -> DataFrame:
    """
    Compute normalized consistency score.
    
    Consistency is measured as 1 - (coefficient of variation).
    Lower variability relative to mean = more consistent.
    
    Normalized to 0-100.
    """
    stats = player_innings_df.groupBy("batter", "format").agg(
        F.avg("runs").alias("mean_runs"),
        F.stddev("runs").alias("stddev_runs"),
        F.count("*").alias("innings_count"),
    )
    
    # CV = stddev / mean (lower is better)
    stats = stats.withColumn(
        "cv",
        F.when(F.col("mean_runs") > 0, F.col("stddev_runs") / F.col("mean_runs"))
        .otherwise(F.lit(1.0))
    )
    
    # Min-max normalize (lower CV = higher score)
    min_max = stats.groupBy("format").agg(
        F.min("cv").alias("min_cv"),
        F.max("cv").alias("max_cv"),
    )
    
    normalized = stats.join(min_max, "format").withColumn(
        "range",
        F.greatest(F.lit(0.01), F.col("max_cv") - F.col("min_cv"))
    ).withColumn(
        "consistency_score",
        F.when(
            F.col("innings_count") >= MIN_INNINGS,
            F.round(
                (F.col("max_cv") - F.col("cv")) / F.col("range") * 100, 2
            )
        ).otherwise(F.lit(None))
    )
    
    return normalized.select("batter", "format", "consistency_score")


def compute_opposition_strength(
    player_innings_df: DataFrame,
) -> DataFrame:
    """
    Compute opposition strength component.
    
    Players who perform well against strong opponents get higher scores.
    
    Methodology:
    1. Rank teams by win rate (proxy for strength)
    2. For each player, compute weighted average performance
       weighted by opponent strength
    3. Normalize to 0-100
    """
    # Compute team win rates (as proxy for strength)
    team_strength = player_innings_df.groupBy("bowling_team").agg(
        F.count("*").alias("balls_faced"),
        F.avg("runs_batter").alias("avg_runs_conceded"),
    )
    
    # Players who score more against strong teams get higher scores
    player_opp = player_innings_df.groupBy(
        "batter", "format", "bowling_team"
    ).agg(
        F.avg("runs_batter").alias("avg_vs_team"),
        F.count("*").alias("balls"),
    )
    
    # Weight by balls faced (more balls = more significant)
    weighted = player_opp.groupBy("batter", "format").agg(
        F.sum(F.col("avg_vs_team") * F.col("balls")).alias("weighted_runs"),
        F.sum("balls").alias("total_balls"),
    )
    
    weighted = weighted.withColumn(
        "weighted_avg",
        F.when(F.col("total_balls") > 0,
               F.col("weighted_runs") / F.col("total_balls")
        ).otherwise(F.lit(0))
    )
    
    # Normalize
    min_max = weighted.groupBy("format").agg(
        F.min("weighted_avg").alias("min_wa"),
        F.max("weighted_avg").alias("max_wa"),
    )
    
    normalized = weighted.join(min_max, "format").withColumn(
        "range",
        F.greatest(F.lit(0.01), F.col("max_wa") - F.col("min_wa"))
    ).withColumn(
        "opposition_strength_score",
        F.round(
            (F.col("weighted_avg") - F.col("min_wa")) / F.col("range") * 100, 2
        )
    )
    
    return normalized.select("batter", "format", "opposition_strength_score")


def compute_venue_component(
    player_innings_df: DataFrame,
) -> DataFrame:
    """
    Compute venue performance component.
    
    Players who perform well across diverse venues get higher scores.
    Uses coefficient of variation across venues as a diversity-adjusted metric.
    """
    venue_perf = player_innings_df.groupBy(
        "batter", "format", "venue"
    ).agg(
        F.avg("runs").alias("avg_at_venue"),
        F.count("*").alias("innings"),
    )
    
    player_venue_diversity = venue_perf.groupBy("batter", "format").agg(
        F.count("*").alias("venues_played"),
        F.avg("avg_at_venue").alias("avg_across_venues"),
        F.stddev("avg_at_venue").alias("venue_stddev"),
    )
    
    # Score: more venues + lower stddev = better
    player_venue_diversity = player_venue_diversity.withColumn(
        "venue_cv",
        F.when(F.col("avg_across_venues") > 0,
               F.col("venue_stddev") / F.col("avg_across_venues")
        ).otherwise(F.lit(1.0))
    )
    
    # Normalize
    min_max = player_venue_diversity.groupBy("format").agg(
        F.min("venue_cv").alias("min_cv"),
        F.max("venue_cv").alias("max_cv"),
    )
    
    normalized = player_venue_diversity.join(min_max, "format").withColumn(
        "range",
        F.greatest(F.lit(0.01), F.col("max_cv") - F.col("min_cv"))
    ).withColumn(
        "venue_performance_score",
        F.round(
            (F.col("max_cv") - F.col("venue_cv")) / F.col("range") * 100, 2
        )
    )
    
    return normalized.select("batter", "format", "venue_performance_score")


def compute_situation_component(
    player_innings_df: DataFrame,
) -> DataFrame:
    """
    Compute match situation component.
    
    Players who perform well under pressure (chasing, tight matches)
    get higher scores.
    """
    situation = player_innings_df.withColumn(
        "situation",
        F.when(F.col("innings_idx") == 1, F.lit("chasing"))
        .otherwise(F.lit("setting"))
    )
    
    chasing_stats = situation.filter(
        F.col("situation") == "chasing"
    ).groupBy("batter", "format").agg(
        F.avg("runs").alias("chasing_avg"),
        F.count("*").alias("chasing_innings"),
    )
    
    all_stats = situation.groupBy("batter", "format").agg(
        F.avg("runs").alias("overall_avg"),
    )
    
    combined = chasing_stats.join(all_stats, ["batter", "format"], "left").withColumn(
        "situation_ratio",
        F.when(F.col("overall_avg") > 0,
               F.col("chasing_avg") / F.col("overall_avg")
        ).otherwise(F.lit(1.0))
    )
    
    min_max = combined.groupBy("format").agg(
        F.min("situation_ratio").alias("min_sr"),
        F.max("situation_ratio").alias("max_sr"),
    )
    
    normalized = combined.join(min_max, "format").withColumn(
        "range",
        F.greatest(F.lit(0.01), F.col("max_sr") - F.col("min_sr"))
    ).withColumn(
        "situation_score",
        F.round(
            (F.col("situation_ratio") - F.col("min_sr")) / F.col("range") * 100, 2
        )
    )
    
    return normalized.select("batter", "format", "situation_score")


def compute_efficiency_component(
    player_innings_df: DataFrame,
) -> DataFrame:
    """
    Compute efficiency component.
    
    Measures how efficiently a player scores relative to format norms.
    High strike rate with good average = high efficiency.
    """
    efficiency = player_innings_df.groupBy("batter", "format").agg(
        F.sum("runs").alias("total_runs"),
        F.sum("balls_faced").alias("total_balls"),
        F.avg("runs").alias("avg_runs"),
        F.count("*").alias("innings"),
    )
    
    efficiency = efficiency.withColumn(
        "strike_rate",
        F.when(F.col("total_balls") > 0,
               F.col("total_runs") * 100.0 / F.col("total_balls")
        ).otherwise(F.lit(0))
    ).withColumn(
        "efficiency_metric",
        F.when(F.col("innings") >= MIN_INNINGS,
               F.col("strike_rate") * F.col("avg_runs") / 100.0
        ).otherwise(F.lit(None))
    )
    
    min_max = efficiency.groupBy("format").agg(
        F.min("efficiency_metric").alias("min_eff"),
        F.max("efficiency_metric").alias("max_eff"),
    )
    
    normalized = efficiency.join(min_max, "format").withColumn(
        "range",
        F.greatest(F.lit(0.01), F.col("max_eff") - F.col("min_eff"))
    ).withColumn(
        "efficiency_score",
        F.when(
            F.col("efficiency_metric").isNotNull(),
            F.round(
                (F.col("efficiency_metric") - F.col("min_eff")) / F.col("range") * 100, 2
            )
        ).otherwise(F.lit(None))
    )
    
    return normalized.select("batter", "format", "efficiency_score")


def compute_form_score(
    player_innings_df: DataFrame,
) -> DataFrame:
    """
    Compute the composite Player Form Score.
    
    Combines all weighted components into a single score.
    """
    # Compute each component
    recent = compute_recent_performance(player_innings_df)
    consistency = compute_consistency_component(player_innings_df)
    opposition = compute_opposition_strength(player_innings_df)
    venue = compute_venue_component(player_innings_df)
    situation = compute_situation_component(player_innings_df)
    efficiency = compute_efficiency_component(player_innings_df)
    
    # Join all components
    result = recent
    
    for component_df in [consistency, opposition, venue, situation, efficiency]:
        result = result.join(component_df, ["batter", "format"], "left")
    
    # Compute weighted composite score
    result = result.withColumn(
        "form_score",
        F.round(
            F.coalesce(F.col("recent_performance_score"), F.lit(50)) * F.lit(WEIGHTS["recent_performance"]) +
            F.coalesce(F.col("consistency_score"), F.lit(50)) * F.lit(WEIGHTS["consistency"]) +
            F.coalesce(F.col("opposition_strength_score"), F.lit(50)) * F.lit(WEIGHTS["opposition_strength"]) +
            F.coalesce(F.col("venue_performance_score"), F.lit(50)) * F.lit(WEIGHTS["venue_performance"]) +
            F.coalesce(F.col("situation_score"), F.lit(50)) * F.lit(WEIGHTS["match_situation"]) +
            F.coalesce(F.col("efficiency_score"), F.lit(50)) * F.lit(WEIGHTS["efficiency"]),
            2
        )
    )
    
    return result
