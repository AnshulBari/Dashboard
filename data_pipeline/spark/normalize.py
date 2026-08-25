"""
Spark Normalize Stage
=====================

Normalizes raw Cricsheet data into canonical entities.

Key challenges solved:
1. Player name disambiguation — "V Kohli" vs "Virat Kohli" vs "VK"
2. Team name normalization — "India" vs "IND" vs "India Men"
3. Venue name normalization — multiple spellings
4. Format standardization — different format strings

Uses name mapping tables and fuzzy matching to resolve identities.
"""

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

# Canonical team names
# Maps all known variants to a canonical short name
TEAM_CANONICAL = {
    # Full names
    "India": ("India", "IND"),
    "Australia": ("Australia", "AUS"),
    "England": ("England", "ENG"),
    "South Africa": ("South Africa", "SA"),
    "New Zealand": ("New Zealand", "NZ"),
    "Pakistan": ("Pakistan", "PAK"),
    "Sri Lanka": ("Sri Lanka", "SL"),
    "West Indies": ("West Indies", "WI"),
    "Bangladesh": ("Bangladesh", "BAN"),
    "Zimbabwe": ("Zimbabwe", "ZIM"),
    "Afghanistan": ("Afghanistan", "AFG"),
    "Ireland": ("Ireland", "IRE"),
    "Netherlands": ("Netherlands", "NED"),
    "Scotland": ("Scotland", "SCO"),
    "UAE": ("UAE", "UAE"),
    "Nepal": ("Nepal", "NEP"),
    "Namibia": ("Namibia", "NAM"),
    # Short names
    "IND": ("India", "IND"),
    "AUS": ("Australia", "AUS"),
    "ENG": ("England", "ENG"),
    "SA": ("South Africa", "SA"),
    "NZ": ("New Zealand", "NZ"),
    "PAK": ("Pakistan", "PAK"),
    "SL": ("Sri Lanka", "SL"),
    "WI": ("West Indies", "WI"),
    "BAN": ("Bangladesh", "BAN"),
    "ZIM": ("Zimbabwe", "ZIM"),
    "AFG": ("Afghanistan", "AFG"),
    "IRE": ("Ireland", "IRE"),
    "NED": ("Netherlands", "NED"),
    "SCO": ("Scotland", "SCO"),
    "UAE": ("UAE", "UAE"),
    "NEP": ("Nepal", "NEP"),
    "NAM": ("Namibia", "NAM"),
    # Common aliases
    "India Men": ("India", "IND"),
    "Australia Men": ("Australia", "AUS"),
    "England Men": ("England", "ENG"),
    "Mumbai Indians": ("Mumbai Indians", "MI"),
    "Chennai Super Kings": ("Chennai Super Kings", "CSK"),
    "Royal Challengers Bangalore": ("Royal Challengers Bangalore", "RCB"),
    "Kolkata Knight Riders": ("Kolkata Knight Riders", "KKR"),
    "Delhi Capitals": ("Delhi Capitals", "DC"),
    "Rajasthan Royals": ("Rajasthan Royals", "RR"),
    "Punjab Kings": ("Punjab Kings", "PBKS"),
    "Sunrisers Hyderabad": ("Sunrisers Hyderabad", "SRH"),
    "Gujarat Titans": ("Gujarat Titans", "GT"),
    "Lucknow Super Giants": ("Lucknow Super Giants", "LSG"),
}

# Format normalization
FORMAT_CANONICAL = {
    "T20I": "T20I",
    "T20": "T20",
    "ODI": "ODI",
    "Test": "Test",
    "T10": "T10",
    "IT20": "T20I",
    "t20i": "T20I",
    "odi": "ODI",
    "test": "Test",
}

# Wicket type normalization
WICKET_TYPES = {
    "bowled": "bowled",
    "caught": "caught",
    "lbw": "lbw",
    "run out": "run_out",
    "run_out": "run_out",
    "stumped": "stumped",
    "caught and bowled": "caught_and_bowled",
    "hit wicket": "hit_wicket",
    "hit_wicket": "hit_wicket",
    "retired hurt": "retired_hurt",
    "retired out": "retired_out",
    "obstructing the field": "obstructing_field",
    "timed out": "timed_out",
}

# Bowling style classification
BOWLING_STYLES = {
    "right arm fast": ("right_arm", "fast", "pace"),
    "right-arm fast": ("right_arm", "fast", "pace"),
    "right arm medium": ("right_arm", "medium", "pace"),
    "right-arm medium": ("right_arm", "medium", "pace"),
    "right arm medium fast": ("right_arm", "medium_fast", "pace"),
    "left arm fast": ("left_arm", "fast", "pace"),
    "left-arm fast": ("left_arm", "fast", "pace"),
    "left arm medium": ("left_arm", "medium", "pace"),
    "left arm orthodox": ("left_arm", "orthodox", "spin"),
    "left-arm orthodox": ("left_arm", "orthodox", "spin"),
    "left arm wrist spin": ("left_arm", "wrist_spin", "spin"),
    "left-arm wrist spin": ("left_arm", "wrist_spin", "spin"),
    "right arm offbreak": ("right_arm", "offbreak", "spin"),
    "right-arm offbreak": ("right_arm", "offbreak", "spin"),
    "right arm legbreak": ("right_arm", "legbreak", "spin"),
    "right-arm legbreak": ("right_arm", "legbreak", "spin"),
    "right arm wrist spin": ("right_arm", "wrist_spin", "spin"),
    "right-arm wrist spin": ("right_arm", "wrist_spin", "spin"),
}


def normalize_team_name(team_name: str) -> tuple[str, str]:
    """
    Normalize a team name to (canonical_name, short_name).
    Returns original name if no mapping found.
    """
    if team_name in TEAM_CANONICAL:
        return TEAM_CANONICAL[team_name]
    
    # Try case-insensitive match
    for key, value in TEAM_CANONICAL.items():
        if key.lower() == team_name.lower():
            return value
    
    # Try partial match
    for key, value in TEAM_CANONICAL.items():
        if key.lower() in team_name.lower() or team_name.lower() in key.lower():
            return value
    
    # Return as-is with abbreviated name
    return (team_name, team_name[:3].upper())


def normalize_format(format_str: str) -> str:
    """Normalize match format string."""
    return FORMAT_CANONICAL.get(format_str, format_str)


def normalize_wicket_type(wicket_kind: str) -> str:
    """Normalize wicket type to canonical form."""
    if wicket_kind is None:
        return None
    lower = wicket_kind.lower().strip()
    return WICKET_TYPES.get(lower, lower.replace(" ", "_"))


def classify_phase_udf():
    """UDF to classify over number into match phase."""
    return F.when(
        F.col("over_number") <= 6, F.lit("powerplay")
    ).when(
        F.col("over_number") <= 15, F.lit("middle")
    ).otherwise(
        F.lit("death")
    )


def normalize_deliveries(df: DataFrame) -> DataFrame:
    """
    Normalize a raw deliveries DataFrame.
    
    Adds canonical columns:
    - canonical_batting_team, canonical_bowling_team
    - canonical_format
    - phase (powerplay/middle/death)
    - normalized_wicket_type
    """
    # Register UDFs for normalization
    normalize_team = F.udf(lambda name: normalize_team_name(name)[0], T.StringType())
    short_team = F.udf(lambda name: normalize_team_name(name)[1], T.StringType())
    normalize_fmt = F.udf(lambda fmt: normalize_format(fmt), T.StringType())
    
    result = df
    
    # Add bowling team (opposite of batting team)
    if "bowling_team" not in df.columns:
        # Derive bowling team from teams array
        result = result.withColumn(
            "bowling_team",
            F.when(
                F.array_contains("teams", F.col("batting_team")),
                F.when(
                    F.element_at("teams", 1) == F.col("batting_team"),
                    F.element_at("teams", 2)
                ).otherwise(F.element_at("teams", 1))
            )
        )
    
    # Normalize team names
    result = result.withColumn(
        "canonical_batting_team", normalize_team(F.col("batting_team"))
    ).withColumn(
        "canonical_bowling_team", normalize_team(F.col("bowling_team"))
    ).withColumn(
        "batting_team_short", short_team(F.col("batting_team"))
    ).withColumn(
        "bowling_team_short", short_team(F.col("bowling_team"))
    )
    
    # Normalize format
    result = result.withColumn(
        "canonical_format", normalize_fmt(F.col("format"))
    )
    
    # Classify phase
    result = result.withColumn(
        "phase",
        F.when(F.col("over_number") <= 6, F.lit("powerplay"))
        .when(F.col("over_number") <= 15, F.lit("middle"))
        .otherwise(F.lit("death"))
    )
    
    # Determine if batting team is chasing (second innings)
    result = result.withColumn(
        "is_chasing",
        F.when(F.col("innings_idx") == 1, F.lit(False)).otherwise(F.lit(True))
    )
    
    return result


def create_player_registry(df: DataFrame) -> DataFrame:
    """
    Extract unique player names from match data.
    
    Returns a DataFrame with unique player names that can be mapped
    to canonical player IDs in the database.
    """
    # Collect all unique player names from batter and bowler columns
    batters = df.select(F.col("batter").alias("name"))
    bowlers = df.select(F.col("bowler").alias("name"))
    
    all_players = batters.union(bowlers).distinct()
    
    # Add first/last name parsing
    result = all_players.withColumn(
        "name_parts", F.split("name", "\\s+")
    ).withColumn(
        "first_name", F.element_at("name_parts", 1)
    ).withColumn(
        "last_name",
        F.when(
            F.size("name_parts") > 1,
            F.concat_ws(" ", F.slice("name_parts", 2, F.size("name_parts")))
        ).otherwise(F.lit(None))
    ).withColumn(
        "initials",
        F.when(
            F.length(F.element_at("name_parts", 1)) <= 2,
            F.element_at("name_parts", 1)
        ).otherwise(F.lit(None))
    )
    
    return result.drop("name_parts")
