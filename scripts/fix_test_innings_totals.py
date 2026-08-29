"""
Fix Test innings total_runs to include extras.

Phase 6.0 discovered that ~30% of Test innings have total_runs that only
count batter runs, not extras. T20/T20I/ODI are all correct (include extras).
This script recalculates Test innings totals from authoritative Cricsheet JSON.
"""
import json
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def fix_test_innings():
    batch_size = 50
    total_fixed = 0
    total_checked = 0
    start = time.time()

    with engine.connect() as conn:
        # Get all Test matches
        matches = conn.execute(text("""
            SELECT m.id as match_id, m.external_id, 
                   i.id as innings_id, i.innings_number, i.total_runs
            FROM matches m
            JOIN innings i ON i.match_id = m.id
            WHERE m.format = 'Test'
            ORDER BY m.match_date
        """)).fetchall()

        total_matches = len(matches)
        print(f"Processing {total_matches} Test innings...")

        fixes = []
        for idx, m in enumerate(matches):
            ext_id = m[1]
            json_path = f"data/raw/test/{ext_id}.json"
            if not os.path.exists(json_path):
                continue

            inn_idx = m[3] - 1
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            innings_data = data.get('innings', [])
            if inn_idx >= len(innings_data):
                continue

            overs = innings_data[inn_idx].get('overs', [])
            json_total = sum(
                d['runs']['total']
                for o in overs
                for d in o.get('deliveries', [])
            )

            total_checked += 1
            if json_total != m[4]:
                fixes.append((m[2], json_total, m[4], ext_id, m[3]))

            # Batch update
            if len(fixes) >= batch_size:
                for fix in fixes:
                    conn.execute(
                        text("UPDATE innings SET total_runs = :new_total WHERE id = :iid"),
                        {"new_total": fix[1], "iid": fix[0]}
                    )
                conn.commit()
                total_fixed += len(fixes)
                print(f"  Fixed {total_fixed}/{total_checked}...")
                fixes = []

        # Final batch
        if fixes:
            for fix in fixes:
                conn.execute(
                    text("UPDATE innings SET total_runs = :new_total WHERE id = :iid"),
                    {"new_total": fix[1], "iid": fix[0]}
                )
            conn.commit()
            total_fixed += len(fixes)

        elapsed = time.time() - start
        print(f"\nDone in {elapsed:.1f}s")
        print(f"Checked: {total_checked} innings")
        print(f"Fixed: {total_fixed} innings")

        # Verify
        mismatches = 0
        verify = conn.execute(text("""
            SELECT COUNT(*) FROM innings i
            JOIN matches m ON i.match_id = m.id
            WHERE m.format = 'Test'
        """)).scalar()
        print(f"Total Test innings: {verify}")

        # Show sample of remaining differences (should be 0 or near-0)
        remaining = conn.execute(text("""
            SELECT m.external_id, i.innings_number, i.total_runs
            FROM matches m
            JOIN innings i ON i.match_id = m.id
            WHERE m.format = 'Test' AND i.total_runs > 0
            ORDER BY RANDOM() LIMIT 5
        """)).fetchall()
        print("\nSample verification:")
        for r in remaining:
            ext_id = r[0]
            json_path = f"data/raw/test/{ext_id}.json"
            if not os.path.exists(json_path):
                continue
            with open(json_path, 'r') as f:
                data = json.load(f)
            inn_idx = r[1] - 1
            if inn_idx >= len(data.get('innings', [])):
                continue
            overs = data['innings'][inn_idx].get('overs', [])
            json_total = sum(
                d['runs']['total']
                for o in overs
                for d in o.get('deliveries', [])
            )
            status = "OK" if json_total == r[2] else f"MISMATCH ({json_total})"
            print(f"  {ext_id} I{r[1]}: DB={r[2]} JSON={json_total} [{status}]")


if __name__ == "__main__":
    fix_test_innings()
