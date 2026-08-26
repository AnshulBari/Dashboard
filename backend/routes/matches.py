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
    competition: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    venue: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List matches with filtering options."""
    target_format = format or "T20"

    where_clauses = ["m.format = :fmt"]
    params = {"fmt": target_format, "limit": limit, "offset": offset}

    if competition:
        where_clauses.append("c.name = :comp")
        params["comp"] = competition

    if season:
        where_clauses.append("s.name = :season")
        params["season"] = season

    where_sql = " AND ".join(where_clauses)

    rows = db.execute(
        text(f"""
            SELECT
                m.id, m.match_date, m.format, m.win_margin, m.win_type,
                m.result_type,
                ta.canonical_name AS team_a,
                tb.canonical_name AS team_b,
                tw.canonical_name AS winner,
                v.name AS venue,
                m.toss_decision,
                c.name AS competition_name,
                s.name AS season_name
            FROM matches m
            LEFT JOIN teams ta ON m.team_a_id = ta.id
            LEFT JOIN teams tb ON m.team_b_id = tb.id
            LEFT JOIN teams tw ON m.winner_id = tw.id
            LEFT JOIN venues v ON m.venue_id = v.id
            LEFT JOIN competitions c ON m.competition_id = c.id
            LEFT JOIN seasons s ON m.season_id = s.id
            WHERE {where_sql}
            ORDER BY m.match_date DESC
            LIMIT :limit OFFSET :offset
        """),
        params
    ).fetchall()

    matches = []
    for row in rows:
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
        elif result_type == "abandoned":
            d["result"] = "Abandoned"
        elif d.get("winner"):
            margin_str = f" by {d['win_margin']} {d['win_type']}"
            d["result"] = f"{d['winner']} won{margin_str}"
        else:
            d["result"] = "No result"
        matches.append(d)

    # Count total
    count_params = {"fmt": target_format}
    count_where = ["m.format = :fmt"]
    if competition:
        count_where.append("c.name = :comp")
        count_params["comp"] = competition
    if season:
        count_where.append("s.name = :season")
        count_params["season"] = season
    count_sql = f"SELECT COUNT(*) FROM matches m LEFT JOIN competitions c ON m.competition_id = c.id LEFT JOIN seasons s ON m.season_id = s.id WHERE {' AND '.join(count_where)}"
    total = db.execute(text(count_sql), count_params).scalar() or 0

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
