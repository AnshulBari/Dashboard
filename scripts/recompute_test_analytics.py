"""Recompute Test analytics from all deliveries in chunks with retry."""
import sys, os, time, pickle
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import psycopg2
import pandas as pd

CHECKPOINT_DIR = Path("data/test_analytics_checkpoint")
CHECKPOINT_DIR.mkdir(exist_ok=True)

def get_conn():
    import os
    return psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=10)

def load_chunk_with_retry(match_ids, max_retries=3):
    """Load deliveries with retry on SSL errors."""
    for attempt in range(max_retries):
        try:
            conn = get_conn()
            placeholders = ','.join(['%s'] * len(match_ids))
            q = f"""SELECT d.id, d.match_id, d.innings_id, d.striker_id, d.bowler_id,
                           d.total_runs, d.is_wicket, d.over_number,
                           i.batting_team_id, i.bowling_team_id,
                           m.venue_id, m.format
                    FROM deliveries d
                    JOIN innings i ON d.innings_id = i.id
                    JOIN matches m ON d.match_id = m.id
                    WHERE d.match_id IN ({placeholders})"""
            df = pd.read_sql(q, conn, params=match_ids)
            conn.close()
            return df
        except Exception as e:
            print(f"    Attempt {attempt+1} failed: {e}")
            time.sleep(2)
            if attempt < max_retries - 1:
                continue
            raise

def compute_batting(df):
    bat = df.groupby('striker_id').agg(
        matches=('match_id', 'nunique'),
        innings=('innings_id', 'nunique'),
        runs=('total_runs', 'sum'),
        balls=('id', 'count'),
        fours=('total_runs', lambda x: (x == 4).sum()),
        sixes=('total_runs', lambda x: (x == 6).sum()),
        fifties=('total_runs', lambda x: ((x >= 50) & (x < 100)).sum()),
        hundreds=('total_runs', lambda x: (x >= 100).sum()),
    ).reset_index()
    bat['format'] = 'Test'
    bat['avg'] = bat['runs'] / bat['innings'].replace(0, 1)
    bat['sr'] = bat['runs'] / bat['balls'].replace(0, 1) * 100
    return bat

def compute_bowling(df):
    bdf = df[df['bowler_id'].notna()].copy()
    bowl = bdf.groupby('bowler_id').agg(
        matches=('match_id', 'nunique'),
        innings=('innings_id', 'nunique'),
        balls_bowled=('id', 'count'),
        runs_conceded=('total_runs', 'sum'),
        wickets=('is_wicket', 'sum'),
    ).reset_index()
    bowl['format'] = 'Test'
    bowl['avg'] = bowl['runs_conceded'] / bowl['wickets'].replace(0, 1)
    bowl['economy'] = bowl['runs_conceded'] / (bowl['balls_bowled'] / 6).replace(0, 1)
    return bowl

def merge_chunks(all_dfs, group_col):
    if not all_dfs:
        return pd.DataFrame()
    combined = pd.concat(all_dfs)
    agg_cols = {c: 'sum' for c in combined.columns if c not in [group_col, 'format']}
    merged = combined.groupby([group_col, 'format']).agg(agg_cols).reset_index()
    return merged

def main():
    phase_file = CHECKPOINT_DIR / "phase.txt"
    phase = 0
    if phase_file.exists():
        phase = int(phase_file.read_text().strip())
    
    CHUNK = 20  # Smaller chunks for reliability
    
    if phase == 0:
        # Get match IDs
        conn = get_conn()
        match_df = pd.read_sql("SELECT id FROM matches WHERE format='Test' ORDER BY match_date", conn)
        match_ids = match_df['id'].tolist()
        conn.close()
        print(f"Total Test matches: {len(match_ids)}")
        
        all_bat = []
        all_bowl = []
        start_time = time.time()
        chunk_idx_file = CHECKPOINT_DIR / "chunk_idx.txt"
        start_chunk = 0
        if chunk_idx_file.exists():
            start_chunk = int(chunk_idx_file.read_text().strip())
        
        for i in range(start_chunk * CHUNK, len(match_ids), CHUNK):
            chunk = match_ids[i:i+CHUNK]
            chunk_num = i // CHUNK + 1
            t0 = time.time()
            try:
                df = load_chunk_with_retry(chunk)
            except Exception as e:
                print(f"  FATAL chunk {chunk_num}: {e}")
                # Save progress so far
                if all_bat:
                    bat_checkpoint = CHECKPOINT_DIR / f"bat_partial_{chunk_num}.pkl"
                    pd.concat(all_bat).to_pickle(str(bat_checkpoint))
                    pd.concat(all_bowl).to_pickle(str(CHECKPOINT_DIR / f"bowl_partial_{chunk_num}.pkl"))
                chunk_idx_file.write_text(str(start_chunk + (i - start_chunk * CHUNK) // CHUNK))
                return
            t1 = time.time()
            bat = compute_batting(df)
            bowl = compute_bowling(df)
            all_bat.append(bat)
            all_bowl.append(bowl)
            print(f"  Chunk {chunk_num}/{(len(match_ids)+CHUNK-1)//CHUNK}: {len(df)} dels, {len(bat)} batters ({t1-t0:.1f}s)")
        
        elapsed = time.time() - start_time
        print(f"\nAll chunks loaded in {elapsed:.1f}s")
        
        bat_final = merge_chunks(all_bat, 'striker_id')
        bowl_final = merge_chunks(all_bowl, 'bowler_id')
        bat_final['avg'] = bat_final['runs'] / bat_final['innings'].replace(0, 1)
        bat_final['sr'] = bat_final['runs'] / bat_final['balls'].replace(0, 1) * 100
        bowl_final['avg'] = bowl_final['runs_conceded'] / bowl_final['wickets'].replace(0, 1)
        bowl_final['economy'] = bowl_final['runs_conceded'] / (bowl_final['balls_bowled'] / 6).replace(0, 1)
        
        bat_final.to_pickle(str(CHECKPOINT_DIR / "batting.pkl"))
        bowl_final.to_pickle(str(CHECKPOINT_DIR / "bowling.pkl"))
        phase_file.write_text("1")
        print(f"Batting: {len(bat_final)} players, Bowling: {len(bowl_final)} players")
        print("Phase 0 complete. Run again to write to DB.")
    
    elif phase == 1:
        bat_final = pd.read_pickle(str(CHECKPOINT_DIR / "batting.pkl"))
        bowl_final = pd.read_pickle(str(CHECKPOINT_DIR / "bowling.pkl"))
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM player_batting_stats WHERE format='Test'")
        cur.execute("DELETE FROM player_bowling_stats WHERE format='Test'")
        conn.commit()
        print("Cleared existing Test analytics")
        
        # Write in batches using execute_values
        from psycopg2.extras import execute_values
        
        bat_rows = []
        for _, row in bat_final.iterrows():
            bat_rows.append((
                str(row['striker_id']), 'Test', int(row['matches']), int(row['innings']),
                int(row['runs']), int(row['balls']), int(row['fours']), int(row['sixes']),
                int(row['fifties']), int(row['hundreds']), round(float(row['avg']),2), round(float(row['sr']),2)
            ))
        
        execute_values(cur, """INSERT INTO player_batting_stats 
            (player_id, format, matches_played, innings, runs, balls_faced, fours, sixes, fifties, hundreds, average, strike_rate)
            VALUES %s""", bat_rows, page_size=200)
        conn.commit()
        print(f"Wrote {len(bat_rows)} batting stats")
        
        bowl_rows = []
        for _, row in bowl_final.iterrows():
            bowl_rows.append((
                str(row['bowler_id']), 'Test', int(row['matches']), int(row['innings']),
                int(row['balls_bowled']), int(row['runs_conceded']), int(row['wickets']),
                round(float(row['avg']),2), round(float(row['economy']),2)
            ))
        
        execute_values(cur, """INSERT INTO player_bowling_stats
            (player_id, format, matches_played, innings, balls_bowled, runs_conceded, wickets_taken, average, economy_rate)
            VALUES %s""", bowl_rows, page_size=200)
        conn.commit()
        print(f"Wrote {len(bowl_rows)} bowling stats")
        
        conn.close()
        phase_file.write_text("2")
        print("Phase 1 complete!")

if __name__ == "__main__":
    main()
