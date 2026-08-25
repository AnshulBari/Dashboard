"""
Player API Routes
=================

Endpoints for player intelligence data.
Queries the database for precomputed analytical results.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.utils.database import get_db

router = APIRouter()


def _row_to_dict(row) -> dict:
    """Convert a SQLAlchemy Row to a dict."""
    if row is None:
        return None
    return dict(row._mapping)


@router.get("/")
async def list_players(
    format: Optional[str] = Query(None, description="Filter by format (T20I, ODI, Test)"),
    role: Optional[str] = Query(None, description="Filter by role"),
    country: Optional[str] = Query(None, description="Filter by country"),
    sort_by: str = Query("form_score", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List players with optional filtering and sorting.

    Returns player summary including form score, batting/bowling stats.
    """
    # Default to T20 (IPL) if no format specified
    target_format = format or "T20"

    # Build query with optional filters
    query = text("""
        SELECT
            p.id,
            p.canonical_name AS name,
            p.role,
            p.country,
            t.canonical_name AS team_name,
            pf.form_score,
            pbs.batting_average,
            pbs.strike_rate,
            pbs.runs AS career_runs,
            pws.wickets AS career_wickets
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        LEFT JOIN player_form pf ON p.id = pf.player_id AND pf.format = :fmt
        LEFT JOIN player_batting_stats pbs ON p.id = pbs.player_id AND pbs.format = :fmt AND pbs.period = 'career'
        LEFT JOIN player_bowling_stats pws ON p.id = pws.player_id AND pws.format = :fmt AND pws.period = 'career'
        WHERE p.is_active = true
    """)
    params = {"fmt": target_format}

    if role:
        query = text(str(query) + " AND p.role = :role")
        params["role"] = role

    if country:
        query = text(str(query) + " AND p.country = :country")
        params["country"] = country

    # Count total
    count_query = text(f"SELECT COUNT(*) FROM ({str(query)}) sub")
    total = db.execute(count_query, params).scalar() or 0

    # Sort
    sort_column = {
        "form_score": "pf.form_score",
        "name": "p.canonical_name",
        "runs": "pbs.runs",
        "wickets": "pws.wickets",
        "batting_average": "pbs.batting_average",
    }.get(sort_by, "pf.form_score")

    order = "DESC" if sort_order.lower() == "desc" else "ASC"
    query = text(str(query) + f" ORDER BY {sort_column} {order} NULLS LAST")
    query = text(str(query) + " LIMIT :limit OFFSET :offset")
    params["limit"] = limit
    params["offset"] = offset

    rows = db.execute(query, params).fetchall()

    players = []
    for row in rows:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        players.append(d)

    return {
        "players": players,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{player_id}")
async def get_player(player_id: str, format: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """
    Get detailed player information.
    """
    # Try UUID format
    try:
        from uuid import UUID
        UUID(player_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid player ID format")

    target_format = format or "T20"

    row = db.execute(
        text("""
            SELECT
                p.id, p.canonical_name AS name, p.full_name, p.role, p.country,
                p.batting_style, p.bowling_style, p.bowling_type,
                t.canonical_name AS team_name,
                pf.form_score,
                pbs.matches, pbs.innings, pbs.runs, pbs.batting_average, pbs.strike_rate,
                pbs.highest_score, pbs.fours, pbs.sixes, pbs.fifties, pbs.hundreds,
                pbs.balls_faced, pbs.not_outs, pbs.boundary_pct, pbs.dot_ball_pct,
                pbs.powerplay_runs, pbs.powerplay_strike_rate,
                pbs.middle_runs, pbs.middle_strike_rate,
                pbs.death_runs, pbs.death_strike_rate
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN player_form pf ON p.id = pf.player_id AND pf.format = :fmt
            LEFT JOIN player_batting_stats pbs ON p.id = pbs.player_id AND pbs.format = :fmt AND pbs.period = 'career'
            WHERE p.id = :pid
        """),
        {"pid": player_id, "fmt": target_format}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Player not found")

    d = _row_to_dict(row)
    d["id"] = str(d["id"])

    # Get bowling stats if applicable
    bowling = db.execute(
        text("""
            SELECT matches, innings, overs, balls_bowled, wickets, runs_conceded,
                   bowling_average, strike_rate, economy, dot_ball_pct
            FROM player_bowling_stats
            WHERE player_id = :pid AND format = :fmt AND period = 'career'
        """),
        {"pid": player_id, "fmt": target_format}
    ).fetchone()

    if bowling:
        d["bowling"] = _row_to_dict(bowling)

    return d


@router.get("/{player_id}/form")
async def get_player_form(player_id: str, format: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get player form score with component breakdown."""
    target_format = format or "T20"

    row = db.execute(
        text("""
            SELECT
                player_id, form_score,
                recent_performance_component, consistency_component,
                opposition_strength_component, venue_performance_component,
                match_situation_component, efficiency_component,
                recent_innings_count
            FROM player_form
            WHERE player_id = :pid AND format = :fmt
        """),
        {"pid": player_id, "fmt": target_format}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Form data not found")

    d = _row_to_dict(row)
    d["player_id"] = str(d["player_id"])

    return {
        "player_id": d["player_id"],
        "form_score": d["form_score"],
        "components": {
            "recent_performance": {"score": d["recent_performance_component"], "weight": 0.35},
            "consistency": {"score": d["consistency_component"], "weight": 0.20},
            "opposition_strength": {"score": d["opposition_strength_component"], "weight": 0.15},
            "venue_performance": {"score": d["venue_performance_component"], "weight": 0.10},
            "match_situation": {"score": d["match_situation_component"], "weight": 0.10},
            "efficiency": {"score": d["efficiency_component"], "weight": 0.10},
        },
        "recent_innings_count": d["recent_innings_count"],
    }


@router.get("/{player_id}/batting")
async def get_player_batting(
    player_id: str,
    format: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get detailed batting statistics for a player."""
    target_format = format or "T20"
    target_period = period or "career"

    row = db.execute(
        text("""
            SELECT * FROM player_batting_stats
            WHERE player_id = :pid AND format = :fmt AND period = :period
        """),
        {"pid": player_id, "fmt": target_format, "period": target_period}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Batting stats not found")

    return _row_to_dict(row)


@router.get("/{player_id}/bowling")
async def get_player_bowling(
    player_id: str,
    format: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get detailed bowling statistics for a player."""
    target_format = format or "T20"
    target_period = period or "career"

    row = db.execute(
        text("""
            SELECT * FROM player_bowling_stats
            WHERE player_id = :pid AND format = :fmt AND period = :period
        """),
        {"pid": player_id, "fmt": target_format, "period": target_period}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Bowling stats not found")

    return _row_to_dict(row)


@router.get("/{player_id}/matchups")
async def get_player_matchups(
    player_id: str,
    type: str = Query("batting", description="Matchup type: batting or bowling"),
    format: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get player matchup data against specific opponents."""
    target_format = format or "T20"

    if type == "batting":
        rows = db.execute(
            text("""
                SELECT
                    bbm.bowler_id AS opponent_id,
                    p.canonical_name AS opponent_name,
                    bbm.total_balls, bbm.total_runs, bbm.total_wickets,
                    bbm.strike_rate, bbm.batting_average,
                    bbm.dot_balls, bbm.boundaries, bbm.sixes
                FROM batter_bowler_matchups bbm
                JOIN players p ON bbm.bowler_id = p.id
                WHERE bbm.batter_id = :pid AND bbm.format = :fmt
                ORDER BY bbm.total_runs DESC
                LIMIT 20
            """),
            {"pid": player_id, "fmt": target_format}
        ).fetchall()
    else:
        rows = db.execute(
            text("""
                SELECT
                    bbm.batter_id AS opponent_id,
                    p.canonical_name AS opponent_name,
                    bbm.total_balls, bbm.total_runs, bbm.total_wickets,
                    bbm.strike_rate, bbm.batting_average,
                    bbm.dot_balls, bbm.boundaries, bbm.sixes
                FROM batter_bowler_matchups bbm
                JOIN players p ON bbm.batter_id = p.id
                WHERE bbm.bowler_id = :pid AND bbm.format = :fmt
                ORDER BY bbm.total_wickets DESC
                LIMIT 20
            """),
            {"pid": player_id, "fmt": target_format}
        ).fetchall()

    return {
        "player_id": player_id,
        "type": type,
        "matchups": [{k: str(v) if k == "opponent_id" else v for k, v in _row_to_dict(r).items()} for r in rows],
    }
