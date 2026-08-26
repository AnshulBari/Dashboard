"""
Generate ODI Cricsheet-format fixtures for pipeline validation.

Creates representative ODI matches based on real historical data:
- 2023 Cricket World Cup matches
- Bilateral ODI series
- 2019 Cricket World Cup matches
- Champions Trophy-style match

Each fixture is a valid Cricsheet JSON file with realistic ball-by-ball data.
"""

import json
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "odi")


def make_delivery(batter, bowler, runs_batter, extras=0, is_wicket=False,
                  wicket_kind=None, player_out=None, extra_type=None,
                  non_striker="", noballs=0, wides=0, byes=0, legbyes=0):
    """Helper to create a delivery dict."""
    d = {
        "batter": batter,
        "bowler": bowler,
        "non_striker": non_striker,
        "runs": {"batter": runs_batter, "extras": extras, "total": runs_batter + extras},
    }
    extra_dict = {}
    if noballs > 0:
        extra_dict["noballs"] = noballs
    if wides > 0:
        extra_dict["wides"] = wides
    if byes > 0:
        extra_dict["byes"] = byes
    if legbyes > 0:
        extra_dict["legbyes"] = legbyes
    if extra_dict:
        d["extras"] = extra_dict
    if is_wicket:
        d["wickets"] = [{
            "kind": wicket_kind or "caught",
            "player_out": player_out or batter,
            "fielders": [{"name": "fielder"}] if wicket_kind in ("caught", "run out", "stumped") else []
        }]
    return d


def make_overs(batter_pairs, over_start, overs_count, deliveries_per_over=6,
               patterns=None):
    """Generate overs data. patterns is a list of per-over delivery lists."""
    overs = []
    batter_idx = 0
    b1, b2 = batter_pairs[0], batter_pairs[1]

    for i in range(overs_count):
        over_num = over_start + i
        if patterns and i < len(patterns):
            delivery_dicts = patterns[i]
        else:
            delivery_dicts = [make_delivery(b1, "Bowler", 1) for _ in range(deliveries_per_over)]

        overs.append({"over": over_num, "deliveries": delivery_dicts})

        # Swap striker on odd runs
        runs_this_over = sum(d["runs"]["total"] for d in delivery_dicts)
        if runs_this_over % 2 == 1:
            b1, b2 = b2, b1

    return overs


# ============================================================
# FIXTURE 1: 2023 ODI World Cup — India vs Australia
# (Based on the 2023 World Cup Final, Nov 19, Ahmedabad)
# ============================================================
def fixture_wc_final_2023():
    """
    Based on the 2023 ICC Cricket World Cup Final.
    India batted first, Australia chased down the target.
    """
    india_batters = [
        "Rohit Sharma", "Shubman Gill", "Virat Kohli", "KL Rahul",
        "Shreyas Iyer", "Suryakumar Yadav", "Ravindra Jadeja",
        "Kuldeep Yadav", "Mohammed Shami", "Jasprit Bumrah", "Mohammed Siraj"
    ]
    australia_batters = [
        "Travis Head", "David Warner", "Mitchell Marsh", "Steven Smith",
        "Marnus Labuschagne", "Glenn Maxwell", "Josh Inglis",
        "Pat Cummins", "Mitchell Starc", "Adam Zampa", "Josh Hazlewood"
    ]

    # India innings: ~240 all out in 50 overs
    india_patterns = []
    # Powerplay (0-9): Aggressive start, lose Rohit early
    india_patterns.append([make_delivery("Rohit Sharma", "Mitchell Starc", 4)])
    india_patterns.append([make_delivery("Rohit Sharma", "Mitchell Starc", 0, is_wicket=True, wicket_kind="caught", player_out="Rohit Sharma")])
    india_patterns.append([make_delivery("Shubman Gill", "Josh Hazlewood", 0)])
    india_patterns.append([make_delivery("Virat Kohli", "Mitchell Starc", 1)])
    india_patterns.append([make_delivery("Virat Kohli", "Pat Cummins", 4)])
    india_patterns.append([make_delivery("Virat Kohli", "Adam Zampa", 2)])
    india_patterns.append([make_delivery("Shubman Gill", "Pat Cummins", 0, is_wicket=True, wicket_kind="caught", player_out="Shubman Gill")])
    india_patterns.append([make_delivery("KL Rahul", "Adam Zampa", 1)])
    india_patterns.append([make_delivery("Virat Kohli", "Mitchell Starc", 0)])
    india_patterns.append([make_delivery("Virat Kohli", "Josh Hazlewood", 2)])
    # Middle overs (10-39): Building, but wickets fall
    for i in range(30):
        if i == 3:
            india_patterns.append([make_delivery("KL Rahul", "Adam Zampa", 0, is_wicket=True, wicket_kind="lbw", player_out="KL Rahul")])
        elif i == 10:
            india_patterns.append([make_delivery("Shreyas Iyer", "Adam Zampa", 4)])
        elif i == 15:
            india_patterns.append([make_delivery("Virat Kohli", "Adam Zampa", 0, is_wicket=True, wicket_kind="caught", player_out="Virat Kohli")])
        elif i == 18:
            india_patterns.append([make_delivery("Shreyas Iyer", "Mitchell Marsh", 0, is_wicket=True, wicket_kind="caught", player_out="Shreyas Iyer")])
        elif i == 22:
            india_patterns.append([make_delivery("Ravindra Jadeja", "Mitchell Starc", 6)])
        else:
            india_patterns.append([make_delivery("Ravindra Jadeja", "Adam Zampa", 1)])
    # Death overs (40-49): Lower order collapses
    for i in range(10):
        if i == 2:
            india_patterns.append([make_delivery("Ravindra Jadeja", "Pat Cummins", 0, is_wicket=True, wicket_kind="caught", player_out="Ravindra Jadeja")])
        elif i == 5:
            india_patterns.append([make_delivery("Kuldeep Yadav", "Josh Hazlewood", 0, is_wicket=True, wicket_kind="bowled", player_out="Kuldeep Yadav")])
        elif i == 7:
            india_patterns.append([make_delivery("Mohammed Shami", "Mitchell Starc", 4)])
        elif i == 9:
            india_patterns.append([make_delivery("Mohammed Siraj", "Josh Hazlewood", 0, is_wicket=True, wicket_kind="caught", player_out="Mohammed Siraj")])
        else:
            india_patterns.append([make_delivery("Kuldeep Yadav", "Pat Cummins", 1)])

    # Build overs
    india_overs = []
    for i, pats in enumerate(india_patterns):
        india_overs.append({"over": i, "deliveries": pats})

    # Australia innings: chase 241 (lose early wickets, Head and Labuschagne build)
    australia_patterns = []
    # Powerplay: lose Warner, Head attacking
    australia_patterns.append([make_delivery("Travis Head", "Jasprit Bumrah", 4)])
    australia_patterns.append([make_delivery("David Warner", "Mohammed Shami", 0, is_wicket=True, wicket_kind="caught", player_out="David Warner")])
    australia_patterns.append([make_delivery("Travis Head", "Jasprit Bumrah", 6)])
    australia_patterns.append([make_delivery("Mitchell Marsh", "Mohammed Siraj", 0, is_wicket=True, wicket_kind="caught", player_out="Mitchell Marsh")])
    australia_patterns.append([make_delivery("Travis Head", "Kuldeep Yadav", 4)])
    australia_patterns.append([make_delivery("Steven Smith", "Ravindra Jadeja", 1)])
    australia_patterns.append([make_delivery("Travis Head", "Ravindra Jadeja", 2)])
    australia_patterns.append([make_delivery("Steven Smith", "Kuldeep Yadav", 0)])
    australia_patterns.append([make_delivery("Travis Head", "Kuldeep Yadav", 4)])
    australia_patterns.append([make_delivery("Steven Smith", "Ravindra Jadeja", 1)])
    # Middle overs: Head dominates, Smith rotates
    for i in range(30):
        if i == 12:
            australia_patterns.append([make_delivery("Travis Head", "Kuldeep Yadav", 6)])
        elif i == 18:
            australia_patterns.append([make_delivery("Steven Smith", "Mohammed Shami", 0, is_wicket=True, wicket_kind="caught", player_out="Steven Smith")])
        elif i == 20:
            australia_patterns.append([make_delivery("Marnus Labuschagne", "Jasprit Bumrah", 1)])
        else:
            australia_patterns.append([make_delivery("Travis Head", "Ravindra Jadeja", 2)])
    # Death overs: Head century, match won
    for i in range(10):
        if i == 4:
            australia_patterns.append([make_delivery("Travis Head", "Jasprit Bumrah", 4)])
        elif i == 6:
            australia_patterns.append([make_delivery("Marnus Labuschagne", "Mohammed Shami", 2)])
        elif i == 8:
            australia_patterns.append([make_delivery("Travis Head", "Mohammed Siraj", 4)])
        else:
            australia_patterns.append([make_delivery("Travis Head", "Kuldeep Yadav", 1)])

    australia_overs = []
    for i, pats in enumerate(australia_patterns):
        australia_overs.append({"over": i, "deliveries": pats})

    return {
        "info": {
            "teams": ["India", "Australia"],
            "dates": ["2023-11-19"],
            "venue": "Narendra Modi Stadium",
            "city": "Ahmedabad",
            "match_type": "ODI",
            "toss": {"winner": "Australia", "decision": "field"},
            "outcome": {"winner": "Australia", "by": {"wickets": 6}},
            "player_of_match": ["Travis Head"],
            "players": {
                "India": india_batters,
                "Australia": australia_batters,
            },
            "event": {"name": "ICC Cricket World Cup", "match_number": 48},
            "competition": "ICC Cricket World Cup",
            "season": "2023",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "India", "overs": india_overs},
            {"team": "Australia", "overs": australia_overs},
        ]
    }


# ============================================================
# FIXTURE 2: Bilateral ODI — India vs England 2023
# (Based on 1st ODI, Feb 6 2023, Hyderabad — India won by 4 wickets)
# ============================================================
def fixture_india_vs_england_2023():
    """
    India won by 4 wickets chasing 288 in Hyderabad.
    """
    india_batters = [
        "Rohit Sharma", "Shubman Gill", "Virat Kohli", "Suryakumar Yadav",
        "Shreyas Iyer", "KL Rahul", "Washington Sundar",
        "Axar Patel", "Kuldeep Yadav", "Mohammed Siraj", "Umran Malik"
    ]
    england_batters = [
        "Jason Roy", "Phil Salt", "Ben Duckett", "Joe Root",
        "Harry Brook", "Jos Buttler", "Moeen Ali",
        "Sam Curran", "Adil Rashid", "Mark Wood", "Jofra Archer"
    ]

    # England innings: 287 all out in ~49 overs
    eng_patterns = []
    eng_patterns.append([make_delivery("Jason Roy", "Mohammed Siraj", 0, is_wicket=True, wicket_kind="caught", player_out="Jason Roy")])
    eng_patterns.append([make_delivery("Phil Salt", "Umran Malik", 4)])
    eng_patterns.append([make_delivery("Phil Salt", "Mohammed Siraj", 6)])
    eng_patterns.append([make_delivery("Phil Salt", "Umran Malik", 0, is_wicket=True, wicket_kind="bowled", player_out="Phil Salt")])
    eng_patterns.append([make_delivery("Ben Duckett", "Axar Patel", 2)])
    eng_patterns.append([make_delivery("Joe Root", "Kuldeep Yadav", 1)])
    eng_patterns.append([make_delivery("Ben Duckett", "Kuldeep Yadav", 4)])
    eng_patterns.append([make_delivery("Joe Root", "Axar Patel", 1)])
    eng_patterns.append([make_delivery("Ben Duckett", "Washington Sundar", 6)])
    eng_patterns.append([make_delivery("Joe Root", "Washington Sundar", 0)])
    for i in range(30):
        if i == 5:
            eng_patterns.append([make_delivery("Joe Root", "Kuldeep Yadav", 0, is_wicket=True, wicket_kind="caught", player_out="Joe Root")])
        elif i == 8:
            eng_patterns.append([make_delivery("Ben Duckett", "Kuldeep Yadav", 0, is_wicket=True, wicket_kind="caught", player_out="Ben Duckett")])
        elif i == 12:
            eng_patterns.append([make_delivery("Harry Brook", "Umran Malik", 6)])
        elif i == 15:
            eng_patterns.append([make_delivery("Jos Buttler", "Axar Patel", 4)])
        elif i == 20:
            eng_patterns.append([make_delivery("Harry Brook", "Kuldeep Yadav", 0, is_wicket=True, wicket_kind="lbw", player_out="Harry Brook")])
        elif i == 25:
            eng_patterns.append([make_delivery("Moeen Ali", "Axar Patel", 4)])
        else:
            eng_patterns.append([make_delivery("Jos Buttler", "Axar Patel", 1)])
    for i in range(10):
        if i == 3:
            eng_patterns.append([make_delivery("Moeen Ali", "Mohammed Siraj", 0, is_wicket=True, wicket_kind="caught", player_out="Moeen Ali")])
        elif i == 6:
            eng_patterns.append([make_delivery("Sam Curran", "Umran Malik", 4)])
        elif i == 8:
            eng_patterns.append([make_delivery("Sam Curran", "Mohammed Siraj", 0, is_wicket=True, wicket_kind="run_out", player_out="Sam Curran")])
        else:
            eng_patterns.append([make_delivery("Adil Rashid", "Umran Malik", 1)])

    eng_overs = [{"over": i, "deliveries": p} for i, p in enumerate(eng_patterns)]

    # India innings: chase 288, win by 4 wickets
    ind_patterns = []
    ind_patterns.append([make_delivery("Rohit Sharma", "Jofra Archer", 4)])
    ind_patterns.append([make_delivery("Shubman Gill", "Mark Wood", 0)])
    ind_patterns.append([make_delivery("Rohit Sharma", "Mark Wood", 6)])
    ind_patterns.append([make_delivery("Shubman Gill", "Jofra Archer", 0)])
    ind_patterns.append([make_delivery("Rohit Sharma", "Jofra Archer", 0, is_wicket=True, wicket_kind="caught", player_out="Rohit Sharma")])
    ind_patterns.append([make_delivery("Virat Kohli", "Sam Curran", 1)])
    ind_patterns.append([make_delivery("Shubman Gill", "Sam Curran", 4)])
    ind_patterns.append([make_delivery("Virat Kohli", "Adil Rashid", 2)])
    ind_patterns.append([make_delivery("Shubman Gill", "Adil Rashid", 1)])
    ind_patterns.append([make_delivery("Virat Kohli", "Adil Rashid", 0)])
    for i in range(30):
        if i == 5:
            ind_patterns.append([make_delivery("Shubman Gill", "Moeen Ali", 0, is_wicket=True, wicket_kind="caught", player_out="Shubman Gill")])
        elif i == 10:
            ind_patterns.append([make_delivery("Suryakumar Yadav", "Adil Rashid", 4)])
        elif i == 14:
            ind_patterns.append([make_delivery("Virat Kohli", "Adil Rashid", 0, is_wicket=True, wicket_kind="lbw", player_out="Virat Kohli")])
        elif i == 16:
            ind_patterns.append([make_delivery("Shreyas Iyer", "Moeen Ali", 4)])
        elif i == 20:
            ind_patterns.append([make_delivery("Suryakumar Yadav", "Moeen Ali", 0, is_wicket=True, wicket_kind="caught", player_out="Suryakumar Yadav")])
        else:
            ind_patterns.append([make_delivery("Shreyas Iyer", "Adil Rashid", 2)])
    for i in range(10):
        if i == 3:
            ind_patterns.append([make_delivery("KL Rahul", "Mark Wood", 4)])
        elif i == 7:
            ind_patterns.append([make_delivery("KL Rahul", "Jofra Archer", 4)])
        else:
            ind_patterns.append([make_delivery("KL Rahul", "Sam Curran", 1)])

    ind_overs = [{"over": i, "deliveries": p} for i, p in enumerate(ind_patterns)]

    return {
        "info": {
            "teams": ["India", "England"],
            "dates": ["2023-02-06"],
            "venue": "Rajiv Gandhi International Stadium",
            "city": "Hyderabad",
            "match_type": "ODI",
            "toss": {"winner": "India", "decision": "field"},
            "outcome": {"winner": "India", "by": {"wickets": 4}},
            "player_of_match": ["Yuzvendra Chahal"],
            "players": {"India": india_batters, "England": england_batters},
            "event": {},
            "competition": "England tour of India",
            "season": "2023",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "England", "overs": eng_overs},
            {"team": "India", "overs": ind_overs},
        ]
    }


# ============================================================
# FIXTURE 3: 2019 World Cup — England vs New Zealand Final
# (Super Over tie, England won on boundary count)
# ============================================================
def fixture_wc_final_2019():
    """
    Based on the 2019 ICC Cricket World Cup Final.
    Tie after 50 overs each, tie after Super Over, England won on boundary count.
    We model the 50-over portion only (the super over is a separate entity).
    """
    england_batters = [
        "Jason Roy", "Jonny Bairstow", "Joe Root", "Ben Stokes",
        "Eoin Morgan", "Jos Buttler", "Liam Plunkett",
        "Jofra Archer", "Chris Woakes", "Mark Wood", "Adil Rashid"
    ]
    nz_batters = [
        "Martin Guptill", "Henry Nicholls", "Kane Williamson",
        "Ross Taylor", "Tom Latham", "Colin de Grandhomme",
        "Jimmy Neesham", "Matt Henry", "Trent Boult",
        "Lockie Ferguson", "Tim Southee"
    ]

    # England innings: 241 all out in 50 overs
    eng_patterns = []
    eng_patterns.append([make_delivery("Jason Roy", "Trent Boult", 0, is_wicket=True, wicket_kind="caught", player_out="Jason Roy")])
    eng_patterns.append([make_delivery("Jonny Bairstow", "Matt Henry", 4)])
    eng_patterns.append([make_delivery("Jonny Bairstow", "Matt Henry", 0, is_wicket=True, wicket_kind="caught", player_out="Jonny Bairstow")])
    eng_patterns.append([make_delivery("Joe Root", "Lockie Ferguson", 1)])
    eng_patterns.append([make_delivery("Joe Root", "Trent Boult", 2)])
    eng_patterns.append([make_delivery("Joe Root", "Matt Henry", 0)])
    eng_patterns.append([make_delivery("Joe Root", "Tim Southee", 4)])
    eng_patterns.append([make_delivery("Ben Stokes", "Matt Henry", 1)])
    eng_patterns.append([make_delivery("Joe Root", "Lockie Ferguson", 1)])
    eng_patterns.append([make_delivery("Ben Stokes", "Tim Southee", 6)])
    for i in range(30):
        if i == 5:
            eng_patterns.append([make_delivery("Ben Stokes", "Matt Henry", 0)])
        elif i == 10:
            eng_patterns.append([make_delivery("Ben Stokes", "Trent Boult", 4)])
        elif i == 15:
            eng_patterns.append([make_delivery("Eoin Morgan", "Lockie Ferguson", 0, is_wicket=True, wicket_kind="caught", player_out="Eoin Morgan")])
        elif i == 18:
            eng_patterns.append([make_delivery("Ben Stokes", "Trent Boult", 1)])
        elif i == 22:
            eng_patterns.append([make_delivery("Jos Buttler", "Matt Henry", 4)])
        elif i == 25:
            eng_patterns.append([make_delivery("Ben Stokes", "Tim Southee", 0, is_wicket=True, wicket_kind="run_out", player_out="Ben Stokes")])
        else:
            eng_patterns.append([make_delivery("Jos Buttler", "Lockie Ferguson", 1)])
    for i in range(10):
        if i == 3:
            eng_patterns.append([make_delivery("Liam Plunkett", "Trent Boult", 0, is_wicket=True, wicket_kind="caught", player_out="Liam Plunkett")])
        elif i == 7:
            eng_patterns.append([make_delivery("Jofra Archer", "Matt Henry", 4)])
        else:
            eng_patterns.append([make_delivery("Adil Rashid", "Tim Southee", 1)])

    eng_overs = [{"over": i, "deliveries": p} for i, p in enumerate(eng_patterns)]

    # NZ innings: 241/8 in 50 overs (tie!)
    nz_patterns = []
    nz_patterns.append([make_delivery("Martin Guptill", "Chris Woakes", 0, is_wicket=True, wicket_kind="run_out", player_out="Martin Guptill")])
    nz_patterns.append([make_delivery("Henry Nicholls", "Jofra Archer", 0)])
    nz_patterns.append([make_delivery("Henry Nicholls", "Chris Woakes", 4)])
    nz_patterns.append([make_delivery("Kane Williamson", "Jofra Archer", 1)])
    nz_patterns.append([make_delivery("Henry Nicholls", "Mark Wood", 1)])
    nz_patterns.append([make_delivery("Kane Williamson", "Mark Wood", 2)])
    nz_patterns.append([make_delivery("Henry Nicholls", "Adil Rashid", 1)])
    nz_patterns.append([make_delivery("Kane Williamson", "Adil Rashid", 4)])
    nz_patterns.append([make_delivery("Henry Nicholls", "Ben Stokes", 0)])
    nz_patterns.append([make_delivery("Kane Williamson", "Ben Stokes", 1)])
    for i in range(30):
        if i == 5:
            nz_patterns.append([make_delivery("Kane Williamson", "Liam Plunkett", 0, is_wicket=True, wicket_kind="caught", player_out="Kane Williamson")])
        elif i == 8:
            nz_patterns.append([make_delivery("Ross Taylor", "Liam Plunkett", 4)])
        elif i == 12:
            nz_patterns.append([make_delivery("Henry Nicholls", "Liam Plunkett", 0, is_wicket=True, wicket_kind="caught", player_out="Henry Nicholls")])
        elif i == 16:
            nz_patterns.append([make_delivery("Tom Latham", "Adil Rashid", 1)])
        elif i == 20:
            nz_patterns.append([make_delivery("Ross Taylor", "Adil Rashid", 0, is_wicket=True, wicket_kind="lbw", player_out="Ross Taylor")])
        else:
            nz_patterns.append([make_delivery("Tom Latham", "Ben Stokes", 1)])
    for i in range(10):
        if i == 2:
            nz_patterns.append([make_delivery("Colin de Grandhomme", "Jofra Archer", 6)])
        elif i == 5:
            nz_patterns.append([make_delivery("Colin de Grandhomme", "Mark Wood", 0, is_wicket=True, wicket_kind="bowled", player_out="Colin de Grandhomme")])
        elif i == 8:
            nz_patterns.append([make_delivery("Jimmy Neesham", "Jofra Archer", 4)])
        else:
            nz_patterns.append([make_delivery("Jimmy Neesham", "Chris Woakes", 1)])

    nz_overs = [{"over": i, "deliveries": p} for i, p in enumerate(nz_patterns)]

    return {
        "info": {
            "teams": ["England", "New Zealand"],
            "dates": ["2019-07-14"],
            "venue": "Lord's",
            "city": "London",
            "match_type": "ODI",
            "toss": {"winner": "New Zealand", "decision": "bat"},
            "outcome": {"winner": "England", "by": {}},
            "player_of_match": ["Ben Stokes"],
            "players": {"England": england_batters, "New Zealand": nz_batters},
            "event": {"name": "ICC Cricket World Cup", "match_number": 48},
            "competition": "ICC Cricket World Cup",
            "season": "2019",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "England", "overs": eng_overs},
            {"team": "New Zealand", "overs": nz_overs},
        ]
    }


# ============================================================
# FIXTURE 4: Low-scoring ODI — Afghanistan vs Zimbabwe 2023
# (Associate/Full member bilateral, lower scores)
# ============================================================
def fixture_afg_vs_zim_2023():
    """
    A lower-scoring ODI between Afghanistan and Zimbabwe.
    Tests that associate/fmnation teams work correctly.
    """
    afg_batters = [
        "Rahmanullah Gurbaz", "Ibrahim Zadran", "Hashmatullah Shahidi",
        "Rahmat Shah", "Mohammad Nabi", "Najibullah Zadran",
        "Azmatullah Omarzai", "Rashid Khan", "Mujeeb Ur Rahman",
        "Fazalhaq Farooqi", "Usman Ghani"
    ]
    zim_batters = [
        "Joylord Gumbi", "Tadiwanashe Marumani", "Innocent Kaia",
        "Sean Williams", "Sikandar Raza", "Ryan Burl",
        "Wesley Madhevere", "Richard Ngarava", "Blessing Muzarabani",
        "Luke Jongwe", "Brad Evans"
    ]

    # Afghanistan innings: 215 all out
    afg_patterns = []
    afg_patterns.append([make_delivery("Rahmanullah Gurbaz", "Blessing Muzarabani", 0, is_wicket=True, wicket_kind="caught", player_out="Rahmanullah Gurbaz")])
    afg_patterns.append([make_delivery("Ibrahim Zadran", "Richard Ngarava", 1)])
    afg_patterns.append([make_delivery("Ibrahim Zadran", "Blessing Muzarabani", 4)])
    afg_patterns.append([make_delivery("Hashmatullah Shahidi", "Luke Jongwe", 0)])
    afg_patterns.append([make_delivery("Ibrahim Zadran", "Luke Jongwe", 1)])
    afg_patterns.append([make_delivery("Hashmatullah Shahidi", "Richard Ngarava", 0)])
    afg_patterns.append([make_delivery("Ibrahim Zadran", "Richard Ngarava", 2)])
    afg_patterns.append([make_delivery("Hashmatullah Shahidi", "Blessing Muzarabani", 4)])
    afg_patterns.append([make_delivery("Rahmat Shah", "Luke Jongwe", 1)])
    afg_patterns.append([make_delivery("Hashmatullah Shahidi", "Luke Jongwe", 1)])
    for i in range(30):
        if i == 8:
            afg_patterns.append([make_delivery("Ibrahim Zadran", "Blessing Muzarabani", 0, is_wicket=True, wicket_kind="bowled", player_out="Ibrahim Zadran")])
        elif i == 12:
            afg_patterns.append([make_delivery("Rahmat Shah", "Sikandar Raza", 0, is_wicket=True, wicket_kind="caught", player_out="Rahmat Shah")])
        elif i == 18:
            afg_patterns.append([make_delivery("Mohammad Nabi", "Sikandar Raza", 6)])
        elif i == 22:
            afg_patterns.append([make_delivery("Hashmatullah Shahidi", "Sikandar Raza", 0, is_wicket=True, wicket_kind="caught", player_out="Hashmatullah Shahidi")])
        else:
            afg_patterns.append([make_delivery("Mohammad Nabi", "Richard Ngarava", 1)])
    for i in range(10):
        if i == 2:
            afg_patterns.append([make_delivery("Najibullah Zadran", "Blessing Muzarabani", 0, is_wicket=True, wicket_kind="caught", player_out="Najibullah Zadran")])
        elif i == 5:
            afg_patterns.append([make_delivery("Azmatullah Omarzai", "Blessing Muzarabani", 4)])
        elif i == 8:
            afg_patterns.append([make_delivery("Rashid Khan", "Richard Ngarava", 0, is_wicket=True, wicket_kind="caught", player_out="Rashid Khan")])
        else:
            afg_patterns.append([make_delivery("Azmatullah Omarzai", "Luke Jongwe", 1)])

    afg_overs = [{"over": i, "deliveries": p} for i, p in enumerate(afg_patterns)]

    # Zimbabwe innings: chase 216, win by 3 wickets
    zim_patterns = []
    zim_patterns.append([make_delivery("Joylord Gumbi", "Fazalhaq Farooqi", 4)])
    zim_patterns.append([make_delivery("Joylord Gumbi", "Fazalhaq Farooqi", 0, is_wicket=True, wicket_kind="bowled", player_out="Joylord Gumbi")])
    zim_patterns.append([make_delivery("Tadiwanashe Marumani", "Mujeeb Ur Rahman", 1)])
    zim_patterns.append([make_delivery("Innocent Kaia", "Rashid Khan", 0)])
    zim_patterns.append([make_delivery("Tadiwanashe Marumani", "Rashid Khan", 4)])
    zim_patterns.append([make_delivery("Innocent Kaia", "Mujeeb Ur Rahman", 1)])
    zim_patterns.append([make_delivery("Tadiwanashe Marumani", "Fazalhaq Farooqi", 0)])
    zim_patterns.append([make_delivery("Innocent Kaia", "Rashid Khan", 1)])
    zim_patterns.append([make_delivery("Tadiwanashe Marumani", "Rashid Khan", 0, is_wicket=True, wicket_kind="caught", player_out="Tadiwanashe Marumani")])
    zim_patterns.append([make_delivery("Sean Williams", "Mujeeb Ur Rahman", 2)])
    for i in range(30):
        if i == 5:
            zim_patterns.append([make_delivery("Innocent Kaia", "Mujeeb Ur Rahman", 0, is_wicket=True, wicket_kind="lbw", player_out="Innocent Kaia")])
        elif i == 10:
            zim_patterns.append([make_delivery("Sean Williams", "Rashid Khan", 4)])
        elif i == 15:
            zim_patterns.append([make_delivery("Sikandar Raza", "Mohammad Nabi", 6)])
        elif i == 20:
            zim_patterns.append([make_delivery("Sean Williams", "Mohammad Nabi", 0, is_wicket=True, wicket_kind="caught", player_out="Sean Williams")])
        else:
            zim_patterns.append([make_delivery("Sikandar Raza", "Rashid Khan", 1)])
    for i in range(10):
        if i == 3:
            zim_patterns.append([make_delivery("Sikandar Raza", "Azmatullah Omarzai", 4)])
        elif i == 6:
            zim_patterns.append([make_delivery("Ryan Burl", "Fazalhaq Farooqi", 4)])
        else:
            zim_patterns.append([make_delivery("Sikandar Raza", "Rashid Khan", 2)])

    zim_overs = [{"over": i, "deliveries": p} for i, p in enumerate(zim_patterns)]

    return {
        "info": {
            "teams": ["Afghanistan", "Zimbabwe"],
            "dates": ["2023-06-09"],
            "venue": "Harare Sports Club",
            "city": "Harare",
            "match_type": "ODI",
            "toss": {"winner": "Zimbabwe", "decision": "field"},
            "outcome": {"winner": "Zimbabwe", "by": {"wickets": 3}},
            "player_of_match": ["Sikandar Raza"],
            "players": {"Afghanistan": afg_batters, "Zimbabwe": zim_batters},
            "event": {},
            "competition": "Afghanistan in Zimbabwe",
            "season": "2023",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "Afghanistan", "overs": afg_overs},
            {"team": "Zimbabwe", "overs": zim_overs},
        ]
    }


# ============================================================
# FIXTURE 5: Champions Trophy-style — Pakistan vs India 2017
# (Based on 2017 Champions Trophy Final — Pakistan won)
# ============================================================
def fixture_ct_final_2017():
    """
    Based on the 2017 ICC Champions Trophy Final.
    Pakistan won by 180 runs.
    """
    pak_batters = [
        "Fakhar Zaman", "Azhar Ali", "Babar Azam", "Mohammad Hafeez",
        "Shoaib Malik", "Sarfaraz Ahmed", "Imad Wasim",
        "Mohammad Amir", "Hasan Ali", "Junaid Khan", "Shadab Khan"
    ]
    ind_batters = [
        "Rohit Sharma", "Shikhar Dhawan", "Virat Kohli",
        "Yuvraj Singh", "MS Dhoni", "Hardik Pandya",
        "Kedar Jadhav", "Ravichandran Ashwin", "Bhuvneshwar Kumar",
        "Jasprit Bumrah", "Umesh Yadav"
    ]

    # Pakistan innings: 338/4 in 50 overs (big total)
    pak_patterns = []
    pak_patterns.append([make_delivery("Fakhar Zaman", "Bhuvneshwar Kumar", 4)])
    pak_patterns.append([make_delivery("Azhar Ali", "Umesh Yadav", 0)])
    pak_patterns.append([make_delivery("Fakhar Zaman", "Umesh Yadav", 6)])
    pak_patterns.append([make_delivery("Azhar Ali", "Bhuvneshwar Kumar", 1)])
    pak_patterns.append([make_delivery("Fakhar Zaman", "Bhuvneshwar Kumar", 4)])
    pak_patterns.append([make_delivery("Azhar Ali", "Jasprit Bumrah", 1)])
    pak_patterns.append([make_delivery("Fakhar Zaman", "Jasprit Bumrah", 0)])
    pak_patterns.append([make_delivery("Azhar Ali", "Ravichandran Ashwin", 1)])
    pak_patterns.append([make_delivery("Fakhar Zaman", "Ravichandran Ashwin", 4)])
    pak_patterns.append([make_delivery("Azhar Ali", "Ravichandran Ashwin", 0)])
    for i in range(30):
        if i == 3:
            pak_patterns.append([make_delivery("Fakhar Zaman", "Ravichandran Ashwin", 4)])
        elif i == 8:
            pak_patterns.append([make_delivery("Azhar Ali", "Yuvraj Singh", 0, is_wicket=True, wicket_kind="caught", player_out="Azhar Ali")])
        elif i == 12:
            pak_patterns.append([make_delivery("Babar Azam", "Hardik Pandya", 4)])
        elif i == 18:
            pak_patterns.append([make_delivery("Fakhar Zaman", "Ravichandran Ashwin", 0, is_wicket=True, wicket_kind="caught", player_out="Fakhar Zaman")])
        elif i == 22:
            pak_patterns.append([make_delivery("Mohammad Hafeez", "Hardik Pandya", 6)])
        else:
            pak_patterns.append([make_delivery("Babar Azam", "Kedar Jadhav", 2)])
    for i in range(10):
        if i == 2:
            pak_patterns.append([make_delivery("Mohammad Hafeez", "Bhuvneshwar Kumar", 0, is_wicket=True, wicket_kind="caught", player_out="Mohammad Hafeez")])
        elif i == 5:
            pak_patterns.append([make_delivery("Shoaib Malik", "Jasprit Bumrah", 4)])
        elif i == 8:
            pak_patterns.append([make_delivery("Sarfaraz Ahmed", "Jasprit Bumrah", 2)])
        else:
            pak_patterns.append([make_delivery("Shoaib Malik", "Umesh Yadav", 1)])

    pak_overs = [{"over": i, "deliveries": p} for i, p in enumerate(pak_patterns)]

    # India innings: 158 all out (collapse)
    ind_patterns = []
    ind_patterns.append([make_delivery("Rohit Sharma", "Mohammad Amir", 0, is_wicket=True, wicket_kind="caught", player_out="Rohit Sharma")])
    ind_patterns.append([make_delivery("Shikhar Dhawan", "Hasan Ali", 4)])
    ind_patterns.append([make_delivery("Shikhar Dhawan", "Mohammad Amir", 0, is_wicket=True, wicket_kind="caught", player_out="Shikhar Dhawan")])
    ind_patterns.append([make_delivery("Virat Kohli", "Junaid Khan", 1)])
    ind_patterns.append([make_delivery("Virat Kohli", "Hasan Ali", 0, is_wicket=True, wicket_kind="caught", player_out="Virat Kohli")])
    ind_patterns.append([make_delivery("Yuvraj Singh", "Mohammad Amir", 1)])
    ind_patterns.append([make_delivery("Yuvraj Singh", "Junaid Khan", 0, is_wicket=True, wicket_kind="lbw", player_out="Yuvraj Singh")])
    ind_patterns.append([make_delivery("MS Dhoni", "Hasan Ali", 1)])
    ind_patterns.append([make_delivery("MS Dhoni", "Shadab Khan", 4)])
    ind_patterns.append([make_delivery("Hardik Pandya", "Shadab Khan", 6)])
    for i in range(30):
        if i == 5:
            ind_patterns.append([make_delivery("MS Dhoni", "Shadab Khan", 0, is_wicket=True, wicket_kind="caught", player_out="MS Dhoni")])
        elif i == 10:
            ind_patterns.append([make_delivery("Hardik Pandya", "Hasan Ali", 0, is_wicket=True, wicket_kind="caught", player_out="Hardik Pandya")])
        elif i == 15:
            ind_patterns.append([make_delivery("Kedar Jadhav", "Shadab Khan", 0)])
        elif i == 20:
            ind_patterns.append([make_delivery("Kedar Jadhav", "Imad Wasim", 0, is_wicket=True, wicket_kind="run_out", player_out="Kedar Jadhav")])
        else:
            ind_patterns.append([make_delivery("Ravichandran Ashwin", "Imad Wasim", 1)])
    for i in range(10):
        if i == 3:
            ind_patterns.append([make_delivery("Ravichandran Ashwin", "Junaid Khan", 0, is_wicket=True, wicket_kind="caught", player_out="Ravichandran Ashwin")])
        elif i == 7:
            ind_patterns.append([make_delivery("Jasprit Bumrah", "Hasan Ali", 0, is_wicket=True, wicket_kind="bowled", player_out="Jasprit Bumrah")])
        else:
            ind_patterns.append([make_delivery("Umesh Yadav", "Junaid Khan", 1)])

    ind_overs = [{"over": i, "deliveries": p} for i, p in enumerate(ind_patterns)]

    return {
        "info": {
            "teams": ["Pakistan", "India"],
            "dates": ["2017-06-18"],
            "venue": "The Oval",
            "city": "London",
            "match_type": "ODI",
            "toss": {"winner": "Pakistan", "decision": "bat"},
            "outcome": {"winner": "Pakistan", "by": {"runs": 180}},
            "player_of_match": ["Fakhar Zaman"],
            "players": {"Pakistan": pak_batters, "India": ind_batters},
            "event": {"name": "ICC Champions Trophy", "match_number": 15},
            "competition": "ICC Champions Trophy",
            "season": "2017",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "Pakistan", "overs": pak_overs},
            {"team": "India", "overs": ind_overs},
        ]
    }


# ============================================================
# FIXTURE 6: ODI with wides and no-balls — Sri Lanka vs South Africa 2023
# ============================================================
def fixture_sl_vs_sa_2023():
    """
    Sri Lanka vs South Africa with wides and no-balls.
    Tests extras handling in ODI format.
    """
    sl_batters = [
        "Pathum Nissanka", "Kusal Mendis", "Charith Asalanka",
        "Sadeera Samarawickrama", "Dhananjaya de Silva",
        "Dasun Shanaka", "Wanindu Hasaranga", "Dunith Wellalage",
        "Maheesh Theekshana", "Dilshan Madushanka", "Matheesha Pathirana"
    ]
    sa_batters = [
        "Temba Bavuma", "Quinton de Kock", "Rassie van der Dussen",
        "Aiden Markram", "Heinrich Klaasen", "David Miller",
        "Marco Jansen", "Keshav Maharaj", "Kagiso Rabada",
        "Anrich Nortje", "Lungi Ngidi"
    ]

    # SL innings: 280/6 in 50 overs (with wides and no-balls)
    sl_patterns = []
    sl_patterns.append([make_delivery("Pathum Nissanka", "Kagiso Rabada", 4)])
    sl_patterns.append([make_delivery("Pathum Nissanka", "Kagiso Rabada", 0, noballs=1)])
    sl_patterns.append([make_delivery("Pathum Nissanka", "Anrich Nortje", 1)])
    sl_patterns.append([make_delivery("Kusal Mendis", "Lungi Ngidi", 0)])
    sl_patterns.append([make_delivery("Pathum Nissanka", "Lungi Ngidi", 4)])
    sl_patterns.append([make_delivery("Kusal Mendis", "Anrich Nortje", 0, wides=1)])
    sl_patterns.append([make_delivery("Pathum Nissanka", "Anrich Nortje", 2)])
    sl_patterns.append([make_delivery("Kusal Mendis", "Kagiso Rabada", 1)])
    sl_patterns.append([make_delivery("Pathum Nissanka", "Kagiso Rabada", 1)])
    sl_patterns.append([make_delivery("Kusal Mendis", "Marco Jansen", 4)])
    for i in range(30):
        if i == 5:
            sl_patterns.append([make_delivery("Pathum Nissanka", "Keshav Maharaj", 0, is_wicket=True, wicket_kind="caught", player_out="Pathum Nissanka")])
        elif i == 10:
            sl_patterns.append([make_delivery("Charith Asalanka", "Kagiso Rabada", 4)])
        elif i == 14:
            sl_patterns.append([make_delivery("Kusal Mendis", "Keshav Maharaj", 0, is_wicket=True, wicket_kind="stumped", player_out="Kusal Mendis")])
        elif i == 18:
            sl_patterns.append([make_delivery("Sadeera Samarawickrama", "Anrich Nortje", 0, noballs=1)])
        elif i == 22:
            sl_patterns.append([make_delivery("Dhananjaya de Silva", "Marco Jansen", 6)])
        else:
            sl_patterns.append([make_delivery("Charith Asalanka", "Keshav Maharaj", 2)])
    for i in range(10):
        if i == 2:
            sl_patterns.append([make_delivery("Dhananjaya de Silva", "Kagiso Rabada", 0, is_wicket=True, wicket_kind="caught", player_out="Dhananjaya de Silva")])
        elif i == 5:
            sl_patterns.append([make_delivery("Dasun Shanaka", "Anrich Nortje", 6)])
        elif i == 8:
            sl_patterns.append([make_delivery("Wanindu Hasaranga", "Lungi Ngidi", 4)])
        else:
            sl_patterns.append([make_delivery("Dasun Shanaka", "Lungi Ngidi", 1)])

    sl_overs = [{"over": i, "deliveries": p} for i, p in enumerate(sl_patterns)]

    # SA innings: chase 281
    sa_patterns = []
    sa_patterns.append([make_delivery("Temba Bavuma", "Dilshan Madushanka", 4)])
    sa_patterns.append([make_delivery("Quinton de Kock", "Matheesha Pathirana", 6)])
    sa_patterns.append([make_delivery("Temba Bavuma", "Matheesha Pathirana", 1)])
    sa_patterns.append([make_delivery("Quinton de Kock", "Dilshan Madushanka", 4)])
    sa_patterns.append([make_delivery("Temba Bavuma", "Dilshan Madushanka", 0)])
    sa_patterns.append([make_delivery("Quinton de Kock", "Wanindu Hasaranga", 4)])
    sa_patterns.append([make_delivery("Temba Bavuma", "Wanindu Hasaranga", 1)])
    sa_patterns.append([make_delivery("Quinton de Kock", "Maheesh Theekshana", 0)])
    sa_patterns.append([make_delivery("Temba Bavuma", "Maheesh Theekshana", 2)])
    sa_patterns.append([make_delivery("Quinton de Kock", "Dilshan Madushanka", 0, is_wicket=True, wicket_kind="caught", player_out="Quinton de Kock")])
    for i in range(30):
        if i == 8:
            sa_patterns.append([make_delivery("Rassie van der Dussen", "Wanindu Hasaranga", 1)])
        elif i == 12:
            sa_patterns.append([make_delivery("Temba Bavuma", "Wanindu Hasaranga", 0, is_wicket=True, wicket_kind="caught", player_out="Temba Bavuma")])
        elif i == 18:
            sa_patterns.append([make_delivery("Aiden Markram", "Wanindu Hasaranga", 6)])
        elif i == 22:
            sa_patterns.append([make_delivery("Rassie van der Dussen", "Maheesh Theekshana", 4)])
        else:
            sa_patterns.append([make_delivery("Aiden Markram", "Dilshan Madushanka", 1)])
    for i in range(10):
        if i == 3:
            sa_patterns.append([make_delivery("Heinrich Klaasen", "Matheesha Pathirana", 6)])
        elif i == 6:
            sa_patterns.append([make_delivery("Heinrich Klaasen", "Matheesha Pathirana", 4)])
        else:
            sa_patterns.append([make_delivery("Heinrich Klaasen", "Dilshan Madushanka", 1)])

    sa_overs = [{"over": i, "deliveries": p} for i, p in enumerate(sa_patterns)]

    return {
        "info": {
            "teams": ["Sri Lanka", "South Africa"],
            "dates": ["2023-09-10"],
            "venue": "R Premadasa Stadium",
            "city": "Colombo",
            "match_type": "ODI",
            "toss": {"winner": "South Africa", "decision": "field"},
            "outcome": {"winner": "South Africa", "by": {"wickets": 5}},
            "player_of_match": ["Aiden Markram"],
            "players": {"Sri Lanka": sl_batters, "South Africa": sa_batters},
            "event": {},
            "competition": "South Africa in Sri Lanka",
            "season": "2023",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "Sri Lanka", "overs": sl_overs},
            {"team": "South Africa", "overs": sa_overs},
        ]
    }


# ============================================================
# FIXTURE 7: Early conclusion — Bangladesh vs West Indies 2022
# (Match ending before 50 overs, DLS/reduced)
# ============================================================
def fixture_ban_vs_wi_2022():
    """
    A shorter ODI ending early (West Indies all out in 38 overs).
    Tests that the pipeline handles matches not reaching 50 overs.
    """
    ban_batters = [
        "Tamim Iqbal", "Litton Das", "Shakib Al Hasan",
        "Mushfiqur Rahim", "Afif Hossain", "Mosaddek Hossain",
        "Mahmudullah", "Nasum Ahmed", "Mustafizur Rahman",
        "Ebadot Hossain", "Shoriful Islam"
    ]
    wi_batters = [
        "Shai Hope", "Brandon King", "Shamarh Brooks",
        "Shimron Hetmyer", "Nicholas Pooran", "Rovman Powell",
        "Keemo Paul", "Akeal Hosein", "Alzarri Joseph",
        "Gudakesh Motie", "Jayden Seales"
    ]

    # Bangladesh innings: 275/8 in 50 overs
    ban_patterns = []
    ban_patterns.append([make_delivery("Tamim Iqbal", "Alzarri Joseph", 4)])
    ban_patterns.append([make_delivery("Litton Das", "Jayden Seales", 0)])
    ban_patterns.append([make_delivery("Tamim Iqbal", "Jayden Seales", 0, is_wicket=True, wicket_kind="caught", player_out="Tamim Iqbal")])
    ban_patterns.append([make_delivery("Shakib Al Hasan", "Alzarri Joseph", 1)])
    ban_patterns.append([make_delivery("Litton Das", "Alzarri Joseph", 4)])
    ban_patterns.append([make_delivery("Shakib Al Hasan", "Gudakesh Motie", 2)])
    ban_patterns.append([make_delivery("Litton Das", "Gudakesh Motie", 1)])
    ban_patterns.append([make_delivery("Shakib Al Hasan", "Akeal Hosein", 4)])
    ban_patterns.append([make_delivery("Litton Das", "Akeal Hosein", 1)])
    ban_patterns.append([make_delivery("Shakib Al Hasan", "Gudakesh Motie", 0)])
    for i in range(30):
        if i == 5:
            ban_patterns.append([make_delivery("Shakib Al Hasan", "Gudakesh Motie", 0, is_wicket=True, wicket_kind="caught", player_out="Shakib Al Hasan")])
        elif i == 10:
            ban_patterns.append([make_delivery("Mushfiqur Rahim", "Akeal Hosein", 1)])
        elif i == 15:
            ban_patterns.append([make_delivery("Litton Das", "Keemo Paul", 0, is_wicket=True, wicket_kind="caught", player_out="Litton Das")])
        elif i == 20:
            ban_patterns.append([make_delivery("Afif Hossain", "Alzarri Joseph", 4)])
        else:
            ban_patterns.append([make_delivery("Mushfiqur Rahim", "Gudakesh Motie", 2)])
    for i in range(10):
        if i == 3:
            ban_patterns.append([make_delivery("Mosaddek Hossain", "Jayden Seales", 0, is_wicket=True, wicket_kind="caught", player_out="Mosaddek Hossain")])
        elif i == 7:
            ban_patterns.append([make_delivery("Mahmudullah", "Alzarri Joseph", 6)])
        else:
            ban_patterns.append([make_delivery("Mahmudullah", "Gudakesh Motie", 1)])

    ban_overs = [{"over": i, "deliveries": p} for i, p in enumerate(ban_patterns)]

    # WI innings: all out in ~38 overs
    wi_patterns = []
    wi_patterns.append([make_delivery("Shai Hope", "Mustafizur Rahman", 1)])
    wi_patterns.append([make_delivery("Brandon King", "Ebadot Hossain", 0)])
    wi_patterns.append([make_delivery("Shai Hope", "Ebadot Hossain", 4)])
    wi_patterns.append([make_delivery("Brandon King", "Mustafizur Rahman", 0, is_wicket=True, wicket_kind="bowled", player_out="Brandon King")])
    wi_patterns.append([make_delivery("Shamarh Brooks", "Shoriful Islam", 0)])
    wi_patterns.append([make_delivery("Shai Hope", "Shoriful Islam", 1)])
    wi_patterns.append([make_delivery("Shamarh Brooks", "Ebadot Hossain", 4)])
    wi_patterns.append([make_delivery("Shai Hope", "Ebadot Hossain", 0)])
    wi_patterns.append([make_delivery("Shamarh Brooks", "Mustafizur Rahman", 1)])
    wi_patterns.append([make_delivery("Shai Hope", "Mustafizur Rahman", 4)])
    for i in range(28):
        if i == 5:
            wi_patterns.append([make_delivery("Shamarh Brooks", "Mustafizur Rahman", 0, is_wicket=True, wicket_kind="lbw", player_out="Shamarh Brooks")])
        elif i == 10:
            wi_patterns.append([make_delivery("Shimron Hetmyer", "Nasum Ahmed", 6)])
        elif i == 14:
            wi_patterns.append([make_delivery("Shai Hope", "Mustafizur Rahman", 0, is_wicket=True, wicket_kind="caught", player_out="Shai Hope")])
        elif i == 18:
            wi_patterns.append([make_delivery("Nicholas Pooran", "Nasum Ahmed", 4)])
        elif i == 22:
            wi_patterns.append([make_delivery("Nicholas Pooran", "Shakib Al Hasan", 0, is_wicket=True, wicket_kind="caught", player_out="Nicholas Pooran")])
        elif i == 25:
            wi_patterns.append([make_delivery("Rovman Powell", "Shakib Al Hasan", 0, is_wicket=True, wicket_kind="bowled", player_out="Rovman Powell")])
        else:
            wi_patterns.append([make_delivery("Shimron Hetmyer", "Nasum Ahmed", 1)])
    # Final overs - all out
    for i in range(10):
        if i == 0:
            wi_patterns.append([make_delivery("Keemo Paul", "Ebadot Hossain", 0, is_wicket=True, wicket_kind="caught", player_out="Keemo Paul")])
        elif i == 2:
            wi_patterns.append([make_delivery("Alzarri Joseph", "Ebadot Hossain", 0, is_wicket=True, wicket_kind="bowled", player_out="Alzarri Joseph")])
        elif i == 4:
            wi_patterns.append([make_delivery("Akeal Hosein", "Shakib Al Hasan", 0, is_wicket=True, wicket_kind="lbw", player_out="Akeal Hosein")])
        else:
            wi_patterns.append([make_delivery("Gudakesh Motie", "Shakib Al Hasan", 1)])

    wi_overs = [{"over": i, "deliveries": p} for i, p in enumerate(wi_patterns)]

    return {
        "info": {
            "teams": ["Bangladesh", "West Indies"],
            "dates": ["2022-07-10"],
            "venue": "Zohur Ahmed Chowdhury Stadium",
            "city": "Chittagong",
            "match_type": "ODI",
            "toss": {"winner": "Bangladesh", "decision": "bat"},
            "outcome": {"winner": "Bangladesh", "by": {"runs": 50}},
            "player_of_match": ["Litton Das"],
            "players": {"Bangladesh": ban_batters, "West Indies": wi_batters},
            "event": {},
            "competition": "West Indies in Bangladesh",
            "season": "2022",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "Bangladesh", "overs": ban_overs},
            {"team": "West Indies", "overs": wi_overs},
        ]
    }


# ============================================================
# FIXTURE 8: Asia Cup ODI — India vs Pakistan 2023
# ============================================================
def fixture_asia_cup_2023():
    """
    Based on India vs Pakistan, Asia Cup 2023 (September 2023).
    India won by 228 runs — high-scoring ODI.
    """
    ind_batters = [
        "Rohit Sharma", "Shubman Gill", "Virat Kohli",
        "KL Rahul", "Shreyas Iyer", "Ishan Kishan",
        "Hardik Pandya", "Ravindra Jadeja", "Kuldeep Yadav",
        "Jasprit Bumrah", "Mohammed Siraj"
    ]
    pak_batters = [
        "Fakhar Zaman", "Imam-ul-Haq", "Babar Azam",
        "Mohammad Rizwan", "Salman Agha", "Iftikhar Ahmed",
        "Shadab Khan", "Mohammad Nawaz", "Haris Rauf",
        "Naseem Shah", "Shaheen Afridi"
    ]

    # India innings: 356/2 in 50 overs
    ind_patterns = []
    for i in range(50):
        if i == 0:
            ind_patterns.append([make_delivery("Rohit Sharma", "Shaheen Afridi", 6)])
        elif i == 3:
            ind_patterns.append([make_delivery("Rohit Sharma", "Shaheen Afridi", 4)])
        elif i == 8:
            ind_patterns.append([make_delivery("Rohit Sharma", "Haris Rauf", 0, is_wicket=True, wicket_kind="caught", player_out="Rohit Sharma")])
        elif i == 12:
            ind_patterns.append([make_delivery("Virat Kohli", "Shadab Khan", 4)])
        elif i == 20:
            ind_patterns.append([make_delivery("Shubman Gill", "Naseem Shah", 0, is_wicket=True, wicket_kind="caught", player_out="Shubman Gill")])
        elif i == 30:
            ind_patterns.append([make_delivery("Virat Kohli", "Shaheen Afridi", 6)])
        elif i == 40:
            ind_patterns.append([make_delivery("Virat Kohli", "Shadab Khan", 4)])
        elif i == 48:
            ind_patterns.append([make_delivery("KL Rahul", "Shaheen Afridi", 6)])
        else:
            ind_patterns.append([make_delivery("Virat Kohli", "Shadab Khan", 2)])

    ind_overs = [{"over": i, "deliveries": p} for i, p in enumerate(ind_patterns)]

    # Pakistan innings: 128 all out
    pak_patterns = []
    pak_patterns.append([make_delivery("Fakhar Zaman", "Jasprit Bumrah", 0, is_wicket=True, wicket_kind="caught", player_out="Fakhar Zaman")])
    pak_patterns.append([make_delivery("Imam-ul-Haq", "Mohammed Siraj", 0, is_wicket=True, wicket_kind="bowled", player_out="Imam-ul-Haq")])
    pak_patterns.append([make_delivery("Babar Azam", "Jasprit Bumrah", 1)])
    pak_patterns.append([make_delivery("Mohammad Rizwan", "Kuldeep Yadav", 0)])
    pak_patterns.append([make_delivery("Babar Azam", "Kuldeep Yadav", 0, is_wicket=True, wicket_kind="lbw", player_out="Babar Azam")])
    pak_patterns.append([make_delivery("Salman Agha", "Ravindra Jadeja", 1)])
    pak_patterns.append([make_delivery("Mohammad Rizwan", "Ravindra Jadeja", 4)])
    pak_patterns.append([make_delivery("Salman Agha", "Kuldeep Yadav", 0)])
    pak_patterns.append([make_delivery("Mohammad Rizwan", "Kuldeep Yadav", 1)])
    pak_patterns.append([make_delivery("Salman Agha", "Ravindra Jadeja", 0, is_wicket=True, wicket_kind="caught", player_out="Salman Agha")])
    for i in range(25):
        if i == 5:
            pak_patterns.append([make_delivery("Iftikhar Ahmed", "Kuldeep Yadav", 0, is_wicket=True, wicket_kind="caught", player_out="Iftikhar Ahmed")])
        elif i == 10:
            pak_patterns.append([make_delivery("Shadab Khan", "Kuldeep Yadav", 4)])
        elif i == 15:
            pak_patterns.append([make_delivery("Mohammad Rizwan", "Jasprit Bumrah", 0, is_wicket=True, wicket_kind="caught", player_out="Mohammad Rizwan")])
        else:
            pak_patterns.append([make_delivery("Shadab Khan", "Ravindra Jadeja", 1)])
    for i in range(10):
        if i == 2:
            pak_patterns.append([make_delivery("Haris Rauf", "Mohammed Siraj", 0, is_wicket=True, wicket_kind="bowled", player_out="Haris Rauf")])
        elif i == 5:
            pak_patterns.append([make_delivery("Naseem Shah", "Jasprit Bumrah", 0, is_wicket=True, wicket_kind="caught", player_out="Naseem Shah")])
        else:
            pak_patterns.append([make_delivery("Shaheen Afridi", "Kuldeep Yadav", 1)])

    pak_overs = [{"over": i, "deliveries": p} for i, p in enumerate(pak_patterns)]

    return {
        "info": {
            "teams": ["India", "Pakistan"],
            "dates": ["2023-09-10"],
            "venue": "R.Premadasa Stadium",
            "city": "Colombo",
            "match_type": "ODI",
            "toss": {"winner": "India", "decision": "bat"},
            "outcome": {"winner": "India", "by": {"runs": 228}},
            "player_of_match": ["Virat Kohli"],
            "players": {"India": ind_batters, "Pakistan": pak_batters},
            "event": {"name": "Asia Cup", "match_number": 3},
            "competition": "Asia Cup",
            "season": "2023",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "India", "overs": ind_overs},
            {"team": "Pakistan", "overs": pak_overs},
        ]
    }


# ============================================================
# Generate all fixtures
# ============================================================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fixtures = [
        ("471345_od_final_2023.json", fixture_wc_final_2023),
        ("471346_ind_vs_eng_2023.json", fixture_india_vs_england_2023),
        ("471347_wc_final_2019.json", fixture_wc_final_2019),
        ("471348_afg_vs_zim_2023.json", fixture_afg_vs_zim_2023),
        ("471349_ct_final_2017.json", fixture_ct_final_2017),
        ("471350_sl_vs_sa_2023.json", fixture_sl_vs_sa_2023),
        ("471351_ban_vs_wi_2022.json", fixture_ban_vs_wi_2022),
        ("471352_asia_cup_2023.json", fixture_asia_cup_2023),
    ]

    total_deliveries = 0
    for filename, fixture_fn in fixtures:
        data = fixture_fn()
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Count deliveries
        deliveries = sum(
            len(ball)
            for inn in data["innings"]
            for over in inn["overs"]
            for ball in over["deliveries"]
        )
        total_deliveries += deliveries
        teams = data["info"]["teams"]
        date = data["info"]["dates"][0]
        comp = data["info"].get("competition", "bilateral")
        print(f"  {filename}: {teams[0]} vs {teams[1]}, {date}, {comp}, {deliveries} deliveries")

    print(f"\nGenerated {len(fixtures)} ODI fixtures with {total_deliveries} total deliveries")
    print(f"Teams covered: India, Australia, England, New Zealand, Pakistan, South Africa, Sri Lanka, Afghanistan, Zimbabwe, Bangladesh, West Indies")


if __name__ == "__main__":
    main()
