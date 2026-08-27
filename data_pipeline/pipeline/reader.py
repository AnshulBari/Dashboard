"""
Cricsheet JSON Reader
=====================

Reads Cricsheet match JSON files and flattens them into pandas DataFrames.

Each Cricsheet JSON file contains one match with:
- info: match metadata (teams, venue, date, toss, result)
- innings: array of innings, each with overs containing deliveries

We flatten this into one row per delivery with match-level context.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def read_match_file(json_path: str | Path) -> dict:
    """Read a single Cricsheet match JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def flatten_match(data: dict, filename: str = "") -> list[dict]:
    """
    Flatten a single Cricsheet match into delivery-level rows.
    
    Returns a list of dicts, one per delivery.
    """
    info = data.get("info", {})
    innings_list = data.get("innings", [])
    
    if not innings_list:
        return []
    
    # Match metadata
    match_date = (info.get("dates") or [""])[0]
    match_type = info.get("match_type", "")
    venue = info.get("venue", "")
    city = info.get("city", "")
    teams = info.get("teams", [])
    toss_winner = info.get("toss", {}).get("winner", "")
    toss_decision = info.get("toss", {}).get("decision", "")
    outcome = info.get("outcome", {})
    winner = outcome.get("winner", "")
    win_by = outcome.get("by", {})
    player_of_match = (info.get("player_of_match") or [""])[0] if info.get("player_of_match") else ""
    
    # Phase 1: Season and day metadata for universal model
    season = info.get("season", "")
    match_dates = info.get("dates", [])
    day_count = len(match_dates) if match_dates else 0
    
    # Outcome details for Test matches
    result_type = "win"  # default
    if not winner or winner == "":
        if outcome.get("draw"):
            result_type = "draw"
        elif outcome.get("no_result"):
            result_type = "no_result"
        elif outcome.get("tie"):
            result_type = "tie"
        else:
            result_type = "no_result"
    
    # Registry for player ID mapping
    registry = info.get("registry", {}).get("people", {})
    
    # Players per team
    players_map = info.get("players", {})
    
    # Event info (for tournament detection)
    event = info.get("event", {})
    event_name = event.get("name", "") if isinstance(event, dict) else ""
    match_number = event.get("match_number") if isinstance(event, dict) else None
    
    # Determine competition
    competition = info.get("competition", "")
    
    # Determine match_id from filename
    match_id = filename.replace(".json", "") if filename else ""
    
    rows = []
    for innings_idx, innings_data in enumerate(innings_list):
        batting_team = innings_data.get("team", "")
        bowling_team = ""
        # Find bowling team (the other team)
        if len(teams) == 2:
            bowling_team = teams[1] if batting_team == teams[0] else teams[0]
        
        for over_data in innings_data.get("overs", []):
            over_number = over_data.get("over", 0)
            deliveries = over_data.get("deliveries", [])
            
            for ball_idx, delivery in enumerate(deliveries):
                batter = delivery.get("batter", "")
                bowler = delivery.get("bowler", "")
                non_striker = delivery.get("non_striker", "")
                
                runs_data = delivery.get("runs", {})
                runs_batter = runs_data.get("batter", 0)
                runs_extras = runs_data.get("extras", 0)
                runs_total = runs_data.get("total", 0)
                
                extras = delivery.get("extras", {})
                extra_type = None
                if extras:
                    if "wides" in extras:
                        extra_type = "wide"
                    elif "noballs" in extras:
                        extra_type = "noball"
                    elif "byes" in extras:
                        extra_type = "bye"
                    elif "legbyes" in extras:
                        extra_type = "legbye"
                    elif "penalty" in extras:
                        extra_type = "penalty"
                
                wickets = delivery.get("wickets", [])
                wicket_type = None
                dismissed_player = ""
                fielder = ""
                is_wicket = False
                
                if wickets:
                    w = wickets[0]
                    is_wicket = True
                    wicket_type = w.get("kind", "")
                    dismissed_player = w.get("player_out", "")
                    fielders = w.get("fielders", [])
                    if fielders:
                        fielder = fielders[0].get("name", "") if isinstance(fielders[0], dict) else str(fielders[0])
                
                ball_in_over = ball_idx + 1
                
                row = {
                    "match_id": match_id,
                    "match_date": match_date,
                    "format": match_type,
                    "season": season,
                    "result_type": result_type,
                    "venue": venue,
                    "city": city,
                    "team_a": teams[0] if len(teams) > 0 else "",
                    "team_b": teams[1] if len(teams) > 1 else "",
                    "batting_team": batting_team,
                    "bowling_team": bowling_team,
                    "toss_winner": toss_winner,
                    "toss_decision": toss_decision,
                    "winner": winner,
                    "win_by_runs": win_by.get("runs") if isinstance(win_by, dict) else None,
                    "win_by_wickets": win_by.get("wickets") if isinstance(win_by, dict) else None,
                    "win_by_innings": win_by.get("innings") if isinstance(win_by, dict) else None,
                    "player_of_match": player_of_match,
                    "innings_number": innings_idx + 1,  # 1-indexed
                    "over_number": over_number,
                    "ball_in_over": ball_in_over,
                    "batter": batter,
                    "bowler": bowler,
                    "non_striker": non_striker,
                    "runs_batter": runs_batter,
                    "runs_extras": runs_extras,
                    "runs_total": runs_total,
                    "extra_type": extra_type,
                    "is_wicket": is_wicket,
                    "wicket_type": wicket_type,
                    "dismissed_player": dismissed_player,
                    "fielder": fielder,
                    # Test innings metadata
                    "innings_declared": innings_data.get("declared", False),
                    "innings_all_out": innings_data.get("all_out", False),
                    "innings_follow_on": innings_data.get("follow_on", False),
                    # Registry IDs
                    "batter_id_ext": registry.get(batter, ""),
                    "bowler_id_ext": registry.get(bowler, ""),
                    "non_striker_id_ext": registry.get(non_striker, ""),
                    "dismissed_id_ext": registry.get(dismissed_player, "") if dismissed_player else "",
                    # Competition/event
                    "event_name": event_name,
                    "match_number": match_number,
                    "competition": competition,
                    # Player lists
                    "team_a_players": ",".join(players_map.get(teams[0], [])) if teams else "",
                    "team_b_players": ",".join(players_map.get(teams[1], [])) if len(teams) > 1 else "",
                }
                rows.append(row)
    
    return rows


def read_directory(
    data_dir: str | Path,
    match_limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    Read all JSON match files from a directory into a single DataFrame.
    
    Args:
        data_dir: Directory containing Cricsheet JSON files
        match_limit: Maximum number of matches to read (for testing)
    
    Returns:
        DataFrame with one row per delivery
    """
    data_dir = Path(data_dir)
    json_files = sorted(data_dir.glob("*.json"))
    
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {data_dir}")
    
    if match_limit:
        json_files = json_files[:match_limit]
    
    all_rows = []
    errors = 0
    
    for i, json_file in enumerate(json_files):
        try:
            data = read_match_file(json_file)
            rows = flatten_match(data, json_file.name)
            all_rows.extend(rows)
        except Exception as e:
            logger.warning(f"Error reading {json_file.name}: {e}")
            errors += 1
            continue
        
        if (i + 1) % 100 == 0:
            logger.info(f"  Read {i + 1}/{len(json_files)} files, {len(all_rows)} deliveries")
    
    logger.info(
        f"Read {len(json_files) - errors} matches, "
        f"{len(all_rows)} deliveries, "
        f"{errors} errors"
    )
    
    df = pd.DataFrame(all_rows)
    
    # Convert date
    if "match_date" in df.columns:
        df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    
    return df


def get_match_info(data_dir: str | Path, match_limit: Optional[int] = None) -> pd.DataFrame:
    """
    Extract match-level info (without deliveries) from JSON files.
    
    Useful for quick metadata inspection.
    """
    data_dir = Path(data_dir)
    json_files = sorted(data_dir.glob("*.json"))
    
    if match_limit:
        json_files = json_files[:match_limit]
    
    matches = []
    for json_file in json_files:
        try:
            data = read_match_file(json_file)
            info = data.get("info", {})
            outcome = info.get("outcome", {})
            event = info.get("event", {})
            
            matches.append({
                "match_id": json_file.stem,
                "date": (info.get("dates") or [""])[0],
                "format": info.get("match_type", ""),
                "venue": info.get("venue", ""),
                "city": info.get("city", ""),
                "teams": info.get("teams", []),
                "toss_winner": info.get("toss", {}).get("winner", ""),
                "toss_decision": info.get("toss", {}).get("decision", ""),
                "winner": outcome.get("winner", ""),
                "event_name": event.get("name", "") if isinstance(event, dict) else "",
                "competition": info.get("competition", ""),
            })
        except Exception:
            continue
    
    return pd.DataFrame(matches)
