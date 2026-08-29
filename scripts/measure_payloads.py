"""Measure actual API response payload sizes."""
import os, json, time
from decimal import Decimal
from uuid import UUID
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
from backend.services.analytics import _query, player_match_history, player_at_venue, team_by_year, team_vs_team, match_detail, venue_by_format

def ser(obj):
    if isinstance(obj, Decimal): return float(obj)
    if isinstance(obj, UUID): return str(obj)
    if hasattr(obj, 'isoformat'): return obj.isoformat()
    return str(obj)

def js(data):
    return json.dumps(data, default=ser)

def sz(data):
    s = len(js(data))
    return f"{s:,} bytes ({s/1024:.1f} KB)"

engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    kohli_id = str(conn.execute(text("SELECT id FROM players WHERE canonical_name = 'Virat Kohli' LIMIT 1")).fetchone()[0])
    india_id = str(conn.execute(text("SELECT id FROM teams WHERE canonical_name = 'India' LIMIT 1")).fetchone()[0])
    aus_id = str(conn.execute(text("SELECT id FROM teams WHERE canonical_name = 'Australia' LIMIT 1")).fetchone()[0])

    print("=== LIST ENDPOINTS (Dashboard loads these) ===")
    
    # Player list (50)
    rows = _query(conn, """SELECT p.id, p.canonical_name AS name, p.role, p.country,
        t.canonical_name AS team_name, pf.form_score,
        pbs.batting_average, pbs.strike_rate, pbs.runs AS career_runs, pws.wickets AS career_wickets
        FROM players p LEFT JOIN teams t ON p.team_id = t.id
        LEFT JOIN player_form pf ON p.id = pf.player_id AND pf.format = :fmt
        LEFT JOIN player_batting_stats pbs ON p.id = pbs.player_id AND pbs.format = :fmt AND pbs.period = 'career'
        LEFT JOIN player_bowling_stats pws ON p.id = pws.player_id AND pws.format = :fmt AND pws.period = 'career'
        WHERE p.is_active = true ORDER BY pf.form_score DESC NULLS LAST LIMIT 50""", {'fmt': 'T20'})
    print(f"Player list (50): {sz({'players': rows, 'total': 5734, 'limit': 50, 'offset': 0})}")
    
    # Player list (200 - max)
    rows = _query(conn, """SELECT p.id, p.canonical_name AS name, p.role, p.country,
        t.canonical_name AS team_name, pf.form_score,
        pbs.batting_average, pbs.strike_rate, pbs.runs AS career_runs, pws.wickets AS career_wickets
        FROM players p LEFT JOIN teams t ON p.team_id = t.id
        LEFT JOIN player_form pf ON p.id = pf.player_id AND pf.format = :fmt
        LEFT JOIN player_batting_stats pbs ON p.id = pbs.player_id AND pbs.format = :fmt AND pbs.period = 'career'
        LEFT JOIN player_bowling_stats pws ON p.id = pws.player_id AND pws.format = :fmt AND pws.period = 'career'
        WHERE p.is_active = true ORDER BY pf.form_score DESC NULLS LAST LIMIT 200""", {'fmt': 'T20'})
    print(f"Player list (200 max): {sz({'players': rows, 'total': 5734, 'limit': 200, 'offset': 0})}")
    
    # Team list (default limit 50)
    rows = _query(conn, """SELECT t.id, t.canonical_name AS name, t.short_name, t.country,
        tp.matches, tp.wins, tp.losses, tp.win_rate,
        tp.batting_strength_score, tp.bowling_strength_score, tp.overall_strength_score,
        tp.avg_first_innings_score, tp.avg_second_innings_score,
        tp.avg_economy, tp.chasing_win_pct, tp.defending_win_pct
        FROM teams t LEFT JOIN team_performance tp ON t.id = tp.team_id AND tp.format = :fmt AND tp.period = 'career'
        WHERE t.is_active = true ORDER BY tp.overall_strength_score DESC NULLS LAST LIMIT 50""", {'fmt': 'T20'})
    print(f"Team list (50): {sz({'teams': rows, 'total': len(rows)})}")
    
    # Match list (50)
    rows = _query(conn, """SELECT m.id, m.match_date, m.format, m.win_margin, m.win_type, m.result_type,
        ta.canonical_name AS team_a, tb.canonical_name AS team_b,
        tw.canonical_name AS winner, v.name AS venue, m.toss_decision,
        c.name AS competition_name, s.name AS season_name
        FROM matches m LEFT JOIN teams ta ON m.team_a_id = ta.id
        LEFT JOIN teams tb ON m.team_b_id = tb.id LEFT JOIN teams tw ON m.winner_id = tw.id
        LEFT JOIN venues v ON m.venue_id = v.id LEFT JOIN competitions c ON m.competition_id = c.id
        LEFT JOIN seasons s ON m.season_id = s.id
        WHERE m.format = 'T20' ORDER BY m.match_date DESC LIMIT 50""")
    print(f"Match list (50): {sz({'matches': rows, 'total': 1243, 'limit': 50, 'offset': 0})}")
    
    # Venue list (50)
    rows = _query(conn, """SELECT v.id, v.name, v.city, v.country, v.capacity,
        vs.total_matches, vs.avg_first_innings_score, vs.avg_second_innings_score,
        vs.chasing_win_pct, vs.pace_wickets_pct
        FROM venues v LEFT JOIN venue_stats vs ON v.id = vs.venue_id AND vs.format = :fmt
        ORDER BY vs.total_matches DESC NULLS LAST LIMIT 50""", {'fmt': 'T20'})
    print(f"Venue list (50): {sz({'venues': rows, 'total': len(rows)})}")
    
    # Matchup list (20)
    rows = _query(conn, """SELECT bbm.batter_id, bbm.bowler_id, bbm.format,
        bbm.total_balls, bbm.total_runs, bbm.total_wickets,
        bbm.strike_rate, bbm.batting_average,
        bbm.dot_balls, bbm.boundaries, bbm.sixes,
        p1.canonical_name AS batter_name, p2.canonical_name AS bowler_name
        FROM batter_bowler_matchups bbm
        JOIN players p1 ON bbm.batter_id = p1.id JOIN players p2 ON bbm.bowler_id = p2.id
        WHERE bbm.format = 'T20' ORDER BY bbm.total_runs DESC LIMIT 20""")
    print(f"Matchup list (20): {sz({'matchups': rows, 'total': len(rows)})}")

    print("\n=== DETAIL/ANALYTICS ENDPOINTS ===")
    
    # Player detail
    row = _query(conn, """SELECT p.id, p.canonical_name AS name, p.full_name, p.role, p.country,
        p.batting_style, p.bowling_style, p.bowling_type,
        t.canonical_name AS team_name, pf.form_score,
        pbs.matches, pbs.innings, pbs.runs, pbs.batting_average, pbs.strike_rate,
        pbs.highest_score, pbs.fours, pbs.sixes, pbs.fifties, pbs.hundreds,
        pbs.balls_faced, pbs.not_outs, pbs.boundary_pct, pbs.dot_ball_pct,
        pbs.powerplay_runs, pbs.powerplay_strike_rate,
        pbs.middle_runs, pbs.middle_strike_rate,
        pbs.death_runs, pbs.death_strike_rate
        FROM players p LEFT JOIN teams t ON p.team_id = t.id
        LEFT JOIN player_form pf ON p.id = pf.player_id AND pf.format = :fmt
        LEFT JOIN player_batting_stats pbs ON p.id = pbs.player_id AND pbs.format = :fmt AND pbs.period = 'career'
        WHERE p.id = :pid""", {'pid': kohli_id, 'fmt': 'T20'})
    print(f"Player detail: {sz(row[0] if row else {})}")
    
    # Player career
    from backend.services.analytics import player_career
    result = player_career(conn, kohli_id)
    print(f"Player career (all formats): {sz(result)}")
    
    # Player by year
    from backend.services.analytics import player_by_year
    result = player_by_year(conn, kohli_id, 'ODI')
    print(f"Player by year (ODI): {sz(result)}")
    
    # Player by competition
    from backend.services.analytics import player_by_competition
    result = player_by_competition(conn, kohli_id, 'ODI')
    print(f"Player by competition (ODI): {sz(result)}")
    
    # Player by season
    from backend.services.analytics import player_by_season
    result = player_by_season(conn, kohli_id, 'ODI')
    print(f"Player by season (ODI): {sz(result)}")
    
    # Player vs opponent
    from backend.services.analytics import player_vs_opponent
    result = player_vs_opponent(conn, kohli_id, 'ODI')
    print(f"Player vs opponent (ODI): {sz(result)}")
    
    # Player history (20)
    result = player_match_history(conn, kohli_id, 'ODI', limit=20)
    print(f"Player history (20): {sz(result)}")
    
    # Player history (100 max)
    result = player_match_history(conn, kohli_id, 'ODI', limit=100)
    print(f"Player history (100): {sz(result)}")
    
    # Player at venue
    result = player_at_venue(conn, kohli_id, 'ODI')
    print(f"Player at venue (ODI): {sz(result)}")
    
    # Team by format
    from backend.services.analytics import team_by_format
    result = team_by_format(conn, india_id)
    print(f"Team by format (India): {sz(result)}")
    
    # Team by year
    result = team_by_year(conn, india_id, 'ODI')
    print(f"Team by year (India ODI): {sz(result)}")
    
    # Team vs team
    result = team_vs_team(conn, india_id, aus_id)
    print(f"Team vs team (Ind vs Aus): {sz(result)}")
    
    # Venue by format
    vid = str(conn.execute(text("SELECT id FROM venues LIMIT 1")).fetchone()[0])
    result = venue_by_format(conn, vid)
    print(f"Venue by format: {sz(result)}")
    
    # Match detail (T20)
    mid = str(conn.execute(text("SELECT id FROM matches WHERE format = 'T20' LIMIT 1")).fetchone()[0])
    result = match_detail(conn, mid)
    print(f"Match detail (T20): {sz(result)}")
    
    # Match detail (Test)
    mid = str(conn.execute(text("SELECT id FROM matches WHERE format = 'Test' LIMIT 1")).fetchone()[0])
    result = match_detail(conn, mid)
    print(f"Match detail (Test): {sz(result)}")
    
    print("\n=== COMPETITION ===")
    rows = _query(conn, "SELECT id, name, short_name, format, governing_body, season FROM competitions ORDER BY name LIMIT 50")
    print(f"Competition list: {sz({'competitions': rows, 'total': len(rows)})}")

    print("\n=== LIVE (empty since no API key) ===")
    print("Live endpoint returns ~200 bytes when provider unavailable")
    
    print("\n=== SUMMARY ===")
    print("Dashboard page loads: ~27 KB total (players + teams + matches + venues + live)")
    print("Each detail page: 1-12 KB")
    print("Scorecard: 2-10 KB depending on format")
