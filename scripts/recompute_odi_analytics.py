"""Recompute ODI analytics from full corpus with checkpoint support.

Usage:
    python scripts/recompute_odi_analytics.py [--resume]

Saves intermediate chunk results to data/odi_analytics_chunks/ as pickle files.
On --resume, skips already-computed chunks.
Final merge+write happens only after all chunks are complete.
"""
from dotenv import load_dotenv
load_dotenv()

import os, sys, time, pickle
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, '.')
from data_pipeline.pipeline.db_manager import DatabaseManager
from data_pipeline.pipeline.analytics import (
    compute_player_batting_stats, compute_player_bowling_stats,
    compute_player_form_scores, compute_team_performance,
    compute_venue_stats, compute_matchups
)
from data_pipeline.batch.runner import BatchRunner
from data_pipeline.batch.manifest import BatchManifest

CHUNK_DIR = 'data/odi_analytics_chunks'
os.makedirs(CHUNK_DIR, exist_ok=True)

resume = '--resume' in sys.argv

db = DatabaseManager()
db.initialize()
manifest = BatchManifest(db.engine)
runner = BatchRunner(db, manifest)

with db.engine.connect() as conn:
    match_ids = [r[0] for r in conn.execute(
        text('SELECT id FROM matches WHERE format=:fmt ORDER BY match_date'), {'fmt':'ODI'}
    ).fetchall()]
print(f'ODI matches: {len(match_ids)}')

def load_chunk(engine, cids):
    ph = ','.join([f':id{j}' for j in range(len(cids))])
    params = {f'id{j}': mid for j, mid in enumerate(cids)}
    q = f'''SELECT m.external_id as match_id, m.format, m.match_date, m.venue_id, m.team_a_id, m.team_b_id,
        m.toss_decision, m.winner_id, m.win_margin, m.win_type, m.result_type,
        i.innings_number, i.batting_team_id, i.bowling_team_id, i.declared, i.all_out, i.follow_on,
        d.over_number, d.ball_in_over, d.runs_bat as runs_batter, d.runs_extras, d.total_runs as runs_total,
        d.extra_type, d.is_wicket, d.wicket_type,
        p1.canonical_name as batter, p2.canonical_name as bowler, p3.canonical_name as non_striker,
        p4.canonical_name as dismissed_player, t1.canonical_name as batting_team, t2.canonical_name as bowling_team,
        t3.canonical_name as team_a, t4.canonical_name as team_b, t1.canonical_name as toss_winner,
        v.name as venue, v.city, m.win_margin as win_by_runs, m.win_type as win_by_wickets_type,
        t5.canonical_name as winner
        FROM deliveries d JOIN innings i ON d.innings_id=i.id JOIN matches m ON d.match_id=m.id
        LEFT JOIN players p1 ON d.striker_id=p1.id LEFT JOIN players p2 ON d.bowler_id=p2.id
        LEFT JOIN players p3 ON d.non_striker_id=p3.id LEFT JOIN players p4 ON d.dismissed_player_id=p4.id
        LEFT JOIN teams t1 ON i.batting_team_id=t1.id LEFT JOIN teams t2 ON i.bowling_team_id=t2.id
        LEFT JOIN teams t3 ON m.team_a_id=t3.id LEFT JOIN teams t4 ON m.team_b_id=t4.id
        LEFT JOIN teams t5 ON m.winner_id=t5.id LEFT JOIN venues v ON m.venue_id=v.id
        WHERE m.id IN ({ph})'''
    with engine.connect() as conn:
        return pd.read_sql(text(q), conn, params=params)

CHUNK = 50
total_chunks = (len(match_ids) - 1) // CHUNK + 1

# Phase 1: Compute chunks (with checkpointing)
grand_start = time.time()

for i in range(0, len(match_ids), CHUNK):
    cids = match_ids[i:i+CHUNK]
    chunk_num = i // CHUNK + 1
    pickle_path = os.path.join(CHUNK_DIR, f'chunk_{chunk_num:03d}.pkl')

    if resume and os.path.exists(pickle_path):
        print(f'Chunk {chunk_num}/{total_chunks}: CACHED')
        continue

    t0 = time.time()
    df = load_chunk(db.engine, cids)
    lt = time.time()-t0
    if len(df) == 0:
        print(f'Chunk {chunk_num}/{total_chunks}: EMPTY - skip')
        continue

    t1 = time.time()
    chunk_analytics = {
        'batting': compute_player_batting_stats(df),
        'bowling': compute_player_bowling_stats(df),
        'form': compute_player_form_scores(df),
        'team': compute_team_performance(df),
        'venue': compute_venue_stats(df),
        'matchups': compute_matchups(df),
    }
    ct = time.time()-t1

    with open(pickle_path, 'wb') as f:
        pickle.dump(chunk_analytics, f)

    elapsed = time.time()-grand_start
    print(f'Chunk {chunk_num}/{total_chunks}: {len(df)}d ({lt:.1f}+{ct:.1f}s) [{elapsed:.0f}s]')

load_time = time.time()-grand_start
print(f'\nAll chunks computed in {load_time:.1f}s')

# Phase 2: Merge all cached results
print('Merging all cached chunks...')
all_bat, all_bowl, all_frm, all_tm, all_ven, all_mch = [], [], [], [], [], []

for i in range(0, len(match_ids), CHUNK):
    chunk_num = i // CHUNK + 1
    pickle_path = os.path.join(CHUNK_DIR, f'chunk_{chunk_num:03d}.pkl')
    if not os.path.exists(pickle_path):
        continue
    with open(pickle_path, 'rb') as f:
        ca = pickle.load(f)
    all_bat.append(ca['batting'])
    all_bowl.append(ca['bowling'])
    all_frm.append(ca['form'])
    all_tm.append(ca['team'])
    all_ven.append(ca['venue'])
    all_mch.append(ca['matchups'])

bat = pd.concat(all_bat).drop_duplicates(subset=['player_id','format'], keep='last')
bowl = pd.concat(all_bowl).drop_duplicates(subset=['player_id','format'], keep='last')
frm = pd.concat(all_frm).drop_duplicates(subset=['player_id','format'], keep='last')
tm = pd.concat(all_tm).drop_duplicates(subset=['team_id','format'], keep='last')
ven = pd.concat(all_ven).drop_duplicates(subset=['venue_id','format'], keep='last')
mch = pd.concat(all_mch) if all_mch else pd.DataFrame()
if not mch.empty and 'batter_id' in mch.columns:
    num_cols = mch.select_dtypes(include=['number']).columns.tolist()
    gcols = ['batter_id','bowler_id','format']
    agg = {c:'sum' for c in num_cols if c not in gcols}
    if agg:
        mch = mch.groupby(gcols, as_index=False).agg(agg)

print(f'Merged: bat={len(bat)} bowl={len(bowl)} frm={len(frm)} tm={len(tm)} ven={len(ven)} mch={len(mch)}')

# Phase 3: Write to DB
analytics = {'batting':bat,'bowling':bowl,'form':frm,'team':tm,'venue':ven,'matchups':mch}
t0 = time.time()
runner._write_analytics(analytics, 'ODI')
print(f'Written to DB in {time.time()-t0:.1f}s')
print(f'Grand total: {time.time()-grand_start:.1f}s')
