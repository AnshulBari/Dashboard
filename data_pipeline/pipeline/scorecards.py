"""
Deterministic Scorecard Generator (JSON-based)
===============================================

Generates match_batting_summary and match_bowling_summary directly from
Cricsheet JSON files. Does NOT depend on the deliveries table.

Design principles:
- Cricsheet JSON is the authoritative source
- Each match is processed exactly once per invocation
- Same input always produces same output (deterministic)
- Running twice does NOT double values (atomic match-level replacement)
- Failed matches do not destroy existing valid data (transaction rollback)
- Scorecards are independently verifiable against source JSON

Usage:
    from data_pipeline.pipeline.scorecards import ScorecardGenerator
    gen = ScorecardGenerator(engine)
    gen.generate_from_directory("data/raw/ipl", format_type="T20")
    gen.generate_from_json_file(Path("data/raw/odi/12345.json"), format_type="ODI")
"""

import json
import logging
import os
import uuid
import zipfile
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

NON_BOWLER_DISMISSALS = {
    "run out",
    "retired hurt",
    "retired out",
    "retired not out",
    "obstructing the field",
    "hit the ball twice",
    "handled the ball",
    "timed out",
}


def compute_innings_totals(data: dict) -> list[dict]:
    """Derive authoritative innings totals and cricket over notation."""
    info = data.get("info", {})
    balls_per_over = int(info.get("balls_per_over", 6) or 6)
    players = info.get("players", {})
    totals = []
    for innings_number, innings in enumerate(data.get("innings", []), 1):
        total_runs = 0
        total_wickets = 0
        legal_balls = 0
        for over in innings.get("overs", []):
            for delivery in over.get("deliveries", []):
                total_runs += int(delivery.get("runs", {}).get("total", 0) or 0)
                extras = delivery.get("extras", {})
                legal_balls += int("wides" not in extras and "noballs" not in extras)
                total_wickets += sum(
                    1 for wicket in delivery.get("wickets", [])
                    if _wicket_kind(wicket) not in {"retired hurt", "retired not out"}
                )
        team = innings.get("team", "")
        player_count = len(players.get(team, [])) or 11
        declared = bool(innings.get("declared", False))
        totals.append({
            "innings_number": innings_number,
            "total_runs": total_runs,
            "total_wickets": total_wickets,
            "total_overs": round(
                legal_balls // balls_per_over
                + (legal_balls % balls_per_over) / 10.0,
                1,
            ),
            "declared": declared,
            "all_out": not declared and total_wickets >= max(player_count - 1, 1),
            "follow_on": bool(innings.get("follow_on", False)),
        })
    return totals


def _wicket_kind(wicket: dict) -> str:
    return str(wicket.get("kind", "")).replace("_", " ").strip().lower()


def compute_scorecard_from_json(data: dict) -> tuple[dict, dict]:
    """
    Compute batting and bowling scorecards from a single Cricsheet JSON.

    This is the single source of truth for scorecard calculation.
    It processes each delivery exactly once.

    Returns:
        (batting_rows, bowling_rows) where each key is (innings_idx, player_name)
        and values are dicts with aggregated statistics.
    """
    batting_rows = {}  # key: (innings_idx, player_name) -> stats
    bowling_rows = {}  # key: (innings_idx, bowler_name) -> stats
    balls_per_over = int(data.get("info", {}).get("balls_per_over", 6) or 6)

    for innings_idx, innings in enumerate(data.get("innings", [])):
        for over_data in innings.get("overs", []):
            over_bowling = {}
            for ball_idx, delivery in enumerate(over_data.get("deliveries", [])):
                batter = delivery.get("batter", "")
                non_striker = delivery.get("non_striker", "")
                bowler = delivery.get("bowler", "")
                runs = delivery.get("runs", {})
                batter_runs = runs.get("batter", 0)
                non_boundary = bool(runs.get("non_boundary", False))
                extras = delivery.get("extras", {})
                wickets = delivery.get("wickets", [])
                is_wide = "wides" in extras
                is_noball = "noballs" in extras
                bowler_runs = (
                    batter_runs
                    + int(extras.get("wides", 0) or 0)
                    + int(extras.get("noballs", 0) or 0)
                )

                # Register both players at the crease. A non-striker can finish
                # not out without facing a ball and must still appear in the
                # scorecard (for example Mohammed Siraj at Perth in 2024).
                for player_at_crease in (batter, non_striker):
                    key = (innings_idx, player_at_crease)
                    if player_at_crease and key not in batting_rows:
                        batting_rows[key] = {
                            "runs": 0,
                            "balls": 0,
                            "fours": 0,
                            "sixes": 0,
                            "is_not_out": True,
                            "dismissal_type": None,
                            "dismissal_bowler": None,
                            "fielder": None,
                        }
                # Batting aggregation
                if batter:
                    key = (innings_idx, batter)
                    agg = batting_rows[key]
                    agg["runs"] += batter_runs
                    if not is_wide:
                        agg["balls"] += 1
                    if batter_runs == 4 and not non_boundary:
                        agg["fours"] += 1
                    if batter_runs == 6 and not non_boundary:
                        agg["sixes"] += 1

                # A wicket can dismiss the non-striker (most commonly a run
                # out). Attribute the dismissal to ``player_out`` rather than
                # assuming that the batter facing the delivery was dismissed.
                # Create a zero-ball row when a non-striker is out before ever
                # facing, because that still counts as a batting innings.
                for wicket_info in wickets:
                    player_out = wicket_info.get("player_out", "")
                    kind = _wicket_kind(wicket_info)
                    if not player_out or kind in {"retired hurt", "retired not out"}:
                        continue
                    out_key = (innings_idx, player_out)
                    if out_key not in batting_rows:
                        batting_rows[out_key] = {
                            "runs": 0,
                            "balls": 0,
                            "fours": 0,
                            "sixes": 0,
                            "is_not_out": True,
                            "dismissal_type": None,
                            "dismissal_bowler": None,
                            "fielder": None,
                        }
                    out = batting_rows[out_key]
                    out["is_not_out"] = False
                    out["dismissal_type"] = wicket_info.get("kind", "")
                    if kind not in NON_BOWLER_DISMISSALS:
                        out["dismissal_bowler"] = bowler or None
                    fielders = wicket_info.get("fielders", [])
                    if fielders:
                        first_fielder = fielders[0]
                        out["fielder"] = (
                            first_fielder.get("name")
                            if isinstance(first_fielder, dict)
                            else str(first_fielder)
                        )

                # Bowling aggregation
                if bowler:
                    key = (innings_idx, bowler)
                    if key not in bowling_rows:
                        bowling_rows[key] = {
                            "balls": 0,
                            "runs": 0,
                            "wickets": 0,
                            "maidens": 0,
                            "wides": 0,
                            "noballs": 0,
                        }
                    agg = bowling_rows[key]
                    if not is_wide and not is_noball:
                        agg["balls"] += 1
                    agg["runs"] += bowler_runs
                    agg["wickets"] += sum(
                        1 for wicket_info in wickets
                        if _wicket_kind(wicket_info) not in NON_BOWLER_DISMISSALS
                    )
                    agg["wides"] += int(extras.get("wides", 0) or 0)
                    agg["noballs"] += int(extras.get("noballs", 0) or 0)

                    over_state = over_bowling.setdefault(
                        bowler, {"legal_balls": 0, "bowler_runs": 0}
                    )
                    over_state["legal_balls"] += int(not is_wide and not is_noball)
                    over_state["bowler_runs"] += bowler_runs

            for bowler, over_state in over_bowling.items():
                if (
                    over_state["legal_balls"] >= balls_per_over
                    and over_state["bowler_runs"] == 0
                ):
                    bowling_rows[(innings_idx, bowler)]["maidens"] += 1

    return batting_rows, bowling_rows


def validate_scorecard(
    batting_rows: dict,
    bowling_rows: dict,
    match_id: str,
) -> list[str]:
    """
    Validate a computed scorecard for correctness.

    Returns a list of warning/error messages. Empty list = valid.
    """
    issues = []

    # Batting validation
    for (innings_idx, player), stats in batting_rows.items():
        if stats["runs"] < 0:
            issues.append(
                f"Match {match_id} innings {innings_idx}: "
                f"player {player} has negative runs ({stats['runs']})"
            )
        if stats["balls"] < 0:
            issues.append(
                f"Match {match_id} innings {innings_idx}: "
                f"player {player} has negative balls ({stats['balls']})"
            )
        if stats["fours"] < 0 or stats["sixes"] < 0:
            issues.append(
                f"Match {match_id} innings {innings_idx}: "
                f"player {player} has negative boundaries"
            )
        if stats["balls"] > 0:
            expected_sr = stats["runs"] / stats["balls"] * 100
            if expected_sr > 400:  # extreme but possible
                issues.append(
                    f"Match {match_id} innings {innings_idx}: "
                    f"player {player} has very high SR ({expected_sr:.1f})"
                )

    # Bowling validation
    for (innings_idx, bowler), stats in bowling_rows.items():
        if stats["runs"] < 0:
            issues.append(
                f"Match {match_id} innings {innings_idx}: "
                f"bowler {bowler} has negative runs conceded ({stats['runs']})"
            )
        if stats["wickets"] < 0:
            issues.append(
                f"Match {match_id} innings {innings_idx}: "
                f"bowler {bowler} has negative wickets ({stats['wickets']})"
            )
        if stats["balls"] < 0:
            issues.append(
                f"Match {match_id} innings {innings_idx}: "
                f"bowler {bowler} has negative balls ({stats['balls']})"
            )

    # Cross-check: batting innings totals vs bowling totals
    innings_bat_totals = {}
    for (innings_idx, _), stats in batting_rows.items():
        if innings_idx not in innings_bat_totals:
            innings_bat_totals[innings_idx] = 0
        innings_bat_totals[innings_idx] += stats["runs"]

    innings_bowl_totals = {}
    for (innings_idx, _), stats in bowling_rows.items():
        if innings_idx not in innings_bowl_totals:
            innings_bowl_totals[innings_idx] = 0
        innings_bowl_totals[innings_idx] += stats["runs"]

    for innings_idx in innings_bat_totals:
        bat_total = innings_bat_totals.get(innings_idx, 0)
        bowl_total = innings_bowl_totals.get(innings_idx, 0)
        # Bowling total should equal batting total + extras
        # Since extras aren't attributed to batters, bowl_total >= bat_total
        if bowl_total < bat_total:
            issues.append(
                f"Match {match_id} innings {innings_idx}: "
                f"bowling total ({bowl_total}) < batting total ({bat_total})"
            )

    return issues


class ScorecardGenerator:
    """
    Generates scorecard summary tables directly from Cricsheet JSON.

    Does NOT depend on the deliveries table.
    Each match is processed exactly once per invocation.
    Uses atomic match-level replacement (delete + insert per match).
    """

    def __init__(self, engine: Engine):
        self.engine = engine
        self._player_ids = {}  # canonical_name -> id
        self._team_ids = {}  # canonical_name -> id
        self._innings_cache = {}  # (match_db_id, innings_number) -> innings_id
        self._innings_team_cache = {}  # innings_id -> (batting_team_id, bowling_team_id)
        self._match_ext_to_db = {}  # external_id -> db_id
        self._load_caches()

    def _load_caches(self):
        """Load existing entity IDs from database."""
        with self.engine.connect() as conn:
            # Players
            try:
                rows = conn.execute(
                    text("SELECT id, canonical_name FROM players")
                ).fetchall()
                self._player_ids = {r[1]: str(r[0]) for r in rows}
                # Scorecard JSON commonly uses initials while the application
                # exposes merged full-name identities. Include every recorded
                # source alias so those players are not silently omitted.
                aliases = conn.execute(
                    text("SELECT name_variant, player_id FROM player_name_mappings")
                ).fetchall()
                self._player_ids.update(
                    {r[0]: str(r[1]) for r in aliases if r[0] and r[1]}
                )
            except Exception:
                pass

            # Teams
            try:
                rows = conn.execute(
                    text("SELECT id, canonical_name FROM teams")
                ).fetchall()
                self._team_ids = {r[1]: str(r[0]) for r in rows}
            except Exception:
                pass

            # Matches (external_id -> db_id)
            try:
                rows = conn.execute(
                    text("SELECT id, external_id FROM matches")
                ).fetchall()
                self._match_ext_to_db = {
                    r[1]: str(r[0]) for r in rows if r[1]
                }
            except Exception:
                pass

            # Innings identifiers and participating teams. Keeping all three
            # values in memory avoids opening nested connections while a
            # match-level scorecard replacement transaction is active.
            try:
                rows = conn.execute(
                    text(
                        "SELECT i.id, m.external_id, i.innings_number, "
                        "i.batting_team_id, i.bowling_team_id "
                        "FROM innings i JOIN matches m ON i.match_id = m.id"
                    )
                ).fetchall()
                for r in rows:
                    innings_id = str(r[0])
                    self._innings_cache[(r[1], r[2])] = innings_id
                    self._innings_team_cache[innings_id] = (
                        str(r[3]) if r[3] else None,
                        str(r[4]) if r[4] else None,
                    )
            except Exception:
                pass

        logger.info(
            f"ScorecardGenerator: loaded {len(self._player_ids)} players, "
            f"{len(self._team_ids)} teams, {len(self._match_ext_to_db)} matches"
        )

    def _resolve_player_id(self, name: str) -> Optional[str]:
        """Resolve a player name to its database UUID."""
        return self._player_ids.get(name)

    def _get_match_db_id(self, external_id: str) -> Optional[str]:
        """Get database UUID for a match external_id."""
        return self._match_ext_to_db.get(external_id)

    def _get_innings_id(
        self, match_external_id: str, innings_number: int
    ) -> Optional[str]:
        """Get innings database UUID."""
        return self._innings_cache.get((match_external_id, innings_number))

    def _get_batting_team_id(
        self, innings_id: str
    ) -> Optional[str]:
        """Get batting_team_id for an innings."""
        teams = self._innings_team_cache.get(str(innings_id))
        return teams[0] if teams else None

    def _get_bowling_team_id(
        self, innings_id: str
    ) -> Optional[str]:
        """Get bowling_team_id for an innings."""
        teams = self._innings_team_cache.get(str(innings_id))
        return teams[1] if teams else None

    def generate_from_json_data(
        self,
        data: dict,
        match_external_id: Optional[str] = None,
        format_type: str = "",
    ) -> dict:
        """
        Generate scorecards for a single match from its Cricsheet JSON data.

        This is the core deterministic function. Same input always produces
        the same output.

        Uses atomic match-level replacement: delete existing rows for this
        match, then insert newly computed rows in a single transaction.

        Returns:
            dict with generation statistics
        """
        ext_id = match_external_id or data.get("match_id", "")
        stats = {
            "match_id": ext_id,
            "batting_rows": 0,
            "bowling_rows": 0,
            "status": "PENDING",
            "issues": [],
        }

        # Compute scorecards from JSON (deterministic)
        batting_rows, bowling_rows = compute_scorecard_from_json(data)
        innings_totals = compute_innings_totals(data)

        # Validate
        issues = validate_scorecard(batting_rows, bowling_rows, ext_id)
        stats["issues"] = issues

        # Get match DB ID
        match_db_id = self._get_match_db_id(ext_id)
        if not match_db_id:
            stats["status"] = "SKIPPED"
            stats["issues"].append(f"Match {ext_id} not found in database")
            return stats

        try:
            # Replacement and insertion share one transaction. A failed insert
            # therefore rolls back the deletes and preserves the prior valid
            # scorecard, as promised by the generator contract.
            with self.engine.begin() as conn:
                for innings_total in innings_totals:
                    innings_id = self._get_innings_id(
                        ext_id, innings_total["innings_number"]
                    )
                    if innings_id:
                        conn.execute(
                            text(
                                "UPDATE innings SET total_runs = :total_runs, "
                                "total_wickets = :total_wickets, total_overs = :total_overs, "
                                "declared = :declared, all_out = :all_out, "
                                "follow_on = :follow_on WHERE id = :innings_id"
                            ),
                            {**innings_total, "innings_id": innings_id},
                        )

                # Delete existing scorecard rows for this match first
                conn.execute(
                    text(
                        "DELETE FROM match_batting_summary "
                        "WHERE match_id = :match_id"
                    ),
                    {"match_id": match_db_id},
                )
                conn.execute(
                    text(
                        "DELETE FROM match_bowling_summary "
                        "WHERE match_id = :match_id"
                    ),
                    {"match_id": match_db_id},
                )

                # Insert batting summaries (ON CONFLICT for idempotency)
                bat_inserted = 0
                batting_positions: dict[int, int] = {}
                for (innings_idx, player_name), row_stats in batting_rows.items():
                    innings_number = innings_idx + 1
                    batting_positions[innings_idx] = batting_positions.get(innings_idx, 0) + 1
                    batting_position = batting_positions[innings_idx]
                    innings_id = self._get_innings_id(ext_id, innings_number)
                    if not innings_id:
                        continue

                    player_id = self._resolve_player_id(player_name)
                    if not player_id:
                        continue

                    batting_team_id = self._get_batting_team_id(innings_id)
                    if not batting_team_id:
                        continue

                    sr = (
                        (row_stats["runs"] / row_stats["balls"] * 100)
                        if row_stats["balls"] > 0
                        else 0
                    )

                    conn.execute(
                        text(
                            "INSERT INTO match_batting_summary "
                            "(id, match_id, innings_id, player_id, batting_team_id, "
                            "runs, balls, fours, sixes, strike_rate, is_not_out, "
                            "dismissal_type, bowler_id, fielder_id, batting_position) "
                            "VALUES "
                            "(:id, :match_id, :innings_id, :player_id, :batting_team_id, "
                            ":runs, :balls, :fours, :sixes, :strike_rate, :is_not_out, "
                            ":dismissal_type, :bowler_id, :fielder_id, :batting_position) "
                            "ON CONFLICT (match_id, innings_id, player_id) DO UPDATE SET "
                            "batting_team_id = EXCLUDED.batting_team_id, "
                            "runs = EXCLUDED.runs, "
                            "balls = EXCLUDED.balls, "
                            "fours = EXCLUDED.fours, "
                            "sixes = EXCLUDED.sixes, "
                            "strike_rate = EXCLUDED.strike_rate, "
                            "is_not_out = EXCLUDED.is_not_out, "
                            "dismissal_type = EXCLUDED.dismissal_type, "
                            "bowler_id = EXCLUDED.bowler_id, "
                            "fielder_id = EXCLUDED.fielder_id, "
                            "batting_position = EXCLUDED.batting_position"
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "match_id": match_db_id,
                            "innings_id": innings_id,
                            "player_id": player_id,
                            "batting_team_id": batting_team_id,
                            "runs": row_stats["runs"],
                            "balls": row_stats["balls"],
                            "fours": row_stats["fours"],
                            "sixes": row_stats["sixes"],
                            "strike_rate": round(sr, 2),
                            "is_not_out": row_stats["is_not_out"],
                            "dismissal_type": row_stats["dismissal_type"],
                            "bowler_id": self._resolve_player_id(
                                row_stats.get("dismissal_bowler")
                            ),
                            "fielder_id": self._resolve_player_id(
                                row_stats.get("fielder")
                            ),
                            "batting_position": batting_position,
                        },
                    )
                    bat_inserted += 1

                # Insert bowling summaries (ON CONFLICT for idempotency)
                bowl_inserted = 0
                bowling_positions: dict[int, int] = {}
                for (innings_idx, bowler_name), row_stats in bowling_rows.items():
                    innings_number = innings_idx + 1
                    bowling_positions[innings_idx] = bowling_positions.get(innings_idx, 0) + 1
                    bowling_position = bowling_positions[innings_idx]
                    innings_id = self._get_innings_id(ext_id, innings_number)
                    if not innings_id:
                        continue

                    player_id = self._resolve_player_id(bowler_name)
                    if not player_id:
                        continue

                    bowling_team_id = self._get_bowling_team_id(innings_id)
                    if not bowling_team_id:
                        continue

                    overs = row_stats["balls"] // 6 + (
                        row_stats["balls"] % 6
                    ) / 10.0
                    econ = (
                        row_stats["runs"] * 6.0 / row_stats["balls"]
                        if row_stats["balls"] > 0
                        else 0
                    )

                    conn.execute(
                        text(
                            "INSERT INTO match_bowling_summary "
                            "(id, match_id, innings_id, player_id, bowling_team_id, "
                            "overs, balls_bowled, maidens, runs_conceded, wickets, "
                            "economy, wides, noballs, bowling_position) "
                            "VALUES "
                            "(:id, :match_id, :innings_id, :player_id, :bowling_team_id, "
                            ":overs, :balls_bowled, :maidens, :runs_conceded, :wickets, "
                            ":economy, :wides, :noballs, :bowling_position) "
                            "ON CONFLICT (match_id, innings_id, player_id) DO UPDATE SET "
                            "bowling_team_id = EXCLUDED.bowling_team_id, "
                            "overs = EXCLUDED.overs, "
                            "balls_bowled = EXCLUDED.balls_bowled, "
                            "runs_conceded = EXCLUDED.runs_conceded, "
                            "wickets = EXCLUDED.wickets, "
                            "maidens = EXCLUDED.maidens, "
                            "economy = EXCLUDED.economy, "
                            "wides = EXCLUDED.wides, "
                            "noballs = EXCLUDED.noballs, "
                            "bowling_position = EXCLUDED.bowling_position"
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "match_id": match_db_id,
                            "innings_id": innings_id,
                            "player_id": player_id,
                            "bowling_team_id": bowling_team_id,
                            "overs": round(overs, 1),
                            "balls_bowled": row_stats["balls"],
                            "maidens": row_stats["maidens"],
                            "runs_conceded": row_stats["runs"],
                            "wickets": row_stats["wickets"],
                            "economy": round(econ, 2),
                            "wides": row_stats["wides"],
                            "noballs": row_stats["noballs"],
                            "bowling_position": bowling_position,
                        },
                    )
                    bowl_inserted += 1

            stats["batting_rows"] = bat_inserted
            stats["bowling_rows"] = bowl_inserted
            stats["status"] = "COMPLETED"

        except Exception as e:
            stats["status"] = "FAILED"
            stats["issues"].append(f"Database error: {e}")
            logger.error(
                f"Scorecard generation failed for {ext_id}: {e}", exc_info=True
            )

        return stats

    def generate_from_json_file(
        self,
        json_path: Path,
        format_type: str = "",
    ) -> dict:
        """
        Generate scorecards from a single Cricsheet JSON file.
        """
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return {
                "match_id": json_path.stem,
                "status": "ERROR",
                "issues": [f"Could not read {json_path}: {e}"],
            }

        ext_id = data.get("match_id") or json_path.stem
        return self.generate_from_json_data(
            data, match_external_id=ext_id, format_type=format_type
        )

    def generate_from_directory(
        self,
        directory: str | Path,
        format_type: str = "",
        file_glob: str = "*.json",
    ) -> dict:
        """
        Generate scorecards for all JSON files in a directory.

        Processes each file exactly once. Idempotent: running twice
        produces identical database state.

        Returns:
            dict with aggregate statistics
        """
        directory = Path(directory)
        if not directory.exists():
            return {"status": "ERROR", "issues": [f"Directory not found: {directory}"]}

        json_files = sorted(directory.glob(file_glob))
        if not json_files:
            return {"status": "ERROR", "issues": [f"No JSON files in {directory}"]}

        aggregate = {
            "total_files": len(json_files),
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "total_batting_rows": 0,
            "total_bowling_rows": 0,
            "all_issues": [],
        }

        for i, json_path in enumerate(json_files):
            result = self.generate_from_json_file(json_path, format_type)
            status = result.get("status", "UNKNOWN")

            if status == "COMPLETED":
                aggregate["processed"] += 1
                aggregate["total_batting_rows"] += result.get("batting_rows", 0)
                aggregate["total_bowling_rows"] += result.get("bowling_rows", 0)
            elif status == "SKIPPED":
                aggregate["skipped"] += 1
            else:
                aggregate["failed"] += 1

            if result.get("issues"):
                aggregate["all_issues"].extend(result["issues"])

            if (i + 1) % 500 == 0:
                logger.info(
                    f"  Scorecard progress: {i + 1}/{len(json_files)} files"
                )

        aggregate["status"] = "COMPLETED"
        return aggregate

    def generate_from_zip(
        self,
        zip_path: str | Path,
        format_type: str = "",
        gender: str = "male",
    ) -> dict:
        """
        Generate scorecards directly from a Cricsheet ZIP file.

        Reads JSON files from the ZIP without extracting to disk.
        Applies gender filter.
        """
        zip_path = Path(zip_path)
        if not zip_path.exists():
            return {"status": "ERROR", "issues": [f"ZIP not found: {zip_path}"]}

        aggregate = {
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "filtered": 0,
            "failed": 0,
            "total_batting_rows": 0,
            "total_bowling_rows": 0,
            "all_issues": [],
        }

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                json_files = [f for f in zf.namelist() if f.endswith(".json")]
                aggregate["total_files"] = len(json_files)

                for i, fname in enumerate(json_files):
                    try:
                        data = json.loads(zf.read(fname))

                        # Gender filter
                        info = data.get("info", {})
                        file_gender = info.get("gender", "")
                        if gender != "all" and file_gender != gender:
                            aggregate["filtered"] += 1
                            continue

                        # Get match ID from filename
                        match_id = Path(fname).stem
                        data["match_id"] = match_id

                        result = self.generate_from_json_data(
                            data,
                            match_external_id=match_id,
                            format_type=format_type,
                        )
                        status = result.get("status", "UNKNOWN")

                        if status == "COMPLETED":
                            aggregate["processed"] += 1
                            aggregate["total_batting_rows"] += result.get(
                                "batting_rows", 0
                            )
                            aggregate["total_bowling_rows"] += result.get(
                                "bowling_rows", 0
                            )
                        elif status == "SKIPPED":
                            aggregate["skipped"] += 1
                        else:
                            aggregate["failed"] += 1

                        if result.get("issues"):
                            aggregate["all_issues"].extend(result["issues"])

                    except Exception as e:
                        aggregate["failed"] += 1
                        aggregate["all_issues"].append(f"{fname}: {e}")

                    if (i + 1) % 500 == 0:
                        logger.info(
                            f"  ZIP scorecard progress: {i + 1}/{len(json_files)}"
                        )

        except Exception as e:
            aggregate["status"] = "ERROR"
            aggregate["all_issues"].append(f"ZIP error: {e}")
            return aggregate

        aggregate["status"] = "COMPLETED"
        return aggregate

    def verify_idempotency(
        self,
        json_path: Path,
    ) -> dict:
        """
        Verify that processing the same match twice produces identical results.

        Returns:
            dict with verification results
        """
        # First pass
        result1 = self.generate_from_json_file(json_path)

        # Second pass
        result2 = self.generate_from_json_file(json_path)

        # Compare database state
        ext_id = json_path.stem
        match_db_id = self._get_match_db_id(ext_id)

        if not match_db_id:
            return {"match_id": ext_id, "idempotent": False, "reason": "Match not in DB"}

        with self.engine.connect() as conn:
            # Count batting rows
            bat1 = conn.execute(
                text(
                    "SELECT COUNT(*) FROM match_batting_summary "
                    "WHERE match_id = :mid"
                ),
                {"mid": match_db_id},
            ).scalar()

            # Sum batting runs
            bat_runs1 = conn.execute(
                text(
                    "SELECT COALESCE(SUM(runs), 0) FROM match_batting_summary "
                    "WHERE match_id = :mid"
                ),
                {"mid": match_db_id},
            ).scalar()

            # Count bowling rows
            bowl1 = conn.execute(
                text(
                    "SELECT COUNT(*) FROM match_bowling_summary "
                    "WHERE match_id = :mid"
                ),
                {"mid": match_db_id},
            ).scalar()

            # Sum bowling wickets
            bowl_wkts1 = conn.execute(
                text(
                    "SELECT COALESCE(SUM(wickets), 0) "
                    "FROM match_bowling_summary WHERE match_id = :mid"
                ),
                {"mid": match_db_id},
            ).scalar()

        # Run third pass
        result3 = self.generate_from_json_file(json_path)

        with self.engine.connect() as conn:
            bat2 = conn.execute(
                text(
                    "SELECT COUNT(*) FROM match_batting_summary "
                    "WHERE match_id = :mid"
                ),
                {"mid": match_db_id},
            ).scalar()
            bat_runs2 = conn.execute(
                text(
                    "SELECT COALESCE(SUM(runs), 0) FROM match_batting_summary "
                    "WHERE match_id = :mid"
                ),
                {"mid": match_db_id},
            ).scalar()
            bowl2 = conn.execute(
                text(
                    "SELECT COUNT(*) FROM match_bowling_summary "
                    "WHERE match_id = :mid"
                ),
                {"mid": match_db_id},
            ).scalar()
            bowl_wkts2 = conn.execute(
                text(
                    "SELECT COALESCE(SUM(wickets), 0) "
                    "FROM match_bowling_summary WHERE match_id = :mid"
                ),
                {"mid": match_db_id},
            ).scalar()

        is_idempotent = (
            bat1 == bat2
            and bat_runs1 == bat_runs2
            and bowl1 == bowl2
            and bowl_wkts1 == bowl_wkts2
        )

        return {
            "match_id": ext_id,
            "idempotent": is_idempotent,
            "run1": {
                "batting_rows": bat1,
                "batting_runs": bat_runs1,
                "bowling_rows": bowl1,
                "bowling_wickets": bowl_wkts1,
            },
            "run2": {
                "batting_rows": bat2,
                "batting_runs": bat_runs2,
                "bowling_rows": bowl2,
                "bowling_wickets": bowl_wkts2,
            },
        }

    def detect_duplicate_sources(
        self,
        directory: str | Path,
    ) -> list[str]:
        """
        Detect duplicate match IDs across source files.

        Returns list of duplicate match IDs.
        """
        directory = Path(directory)
        seen_ids = {}
        duplicates = []

        for json_path in sorted(directory.glob("*.json")):
            match_id = json_path.stem
            if match_id in seen_ids:
                duplicates.append(match_id)
            else:
                seen_ids[match_id] = json_path

        return duplicates
