"""Atomically synchronize corrected serving aggregates to PostgreSQL.

The local SQLite database is the rebuildable serving snapshot. This command
copies derived analytics, fills missing competition/season catalog rows, links
matches to those editions by stable external ID, and removes known reconstructed
fixtures. Entity identities and compact official match scorecards are preserved.
No ball-by-ball delivery data is uploaded.

The command is read-only unless ``--apply`` is supplied.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import execute_values

from purge_reconstructed_matches import RECONSTRUCTED_IDS


ROOT = Path(__file__).resolve().parents[1]
SQLITE_PATH = ROOT / "data" / "cricket_intelligence.db"
TABLES = (
    "match_batting_summary",
    "match_bowling_summary",
    "player_batting_stats",
    "player_bowling_stats",
    "batter_bowler_matchups",
    "player_recent_stats",
    "season_player_stats",
    "player_form",
    "team_performance",
    "venue_stats",
)


def _local_table(conn: sqlite3.Connection, table: str):
    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    return columns, rows


def _remote_columns(cursor, table: str) -> set[str]:
    cursor.execute(
        """SELECT column_name FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = %s""",
        (table,),
    )
    return {row[0] for row in cursor.fetchall()}


def _identity_key(values) -> tuple[str, ...]:
    return tuple(" ".join(str(value or "").strip().casefold().split()) for value in values)


def _entity_id_map(
    cursor, local: sqlite3.Connection, table: str, identity_columns: tuple[str, ...]
) -> tuple[dict[str, str], int, int]:
    column_sql = ", ".join(identity_columns)
    local_rows = local.execute(f"SELECT id, {column_sql} FROM {table}").fetchall()
    remote_query = sql.SQL("SELECT id::text, {} FROM {}").format(
        sql.SQL(", ").join(map(sql.Identifier, identity_columns)),
        sql.Identifier(table),
    )
    cursor.execute(remote_query)
    remote_rows = cursor.fetchall()
    remote_ids = {str(row[0]) for row in remote_rows}
    remote_by_key = {_identity_key(row[1:]): str(row[0]) for row in remote_rows}
    mapping = {}
    for row in local_rows:
        local_id = str(row[0])
        # Stable shared UUIDs are the strongest identity signal. Fall back to
        # canonical entity fields only for databases produced by different
        # identity-merge runs.
        if local_id in remote_ids:
            mapping[local_id] = local_id
        elif _identity_key(row[1:]) in remote_by_key:
            mapping[local_id] = remote_by_key[_identity_key(row[1:])]
    return mapping, len(local_rows), len(remote_rows)


def _player_id_map(cursor, local: sqlite3.Connection):
    local_rows = local.execute(
        "SELECT id, canonical_name, full_name FROM players"
    ).fetchall()
    cursor.execute("SELECT id::text, canonical_name, full_name FROM players")
    remote_rows = cursor.fetchall()
    remote_ids = {str(row[0]) for row in remote_rows}

    local_names: dict[str, set[str]] = {
        str(row[0]): {
            _identity_key((value,))[0] for value in row[1:] if value
        }
        for row in local_rows
    }
    for player_id, variant in local.execute(
        "SELECT player_id, name_variant FROM player_name_mappings"
    ):
        if player_id in local_names and variant:
            local_names[player_id].add(_identity_key((variant,))[0])

    remote_canonical: dict[str, set[str]] = {}
    remote_names: dict[str, set[str]] = {}
    remote_aliases: dict[str, set[str]] = {}
    remote_labels = {}
    for player_id, canonical, full_name in remote_rows:
        player_id = str(player_id)
        remote_labels[player_id] = canonical
        if canonical:
            key = _identity_key((canonical,))[0]
            remote_canonical.setdefault(key, set()).add(player_id)
        for value in (canonical, full_name):
            if value:
                remote_names.setdefault(_identity_key((value,))[0], set()).add(player_id)
    cursor.execute("SELECT player_id::text, name_variant FROM player_name_mappings")
    for player_id, variant in cursor.fetchall():
        if variant:
            remote_aliases.setdefault(_identity_key((variant,))[0], set()).add(str(player_id))

    mapping = {}
    changed = []
    local_labels = {str(row[0]): row[1] for row in local_rows}
    local_full_names = {str(row[0]): row[2] for row in local_rows}
    for local_id, names in local_names.items():
        if local_id in remote_ids:
            mapping[local_id] = local_id
            continue
        canonical_key = _identity_key((local_labels[local_id],))[0]
        candidates = remote_canonical.get(canonical_key, set())
        if len(candidates) != 1 and local_full_names.get(local_id):
            full_key = _identity_key((local_full_names[local_id],))[0]
            candidates = remote_names.get(full_key, set())
        if len(candidates) != 1:
            # Alias mappings are the weakest signal because initials can be
            # shared. Prefer an unambiguous mapping for the local canonical
            # label before considering all recorded variants.
            candidates = remote_aliases.get(canonical_key, set())
        if len(candidates) != 1:
            candidates = set()
            for name in names:
                candidates.update(remote_names.get(name, set()))
                candidates.update(remote_aliases.get(name, set()))
        if len(candidates) == 1:
            remote_id = next(iter(candidates))
            mapping[local_id] = remote_id
            remote_label = remote_labels.get(remote_id, remote_id)
            if _identity_key((local_labels[local_id],)) != _identity_key((remote_label,)):
                changed.append((local_labels[local_id], remote_label))
    return mapping, len(local_rows), len(remote_rows), changed


def _season_id_map(
    cursor, local: sqlite3.Connection, competition_ids: dict[str, str]
) -> tuple[dict[str, str], int, int]:
    local_rows = local.execute(
        "SELECT id, competition_id, name FROM seasons"
    ).fetchall()
    cursor.execute("SELECT id::text, competition_id::text, name FROM seasons")
    remote_rows = cursor.fetchall()
    remote_ids = {str(row[0]) for row in remote_rows}
    remote_by_key = {
        (str(row[1]), _identity_key((row[2],))[0]): str(row[0])
        for row in remote_rows
    }
    mapping = {}
    for season_id, competition_id, name in local_rows:
        season_id = str(season_id)
        if season_id in remote_ids:
            mapping[season_id] = season_id
            continue
        remote_competition_id = competition_ids.get(str(competition_id))
        if remote_competition_id:
            remote_id = remote_by_key.get(
                (remote_competition_id, _identity_key((name,))[0])
            )
            if remote_id:
                mapping[season_id] = remote_id
    return mapping, len(local_rows), len(remote_rows)


def _match_id_map(cursor, local: sqlite3.Connection) -> tuple[dict[str, str], int, int]:
    local_rows = local.execute("SELECT id, external_id FROM matches").fetchall()
    cursor.execute("SELECT id::text, external_id FROM matches")
    remote_rows = cursor.fetchall()
    remote_by_external = {str(row[1]): str(row[0]) for row in remote_rows}
    mapping = {
        str(match_id): remote_by_external[str(external_id)]
        for match_id, external_id in local_rows
        if str(external_id) in remote_by_external
    }
    return mapping, len(local_rows), len(remote_rows)


def _innings_id_map(cursor, local: sqlite3.Connection) -> tuple[dict[str, str], int, int]:
    local_rows = local.execute(
        """SELECT i.id, m.external_id, i.innings_number
           FROM innings i JOIN matches m ON m.id = i.match_id"""
    ).fetchall()
    cursor.execute(
        """SELECT i.id::text, m.external_id, i.innings_number
           FROM innings i JOIN matches m ON m.id = i.match_id"""
    )
    remote_rows = cursor.fetchall()
    remote_by_key = {
        (str(external_id), int(number)): str(innings_id)
        for innings_id, external_id, number in remote_rows
    }
    mapping = {
        str(innings_id): remote_by_key[(str(external_id), int(number))]
        for innings_id, external_id, number in local_rows
        if (str(external_id), int(number)) in remote_by_key
    }
    return mapping, len(local_rows), len(remote_rows)


def _insert_missing_competitions(
    cursor, local: sqlite3.Connection, competition_ids: dict[str, str]
) -> int:
    source = local.execute(
        "SELECT id, name, short_name, format, governing_body, season FROM competitions"
    ).fetchall()
    rows = [row for row in source if str(row[0]) not in competition_ids]
    if rows:
        execute_values(cursor, """
            INSERT INTO competitions (id, name, short_name, format, governing_body, season)
            VALUES %s ON CONFLICT DO NOTHING
        """, rows, page_size=500)
    return len(rows)


def _insert_missing_seasons(
    cursor, local: sqlite3.Connection, season_ids: dict[str, str],
    competition_ids: dict[str, str],
) -> int:
    rows = []
    for season_id, competition_id, name, start_date, end_date in local.execute(
        "SELECT id, competition_id, name, start_date, end_date FROM seasons"
    ):
        if str(season_id) in season_ids:
            continue
        remote_competition = competition_ids.get(str(competition_id))
        if remote_competition:
            rows.append((season_id, remote_competition, name, start_date, end_date))
    if rows:
        execute_values(cursor, """
            INSERT INTO seasons (id, competition_id, name, start_date, end_date)
            VALUES %s ON CONFLICT DO NOTHING
        """, rows, page_size=500)
    return len(rows)


def _sync_match_dimensions(
    cursor, local: sqlite3.Connection, competition_ids: dict[str, str],
    season_ids: dict[str, str],
) -> int:
    rows = [
        (
            str(external_id),
            competition_ids.get(str(competition_id)) if competition_id else None,
            season_ids.get(str(season_id)) if season_id else None,
        )
        for external_id, competition_id, season_id in local.execute(
            "SELECT external_id, competition_id, season_id FROM matches"
        )
    ]
    execute_values(cursor, """
        UPDATE matches AS m
        SET competition_id = v.competition_id::uuid,
            season_id = v.season_id::uuid
        FROM (VALUES %s) AS v(external_id, competition_id, season_id)
        WHERE m.external_id = v.external_id
    """, rows, page_size=1000)
    return len(rows)


def _sync_innings_totals(
    cursor, local: sqlite3.Connection, innings_ids: dict[str, str]
) -> int:
    rows = [
        (
            innings_ids[str(innings_id)],
            int(total_runs or 0),
            int(total_wickets or 0),
            float(total_overs or 0),
            bool(declared),
            bool(all_out),
            bool(follow_on),
        )
        for innings_id, total_runs, total_wickets, total_overs, declared, all_out, follow_on
        in local.execute(
            """SELECT id, total_runs, total_wickets, total_overs,
                      declared, all_out, follow_on FROM innings"""
        )
        if str(innings_id) in innings_ids
    ]
    execute_values(cursor, """
        UPDATE innings AS i
        SET total_runs = v.total_runs,
            total_wickets = v.total_wickets,
            total_overs = v.total_overs,
            declared = v.declared,
            all_out = v.all_out,
            follow_on = v.follow_on
        FROM (VALUES %s) AS v(
            id, total_runs, total_wickets, total_overs,
            declared, all_out, follow_on
        )
        WHERE i.id = v.id::uuid
    """, rows, page_size=1000)
    return len(rows)


def _replace_table(
    cursor, local: sqlite3.Connection, table: str,
    foreign_keys: dict[str, dict[str, str]],
) -> tuple[int, int]:
    local_columns, local_rows = _local_table(local, table)
    remote_columns = _remote_columns(cursor, table)
    if not remote_columns:
        raise RuntimeError(f"PostgreSQL table does not exist: {table}")

    selected = [name for name in local_columns if name in remote_columns]
    indices = [local_columns.index(name) for name in selected]
    rows = []
    skipped = 0
    for local_row in local_rows:
        row = [local_row[index] for index in indices]
        if table == "match_batting_summary" and "is_not_out" in selected:
            boolean_index = selected.index("is_not_out")
            row[boolean_index] = bool(row[boolean_index])
        valid = True
        for column, mapping in foreign_keys.items():
            if column not in selected:
                continue
            index = selected.index(column)
            value = row[index]
            if value is None:
                continue
            mapped = mapping.get(str(value))
            if not mapped:
                valid = False
                break
            row[index] = mapped
        if valid:
            rows.append(tuple(row))
        else:
            skipped += 1

    cursor.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(table)))
    if rows:
        statement = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
            sql.Identifier(table),
            sql.SQL(", ").join(map(sql.Identifier, selected)),
        )
        execute_values(cursor, statement.as_string(cursor), rows, page_size=1000)
    return len(rows), skipped


def _referenced_player_ids(local: sqlite3.Connection) -> set[str]:
    rows = local.execute(
        """SELECT player_id FROM player_batting_stats
           UNION SELECT player_id FROM player_bowling_stats
           UNION SELECT player_id FROM player_recent_stats
           UNION SELECT player_id FROM player_form
           UNION SELECT player_id FROM match_batting_summary
           UNION SELECT bowler_id FROM match_batting_summary
           UNION SELECT fielder_id FROM match_batting_summary
           UNION SELECT player_id FROM match_bowling_summary
           UNION SELECT batter_id FROM batter_bowler_matchups
           UNION SELECT bowler_id FROM batter_bowler_matchups"""
    ).fetchall()
    return {str(row[0]) for row in rows if row[0]}


def _insert_required_players(
    cursor, local: sqlite3.Connection, player_ids: dict[str, str],
    team_ids: dict[str, str], required_ids: set[str],
) -> int:
    if not required_ids:
        return 0
    local_columns = [row[1] for row in local.execute("PRAGMA table_info(players)")]
    remote_columns = _remote_columns(cursor, "players")
    selected = [name for name in local_columns if name in remote_columns]
    placeholders = ",".join("?" for _ in required_ids)
    source_rows = local.execute(
        f"SELECT * FROM players WHERE id IN ({placeholders})", tuple(required_ids)
    ).fetchall()
    rows = []
    for source in source_rows:
        row = [source[local_columns.index(column)] for column in selected]
        if "team_id" in selected:
            index = selected.index("team_id")
            if row[index] is not None:
                row[index] = team_ids.get(str(row[index]))
        if "is_active" in selected:
            index = selected.index("is_active")
            row[index] = bool(row[index])
        rows.append(tuple(row))
    statement = sql.SQL("INSERT INTO players ({}) VALUES %s ON CONFLICT (id) DO NOTHING").format(
        sql.SQL(", ").join(map(sql.Identifier, selected))
    )
    execute_values(cursor, statement.as_string(cursor), rows, page_size=100)
    for player_id in required_ids:
        player_ids[player_id] = player_id
    return len(rows)


def _ensure_remote_analytics_schema(cursor) -> None:
    """Apply additive schema required by the current read-only API routes."""
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS player_recent_stats (
               player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
               format VARCHAR(20) NOT NULL,
               window_start DATE NOT NULL,
               last_match_date DATE,
               matches INTEGER DEFAULT 0,
               batting_innings INTEGER DEFAULT 0,
               runs INTEGER DEFAULT 0,
               balls_faced INTEGER DEFAULT 0,
               bowling_innings INTEGER DEFAULT 0,
               wickets INTEGER DEFAULT 0,
               balls_bowled INTEGER DEFAULT 0,
               runs_conceded INTEGER DEFAULT 0,
               PRIMARY KEY (player_id, format)
           )"""
    )
    cursor.execute(
        "ALTER TABLE player_form ADD COLUMN IF NOT EXISTS last_match_date DATE"
    )
    cursor.execute(
        "ALTER TABLE match_batting_summary "
        "ADD COLUMN IF NOT EXISTS batting_position INTEGER"
    )
    cursor.execute(
        "ALTER TABLE match_bowling_summary "
        "ADD COLUMN IF NOT EXISTS bowling_position INTEGER"
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS season_player_stats (
               season_id UUID NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
               player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
               matches INTEGER DEFAULT 0,
               batting_innings INTEGER DEFAULT 0,
               not_outs INTEGER DEFAULT 0,
               runs INTEGER DEFAULT 0,
               balls_faced INTEGER DEFAULT 0,
               fours INTEGER DEFAULT 0,
               sixes INTEGER DEFAULT 0,
               highest_score INTEGER,
               fifties INTEGER DEFAULT 0,
               hundreds INTEGER DEFAULT 0,
               bowling_innings INTEGER DEFAULT 0,
               balls_bowled INTEGER DEFAULT 0,
               runs_conceded INTEGER DEFAULT 0,
               wickets INTEGER DEFAULT 0,
               maidens INTEGER DEFAULT 0,
               best_wickets INTEGER,
               best_runs INTEGER,
               PRIMARY KEY (season_id, player_id)
           )"""
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_sps_season_runs "
        "ON season_player_stats(season_id, runs DESC)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_sps_season_wickets "
        "ON season_player_stats(season_id, wickets DESC)"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise SystemExit("DATABASE_URL must point to PostgreSQL")
    database_url = database_url.replace("postgresql+psycopg2://", "postgresql://", 1)

    with sqlite3.connect(SQLITE_PATH) as local, psycopg2.connect(
        database_url, connect_timeout=15
    ) as remote:
        with remote.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM matches")
            remote_match_count = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(*) FROM matches WHERE external_id = ANY(%s)",
                (list(RECONSTRUCTED_IDS),),
            )
            fixture_count = cursor.fetchone()[0]
            local_counts = {
                table: local.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in TABLES
            }
            player_ids, local_players, remote_players, player_remaps = _player_id_map(
                cursor, local
            )
            team_ids, local_teams, remote_teams = _entity_id_map(
                cursor, local, "teams", ("canonical_name",)
            )
            venue_ids, local_venues, remote_venues = _entity_id_map(
                cursor, local, "venues", ("name",)
            )
            competition_ids, local_competitions, remote_competitions = _entity_id_map(
                cursor, local, "competitions", ("name", "format")
            )
            season_ids, local_seasons, remote_seasons = _season_id_map(
                cursor, local, competition_ids
            )
            match_id_map, local_matches, remote_matches = _match_id_map(cursor, local)
            innings_ids, local_innings, remote_innings = _innings_id_map(cursor, local)
            print(f"PostgreSQL matches: {remote_match_count:,}")
            print(f"Reconstructed matches to remove: {fixture_count}")
            print(
                f"Identity maps: players {len(player_ids):,}/{local_players:,} local "
                f"({remote_players:,} remote), teams {len(team_ids):,}/{local_teams:,} local "
                f"({remote_teams:,} remote), venues {len(venue_ids):,}/{local_venues:,} local "
                f"({remote_venues:,} remote), competitions "
                f"{len(competition_ids):,}/{local_competitions:,} local "
                f"({remote_competitions:,} remote), seasons "
                f"{len(season_ids):,}/{local_seasons:,} local ({remote_seasons:,} remote), "
                f"match IDs {len(match_id_map):,}/{local_matches:,} local "
                f"({remote_matches:,} remote), innings IDs "
                f"{len(innings_ids):,}/{local_innings:,} local ({remote_innings:,} remote)"
            )
            missing_players = local.execute(
                "SELECT canonical_name FROM players ORDER BY canonical_name"
            ).fetchall()
            missing_players = [
                row[0] for row in missing_players
                if local.execute(
                    "SELECT id FROM players WHERE canonical_name = ?", (row[0],)
                ).fetchone()[0] not in player_ids
            ]
            if missing_players:
                print("Local-only player identities: " + ", ".join(missing_players))
            if player_remaps:
                print(
                    "Alias remaps: "
                    + ", ".join(f"{source} -> {target}" for source, target in player_remaps)
                )
            required_new_player_ids = _referenced_player_ids(local) - set(player_ids)
            if required_new_player_ids:
                placeholders = ",".join("?" for _ in required_new_player_ids)
                required_names = [
                    row[0] for row in local.execute(
                        f"SELECT canonical_name FROM players WHERE id IN ({placeholders}) "
                        "ORDER BY canonical_name",
                        tuple(required_new_player_ids),
                    )
                ]
                print("Required new player identities: " + ", ".join(required_names))
            for table, count in local_counts.items():
                print(f"  {table}: {count:,} local rows")
            print(
                f"Catalog additions required: competitions "
                f"{local_competitions - len(competition_ids):,}, seasons "
                f"{local_seasons - len(season_ids):,}"
            )

            if not args.apply:
                remote.rollback()
                print("Dry run only; pass --apply to synchronize PostgreSQL.")
                return

            added_competitions = _insert_missing_competitions(
                cursor, local, competition_ids
            )
            competition_ids, local_competitions, remote_competitions = _entity_id_map(
                cursor, local, "competitions", ("name", "format")
            )
            added_seasons = _insert_missing_seasons(
                cursor, local, season_ids, competition_ids
            )
            season_ids, local_seasons, remote_seasons = _season_id_map(
                cursor, local, competition_ids
            )
            if len(competition_ids) != local_competitions or len(season_ids) != local_seasons:
                raise RuntimeError(
                    "Competition catalog mapping is incomplete after insert: "
                    f"competitions {len(competition_ids)}/{local_competitions}, "
                    f"seasons {len(season_ids)}/{local_seasons}"
                )
            updated_matches = _sync_match_dimensions(
                cursor, local, competition_ids, season_ids
            )
            updated_innings = _sync_innings_totals(cursor, local, innings_ids)
            print(
                f"  synchronized catalog: {added_competitions:,} competitions, "
                f"{added_seasons:,} seasons, {updated_matches:,} match links, "
                f"{updated_innings:,} innings totals",
                flush=True,
            )

            inserted_players = _insert_required_players(
                cursor, local, player_ids, team_ids, required_new_player_ids
            )
            if inserted_players:
                print(f"  inserted required player identities: {inserted_players}", flush=True)
            _ensure_remote_analytics_schema(cursor)

            cursor.execute(
                "SELECT id FROM matches WHERE external_id = ANY(%s)",
                (list(RECONSTRUCTED_IDS),),
            )
            reconstructed_match_ids = [row[0] for row in cursor.fetchall()]
            if reconstructed_match_ids:
                for table in (
                    "match_batting_summary", "match_bowling_summary",
                    "deliveries", "innings",
                ):
                    if not _remote_columns(cursor, table):
                        print(f"  skipped absent compact table: {table}", flush=True)
                        continue
                    cursor.execute(
                        sql.SQL("DELETE FROM {} WHERE match_id = ANY(%s::uuid[])").format(
                            sql.Identifier(table)
                        ),
                        (reconstructed_match_ids,),
                    )
                cursor.execute(
                    "DELETE FROM matches WHERE id = ANY(%s::uuid[])",
                    (reconstructed_match_ids,),
                )

            written = {}
            key_maps = {
                "match_batting_summary": {
                    "match_id": match_id_map, "innings_id": innings_ids,
                    "player_id": player_ids, "batting_team_id": team_ids,
                    "bowler_id": player_ids, "fielder_id": player_ids,
                },
                "match_bowling_summary": {
                    "match_id": match_id_map, "innings_id": innings_ids,
                    "player_id": player_ids, "bowling_team_id": team_ids,
                },
                "player_batting_stats": {"player_id": player_ids},
                "player_bowling_stats": {"player_id": player_ids},
                "batter_bowler_matchups": {
                    "batter_id": player_ids, "bowler_id": player_ids,
                },
                "player_recent_stats": {"player_id": player_ids},
                "season_player_stats": {
                    "player_id": player_ids, "season_id": season_ids,
                },
                "player_form": {"player_id": player_ids},
                "team_performance": {"team_id": team_ids},
                "venue_stats": {"venue_id": venue_ids},
            }
            for table in TABLES:
                count, skipped = _replace_table(cursor, local, table, key_maps[table])
                written[table] = count
                print(
                    f"  synchronized {table}: {count:,}"
                    + (f" ({skipped:,} unresolved rows rejected)" if skipped else ""),
                    flush=True,
                )

            cursor.execute("SELECT COUNT(*) FROM matches")
            final_matches = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM matches WHERE competition_id IS NOT NULL")
            remote_competition_links = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM matches WHERE season_id IS NOT NULL")
            remote_season_links = cursor.fetchone()[0]
            local_competition_links = local.execute(
                "SELECT COUNT(*) FROM matches WHERE competition_id IS NOT NULL"
            ).fetchone()[0]
            local_season_links = local.execute(
                "SELECT COUNT(*) FROM matches WHERE season_id IS NOT NULL"
            ).fetchone()[0]
            cursor.execute(
                """SELECT COUNT(DISTINCT m.id), COUNT(DISTINCT sp.player_id)
                   FROM competitions c
                   JOIN seasons s ON s.competition_id = c.id
                   LEFT JOIN matches m ON m.season_id = s.id
                   LEFT JOIN season_player_stats sp ON sp.season_id = s.id
                   WHERE lower(c.name) = 'icc cricket world cup'
                     AND s.name = '2023'"""
            )
            cwc_matches, cwc_player_rows = cursor.fetchone()
            cursor.execute(
                """SELECT s.matches, s.innings, s.not_outs, s.runs,
                          s.batting_average, s.balls_faced, s.strike_rate,
                          s.hundreds
                   FROM player_batting_stats s
                   JOIN players p ON p.id = s.player_id
                   WHERE lower(p.canonical_name) = 'virat kohli'
                     AND s.format = 'Test' AND s.period = 'career'"""
            )
            kohli = cursor.fetchone()
            cursor.execute(
                """SELECT
                     (SELECT COUNT(DISTINCT match_id) FROM match_batting_summary),
                     (SELECT COUNT(DISTINCT match_id) FROM match_bowling_summary),
                     (SELECT COUNT(*) FROM match_batting_summary b
                      JOIN innings i ON i.id = b.innings_id
                      WHERE b.match_id != i.match_id
                         OR b.batting_team_id != i.batting_team_id),
                     (SELECT COUNT(*) FROM match_bowling_summary b
                      JOIN innings i ON i.id = b.innings_id
                      WHERE b.match_id != i.match_id
                         OR b.bowling_team_id != i.bowling_team_id)"""
            )
            scorecard_coverage = cursor.fetchone()
            cursor.execute(
                """SELECT i.innings_number, bt.canonical_name,
                          i.total_runs, i.total_wickets, i.total_overs
                   FROM innings i
                   JOIN matches m ON m.id = i.match_id
                   JOIN teams bt ON bt.id = i.batting_team_id
                   WHERE m.external_id = '1384439'
                   ORDER BY i.innings_number"""
            )
            cwc_final_innings = [
                (row[0], row[1], row[2], row[3], round(float(row[4]), 1))
                for row in cursor.fetchall()
            ]
            if final_matches != 8232:
                raise RuntimeError(f"Expected 8,232 PostgreSQL matches, found {final_matches}")
            if remote_competition_links != local_competition_links:
                raise RuntimeError(
                    f"Competition-link verification failed: expected "
                    f"{local_competition_links}, found {remote_competition_links}"
                )
            if remote_season_links != local_season_links:
                raise RuntimeError(
                    f"Season-link verification failed: expected "
                    f"{local_season_links}, found {remote_season_links}"
                )
            if cwc_matches != 39 or cwc_player_rows <= 0:
                raise RuntimeError(
                    f"CWC 2023 verification failed: matches={cwc_matches}, "
                    f"player_rows={cwc_player_rows}"
                )
            if scorecard_coverage != (8232, 8232, 0, 0):
                raise RuntimeError(
                    f"Scorecard coverage/team verification failed: {scorecard_coverage}"
                )
            if cwc_final_innings != [
                (1, "India", 240, 10, 50.0),
                (2, "Australia", 241, 4, 43.0),
            ]:
                raise RuntimeError(
                    f"CWC 2023 final innings verification failed: {cwc_final_innings}"
                )
            normalized_kohli = (
                *kohli[:4], round(float(kohli[4]), 2), kohli[5],
                round(float(kohli[6]), 2), kohli[7],
            ) if kohli else None
            if normalized_kohli != (123, 210, 13, 9230, 46.85, 16608, 55.58, 30):
                raise RuntimeError(f"Virat Kohli Test verification failed: {kohli}")

        remote.commit()

    print("PostgreSQL synchronization committed successfully.")


if __name__ == "__main__":
    main()
