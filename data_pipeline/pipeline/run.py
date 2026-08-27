"""
Cricket Intelligence Pipeline — Pandas Implementation
======================================================

Main orchestrator for the data pipeline using pandas.

Stages:
1. INGEST   → Download/extract Cricsheet data
2. READ     → Parse JSON into DataFrames
3. VALIDATE → Check data quality
4. RESOLVE  → Discover and resolve entities (teams, players, venues)
5. WRITE    → Write core entities to database
6. COMPUTE  → Calculate analytics
7. WRITE    → Write analytics to database
8. REPORT   → Summary statistics

Usage:
    python -m data_pipeline.pipeline.run --format t20i --sample 50
    python -m data_pipeline.pipeline.run --format ipl
    python -m data_pipeline.pipeline.run --format all
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.ingestion.cricsheet import CricsheetIngestor
from data_pipeline.pipeline.reader import read_directory
from data_pipeline.pipeline.db_manager import DatabaseManager
from data_pipeline.pipeline.analytics import (
    compute_player_batting_stats,
    compute_player_bowling_stats,
    compute_player_form_scores,
    compute_team_performance,
    compute_venue_stats,
    compute_matchups,
)

logger = logging.getLogger(__name__)


class CricketPipeline:
    """
    Pandas-based cricket data pipeline.
    
    Orchestrates download, parsing, entity resolution, analytics,
    and database writing.
    """
    
    def __init__(
        self,
        data_dir: str = "data/raw",
        database_url: str = None,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.ingestor = CricsheetIngestor(str(self.data_dir))
        self.db = DatabaseManager(database_url=database_url)
        
        self.stats = {
            "matches_processed": 0,
            "deliveries_processed": 0,
            "matches_rejected": 0,
            "players_discovered": 0,
            "teams_discovered": 0,
            "venues_discovered": 0,
            "processing_time_seconds": 0,
        }
    
    def initialize(self):
        """Initialize database schema and load existing IDs."""
        self.db.initialize()
    
    def ingest(self, format_type: str, force: bool = False) -> Path:
        """Stage 1: Download and extract Cricsheet data."""
        logger.info(f"[Stage 1] Downloading {format_type} data from Cricsheet...")
        self.ingestor.download(format_type, force=force)
        extract_dir = self.ingestor.extract(format_type, force=force)
        count = self.ingestor.get_match_count(format_type)
        logger.info(f"[Stage 1] Ready: {count} match files in {extract_dir}")
        return extract_dir
    
    def read(self, extract_dir: Path, match_limit: int = None) -> pd.DataFrame:
        """Stage 2: Read and flatten JSON match files."""
        logger.info(f"[Stage 2] Reading match files from {extract_dir}...")
        df = read_directory(extract_dir, match_limit=match_limit)
        self.stats["deliveries_processed"] = len(df)
        self.stats["matches_processed"] = df["match_id"].nunique()
        logger.info(
            f"[Stage 2] {self.stats['matches_processed']} matches, "
            f"{self.stats['deliveries_processed']} deliveries"
        )
        return df
    
    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Stage 3: Validate data quality."""
        logger.info("[Stage 3] Validating data quality...")
        initial = len(df)
        
        valid = df[
            df["batter"].notna() &
            df["bowler"].notna() &
            (df["runs_batter"] >= 0) &
            (df["runs_total"] >= 0) &
            (df["over_number"] >= 0) &
            (df["over_number"] <= 100)
        ].copy()
        
        rejected = initial - len(valid)
        self.stats["matches_rejected"] = rejected
        logger.info(
            f"[Stage 3] {len(valid)} valid, {rejected} rejected "
            f"({rejected/max(initial,1)*100:.1f}%)"
        )
        return valid
    
    def resolve_entities(self, df: pd.DataFrame):
        """Stage 4: Discover and resolve entities."""
        logger.info("[Stage 4] Discovering entities...")
        self.db.discover_entities(df)
        self.stats["teams_discovered"] = len(self.db._team_ids)
        self.stats["players_discovered"] = len(self.db._player_ids)
        self.stats["venues_discovered"] = len(self.db._venue_ids)
        
        # Discover competitions
        event_names = df["event_name"].dropna().unique()
        event_names = [e for e in event_names if e]
        for event in event_names:
            fmt = df[df["event_name"] == event]["format"].mode()
            fmt_val = fmt.iloc[0] if len(fmt) > 0 else ""
            self.db.resolve_competition(event, format=fmt_val)
        
        logger.info(
            f"[Stage 4] {self.stats['teams_discovered']} teams, "
            f"{self.stats['players_discovered']} players, "
            f"{self.stats['venues_discovered']} venues, "
            f"{len(self.db._competition_ids)} competitions"
        )
    
    def write_core_data(self, df: pd.DataFrame):
        """Stage 5: Write core entities to database."""
        logger.info("[Stage 5] Writing core entities to database...")
        self.db.write_matches(df)
        self.db.write_innings(df)
        self.db.write_deliveries_batch(df)
        self.db.write_affiliations(df)
    
    def compute_analytics(self, df: pd.DataFrame) -> dict:
        """Stage 6: Compute all analytics."""
        logger.info("[Stage 6] Computing analytics...")
        
        results = {}
        
        # Player batting stats
        results["batting"] = compute_player_batting_stats(df)
        
        # Player bowling stats
        results["bowling"] = compute_player_bowling_stats(df)
        
        # Form scores
        results["form"] = compute_player_form_scores(df)
        
        # Team performance
        results["team"] = compute_team_performance(df)
        
        # Venue stats
        results["venue"] = compute_venue_stats(df)
        
        # Matchups
        results["matchups"] = compute_matchups(df)
        
        return results
    
    def write_analytics(self, analytics: dict, format_filter: str = None):
        """Stage 7: Write analytics to database.
        
        If format_filter is provided, only deletes existing analytics for that format
        before inserting new ones (preserving other formats).
        """
        logger.info("[Stage 7] Writing analytics to database...")
        
        batting_df = analytics["batting"]
        bowling_df = analytics["bowling"]
        form_df = analytics["form"]
        matchups_df = analytics["matchups"]
        
        # --- Player Batting Stats ---
        if not batting_df.empty:
            batting_df = self._resolve_player_ids(batting_df, "player_name")
            cols = [
                "player_id", "format", "period",
                "matches", "innings", "not_outs", "runs", "highest_score",
                "batting_average", "strike_rate", "balls_faced",
                "fours", "sixes", "boundary_pct", "dot_ball_pct",
                "fifties", "hundreds",
                "powerplay_runs", "powerplay_strike_rate",
                "middle_runs", "middle_strike_rate",
                "death_runs", "death_strike_rate",
                "chasing_runs", "chasing_strike_rate",
            ]
            write_df = batting_df[[c for c in cols if c in batting_df.columns]].copy()
            self.db.write_analytics_table(write_df, "player_batting_stats", format_filter=format_filter)
        
        # --- Player Bowling Stats ---
        if not bowling_df.empty:
            bowling_df = self._resolve_player_ids(bowling_df, "player_name")
            cols = [
                "player_id", "format", "period",
                "matches", "innings", "overs", "balls_bowled",
                "wickets", "runs_conceded", "bowling_average",
                "strike_rate", "economy", "dot_ball_pct",
                "boundary_conceded_pct",
                "powerplay_overs", "powerplay_wickets", "powerplay_economy",
                "middle_overs", "middle_wickets", "middle_economy",
                "death_overs", "death_wickets", "death_economy",
            ]
            write_df = bowling_df[[c for c in cols if c in bowling_df.columns]].copy()
            self.db.write_analytics_table(write_df, "player_bowling_stats", format_filter=format_filter)
        
        # --- Player Form ---
        if not form_df.empty:
            form_df = self._resolve_player_ids(form_df, "player_name")
            cols = [
                "player_id", "format", "form_score",
                "recent_performance_component", "consistency_component",
                "opposition_strength_component", "venue_performance_component",
                "match_situation_component", "efficiency_component",
                "recent_innings_count",
            ]
            write_df = form_df[[c for c in cols if c in form_df.columns]].copy()
            self.db.write_analytics_table(write_df, "player_form", format_filter=format_filter)
        
        # --- Team Performance ---
        team_df = analytics["team"]
        if not team_df.empty:
            team_df = self._resolve_team_ids(team_df, "team_name")
            cols = [
                "team_id", "format", "period",
                "matches", "wins", "losses", "win_rate",
                "avg_first_innings_score", "avg_second_innings_score",
                "avg_powerplay_score", "avg_middle_overs_score", "avg_death_overs_score",
                "avg_economy",
                "batting_strength_score", "bowling_strength_score", "overall_strength_score",
                "chasing_win_pct", "defending_win_pct",
            ]
            write_df = team_df[[c for c in cols if c in team_df.columns]].copy()
            self.db.write_analytics_table(write_df, "team_performance", format_filter=format_filter)
        
        # --- Venue Stats ---
        venue_df = analytics["venue"]
        if not venue_df.empty:
            venue_df = self._resolve_venue_ids(venue_df, "venue_name")
            cols = [
                "venue_id", "format",
                "total_matches", "avg_first_innings_score", "avg_second_innings_score",
                "highest_total", "lowest_total",
                "chasing_win_pct", "defending_win_pct",
                "pace_wickets_pct", "spin_wickets_pct",
                "avg_powerplay_runs", "avg_middle_overs_runs", "avg_death_overs_runs",
                "boundary_frequency",
            ]
            write_df = venue_df[[c for c in cols if c in venue_df.columns]].copy()
            self.db.write_analytics_table(write_df, "venue_stats", format_filter=format_filter)
        
        # --- Matchups ---
        if not matchups_df.empty:
            matchups_df = self._resolve_player_ids(matchups_df, "batter_name", target_col="batter_id")
            matchups_df = self._resolve_player_ids(matchups_df, "bowler_name", target_col="bowler_id")
            cols = [
                "batter_id", "bowler_id", "format",
                "total_balls", "total_runs", "total_wickets",
                "strike_rate", "batting_average",
                "dot_balls", "boundaries", "sixes",
            ]
            write_df = matchups_df[[c for c in cols if c in matchups_df.columns]].copy()
            self.db.write_analytics_table(write_df, "batter_bowler_matchups", format_filter=format_filter)
    
    def _resolve_player_ids(self, df: pd.DataFrame, name_col: str, target_col: str = "player_id") -> pd.DataFrame:
        """Resolve player names to UUIDs in a DataFrame.
        
        Uses a multi-step resolution:
        1. Direct lookup in _player_ids cache (canonical name -> id)
        2. Fallback via _player_name_mappings (source name -> canonical -> id)
        3. If still unresolved, log and leave as None
        """
        df = df.copy()
        # Direct lookup
        df[target_col] = df[name_col].map(self.db._player_ids)
        # Fallback: resolve via name mappings for unresolved names
        unresolved_mask = df[target_col].isna() & df[name_col].notna() & (df[name_col] != "")
        if unresolved_mask.any():
            unresolved_names = df.loc[unresolved_mask, name_col].unique()
            resolved = 0
            for name in unresolved_names:
                canonical = self.db._player_name_mappings.get(name)
                if canonical and canonical in self.db._player_ids:
                    df.loc[df[name_col] == name, target_col] = self.db._player_ids[canonical]
                    resolved += 1
            remaining = unresolved_mask.sum() - resolved
            if remaining > 0:
                remaining_names = df.loc[df[name_col].map(self.db._player_ids).isna() & df[name_col].notna(), name_col].unique()[:10]
                logger.warning(f"  {remaining} rows unresolved in {name_col}. Examples: {list(remaining_names)}")
        return df
    
    def _resolve_team_ids(self, df: pd.DataFrame, name_col: str) -> pd.DataFrame:
        """Resolve team names to UUIDs in a DataFrame."""
        df = df.copy()
        df["team_id"] = df[name_col].map(self.db._team_ids)
        return df
    
    def _resolve_venue_ids(self, df: pd.DataFrame, name_col: str) -> pd.DataFrame:
        """Resolve venue names to UUIDs in a DataFrame."""
        df = df.copy()
        df["venue_id"] = df[name_col].map(self.db._venue_ids)
        return df
    
    def run(
        self,
        format_type: str = "t20i",
        force: bool = False,
        match_limit: int = None,
    ):
        """
        Run the complete pipeline.
        
        Args:
            format_type: 't20i', 'odi', 'test', 'ipl', or 'all'
            force: Force re-download
            match_limit: Limit matches (for testing)
        """
        start_time = time.time()
        
        try:
            self.initialize()
            
            formats_to_process = (
                ["ipl", "t20i", "odi", "test"]
                if format_type == "all"
                else [format_type]
            )
            
            for fmt in formats_to_process:
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing format: {fmt.upper()}")
                logger.info(f"{'='*60}")
                
                try:
                    extract_dir = self.ingest(fmt, force=force)
                except Exception as e:
                    logger.warning(f"Could not ingest {fmt}: {e}")
                    continue
                
                limit = match_limit if format_type != "all" else None
                df = self.read(extract_dir, match_limit=limit)
                
                if df.empty:
                    logger.warning(f"No data for {fmt}, skipping")
                    continue
                
                df = self.validate(df)
                
                # Normalize venue and team names to merge duplicates
                from data_pipeline.spark.normalize import normalize_venue_name, normalize_team_name, normalize_format
                df["venue"] = df["venue"].apply(lambda v: normalize_venue_name(v) if pd.notna(v) else v)
                for col in ["batting_team", "bowling_team", "team_a", "team_b", "toss_winner", "winner"]:
                    if col in df.columns:
                        df[col] = df[col].apply(lambda v: normalize_team_name(v)[0] if pd.notna(v) and v else v)
                # Normalize format to canonical form (T20I, ODI, Test, T20)
                df["format"] = df["format"].apply(lambda v: normalize_format(v) if pd.notna(v) and v else v)
                
                self.resolve_entities(df)
                self.write_core_data(df)
                
                analytics = self.compute_analytics(df)
                # Use the canonical format from the data for format-scoped analytics
                canonical_fmt = df["format"].mode().iloc[0] if len(df) > 0 else fmt.upper()
                self.write_analytics(analytics, format_filter=canonical_fmt)
            
            # Report
            elapsed = round(time.time() - start_time, 2)
            self.stats["processing_time_seconds"] = elapsed
            
            logger.info(f"\n{'='*60}")
            logger.info("PIPELINE COMPLETE")
            logger.info(f"{'='*60}")
            logger.info(f"  Matches processed: {self.stats['matches_processed']}")
            logger.info(f"  Deliveries processed: {self.stats['deliveries_processed']}")
            logger.info(f"  Teams discovered: {self.stats['teams_discovered']}")
            logger.info(f"  Players discovered: {self.stats['players_discovered']}")
            logger.info(f"  Venues discovered: {self.stats['venues_discovered']}")
            logger.info(f"  Processing time: {elapsed}s")
            logger.info(f"{'='*60}")
            
            # Show DB state
            counts = self.db.get_table_counts()
            logger.info("\nDatabase table counts:")
            for table, count in counts.items():
                logger.info(f"  {table}: {count}")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise
        finally:
            self.db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Cricket Intelligence Platform — Data Pipeline"
    )
    parser.add_argument(
        "--format", "-f",
        default="ipl",
        choices=["t20i", "odi", "test", "ipl", "all"],
        help="Cricket format to process (default: ipl)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download",
    )
    parser.add_argument(
        "--sample", "-n",
        type=int,
        default=None,
        help="Limit number of matches (for testing)",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Override DATABASE_URL",
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    
    pipeline = CricketPipeline(database_url=args.database_url)
    pipeline.run(
        format_type=args.format,
        force=args.force,
        match_limit=args.sample,
    )


if __name__ == "__main__":
    main()
