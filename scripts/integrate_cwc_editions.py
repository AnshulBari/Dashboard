"""Merge historical ODI World Cup aliases into one searchable competition."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from backend.services.cwc_reference import CWC_NAME, load_cwc_reference
from rebuild_official_player_stats import DEFAULT_DB
from rebuild_season_player_stats import apply_cwc_reference_overrides


ALIASES = ("ICC World Cup", "World Cup")


def integrate(conn: sqlite3.Connection) -> dict[str, int]:
    canonical = conn.execute(
        "SELECT id FROM competitions WHERE lower(name) = lower(?)", (CWC_NAME,)
    ).fetchone()
    if not canonical:
        raise RuntimeError(f"Canonical competition is missing: {CWC_NAME}")
    canonical_id = str(canonical[0])
    moved_matches = moved_seasons = 0

    for alias in ALIASES:
        competitions = conn.execute(
            "SELECT id FROM competitions WHERE lower(name) = lower(?)", (alias,)
        ).fetchall()
        for (alias_id,) in competitions:
            source_seasons = conn.execute(
                "SELECT id, name, start_date, end_date FROM seasons WHERE competition_id = ?",
                (alias_id,),
            ).fetchall()
            for source_id, name, start_date, end_date in source_seasons:
                target = conn.execute(
                    "SELECT id FROM seasons WHERE competition_id = ? AND name = ?",
                    (canonical_id, name),
                ).fetchone()
                if target:
                    target_id = str(target[0])
                    target_rows = conn.execute(
                        "SELECT COUNT(*) FROM season_player_stats WHERE season_id = ?", (target_id,)
                    ).fetchone()[0]
                    source_rows = conn.execute(
                        "SELECT COUNT(*) FROM season_player_stats WHERE season_id = ?", (source_id,)
                    ).fetchone()[0]
                    if target_rows and source_rows:
                        raise RuntimeError(f"Both source and target seasons contain player stats: {name}")
                    conn.execute(
                        "UPDATE season_player_stats SET season_id = ? WHERE season_id = ?",
                        (target_id, source_id),
                    )
                    conn.execute("""
                        UPDATE seasons SET
                            start_date = COALESCE(start_date, ?),
                            end_date = COALESCE(end_date, ?)
                        WHERE id = ?
                    """, (start_date, end_date, target_id))
                    cursor = conn.execute("""
                        UPDATE matches SET competition_id = ?, season_id = ?
                        WHERE season_id = ?
                    """, (canonical_id, target_id, source_id))
                    moved_matches += max(cursor.rowcount, 0)
                    conn.execute("DELETE FROM seasons WHERE id = ?", (source_id,))
                else:
                    conn.execute(
                        "UPDATE seasons SET competition_id = ? WHERE id = ?",
                        (canonical_id, source_id),
                    )
                    cursor = conn.execute(
                        "UPDATE matches SET competition_id = ? WHERE season_id = ?",
                        (canonical_id, source_id),
                    )
                    moved_matches += max(cursor.rowcount, 0)
                moved_seasons += 1
            conn.execute("DELETE FROM competitions WHERE id = ?", (alias_id,))

    expected = set(load_cwc_reference()["editions"])
    present = {
        row[0] for row in conn.execute(
            "SELECT name FROM seasons WHERE competition_id = ?", (canonical_id,)
        )
    }
    missing = sorted(expected - present)
    if missing:
        raise RuntimeError("Missing canonical CWC seasons: " + ", ".join(missing))

    overrides = apply_cwc_reference_overrides(conn)
    return {
        "seasons_merged": moved_seasons,
        "matches_relinked": moved_matches,
        "leader_records_overlaid": overrides,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        report = integrate(conn)
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
        print("CWC integration: " + ", ".join(f"{key}={value:,}" for key, value in report.items()))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
