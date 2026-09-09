"""
Competition API Routes
======================

Endpoints for competition and season data.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.utils.database import get_db
from backend.utils.validation import format_scope_clause, validate_uuid

router = APIRouter()


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return dict(row._mapping)


@router.get("/")
async def list_competitions(
    format: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all competitions."""
    target_format, competition_filter, params = format_scope_clause("c.format", format)
    params["limit"] = limit
    where = f"WHERE {competition_filter}"

    rows = db.execute(
        text(f"""
            SELECT c.id, c.name, c.short_name, c.format, c.governing_body, c.season
            FROM competitions c
            {where}
            ORDER BY c.name
            LIMIT :limit
        """),
        params,
    ).fetchall()
    total = db.execute(
        text(f"SELECT COUNT(*) FROM competitions c {where}"), params
    ).scalar() or 0

    competitions = []
    for row in rows:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        competitions.append(d)

    return {"competitions": competitions, "total": total, "format": target_format}


@router.get("/{competition_id}")
async def get_competition(competition_id: str, db: Session = Depends(get_db)):
    """Get detailed competition information."""
    validate_uuid(competition_id, "competition_id")
    row = db.execute(
        text("""
            SELECT id, name, short_name, format, governing_body, season
            FROM competitions
            WHERE id = :cid
        """),
        {"cid": competition_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Competition not found")

    d = _row_to_dict(row)
    d["id"] = str(d["id"])
    d["seasons"] = []

    seasons = db.execute(
        text("""
            SELECT id, name, start_date, end_date
            FROM seasons
            WHERE competition_id = :cid
            ORDER BY name DESC
        """),
        {"cid": competition_id},
    ).fetchall()

    d["seasons"] = [
        {
            "id": str(s.id),
            "name": s.name,
            "start_date": str(s.start_date) if s.start_date else None,
            "end_date": str(s.end_date) if s.end_date else None,
        }
        for s in seasons
    ]

    return d


@router.get("/{competition_id}/seasons")
async def list_seasons(competition_id: str, db: Session = Depends(get_db)):
    """List seasons for a competition."""
    validate_uuid(competition_id, "competition_id")
    exists = db.execute(
        text("SELECT 1 FROM competitions WHERE id = :cid"), {"cid": competition_id}
    ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Competition not found")

    rows = db.execute(
        text("""
            SELECT id, name, start_date, end_date
            FROM seasons
            WHERE competition_id = :cid
            ORDER BY name DESC
        """),
        {"cid": competition_id},
    ).fetchall()

    seasons = []
    for row in rows:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        seasons.append(d)

    return {"seasons": seasons, "total": len(seasons)}
