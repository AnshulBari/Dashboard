"""Canonical player identities shared by every local ingestion path.

Cricsheet scorecards commonly use initials while the application exposes full
display names.  Keeping this mapping in one place prevents each format from
creating a separate profile for the same international player.
"""

from __future__ import annotations

import pandas as pd


PLAYER_ALIASES = {
    # India
    "V Kohli": "Virat Kohli",
    "RG Sharma": "Rohit Sharma",
    "SA Yadav": "Suryakumar Yadav",
    "JJ Bumrah": "Jasprit Bumrah",
    "HH Pandya": "Hardik Pandya",
    "RA Jadeja": "Ravindra Jadeja",
    "YS Chahal": "Yuzvendra Chahal",
    "AR Patel": "Axar Patel",
    "RR Pant": "Rishabh Pant",
    # Australia
    "DA Warner": "David Warner",
    "SPD Smith": "Steve Smith",
    "GJ Maxwell": "Glenn Maxwell",
    "MA Starc": "Mitchell Starc",
    "PJ Cummins": "Pat Cummins",
    "TM Head": "Travis Head",
    "MR Marsh": "Mitchell Marsh",
    # England
    "JC Buttler": "Jos Buttler",
    "BA Stokes": "Ben Stokes",
    "JE Root": "Joe Root",
    "JC Archer": "Jofra Archer",
    "AU Rashid": "Adil Rashid",
    "HC Brook": "Harry Brook",
    "AD Hales": "Alex Hales",
    "PD Salt": "Phil Salt",
    "WG Jacks": "Will Jacks",
    # Pakistan
    "Shaheen Shah Afridi": "Shaheen Afridi",
    # South Africa
    "Q de Kock": "Quinton de Kock",
    "AK Markram": "Aiden Markram",
    "K Rabada": "Kagiso Rabada",
    "A Nortje": "Anrich Nortje",
    "T Bavuma": "Temba Bavuma",
    # New Zealand
    "KS Williamson": "Kane Williamson",
    "TA Boult": "Trent Boult",
    "DP Conway": "Devon Conway",
    "TG Southee": "Tim Southee",
    # West Indies
    "N Pooran": "Nicholas Pooran",
    "JO Holder": "Jason Holder",
}


PLAYER_COLUMNS = (
    "batter",
    "bowler",
    "non_striker",
    "dismissed_player",
    "fielder",
    "player_of_match",
)


def canonical_player_name(value):
    """Return the application's display identity for a source player name."""
    if not isinstance(value, str):
        return value
    clean = value.strip()
    return PLAYER_ALIASES.get(clean, clean)


def normalize_player_names(df: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize every player-bearing column in a flattened match frame."""
    normalized = df.copy()
    for column in PLAYER_COLUMNS:
        if column in normalized.columns:
            normalized[column] = normalized[column].map(canonical_player_name)

    for column in ("team_a_players", "team_b_players"):
        if column in normalized.columns:
            normalized[column] = normalized[column].map(
                lambda value: ",".join(
                    canonical_player_name(name) for name in value.split(",")
                )
                if isinstance(value, str) and value
                else value
            )
    return normalized
