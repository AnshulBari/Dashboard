"""Generate match batting and bowling scorecards from deliveries table.

Processes in small chunks to avoid Supabase timeouts.
Writes to match_batting_summary and match_bowling_summary tables.
"""
import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import execute_values

CHECKPOINT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'scorecard_checkpoint.json')

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {'processed_matches': [], 'batting_count': 0, 'bowling_count': 0, 'phase': 'batting'}

def save_checkpoint(state):
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(state, f)

def generate_scorecards():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.autocommit = False
    cur = conn.cursor()
    
    state = load_checkpoint()
    processed = set(state.get('processed_matches', []))
    batting_count = state.get('batting_count', 0)
    bowling_count = state.get('bowling_count', 0)
    
    # Get all match IDs that have deliveries
    cur.execute('SELECT DISTINCT match_id FROM deliveries ORDER BY match_id')
    all_match_ids = [r[0] for r in cur.fetchall()]
    remaining = [m for m in all_match_ids if m not in processed]
    
    print(f'Total matches: {len(all_match_ids)}, Already processed: {len(processed)}, Remaining: {len(remaining)}')
    
    chunk_size = 50  # Small chunks to avoid timeout
    
    for chunk_start in range(0, len(remaining), chunk_size):
        chunk_ids = remaining[chunk_start:chunk_start + chunk_size]
        placeholders = ','.join(['%s'] * len(chunk_ids))
        
        # Fetch deliveries for this chunk
        cur.execute(f'''
            SELECT 
                d.match_id, d.innings_id, d.striker_id, d.bowler_id,
                d.runs_bat, d.total_runs, d.extra_type, d.is_wicket,
                d.wicket_type, d.dismissed_player_id, d.fielder_id,
                i.batting_team_id, i.bowling_team_id
            FROM deliveries d
            JOIN innings i ON d.innings_id = i.id
            WHERE d.match_id IN ({placeholders})
        ''', chunk_ids)
        
        rows = cur.fetchall()
        
        # Aggregate
        bat_agg = {}
        bowl_agg = {}
        
        for r in rows:
            match_id, innings_id, striker_id, bowler_id = r[0], r[1], r[2], r[3]
            runs_bat = r[4] or 0
            total_runs = r[5] or 0
            extra_type = r[6]
            is_wicket = r[7]
            wicket_type = r[8]
            dismissed_player_id = r[9]
            fielder_id = r[10]
            batting_team_id = r[11]
            bowling_team_id = r[12]
            
            if striker_id:
                key = (match_id, innings_id, striker_id)
                if key not in bat_agg:
                    bat_agg[key] = {
                        'batting_team_id': batting_team_id,
                        'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0,
                        'is_not_out': True, 'dismissal_type': None,
                        'bowler_id': None, 'fielder_id': None
                    }
                agg = bat_agg[key]
                agg['runs'] += runs_bat
                agg['balls'] += 1
                if runs_bat == 4: agg['fours'] += 1
                if runs_bat == 6: agg['sixes'] += 1
                if is_wicket and dismissed_player_id == striker_id:
                    agg['is_not_out'] = False
                    agg['dismissal_type'] = wicket_type
                    agg['bowler_id'] = bowler_id
                    agg['fielder_id'] = fielder_id
            
            if bowler_id:
                key = (match_id, innings_id, bowler_id)
                if key not in bowl_agg:
                    bowl_agg[key] = {
                        'bowling_team_id': bowling_team_id,
                        'balls': 0, 'runs': 0, 'wickets': 0,
                        'wides': 0, 'noballs': 0
                    }
                agg = bowl_agg[key]
                agg['balls'] += 1
                agg['runs'] += total_runs
                if is_wicket and wicket_type not in ('run out', 'retired hurt', 'obstructing the field'):
                    agg['wickets'] += 1
                if extra_type == 'wides': agg['wides'] += 1
                if extra_type == 'noballs': agg['noballs'] += 1
        
        # Build insert rows
        batting_rows = []
        for (mid, iid, pid), agg in bat_agg.items():
            sr = (agg['runs'] / agg['balls'] * 100) if agg['balls'] > 0 else 0
            batting_rows.append((
                mid, iid, pid, agg['batting_team_id'],
                agg['runs'], agg['balls'], agg['fours'], agg['sixes'],
                round(sr, 2), agg['is_not_out'], agg['dismissal_type'],
                agg['bowler_id'], agg['fielder_id']
            ))
        
        bowling_rows = []
        for (mid, iid, pid), agg in bowl_agg.items():
            overs = agg['balls'] // 6 + (agg['balls'] % 6) / 10.0
            econ = (agg['runs'] / overs) if overs > 0 else 0
            bowling_rows.append((
                mid, iid, pid, agg['bowling_team_id'],
                round(overs, 1), agg['balls'], 0,
                agg['runs'], agg['wickets'], round(econ, 2),
                agg['wides'], agg['noballs']
            ))
        
        # Insert
        if batting_rows:
            execute_values(cur, '''INSERT INTO match_batting_summary 
                (match_id, innings_id, player_id, batting_team_id,
                 runs, balls, fours, sixes, strike_rate, is_not_out,
                 dismissal_type, bowler_id, fielder_id) VALUES %s 
                ON CONFLICT (match_id, innings_id, player_id) DO NOTHING''',
                batting_rows, page_size=500)
            batting_count += len(batting_rows)
        
        if bowling_rows:
            execute_values(cur, '''INSERT INTO match_bowling_summary
                (match_id, innings_id, player_id, bowling_team_id,
                 overs, balls_bowled, maidens, runs_conceded, wickets,
                 economy, wides, noballs) VALUES %s
                ON CONFLICT (match_id, innings_id, player_id) DO NOTHING''',
                bowling_rows, page_size=500)
            bowling_count += len(bowling_rows)
        
        conn.commit()
        
        for m in chunk_ids:
            processed.add(m)
        
        # Save checkpoint every 5 chunks
        if (chunk_start // chunk_size) % 5 == 0:
            state = {
                'processed_matches': list(processed),
                'batting_count': batting_count,
                'bowling_count': bowling_count
            }
            save_checkpoint(state)
        
        chunk_num = chunk_start // chunk_size + 1
        total_chunks = (len(remaining) + chunk_size - 1) // chunk_size
        print(f'Chunk {chunk_num}/{total_chunks}: {len(chunk_ids)} matches, batting={batting_count}, bowling={bowling_count}')
    
    # Final checkpoint
    state = {
        'processed_matches': list(processed),
        'batting_count': batting_count,
        'bowling_count': bowling_count,
        'complete': True
    }
    save_checkpoint(state)
    
    conn.close()
    print(f'\nDone! Batting rows: {batting_count}, Bowling rows: {bowling_count}')

if __name__ == '__main__':
    generate_scorecards()
