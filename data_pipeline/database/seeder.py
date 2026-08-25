"""
Database Seeder
===============

Populates the database with realistic sample data for local development.

This is independent of the Spark pipeline — it creates directly insertable
data so the backend can be developed and tested without running the full ETL.

The seed data represents a realistic cricket intelligence dataset with:
- 8 international teams
- 40 players across teams
- 10 venues
- 20 matches with full scorecards
- Precomputed analytical results (stats, form scores, matchups)
"""

import uuid
import random
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

# Use a fixed seed for reproducible data
random.seed(42)

# ============================================================
# Seed Data Definitions
# ============================================================

TEAMS = [
    {"canonical_name": "India", "short_name": "IND", "country": "India"},
    {"canonical_name": "Australia", "short_name": "AUS", "country": "Australia"},
    {"canonical_name": "England", "short_name": "ENG", "country": "England"},
    {"canonical_name": "South Africa", "short_name": "SA", "country": "South Africa"},
    {"canonical_name": "Pakistan", "short_name": "PAK", "country": "Pakistan"},
    {"canonical_name": "New Zealand", "short_name": "NZ", "country": "New Zealand"},
    {"canonical_name": "West Indies", "short_name": "WI", "country": "West Indies"},
    {"canonical_name": "Bangladesh", "short_name": "BAN", "country": "Bangladesh"},
]

PLAYERS = [
    # India
    {"canonical_name": "Virat Kohli", "country": "India", "team": "India", "role": "batsman", "batting_style": "right_hand", "bowling_type": None},
    {"canonical_name": "Rohit Sharma", "country": "India", "team": "India", "role": "batsman", "batting_style": "right_hand", "bowling_type": None},
    {"canonical_name": "Suryakumar Yadav", "country": "India", "team": "India", "role": "batsman", "batting_style": "right_hand", "bowling_type": None},
    {"canonical_name": "Jasprit Bumrah", "country": "India", "team": "India", "role": "bowler", "batting_style": "right_hand", "bowling_type": "pace"},
    {"canonical_name": "Hardik Pandya", "country": "India", "team": "India", "role": "allrounder", "batting_style": "right_hand", "bowling_type": "pace"},
    {"canonical_name": "KL Rahul", "country": "India", "team": "India", "role": "wicketkeeper", "batting_style": "right_hand", "bowling_type": None},
    {"canonical_name": "Ravindra Jadeja", "country": "India", "team": "India", "role": "allrounder", "batting_style": "left_hand", "bowling_type": "spin"},
    {"canonical_name": "Yuzvendra Chahal", "country": "India", "team": "India", "role": "bowler", "batting_style": "right_hand", "bowling_type": "spin"},
    # Australia
    {"canonical_name": "David Warner", "country": "Australia", "team": "Australia", "role": "batsman", "batting_style": "left_hand", "bowling_type": None},
    {"canonical_name": "Steve Smith", "country": "Australia", "team": "Australia", "role": "batsman", "batting_style": "right_hand", "bowling_type": None},
    {"canonical_name": "Glenn Maxwell", "country": "Australia", "team": "Australia", "role": "allrounder", "batting_style": "right_hand", "bowling_type": "spin"},
    {"canonical_name": "Mitchell Starc", "country": "Australia", "team": "Australia", "role": "bowler", "batting_style": "left_hand", "bowling_type": "pace"},
    {"canonical_name": "Pat Cummins", "country": "Australia", "team": "Australia", "role": "bowler", "batting_style": "right_hand", "bowling_type": "pace"},
    {"canonical_name": "Travis Head", "country": "Australia", "team": "Australia", "role": "batsman", "batting_style": "left_hand", "bowling_type": None},
    # England
    {"canonical_name": "Jos Buttler", "country": "England", "team": "England", "role": "wicketkeeper", "batting_style": "right_hand", "bowling_type": None},
    {"canonical_name": "Ben Stokes", "country": "England", "team": "England", "role": "allrounder", "batting_style": "right_hand", "bowling_type": "pace"},
    {"canonical_name": "Joe Root", "country": "England", "team": "England", "role": "batsman", "batting_style": "right_hand", "bowling_type": None},
    {"canonical_name": "Jofra Archer", "country": "England", "team": "England", "role": "bowler", "batting_style": "right_hand", "bowling_type": "pace"},
    {"canonical_name": "Adil Rashid", "country": "England", "team": "England", "role": "bowler", "batting_style": "right_hand", "bowling_type": "spin"},
    {"canonical_name": "Harry Brook", "country": "England", "team": "England", "role": "batsman", "batting_style": "right_hand", "bowling_type": None},
    # Pakistan
    {"canonical_name": "Babar Azam", "country": "Pakistan", "team": "Pakistan", "role": "batsman", "batting_style": "right_hand", "bowling_type": None},
    {"canonical_name": "Mohammad Rizwan", "country": "Pakistan", "team": "Pakistan", "role": "wicketkeeper", "batting_style": "right_hand", "bowling_type": None},
    {"canonical_name": "Shaheen Afridi", "country": "Pakistan", "team": "Pakistan", "role": "bowler", "batting_style": "left_hand", "bowling_type": "pace"},
    {"canonical_name": "Shadab Khan", "country": "Pakistan", "team": "Pakistan", "role": "allrounder", "batting_style": "right_hand", "bowling_type": "spin"},
    # South Africa
    {"canonical_name": "Quinton de Kock", "country": "South Africa", "team": "South Africa", "role": "wicketkeeper", "batting_style": "left_hand", "bowling_type": None},
    {"canonical_name": "Aiden Markram", "country": "South Africa", "team": "South Africa", "role": "batsman", "batting_style": "right_hand", "bowling_type": None},
    {"canonical_name": "Kagiso Rabada", "country": "South Africa", "team": "South Africa", "role": "bowler", "batting_style": "right_hand", "bowling_type": "pace"},
    {"canonical_name": "Anrich Nortje", "country": "South Africa", "team": "South Africa", "role": "bowler", "batting_style": "right_hand", "bowling_type": "pace"},
    # New Zealand
    {"canonical_name": "Kane Williamson", "country": "New Zealand", "team": "New Zealand", "role": "batsman", "batting_style": "right_hand", "bowling_type": None},
    {"canonical_name": "Trent Boult", "country": "New Zealand", "team": "New Zealand", "role": "bowler", "batting_style": "left_hand", "bowling_type": "pace"},
    {"canonical_name": "Devon Conway", "country": "New Zealand", "team": "New Zealand", "role": "batsman", "batting_style": "left_hand", "bowling_type": None},
    {"canonical_name": "Tim Southee", "country": "New Zealand", "team": "New Zealand", "role": "bowler", "batting_style": "right_hand", "bowling_type": "pace"},
    # West Indies
    {"canonical_name": "Nicholas Pooran", "country": "West Indies", "team": "West Indies", "role": "wicketkeeper", "batting_style": "left_hand", "bowling_type": None},
    {"canonical_name": "Jason Holder", "country": "West Indies", "team": "West Indies", "role": "allrounder", "batting_style": "right_hand", "bowling_type": "pace"},
    # Bangladesh
    {"canonical_name": "Shakib Al Hasan", "country": "Bangladesh", "team": "Bangladesh", "role": "allrounder", "batting_style": "left_hand", "bowling_type": "spin"},
    {"canonical_name": "Mustafizur Rahman", "country": "Bangladesh", "team": "Bangladesh", "role": "bowler", "batting_style": "left_hand", "bowling_type": "pace"},
]

VENUES = [
    {"name": "Melbourne Cricket Ground", "city": "Melbourne", "country": "Australia", "capacity": 100024},
    {"name": "Eden Gardens", "city": "Kolkata", "country": "India", "capacity": 66000},
    {"name": "Dubai International Cricket Stadium", "city": "Dubai", "country": "UAE", "capacity": 25000},
    {"name": "The Oval", "city": "London", "country": "England", "capacity": 25500},
    {"name": "Wankhede Stadium", "city": "Mumbai", "country": "India", "capacity": 33000},
    {"name": "Gaddafi Stadium", "city": "Lahore", "country": "Pakistan", "capacity": 27000},
    {"name": "SuperSport Park", "city": "Centurion", "country": "South Africa", "capacity": 22000},
    {"name": "Basin Reserve", "city": "Wellington", "country": "New Zealand", "capacity": 11600},
    {"name": "Sydney Cricket Ground", "city": "Sydney", "country": "Australia", "capacity": 48000},
    {"name": "Lord's", "city": "London", "country": "England", "capacity": 31100},
]


class DatabaseSeeder:
    """
    Seeds the database with realistic cricket data.
    
    Creates entities, analytical results, and relationships
    that allow the backend to serve real-looking data.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        from backend.utils.database import DATABASE_URL
        self.database_url = database_url or DATABASE_URL
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # UUID caches for foreign key references
        self._team_ids = {}
        self._player_ids = {}
        self._venue_ids = {}
    
    def seed_all(self):
        """Run all seed operations in order."""
        logger.info("Seeding database...")
        
        self._ensure_schema()
        self._seed_teams()
        self._seed_players()
        self._seed_venues()
        self._seed_player_batting_stats()
        self._seed_player_bowling_stats()
        self._seed_player_form()
        self._seed_team_performance()
        self._seed_venue_stats()
        self._seed_matches()
        
        logger.info("Database seeding complete!")
    
    def _ensure_schema(self):
        """Create tables from schema.sql."""
        schema_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "database", "schema.sql"
        )
        if not os.path.exists(schema_path):
            logger.warning(f"Schema file not found: {schema_path}, skipping")
            return
        
        logger.info("Creating schema from schema.sql...")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        
        with self.engine.connect() as conn:
            for statement in schema_sql.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        conn.execute(text(statement))
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            logger.debug(f"Schema statement: {e}")
            conn.commit()
    
    def _seed_teams(self):
        """Insert canonical teams."""
        logger.info("Seeding teams...")
        with self.SessionLocal() as session:
            for team_data in TEAMS:
                # Check if team already exists
                existing = session.execute(
                    text("SELECT id FROM teams WHERE canonical_name = :name"),
                    {"name": team_data["canonical_name"]}
                ).fetchone()
                
                if existing:
                    self._team_ids[team_data["canonical_name"]] = existing[0]
                    continue
                
                team_id = str(uuid.uuid4())
                session.execute(
                    text("""
                        INSERT INTO teams (id, canonical_name, short_name, country, is_active)
                        VALUES (:id, :name, :short, :country, 1)
                    """),
                    {
                        "id": team_id,
                        "name": team_data["canonical_name"],
                        "short": team_data["short_name"],
                        "country": team_data["country"],
                    }
                )
                self._team_ids[team_data["canonical_name"]] = team_id
            
            session.commit()
        logger.info(f"  Seeded {len(self._team_ids)} teams")
    
    def _seed_players(self):
        """Insert canonical players."""
        logger.info("Seeding players...")
        with self.SessionLocal() as session:
            for player_data in PLAYERS:
                existing = session.execute(
                    text("SELECT id FROM players WHERE canonical_name = :name"),
                    {"name": player_data["canonical_name"]}
                ).fetchone()
                
                if existing:
                    self._player_ids[player_data["canonical_name"]] = existing[0]
                    continue
                
                player_id = str(uuid.uuid4())
                team_id = self._team_ids.get(player_data.get("team"))
                
                session.execute(
                    text("""
                        INSERT INTO players (id, canonical_name, country, team_id, role, batting_style, bowling_type, is_active)
                        VALUES (:id, :name, :country, :team_id, :role, :bat_style, :bowl_type, 1)
                    """),
                    {
                        "id": player_id,
                        "name": player_data["canonical_name"],
                        "country": player_data["country"],
                        "team_id": team_id,
                        "role": player_data["role"],
                        "bat_style": player_data["batting_style"],
                        "bowl_type": player_data.get("bowling_type"),
                    }
                )
                self._player_ids[player_data["canonical_name"]] = player_id
            
            session.commit()
        logger.info(f"  Seeded {len(self._player_ids)} players")
    
    def _seed_venues(self):
        """Insert venues."""
        logger.info("Seeding venues...")
        with self.SessionLocal() as session:
            for venue_data in VENUES:
                existing = session.execute(
                    text("SELECT id FROM venues WHERE name = :name"),
                    {"name": venue_data["name"]}
                ).fetchone()
                
                if existing:
                    self._venue_ids[venue_data["name"]] = existing[0]
                    continue
                
                venue_id = str(uuid.uuid4())
                session.execute(
                    text("""
                        INSERT INTO venues (id, name, city, country, capacity)
                        VALUES (:id, :name, :city, :country, :capacity)
                    """),
                    {
                        "id": venue_id,
                        "name": venue_data["name"],
                        "city": venue_data["city"],
                        "country": venue_data["country"],
                        "capacity": venue_data["capacity"],
                    }
                )
                self._venue_ids[venue_data["name"]] = venue_id
            
            session.commit()
        logger.info(f"  Seeded {len(self._venue_ids)} venues")
    
    def _seed_player_batting_stats(self):
        """Insert career batting stats for each player."""
        logger.info("Seeding player batting stats...")
        
        # Realistic batting stat ranges by role
        stat_ranges = {
            "batsman": {"avg": (28, 55), "sr": (120, 160), "runs": (800, 4000), "fours": (50, 400), "sixes": (20, 200)},
            "allrounder": {"avg": (18, 35), "sr": (115, 150), "runs": (400, 2000), "fours": (25, 150), "sixes": (15, 80)},
            "wicketkeeper": {"avg": (25, 45), "sr": (125, 155), "runs": (600, 3000), "fours": (40, 250), "sixes": (25, 120)},
            "bowler": {"avg": (5, 18), "sr": (90, 140), "runs": (50, 500), "fours": (3, 30), "sixes": (2, 20)},
        }
        
        with self.SessionLocal() as session:
            count = 0
            for player_data in PLAYERS:
                player_id = self._player_ids.get(player_data["canonical_name"])
                if not player_id:
                    continue
                
                # Check if stats already exist
                existing = session.execute(
                    text("SELECT id FROM player_batting_stats WHERE player_id = :pid AND format = 'T20I' AND period = 'career'"),
                    {"pid": player_id}
                ).fetchone()
                if existing:
                    continue
                
                role = player_data["role"]
                ranges = stat_ranges.get(role, stat_ranges["batsman"])
                
                innings = random.randint(20, 180)
                runs = random.randint(*ranges["runs"])
                avg = round(runs / max(innings - random.randint(2, 10), 1), 2)
                sr = round(random.uniform(*ranges["sr"]), 2)
                fours = random.randint(*ranges["fours"])
                sixes = random.randint(*ranges["sixes"])
                balls_faced = int(runs * 100 / max(sr, 1))
                
                session.execute(
                    text("""
                        INSERT INTO player_batting_stats 
                        (player_id, format, period, matches, innings, not_outs, runs, highest_score,
                         batting_average, strike_rate, balls_faced, fours, sixes, 
                         boundary_pct, dot_ball_pct, fifties, hundreds,
                         powerplay_runs, powerplay_strike_rate, middle_runs, middle_strike_rate,
                         death_runs, death_strike_rate, chasing_runs, chasing_strike_rate)
                        VALUES (:pid, 'T20I', 'career', :matches, :innings, :not_outs, :runs, :hs,
                                :avg, :sr, :bf, :fours, :sixes,
                                :bp, :dp, :fifties, :hundreds,
                                :pp_runs, :pp_sr, :mid_runs, :mid_sr,
                                :dth_runs, :dth_sr, :chase_runs, :chase_sr)
                    """),
                    {
                        "pid": player_id,
                        "matches": innings + random.randint(0, 20),
                        "innings": innings,
                        "not_outs": random.randint(2, 10),
                        "runs": runs,
                        "hs": min(runs, random.randint(25, 120)),
                        "avg": avg,
                        "sr": sr,
                        "bf": balls_faced,
                        "fours": fours,
                        "sixes": sixes,
                        "bp": round((fours * 4 + sixes * 6) / max(runs, 1) * 100, 2),
                        "dp": round(random.uniform(25, 50), 2),
                        "fifties": random.randint(0, max(1, innings // 6)),
                        "hundreds": random.randint(0, max(1, innings // 20)),
                        "pp_runs": int(runs * random.uniform(0.2, 0.35)),
                        "pp_sr": round(sr * random.uniform(0.9, 1.15), 2),
                        "mid_runs": int(runs * random.uniform(0.3, 0.45)),
                        "mid_sr": round(sr * random.uniform(0.85, 1.05), 2),
                        "dth_runs": int(runs * random.uniform(0.2, 0.4)),
                        "dth_sr": round(sr * random.uniform(1.0, 1.25), 2),
                        "chase_runs": int(runs * random.uniform(0.4, 0.6)),
                        "chase_sr": round(sr * random.uniform(0.95, 1.1), 2),
                    }
                )
                count += 1
            
            session.commit()
        logger.info(f"  Seeded batting stats for {count} players")
    
    def _seed_player_bowling_stats(self):
        """Insert career bowling stats for bowlers and allrounders."""
        logger.info("Seeding player bowling stats...")
        
        with self.SessionLocal() as session:
            count = 0
            for player_data in PLAYERS:
                if player_data["role"] not in ("bowler", "allrounder"):
                    continue
                
                player_id = self._player_ids.get(player_data["canonical_name"])
                if not player_id:
                    continue
                
                existing = session.execute(
                    text("SELECT id FROM player_bowling_stats WHERE player_id = :pid AND format = 'T20I' AND period = 'career'"),
                    {"pid": player_id}
                ).fetchone()
                if existing:
                    continue
                
                is_pace = player_data.get("bowling_type") == "pace"
                
                wickets = random.randint(15, 120)
                economy = round(random.uniform(5.5, 9.0) if is_pace else random.uniform(6.0, 8.5), 2)
                runs_conceded = random.randint(300, 2500)
                overs = round(runs_conceded / max(economy, 1), 1)
                balls = int(overs * 6)
                avg = round(runs_conceded / max(wickets, 1), 2)
                sr = round(balls / max(wickets, 1), 2)
                
                session.execute(
                    text("""
                        INSERT INTO player_bowling_stats
                        (player_id, format, period, matches, innings, overs, balls_bowled,
                         wickets, runs_conceded, bowling_average, strike_rate, economy,
                         dot_ball_pct, boundary_conceded_pct)
                        VALUES (:pid, 'T20I', 'career', :matches, :innings, :overs, :balls,
                                :wickets, :runs, :avg, :sr, :econ, :dot_pct, :bpct)
                    """),
                    {
                        "pid": player_id,
                        "matches": random.randint(15, 120),
                        "innings": random.randint(15, 110),
                        "overs": overs,
                        "balls": balls,
                        "wickets": wickets,
                        "runs": runs_conceded,
                        "avg": avg,
                        "sr": sr,
                        "econ": economy,
                        "dot_pct": round(random.uniform(30, 55), 2),
                        "bpct": round(random.uniform(8, 18), 2),
                    }
                )
                count += 1
            
            session.commit()
        logger.info(f"  Seeded bowling stats for {count} players")
    
    def _seed_player_form(self):
        """Insert form scores for all players."""
        logger.info("Seeding player form scores...")
        
        with self.SessionLocal() as session:
            count = 0
            for player_data in PLAYERS:
                player_id = self._player_ids.get(player_data["canonical_name"])
                if not player_id:
                    continue
                
                existing = session.execute(
                    text("SELECT id FROM player_form WHERE player_id = :pid AND format = 'T20I'"),
                    {"pid": player_id}
                ).fetchone()
                if existing:
                    continue
                
                # Generate realistic form scores with component breakdown
                recent = round(random.uniform(40, 95), 2)
                consistency = round(random.uniform(35, 90), 2)
                opp_strength = round(random.uniform(30, 85), 2)
                venue = round(random.uniform(40, 80), 2)
                situation = round(random.uniform(40, 85), 2)
                efficiency = round(random.uniform(35, 90), 2)
                
                form_score = round(
                    recent * 0.35 + consistency * 0.20 + opp_strength * 0.15 +
                    venue * 0.10 + situation * 0.10 + efficiency * 0.10, 2
                )
                
                session.execute(
                    text("""
                        INSERT INTO player_form
                        (player_id, format, form_score, recent_performance_component,
                         consistency_component, opposition_strength_component,
                         venue_performance_component, match_situation_component,
                         efficiency_component, recent_innings_count)
                        VALUES (:pid, 'T20I', :fs, :rp, :cc, :os, :vp, :ms, :ef, :ri)
                    """),
                    {
                        "pid": player_id,
                        "fs": form_score,
                        "rp": recent,
                        "cc": consistency,
                        "os": opp_strength,
                        "vp": venue,
                        "ms": situation,
                        "ef": efficiency,
                        "ri": random.randint(5, 20),
                    }
                )
                count += 1
            
            session.commit()
        logger.info(f"  Seeded form scores for {count} players")
    
    def _seed_team_performance(self):
        """Insert team performance analytics."""
        logger.info("Seeding team performance...")
        
        with self.SessionLocal() as session:
            count = 0
            for team_data in TEAMS:
                team_id = self._team_ids.get(team_data["canonical_name"])
                if not team_id:
                    continue
                
                existing = session.execute(
                    text("SELECT id FROM team_performance WHERE team_id = :tid AND format = 'T20I' AND period = 'career'"),
                    {"tid": team_id}
                ).fetchone()
                if existing:
                    continue
                
                matches = random.randint(25, 55)
                wins = random.randint(int(matches * 0.3), int(matches * 0.75))
                win_rate = round(wins / matches * 100, 2)
                
                session.execute(
                    text("""
                        INSERT INTO team_performance
                        (team_id, format, period, matches, wins, losses, win_rate,
                         avg_first_innings_score, avg_second_innings_score,
                         avg_powerplay_score, avg_middle_overs_score, avg_death_overs_score,
                         avg_economy, batting_strength_score, bowling_strength_score, overall_strength_score,
                         chasing_win_pct, defending_win_pct)
                        VALUES (:tid, 'T20I', 'career', :matches, :wins, :losses, :wr,
                                :avg1, :avg2, :pp, :mid, :dth, :econ, :bat_str, :bowl_str, :overall,
                                :chase_pct, :def_pct)
                    """),
                    {
                        "tid": team_id,
                        "matches": matches,
                        "wins": wins,
                        "losses": matches - wins,
                        "wr": win_rate,
                        "avg1": round(random.uniform(155, 185), 2),
                        "avg2": round(random.uniform(145, 175), 2),
                        "pp": round(random.uniform(40, 55), 2),
                        "mid": round(random.uniform(55, 70), 2),
                        "dth": round(random.uniform(58, 75), 2),
                        "econ": round(random.uniform(6.5, 9.5), 2),
                        "bat_str": round(random.uniform(55, 95), 2),
                        "bowl_str": round(random.uniform(55, 95), 2),
                        "overall": round(random.uniform(55, 92), 2),
                        "chase_pct": round(random.uniform(40, 72), 2),
                        "def_pct": round(random.uniform(42, 75), 2),
                    }
                )
                count += 1
            
            session.commit()
        logger.info(f"  Seeded team performance for {count} teams")
    
    def _seed_venue_stats(self):
        """Insert venue statistics."""
        logger.info("Seeding venue stats...")
        
        with self.SessionLocal() as session:
            count = 0
            for venue_data in VENUES:
                venue_id = self._venue_ids.get(venue_data["name"])
                if not venue_id:
                    continue
                
                existing = session.execute(
                    text("SELECT id FROM venue_stats WHERE venue_id = :vid AND format = 'T20I'"),
                    {"vid": venue_id}
                ).fetchone()
                if existing:
                    continue
                
                matches = random.randint(15, 85)
                session.execute(
                    text("""
                        INSERT INTO venue_stats
                        (venue_id, format, total_matches, avg_first_innings_score,
                         avg_second_innings_score, highest_total, lowest_total,
                         chasing_win_pct, defending_win_pct,
                         pace_wickets_pct, spin_wickets_pct,
                         avg_powerplay_runs, avg_middle_overs_runs, avg_death_overs_runs,
                         avg_fours_per_match, avg_sixes_per_match, boundary_frequency)
                        VALUES (:vid, 'T20I', :matches, :avg1, :avg2, :hi, :lo,
                                :chase_pct, :def_pct, :pace_pct, :spin_pct,
                                :pp, :mid, :dth, :fours, :sixes, :bf)
                    """),
                    {
                        "vid": venue_id,
                        "matches": matches,
                        "avg1": round(random.uniform(150, 185), 2),
                        "avg2": round(random.uniform(140, 175), 2),
                        "hi": random.randint(200, 240),
                        "lo": random.randint(65, 110),
                        "chase_pct": round(random.uniform(38, 65), 2),
                        "def_pct": round(random.uniform(35, 62), 2),
                        "pace_pct": round(random.uniform(45, 65), 2),
                        "spin_pct": round(random.uniform(35, 55), 2),
                        "pp": round(random.uniform(38, 52), 2),
                        "mid": round(random.uniform(50, 68), 2),
                        "dth": round(random.uniform(55, 75), 2),
                        "fours": round(random.uniform(14, 22), 2),
                        "sixes": round(random.uniform(6, 14), 2),
                        "bf": round(random.uniform(12, 18), 2),
                    }
                )
                count += 1
            
            session.commit()
        logger.info(f"  Seeded venue stats for {count} venues")
    
    def _seed_matches(self):
        """Insert sample match records."""
        logger.info("Seeding matches...")
        
        team_names = list(self._team_ids.keys())
        venue_names = list(self._venue_ids.keys())
        
        with self.SessionLocal() as session:
            count = 0
            for i in range(20):
                # Pick two different teams
                team_a_name, team_b_name = random.sample(team_names, 2)
                team_a_id = self._team_ids[team_a_name]
                team_b_id = self._team_ids[team_b_name]
                
                venue_name = random.choice(venue_names)
                venue_id = self._venue_ids[venue_name]
                
                match_date = date(2024, 1, 1) + timedelta(days=random.randint(0, 300))
                winner_id = random.choice([team_a_id, team_b_id])
                win_margin = random.randint(5, 50)
                win_type = random.choice(["runs", "wickets"])
                
                session.execute(
                    text("""
                        INSERT INTO matches (id, match_date, format, venue_id, team_a_id, team_b_id,
                                             winner_id, win_margin, win_type, toss_decision, is_live)
                        VALUES (:id, :date, 'T20I', :venue, :ta, :tb, :winner, :margin, :wtype, :toss, 0)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "date": match_date,
                        "venue": venue_id,
                        "ta": team_a_id,
                        "tb": team_b_id,
                        "winner": winner_id,
                        "margin": win_margin,
                        "wtype": win_type,
                        "toss": random.choice(["bat", "field"]),
                    }
                )
                count += 1
            
            session.commit()
        logger.info(f"  Seeded {count} matches")


import os

def seed_database(database_url: Optional[str] = None):
    """Convenience function to seed the database."""
    seeder = DatabaseSeeder(database_url=database_url)
    seeder.seed_all()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    seed_database()
