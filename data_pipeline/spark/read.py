"""
Spark Data Read Stage
=====================

Reads raw Cricsheet JSON match files into Spark DataFrames.

Cricsheet JSON format:
- Each file = one match
- Contains "info" (metadata) and "innings" (ball-by-ball data)
- Deliveries are nested: innings -> overs -> deliveries

We flatten this into structured DataFrames for downstream processing.
"""

import json
from pathlib import Path
from typing import Optional

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import types as T
from pyspark.sql import functions as F


# Schema for a single delivery (used for JSON parsing)
DELIVERY_SCHEMA = T.StructType([
    T.StructField("batter", T.StringType(), False),
    T.StructField("bowler", T.StringType(), False),
    T.StructField("non_striker", T.StringType(), True),
    T.StructField("runs", T.StructType([
        T.StructField("batter", T.IntegerType(), False),
        T.StructField("extras", T.IntegerType(), False),
        T.StructField("total", T.IntegerType(), False),
        T.StructField("non_boundary", T.BooleanType(), True),
    ]), False),
    T.StructField("extras", T.MapType(T.StringType(), T.IntegerType()), True),
    T.StructField("wickets", T.ArrayType(T.StructType([
        T.StructField("player_out", T.StringType(), False),
        T.StructField("kind", T.StringType(), False),
        T.StructField("fielders", T.ArrayType(
            T.StructType([T.StructField("name", T.StringType(), True)])
        ), True),
    ])), True),
    T.StructField("replaced_by", T.StringType(), True),
])


def read_match_json(spark: SparkSession, json_path: str | Path) -> dict:
    """
    Read a single Cricsheet match JSON file and return parsed data.
    
    This uses Python JSON parsing for single files (not Spark).
    For batch processing, use read_matches_batch().
    """
    with open(json_path, "r") as f:
        data = json.load(f)
    return data


def read_matches_batch(
    spark: SparkSession,
    data_dir: str | Path,
    format_type: Optional[str] = None,
) -> DataFrame:
    """
    Read multiple Cricsheet match files into a single Spark DataFrame.
    
    Each match becomes multiple rows (one per delivery).
    
    Args:
        spark: Active SparkSession
        data_dir: Directory containing JSON match files
        format_type: Optional filter for match format (t20i, odi, test, etc.)
    
    Returns:
        DataFrame with columns: match_info, innings_data
    """
    data_dir = Path(data_dir)
    
    # Find all JSON files
    if format_type:
        json_files = sorted(data_dir.glob("*.json"))
    else:
        json_files = sorted(data_dir.glob("*.json"))
    
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {data_dir}")
    
    # Read files as text, then parse
    file_paths = [str(f) for f in json_files]
    
    # Use spark.read.json for each file, then union
    # This handles nested JSON well
    dfs = []
    for path in file_paths:
        try:
            df = spark.read.json(path, multiLine=True).withColumn(
                "_source_file", F.input_file_name()
            )
            dfs.append(df)
        except Exception as e:
            # Some files may be malformed — log and skip
            print(f"Warning: Could not read {path}: {e}")
            continue
    
    if not dfs:
        raise ValueError(f"Could not read any files from {data_dir}")
    
    # Union all match DataFrames
    combined_df = dfs[0]
    for df in dfs[1:]:
        combined_df = combined_df.unionByName(df, allowMissingColumns=True)
    
    return combined_df


def flatten_match_data(spark: SparkSession, matches_df: DataFrame) -> DataFrame:
    """
    Flatten nested match DataFrames into delivery-level rows.
    
    Input: Raw JSON with nested innings/overs/deliveries
    Output: Flat DataFrame with one row per delivery
    
    This is the key transformation that makes the data processable
    with Spark DataFrame operations.
    """
    
    # Explode innings array
    innings_df = matches_df.select(
        F.col("_source_file"),
        F.col("meta"),
        F.col("info"),
        F.posexplode("innings").alias("innings_idx", "innings_data")
    )
    
    # Extract info fields
    info_df = innings_df.select(
        # Match metadata from info
        F.regexp_extract(F.col("_source_file"), r"([^/\\]+)\.json$", 1).alias("match_id"),
        F.element_at(F.col("info.dates"), 1).alias("match_date"),
        F.coalesce(
            F.get_json_object(F.to_json(F.col("meta")), "$.prepared_format"),
            F.col("info.match_type"),
        ).alias("format"),
        F.col("info.venue").alias("venue"),
        F.col("info.teams").alias("teams"),
        F.col("info.toss.winner").alias("toss_winner"),
        F.col("info.toss.decision").alias("toss_decision"),
        F.col("info.outcome.winner").alias("outcome_winner"),
        F.get_json_object(F.to_json(F.col("info.outcome")), "$.result").alias("outcome_result"),
        F.col("info.outcome.by").alias("outcome_by"),
        F.col("info.player_of_match").alias("player_of_match"),
        F.col("info.players").alias("players"),
        F.col("info.registry.people").alias("registry"),
        # Innings data
        F.col("innings_idx"),
        F.col("innings_data.team").alias("batting_team"),
        F.col("innings_data.overs").alias("overs"),
    )
    
    # Explode overs
    overs_df = info_df.select(
        "*",
        F.posexplode("overs").alias("over_idx", "over_data")
    )
    
    # Explode deliveries within each over
    deliveries_df = overs_df.select(
        # Match fields
        "match_id", "match_date", "format", "venue", "teams",
        "toss_winner", "toss_decision", "outcome_winner", "outcome_result", "outcome_by",
        "player_of_match", "players", "registry",
        "batting_team",
        "innings_idx",
        F.col("over_data.over").alias("over_number"),
        # Explode deliveries
        F.posexplode("over_data.deliveries").alias("ball_idx", "delivery"),
    )
    
    # Flatten delivery fields
    flat_df = deliveries_df.select(
        # Match context
        "match_id", "match_date", "format", "venue", "teams",
        "toss_winner", "toss_decision", "outcome_winner", "outcome_result", "outcome_by",
        "player_of_match", "players", "registry",
        "batting_team",
        "innings_idx",
        "over_number",
        "ball_idx",
        # Delivery details
        "delivery.batter",
        "delivery.bowler",
        "delivery.non_striker",
        F.col("delivery.runs.batter").alias("runs_batter"),
        F.col("delivery.runs.extras").alias("runs_extras"),
        F.col("delivery.runs.total").alias("runs_total"),
        F.coalesce(
            F.get_json_object(F.to_json(F.col("delivery.runs")), "$.non_boundary").cast("boolean"),
            F.lit(False),
        ).alias("non_boundary"),
        "delivery.extras",
        F.coalesce(F.get_json_object(F.to_json(F.col("delivery.extras")), "$.wides").cast("integer"), F.lit(0)).alias("extras_wides"),
        F.coalesce(F.get_json_object(F.to_json(F.col("delivery.extras")), "$.noballs").cast("integer"), F.lit(0)).alias("extras_noballs"),
        F.coalesce(F.get_json_object(F.to_json(F.col("delivery.extras")), "$.byes").cast("integer"), F.lit(0)).alias("extras_byes"),
        F.coalesce(F.get_json_object(F.to_json(F.col("delivery.extras")), "$.legbyes").cast("integer"), F.lit(0)).alias("extras_legbyes"),
        F.coalesce(F.get_json_object(F.to_json(F.col("delivery.extras")), "$.penalty").cast("integer"), F.lit(0)).alias("extras_penalty"),
        # Wicket info
        F.when(
            F.col("delivery.wickets").isNotNull() & (F.size("delivery.wickets") > 0),
            F.col("delivery.wickets")[0]["player_out"]
        ).alias("wicket_player"),
        F.when(
            F.col("delivery.wickets").isNotNull() & (F.size("delivery.wickets") > 0),
            F.col("delivery.wickets")[0]["kind"]
        ).alias("wicket_kind"),
        F.when(
            F.col("delivery.wickets").isNotNull() & (F.size("delivery.wickets") > 0),
            F.col("delivery.wickets")[0]["fielders"]
        ).alias("wicket_fielders"),
    )
    
    # Add computed fields
    result_df = flat_df.withColumn(
        "is_wicket",
        F.when(F.col("wicket_kind").isNotNull(), F.lit(True)).otherwise(F.lit(False))
    ).withColumn(
        "ball_in_over",
        F.col("ball_idx") + 1
    ).withColumn(
        "innings_id",
        F.concat_ws("-", F.col("match_id"), (F.col("innings_idx") + 1).cast("string"))
    ).withColumn(
        "current_over",
        F.col("over_number") + F.col("ball_idx") / 6.0
    ).withColumn(
        "extra_type",
        F.when(F.col("extras_wides") > 0, F.lit("wide"))
        .when(F.col("extras_noballs") > 0, F.lit("noball"))
        .when(F.col("extras_byes") > 0, F.lit("bye"))
        .when(F.col("extras_legbyes") > 0, F.lit("legbye"))
        .when(F.col("extras_penalty") > 0, F.lit("penalty"))
        .otherwise(F.lit(None))
    )
    
    return result_df


def get_delivery_count(spark: SparkSession, data_dir: str | Path) -> int:
    """Count total deliveries in a directory of match files."""
    data_dir = Path(data_dir)
    total = 0
    for json_file in data_dir.glob("*.json"):
        try:
            data = read_match_json(spark, json_file)
            for innings in data.get("innings", []):
                for over in innings.get("overs", []):
                    total += len(over.get("deliveries", []))
        except Exception:
            continue
    return total
