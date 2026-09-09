"""Restore full ODI career analytics into the local SQLite serving database.

The repository retains all 52 completed ODI analytics checkpoints even when the
large source match corpus is not present locally.  This script merges those
checkpoints additively, resolves players by canonical name, and upserts the
derived career tables used by the API.
"""

from __future__ import annotations

import glob
import pickle
import sqlite3
import sys
import uuid
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline.pipeline.player_identity import PLAYER_ALIASES


DB_PATH = ROOT / "data" / "cricket_intelligence.db"
CHUNK_PATTERN = str(ROOT / "data" / "odi_analytics_chunks" / "chunk_*.pkl")

def _number(value, default=0):
    return default if pd.isna(value) else value


def _weighted(group: pd.DataFrame, value: str, weight: str) -> float | None:
    valid = group[value].notna() & group[weight].notna() & (group[weight] > 0)
    if not valid.any():
        return None
    weights = group.loc[valid, weight].astype(float)
    return float((group.loc[valid, value].astype(float) * weights).sum() / weights.sum())


def _load_chunks() -> dict[str, pd.DataFrame]:
    paths = sorted(glob.glob(CHUNK_PATTERN))
    if not paths:
        raise RuntimeError("No ODI analytics checkpoints were found")
    buckets: dict[str, list[pd.DataFrame]] = {
        key: [] for key in ("batting", "bowling", "form", "team", "venue", "matchups")
    }
    for path in paths:
        with open(path, "rb") as handle:
            chunk = pickle.load(handle)
        for key in buckets:
            if key in chunk and not chunk[key].empty:
                frame = chunk[key].copy()
                frame["_chunk"] = Path(path).stem
                buckets[key].append(frame)
    return {key: pd.concat(frames, ignore_index=True) for key, frames in buckets.items()}


def _player_ids(conn: sqlite3.Connection, names: set[str]) -> dict[str, str]:
    existing = {
        row[1].strip().casefold(): row[0]
        for row in conn.execute("SELECT id, canonical_name FROM players")
        if row[1]
    }
    result: dict[str, str] = {}
    for name in sorted(names):
        clean = str(name).strip()
        if not clean:
            continue
        canonical = PLAYER_ALIASES.get(clean, clean)
        key = canonical.casefold()
        player_id = existing.get(key)
        if player_id is None:
            player_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO players (id, canonical_name, full_name, role, is_active) VALUES (?, ?, ?, ?, 1)",
                (player_id, canonical, canonical, "unknown"),
            )
            existing[key] = player_id
        result[clean] = player_id
    return result


def _remove_stale_alias_stats(conn: sqlite3.Connection) -> None:
    """Remove ODI rows created against abbreviation-only duplicate identities."""
    for alias, canonical in PLAYER_ALIASES.items():
        alias_id = conn.execute(
            "SELECT id FROM players WHERE lower(canonical_name) = lower(?)", (alias,)
        ).fetchone()
        canonical_id = conn.execute(
            "SELECT id FROM players WHERE lower(canonical_name) = lower(?)", (canonical,)
        ).fetchone()
        if not alias_id or not canonical_id or alias_id[0] == canonical_id[0]:
            continue
        for table in ("player_batting_stats", "player_bowling_stats", "player_form"):
            conn.execute(f"DELETE FROM {table} WHERE player_id = ? AND format = 'ODI'", (alias_id[0],))
        conn.execute(
            "DELETE FROM batter_bowler_matchups WHERE format = 'ODI' AND (batter_id = ? OR bowler_id = ?)",
            (alias_id[0], alias_id[0]),
        )


def _restore_batting(conn: sqlite3.Connection, frame: pd.DataFrame, ids: dict[str, str]) -> int:
    invalid = frame["not_outs"].fillna(0).lt(0) | frame["not_outs"].fillna(0).gt(frame["innings"].fillna(0))
    if invalid.any():
        raise RuntimeError(
            "Legacy ODI checkpoints contain impossible not-out counts. "
            "Run scripts/repair_stat_invariants.py against the raw match archive instead."
        )
    additive = [
        "matches", "innings", "not_outs", "runs", "balls_faced", "fours", "sixes",
        "fifties", "hundreds", "powerplay_runs", "middle_runs", "death_runs",
        "chasing_runs", "first_innings_runs",
    ]
    count = 0
    for name, group in frame.groupby("player_name", sort=False):
        sums = {column: int(round(group[column].fillna(0).sum())) for column in additive}
        runs, balls = sums["runs"], sums["balls_faced"]
        dismissals = sums["innings"] - sums["not_outs"]
        high_columns = [c for c in ("highest_score_x", "highest_score_y", "highest_score") if c in group]
        high_values = pd.concat([group[c] for c in high_columns], ignore_index=True)
        # Checkpoints predate the scorecard-inflation repair; impossible ODI
        # innings totals (>264) are excluded from the career maximum.
        high_values = high_values[(high_values >= 0) & (high_values <= 264)]
        highest = high_values.max(skipna=True) if not high_values.empty else None
        highest = None if pd.isna(highest) else int(highest)
        values = (
            str(uuid.uuid4()), ids[str(name)], "ODI", "career",
            sums["matches"], sums["innings"], sums["not_outs"], runs, highest,
            round(runs / dismissals, 2) if dismissals > 0 else None,
            round(100 * runs / balls, 2) if balls > 0 else None,
            balls, sums["fours"], sums["sixes"],
            round(100 * (4 * sums["fours"] + 6 * sums["sixes"]) / runs, 2) if runs else None,
            round(100 * group["dot_balls"].fillna(0).sum() / balls, 2) if balls else None,
            sums["fifties"], sums["hundreds"],
            sums["powerplay_runs"], _weighted(group, "powerplay_strike_rate", "powerplay_runs"),
            sums["middle_runs"], _weighted(group, "middle_strike_rate", "middle_runs"),
            sums["death_runs"], _weighted(group, "death_strike_rate", "death_runs"),
            sums["chasing_runs"], _weighted(group, "chasing_strike_rate", "chasing_runs"),
            sums["first_innings_runs"], _weighted(group, "first_innings_strike_rate", "first_innings_runs"),
            _weighted(group, "consistency_score", "innings"),
        )
        conn.execute(
            """INSERT INTO player_batting_stats
               (id, player_id, format, period, matches, innings, not_outs, runs, highest_score,
                batting_average, strike_rate, balls_faced, fours, sixes, boundary_pct, dot_ball_pct,
                fifties, hundreds, powerplay_runs, powerplay_strike_rate, middle_runs,
                middle_strike_rate, death_runs, death_strike_rate, chasing_runs,
                chasing_strike_rate, first_innings_runs, first_innings_strike_rate, consistency_score)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(player_id, format, period) DO UPDATE SET
                matches=excluded.matches, innings=excluded.innings, not_outs=excluded.not_outs,
                runs=excluded.runs, highest_score=excluded.highest_score,
                batting_average=excluded.batting_average, strike_rate=excluded.strike_rate,
                balls_faced=excluded.balls_faced, fours=excluded.fours, sixes=excluded.sixes,
                boundary_pct=excluded.boundary_pct, dot_ball_pct=excluded.dot_ball_pct,
                fifties=excluded.fifties, hundreds=excluded.hundreds,
                powerplay_runs=excluded.powerplay_runs, powerplay_strike_rate=excluded.powerplay_strike_rate,
                middle_runs=excluded.middle_runs, middle_strike_rate=excluded.middle_strike_rate,
                death_runs=excluded.death_runs, death_strike_rate=excluded.death_strike_rate,
                chasing_runs=excluded.chasing_runs, chasing_strike_rate=excluded.chasing_strike_rate,
                first_innings_runs=excluded.first_innings_runs,
                first_innings_strike_rate=excluded.first_innings_strike_rate,
                consistency_score=excluded.consistency_score""",
            values,
        )
        count += 1
    return count


def _restore_bowling(conn: sqlite3.Connection, frame: pd.DataFrame, ids: dict[str, str]) -> int:
    additive = [
        "matches", "innings", "balls_bowled", "runs_conceded", "wickets",
        "dot_balls", "boundaries_conceded", "powerplay_overs", "powerplay_wickets",
        "middle_overs", "middle_wickets", "death_overs", "death_wickets",
    ]
    count = 0
    for name, group in frame.groupby("player_name", sort=False):
        sums = {column: float(group[column].fillna(0).sum()) for column in additive}
        balls, runs, wickets = int(sums["balls_bowled"]), int(sums["runs_conceded"]), int(sums["wickets"])
        values = (
            str(uuid.uuid4()), ids[str(name)], "ODI", "career", int(sums["matches"]),
            int(sums["innings"]), round(balls / 6, 1), balls, wickets, runs,
            round(runs / wickets, 2) if wickets else None,
            round(balls / wickets, 2) if wickets else None,
            round(6 * runs / balls, 2) if balls else None,
            round(100 * sums["dot_balls"] / balls, 2) if balls else None,
            round(100 * sums["boundaries_conceded"] / balls, 2) if balls else None,
            sums["powerplay_overs"], int(sums["powerplay_wickets"]),
            _weighted(group, "powerplay_economy", "powerplay_overs"),
            sums["middle_overs"], int(sums["middle_wickets"]),
            _weighted(group, "middle_economy", "middle_overs"),
            sums["death_overs"], int(sums["death_wickets"]),
            _weighted(group, "death_economy", "death_overs"),
        )
        conn.execute(
            """INSERT INTO player_bowling_stats
               (id, player_id, format, period, matches, innings, overs, balls_bowled, wickets,
                runs_conceded, bowling_average, strike_rate, economy, dot_ball_pct,
                boundary_conceded_pct, powerplay_overs, powerplay_wickets, powerplay_economy,
                middle_overs, middle_wickets, middle_economy, death_overs, death_wickets, death_economy)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(player_id, format, period) DO UPDATE SET
                matches=excluded.matches, innings=excluded.innings, overs=excluded.overs,
                balls_bowled=excluded.balls_bowled, wickets=excluded.wickets,
                runs_conceded=excluded.runs_conceded, bowling_average=excluded.bowling_average,
                strike_rate=excluded.strike_rate, economy=excluded.economy,
                dot_ball_pct=excluded.dot_ball_pct, boundary_conceded_pct=excluded.boundary_conceded_pct,
                powerplay_overs=excluded.powerplay_overs, powerplay_wickets=excluded.powerplay_wickets,
                powerplay_economy=excluded.powerplay_economy, middle_overs=excluded.middle_overs,
                middle_wickets=excluded.middle_wickets, middle_economy=excluded.middle_economy,
                death_overs=excluded.death_overs, death_wickets=excluded.death_wickets,
                death_economy=excluded.death_economy""",
            values,
        )
        count += 1
    return count


def _restore_form(conn: sqlite3.Connection, frame: pd.DataFrame, ids: dict[str, str]) -> int:
    latest = frame.sort_values("_chunk").drop_duplicates("player_name", keep="last")
    columns = [
        "form_score", "recent_performance_component", "consistency_component",
        "opposition_strength_component", "venue_performance_component",
        "match_situation_component", "efficiency_component", "recent_innings_count",
    ]
    for _, row in latest.iterrows():
        values = [None if pd.isna(row[c]) else float(row[c]) for c in columns]
        values[-1] = int(_number(row["recent_innings_count"]))
        conn.execute(
            """INSERT INTO player_form
               (id, player_id, format, form_score, recent_performance_component,
                consistency_component, opposition_strength_component, venue_performance_component,
                match_situation_component, efficiency_component, recent_innings_count)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(player_id, format) DO UPDATE SET
                form_score=excluded.form_score,
                recent_performance_component=excluded.recent_performance_component,
                consistency_component=excluded.consistency_component,
                opposition_strength_component=excluded.opposition_strength_component,
                venue_performance_component=excluded.venue_performance_component,
                match_situation_component=excluded.match_situation_component,
                efficiency_component=excluded.efficiency_component,
                recent_innings_count=excluded.recent_innings_count""",
            (str(uuid.uuid4()), ids[str(row["player_name"])], "ODI", *values),
        )
    return len(latest)


def _named_ids(conn: sqlite3.Connection, table: str, names: set[str]) -> dict[str, str]:
    existing = {
        row[1].strip().casefold(): row[0]
        for row in conn.execute(f"SELECT id, canonical_name FROM {table}")
        if row[1]
    }
    result: dict[str, str] = {}
    for name in sorted(names):
        clean = str(name).strip()
        if not clean:
            continue
        item_id = existing.get(clean.casefold())
        if item_id is None:
            item_id = str(uuid.uuid4())
            if table == "teams":
                words = [word for word in clean.replace("-", " ").split() if word]
                short_name = "".join(word[0] for word in words[:4]).upper() or clean[:4].upper()
                conn.execute(
                    "INSERT INTO teams (id, canonical_name, short_name, is_active) VALUES (?, ?, ?, 1)",
                    (item_id, clean, short_name),
                )
            else:
                conn.execute(
                    f"INSERT INTO {table} (id, canonical_name, is_active) VALUES (?, ?, 1)",
                    (item_id, clean),
                )
        result[clean] = item_id
    return result


def _restore_teams(conn: sqlite3.Connection, frame: pd.DataFrame) -> int:
    ids = _named_ids(conn, "teams", set(frame["team_name"].dropna().astype(str)))
    for name, group in frame.groupby("team_name", sort=False):
        matches = int(group["matches"].fillna(0).sum())
        wins = int(group["wins"].fillna(0).sum())
        losses = int(group["losses"].fillna(0).sum())
        weighted = lambda column: _weighted(group, column, "matches")
        values = (
            str(uuid.uuid4()), ids[str(name)], "ODI", "career", matches, wins, losses,
            round(100 * wins / matches, 2) if matches else None,
            weighted("avg_first_innings_score"), weighted("avg_second_innings_score"),
            weighted("avg_powerplay_score"), weighted("avg_middle_score"),
            weighted("avg_death_score"), weighted("avg_economy"),
            weighted("batting_strength_score"), weighted("bowling_strength_score"),
            weighted("overall_strength_score"), weighted("chasing_win_pct"),
            weighted("defending_win_pct"),
        )
        conn.execute(
            """INSERT INTO team_performance
               (id, team_id, format, period, matches, wins, losses, win_rate,
                avg_first_innings_score, avg_second_innings_score, avg_powerplay_score,
                avg_middle_overs_score, avg_death_overs_score, avg_economy,
                batting_strength_score, bowling_strength_score, overall_strength_score,
                chasing_win_pct, defending_win_pct)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(team_id, format, period) DO UPDATE SET
                matches=excluded.matches, wins=excluded.wins, losses=excluded.losses,
                win_rate=excluded.win_rate, avg_first_innings_score=excluded.avg_first_innings_score,
                avg_second_innings_score=excluded.avg_second_innings_score,
                avg_powerplay_score=excluded.avg_powerplay_score,
                avg_middle_overs_score=excluded.avg_middle_overs_score,
                avg_death_overs_score=excluded.avg_death_overs_score,
                avg_economy=excluded.avg_economy,
                batting_strength_score=excluded.batting_strength_score,
                bowling_strength_score=excluded.bowling_strength_score,
                overall_strength_score=excluded.overall_strength_score,
                chasing_win_pct=excluded.chasing_win_pct,
                defending_win_pct=excluded.defending_win_pct""",
            values,
        )
    return frame["team_name"].nunique()


def _restore_venues(conn: sqlite3.Connection, frame: pd.DataFrame) -> int:
    existing = {
        row[1].strip().casefold(): row[0]
        for row in conn.execute("SELECT id, name FROM venues") if row[1]
    }
    ids: dict[str, str] = {}
    for name in sorted(set(frame["venue_name"].dropna().astype(str))):
        clean = name.strip()
        venue_id = existing.get(clean.casefold())
        if venue_id is None:
            venue_id = str(uuid.uuid4())
            conn.execute("INSERT INTO venues (id, name) VALUES (?, ?)", (venue_id, clean))
        ids[name] = venue_id
    for name, group in frame.groupby("venue_name", sort=False):
        matches = int(group["total_matches"].fillna(0).sum())
        weighted = lambda column: _weighted(group, column, "total_matches")
        highest = group["highest_total"].dropna()
        highest = highest[highest <= 500]
        lowest = group["lowest_total"].dropna()
        values = (
            str(uuid.uuid4()), ids[str(name)], "ODI", matches,
            weighted("avg_first_innings_score"), weighted("avg_second_innings_score"),
            int(highest.max()) if not highest.empty else None,
            int(lowest.min()) if not lowest.empty else None,
            weighted("chasing_win_pct"), weighted("defending_win_pct"),
            weighted("pace_wickets_pct"), weighted("spin_wickets_pct"),
            weighted("avg_powerplay_runs"), weighted("avg_middle_overs_runs"),
            weighted("avg_death_overs_runs"),
            round(group["fours"].fillna(0).sum() / matches, 2) if matches else None,
            round(group["sixes"].fillna(0).sum() / matches, 2) if matches else None,
            weighted("boundary_frequency"),
        )
        conn.execute(
            """INSERT INTO venue_stats
               (id, venue_id, format, total_matches, avg_first_innings_score,
                avg_second_innings_score, highest_total, lowest_total, chasing_win_pct,
                defending_win_pct, pace_wickets_pct, spin_wickets_pct, avg_powerplay_runs,
                avg_middle_overs_runs, avg_death_overs_runs, avg_fours_per_match,
                avg_sixes_per_match, boundary_frequency)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(venue_id, format) DO UPDATE SET
                total_matches=excluded.total_matches,
                avg_first_innings_score=excluded.avg_first_innings_score,
                avg_second_innings_score=excluded.avg_second_innings_score,
                highest_total=excluded.highest_total, lowest_total=excluded.lowest_total,
                chasing_win_pct=excluded.chasing_win_pct,
                defending_win_pct=excluded.defending_win_pct,
                pace_wickets_pct=excluded.pace_wickets_pct,
                spin_wickets_pct=excluded.spin_wickets_pct,
                avg_powerplay_runs=excluded.avg_powerplay_runs,
                avg_middle_overs_runs=excluded.avg_middle_overs_runs,
                avg_death_overs_runs=excluded.avg_death_overs_runs,
                avg_fours_per_match=excluded.avg_fours_per_match,
                avg_sixes_per_match=excluded.avg_sixes_per_match,
                boundary_frequency=excluded.boundary_frequency""",
            values,
        )
    return frame["venue_name"].nunique()


def _restore_matchups(conn: sqlite3.Connection, frame: pd.DataFrame, ids: dict[str, str]) -> int:
    grouped = frame.groupby(["batter_name", "bowler_name"], as_index=False).agg(
        total_balls=("total_balls", "sum"), total_runs=("total_runs", "sum"),
        total_wickets=("total_wickets", "sum"), dot_balls=("dot_balls", "sum"),
        boundaries=("boundaries", "sum"), sixes=("sixes", "sum"),
    )
    count = 0
    for _, row in grouped.iterrows():
        batter, bowler = str(row["batter_name"]), str(row["bowler_name"])
        balls, runs, wickets = int(row["total_balls"]), int(row["total_runs"]), int(row["total_wickets"])
        conn.execute(
            """INSERT INTO batter_bowler_matchups
               (id, batter_id, bowler_id, format, total_balls, total_runs, total_wickets,
                strike_rate, batting_average, dot_balls, boundaries, sixes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(batter_id, bowler_id, format) DO UPDATE SET
                total_balls=excluded.total_balls, total_runs=excluded.total_runs,
                total_wickets=excluded.total_wickets, strike_rate=excluded.strike_rate,
                batting_average=excluded.batting_average, dot_balls=excluded.dot_balls,
                boundaries=excluded.boundaries, sixes=excluded.sixes""",
            (
                str(uuid.uuid4()), ids[batter], ids[bowler], "ODI", balls, runs, wickets,
                round(100 * runs / balls, 2) if balls else None,
                round(runs / wickets, 2) if wickets else None,
                int(row["dot_balls"]), int(row["boundaries"]), int(row["sixes"]),
            ),
        )
        count += 1
    return count


def main() -> None:
    chunks = _load_chunks()
    for key in ("batting", "bowling", "form"):
        chunks[key]["player_name"] = chunks[key]["player_name"].replace(PLAYER_ALIASES)
    chunks["matchups"]["batter_name"] = chunks["matchups"]["batter_name"].replace(PLAYER_ALIASES)
    chunks["matchups"]["bowler_name"] = chunks["matchups"]["bowler_name"].replace(PLAYER_ALIASES)
    names = set(chunks["batting"]["player_name"].dropna().astype(str))
    names.update(chunks["bowling"]["player_name"].dropna().astype(str))
    names.update(chunks["form"]["player_name"].dropna().astype(str))
    names.update(chunks["matchups"]["batter_name"].dropna().astype(str))
    names.update(chunks["matchups"]["bowler_name"].dropna().astype(str))
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        _remove_stale_alias_stats(conn)
        ids = _player_ids(conn, names)
        batting = _restore_batting(conn, chunks["batting"], ids)
        bowling = _restore_bowling(conn, chunks["bowling"], ids)
        form = _restore_form(conn, chunks["form"], ids)
        teams = _restore_teams(conn, chunks["team"])
        venues = _restore_venues(conn, chunks["venue"])
        matchups = _restore_matchups(conn, chunks["matchups"], ids)
        conn.commit()
    print(
        f"Restored ODI analytics: {batting} batters, {bowling} bowlers, "
        f"{form} form rows, {teams} teams, {venues} venues, {matchups} matchups"
    )


if __name__ == "__main__":
    main()
