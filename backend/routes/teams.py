"""
Team API Routes
===============

Endpoints for team intelligence data.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.utils.database import get_db

router = APIRouter()


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return dict(row._mapping)


@router.get("/")
async def list_teams(
    format: Optional[str] = Query(None),
    sort_by: str = Query("overall_strength", description="Sort field"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all teams with strength ratings."""
    target_format = format or "T20"

    rows = db.execute(
        text("""
            SELECT
                t.id, t.canonical_name AS name, t.short_name, t.country,
                tp.matches, tp.wins, tp.losses, tp.win_rate,
                tp.batting_strength_score, tp.bowling_strength_score, tp.overall_strength_score,
                tp.avg_first_innings_score, tp.avg_second_innings_score,
                tp.avg_economy, tp.chasing_win_pct, tp.defending_win_pct
            FROM teams t
            LEFT JOIN team_performance tp ON t.id = tp.team_id AND tp.format = :fmt AND tp.period = 'career'
            WHERE t.is_active = true
            ORDER BY tp.overall_strength_score DESC NULLS LAST
            LIMIT :limit
        """),
        {"fmt": target_format, "limit": limit}
    ).fetchall()

    teams = []
    for row in rows:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        teams.append(d)

    return {"teams": teams, "total": len(teams)}


@router.get("/{team_id}")
async def get_team(team_id: str, format: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get detailed team information and analytics."""
    target_format = format or "T20"
    row = db.execute(
        text("""
            SELECT
                t.id, t.canonical_name AS name, t.short_name, t.country,
                tp.matches, tp.wins, tp.losses, tp.win_rate,
                tp.batting_strength_score, tp.bowling_strength_score, tp.overall_strength_score
            FROM teams t
            LEFT JOIN team_performance tp ON t.id = tp.team_id AND tp.format = :fmt AND tp.period = 'career'
            WHERE t.id = :tid
        """),
        {"tid": team_id, "fmt": target_format}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Team not found")

    d = _row_to_dict(row)
    d["id"] = str(d["id"])
    return d


@router.get("/{team_id}/analytics")
async def get_team_analytics(
    team_id: str,
    format: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get comprehensive team analytics."""
    target_format = format or "T20"
    target_period = period or "career"

    row = db.execute(
        text("""
            SELECT * FROM team_performance
            WHERE team_id = :tid AND format = :fmt AND period = :period
        """),
        {"tid": team_id, "fmt": target_format, "period": target_period}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Team analytics not found")

    return _row_to_dict(row)
