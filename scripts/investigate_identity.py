"""Investigate player identity issues in the database."""
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text

engine = create_engine(os.getenv("DATABASE_URL"))


def main():
    with engine.connect() as conn:
        # 1. T Kohli investigation
        print("=== T KOHLI DETAILS ===")
        r = conn.execute(text(
            "SELECT CAST(id AS VARCHAR), canonical_name, country, role "
            "FROM players WHERE canonical_name = 'T Kohli'"
        )).fetchone()
        if r:
            pid = r[0]
            print(f"  Name: {r[1]}, Country: {r[2]}, Role: {r[3]}")
            # Check in deliveries
            rows = conn.execute(text(
                "SELECT m.format, COUNT(*) as cnt "
                "FROM deliveries del "
                "JOIN innings i ON del.innings_id = i.id "
                "JOIN matches m ON del.match_id = m.id "
                "WHERE CAST(del.striker_id AS VARCHAR) = :pid "
                "OR CAST(del.bowler_id AS VARCHAR) = :pid "
                "GROUP BY m.format"
            ), {"pid": pid}).fetchall()
            for row in rows:
                print(f"    In deliveries: format={row[0]}, count={row[1]}")

        # 2. Kohli affiliations
        print("\n=== KOHLI AFFILIATIONS ===")
        rows = conn.execute(text(
            "SELECT p.canonical_name, t.canonical_name, a.format "
            "FROM player_team_affiliations a "
            "JOIN players p ON a.player_id = p.id "
            "JOIN teams t ON a.team_id = t.id "
            "WHERE p.canonical_name LIKE '%Kohli%' "
            "ORDER BY p.canonical_name, a.format"
        )).fetchall()
        for row in rows:
            print(f"  {row[0]} -> {row[1]} ({row[2]})")

        # 3. Kohli stats by player
        print("\n=== KOHLI STATS BY PLAYER ===")
        rows = conn.execute(text(
            "SELECT p.canonical_name, p.id::text, b.format, b.runs, b.innings, b.batting_average "
            "FROM player_batting_stats b "
            "JOIN players p ON b.player_id = p.id "
            "WHERE p.canonical_name LIKE '%Kohli%' "
            "ORDER BY p.canonical_name, b.format"
        )).fetchall()
        for row in rows:
            print(f"  {row[0]} ({row[1][:8]}...): {row[2]} = {row[3]} runs, {row[4]} inn, avg={row[5]}")

        # 4. Which IPL files use which name for Kohli?
        print("\n=== IPL: WHICH FILES USE WHICH KOHLI NAME ===")
        import json
        ipl_dir = Path("data/raw/ipl")
        v_kohli_files = 0
        virat_files = 0
        other_kohli = set()
        for f in sorted(ipl_dir.glob("*.json"))[:50]:
            with open(f) as fp:
                data = json.load(fp)
            info = data.get("info", {})
            players = info.get("players", {})
            for team, plist in players.items():
                for p in plist:
                    if "Kohli" in p or "kohli" in p.lower():
                        if p == "V Kohli":
                            v_kohli_files += 1
                        elif p == "Virat Kohli":
                            virat_files += 1
                        else:
                            other_kohli.add(p)
        print(f"  'V Kohli' in {v_kohli_files} player-list entries (first 50 files)")
        print(f"  'Virat Kohli' in {virat_files} player-list entries (first 50 files)")
        if other_kohli:
            print(f"  Other: {other_kohli}")

        # 5. Check delivery-level: which Kohli name appears in deliveries?
        print("\n=== DELIVERY-LEVEL: KOHLI NAME IN SOURCE DATA ===")
        v_kohli_count = 0
        virat_count = 0
        for f in sorted(ipl_dir.glob("*.json"))[:20]:
            with open(f) as fp:
                data = json.load(fp)
            for innings in data.get("innings", []):
                for over in innings.get("overs", []):
                    for d in over.get("deliveries", []):
                        if d.get("batter") == "V Kohli":
                            v_kohli_count += 1
                        elif d.get("batter") == "Virat Kohli":
                            virat_count += 1
                        if d.get("bowler") == "V Kohli":
                            v_kohli_count += 1
                        elif d.get("bowler") == "Virat Kohli":
                            virat_count += 1
        print(f"  First 20 IPL files: 'V Kohli' = {v_kohli_count}, 'Virat Kohli' = {virat_count}")

        # 6. The key question: does the Cricsheet registry map both names to the same ID?
        print("\n=== CRICSHEET REGISTRY MAPPING ===")
        for f in sorted(ipl_dir.glob("*.json"))[:5]:
            with open(f) as fp:
                data = json.load(fp)
            registry = data.get("info", {}).get("registry", {}).get("people", {})
            v_entry = registry.get("V Kohli")
            virat_entry = registry.get("Virat Kohli")
            if v_entry or virat_entry:
                print(f"  {f.name}: V Kohli={v_entry}, Virat Kohli={virat_entry}")

        # 7. How many players have ONLY one format vs multiple?
        print("\n=== PLAYER FORMAT DISTRIBUTION ===")
        rows = conn.execute(text(
            "SELECT p.canonical_name, COUNT(DISTINCT b.format) as fmt_count, "
            "STRING_AGG(DISTINCT b.format, ', ' ORDER BY b.format) as formats "
            "FROM player_batting_stats b "
            "JOIN players p ON b.player_id = p.id "
            "GROUP BY p.canonical_name "
            "HAVING COUNT(DISTINCT b.format) >= 2 "
            "ORDER BY fmt_count DESC, p.canonical_name "
            "LIMIT 20"
        )).fetchall()
        for row in rows:
            print(f"  {row[0]}: {row[1]} formats = {row[2]}")

        # 8. Total potential duplicates - players with very similar names
        print("\n=== TOTAL POTENTIAL DUPLICATES ===")
        rows = conn.execute(text(
            "SELECT p1.canonical_name, p2.canonical_name "
            "FROM players p1 "
            "JOIN players p2 ON p1.id < p2.id "
            "WHERE p1.canonical_name != p2.canonical_name "
            "AND ("
            "  REPLACE(p1.canonical_name, ' ', '') = REPLACE(p2.canonical_name, ' ', '') "
            "  OR p1.canonical_name || ' ' = p2.canonical_name "
            "  OR p2.canonical_name || ' ' = p1.canonical_name "
            "  OR p1.canonical_name = REPLACE(p2.canonical_name, ' (2)', '') "
            "  OR p2.canonical_name = REPLACE(p1.canonical_name, ' (2)', '')"
            ") "
            "ORDER BY p1.canonical_name "
            "LIMIT 30"
        )).fetchall()
        print(f"  Found {len(rows)} potential name pairs")
        for row in rows:
            print(f"    \"{row[0]}\" <-> \"{row[1]}\"")


if __name__ == "__main__":
    main()
