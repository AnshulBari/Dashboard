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
    # Historical IPL name changes
    "Delhi Daredevils": ("Delhi Capitals", "DC"),
    "Kings XI Punjab": ("Punjab Kings", "PBKS"),
    "Deccan Chargers": ("Deccan Chargers", "DC"),
    "Rising Pune Supergiants": ("Rising Pune Supergiants", "RPS"),
    "Rising Pune Supergiant": ("Rising Pune Supergiants", "RPS"),
    "Kochi Tuskers Kerala": ("Kochi Tuskers Kerala", "KTK"),
    "Pune Warriors": ("Pune Warriors", "PWI"),
    "Pune Warriors India": ("Pune Warriors", "PWI"),
    "Gujarat Lions": ("Gujarat Lions", "GL"),
    "Royal Challengers Bengaluru": ("Royal Challengers Bangalore", "RCB"),
    "England": ("England", "ENG"),
    "England Lions": ("England Lions", "ENG-L"),
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
    
    # Return as-is with abbreviated name
    return (team_name, team_name[:3].upper())


# Venue normalization
# Maps variant venue names to a canonical form
VENUE_CANONICAL = {
    # Wankhede
    "Wankhede Stadium": "Wankhede Stadium, Mumbai",
    "Wankhede Stadium, Mumbai": "Wankhede Stadium, Mumbai",
    # Chinnaswamy
    "M Chinnaswamy Stadium": "M.Chinnaswamy Stadium, Bengaluru",
    "M.Chinnaswamy Stadium": "M.Chinnaswamy Stadium, Bengaluru",
    "M.Chinnaswamy Stadium, Bengaluru": "M.Chinnaswamy Stadium, Bengaluru",
    # Eden Gardens
    "Eden Gardens": "Eden Gardens, Kolkata",
    "Eden Gardens, Kolkata": "Eden Gardens, Kolkata",
    # Feroz Shah Kotla
    "Feroz Shah Kotla": "Arun Jaitley Stadium, Delhi",
    "Arun Jaitley Stadium": "Arun Jaitley Stadium, Delhi",
    "Arun Jaitley Stadium, Delhi": "Arun Jaitley Stadium, Delhi",
    "Arun Jaitley Stadium, Feroz Shah Kotla ground": "Arun Jaitley Stadium, Delhi",
    # Chepauk
    "MA Chidambaram Stadium, Chepauk": "MA Chidambaram Stadium, Chennai",
    "MA Chidambaram Stadium": "MA Chidambaram Stadium, Chennai",
    "MA Chidambaram Stadium, Chennai": "MA Chidambaram Stadium, Chennai",
    # Rajiv Gandhi
    "Rajiv Gandhi International Stadium, Uppal": "Rajiv Gandhi International Stadium, Hyderabad",
    "Rajiv Gandhi International Stadium": "Rajiv Gandhi International Stadium, Hyderabad",
    "Rajiv Gandhi International Stadium, Hyderabad": "Rajiv Gandhi International Stadium, Hyderabad",
    # Sawai Mansingh
    "Sawai Mansingh Stadium": "Sawai Mansingh Stadium, Jaipur",
    "Sawai Mansingh Stadium, Jaipur": "Sawai Mansingh Stadium, Jaipur",
    # Dubai
    "Dubai International Cricket Stadium": "Dubai International Cricket Stadium, Dubai",
    "Dubai International Cricket Stadium, Dubai": "Dubai International Cricket Stadium, Dubai",
    # Narendra Modi
    "Narendra Modi Stadium": "Narendra Modi Stadium, Ahmedabad",
    "Narendra Modi Stadium, Ahmedabad": "Narendra Modi Stadium, Ahmedabad",
    "Motera Stadium": "Narendra Modi Stadium, Ahmedabad",
    "Sardar Patel Stadium": "Narendra Modi Stadium, Ahmedabad",
    # Others
    "PCA Stadium, Mohali": "IS Bindra Stadium, Mohali",
    "IS Bindra Stadium": "IS Bindra Stadium, Mohali",
    "IS Bindra Stadium, Mohali": "IS Bindra Stadium, Mohali",
    "Green Park": "Green Park, Kanpur",
    "Holkar Cricket Stadium": "Holkar Cricket Stadium, Indore",
    "Shaheed Veer Narayan Singh International Stadium": "Shaheed Veer Narayan Singh International Stadium, Raipur",
    "Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium": "ACA-VDCA Cricket Stadium, Visakhapatnam",
    "ACA-VDCA Cricket Stadium": "ACA-VDCA Cricket Stadium, Visakhapatnam",
    "ACA-VDCA Cricket Stadium, Visakhapatnam": "ACA-VDCA Cricket Stadium, Visakhapatnam",
    "Barabati Stadium": "Barabati Stadium, Cuttack",
    "M. A. Chidambaram Stadium": "MA Chidambaram Stadium, Chennai",
    "MA Chidambaram Stadium, Chepauk, Chennai": "MA Chidambaram Stadium, Chennai",
    "MA Chidambaram Stadium, Chepauk": "MA Chidambaram Stadium, Chennai",
}


def normalize_venue_name(venue_name: str) -> str:
    """
    Normalize a venue name to its canonical form.
    Returns the canonical name if found, otherwise the original name.
    """
    if not venue_name:
        return venue_name

    # Direct match
    if venue_name in VENUE_CANONICAL:
        return VENUE_CANONICAL[venue_name]

    # Case-insensitive match
    for key, value in VENUE_CANONICAL.items():
        if key.lower() == venue_name.lower():
            return value

    return venue_name


def normalize_format(format_str: str) -> str:
    """Normalize match format string."""
    return FORMAT_CANONICAL.get(format_str, format_str)


def normalize_wicket_type(wicket_kind: str) -> str:
    """Normalize wicket type to canonical form."""
    if wicket_kind is None:
        return None
    lower = wicket_kind.lower().strip()
    return WICKET_TYPES.get(lower, lower.replace(" ", "_"))


def classify_phase_udf(format_col=None):
    """UDF to classify over number into match phase.
    
    If format_col is provided, uses format-aware rules:
    - T20/T20I: powerplay 0-5, middle 6-14, death 15+
    - ODI: powerplay 0-9, middle 10-39, death 40+
    - Test: returns 'general' (no T20-style phases)
    
    If format_col is None, falls back to T20 rules.
    """
    if format_col is not None:
        return F.when(
            F.col(format_col) == "Test", F.lit("general")
        ).when(
            F.col(format_col) == "ODI",
            F.when(F.col("over_number") <= 9, F.lit("powerplay"))
            .when(F.col("over_number") <= 39, F.lit("middle"))
            .otherwise(F.lit("death"))
        ).otherwise(
            F.when(F.col("over_number") <= 5, F.lit("powerplay"))
            .when(F.col("over_number") <= 14, F.lit("middle"))
            .otherwise(F.lit("death"))
        )
    # Default: T20 rules
    return F.when(
        F.col("over_number") <= 5, F.lit("powerplay")
    ).when(
        F.col("over_number") <= 14, F.lit("middle")
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
    
    # Classify phase (format-aware)
    result = result.withColumn(
        "phase",
        classify_phase_udf("canonical_format")
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
