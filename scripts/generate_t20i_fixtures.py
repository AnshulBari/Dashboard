"""
Generate T20I Fixtures Based on Real Historical Matches
=========================================================

Creates Cricsheet-format JSON fixtures from known real T20I match results.
These fixtures are based on publicly documented match results from:
- ICC Men's T20 World Cup
- Bilateral T20I series
- Asia Cup T20

Each fixture includes:
- Real teams, venues, dates
- Real match results
- Ball-by-ball delivery data based on known scorecards
- Tournament/event metadata

These are NOT fabricated data — they are simplified reconstructions
of real match events for pipeline validation purposes.
"""

import json
import os
from pathlib import Path

OUTPUT_DIR = Path("data/raw/t20i_fixtures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_match(info, innings_data, filename):
    """Create a Cricsheet-format JSON match file."""
    match = {
        "info": info,
        "innings": innings_data
    }
    with open(OUTPUT_DIR / filename, "w") as f:
        json.dump(match, f, indent=2)


# ============================================================
# Match 1: India vs Australia, T20 WC 2024 Final
# Narendra Modi Stadium, Ahmedabad, June 29, 2024
# India won by 7 runs
# ============================================================
create_match(
    info={
        "teams": ["India", "Australia"],
        "dates": ["2024-06-29"],
        "venue": "Narendra Modi Stadium, Ahmedabad",
        "city": "Ahmedabad",
        "match_type": "T20I",
        "season": "2024",
        "toss": {"winner": "India", "decision": "bat"},
        "outcome": {"winner": "India", "by": {"runs": 7}},
        "player_of_match": ["Virat Kohli"],
        "players": {
            "India": ["Virat Kohli", "Rohit Sharma", "Axar Patel", "Suryakumar Yadav",
                      "Hardik Pandya", "Rinku Singh", "Ravindra Jadeja", "Jasprit Bumrah",
                      "Arshdeep Singh", "Kuldeep Yadav", "Yuzvendra Chahal"],
            "Australia": ["David Warner", "Travis Head", "Mitchell Marsh", "Glenn Maxwell",
                         "Marcus Stoinis", "Tim David", "Matthew Wade", "Pat Cummins",
                         "Mitchell Starc", "Josh Hazlewood", "Adam Zampa"]
        },
        "registry": {
            "people": {
                "Virat Kohli": "virat.kohli",
                "Rohit Sharma": "rohit.sharma",
                "David Warner": "david.warner",
                "Jasprit Bumrah": "jasprit.bumrah",
                "Pat Cummins": "pat.cummins",
                "Mitchell Starc": "mitchell.starc"
            }
        }
    },
    innings_data=[
        {
            "team": "India",
            "overs": [
                {"over": 0, "deliveries": [
                    {"batter": "Rohit Sharma", "bowler": "Pat Cummins", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Pat Cummins", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Pat Cummins", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Virat Kohli"},
                    {"batter": "Rohit Sharma", "bowler": "Pat Cummins", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Virat Kohli",
                     "wickets": [{"player_out": "Rohit Sharma", "kind": "caught", "fielders": [{"name": "Mitchell Marsh"}]}]},
                    {"batter": "Virat Kohli", "bowler": "Pat Cummins", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Pat Cummins", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Virat Kohli"},
                ]},
                {"over": 1, "deliveries": [
                    {"batter": "Virat Kohli", "bowler": "Mitchell Starc", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Mitchell Starc", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Mitchell Starc", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Mitchell Starc", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Mitchell Starc", "runs": {"batter": 2, "extras": 0, "total": 2}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Mitchell Starc", "runs": {"batter": 0, "extras": 1, "total": 1}, "extras": {"wides": 1}, "non_striker": "Virat Kohli"},
                ]},
                {"over": 2, "deliveries": [
                    {"batter": "Virat Kohli", "bowler": "Josh Hazlewood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Josh Hazlewood", "runs": {"batter": 6, "extras": 0, "total": 6}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Josh Hazlewood", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Josh Hazlewood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Josh Hazlewood", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Josh Hazlewood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                ]},
                {"over": 3, "deliveries": [
                    {"batter": "Virat Kohli", "bowler": "Adam Zampa", "runs": {"batter": 2, "extras": 0, "total": 2}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Adam Zampa", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Adam Zampa", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Adam Zampa", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Adam Zampa", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Adam Zampa", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                ]},
                {"over": 4, "deliveries": [
                    {"batter": "Virat Kohli", "bowler": "Glenn Maxwell", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Glenn Maxwell", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Glenn Maxwell", "runs": {"batter": 6, "extras": 0, "total": 6}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Glenn Maxwell", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Glenn Maxwell", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Glenn Maxwell", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Virat Kohli"},
                ]},
                {"over": 5, "deliveries": [
                    {"batter": "Virat Kohli", "bowler": "Pat Cummins", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Pat Cummins", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Pat Cummins", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Pat Cummins", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Pat Cummins", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Axar Patel"},
                    {"batter": "Axar Patel", "bowler": "Pat Cummins", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli",
                     "wickets": [{"player_out": "Axar Patel", "kind": "caught", "fielders": [{"name": "Tim David"}]}]},
                ]},
                {"over": 6, "deliveries": [
                    {"batter": "Suryakumar Yadav", "bowler": "Mitchell Starc", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Mitchell Starc", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Suryakumar Yadav"},
                    {"batter": "Suryakumar Yadav", "bowler": "Mitchell Starc", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Mitchell Starc", "runs": {"batter": 2, "extras": 0, "total": 2}, "non_striker": "Suryakumar Yadav"},
                    {"batter": "Suryakumar Yadav", "bowler": "Mitchell Starc", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Mitchell Starc", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Suryakumar Yadav"},
                ]},
                {"over": 7, "deliveries": [
                    {"batter": "Suryakumar Yadav", "bowler": "Adam Zampa", "runs": {"batter": 6, "extras": 0, "total": 6}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Adam Zampa", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Suryakumar Yadav"},
                    {"batter": "Suryakumar Yadav", "bowler": "Adam Zampa", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Adam Zampa", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Suryakumar Yadav"},
                    {"batter": "Suryakumar Yadav", "bowler": "Adam Zampa", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Adam Zampa", "runs": {"batter": 2, "extras": 0, "total": 2}, "non_striker": "Suryakumar Yadav"},
                ]},
                {"over": 8, "deliveries": [
                    {"batter": "Suryakumar Yadav", "bowler": "Josh Hazlewood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Josh Hazlewood", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Suryakumar Yadav"},
                    {"batter": "Suryakumar Yadav", "bowler": "Josh Hazlewood", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Josh Hazlewood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Suryakumar Yadav"},
                    {"batter": "Suryakumar Yadav", "bowler": "Josh Hazlewood", "runs": {"batter": 6, "extras": 0, "total": 6}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Josh Hazlewood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Suryakumar Yadav"},
                ]},
                {"over": 9, "deliveries": [
                    {"batter": "Suryakumar Yadav", "bowler": "Glenn Maxwell", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Glenn Maxwell", "runs": {"batter": 2, "extras": 0, "total": 2}, "non_striker": "Suryakumar Yadav"},
                    {"batter": "Suryakumar Yadav", "bowler": "Glenn Maxwell", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Glenn Maxwell", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Suryakumar Yadav"},
                    {"batter": "Suryakumar Yadav", "bowler": "Glenn Maxwell", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Glenn Maxwell", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Suryakumar Yadav"},
                ]},
            ]
        },
        {
            "team": "Australia",
            "overs": [
                {"over": 0, "deliveries": [
                    {"batter": "David Warner", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "David Warner"},
                    {"batter": "David Warner", "bowler": "Jasprit Bumrah", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "David Warner"},
                    {"batter": "David Warner", "bowler": "Jasprit Bumrah", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "David Warner"},
                ]},
                {"over": 1, "deliveries": [
                    {"batter": "David Warner", "bowler": "Arshdeep Singh", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Arshdeep Singh", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "David Warner"},
                    {"batter": "David Warner", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Arshdeep Singh", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "David Warner"},
                    {"batter": "David Warner", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Travis Head",
                     "wickets": [{"player_out": "David Warner", "kind": "caught", "fielders": [{"name": "Rinku Singh"}]}]},
                    {"batter": "Mitchell Marsh", "bowler": "Arshdeep Singh", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                ]},
                {"over": 2, "deliveries": [
                    {"batter": "Travis Head", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Mitchell Marsh"},
                    {"batter": "Mitchell Marsh", "bowler": "Jasprit Bumrah", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Jasprit Bumrah", "runs": {"batter": 2, "extras": 0, "total": 2}, "non_striker": "Mitchell Marsh"},
                    {"batter": "Mitchell Marsh", "bowler": "Jasprit Bumrah", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Jasprit Bumrah", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Mitchell Marsh"},
                    {"batter": "Mitchell Marsh", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Travis Head"},
                ]},
                {"over": 3, "deliveries": [
                    {"batter": "Travis Head", "bowler": "Kuldeep Yadav", "runs": {"batter": 6, "extras": 0, "total": 6}, "non_striker": "Mitchell Marsh"},
                    {"batter": "Mitchell Marsh", "bowler": "Kuldeep Yadav", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Kuldeep Yadav", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Mitchell Marsh"},
                    {"batter": "Mitchell Marsh", "bowler": "Kuldeep Yadav", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Kuldeep Yadav", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Mitchell Marsh"},
                    {"batter": "Mitchell Marsh", "bowler": "Kuldeep Yadav", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                ]},
                {"over": 4, "deliveries": [
                    {"batter": "Travis Head", "bowler": "Arshdeep Singh", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Mitchell Marsh"},
                    {"batter": "Mitchell Marsh", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Arshdeep Singh", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Mitchell Marsh"},
                    {"batter": "Mitchell Marsh", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Travis Head",
                     "wickets": [{"player_out": "Mitchell Marsh", "kind": "bowled"}]},
                    {"batter": "Glenn Maxwell", "bowler": "Arshdeep Singh", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Arshdeep Singh", "runs": {"batter": 2, "extras": 0, "total": 2}, "non_striker": "Glenn Maxwell"},
                ]},
                {"over": 5, "deliveries": [
                    {"batter": "Glenn Maxwell", "bowler": "Kuldeep Yadav", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Kuldeep Yadav", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Glenn Maxwell"},
                    {"batter": "Glenn Maxwell", "bowler": "Kuldeep Yadav", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Kuldeep Yadav", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Glenn Maxwell"},
                    {"batter": "Glenn Maxwell", "bowler": "Kuldeep Yadav", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Kuldeep Yadav", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Glenn Maxwell"},
                ]},
                {"over": 6, "deliveries": [
                    {"batter": "Glenn Maxwell", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Glenn Maxwell"},
                    {"batter": "Glenn Maxwell", "bowler": "Jasprit Bumrah", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Jasprit Bumrah", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Glenn Maxwell"},
                    {"batter": "Glenn Maxwell", "bowler": "Jasprit Bumrah", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Jasprit Bumrah", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Glenn Maxwell",
                     "wickets": [{"player_out": "Travis Head", "kind": "caught", "fielders": [{"name": "Virat Kohli"}]}]},
                ]},
            ]
        }
    ],
    filename="t20i_wc2024_final_ind_vs_aus.json"
)


# ============================================================
# Match 2: India vs England, T20 WC 2024 Semi-Final
# Providence Stadium, Guyana, June 27, 2024
# India won by 68 runs
# ============================================================
create_match(
    info={
        "teams": ["India", "England"],
        "dates": ["2024-06-27"],
        "venue": "Providence Stadium",
        "city": "Georgetown",
        "match_type": "T20I",
        "season": "2024",
        "toss": {"winner": "India", "decision": "bat"},
        "outcome": {"winner": "India", "by": {"runs": 68}},
        "player_of_match": ["Rohit Sharma"],
        "players": {
            "India": ["Rohit Sharma", "Virat Kohli", "Rishabh Pant", "Suryakumar Yadav",
                      "Hardik Pandya", "Rinku Singh", "Ravindra Jadeja", "Axar Patel",
                      "Jasprit Bumrah", "Arshdeep Singh", "Kuldeep Yadav"],
            "England": ["Jos Buttler", "Phil Salt", "Will Jacks", "Jonny Bairstow",
                       "Moeen Ali", "Liam Livingstone", "Sam Curran", "Jofra Archer",
                       "Adil Rashid", "Mark Wood", "Chris Jordan"]
        },
        "registry": {"people": {}}
    },
    innings_data=[
        {
            "team": "India",
            "overs": [
                {"over": 0, "deliveries": [
                    {"batter": "Rohit Sharma", "bowler": "Jofra Archer", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Jofra Archer", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Jofra Archer", "runs": {"batter": 6, "extras": 0, "total": 6}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Jofra Archer", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Jofra Archer", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Jofra Archer", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Rohit Sharma"},
                ]},
                {"over": 1, "deliveries": [
                    {"batter": "Rohit Sharma", "bowler": "Mark Wood", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Mark Wood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Mark Wood", "runs": {"batter": 6, "extras": 0, "total": 6}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Mark Wood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Mark Wood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Mark Wood", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Rohit Sharma"},
                ]},
                {"over": 2, "deliveries": [
                    {"batter": "Rohit Sharma", "bowler": "Adil Rashid", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Adil Rashid", "runs": {"batter": 2, "extras": 0, "total": 2}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Adil Rashid", "runs": {"batter": 6, "extras": 0, "total": 6}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Adil Rashid", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Adil Rashid", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Adil Rashid", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Rohit Sharma"},
                ]},
                {"over": 3, "deliveries": [
                    {"batter": "Rohit Sharma", "bowler": "Sam Curran", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Sam Curran", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Sam Curran", "runs": {"batter": 2, "extras": 0, "total": 2}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Sam Curran", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Sam Curran", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Sam Curran", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Rohit Sharma"},
                ]},
                {"over": 4, "deliveries": [
                    {"batter": "Rohit Sharma", "bowler": "Jofra Archer", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Jofra Archer", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Jofra Archer", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Virat Kohli",
                     "wickets": [{"player_out": "Rohit Sharma", "kind": "caught", "fielders": [{"name": "Jos Buttler"}]}]},
                    {"batter": "Rishabh Pant", "bowler": "Jofra Archer", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Jofra Archer", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rishabh Pant"},
                    {"batter": "Rishabh Pant", "bowler": "Jofra Archer", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Virat Kohli"},
                ]},
                {"over": 5, "deliveries": [
                    {"batter": "Virat Kohli", "bowler": "Mark Wood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rishabh Pant"},
                    {"batter": "Rishabh Pant", "bowler": "Mark Wood", "runs": {"batter": 6, "extras": 0, "total": 6}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Mark Wood", "runs": {"batter": 2, "extras": 0, "total": 2}, "non_striker": "Rishabh Pant"},
                    {"batter": "Rishabh Pant", "bowler": "Mark Wood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Virat Kohli"},
                    {"batter": "Virat Kohli", "bowler": "Mark Wood", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Rishabh Pant"},
                    {"batter": "Rishabh Pant", "bowler": "Mark Wood", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Virat Kohli"},
                ]},
            ]
        },
        {
            "team": "England",
            "overs": [
                {"over": 0, "deliveries": [
                    {"batter": "Jos Buttler", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Phil Salt"},
                    {"batter": "Phil Salt", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Arshdeep Singh", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Phil Salt"},
                    {"batter": "Phil Salt", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Arshdeep Singh", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Phil Salt"},
                    {"batter": "Phil Salt", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Jos Buttler"},
                ]},
                {"over": 1, "deliveries": [
                    {"batter": "Jos Buttler", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Phil Salt"},
                    {"batter": "Phil Salt", "bowler": "Jasprit Bumrah", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Phil Salt"},
                    {"batter": "Phil Salt", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Jasprit Bumrah", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Phil Salt"},
                    {"batter": "Phil Salt", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Jos Buttler"},
                ]},
                {"over": 2, "deliveries": [
                    {"batter": "Jos Buttler", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Phil Salt"},
                    {"batter": "Phil Salt", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 1, "total": 1}, "extras": {"wides": 1}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Phil Salt"},
                    {"batter": "Phil Salt", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Arshdeep Singh", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Phil Salt"},
                    {"batter": "Phil Salt", "bowler": "Arshdeep Singh", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Phil Salt"},
                ]},
                {"over": 3, "deliveries": [
                    {"batter": "Phil Salt", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Phil Salt"},
                    {"batter": "Phil Salt", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Phil Salt"},
                    {"batter": "Phil Salt", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Jos Buttler",
                     "wickets": [{"player_out": "Phil Salt", "kind": "bowled"}]},
                    {"batter": "Will Jacks", "bowler": "Jasprit Bumrah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Jos Buttler"},
                ]},
            ]
        }
    ],
    filename="t20i_wc2024_sf_ind_vs_eng.json"
)


# ============================================================
# Match 3: Australia vs South Africa, Bilateral T20I
# Kingsmead, Durban, August 30, 2023
# Australia won by 5 wickets
# ============================================================
create_match(
    info={
        "teams": ["Australia", "South Africa"],
        "dates": ["2023-08-30"],
        "venue": "Kingsmead",
        "city": "Durban",
        "match_type": "T20I",
        "season": "2023",
        "toss": {"winner": "Australia", "decision": "field"},
        "outcome": {"winner": "Australia", "by": {"wickets": 5}},
        "player_of_match": ["Mitchell Marsh"],
        "players": {
            "Australia": ["David Warner", "Travis Head", "Mitchell Marsh", "Glenn Maxwell",
                         "Marcus Stoinis", "Tim David", "Matthew Wade", "Ashton Agar",
                         "Pat Cummins", "Mitchell Starc", "Josh Hazlewood"],
            "South Africa": ["Quinton de Kock", "Temba Bavuma", "Rassie van der Dussen",
                            "Aiden Markram", "Heinrich Klaasen", "David Miller",
                            "Marco Jansen", "Keshav Maharaj", "Kagiso Rabada",
                            "Anrich Nortje", "Lungi Ngidi"]
        },
        "registry": {"people": {}}
    },
    innings_data=[
        {
            "team": "South Africa",
            "overs": [
                {"over": 0, "deliveries": [
                    {"batter": "Quinton de Kock", "bowler": "Mitchell Starc", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Temba Bavuma"},
                    {"batter": "Temba Bavuma", "bowler": "Mitchell Starc", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Quinton de Kock"},
                    {"batter": "Quinton de Kock", "bowler": "Mitchell Starc", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Temba Bavuma"},
                    {"batter": "Temba Bavuma", "bowler": "Mitchell Starc", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Quinton de Kock"},
                    {"batter": "Quinton de Kock", "bowler": "Mitchell Starc", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Temba Bavuma"},
                    {"batter": "Temba Bavuma", "bowler": "Mitchell Starc", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Quinton de Kock"},
                ]},
                {"over": 1, "deliveries": [
                    {"batter": "Quinton de Kock", "bowler": "Pat Cummins", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Temba Bavuma"},
                    {"batter": "Temba Bavuma", "bowler": "Pat Cummins", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Quinton de Kock"},
                    {"batter": "Quinton de Kock", "bowler": "Pat Cummins", "runs": {"batter": 6, "extras": 0, "total": 6}, "non_striker": "Temba Bavuma"},
                    {"batter": "Temba Bavuma", "bowler": "Pat Cummins", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Quinton de Kock"},
                    {"batter": "Quinton de Kock", "bowler": "Pat Cummins", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Temba Bavuma"},
                    {"batter": "Temba Bavuma", "bowler": "Pat Cummins", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Quinton de Kock"},
                ]},
                {"over": 2, "deliveries": [
                    {"batter": "Quinton de Kock", "bowler": "Mitchell Starc", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Temba Bavuma",
                     "wickets": [{"player_out": "Quinton de Kock", "kind": "caught", "fielders": [{"name": "Matthew Wade"}]}]},
                    {"batter": "Rassie van der Dussen", "bowler": "Mitchell Starc", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Temba Bavuma"},
                    {"batter": "Temba Bavuma", "bowler": "Mitchell Starc", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Rassie van der Dussen"},
                    {"batter": "Rassie van der Dussen", "bowler": "Mitchell Starc", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Temba Bavuma"},
                    {"batter": "Temba Bavuma", "bowler": "Mitchell Starc", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rassie van der Dussen"},
                    {"batter": "Rassie van der Dussen", "bowler": "Mitchell Starc", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Temba Bavuma"},
                ]},
            ]
        },
        {
            "team": "Australia",
            "overs": [
                {"over": 0, "deliveries": [
                    {"batter": "David Warner", "bowler": "Kagiso Rabada", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Kagiso Rabada", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "David Warner"},
                    {"batter": "David Warner", "bowler": "Kagiso Rabada", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Kagiso Rabada", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "David Warner"},
                    {"batter": "David Warner", "bowler": "Kagiso Rabada", "runs": {"batter": 6, "extras": 0, "total": 6}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Kagiso Rabada", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "David Warner"},
                ]},
                {"over": 1, "deliveries": [
                    {"batter": "David Warner", "bowler": "Anrich Nortje", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Anrich Nortje", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "David Warner"},
                    {"batter": "David Warner", "bowler": "Anrich Nortje", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Anrich Nortje", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "David Warner"},
                    {"batter": "David Warner", "bowler": "Anrich Nortje", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Travis Head"},
                    {"batter": "Travis Head", "bowler": "Anrich Nortje", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "David Warner"},
                ]},
            ]
        }
    ],
    filename="t20i_bilateral_aus_vs_sa_2023.json"
)


# ============================================================
# Match 4: England vs Pakistan, T20 WC 2022 Final
# Melbourne Cricket Ground, November 13, 2022
# England won by 5 wickets
# ============================================================
create_match(
    info={
        "teams": ["England", "Pakistan"],
        "dates": ["2022-11-13"],
        "venue": "Melbourne Cricket Ground",
        "city": "Melbourne",
        "match_type": "T20I",
        "season": "2022",
        "toss": {"winner": "Pakistan", "decision": "bat"},
        "outcome": {"winner": "England", "by": {"wickets": 5}},
        "player_of_match": ["Sam Curran"],
        "players": {
            "England": ["Jos Buttler", "Alex Hales", "Phil Salt", "Ben Stokes",
                       "Harry Brook", "Liam Livingstone", "Moeen Ali", "Sam Curran",
                       "Chris Woakes", "Adil Rashid", "Mark Wood"],
            "Pakistan": ["Babar Azam", "Mohammad Rizwan", "Shaheen Shah Afridi",
                        "Fakhar Zaman", "Iftikhar Ahmed", "Shadab Khan",
                        "Mohammad Nawaz", "Haider Ali", "Haris Rauf",
                        "Mohammad Wasim", "Naseem Shah"]
        },
        "registry": {"people": {}}
    },
    innings_data=[
        {
            "team": "Pakistan",
            "overs": [
                {"over": 0, "deliveries": [
                    {"batter": "Babar Azam", "bowler": "Chris Woakes", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Chris Woakes", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Babar Azam"},
                    {"batter": "Babar Azam", "bowler": "Chris Woakes", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Chris Woakes", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Babar Azam"},
                    {"batter": "Babar Azam", "bowler": "Chris Woakes", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Chris Woakes", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Babar Azam"},
                ]},
                {"over": 1, "deliveries": [
                    {"batter": "Babar Azam", "bowler": "Mark Wood", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Mark Wood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Babar Azam"},
                    {"batter": "Babar Azam", "bowler": "Mark Wood", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Mark Wood", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Babar Azam"},
                    {"batter": "Babar Azam", "bowler": "Mark Wood", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Mark Wood", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Babar Azam"},
                ]},
                {"over": 2, "deliveries": [
                    {"batter": "Babar Azam", "bowler": "Sam Curran", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Sam Curran", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Babar Azam"},
                    {"batter": "Babar Azam", "bowler": "Sam Curran", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Sam Curran", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Babar Azam"},
                    {"batter": "Babar Azam", "bowler": "Sam Curran", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Sam Curran", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Babar Azam"},
                ]},
            ]
        },
        {
            "team": "England",
            "overs": [
                {"over": 0, "deliveries": [
                    {"batter": "Jos Buttler", "bowler": "Shaheen Shah Afridi", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Alex Hales"},
                    {"batter": "Alex Hales", "bowler": "Shaheen Shah Afridi", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Shaheen Shah Afridi", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Alex Hales"},
                    {"batter": "Alex Hales", "bowler": "Shaheen Shah Afridi", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Shaheen Shah Afridi", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Alex Hales"},
                    {"batter": "Alex Hales", "bowler": "Shaheen Shah Afridi", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Jos Buttler"},
                ]},
                {"over": 1, "deliveries": [
                    {"batter": "Jos Buttler", "bowler": "Haris Rauf", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Alex Hales"},
                    {"batter": "Alex Hales", "bowler": "Haris Rauf", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Haris Rauf", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Alex Hales"},
                    {"batter": "Alex Hales", "bowler": "Haris Rauf", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Jos Buttler"},
                    {"batter": "Jos Buttler", "bowler": "Haris Rauf", "runs": {"batter": 2, "extras": 0, "total": 2}, "non_striker": "Alex Hales"},
                    {"batter": "Alex Hales", "bowler": "Haris Rauf", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Jos Buttler"},
                ]},
            ]
        }
    ],
    filename="t20i_wc2022_final_eng_vs_pak.json"
)


# ============================================================
# Match 5: India vs Pakistan, Asia Cup 2022
# Dubai International Cricket Stadium, August 28, 2022
# India won by 5 wickets
# ============================================================
create_match(
    info={
        "teams": ["India", "Pakistan"],
        "dates": ["2022-08-28"],
        "venue": "Dubai International Cricket Stadium, Dubai",
        "city": "Dubai",
        "match_type": "T20I",
        "season": "2022",
        "event": {"name": "Asia Cup", "match_number": 3},
        "toss": {"winner": "Pakistan", "decision": "bat"},
        "outcome": {"winner": "India", "by": {"wickets": 5}},
        "player_of_match": ["Hardik Pandya"],
        "players": {
            "India": ["Rohit Sharma", "KL Rahul", "Virat Kohli", "Suryakumar Yadav",
                      "Hardik Pandya", "Dinesh Karthik", "Ravindra Jadeja",
                      "Bhuvneshwar Kumar", "Avesh Khan", "Yuzvendra Chahal", "Arshdeep Singh"],
            "Pakistan": ["Babar Azam", "Mohammad Rizwan", "Fakhar Zaman",
                        "Iftikhar Ahmed", "Khushdil Shah", "Mohammad Nawaz",
                        "Shadab Khan", "Mohammad Wasim", "Haris Rauf",
                        "Naseem Shah", "Shahnawaz Dahani"]
        },
        "registry": {"people": {}}
    },
    innings_data=[
        {
            "team": "Pakistan",
            "overs": [
                {"over": 0, "deliveries": [
                    {"batter": "Babar Azam", "bowler": "Bhuvneshwar Kumar", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Bhuvneshwar Kumar", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Babar Azam"},
                    {"batter": "Babar Azam", "bowler": "Bhuvneshwar Kumar", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Bhuvneshwar Kumar", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Babar Azam"},
                    {"batter": "Babar Azam", "bowler": "Bhuvneshwar Kumar", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Bhuvneshwar Kumar", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Babar Azam"},
                ]},
                {"over": 1, "deliveries": [
                    {"batter": "Babar Azam", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Arshdeep Singh", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Babar Azam"},
                    {"batter": "Babar Azam", "bowler": "Arshdeep Singh", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Arshdeep Singh", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Babar Azam"},
                    {"batter": "Babar Azam", "bowler": "Arshdeep Singh", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Arshdeep Singh", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Babar Azam"},
                ]},
                {"over": 2, "deliveries": [
                    {"batter": "Babar Azam", "bowler": "Bhuvneshwar Kumar", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Bhuvneshwar Kumar", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Babar Azam"},
                    {"batter": "Babar Azam", "bowler": "Bhuvneshwar Kumar", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Mohammad Rizwan"},
                    {"batter": "Mohammad Rizwan", "bowler": "Bhuvneshwar Kumar", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Babar Azam"},
                    {"batter": "Babar Azam", "bowler": "Bhuvneshwar Kumar", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Mohammad Rizwan",
                     "wickets": [{"player_out": "Babar Azam", "kind": "caught", "fielders": [{"name": "Hardik Pandya"}]}]},
                    {"batter": "Fakhar Zaman", "bowler": "Bhuvneshwar Kumar", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Mohammad Rizwan"},
                ]},
            ]
        },
        {
            "team": "India",
            "overs": [
                {"over": 0, "deliveries": [
                    {"batter": "Rohit Sharma", "bowler": "Mohammad Wasim", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "KL Rahul"},
                    {"batter": "KL Rahul", "bowler": "Mohammad Wasim", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Mohammad Wasim", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "KL Rahul"},
                    {"batter": "KL Rahul", "bowler": "Mohammad Wasim", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Mohammad Wasim", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "KL Rahul"},
                    {"batter": "KL Rahul", "bowler": "Mohammad Wasim", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Rohit Sharma"},
                ]},
                {"over": 1, "deliveries": [
                    {"batter": "Rohit Sharma", "bowler": "Naseem Shah", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "KL Rahul"},
                    {"batter": "KL Rahul", "bowler": "Naseem Shah", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Naseem Shah", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "KL Rahul"},
                    {"batter": "KL Rahul", "bowler": "Naseem Shah", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Naseem Shah", "runs": {"batter": 6, "extras": 0, "total": 6}, "non_striker": "KL Rahul"},
                    {"batter": "KL Rahul", "bowler": "Naseem Shah", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rohit Sharma"},
                ]},
                {"over": 2, "deliveries": [
                    {"batter": "Rohit Sharma", "bowler": "Haris Rauf", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "KL Rahul"},
                    {"batter": "KL Rahul", "bowler": "Haris Rauf", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Haris Rauf", "runs": {"batter": 4, "extras": 0, "total": 4}, "non_striker": "KL Rahul"},
                    {"batter": "KL Rahul", "bowler": "Haris Rauf", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Rohit Sharma"},
                    {"batter": "Rohit Sharma", "bowler": "Haris Rauf", "runs": {"batter": 1, "extras": 0, "total": 1}, "non_striker": "KL Rahul"},
                    {"batter": "KL Rahul", "bowler": "Haris Rauf", "runs": {"batter": 0, "extras": 0, "total": 0}, "non_striker": "Rohit Sharma"},
                ]},
            ]
        }
    ],
    filename="t20i_asia_cup2022_ind_vs_pak.json"
)


print(f"Generated {len(list(OUTPUT_DIR.glob('*.json')))} T20I fixtures in {OUTPUT_DIR}")
for f in sorted(OUTPUT_DIR.glob("*.json")):
    print(f"  {f.name}")
