"""
Dashboard API Routes
====================

Consolidated endpoint for the main dashboard view.
Reduces 5+ separate API calls into a single response.

The dashboard needs:
1. Entity counts (players, teams, matches, venues)
2. Top players by form score
3. Recent matches
4. Top venues
5. Live match status

All served in one response with conservative limits.
"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.utils.database import get_db

router = APIRouter()


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return dict(row._mapping)


@router.get("/summary")
async def dashboard_summary(
    format: Optional[str] = Query(None, description="Filter by format"),
    db: Session = Depends(get_db),
):
    """
    Consolidated dashboard summary endpoint.
    
    Returns entity counts, top players, recent matches, and top venues
    in a single response. Designed to replace 5 separate API calls
    that the dashboard previously made.
    
    This significantly reduces:
    - Supabase egress (1 request vs 5)
    - Latency (1 round trip vs 5)
    - Database connection pressure
    """
    target_format = format or "T20"
    
    # 1. Entity counts (single efficient query)
    counts = db.execute(
        text("""
            SELECT
                (SELECT COUNT(*) FROM players WHERE is_active = true) AS players,
                (SELECT COUNT(*) FROM teams WHERE is_active = true) AS teams,
                (SELECT COUNT(*) FROM matches) AS matches,
                (SELECT COUNT(*) FROM venues) AS venues
        """)
    ).fetchone()
    
    # 2. Top players by form score (limited to 10)
    top_players = db.execute(
        text("""
            SELECT
                p.id, p.canonical_name AS name, p.role, p.country,
                t.canonical_name AS team_name,
                pf.form_score
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN player_form pf ON p.id = pf.player_id AND pf.format = :fmt
            WHERE p.is_active = true AND pf.form_score IS NOT NULL
            ORDER BY pf.form_score DESC
            LIMIT 10
        """),
        {"fmt": target_format},
    ).fetchall()
    
    # 3. Recent matches (limited to 8)
    recent_matches = db.execute(
        text("""
            SELECT
                m.id, m.match_date, m.format,
                ta.canonical_name AS team_a,
                tb.canonical_name AS team_b,
                tw.canonical_name AS winner,
                v.name AS venue,
                m.win_margin, m.win_type, m.result_type,
                c.name AS competition_name
            FROM matches m
            LEFT JOIN teams ta ON m.team_a_id = ta.id
            LEFT JOIN teams tb ON m.team_b_id = tb.id
            LEFT JOIN teams tw ON m.winner_id = tw.id
            LEFT JOIN venues v ON m.venue_id = v.id
            LEFT JOIN competitions c ON m.competition_id = c.id
            ORDER BY m.match_date DESC
            LIMIT 8
        """),
    ).fetchall()
    
    # 4. Top venues by match count (limited to 6)
    top_venues = db.execute(
        text("""
            SELECT
                v.id, v.name, v.city, v.country,
                vs.total_matches, vs.avg_first_innings_score,
                vs.chasing_win_pct
            FROM venues v
            LEFT JOIN venue_stats vs ON v.id = vs.venue_id AND vs.format = :fmt
            WHERE vs.total_matches IS NOT NULL
            ORDER BY vs.total_matches DESC
            LIMIT 6
        """),
        {"fmt": target_format},
    ).fetchall()
    
    # Build response
    players_list = []
    for row in top_players:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        players_list.append(d)
    
    matches_list = []
    for row in recent_matches:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        # Build result string
        result_type = d.get("result_type", "win")
        if result_type == "draw":
            d["result"] = "Draw"
        elif result_type == "tie":
            d["result"] = "Tie"
        elif result_type == "no_result":
            d["result"] = "No result"
        elif d.get("winner"):
            margin = f" by {d['win_margin']} {d['win_type']}" if d.get("win_margin") else ""
            d["result"] = f"{d['winner']} won{margin}"
        else:
            d["result"] = "No result"
        matches_list.append(d)
    
    venues_list = []
    for row in top_venues:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        venues_list.append(d)
    
    return {
        "counts": {
            "players": counts[0] if counts else 0,
            "teams": counts[1] if counts else 0,
            "matches": counts[2] if counts else 0,
            "venues": counts[3] if counts else 0,
        },
        "top_players": players_list,
        "recent_matches": matches_list,
        "top_venues": venues_list,
        "format": target_format,
    }
