"""
Venue API Routes
================

Endpoints for venue intelligence data.
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
async def list_venues(
    format: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List all venues with key statistics."""
    target_format = format or "T20"

    rows = db.execute(
        text("""
            SELECT
                v.id, v.name, v.city, v.country, v.capacity,
                vs.total_matches, vs.avg_first_innings_score, vs.avg_second_innings_score,
                vs.chasing_win_pct, vs.pace_wickets_pct
            FROM venues v
            LEFT JOIN venue_stats vs ON v.id = vs.venue_id AND vs.format = :fmt
            ORDER BY vs.total_matches DESC NULLS LAST
            LIMIT :limit
        """),
        {"fmt": target_format, "limit": limit}
    ).fetchall()

    venues = []
    for row in rows:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        venues.append(d)

    return {"venues": venues, "total": len(venues)}


@router.get("/{venue_id}/analytics")
async def get_venue_analytics(
    venue_id: str,
    format: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get comprehensive venue analytics."""
    target_format = format or "T20"

    row = db.execute(
        text("""
            SELECT vs.*, v.name, v.city, v.country
            FROM venue_stats vs
            JOIN venues v ON vs.venue_id = v.id
            WHERE vs.venue_id = :vid AND vs.format = :fmt
        """),
        {"vid": venue_id, "fmt": target_format}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Venue analytics not found")

    return _row_to_dict(row)
