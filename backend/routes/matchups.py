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
from backend.utils.player_images import get_player_image_url
from backend.utils.stat_invariants import sanitize_stat_record
from backend.utils.validation import format_scope_clause, validate_uuid

router = APIRouter()


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return sanitize_stat_record(dict(row._mapping))


@router.get("/")
async def list_matchups(
    format: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List top batter-bowler matchups by total runs scored."""
    target_format, matchup_filter, params = format_scope_clause("bbm.format", format)
    params["limit"] = limit

    rows = db.execute(
        text(f"""
            SELECT
                bbm.batter_id, bbm.bowler_id,
                SUM(bbm.total_balls) AS total_balls, SUM(bbm.total_runs) AS total_runs,
                SUM(bbm.total_wickets) AS total_wickets,
                ROUND(100.0 * SUM(bbm.total_runs) / NULLIF(SUM(bbm.total_balls), 0), 2) AS strike_rate,
                ROUND(1.0 * SUM(bbm.total_runs) / NULLIF(SUM(bbm.total_wickets), 0), 2) AS batting_average,
                SUM(bbm.dot_balls) AS dot_balls, SUM(bbm.boundaries) AS boundaries,
                SUM(bbm.sixes) AS sixes,
                p1.canonical_name AS batter_name,
                p2.canonical_name AS bowler_name
            FROM batter_bowler_matchups bbm
            JOIN players p1 ON bbm.batter_id = p1.id
            JOIN players p2 ON bbm.bowler_id = p2.id
            WHERE {matchup_filter}
            GROUP BY bbm.batter_id, bbm.bowler_id, p1.canonical_name, p2.canonical_name
            ORDER BY total_runs DESC
            LIMIT :limit
        """),
        params,
    ).fetchall()

    matchups = []
    for row in rows:
        d = _row_to_dict(row)
        d["batter_id"] = str(d["batter_id"])
        d["bowler_id"] = str(d["bowler_id"])
        d["format"] = target_format
        d["batter_image_url"] = get_player_image_url(d.get("batter_name"), player_id=d.get("batter_id"))
        d["bowler_image_url"] = get_player_image_url(d.get("bowler_name"), player_id=d.get("bowler_id"))
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
    validate_uuid(batter_id, "batter_id")
    validate_uuid(bowler_id, "bowler_id")
    target_format, matchup_filter, params = format_scope_clause("bbm.format", format)
    params.update({"batter_id": batter_id, "bowler_id": bowler_id})

    row = db.execute(
        text(f"""
            SELECT
                bbm.batter_id, bbm.bowler_id,
                SUM(bbm.total_balls) AS total_balls, SUM(bbm.total_runs) AS total_runs,
                SUM(bbm.total_wickets) AS total_wickets,
                ROUND(100.0 * SUM(bbm.total_runs) / NULLIF(SUM(bbm.total_balls), 0), 2) AS strike_rate,
                ROUND(1.0 * SUM(bbm.total_runs) / NULLIF(SUM(bbm.total_wickets), 0), 2) AS batting_average,
                SUM(bbm.dot_balls) AS dot_balls, SUM(bbm.boundaries) AS boundaries,
                SUM(bbm.sixes) AS sixes,
                p1.canonical_name AS batter_name,
                p2.canonical_name AS bowler_name
            FROM batter_bowler_matchups bbm
            JOIN players p1 ON bbm.batter_id = p1.id
            JOIN players p2 ON bbm.bowler_id = p2.id
            WHERE bbm.batter_id = :batter_id
                AND bbm.bowler_id = :bowler_id
                AND {matchup_filter}
            GROUP BY bbm.batter_id, bbm.bowler_id, p1.canonical_name, p2.canonical_name
        """),
        params,
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
            "batter_image_url": None,
            "bowler_image_url": None,
            "message": "No matchup data found for this pair",
        }

    d = _row_to_dict(row)
    d["batter_id"] = str(d["batter_id"])
    d["bowler_id"] = str(d["bowler_id"])
    d["format"] = target_format
    d["batter_image_url"] = get_player_image_url(d.get("batter_name"), player_id=d.get("batter_id"))
    d["bowler_image_url"] = get_player_image_url(d.get("bowler_name"), player_id=d.get("bowler_id"))
    return d
