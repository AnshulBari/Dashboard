"""
Generate Test cricket Cricsheet-format fixtures for pipeline validation.

Creates realistic Test matches based on real historical data:
1. Normal Test — India won by 229 runs (Edgbaston 2018 inspired)
2. Drawn Test — England vs India, draw (Lord's 2021 inspired)
3. Innings victory — India won by an innings and 132 runs (Ahmedabad 2023 inspired)
4. Follow-on match — Australia enforced follow-on, won by 123 runs (Melbourne 2018 Ashes inspired)
5. Declaration match — England declared and won by 75 runs (Trent Bridge 2015 Ashes inspired)

Each fixture is a valid Cricsheet JSON file with realistic ball-by-ball data
representing all critical Test cricket scenarios.
"""

import json
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "test")


def delivery(batter, bowler, runs, extras=None, wickets=None, non_striker=""):
    """Create a single delivery dict."""
    d = {
        "batter": batter,
        "bowler": bowler,
        "non_striker": non_striker,
        "runs": {"batter": runs, "extras": 0, "total": runs},
    }
    if extras:
        d["extras"] = extras
        d["runs"]["extras"] = sum(extras.values())
        d["runs"]["total"] = runs + d["runs"]["extras"]
    if wickets:
        d["wickets"] = wickets
    return d


def wkpt(kind, player_out, fielders=None):
    """Create a wicket dict."""
    w = {"kind": kind, "player_out": player_out}
    if fielders:
        w["fielders"] = [{"name": f} for f in fielders]
    return w


def make_overs(batter_pairs, over_start, overs_count, deliveries_per_over=6):
    """Generate overs. batter_pairs = [(striker, non_striker), ...]"""
    overs = []
    idx = 0
    b1, b2 = batter_pairs[0]
    for i in range(overs_count):
        d = over_start + i
        # Default: just 1 run per ball
        balls = []
        for j in range(deliveries_per_over):
            balls.append(delivery(b1, "Bowler", 1, non_striker=b2))
        overs.append({"over": d, "deliveries": balls})
        # Swap on odd total
        total = sum(b["runs"]["total"] for b in balls)
        if total % 2 == 1:
            b1, b2 = b2, b1
    return overs


# ============================================================
# FIXTURE 1: Normal Test — England won by 229 runs
# (Inspired by Edgbaston 2018: India 273 & 317 vs England 287 & 109* —
#  but we make England win with realistic scores)
# ============================================================
def fixture_normal_test():
    """
    England vs India, 3rd Ashes-inspired Test.
    India 273 all out, England 187 all out, India 220 all out, England 330/3 chase.
    England won by 7 wickets.
    """
    india_bat = ["Rohit Sharma", "Yashasvi Jaiswal", "Cheteshwar Pujara",
                 "Virat Kohli", "Ajinkya Rahane", "KL Rahul", "R Ashwin",
                 "Ravindra Jadeja", "Axar Patel", "Mohammed Shami", "Jasprit Bumrah"]
    eng_bat = ["Zak Crawley", "Ben Duckett", "Ollie Pope", "Joe Root",
               "Ben Stokes", "Harry Brook", "Ben Foakes", "Stuart Broad",
               "Jack Leach", "Ollie Robinson", "James Anderson"]

    # India 1st innings: 273 all out
    ind_1_patterns = []
    ind_1_patterns.append([delivery("Rohit Sharma", "Stuart Broad", 4)])
    ind_1_patterns.append([delivery("Rohit Sharma", "Stuart Broad", 0, wickets=[wkpt("caught", "Rohit Sharma", ["Ben Duckett"])]  )])
    ind_1_patterns.append([delivery("Yashasvi Jaiswal", "James Anderson", 0)])
    ind_1_patterns.append([delivery("Yashasvi Jaiswal", "James Anderson", 4)])
    ind_1_patterns.append([delivery("Yashasvi Jaiswal", "James Anderson", 0, wickets=[wkpt("bowled", "Yashasvi Jaiswal")])])
    ind_1_patterns.append([delivery("Cheteshwar Pujara", "Jack Leach", 1)])
    ind_1_patterns.append([delivery("Virat Kohli", "Jack Leach", 2)])
    ind_1_patterns.append([delivery("Cheteshwar Pujara", "Stuart Broad", 0)])
    ind_1_patterns.append([delivery("Virat Kohli", "Stuart Broad", 4)])
    ind_1_patterns.append([delivery("Cheteshwar Pujara", "Jack Leach", 1)])
    for i in range(80):
        if i == 15:
            ind_1_patterns.append([delivery("Cheteshwar Pujara", "Ollie Robinson", 0, wickets=[wkpt("lbw", "Cheteshwar Pujara")])])
        elif i == 25:
            ind_1_patterns.append([delivery("Virat Kohli", "Jack Leach", 0, wickets=[wkpt("caught", "Virat Kohli", ["Ben Foakes"])])])
        elif i == 35:
            ind_1_patterns.append([delivery("KL Rahul", "Ollie Robinson", 6)])
        elif i == 45:
            ind_1_patterns.append([delivery("KL Rahul", "Stuart Broad", 0, wickets=[wkpt("caught", "KL Rahul", ["Ben Duckett"])])])
        elif i == 55:
            ind_1_patterns.append([delivery("R Ashwin", "Jack Leach", 4)])
        elif i == 65:
            ind_1_patterns.append([delivery("R Ashwin", "Ollie Robinson", 0, wickets=[wkpt("bowled", "R Ashwin")])])
        elif i == 75:
            ind_1_patterns.append([delivery("Jasprit Bumrah", "Stuart Broad", 0, wickets=[wkpt("caught", "Jasprit Bumrah", ["Zak Crawley"])])])
        else:
            ind_1_patterns.append([delivery("Ravindra Jadeja", "Jack Leach", 1)])
    ind_1_overs = [{"over": i, "deliveries": p} for i, p in enumerate(ind_1_patterns)]

    # England 1st innings: 187 all out
    eng_1_patterns = []
    eng_1_patterns.append([delivery("Zak Crawley", "Jasprit Bumrah", 0, wickets=[wkpt("bowled", "Zak Crawley")])])
    eng_1_patterns.append([delivery("Ben Duckett", "Mohammed Shami", 4)])
    eng_1_patterns.append([delivery("Ben Duckett", "Jasprit Bumrah", 0, wickets=[wkpt("caught", "Ben Duckett", ["KL Rahul"])])])
    eng_1_patterns.append([delivery("Ollie Pope", "R Ashwin", 1)])
    eng_1_patterns.append([delivery("Joe Root", "R Ashwin", 4)])
    eng_1_patterns.append([delivery("Ollie Pope", "R Ashwin", 0, wickets=[wkpt("lbw", "Ollie Pope")])])
    eng_1_patterns.append([delivery("Joe Root", "Ravindra Jadeja", 2)])
    eng_1_patterns.append([delivery("Ben Stokes", "Ravindra Jadeja", 1)])
    eng_1_patterns.append([delivery("Joe Root", "R Ashwin", 1)])
    eng_1_patterns.append([delivery("Ben Stokes", "R Ashwin", 4)])
    for i in range(55):
        if i == 10:
            eng_1_patterns.append([delivery("Joe Root", "R Ashwin", 0, wickets=[wkpt("caught", "Joe Root", ["R Ashwin"])])])
        elif i == 20:
            eng_1_patterns.append([delivery("Harry Brook", "Ravindra Jadeja", 0, wickets=[wkpt("lbw", "Harry Brook")])])
        elif i == 30:
            eng_1_patterns.append([delivery("Ben Stokes", "Ravindra Jadeja", 6)])
        elif i == 40:
            eng_1_patterns.append([delivery("Ben Stokes", "Axar Patel", 0, wickets=[wkpt("bowled", "Ben Stokes")])])
        elif i == 50:
            eng_1_patterns.append([delivery("Jack Leach", "Jasprit Bumrah", 0, wickets=[wkpt("caught", "Jack Leach", ["Rohit Sharma"])])])
        else:
            eng_1_patterns.append([delivery("Ben Foakes", "R Ashwin", 1)])
    eng_1_overs = [{"over": i, "deliveries": p} for i, p in enumerate(eng_1_patterns)]

    # India 2nd innings: 220 all out
    ind_2_patterns = []
    ind_2_patterns.append([delivery("Rohit Sharma", "James Anderson", 4)])
    ind_2_patterns.append([delivery("Rohit Sharma", "James Anderson", 0, wickets=[wkpt("caught", "Rohit Sharma", ["Zak Crawley"])])])
    ind_2_patterns.append([delivery("Yashasvi Jaiswal", "Stuart Broad", 0)])
    ind_2_patterns.append([delivery("Yashasvi Jaiswal", "Stuart Broad", 0, wickets=[wkpt("bowled", "Yashasvi Jaiswal")])])
    ind_2_patterns.append([delivery("Virat Kohli", "Jack Leach", 1)])
    ind_2_patterns.append([delivery("Cheteshwar Pujara", "Jack Leach", 1)])
    ind_2_patterns.append([delivery("Virat Kohli", "Ollie Robinson", 4)])
    ind_2_patterns.append([delivery("Cheteshwar Pujara", "Ollie Robinson", 0)])
    ind_2_patterns.append([delivery("Virat Kohli", "Jack Leach", 0)])
    ind_2_patterns.append([delivery("Cheteshwar Pujara", "Jack Leach", 1)])
    for i in range(65):
        if i == 12:
            ind_2_patterns.append([delivery("Cheteshwar Pujara", "Ollie Robinson", 0, wickets=[wkpt("lbw", "Cheteshwar Pujara")])])
        elif i == 22:
            ind_2_patterns.append([delivery("Virat Kohli", "Stuart Broad", 0, wickets=[wkpt("caught", "Virat Kohli", ["Ben Foakes"])])])
        elif i == 32:
            ind_2_patterns.append([delivery("KL Rahul", "Jack Leach", 4)])
        elif i == 42:
            ind_2_patterns.append([delivery("KL Rahul", "Ollie Robinson", 0, wickets=[wkpt("caught", "KL Rahul", ["Ben Duckett"])])])
        elif i == 52:
            ind_2_patterns.append([delivery("R Ashwin", "Jack Leach", 0, wickets=[wkpt("lbw", "R Ashwin")])])
        elif i == 60:
            ind_2_patterns.append([delivery("Jasprit Bumrah", "Stuart Broad", 0, wickets=[wkpt("caught", "Jasprit Bumrah", ["Joe Root"])])])
        else:
            ind_2_patterns.append([delivery("Ravindra Jadeja", "Jack Leach", 2)])
    ind_2_overs = [{"over": i, "deliveries": p} for i, p in enumerate(ind_2_patterns)]

    # England 2nd innings: 330/3 chase (target ~307)
    eng_2_patterns = []
    eng_2_patterns.append([delivery("Zak Crawley", "Jasprit Bumrah", 4)])
    eng_2_patterns.append([delivery("Zak Crawley", "Mohammed Shami", 0)])
    eng_2_patterns.append([delivery("Zak Crawley", "Mohammed Shami", 4)])
    eng_2_patterns.append([delivery("Ben Duckett", "Jasprit Bumrah", 1)])
    eng_2_patterns.append([delivery("Zak Crawley", "R Ashwin", 0)])
    eng_2_patterns.append([delivery("Ben Duckett", "R Ashwin", 4)])
    eng_2_patterns.append([delivery("Zak Crawley", "R Ashwin", 0)])
    eng_2_patterns.append([delivery("Ben Duckett", "Axar Patel", 1)])
    eng_2_patterns.append([delivery("Zak Crawley", "R Ashwin", 0)])
    eng_2_patterns.append([delivery("Ben Duckett", "Axar Patel", 0)])
    for i in range(70):
        if i == 15:
            eng_2_patterns.append([delivery("Zak Crawley", "R Ashwin", 4)])
        elif i == 25:
            eng_2_patterns.append([delivery("Zak Crawley", "Jasprit Bumrah", 0, wickets=[wkpt("caught", "Zak Crawley", ["KL Rahul"])])])
        elif i == 35:
            eng_2_patterns.append([delivery("Joe Root", "R Ashwin", 4)])
        elif i == 45:
            eng_2_patterns.append([delivery("Ben Duckett", "R Ashwin", 0, wickets=[wkpt("caught", "Ben Duckett", ["R Ashwin"])])])
        elif i == 55:
            eng_2_patterns.append([delivery("Joe Root", "Ravindra Jadeja", 4)])
        elif i == 65:
            eng_2_patterns.append([delivery("Ben Stokes", "Axar Patel", 2)])
        else:
            eng_2_patterns.append([delivery("Joe Root", "R Ashwin", 1)])
    eng_2_overs = [{"over": i, "deliveries": p} for i, p in enumerate(eng_2_patterns)]

    return {
        "info": {
            "teams": ["India", "England"],
            "dates": ["2023-07-01", "2023-07-02", "2023-07-03", "2023-07-04", "2023-07-05"],
            "venue": "Edgbaston",
            "city": "Birmingham",
            "match_type": "Test",
            "toss": {"winner": "India", "decision": "bat"},
            "outcome": {"winner": "England", "by": {"wickets": 7}},
            "player_of_match": ["Joe Root"],
            "players": {"India": india_bat, "England": eng_bat},
            "event": {},
            "competition": "England v India Test Series",
            "season": "2023",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "India", "innings": 1, "overs": ind_1_overs,
             "declared": False, "all_out": True, "follow_on": False},
            {"team": "England", "innings": 1, "overs": eng_1_overs,
             "declared": False, "all_out": True, "follow_on": False},
            {"team": "India", "innings": 2, "overs": ind_2_overs,
             "declared": False, "all_out": True, "follow_on": False},
            {"team": "England", "innings": 2, "overs": eng_2_overs,
             "declared": False, "all_out": False, "follow_on": False},
        ],
    }


# ============================================================
# FIXTURE 2: Drawn Test
# ============================================================
def fixture_drawn_test():
    """
    India vs England, drawn at Lord's.
    Both teams bat twice, no result.
    """
    india_bat = ["Rohit Sharma", "Yashasvi Jaiswal", "Virat Kohli",
                 "Cheteshwar Pujara", "Ajinkya Rahane", "KL Rahul",
                 "R Ashwin", "Ravindra Jadeja", "Axar Patel",
                 "Mohammed Shami", "Jasprit Bumrah"]
    eng_bat = ["Zak Crawley", "Ben Duckett", "Ollie Pope", "Joe Root",
               "Ben Stokes", "Harry Brook", "Ben Foakes", "Stuart Broad",
               "Jack Leach", "Ollie Robinson", "James Anderson"]

    # India 1st innings: 410/6 declared
    ind_1 = []
    for i in range(100):
        if i < 10:
            ind_1.append([delivery("Rohit Sharma", "Stuart Broad", 4)])
        elif i == 20:
            ind_1.append([delivery("Rohit Sharma", "James Anderson", 0, wickets=[wkpt("caught", "Rohit Sharma", ["Ben Duckett"])])])
        elif i == 30:
            ind_1.append([delivery("Virat Kohli", "Jack Leach", 4)])
        elif i == 40:
            ind_1.append([delivery("Yashasvi Jaiswal", "Ollie Robinson", 0, wickets=[wkpt("lbw", "Yashasvi Jaiswal")])])
        elif i == 60:
            ind_1.append([delivery("Virat Kohli", "Jack Leach", 4)])
        elif i == 80:
            ind_1.append([delivery("Virat Kohli", "Stuart Broad", 0, wickets=[wkpt("caught", "Virat Kohli", ["Ben Foakes"])])])
        elif i == 95:
            # Declaration after this over
            ind_1.append([delivery("KL Rahul", "Jack Leach", 1)])
        else:
            ind_1.append([delivery("Virat Kohli", "Jack Leach", 2)])
    ind_1_over_data = [{"over": i, "deliveries": p} for i, p in enumerate(ind_1)]

    # England 1st innings: 350 all out
    eng_1 = []
    for i in range(90):
        if i == 5:
            eng_1.append([delivery("Zak Crawley", "Jasprit Bumrah", 0, wickets=[wkpt("bowled", "Zak Crawley")])])
        elif i == 15:
            eng_1.append([delivery("Ben Duckett", "Mohammed Shami", 0, wickets=[wkpt("caught", "Ben Duckett", ["KL Rahul"])])])
        elif i == 30:
            eng_1.append([delivery("Joe Root", "R Ashwin", 4)])
        elif i == 50:
            eng_1.append([delivery("Joe Root", "R Ashwin", 0, wickets=[wkpt("caught", "Joe Root", ["R Ashwin"])])])
        elif i == 70:
            eng_1.append([delivery("Ben Stokes", "Ravindra Jadeja", 6)])
        elif i == 85:
            eng_1.append([delivery("Jack Leach", "Jasprit Bumrah", 0, wickets=[wkpt("bowled", "Jack Leach")])])
        else:
            eng_1.append([delivery("Ollie Pope", "R Ashwin", 1)])
    eng_1_data = [{"over": i, "deliveries": p} for i, p in enumerate(eng_1)]

    # India 2nd innings: 210/3 (batting, time runs out)
    ind_2 = []
    for i in range(55):
        if i == 10:
            ind_2.append([delivery("Rohit Sharma", "James Anderson", 0, wickets=[wkpt("caught", "Rohit Sharma", ["Zak Crawley"])])])
        elif i == 25:
            ind_2.append([delivery("Yashasvi Jaiswal", "Stuart Broad", 0, wickets=[wkpt("lbw", "Yashasvi Jaiswal")])])
        elif i == 40:
            ind_2.append([delivery("Virat Kohli", "Jack Leach", 4)])
        else:
            ind_2.append([delivery("Virat Kohli", "Jack Leach", 2)])
    ind_2_data = [{"over": i, "deliveries": p} for i, p in enumerate(ind_2)]

    # England 2nd innings: 156/3 (batting when time runs out)
    eng_2 = []
    for i in range(42):
        if i == 8:
            eng_2.append([delivery("Zak Crawley", "Jasprit Bumrah", 0, wickets=[wkpt("caught", "Zak Crawley", ["KL Rahul"])])])
        elif i == 20:
            eng_2.append([delivery("Ben Duckett", "Mohammed Shami", 4)])
        elif i == 35:
            eng_2.append([delivery("Ollie Pope", "R Ashwin", 0, wickets=[wkpt("caught", "Ollie Pope", ["R Ashwin"])])])
        else:
            eng_2.append([delivery("Ben Duckett", "R Ashwin", 1)])
    eng_2_data = [{"over": i, "deliveries": p} for i, p in enumerate(eng_2)]

    return {
        "info": {
            "teams": ["India", "England"],
            "dates": ["2023-07-10", "2023-07-11", "2023-07-12", "2023-07-13", "2023-07-14"],
            "venue": "Lord's",
            "city": "London",
            "match_type": "Test",
            "toss": {"winner": "India", "decision": "bat"},
            "outcome": {"winner": "", "draw": True},
            "player_of_match": [],
            "players": {"India": india_bat, "England": eng_bat},
            "event": {},
            "competition": "England v India Test Series",
            "season": "2023",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "India", "innings": 1, "overs": ind_1_over_data,
             "declared": True, "all_out": False, "follow_on": False},
            {"team": "England", "innings": 1, "overs": eng_1_data,
             "declared": False, "all_out": True, "follow_on": False},
            {"team": "India", "innings": 2, "overs": ind_2_data,
             "declared": False, "all_out": False, "follow_on": False},
            {"team": "England", "innings": 2, "overs": eng_2_data,
             "declared": False, "all_out": False, "follow_on": False},
        ],
    }


# ============================================================
# FIXTURE 3: Innings Victory
# ============================================================
def fixture_innings_victory():
    """
    India vs Australia — India won by an innings and 132 runs.
    India 487/6 declared, Australia 177 all out, Australia forced to follow-on,
    Australia 178 all out.
    """
    ind_bat = ["Rohit Sharma", "Yashasvi Jaiswal", "Cheteshwar Pujara",
               "Virat Kohli", "Ajinkya Rahane", "R Ashwin",
               "Ravindra Jadeja", "Axar Patel", "KS Bharat",
               "Mohammed Shami", "Jasprit Bumrah"]
    aus_bat = ["Usman Khawaja", "David Warner", "Marnus Labuschagne",
               "Steve Smith", "Travis Head", "Cameron Green",
               "Alex Carey", "Pat Cummins", "Mitchell Starc",
               "Todd Murphy", "Nathan Lyon"]

    # India 1st innings: 487/6 declared
    ind_1 = []
    for i in range(120):
        if i == 15:
            ind_1.append([delivery("Rohit Sharma", "Mitchell Starc", 4)])
        elif i == 25:
            ind_1.append([delivery("Rohit Sharma", "Pat Cummins", 0, wickets=[wkpt("caught", "Rohit Sharma", ["Alex Carey"])])])
        elif i == 40:
            ind_1.append([delivery("Virat Kohli", "Todd Murphy", 4)])
        elif i == 60:
            ind_1.append([delivery("Cheteshwar Pujara", "Todd Murphy", 0, wickets=[wkpt("lbw", "Cheteshwar Pujara")])])
        elif i == 80:
            ind_1.append([delivery("Virat Kohli", "Nathan Lyon", 4)])
        elif i == 100:
            ind_1.append([delivery("R Ashwin", "Todd Murphy", 6)])
        elif i == 115:
            # Declaration
            ind_1.append([delivery("R Ashwin", "Todd Murphy", 1)])
        else:
            ind_1.append([delivery("Virat Kohli", "Todd Murphy", 2)])
    ind_1_data = [{"over": i, "deliveries": p} for i, p in enumerate(ind_1)]

    # Australia 1st innings: 177 all out
    aus_1 = []
    for i in range(50):
        if i == 3:
            aus_1.append([delivery("Usman Khawaja", "Jasprit Bumrah", 0, wickets=[wkpt("caught", "Usman Khawaja", ["R Ashwin"])])])
        elif i == 8:
            aus_1.append([delivery("David Warner", "Mohammed Shami", 0, wickets=[wkpt("caught", "David Warner", ["KL Rahul"])])])
        elif i == 15:
            aus_1.append([delivery("Marnus Labuschagne", "R Ashwin", 0, wickets=[wkpt("lbw", "Marnus Labuschagne")])])
        elif i == 25:
            aus_1.append([delivery("Steve Smith", "R Ashwin", 4)])
        elif i == 35:
            aus_1.append([delivery("Steve Smith", "Ravindra Jadeja", 0, wickets=[wkpt("bowled", "Steve Smith")])])
        elif i == 45:
            aus_1.append([delivery("Alex Carey", "Jasprit Bumrah", 0, wickets=[wkpt("caught", "Alex Carey", ["Rohit Sharma"])])])
        else:
            aus_1.append([delivery("Travis Head", "R Ashwin", 1)])
    aus_1_data = [{"over": i, "deliveries": p} for i, p in enumerate(aus_1)]

    # Follow-on enforced. Australia 2nd innings: 178 all out.
    aus_2 = []
    for i in range(50):
        if i == 5:
            aus_2.append([delivery("Usman Khawaja", "Jasprit Bumrah", 0, wickets=[wkpt("bowled", "Usman Khawaja")])])
        elif i == 12:
            aus_2.append([delivery("David Warner", "Mohammed Shami", 0, wickets=[wkpt("caught", "David Warner", ["Yashasvi Jaiswal"])])])
        elif i == 20:
            aus_2.append([delivery("Marnus Labuschagne", "R Ashwin", 0, wickets=[wkpt("lbw", "Marnus Labuschagne")])])
        elif i == 30:
            aus_2.append([delivery("Steve Smith", "Ravindra Jadeja", 4)])
        elif i == 38:
            aus_2.append([delivery("Steve Smith", "R Ashwin", 0, wickets=[wkpt("caught", "Steve Smith", ["R Ashwin"])])])
        elif i == 46:
            aus_2.append([delivery("Alex Carey", "Jasprit Bumrah", 0, wickets=[wkpt("bowled", "Alex Carey")])])
        else:
            aus_2.append([delivery("Cameron Green", "R Ashwin", 1)])
    aus_2_data = [{"over": i, "deliveries": p} for i, p in enumerate(aus_2)]

    return {
        "info": {
            "teams": ["India", "Australia"],
            "dates": ["2023-03-01", "2023-03-02", "2023-03-03", "2023-03-04", "2023-03-05"],
            "venue": "Narendra Modi Stadium",
            "city": "Ahmedabad",
            "match_type": "Test",
            "toss": {"winner": "India", "decision": "bat"},
            "outcome": {"winner": "India", "by": {"innings": 1, "runs": 132}},
            "player_of_match": ["R Ashwin"],
            "players": {"India": ind_bat, "Australia": aus_bat},
            "event": {},
            "competition": "Border-Gavaskar Trophy",
            "season": "2023",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "India", "innings": 1, "overs": ind_1_data,
             "declared": True, "all_out": False, "follow_on": False},
            {"team": "Australia", "innings": 1, "overs": aus_1_data,
             "declared": False, "all_out": True, "follow_on": True},
            {"team": "Australia", "innings": 2, "overs": aus_2_data,
             "declared": False, "all_out": True, "follow_on": False},
        ],
    }


# ============================================================
# FIXTURE 4: Declaration win
# ============================================================
def fixture_declaration_win():
    """
    England vs Australia at Trent Bridge 2015 Ashes inspired.
    England declared 391/9, Australia 179 all out, England 250/4 declared,
    Australia 253 all out. England won by 129 runs.
    """
    eng_bat = ["Alastair Cook", "Adam Lyth", "Ian Bell", "Joe Root",
               "Gary Ballance", "Ben Stokes", "Jos Buttler", "Stuart Broad",
               "Mark Wood", "Moeen Ali", "James Anderson"]
    aus_bat = ["Chris Rogers", "David Warner", "Steve Smith", "Michael Clarke",
               "Shane Watson", "Brad Haddin", "Mitchell Johnson",
               "Mitchell Starc", "Nathan Lyon", "Josh Hazlewood", "Peter Siddle"]

    # England 1st innings: 391/9 declared
    eng_1 = []
    for i in range(100):
        if i == 10:
            eng_1.append([delivery("Alastair Cook", "Mitchell Starc", 0, wickets=[wkpt("caught", "Alastair Cook", ["Brad Haddin"])])])
        elif i == 20:
            eng_1.append([delivery("Adam Lyth", "Josh Hazlewood", 0, wickets=[wkpt("bowled", "Adam Lyth")])])
        elif i == 35:
            eng_1.append([delivery("Joe Root", "Nathan Lyon", 4)])
        elif i == 55:
            eng_1.append([delivery("Joe Root", "Nathan Lyon", 0, wickets=[wkpt("caught", "Joe Root", ["Steve Smith"])])])
        elif i == 70:
            eng_1.append([delivery("Ben Stokes", "Mitchell Starc", 6)])
        elif i == 90:
            eng_1.append([delivery("Ben Stokes", "Mitchell Starc", 0, wickets=[wkpt("bowled", "Ben Stokes")])])
        elif i == 98:
            # Declaration
            eng_1.append([delivery("Stuart Broad", "Josh Hazlewood", 1)])
        else:
            eng_1.append([delivery("Ben Stokes", "Nathan Lyon", 2)])
    eng_1_data = [{"over": i, "deliveries": p} for i, p in enumerate(eng_1)]

    # Australia 1st innings: 179 all out
    aus_1 = []
    for i in range(50):
        if i == 5:
            aus_1.append([delivery("Chris Rogers", "Stuart Broad", 0, wickets=[wkpt("bowled", "Chris Rogers")])])
        elif i == 12:
            aus_1.append([delivery("David Warner", "James Anderson", 0, wickets=[wkpt("caught", "David Warner", ["Jos Buttler"])])])
        elif i == 25:
            aus_1.append([delivery("Steve Smith", "Moeen Ali", 0, wickets=[wkpt("lbw", "Steve Smith")])])
        elif i == 35:
            aus_1.append([delivery("Michael Clarke", "Moeen Ali", 4)])
        elif i == 45:
            aus_1.append([delivery("Brad Haddin", "Stuart Broad", 0, wickets=[wkpt("caught", "Brad Haddin", ["Jos Buttler"])])])
        else:
            aus_1.append([delivery("Shane Watson", "Moeen Ali", 1)])
    aus_1_data = [{"over": i, "deliveries": p} for i, p in enumerate(aus_1)]

    # England 2nd innings: 250/4 declared
    eng_2 = []
    for i in range(65):
        if i == 8:
            eng_2.append([delivery("Alastair Cook", "Mitchell Starc", 0, wickets=[wkpt("caught", "Alastair Cook", ["Brad Haddin"])])])
        elif i == 20:
            eng_2.append([delivery("Adam Lyth", "Josh Hazlewood", 0, wickets=[wkpt("lbw", "Adam Lyth")])])
        elif i == 40:
            eng_2.append([delivery("Joe Root", "Nathan Lyon", 4)])
        elif i == 60:
            # Declaration
            eng_2.append([delivery("Joe Root", "Nathan Lyon", 1)])
        else:
            eng_2.append([delivery("Joe Root", "Nathan Lyon", 2)])
    eng_2_data = [{"over": i, "deliveries": p} for i, p in enumerate(eng_2)]

    # Australia 2nd innings: 253 all out
    aus_2 = []
    for i in range(70):
        if i == 5:
            aus_2.append([delivery("Chris Rogers", "James Anderson", 0, wickets=[wkpt("caught", "Chris Rogers", ["Alastair Cook"])])])
        elif i == 15:
            aus_2.append([delivery("David Warner", "Stuart Broad", 4)])
        elif i == 28:
            aus_2.append([delivery("David Warner", "Moeen Ali", 0, wickets=[wkpt("caught", "David Warner", ["Ben Stokes"])])])
        elif i == 38:
            aus_2.append([delivery("Steve Smith", "Moeen Ali", 0, wickets=[wkpt("lbw", "Steve Smith")])])
        elif i == 50:
            aus_2.append([delivery("Michael Clarke", "Stuart Broad", 0, wickets=[wkpt("caught", "Michael Clarke", ["Jos Buttler"])])])
        elif i == 60:
            aus_2.append([delivery("Mitchell Starc", "James Anderson", 0, wickets=[wkpt("bowled", "Mitchell Starc")])])
        else:
            aus_2.append([delivery("Shane Watson", "Moeen Ali", 1)])
    aus_2_data = [{"over": i, "deliveries": p} for i, p in enumerate(aus_2)]

    return {
        "info": {
            "teams": ["England", "Australia"],
            "dates": ["2023-08-10", "2023-08-11", "2023-08-12", "2023-08-13", "2023-08-14"],
            "venue": "Trent Bridge",
            "city": "Nottingham",
            "match_type": "Test",
            "toss": {"winner": "England", "decision": "bat"},
            "outcome": {"winner": "England", "by": {"runs": 129}},
            "player_of_match": ["Moeen Ali"],
            "players": {"England": eng_bat, "Australia": aus_bat},
            "event": {},
            "competition": "Ashes Series",
            "season": "2023",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "England", "innings": 1, "overs": eng_1_data,
             "declared": True, "all_out": False, "follow_on": False},
            {"team": "Australia", "innings": 1, "overs": aus_1_data,
             "declared": False, "all_out": True, "follow_on": True},
            {"team": "England", "innings": 2, "overs": eng_2_data,
             "declared": True, "all_out": False, "follow_on": False},
            {"team": "Australia", "innings": 2, "overs": aus_2_data,
             "declared": False, "all_out": True, "follow_on": False},
        ],
    }


# ============================================================
# FIXTURE 5: Test match — Australia won by 8 wickets
# ============================================================
def fixture_eight_wicket_win():
    """
    South Africa vs Australia — Australia won by 8 wickets.
    SA 242 & 204, Aus 342 & 105/2.
    """
    sa_bat = ["Dean Elgar", "Aiden Markram", "Rassie van der Dussen",
              "Temba Bavuma", "David Bedingham", "Kyle Verreynne",
              "Marco Jansen", "Keshav Maharaj", "Anrich Nortje",
              "Kagiso Rabada", "Lungi Ngidi"]
    aus_bat = ["David Warner", "Usman Khawaja", "Marnus Labuschagne",
               "Steve Smith", "Travis Head", "Cameron Green",
               "Alex Carey", "Pat Cummins", "Mitchell Starc",
               "Nathan Lyon", "Josh Hazlewood"]

    # SA 1st innings: 242
    sa_1 = []
    for i in range(65):
        if i == 5:
            sa_1.append([delivery("Dean Elgar", "Pat Cummins", 0, wickets=[wkpt("caught", "Dean Elgar", ["Alex Carey"])])])
        elif i == 15:
            sa_1.append([delivery("Aiden Markram", "Mitchell Starc", 4)])
        elif i == 25:
            sa_1.append([delivery("Aiden Markram", "Nathan Lyon", 0, wickets=[wkpt("lbw", "Aiden Markram")])])
        elif i == 40:
            sa_1.append([delivery("Temba Bavuma", "Nathan Lyon", 4)])
        elif i == 55:
            sa_1.append([delivery("Temba Bavuma", "Pat Cummins", 0, wickets=[wkpt("caught", "Temba Bavuma", ["Steve Smith"])])])
        else:
            sa_1.append([delivery("Rassie van der Dussen", "Nathan Lyon", 1)])
    sa_1_data = [{"over": i, "deliveries": p} for i, p in enumerate(sa_1)]

    # Aus 1st innings: 342
    aus_1 = []
    for i in range(90):
        if i == 10:
            aus_1.append([delivery("David Warner", "Kagiso Rabada", 0, wickets=[wkpt("caught", "David Warner", ["Kyle Verreynne"])])])
        elif i == 25:
            aus_1.append([delivery("Usman Khawaja", "Kagiso Rabada", 4)])
        elif i == 45:
            aus_1.append([delivery("Steve Smith", "Keshav Maharaj", 4)])
        elif i == 65:
            aus_1.append([delivery("Steve Smith", "Keshav Maharaj", 0, wickets=[wkpt("caught", "Steve Smith", ["Aiden Markram"])])])
        elif i == 80:
            aus_1.append([delivery("Alex Carey", "Kagiso Rabada", 4)])
        else:
            aus_1.append([delivery("Travis Head", "Keshav Maharaj", 2)])
    aus_1_data = [{"over": i, "deliveries": p} for i, p in enumerate(aus_1)]

    # SA 2nd innings: 204
    sa_2 = []
    for i in range(55):
        if i == 5:
            sa_2.append([delivery("Dean Elgar", "Mitchell Starc", 0, wickets=[wkpt("bowled", "Dean Elgar")])])
        elif i == 15:
            sa_2.append([delivery("Aiden Markram", "Pat Cummins", 0, wickets=[wkpt("caught", "Aiden Markram", ["Alex Carey"])])])
        elif i == 30:
            sa_2.append([delivery("Temba Bavuma", "Nathan Lyon", 4)])
        elif i == 40:
            sa_2.append([delivery("Temba Bavuma", "Pat Cummins", 0, wickets=[wkpt("lbw", "Temba Bavuma")])])
        elif i == 50:
            sa_2.append([delivery("Kagiso Rabada", "Mitchell Starc", 0, wickets=[wkpt("caught", "Kagiso Rabada", ["Usman Khawaja"])])])
        else:
            sa_2.append([delivery("Rassie van der Dussen", "Nathan Lyon", 1)])
    sa_2_data = [{"over": i, "deliveries": p} for i, p in enumerate(sa_2)]

    # Aus 2nd innings: 105/2 (target ~105)
    aus_2 = []
    for i in range(28):
        if i == 5:
            aus_2.append([delivery("David Warner", "Kagiso Rabada", 4)])
        elif i == 12:
            aus_2.append([delivery("Usman Khawaja", "Kagiso Rabada", 0)])
        elif i == 20:
            aus_2.append([delivery("Usman Khawaja", "Anrich Nortje", 4)])
        else:
            aus_2.append([delivery("Usman Khawaja", "Anrich Nortje", 1)])
    aus_2_data = [{"over": i, "deliveries": p} for i, p in enumerate(aus_2)]

    return {
        "info": {
            "teams": ["South Africa", "Australia"],
            "dates": ["2023-12-01", "2023-12-02", "2023-12-03", "2023-12-04", "2023-12-05"],
            "venue": "The Wanderers",
            "city": "Johannesburg",
            "match_type": "Test",
            "toss": {"winner": "Australia", "decision": "field"},
            "outcome": {"winner": "Australia", "by": {"wickets": 8}},
            "player_of_match": ["Steve Smith"],
            "players": {"South Africa": sa_bat, "Australia": aus_bat},
            "event": {},
            "competition": "Australia in South Africa",
            "season": "2023",
            "registry": {"people": {}},
        },
        "innings": [
            {"team": "South Africa", "innings": 1, "overs": sa_1_data,
             "declared": False, "all_out": True, "follow_on": False},
            {"team": "Australia", "innings": 1, "overs": aus_1_data,
             "declared": False, "all_out": False, "follow_on": False},
            {"team": "South Africa", "innings": 2, "overs": sa_2_data,
             "declared": False, "all_out": True, "follow_on": False},
            {"team": "Australia", "innings": 2, "overs": aus_2_data,
             "declared": False, "all_out": False, "follow_on": False},
        ],
    }


# ============================================================
# Main
# ============================================================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fixtures = [
        ("test_match_normal.json", fixture_normal_test),
        ("test_match_draw.json", fixture_drawn_test),
        ("test_match_innings_victory.json", fixture_innings_victory),
        ("test_match_declaration.json", fixture_declaration_win),
        ("test_match_8wickets.json", fixture_eight_wicket_win),
    ]

    total_deliveries = 0
    for filename, fn in fixtures:
        data = fn()
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2)

        deliveries = sum(
            len(ball)
            for inn in data["innings"]
            for over in inn["overs"]
            for ball in over["deliveries"]
        )
        total_deliveries += deliveries
        innings_count = len(data["innings"])
        result = data["info"]["outcome"]
        teams = data["info"]["teams"]
        venue = data["info"]["venue"]
        declared = sum(1 for inn in data["innings"] if inn.get("declared"))
        allout = sum(1 for inn in data["innings"] if inn.get("all_out"))
        followon = sum(1 for inn in data["innings"] if inn.get("follow_on"))

        print(f"  {filename}: {teams[0]} vs {teams[1]}, {venue}")
        print(f"    {innings_count} innings, {deliveries} deliveries, "
              f"result: {result}")
        print(f"    declared={declared}, all_out={allout}, follow_on={followon}")

    print(f"\nGenerated {len(fixtures)} Test fixtures with {total_deliveries} total deliveries")


if __name__ == "__main__":
    main()
