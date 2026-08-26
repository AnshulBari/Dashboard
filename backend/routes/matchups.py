"""
Matchup API Routes
==================

Endpoints for batter-bowler matchup analytics.
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


@router.get("/")
async def list_matchups(
    format: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List top batter-bowler matchups by total runs scored."""
    target_format = format or "T20"

    rows = db.execute(
        text("""
            SELECT
                bbm.batter_id, bbm.bowler_id, bbm.format,
                bbm.total_balls, bbm.total_runs, bbm.total_wickets,
                bbm.strike_rate, bbm.batting_average,
                bbm.dot_balls, bbm.boundaries, bbm.sixes,
                p1.canonical_name AS batter_name,
                p2.canonical_name AS bowler_name
            FROM batter_bowler_matchups bbm
            JOIN players p1 ON bbm.batter_id = p1.id
            JOIN players p2 ON bbm.bowler_id = p2.id
            WHERE bbm.format = :fmt
            ORDER BY bbm.total_runs DESC
            LIMIT :limit
        """),
        {"fmt": target_format, "limit": limit},
    ).fetchall()

    matchups = []
    for row in rows:
        d = _row_to_dict(row)
        d["batter_id"] = str(d["batter_id"])
        d["bowler_id"] = str(d["bowler_id"])
        matchups.append(d)

    return {"matchups": matchups, "total": len(matchups)}


@router.get("/{batter_id}/{bowler_id}")
async def get_matchup(
    batter_id: str,
    bowler_id: str,
    format: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get head-to-head matchup between a specific batter and bowler."""
    target_format = format or "T20"

    row = db.execute(
        text("""
            SELECT
                bbm.batter_id, bbm.bowler_id, bbm.format,
                bbm.total_balls, bbm.total_runs, bbm.total_wickets,
                bbm.strike_rate, bbm.batting_average,
                bbm.dot_balls, bbm.boundaries, bbm.sixes,
                p1.canonical_name AS batter_name,
                p2.canonical_name AS bowler_name
            FROM batter_bowler_matchups bbm
            JOIN players p1 ON bbm.batter_id = p1.id
            JOIN players p2 ON bbm.bowler_id = p2.id
            WHERE bbm.batter_id = :batter_id
                AND bbm.bowler_id = :bowler_id
                AND bbm.format = :fmt
        """),
        {"batter_id": batter_id, "bowler_id": bowler_id, "fmt": target_format},
    ).fetchone()

    if not row:
        return {
            "batter_id": batter_id,
            "bowler_id": bowler_id,
            "format": target_format,
            "total_balls": 0,
            "total_runs": 0,
            "total_wickets": 0,
            "strike_rate": 0,
            "average": 0,
            "dot_balls": 0,
            "boundaries": 0,
            "sixes": 0,
            "batter_name": None,
            "bowler_name": None,
            "message": "No matchup data found for this pair",
        }

    d = _row_to_dict(row)
    d["batter_id"] = str(d["batter_id"])
    d["bowler_id"] = str(d["bowler_id"])
    return d
