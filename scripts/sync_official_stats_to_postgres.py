"""Atomically synchronize corrected serving aggregates to PostgreSQL.

The local SQLite database is the rebuildable serving snapshot.  This command
copies only derived analytics tables, then removes the known reconstructed
fixture matches from PostgreSQL.  Entity identities and compact official match
scorecards are preserved.  No ball-by-ball delivery data is uploaded.

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
    "player_batting_stats",
    "player_bowling_stats",
    "batter_bowler_matchups",
    "player_recent_stats",
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


def _replace_table(cursor, local: sqlite3.Connection, table: str) -> int:
    local_columns, local_rows = _local_table(local, table)
    remote_columns = _remote_columns(cursor, table)
    if not remote_columns:
        raise RuntimeError(f"PostgreSQL table does not exist: {table}")

    selected = [name for name in local_columns if name in remote_columns]
    indices = [local_columns.index(name) for name in selected]
    rows = [tuple(row[index] for index in indices) for row in local_rows]

    cursor.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(table)))
    if rows:
        statement = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
            sql.Identifier(table),
            sql.SQL(", ").join(map(sql.Identifier, selected)),
        )
        execute_values(cursor, statement.as_string(cursor), rows, page_size=1000)
    return len(rows)


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
            print(f"PostgreSQL matches: {remote_match_count:,}")
            print(f"Reconstructed matches to remove: {fixture_count}")
            for table, count in local_counts.items():
                print(f"  {table}: {count:,} local rows")

            if not args.apply:
                remote.rollback()
                print("Dry run only; pass --apply to synchronize PostgreSQL.")
                return

            cursor.execute(
                "SELECT id FROM matches WHERE external_id = ANY(%s)",
                (list(RECONSTRUCTED_IDS),),
            )
            match_ids = [row[0] for row in cursor.fetchall()]
            if match_ids:
                for table in (
                    "match_batting_summary", "match_bowling_summary",
                    "deliveries", "innings",
                ):
                    cursor.execute(
                        sql.SQL("DELETE FROM {} WHERE match_id = ANY(%s)").format(
                            sql.Identifier(table)
                        ),
                        (match_ids,),
                    )
                cursor.execute("DELETE FROM matches WHERE id = ANY(%s)", (match_ids,))

            written = {}
            for table in TABLES:
                written[table] = _replace_table(cursor, local, table)
                print(f"  synchronized {table}: {written[table]:,}", flush=True)

            cursor.execute("SELECT COUNT(*) FROM matches")
            final_matches = cursor.fetchone()[0]
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
            if final_matches != 8232:
                raise RuntimeError(f"Expected 8,232 PostgreSQL matches, found {final_matches}")
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
