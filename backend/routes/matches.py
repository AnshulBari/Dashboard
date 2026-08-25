"""
Match API Routes
================

Endpoints for match data.
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
async def list_matches(
    format: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    venue: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List matches with filtering options."""
    target_format = format or "T20"

    rows = db.execute(
        text("""
            SELECT
                m.id, m.match_date, m.format, m.win_margin, m.win_type,
                ta.canonical_name AS team_a,
                tb.canonical_name AS team_b,
                tw.canonical_name AS winner,
                v.name AS venue,
                m.toss_decision
            FROM matches m
            LEFT JOIN teams ta ON m.team_a_id = ta.id
            LEFT JOIN teams tb ON m.team_b_id = tb.id
            LEFT JOIN teams tw ON m.winner_id = tw.id
            LEFT JOIN venues v ON m.venue_id = v.id
            WHERE m.format = :fmt
            ORDER BY m.match_date DESC
            LIMIT :limit OFFSET :offset
        """),
        {"fmt": target_format, "limit": limit, "offset": offset}
    ).fetchall()

    matches = []
    for row in rows:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        # Build result string
        if d.get("winner"):
            margin_str = f" by {d['win_margin']} {d['win_type']}"
            d["result"] = f"{d['winner']} won{margin_str}"
        else:
            d["result"] = "No result"
        matches.append(d)

    total = db.execute(
        text("SELECT COUNT(*) FROM matches WHERE format = :fmt"),
        {"fmt": target_format}
    ).scalar() or 0

    return {
        "matches": matches,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{match_id}")
async def get_match(match_id: str, db: Session = Depends(get_db)):
    """Get detailed match information."""
    row = db.execute(
        text("""
            SELECT
                m.id, m.match_date, m.format, m.win_margin, m.win_type,
                m.toss_decision,
                ta.canonical_name AS team_a,
                tb.canonical_name AS team_b,
                tw.canonical_name AS winner,
                v.name AS venue
            FROM matches m
            LEFT JOIN teams ta ON m.team_a_id = ta.id
            LEFT JOIN teams tb ON m.team_b_id = tb.id
            LEFT JOIN teams tw ON m.winner_id = tw.id
            LEFT JOIN venues v ON m.venue_id = v.id
            WHERE m.id = :mid
        """),
        {"mid": match_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Match not found")

    d = _row_to_dict(row)
    d["id"] = str(d["id"])
    if d.get("winner"):
        d["result"] = f"{d['winner']} won by {d['win_margin']} {d['win_type']}"
    else:
        d["result"] = "No result"

    return d
