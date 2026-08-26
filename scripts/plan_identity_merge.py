"""Plan and execute the player identity merge migration."""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text

engine = create_engine(os.getenv("DATABASE_URL"))

# Known Cricsheet-to-canonical mappings
# Format: cricsheet_name -> canonical_name
CRICSHEET_ALIASES = {
    "V Kohli": "Virat Kohli",
    "V Dharma": "Wriddhiman Saha",  # check if this is real
}


def main():
    with engine.connect() as conn:
        # Count how many deliveries reference "V Kohli"
        print("=== DELIVERIES REFERENCING 'V Kohli' ===")
        v_kohli_id = conn.execute(text(
            "SELECT CAST(id AS VARCHAR) FROM players WHERE canonical_name = 'V Kohli'"
        )).scalar()
        virat_id = conn.execute(text(
            "SELECT CAST(id AS VARCHAR) FROM players WHERE canonical_name = 'Virat Kohli'"
        )).scalar()
        print(f"  V Kohli ID: {v_kohli_id}")
        print(f"  Virat Kohli ID: {virat_id}")

        # Count dependent records
        for table_col in [
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
        ]:
            table, col = table_col
            count = conn.execute(text(
                f"SELECT COUNT(*) FROM {table} WHERE CAST({col} AS VARCHAR) = :pid"
            ), {"pid": v_kohli_id}).scalar()
            if count > 0:
                print(f"  {table}.{col}: {count} records")

        # Check if there are other Cricsheet-style abbreviated names that need mapping
        # Look at all players with single-letter first names (potential abbreviations)
        print("\n=== PLAYERS WITH ABBREVIATED NAMES (first name = 1-2 chars) ===")
        rows = conn.execute(text(
            "SELECT canonical_name, id::text FROM players "
            "WHERE LENGTH(SPLIT_PART(canonical_name, ' ', 1)) <= 2 "
            "AND LENGTH(canonical_name) > 4 "
            "ORDER BY canonical_name LIMIT 30"
        )).fetchall()
        for row in rows:
            print(f"  {row[0]} ({row[1][:8]}...)")

        # Check how many players could potentially have full-name equivalents
        print("\n=== FULL NAMES WITH INITIAL-PREFIX PATTERN ===")
        rows = conn.execute(text(
            "SELECT p1.canonical_name, p2.canonical_name "
            "FROM players p1 "
            "JOIN players p2 ON p1.id != p2.id "
            "WHERE LENGTH(SPLIT_PART(p1.canonical_name, ' ', 1)) <= 2 "
            "AND p2.canonical_name LIKE '%' || SPLIT_PART(p1.canonical_name, ' ', 2) || '%' "
            "AND LENGTH(SPLIT_PART(p1.canonical_name, ' ', 1)) = 1 "
            "AND p2.canonical_name != p1.canonical_name "
            "ORDER BY p1.canonical_name "
            "LIMIT 30"
        )).fetchall()
        print(f"  Found {len(rows)} potential abbreviation-to-full pairs")
        for row in rows[:10]:
            print(f"    \"{row[0]}\" -> \"{row[1]}\"")


if __name__ == "__main__":
    main()
