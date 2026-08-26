"""
Phase 3.1 Migration: Player Identity Merge
===========================================

Creates player_aliases table and merges duplicate player identities.

Known merge: "V Kohli" → "Virat Kohli"

Strategy:
1. Create player_aliases table
2. Record the mapping
3. Update all FK references from V Kohli to Virat Kohli
4. Remove V Kohli player record
5. Validate no orphaned records
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

engine = create_engine(DATABASE_URL)


def create_aliases_table(conn):
    """Create the player_aliases table if it doesn't exist."""
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS player_aliases (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
            alias_name VARCHAR(255) NOT NULL,
            source VARCHAR(100) DEFAULT 'cricsheet',
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(player_id, alias_name)
        )
    """))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS idx_player_aliases_alias ON player_aliases(alias_name)"
    ))
    conn.commit()
    print("  Created player_aliases table")


def record_alias(conn, canonical_player_id, alias_name, source="cricsheet"):
    """Record a player alias."""
    conn.execute(text(
        "INSERT INTO player_aliases (player_id, alias_name, source) "
        "VALUES (:pid, :alias, :src) "
        "ON CONFLICT (player_id, alias_name) DO NOTHING"
    ), {"pid": canonical_player_id, "alias": alias_name, "src": source})
    print(f"  Recorded alias: \"{alias_name}\" -> player {str(canonical_player_id)[:8]}...")


def merge_player_foreign_keys(conn, from_id, to_id):
    """
    Update all FK references from one player to another.
    Returns a dict of table → updated count.
    """
    updates = {}

    fk_columns = [
        ("deliveries", "striker_id"),
        ("deliveries", "bowler_id"),
        ("deliveries", "non_striker_id"),
        ("deliveries", "dismissed_player_id"),
        ("player_batting_stats", "player_id"),
        ("player_bowling_stats", "player_id"),
        ("player_form", "player_id"),
        ("batter_bowler_matchups", "batter_id"),
        ("batter_bowler_matchups", "bowler_id"),
        ("player_team_affiliations", "player_id"),
        ("matches", "player_of_match_id"),
    ]

    for table, col in fk_columns:
        result = conn.execute(text(
            f"UPDATE {table} SET {col} = :to_id WHERE {col} = :from_id"
        ), {"to_id": to_id, "from_id": from_id})
        count = result.rowcount
        if count > 0:
            updates[f"{table}.{col}"] = count
            print(f"    Updated {table}.{col}: {count} records")

    return updates


def main():
    with engine.connect() as conn:
        # Step 1: Create aliases table
        print("Step 1: Creating player_aliases table...")
        create_aliases_table(conn)

        # Step 2: Find V Kohli and Virat Kohli
        print("\nStep 2: Finding player IDs...")
        v_kohli_id = conn.execute(text(
            "SELECT id FROM players WHERE canonical_name = 'V Kohli'"
        )).scalar()
        virat_id = conn.execute(text(
            "SELECT id FROM players WHERE canonical_name = 'Virat Kohli'"
        )).scalar()

        if not v_kohli_id:
            print("  ERROR: 'V Kohli' not found")
            return
        if not virat_id:
            print("  ERROR: 'Virat Kohli' not found")
            return

        print(f"  V Kohli: {v_kohli_id}")
        print(f"  Virat Kohli: {virat_id}")

        # Step 3: Record aliases
        print("\nStep 3: Recording aliases...")
        record_alias(conn, virat_id, "V Kohli", "cricsheet")
        record_alias(conn, virat_id, "Virat Kohli", "cricsheet")
        conn.commit()

        # Step 4: Merge FK references
        print("\nStep 4: Merging foreign key references...")
        updates = merge_player_foreign_keys(conn, v_kohli_id, virat_id)
        conn.commit()

        total_updates = sum(updates.values())
        print(f"\n  Total FK updates: {total_updates}")

        # Step 5: Delete V Kohli player record
        print("\nStep 5: Removing V Kohli player record...")
        result = conn.execute(text("DELETE FROM players WHERE id = :id"), {"id": v_kohli_id})
        print(f"  Deleted {result.rowcount} player record")
        conn.commit()

        # Step 6: Validate - no orphans
        print("\nStep 6: Validating no orphaned records...")
        for table, col in [
            ("deliveries", "striker_id"),
            ("deliveries", "bowler_id"),
            ("player_batting_stats", "player_id"),
            ("player_bowling_stats", "player_id"),
            ("player_form", "player_id"),
            ("batter_bowler_matchups", "batter_id"),
            ("batter_bowler_matchups", "bowler_id"),
            ("player_team_affiliations", "player_id"),
        ]:
            orphan_count = conn.execute(text(
                f"SELECT COUNT(*) FROM {table} t "
                f"WHERE t.{col} IS NOT NULL "
                f"AND NOT EXISTS (SELECT 1 FROM players p WHERE p.id = t.{col})"
            )).scalar()
            if orphan_count > 0:
                print(f"  WARNING: {table}.{col} has {orphan_count} orphans!")
            else:
                print(f"  OK: {table}.{col} no orphans")

        # Step 7: Verify merged identity
        print("\nStep 7: Verifying merged identity...")
        rows = conn.execute(text(
            "SELECT b.format, b.runs, b.innings "
            "FROM player_batting_stats b "
            "WHERE b.player_id = :pid "
            "ORDER BY b.format"
        ), {"pid": virat_id}).fetchall()
        print(f"  Virat Kohli batting stats:")
        for r in rows:
            print(f"    {r[0]}: {r[1]} runs, {r[2]} innings")

        # Check affiliations
        rows = conn.execute(text(
            "SELECT t.canonical_name, a.format "
            "FROM player_team_affiliations a "
            "JOIN teams t ON a.team_id = t.id "
            "WHERE a.player_id = :pid "
            "ORDER BY a.format"
        ), {"pid": virat_id}).fetchall()
        print(f"  Virat Kohli affiliations:")
        for r in rows:
            print(f"    {r[0]} ({r[1]})")

        # Final counts
        print("\nFinal player count:")
        count = conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
        print(f"  players: {count}")
        alias_count = conn.execute(text("SELECT COUNT(*) FROM player_aliases")).scalar()
        print(f"  player_aliases: {alias_count}")


if __name__ == "__main__":
    main()
