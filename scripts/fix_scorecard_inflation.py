"""
Fix doubled scorecard values for affected ODI/T20I matches.

Root cause: The scorecard generation script processed certain deliveries twice,
resulting in exactly 2x the correct batting/bowling values for ~407 matches
(ODI 2022-2023, T20I 2025-2026).

Fix: Re-read Cricsheet JSON, recompute correct scorecards, overwrite in database.
"""
import os
import sys
import json
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import execute_values

# ZIP paths
ZIP_PATHS = {
    'ODI': 'data/raw/odi/odis_json.zip',
    'T20I': 'data/raw/t20i/t20s_json.zip',
    'T20': 'data/raw/ipl/ipl_json.zip',  # not expected to have issues
}

def compute_scorecard_from_json(data):
    """Compute correct batting and bowling scorecards from Cricsheet JSON."""
    batting_rows = {}  # key: (innings_idx, player_name) -> stats
    bowling_rows = {}  # key: (innings_idx, bowler_name) -> stats

    for innings_idx, innings in enumerate(data.get('innings', [])):
        team = innings.get('team', '')
        for over_data in innings.get('overs', []):
            for ball_idx, delivery in enumerate(over_data.get('deliveries', [])):
                batter = delivery.get('batter', '')
                bowler = delivery.get('bowler', '')
                runs = delivery.get('runs', {})
                batter_runs = runs.get('batter', 0)
                total_runs = runs.get('total', 0)
                extras = delivery.get('extras', {})
                is_wicket = len(delivery.get('wickets', [])) > 0
                wicket_info = delivery.get('wickets', [{}])[0] if is_wicket else {}

                # Batting
                if batter:
                    key = (innings_idx, batter)
                    if key not in batting_rows:
                        batting_rows[key] = {
                            'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0,
                            'is_not_out': True, 'dismissal_type': None
                        }
                    agg = batting_rows[key]
                    agg['runs'] += batter_runs
                    agg['balls'] += 1
                    if batter_runs == 4: agg['fours'] += 1
                    if batter_runs == 6: agg['sixes'] += 1
                    if is_wicket and wicket_info.get('player_out') == batter:
                        agg['is_not_out'] = False
                        agg['dismissal_type'] = wicket_info.get('kind', '')

                # Bowling
                if bowler:
                    key = (innings_idx, bowler)
                    if key not in bowling_rows:
                        bowling_rows[key] = {
                            'balls': 0, 'runs': 0, 'wickets': 0,
                            'wides': 0, 'noballs': 0
                        }
                    agg = bowling_rows[key]
                    agg['balls'] += 1
                    agg['runs'] += total_runs
                    if is_wicket and wicket_info.get('kind', '') not in (
                        'run out', 'retired hurt', 'obstructing the field', 'retired out'
                    ):
                        agg['wickets'] += 1
                    if 'wides' in extras: agg['wides'] += 1
                    if 'noballs' in extras: agg['noballs'] += 1

    return batting_rows, bowling_rows


def fix_affected_matches():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.autocommit = False
    cur = conn.cursor()

    # Find all affected matches (scorecard > 1.5x innings total)
    cur.execute('''
        SELECT DISTINCT m.id, m.external_id, m.format
        FROM matches m
        JOIN innings i ON i.match_id = m.id
        JOIN (SELECT innings_id, SUM(runs) as bat_runs FROM match_batting_summary GROUP BY innings_id) bsc
            ON bsc.innings_id = i.id
        WHERE bsc.bat_runs > i.total_runs * 1.5
        AND m.format IN ('ODI', 'T20I')
    ''')
    affected = cur.fetchall()
    print(f'Found {len(affected)} affected matches to fix')

    fixed = 0
    errors = 0

    for match_db_id, external_id, fmt in affected:
        # Read source JSON
        zip_path = ZIP_PATHS.get(fmt)
        if not zip_path or not os.path.exists(zip_path):
            print(f'  SKIP {external_id} ({fmt}): ZIP not found')
            continue

        try:
            with zipfile.ZipFile(zip_path) as zf:
                fname = f'{external_id}.json'
                if fname not in zf.namelist():
                    print(f'  SKIP {external_id}: not in ZIP')
                    continue
                data = json.loads(zf.read(fname))
        except Exception as e:
            print(f'  ERROR reading {external_id}: {e}')
            errors += 1
            continue

        # Get innings mapping
        cur.execute('''
            SELECT i.id, i.innings_number, i.batting_team_id, ta.canonical_name
            FROM innings i
            JOIN teams ta ON i.batting_team_id = ta.id
            WHERE i.match_id = %s ORDER BY i.innings_number
        ''', (match_db_id,))
        innings_rows = cur.fetchall()
        innings_map = {}  # innings_idx (0-based) -> (innings_id, batting_team_id, team_name)
        for inn in innings_rows:
            innings_map[inn[1] - 1] = (inn[0], inn[2], inn[3])

        # Compute correct scorecards from JSON
        batting_rows, bowling_rows = compute_scorecard_from_json(data)

        # Get player name -> ID mapping
        cur.execute('SELECT id, canonical_name FROM players')
        player_map = {r[1]: r[0] for r in cur.fetchall()}

        # Delete and re-insert batting summaries for this match
        cur.execute('DELETE FROM match_batting_summary WHERE match_id = %s', (match_db_id,))
        bat_deleted = cur.rowcount
        conn.commit()

        bat_inserts = []
        for (innings_idx, player_name), stats in batting_rows.items():
            if innings_idx not in innings_map:
                continue
            innings_id, batting_team_id, _ = innings_map[innings_idx]
            player_id = player_map.get(player_name)
            if not player_id:
                continue
            sr = (stats['runs'] / stats['balls'] * 100) if stats['balls'] > 0 else 0
            bat_inserts.append((
                match_db_id, innings_id, player_id, batting_team_id,
                stats['runs'], stats['balls'], stats['fours'], stats['sixes'],
                round(sr, 2), stats['is_not_out'], stats['dismissal_type'],
                None, None
            ))

        if bat_inserts:
            execute_values(cur, '''INSERT INTO match_batting_summary
                (match_id, innings_id, player_id, batting_team_id,
                 runs, balls, fours, sixes, strike_rate, is_not_out,
                 dismissal_type, bowler_id, fielder_id) VALUES %s
                ON CONFLICT (match_id, innings_id, player_id) DO NOTHING''',
                bat_inserts, page_size=500)

        # Delete and re-insert bowling summaries for this match
        cur.execute('DELETE FROM match_bowling_summary WHERE match_id = %s', (match_db_id,))
        bowl_deleted = cur.rowcount
        conn.commit()

        bowl_inserts = []
        for (innings_idx, bowler_name), stats in bowling_rows.items():
            if innings_idx not in innings_map:
                continue
            innings_id, _, _ = innings_map[innings_idx]
            cur.execute('SELECT bowling_team_id FROM innings WHERE id = %s', (innings_id,))
            bowling_team_id = cur.fetchone()[0]
            player_id = player_map.get(bowler_name)
            if not player_id:
                continue
            overs = stats['balls'] // 6 + (stats['balls'] % 6) / 10.0
            econ = (stats['runs'] / overs) if overs > 0 else 0
            bowl_inserts.append((
                match_db_id, innings_id, player_id, bowling_team_id,
                round(overs, 1), stats['balls'], 0,
                stats['runs'], stats['wickets'], round(econ, 2),
                stats['wides'], stats['noballs']
            ))

        if bowl_inserts:
            execute_values(cur, '''INSERT INTO match_bowling_summary
                (match_id, innings_id, player_id, bowling_team_id,
                 overs, balls_bowled, maidens, runs_conceded, wickets,
                 economy, wides, noballs) VALUES %s
                ON CONFLICT (match_id, innings_id, player_id) DO NOTHING''',
                bowl_inserts, page_size=500)

        conn.commit()
        fixed += 1
        if fixed % 50 == 0:
            print(f'  Fixed {fixed}/{len(affected)} matches...')

    print(f'\nDone! Fixed: {fixed}, Errors: {errors}')

    # Verify
    cur.execute('''
        SELECT m.format,
               SUM(CASE WHEN bsc.bat_runs > i.total_runs * 1.5 THEN 1 ELSE 0 END) as still_inflated,
               COUNT(*) as total
        FROM innings i
        JOIN matches m ON i.match_id = m.id
        LEFT JOIN (SELECT innings_id, SUM(runs) as bat_runs FROM match_batting_summary GROUP BY innings_id) bsc
            ON bsc.innings_id = i.id
        WHERE m.format IN ('ODI', 'T20I') AND i.total_runs > 0
        GROUP BY m.format
    ''')
    print('\n=== POST-FIX VERIFICATION ===')
    for r in cur.fetchall():
        print(f'  {r[0]}: {r[1] or 0} still inflated / {r[2]} total')

    conn.close()


if __name__ == '__main__':
    fix_affected_matches()
