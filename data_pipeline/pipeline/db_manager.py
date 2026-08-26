"""
Database Manager
================

Handles all database operations for the pipeline:
- Schema creation
- Entity resolution (names → UUIDs)
- Upsert operations for teams, players, venues, matches, innings, deliveries
- Analytics table writes

Uses SQLAlchemy for schema management and psycopg2 for bulk operations.
Falls back to SQLite for local development.
"""

import os
import uuid
import logging
from typing import Optional
from datetime import date

import pandas as pd
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database operations for the cricket pipeline.
    
    Provides:
    - Entity creation and ID resolution
    - Upsert operations for all core tables
    - Analytics table writes
    - Data validation queries
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "sqlite:///data/cricket_intelligence.db"
        )
        self.is_sqlite = self.database_url.startswith("sqlite")
        
        self.engine = create_engine(
            self.database_url,
            echo=False,
            **({} if self.is_sqlite else {
                "pool_pre_ping": True,
                "pool_size": 5,
            }),
        )
        
        # Enable WAL mode for SQLite
        if self.is_sqlite:
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # ID caches: name → UUID string
        self._team_ids = {}      # canonical_name → id
        self._player_ids = {}    # canonical_name → id
        self._venue_ids = {}     # name → id
        self._competition_ids = {} # name → id
        self._match_ids = {}     # external_id → id
        self._innings_ids = {}   # (match_id, innings_number) → id
        
        # Reverse caches for lookup
        self._team_names = {}    # id → canonical_name
        self._player_names = {}  # id → canonical_name
    
    def initialize(self):
        """Create all tables from schema."""
        logger.info("Initializing database schema...")
        self._create_schema()
        self._load_existing_ids()
    
    def _create_schema(self):
        """Create schema appropriate for the database dialect."""
        if self.is_sqlite:
            from setup import _create_sqlite_schema
            conn = self.engine.raw_connection()
            try:
                _create_sqlite_schema(conn)
                conn.commit()
            finally:
                conn.close()
        else:
            # PostgreSQL: check if tables exist, skip if they do
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'teams'"
                )).scalar()
                if result > 0:
                    logger.info("Schema already exists, skipping creation")
                else:
                    schema_path = os.path.join(
                        os.path.dirname(__file__), "..", "..", "database", "schema.sql"
                    )
                    if os.path.exists(schema_path):
                        with open(schema_path, "r") as f:
                            schema_sql = f.read()
                        raw_conn = self.engine.raw_connection()
                        try:
                            cursor = raw_conn.cursor()
                            cursor.execute(schema_sql)
                            raw_conn.commit()
                        finally:
                            raw_conn.close()
                    else:
                        logger.warning("schema.sql not found, skipping")
        
        logger.info("Schema created/verified")
    
    def _load_existing_ids(self):
        """Load existing entity IDs from the database."""
        with self.engine.connect() as conn:
            # Teams
            try:
                rows = conn.execute(text("SELECT id, canonical_name FROM teams")).fetchall()
                for row in rows:
                    self._team_ids[row[1]] = str(row[0])
                    self._team_names[str(row[0])] = row[1]
            except Exception:
                pass
            
            # Players
            try:
                rows = conn.execute(text("SELECT id, canonical_name FROM players")).fetchall()
                for row in rows:
                    self._player_ids[row[1]] = str(row[0])
                    self._player_names[str(row[0])] = row[1]
            except Exception:
                pass
            
            # Venues
            try:
                rows = conn.execute(text("SELECT id, name FROM venues")).fetchall()
                for row in rows:
                    self._venue_ids[row[1]] = str(row[0])
            except Exception:
                pass
            
            # Competitions
            try:
                rows = conn.execute(text("SELECT id, name FROM competitions")).fetchall()
                for row in rows:
                    self._competition_ids[row[1]] = str(row[0])
            except Exception:
                pass
            
            # Matches
            try:
                rows = conn.execute(text("SELECT id, external_id FROM matches")).fetchall()
                for row in rows:
                    if row[1]:
                        self._match_ids[row[1]] = str(row[0])
            except Exception:
                pass
            
            # Innings (for idempotency on reruns)
            try:
                rows = conn.execute(text(
                    "SELECT i.id, m.external_id, i.innings_number "
                    "FROM innings i JOIN matches m ON i.match_id = m.id"
                )).fetchall()
                for row in rows:
                    self._innings_ids[(row[1], row[2])] = str(row[0])
            except Exception:
                pass
        
        logger.info(
            f"Loaded existing: {len(self._team_ids)} teams, "
            f"{len(self._player_ids)} players, "
            f"{len(self._venue_ids)} venues, "
            f"{len(self._match_ids)} matches"
        )
    
    def _new_id(self) -> str:
        """Generate a new UUID string."""
        return str(uuid.uuid4())
    
    def _upsert_sql(self, table: str, pk_col: str, columns: list[str]) -> str:
        """Generate dialect-aware upsert SQL.
        
        SQLite: INSERT OR IGNORE
        PostgreSQL: INSERT ... ON CONFLICT (pk) DO NOTHING
        """
        col_list = ", ".join([pk_col] + columns)
        placeholders = ", ".join([f":{c}" for c in [pk_col] + columns])
        
        if self.is_sqlite:
            return f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})"
        else:
            # PostgreSQL: ON CONFLICT DO NOTHING
            return f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT ({pk_col}) DO NOTHING"
    
    # ============================================================
    # Entity Resolution
    # ============================================================
    
    def resolve_team(self, name: str) -> str:
        """Get or create a team, returning its UUID."""
        canonical, short = self._normalize_team_name(name)
        
        # Check if already resolved by raw or canonical name
        if canonical in self._team_ids:
            # Store both raw and canonical mappings
            self._team_ids[name] = self._team_ids[canonical]
            return self._team_ids[canonical]
        if name in self._team_ids:
            return self._team_ids[name]
        
        team_id = self._new_id()
        
        with self.engine.connect() as conn:
            conn.execute(
                text(self._upsert_sql("teams", "id", ["canonical_name", "short_name", "country", "is_active"])),
                {"id": team_id, "canonical_name": canonical, "short_name": short, "country": canonical, "is_active": True}
            )
            conn.commit()
        
        self._team_ids[name] = team_id
        self._team_ids[canonical] = team_id
        self._team_names[team_id] = canonical
        
        return team_id
    
    def resolve_player(
        self, name: str, country: str = "", team_id: str = None,
        role: str = "", batting_style: str = "",
        bowling_style: str = "", bowling_type: str = "",
        external_id: str = "",
    ) -> str:
        """Get or create a player, returning its UUID."""
        if name in self._player_ids:
            return self._player_ids[name]
        
        player_id = self._new_id()
        
        with self.engine.connect() as conn:
            conn.execute(
                text(self._upsert_sql("players", "id", [
                    "canonical_name", "country", "team_id", "role",
                    "batting_style", "bowling_style", "bowling_type", "is_active"
                ])),
                {
                    "id": player_id, "canonical_name": name, "country": country,
                    "team_id": team_id or None, "role": role,
                    "batting_style": batting_style, "bowling_style": bowling_style,
                    "bowling_type": bowling_type, "is_active": True,
                }
            )
            conn.commit()
        
        self._player_ids[name] = player_id
        self._player_names[player_id] = name
        
        return player_id
    
    def resolve_venue(self, name: str, city: str = "", country: str = "") -> str:
        """Get or create a venue, returning its UUID."""
        if name in self._venue_ids:
            return self._venue_ids[name]
        
        venue_id = self._new_id()
        
        with self.engine.connect() as conn:
            conn.execute(
                text(self._upsert_sql("venues", "id", ["name", "city", "country"])),
                {"id": venue_id, "name": name, "city": city or "", "country": country or ""}
            )
            conn.commit()
        
        self._venue_ids[name] = venue_id
        return venue_id
    
    def resolve_competition(self, name: str, format: str = "", season: str = "") -> str:
        """Get or create a competition, returning its UUID."""
        if name in self._competition_ids:
            return self._competition_ids[name]
        
        comp_id = self._new_id()
        
        with self.engine.connect() as conn:
            conn.execute(
                text(self._upsert_sql("competitions", "id", ["name", "format", "season"])),
                {"id": comp_id, "name": name, "format": format or "", "season": season or ""}
            )
            conn.commit()
        
        self._competition_ids[name] = comp_id
        return comp_id
    
    def resolve_season(self, competition_id: str, season_name: str) -> str:
        """Get or create a season/edition for a competition."""
        cache_key = f"{competition_id}:{season_name}"
        if hasattr(self, '_season_ids') and cache_key in self._season_ids:
            return self._season_ids[cache_key]
        
        if not hasattr(self, '_season_ids'):
            self._season_ids = {}
        
        season_id = self._new_id()
        
        with self.engine.connect() as conn:
            conn.execute(
                text(self._upsert_sql("seasons", "id", ["competition_id", "name"])),
                {"id": season_id, "competition_id": competition_id, "name": season_name}
            )
            conn.commit()
        
        self._season_ids[cache_key] = season_id
        return season_id
    
    def _normalize_team_name(self, name: str) -> tuple[str, str]:
        """Normalize a team name to (canonical_name, short_name)."""
        from data_pipeline.spark.normalize import normalize_team_name
        return normalize_team_name(name)
    
    def _normalize_venue_name(self, name: str) -> str:
        """Normalize a venue name to its canonical form."""
        from data_pipeline.spark.normalize import normalize_venue_name
        return normalize_venue_name(name)
    
    # ============================================================
    # Bulk Entity Resolution
    # ============================================================
    
    def discover_entities(self, df: pd.DataFrame):
        """
        Discover all teams, players, venues from the delivery DataFrame.
        
        Must be called before writing matches/deliveries.
        """
        logger.info("Discovering entities from data...")
        
        # Discover teams
        all_teams = set()
        all_teams.update(df["batting_team"].dropna().unique())
        all_teams.update(df["bowling_team"].dropna().unique())
        all_teams.update(df["team_a"].dropna().unique())
        all_teams.update(df["team_b"].dropna().unique())
        all_teams.update(df["toss_winner"].dropna().unique())
        if "winner" in df.columns:
            all_teams.update(df["winner"].dropna().unique())
        
        for team in sorted(all_teams):
            if team and team not in self._team_ids:
                self.resolve_team(team)
        
        logger.info(f"  Discovered {len(self._team_ids)} teams")
        
        # Discover venues (normalize names to merge duplicates)
        from data_pipeline.spark.normalize import normalize_venue_name
        venue_data = df[["venue", "city"]].drop_duplicates()
        for _, row in venue_data.iterrows():
            v = row.get("venue", "")
            c = row.get("city", "")
            if v:
                v = normalize_venue_name(v)
            if v and v not in self._venue_ids:
                self.resolve_venue(v, c or "")
        
        logger.info(f"  Discovered {len(self._venue_ids)} venues")
        
        # Discover players from all columns
        player_names = set()
        player_names.update(df["batter"].dropna().unique())
        player_names.update(df["bowler"].dropna().unique())
        player_names.update(df["non_striker"].dropna().unique())
        player_names.update(df["dismissed_player"].dropna().unique())
        player_names.update(df["player_of_match"].dropna().unique())
        
        # Also extract from player lists
        for _, row in df.head(1000).iterrows():  # Sample for efficiency
            for team_key in ["team_a_players", "team_b_players"]:
                players_str = row.get(team_key, "")
                if players_str:
                    for p in players_str.split(","):
                        if p.strip():
                            player_names.add(p.strip())
        
        # Track which players bowl significantly (30+ balls) vs bat
        bowler_ball_counts = df["bowler"].value_counts()
        bowlers_set = set(bowler_ball_counts[bowler_ball_counts >= 30].index)
        batters_set = set(df["batter"].dropna().unique())
        
        # Build player → team mapping from the first appearance
        player_team_map = {}
        player_country_map = {}
        for _, row in df.iterrows():
            batter = row.get("batter", "")
            batting_team = row.get("batting_team", "")
            if batter and batter not in player_team_map and batting_team:
                player_team_map[batter] = batting_team
            bowler = row.get("bowler", "")
            bowling_team = row.get("bowling_team", "")
            if bowler and bowler not in player_team_map and bowling_team:
                player_team_map[bowler] = bowling_team
        
        for name in sorted(player_names):
            if name and name not in self._player_ids:
                raw_team = player_team_map.get(name, "")
                team_name, _ = self._normalize_team_name(raw_team) if raw_team else ("", "")
                team_id = self._team_ids.get(team_name, None)
                # Infer role from appearances
                appears_batting = name in batters_set
                appears_bowling = name in bowlers_set
                if appears_batting and appears_bowling:
                    role = "allrounder"
                elif appears_bowling:
                    role = "bowler"
                else:
                    role = "batsman"
                self.resolve_player(name, team_id=team_id, role=role)
        
        logger.info(f"  Discovered {len(self._player_ids)} players")
    
    # ============================================================
    # Match Writing
    # ============================================================
    
    def write_matches(self, df: pd.DataFrame) -> int:
        """
        Write unique matches from delivery DataFrame.
        
        Returns count of matches written.
        """
        # Extract match-level rows
        match_cols = [
            "match_id", "match_date", "format", "venue", "city",
            "team_a", "team_b", "toss_winner", "toss_decision",
            "winner", "win_by_runs", "win_by_wickets",
            "player_of_match", "event_name", "match_number", "competition",
            "season", "result_type",
        ]
        available_cols = [c for c in match_cols if c in df.columns]
        matches_df = df[available_cols].drop_duplicates(subset=["match_id"])
        
        count = 0
        with self.engine.connect() as conn:
            for _, row in matches_df.iterrows():
                match_external_id = str(row["match_id"])
                if match_external_id in self._match_ids:
                    continue  # Already exists (upsert)
                
                match_db_id = self._new_id()
                
                # Resolve foreign keys
                venue_raw = row.get("venue", "")
                venue_id = self._venue_ids.get(self._normalize_venue_name(venue_raw), None)
                team_a_id = self._team_ids.get(row.get("team_a", ""), None)
                team_b_id = self._team_ids.get(row.get("team_b", ""), None)
                toss_winner_id = self._team_ids.get(row.get("toss_winner", ""), None)
                winner_id = self._team_ids.get(row.get("winner", ""), None)
                pom_id = self._player_ids.get(row.get("player_of_match", ""), None)
                
                # Determine competition_id
                event_name = str(row.get("event_name", "")) or str(row.get("competition", ""))
                comp_id = None
                if event_name and event_name in self._competition_ids:
                    comp_id = self._competition_ids[event_name]
                
                # Determine season_id from match date and competition
                season_id = None
                if comp_id:
                    match_date_tmp = row.get("match_date")
                    if pd.notna(match_date_tmp) and match_date_tmp is not None:
                        if isinstance(match_date_tmp, pd.Timestamp):
                            season_name = str(match_date_tmp.year)
                        else:
                            season_name = str(match_date_tmp)[:4]
                        season_id = self.resolve_season(comp_id, season_name)
                
                # Parse date
                match_date = row.get("match_date")
                if pd.isna(match_date) or match_date is None:
                    match_date = date(2000, 1, 1)
                elif isinstance(match_date, pd.Timestamp):
                    match_date = match_date.date()
                
                # Determine win type and margin
                win_margin = None
                win_type = None
                if pd.notna(row.get("win_by_runs")) and row["win_by_runs"]:
                    win_margin = int(row["win_by_runs"])
                    win_type = "runs"
                elif pd.notna(row.get("win_by_wickets")) and row["win_by_wickets"]:
                    win_margin = int(row["win_by_wickets"])
                    win_type = "wickets"
                
                # Determine result_type
                result_type = row.get("result_type", "win") if "result_type" in df.columns else "win"
                if not result_type or pd.isna(result_type):
                    result_type = "win"
                
                # Count deliveries for this match
                match_deliveries = df[df["match_id"] == match_external_id]
                total_deliveries = len(match_deliveries)
                total_innings = int(match_deliveries["innings_number"].max()) if len(match_deliveries) > 0 else 2
                
                conn.execute(
                    text(self._upsert_sql("matches", "id", [
                        "external_id", "competition_id", "season_id", "venue_id", "match_date", "format",
                        "team_a_id", "team_b_id", "toss_winner_id", "toss_decision",
                        "winner_id", "win_margin", "win_type", "result_type",
                        "player_of_match_id",
                        "total_innings", "total_deliveries"
                    ])),
                    {
                        "id": match_db_id,
                        "external_id": match_external_id,
                        "competition_id": comp_id or None,
                        "season_id": season_id or None,
                        "venue_id": venue_id or None,
                        "match_date": match_date,
                        "format": row.get("format", ""),
                        "team_a_id": team_a_id or None,
                        "team_b_id": team_b_id or None,
                        "toss_winner_id": toss_winner_id or None,
                        "toss_decision": row.get("toss_decision", ""),
                        "winner_id": winner_id or None,
                        "win_margin": win_margin,
                        "win_type": win_type,
                        "result_type": result_type,
                        "player_of_match_id": pom_id or None,
                        "total_innings": total_innings,
                        "total_deliveries": total_deliveries,
                    }
                )
                
                self._match_ids[match_external_id] = match_db_id
                count += 1
            
            conn.commit()
        
        logger.info(f"  Wrote {count} matches to database")
        return count
    
    def write_innings(self, df: pd.DataFrame) -> int:
        """
        Write innings from delivery DataFrame.
        
        Returns count of innings written.
        """
        # Extract innings-level rows
        innings_groups = df.groupby(["match_id", "innings_number"]).agg(
            batting_team=("batting_team", "first"),
            bowling_team=("bowling_team", "first"),
            total_runs=("runs_total", "sum"),
            total_wickets=("is_wicket", "sum"),
            max_over=("over_number", "max"),
            ball_count=("ball_in_over", "count"),
        ).reset_index()
        
        count = 0
        with self.engine.connect() as conn:
            for _, row in innings_groups.iterrows():
                match_ext_id = str(row["match_id"])
                match_db_id = self._match_ids.get(match_ext_id, "")
                if not match_db_id:
                    continue
                
                key = (match_ext_id, int(row["innings_number"]))
                if key in self._innings_ids:
                    continue
                
                innings_id = self._new_id()
                batting_team_id = self._team_ids.get(row["batting_team"], None)
                bowling_team_id = self._team_ids.get(row["bowling_team"], None)
                
                # Calculate overs: max_over + (last_ball / 6)
                total_overs = float(row["max_over"]) + (row["ball_count"] % 6) / 10.0 if row["ball_count"] > 0 else 0
                
                conn.execute(
                    text(self._upsert_sql("innings", "id", [
                        "match_id", "innings_number", "batting_team_id", "bowling_team_id",
                        "total_runs", "total_wickets", "total_overs"
                    ])),
                    {
                        "id": innings_id,
                        "match_id": match_db_id,
                        "innings_number": int(row["innings_number"]),
                        "batting_team_id": batting_team_id or None,
                        "bowling_team_id": bowling_team_id or None,
                        "total_runs": int(row["total_runs"]),
                        "total_wickets": int(row["total_wickets"]),
                        "total_overs": round(total_overs, 1),
                    }
                )
                
                self._innings_ids[key] = innings_id
                count += 1
            
            conn.commit()
        
        logger.info(f"  Wrote {count} innings to database")
        return count
    
    def write_affiliations(self, df: pd.DataFrame):
        """Write player-team affiliations from delivery data.
        
        Creates affiliation records for each (player, team, format) combination.
        Skips existing affiliations to ensure idempotency.
        """
        logger.info("Writing player-team affiliations...")
        
        # Extract (player, team, format) combinations from deliveries
        affiliations = set()
        for _, row in df.iterrows():
            batter = row.get("batter", "")
            batting_team = row.get("batting_team", "")
            bowler = row.get("bowler", "")
            bowling_team = row.get("bowling_team", "")
            fmt = row.get("format", "")
            
            if batter and batting_team:
                affiliations.add((batter, batting_team, fmt))
            if bowler and bowling_team:
                affiliations.add((bowler, bowling_team, fmt))
        
        # Load existing affiliations to skip duplicates
        existing = set()
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(text(
                    "SELECT p.canonical_name, t.canonical_name, a.format "
                    "FROM player_team_affiliations a "
                    "JOIN players p ON a.player_id = p.id "
                    "JOIN teams t ON a.team_id = t.id"
                )).fetchall()
                for row in rows:
                    existing.add((row[0], row[1], row[2] or ""))
        except Exception:
            pass
        
        count = 0
        skipped = 0
        with self.engine.connect() as conn:
            for player_name, team_name, fmt in affiliations:
                # Skip if already exists
                if (player_name, team_name, fmt) in existing:
                    skipped += 1
                    continue
                
                player_id = self._player_ids.get(player_name)
                team_id = self._team_ids.get(team_name)
                if not player_id or not team_id:
                    continue
                
                aff_id = self._new_id()
                conn.execute(
                    text(self._upsert_sql(
                        "player_team_affiliations", "id",
                        ["player_id", "team_id", "format", "is_current"]
                    )),
                    {
                        "id": aff_id,
                        "player_id": player_id,
                        "team_id": team_id,
                        "format": fmt or None,
                        "is_current": True,
                    }
                )
                count += 1
            
            conn.commit()
        
        if skipped > 0:
            logger.info(f"  Skipped {skipped} existing affiliations")
        logger.info(f"  Wrote {count} player-team affiliations")
    
    def write_deliveries_batch(self, df: pd.DataFrame, batch_size: int = 5000) -> int:
        """
        Write deliveries in batches.
        
        Skips deliveries that already exist (matched by innings_id + over + ball).
        Returns count of deliveries written.
        """
        total = 0
        skipped = 0
        
        # Load existing deliveries to avoid duplicates on rerun
        existing_deliveries = set()
        try:
            with self.engine.connect() as conn:
                rows = conn.execute(text(
                    "SELECT innings_id, over_number, ball_in_over FROM deliveries"
                )).fetchall()
                for row in rows:
                    existing_deliveries.add((str(row[0]), row[1], row[2]))
        except Exception:
            pass
        
        # Process in batches
        for start in range(0, len(df), batch_size):
            batch = df.iloc[start:start + batch_size]
            rows_to_insert = []
            
            for _, row in batch.iterrows():
                match_ext_id = str(row["match_id"])
                match_db_id = self._match_ids.get(match_ext_id, "")
                innings_key = (match_ext_id, int(row["innings_number"]))
                innings_id = self._innings_ids.get(innings_key, "")
                
                if not match_db_id or not innings_id:
                    continue
                
                # Skip if already exists
                over_num = int(row["over_number"])
                ball_num = int(row["ball_in_over"])
                if (innings_id, over_num, ball_num) in existing_deliveries:
                    skipped += 1
                    continue
                
                striker_id = self._player_ids.get(row.get("batter", ""), None)
                non_striker_id = self._player_ids.get(row.get("non_striker", ""), None)
                bowler_id = self._player_ids.get(row.get("bowler", ""), None)
                dismissed_id = self._player_ids.get(row.get("dismissed_player", ""), None) if row.get("dismissed_player") else None
                
                rows_to_insert.append({
                    "id": self._new_id(),
                    "innings_id": innings_id,
                    "match_id": match_db_id,
                    "over_number": over_num,
                    "ball_in_over": ball_num,
                    "striker_id": striker_id,
                    "non_striker_id": non_striker_id or None,
                    "bowler_id": bowler_id,
                    "runs_bat": int(row.get("runs_batter", 0)),
                    "runs_extras": int(row.get("runs_extras", 0)),
                    "total_runs": int(row.get("runs_total", 0)),
                    "extra_type": row.get("extra_type"),
                    "is_wicket": bool(row.get("is_wicket", False)),
                    "wicket_type": row.get("wicket_type"),
                    "dismissed_player_id": dismissed_id or None,
                })
            
            if rows_to_insert:
                # Remove rows with empty foreign keys
                rows_to_insert = [
                    r for r in rows_to_insert
                    if r.get("match_id") and r.get("innings_id")
                ]
                if rows_to_insert:
                    insert_df = pd.DataFrame(rows_to_insert)
                    insert_df.to_sql(
                        "deliveries", self.engine, if_exists="append",
                        index=False, method="multi", chunksize=1000,
                    )
                    total += len(rows_to_insert)
            
            if (start // batch_size + 1) % 5 == 0:
                logger.info(f"  Written {total} deliveries...")
        
        if skipped > 0:
            logger.info(f"  Skipped {skipped} existing deliveries")
        logger.info(f"  Wrote {total} deliveries to database")
        return total
    
    # ============================================================
    # Analytics Writing
    # ============================================================
    
    def write_analytics_table(self, df: pd.DataFrame, table_name: str, format_filter: str = None):
        """Write a pandas DataFrame to an analytics table.
        
        If format_filter is provided, only deletes existing rows for that format
        (preserving other formats). Otherwise truncates the entire table.
        
        This is critical for multi-format ingestion: running T20I analytics
        must not destroy IPL analytics.
        """
        if df.empty:
            logger.info(f"  Skipping {table_name} (empty)")
            return
        
        # Add UUID column if not present
        if "id" not in df.columns:
            df = df.copy()
            df["id"] = [str(uuid.uuid4()) for _ in range(len(df))]
        
        try:
            with self.engine.connect() as conn:
                if format_filter:
                    # Only delete rows for this format (preserves other formats)
                    conn.execute(text(f"DELETE FROM {table_name} WHERE format = :fmt"), {"fmt": format_filter})
                elif self.is_sqlite:
                    conn.execute(text(f"DELETE FROM {table_name}"))
                else:
                    conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"))
                conn.commit()
            
            df.to_sql(
                table_name, self.engine, if_exists="append",
                index=False, method="multi", chunksize=1000,
            )
            logger.info(f"  Wrote {len(df)} rows to {table_name}")
        except Exception as e:
            logger.error(f"  Failed to write to {table_name}: {e}")
            raise
    
    # ============================================================
    # Utility
    # ============================================================
    
    def get_table_counts(self) -> dict:
        """Get row counts for all tables."""
        tables = [
            "teams", "players", "venues", "competitions",
            "matches", "innings", "deliveries",
            "player_batting_stats", "player_bowling_stats", "player_form",
            "team_performance", "venue_stats", "batter_bowler_matchups",
            "seasons", "format_config", "player_team_affiliations",
        ]
        counts = {}
        with self.engine.connect() as conn:
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    counts[table] = result.scalar()
                except Exception:
                    counts[table] = 0
        return counts
    
    def close(self):
        """Dispose of the connection pool."""
        self.engine.dispose()
