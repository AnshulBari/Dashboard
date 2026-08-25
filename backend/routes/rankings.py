"""
Rankings API Routes
===================

Endpoints for platform-computed player and team rankings.
These are computed from the platform's own analytics.
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
async def get_rankings(
    format: str = Query("T20I"),
    category: str = Query("batting", description="batting, bowling, allrounder"),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get platform rankings for a given format and category.

    These rankings are derived from the platform's precomputed analytics:
    - Batting: based on batting_average + strike_rate + form_score
    - Bowling: based on economy + wickets + bowling_average
    - Allrounder: combined batting + bowling metrics
    """
    target_format = format or "T20"

    if category == "batting":
        rows = db.execute(
            text("""
                SELECT
                    p.id, p.canonical_name AS name, p.country,
                    t.short_name AS team,
                    pbs.runs, pbs.batting_average, pbs.strike_rate,
                    pbs.innings, pbs.fifties, pbs.hundreds,
                    pf.form_score,
                    ROUND(
                        COALESCE(pbs.batting_average, 0) * 0.4 +
                        COALESCE(pbs.strike_rate, 0) * 0.3 +
                        COALESCE(pf.form_score, 50) * 0.3
                    , 2) AS rating
                FROM players p
                LEFT JOIN teams t ON p.team_id = t.id
                LEFT JOIN player_batting_stats pbs ON p.id = pbs.player_id AND pbs.format = :fmt AND pbs.period = 'career'
                LEFT JOIN player_form pf ON p.id = pf.player_id AND pf.format = :fmt
                WHERE p.role IN ('batsman', 'allrounder', 'wicketkeeper')
                    AND p.is_active = true
                    AND pbs.innings >= 5
                ORDER BY rating DESC NULLS LAST
                LIMIT :limit
            """),
            {"fmt": target_format, "limit": limit}
        ).fetchall()

    elif category == "bowling":
        rows = db.execute(
            text("""
                SELECT
                    p.id, p.canonical_name AS name, p.country,
                    t.short_name AS team,
                    pws.wickets, pws.economy, pws.bowling_average, pws.strike_rate,
                    pws.innings,
                    ROUND(
                        COALESCE(pws.wickets, 0) * 0.3 +
                        (10 - CASE WHEN COALESCE(pws.economy, 15) < 10 THEN COALESCE(pws.economy, 15) ELSE 10 END) * 10 * 0.4 +
                        COALESCE(30 - CASE WHEN COALESCE(pws.bowling_average, 60) < 30 THEN COALESCE(pws.bowling_average, 60) ELSE 30 END, 0) * 0.3
                    , 2) AS rating
                FROM players p
                LEFT JOIN teams t ON p.team_id = t.id
                LEFT JOIN player_bowling_stats pws ON p.id = pws.player_id AND pws.format = :fmt AND pws.period = 'career'
                WHERE p.role IN ('bowler', 'allrounder')
                    AND p.is_active = true
                    AND pws.innings >= 5
                ORDER BY rating DESC NULLS LAST
                LIMIT :limit
            """),
            {"fmt": target_format, "limit": limit}
        ).fetchall()

    else:  # allrounder
        rows = db.execute(
            text("""
                SELECT
                    p.id, p.canonical_name AS name, p.country,
                    t.short_name AS team,
                    pbs.runs, pbs.batting_average, pbs.strike_rate,
                    pws.wickets, pws.economy,
                    pf.form_score,
                    ROUND(
                        COALESCE(pbs.batting_average, 0) * 0.25 +
                        COALESCE(pbs.strike_rate, 0) * 0.15 +
                        COALESCE(pws.wickets, 0) * 0.3 +
                        COALESCE(pf.form_score, 50) * 0.3
                    , 2) AS rating
                FROM players p
                LEFT JOIN teams t ON p.team_id = t.id
                LEFT JOIN player_batting_stats pbs ON p.id = pbs.player_id AND pbs.format = :fmt AND pbs.period = 'career'
                LEFT JOIN player_bowling_stats pws ON p.id = pws.player_id AND pws.format = :fmt AND pws.period = 'career'
                LEFT JOIN player_form pf ON p.id = pf.player_id AND pf.format = :fmt
                WHERE p.role = 'allrounder'
                    AND p.is_active = true
                ORDER BY rating DESC NULLS LAST
                LIMIT :limit
            """),
            {"fmt": target_format, "limit": limit}
        ).fetchall()

    rankings = []
    for idx, row in enumerate(rows, 1):
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        d["rank"] = idx
        rankings.append(d)

    return {
        "format": target_format,
        "category": category,
        "rankings": rankings,
        "total": len(rankings),
    }
