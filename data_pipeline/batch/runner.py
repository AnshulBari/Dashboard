"""
Batch Runner — Process Individual Batches
==========================================

Processes a single batch of match files through the existing pipeline:

    Batch Files
    → Read (flatten JSON)
    → Validate
    → Normalize
    → Entity Resolution
    → Database Write (matches, innings, deliveries, affiliations)
    → Analytics Computation
    → Analytics Write
    → Validation Report

Uses the existing CricketPipeline components. This module adds:
- Batch manifest tracking
- Checkpoint/resume
- Error handling with status recording
- Statistics collection
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from sqlalchemy import text

import pandas as pd

from data_pipeline.batch.manifest import BatchManifest
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
from data_pipeline.spark.normalize import (
    normalize_venue_name,
    normalize_team_name,
    normalize_format,
)

logger = logging.getLogger(__name__)


class BatchRunner:
    """
    Processes individual batches of match files.

    Wraps the existing pipeline stages with batch-level
    checkpoint tracking and error handling.
    """

    def __init__(self, db: DatabaseManager, manifest: BatchManifest):
        self.db = db
        self.manifest = manifest

    def run_batch(
        self,
        format_type: str,
        batch_id: int,
        file_paths: list[Path],
        dry_run: bool = False,
    ) -> dict:
        """
        Process a single batch.

        Args:
            format_type: Format string ('t20i', 'odi', 'test', 'ipl')
            batch_id: Batch number (0-indexed)
            file_paths: List of JSON files in this batch
            dry_run: If True, don't write to database

        Returns:
            Statistics dictionary
        """
        stats = {
            "format": format_type,
            "batch_id": batch_id,
            "file_count": len(file_paths),
            "match_count": 0,
            "delivery_count": 0,
            "innings_count": 0,
            "new_players": 0,
            "new_teams": 0,
            "new_venues": 0,
            "duration_seconds": 0,
            "status": "PENDING",
        }

        start_time = time.time()

        try:
            # Register batch in manifest
            if not dry_run:
                manifest_id = self.manifest.create_batch(
                    dataset=format_type,
                    batch_id=batch_id,
                    batch_size=len(file_paths),
                    file_count=len(file_paths),
                )
                self.manifest.start_batch(format_type, batch_id)

            # Count teams/players/venues before processing
            pre_counts = self._get_entity_counts()

            # Stage 1: Read and flatten match files
            logger.info(
                f"[Batch {batch_id}] Reading {len(file_paths)} files..."
            )

            # Create a temporary directory or use the file paths directly
            # The reader expects a directory, so we need to handle this
            # by reading individual files and concatenating
            df = self._read_batch_files(file_paths)

            if df.empty:
                logger.warning(f"[Batch {batch_id}] No data found in files")
                stats["status"] = "COMPLETED"
                if not dry_run:
                    self.manifest.complete_batch(format_type, batch_id)
                return stats

            stats["match_count"] = df["match_id"].nunique()
            stats["delivery_count"] = len(df)
            logger.info(
                f"[Batch {batch_id}] Read {stats['match_count']} matches, "
                f"{stats['delivery_count']} deliveries"
            )

            # Stage 2: Validate
            df = self._validate(df)

            # Stage 3: Normalize
            df = self._normalize(df, format_type)

            # Stage 4: Entity resolution
            self.db.discover_entities(df)

            if dry_run:
                logger.info(f"[Batch {batch_id}] Dry run — skipping writes")
                stats["status"] = "DRY_RUN"
                return stats

            # Stage 5: Write core data
            logger.info(f"[Batch {batch_id}] Writing core data...")
            self.db.write_matches(df)
            self.db.write_innings(df)
            self.db.write_deliveries_batch(df)
            self.db.write_affiliations(df)

            # Count innings
            stats["innings_count"] = (
                df.groupby(["match_id", "innings_number"]).ngroups
            )

            # Stage 6: Compute analytics for this batch only.
            # Full-format recomputation should be done separately after all batches complete.
            canonical_fmt = (
                df["format"].mode().iloc[0]
                if len(df) > 0
                else format_type.upper()
            )
            logger.info(f"[Batch {batch_id}] Computing analytics for batch {batch_id}...")

            analytics = {}
            analytics["batting"] = compute_player_batting_stats(df)
            analytics["bowling"] = compute_player_bowling_stats(df)
            analytics["form"] = compute_player_form_scores(df)
            analytics["team"] = compute_team_performance(df)
            analytics["venue"] = compute_venue_stats(df)
            analytics["matchups"] = compute_matchups(df)

            # Stage 7: Write analytics (format-scoped)
            logger.info(f"[Batch {batch_id}] Writing analytics...")
            self._write_analytics(analytics, canonical_fmt)

            # Count new entities
            post_counts = self._get_entity_counts()
            stats["new_players"] = post_counts["players"] - pre_counts["players"]
            stats["new_teams"] = post_counts["teams"] - pre_counts["teams"]
            stats["new_venues"] = post_counts["venues"] - pre_counts["venues"]

            # Record completion
            stats["status"] = "COMPLETED"
            stats["duration_seconds"] = round(time.time() - start_time, 2)

            self.manifest.complete_batch(
                dataset=format_type,
                batch_id=batch_id,
                match_count=stats["match_count"],
                delivery_count=stats["delivery_count"],
                innings_count=stats["innings_count"],
                player_count=stats["new_players"],
                team_count=stats["new_teams"],
                venue_count=stats["new_venues"],
            )

            # Print batch summary
            self._print_batch_summary(stats)

            return stats

        except Exception as e:
            stats["status"] = "FAILED"
            stats["duration_seconds"] = round(time.time() - start_time, 2)
            error_msg = str(e)

            if not dry_run:
                self.manifest.fail_batch(format_type, batch_id, error_msg)

            logger.error(
                f"[Batch {batch_id}] FAILED: {error_msg}", exc_info=True
            )
            return stats

    def _read_batch_files(self, file_paths: list[Path]) -> pd.DataFrame:
        """
        Read a list of match JSON files into a single DataFrame.

        This mirrors the read_directory() function but works on
        a list of specific files rather than a directory.
        """
        all_matches = []

        for fp in file_paths:
            try:
                with open(fp, "r") as f:
                    data = json.load(f)
                # Inject filename as match_id if not present in JSON
                if not data.get("match_id"):
                    data["match_id"] = fp.stem
                flattened = self._flatten_match(data)
                if flattened is not None and not flattened.empty:
                    all_matches.append(flattened)
            except Exception as e:
                logger.warning(f"Could not read {fp.name}: {e}")
                continue

        if not all_matches:
            return pd.DataFrame()

        return pd.concat(all_matches, ignore_index=True)

    def _flatten_match(self, data: dict) -> Optional[pd.DataFrame]:
        """
        Flatten a single Cricsheet JSON match into delivery-level rows.

        This replicates the logic from reader.py's flatten_match function.
        """
        info = data.get("info", {})
        innings_list = data.get("innings", [])

        match_id = data.get("match_id") or info.get("match_id") or ""
        match_date = info.get("date") or (info.get("dates", [""])[0] if info.get("dates") else "")
        # Use prepared_format from metadata if available (set by prepare.py)
        # This handles Cricsheet T20I data where match_type='T20' but format should be 'T20I'
        meta = data.get("meta", {})
        match_type = meta.get("prepared_format") or info.get("match_type", "")
        venue = info.get("venue", "")
        city = info.get("city", "")
        teams = info.get("teams", [])
        toss_winner = info.get("toss", {}).get("winner", "")
        toss_decision = info.get("toss", {}).get("decision", "")
        outcome = info.get("outcome", {})
        outcome_winner = outcome.get("winner", "")
        outcome_by = outcome.get("by", {})
        player_of_match = ""
        pom_list = info.get("player_of_match", [])
        if pom_list:
            player_of_match = pom_list[0]

        event_name = info.get("event", {}).get("name", "")
        match_number = info.get("event", {}).get("match_number", "")

        # Determine result type
        result_type = "win"
        if "result" in outcome:
            result_type = outcome["result"]

        # Determine win margins
        win_by_runs = None
        win_by_wickets = None
        win_by_innings = None

        if isinstance(outcome_by, dict):
            if "runs" in outcome_by:
                win_by_runs = outcome_by["runs"]
            if "wickets" in outcome_by:
                win_by_wickets = outcome_by["wickets"]
            if "innings" in outcome_by:
                win_by_innings = outcome_by["innings"]

        # Player lists
        players_data = info.get("players", {})
        registry = info.get("registry", {}).get("people", {})
        team_a = teams[0] if teams else ""
        team_b = teams[1] if len(teams) > 1 else ""
        team_a_players = ",".join(players_data.get(team_a, []))
        team_b_players = ",".join(players_data.get(team_b, []))

        rows = []

        for innings_idx, innings in enumerate(innings_list):
            batting_team = innings.get("team", "")
            bowling_team = team_b if batting_team == team_a else team_a

            # Extract innings-level metadata
            innings_declared = False
            innings_all_out = False
            innings_follow_on = False

            # Check for declared/all_out/follow_on in Cricsheet data
            if "declared" in innings:
                innings_declared = True
            if innings.get("all_out", False):
                innings_all_out = True
            if innings.get("follow_on", False):
                innings_follow_on = True

            # Check for wickets falling (all out heuristic: 10 wickets)
            wicket_count = 0

            for over_data in innings.get("overs", []):
                over_number = over_data.get("over", 0)

                for ball_idx, delivery in enumerate(over_data.get("deliveries", [])):
                    batter = delivery.get("batter", "")
                    bowler = delivery.get("bowler", "")
                    non_striker = delivery.get("non_striker", "")

                    runs = delivery.get("runs", {})
                    runs_batter = runs.get("batter", 0)
                    runs_extras = runs.get("extras", 0)
                    runs_total = runs.get("total", 0)

                    # Extras
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

                    # Wickets
                    wickets = delivery.get("wickets", [])
                    is_wicket = len(wickets) > 0
                    wicket_type = None
                    dismissed_player = None

                    if is_wicket:
                        w = wickets[0]
                        wicket_type = w.get("kind", "")
                        dismissed_player = w.get("player_out", "")
                        wicket_count += 1

                    ball_in_over = ball_idx + 1

                    rows.append(
                        {
                            "match_id": match_id,
                            "match_date": match_date,
                            "format": match_type,
                            "venue": venue,
                            "city": city,
                            "batting_team": batting_team,
                            "bowling_team": bowling_team,
                            "team_a": team_a,
                            "team_b": team_b,
                            "toss_winner": toss_winner,
                            "toss_decision": toss_decision,
                            "winner": outcome_winner,
                            "win_by_runs": win_by_runs,
                            "win_by_wickets": win_by_wickets,
                            "win_by_innings": win_by_innings,
                            "result_type": result_type,
                            "player_of_match": player_of_match,
                            "event_name": event_name,
                            "match_number": match_number,
                            "innings_number": innings_idx + 1,
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
                            "innings_declared": innings_declared,
                            "innings_all_out": innings_all_out,
                            "innings_follow_on": innings_follow_on,
                            "team_a_players": team_a_players,
                            "team_b_players": team_b_players,
                        }
                    )

        if not rows:
            return None

        return pd.DataFrame(rows)

    def _validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate delivery data quality."""
        initial = len(df)

        valid = df[
            df["batter"].notna()
            & df["bowler"].notna()
            & (df["runs_batter"] >= 0)
            & (df["runs_total"] >= 0)
            & (df["over_number"] >= 0)
            & (df["over_number"] <= 100)
        ].copy()

        rejected = initial - len(valid)
        if rejected > 0:
            logger.warning(
                f"  Validation: {len(valid)} valid, {rejected} rejected"
            )

        return valid

    def _normalize(self, df: pd.DataFrame, format_type: str) -> pd.DataFrame:
        """Normalize venue, team, and format names."""
        df["venue"] = df["venue"].apply(
            lambda v: normalize_venue_name(v) if pd.notna(v) else v
        )

        for col in [
            "batting_team",
            "bowling_team",
            "team_a",
            "team_b",
            "toss_winner",
            "winner",
        ]:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda v: normalize_team_name(v)[0]
                    if pd.notna(v) and v
                    else v
                )

        df["format"] = df["format"].apply(
            lambda v: normalize_format(v) if pd.notna(v) and v else v
        )

        return df

    def _get_entity_counts(self) -> dict:
        """Get current entity counts from the database."""
        counts = {}
        with self.db.engine.connect() as conn:
            for table in ["teams", "players", "venues"]:
                try:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table}")
                    )
                    counts[table] = result.scalar()
                except Exception:
                    counts[table] = 0
        return counts

    def _load_all_format_deliveries(self, format_type: str) -> pd.DataFrame:
        """Load ALL deliveries for a format from the database.

        Uses chunked loading to avoid Supabase statement timeouts.
        Loads matches in groups of 500, then fetches deliveries for those matches.
        
        Returns empty DataFrame if deliveries table does not exist (Phase 5.6a+).
        """
        try:
            # Check if deliveries table exists
            with self.db.engine.connect() as conn:
                exists = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_name = 'deliveries' AND table_schema = 'public'"
                )).scalar()
                if not exists:
                    logger.info("  Deliveries table not found — skipping full-format analytics")
                    return pd.DataFrame()

            # First get all match IDs for this format
            match_query = """
                SELECT id FROM matches WHERE format = :fmt ORDER BY match_date
            """
            with self.db.engine.connect() as conn:
                match_ids = [r[0] for r in conn.execute(text(match_query), {"fmt": format_type}).fetchall()]

            if not match_ids:
                return pd.DataFrame()

            logger.info(f"  Loading {len(match_ids)} {format_type} matches for analytics...")

            # Load in chunks of 500 matches to avoid Supabase timeout
            chunk_size = 500
            all_chunks = []
            for i in range(0, len(match_ids), chunk_size):
                chunk_ids = match_ids[i:i+chunk_size]
                placeholders = ','.join([f":id{j}" for j in range(len(chunk_ids))])
                params = {f"id{j}": mid for j, mid in enumerate(chunk_ids)}

                query = f"""
                    SELECT
                        m.external_id as match_id, m.format, m.match_date,
                        m.venue_id, m.team_a_id, m.team_b_id,
                        m.toss_decision, m.winner_id, m.win_margin,
                        m.win_type, m.result_type,
                        i.innings_number, i.batting_team_id, i.bowling_team_id,
                        i.declared, i.all_out, i.follow_on,
                        d.over_number, d.ball_in_over,
                        d.runs_bat as runs_batter, d.runs_extras, d.total_runs as runs_total,
                        d.extra_type, d.is_wicket, d.wicket_type,
                        p_striker.canonical_name as batter,
                        p_bowler.canonical_name as bowler,
                        p_ns.canonical_name as non_striker,
                        p_dismissed.canonical_name as dismissed_player,
                        t_bat.canonical_name as batting_team,
                        t_bowl.canonical_name as bowling_team,
                        t_a.canonical_name as team_a,
                        t_b.canonical_name as team_b,
                        t_bat.canonical_name as toss_winner,
                        v.name as venue, v.city,
                        m.win_margin as win_by_runs,
                        m.win_type as win_by_wickets_type,
                        t_winner.canonical_name as winner
                    FROM deliveries d
                    JOIN innings i ON d.innings_id = i.id
                    JOIN matches m ON d.match_id = m.id
                    LEFT JOIN players p_striker ON d.striker_id = p_striker.id
                    LEFT JOIN players p_bowler ON d.bowler_id = p_bowler.id
                    LEFT JOIN players p_ns ON d.non_striker_id = p_ns.id
                    LEFT JOIN players p_dismissed ON d.dismissed_player_id = p_dismissed.id
                    LEFT JOIN teams t_bat ON i.batting_team_id = t_bat.id
                    LEFT JOIN teams t_bowl ON i.bowling_team_id = t_bowl.id
                    LEFT JOIN teams t_a ON m.team_a_id = t_a.id
                    LEFT JOIN teams t_b ON m.team_b_id = t_b.id
                    LEFT JOIN teams t_winner ON m.winner_id = t_winner.id
                    LEFT JOIN venues v ON m.venue_id = v.id
                    WHERE m.id IN ({placeholders})
                """
                with self.db.engine.connect() as conn:
                    chunk_df = pd.read_sql(text(query), conn, params=params)
                all_chunks.append(chunk_df)
                logger.info(f"    Loaded chunk {i//chunk_size + 1}/{(len(match_ids)-1)//chunk_size + 1}: {len(chunk_df)} deliveries")

            df = pd.concat(all_chunks, ignore_index=True) if all_chunks else pd.DataFrame()
            logger.info(f"  Total loaded {len(df)} deliveries for {format_type}")
            return df
        except Exception as e:
            logger.warning(f"  Could not load format deliveries: {e}")
            return pd.DataFrame()

    def _write_analytics(
        self, analytics: dict, format_filter: str
    ):
        """Write analytics to database (format-scoped)."""
        from sqlalchemy import text

        # Player Batting Stats
        batting_df = analytics["batting"]
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
            write_df = batting_df[
                [c for c in cols if c in batting_df.columns]
            ].copy()
            self.db.write_analytics_table(
                write_df, "player_batting_stats", format_filter=format_filter
            )

        # Player Bowling Stats
        bowling_df = analytics["bowling"]
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
            write_df = bowling_df[
                [c for c in cols if c in bowling_df.columns]
            ].copy()
            self.db.write_analytics_table(
                write_df, "player_bowling_stats", format_filter=format_filter
            )

        # Player Form
        form_df = analytics["form"]
        if not form_df.empty:
            form_df = self._resolve_player_ids(form_df, "player_name")
            cols = [
                "player_id", "format", "form_score",
                "recent_performance_component", "consistency_component",
                "opposition_strength_component", "venue_performance_component",
                "match_situation_component", "efficiency_component",
                "recent_innings_count",
            ]
            write_df = form_df[
                [c for c in cols if c in form_df.columns]
            ].copy()
            self.db.write_analytics_table(
                write_df, "player_form", format_filter=format_filter
            )

        # Team Performance
        team_df = analytics["team"]
        if not team_df.empty:
            team_df = self._resolve_team_ids(team_df, "team_name")
            cols = [
                "team_id", "format", "period",
                "matches", "wins", "losses", "win_rate",
                "avg_first_innings_score", "avg_second_innings_score",
                "avg_powerplay_score", "avg_middle_overs_score",
                "avg_death_overs_score", "avg_economy",
                "batting_strength_score", "bowling_strength_score",
                "overall_strength_score",
                "chasing_win_pct", "defending_win_pct",
            ]
            write_df = team_df[
                [c for c in cols if c in team_df.columns]
            ].copy()
            self.db.write_analytics_table(
                write_df, "team_performance", format_filter=format_filter
            )

        # Venue Stats
        venue_df = analytics["venue"]
        if not venue_df.empty:
            venue_df = self._resolve_venue_ids(venue_df, "venue_name")
            cols = [
                "venue_id", "format",
                "total_matches", "avg_first_innings_score",
                "avg_second_innings_score",
                "highest_total", "lowest_total",
                "chasing_win_pct", "defending_win_pct",
                "pace_wickets_pct", "spin_wickets_pct",
                "avg_powerplay_runs", "avg_middle_overs_runs",
                "avg_death_overs_runs", "boundary_frequency",
            ]
            write_df = venue_df[
                [c for c in cols if c in venue_df.columns]
            ].copy()
            self.db.write_analytics_table(
                write_df, "venue_stats", format_filter=format_filter
            )

        # Matchups
        matchups_df = analytics["matchups"]
        if not matchups_df.empty:
            matchups_df = self._resolve_player_ids(
                matchups_df, "batter_name", target_col="batter_id"
            )
            matchups_df = self._resolve_player_ids(
                matchups_df, "bowler_name", target_col="bowler_id"
            )
            cols = [
                "batter_id", "bowler_id", "format",
                "total_balls", "total_runs", "total_wickets",
                "strike_rate", "batting_average",
                "dot_balls", "boundaries", "sixes",
            ]
            write_df = matchups_df[
                [c for c in cols if c in matchups_df.columns]
            ].copy()
            self.db.write_analytics_table(
                write_df, "batter_bowler_matchups", format_filter=format_filter
            )

    def _resolve_player_ids(
        self, df: pd.DataFrame, name_col: str, target_col: str = "player_id"
    ) -> pd.DataFrame:
        """Resolve player names to UUIDs.
        
        Uses a multi-step resolution:
        1. Direct lookup in _player_ids cache (canonical name -> id)
        2. Fallback via _player_name_mappings (source name -> canonical -> id)
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
                logger.warning(f"  {remaining} rows still unresolved in {name_col} after alias lookup")
        return df

    def _resolve_team_ids(self, df: pd.DataFrame, name_col: str) -> pd.DataFrame:
        """Resolve team names to UUIDs."""
        df = df.copy()
        df["team_id"] = df[name_col].map(self.db._team_ids)
        return df

    def _resolve_venue_ids(self, df: pd.DataFrame, name_col: str) -> pd.DataFrame:
        """Resolve venue names to UUIDs."""
        df = df.copy()
        df["venue_id"] = df[name_col].map(self.db._venue_ids)
        return df

    def _print_batch_summary(self, stats: dict):
        """Print a human-readable batch summary."""
        print(f"\n{'-'*60}")
        print(f"Batch {stats['batch_id']}")
        print(f"{'-'*60}")
        print(f"Format:     {stats['format'].upper()}")
        print(f"Files:      {stats['file_count']}")
        print(f"Matches:    {stats['match_count']}")
        print(f"Innings:    {stats['innings_count']}")
        print(f"Deliveries: {stats['delivery_count']}")
        print(f"New players:    {stats['new_players']}")
        print(f"New teams:      {stats['new_teams']}")
        print(f"New venues:     {stats['new_venues']}")
        print(f"Status:     {stats['status']}")
        print(f"Duration:   {stats['duration_seconds']}s")
        print(f"{'-'*60}")
