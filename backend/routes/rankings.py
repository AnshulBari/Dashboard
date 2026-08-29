"""
Rankings API Routes
===================

Endpoints for player and team rankings.

Supports two ranking sources:
1. Platform rankings - computed from historical analytics
2. ICC rankings - from external provider (CricketData.org)
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.utils.database import get_db, engine
from backend.utils.validation import validate_format, VALID_FORMATS
from backend.services.rankings import RankingsService
from backend.providers.cricketdata import CricketDataProvider

router = APIRouter()

# Initialize rankings service with provider
_rankings_provider = CricketDataProvider()
_rankings_service = RankingsService(
    provider=_rankings_provider,
    db_engine=engine,
    cache_ttl=3600,  # 1 hour cache for rankings
)


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return dict(row._mapping)


# ============================================================
# Platform Rankings (existing)
# ============================================================


@router.get("/platform")
async def get_platform_rankings(
    format: str = Query("T20"),
    category: str = Query("batting", description="batting, bowling, allrounder"),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get platform-computed rankings from historical analytics.

    These are derived from the platform's own statistical analysis.
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
        "source": "platform",
        "format": target_format,
        "category": category,
        "rankings": rankings,
        "total": len(rankings),
    }


# ============================================================
# ICC Rankings (external provider)
# ============================================================


@router.get("/icc")
async def get_icc_rankings(
    format: str = Query("Test", description="Test, ODI, T20I"),
    category: str = Query("batting", description="batting, bowling, allrounders, teams"),
    refresh: bool = Query(False, description="Force refresh from provider"),
):
    """
    Get official ICC rankings from external provider.

    Rankings are sourced from CricketData.org and mapped to
    canonical player/team IDs where possible.

    Note: ICC rankings are separate from platform-computed rankings.
    """
    fmt = validate_format(format)

    if category == "teams":
        result = _rankings_service.get_team_rankings(
            format=fmt,
            force_refresh=refresh,
        )
    else:
        if category not in ("batting", "bowling", "allrounders"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category '{category}'. Must be one of: batting, bowling, allrounders, teams",
            )
        result = _rankings_service.get_player_rankings(
            format=fmt,
            category=category,
            force_refresh=refresh,
        )

    # Add provider availability info
    result["provider_available"] = _rankings_service.is_available()

    return result


# ============================================================
# Backward Compatibility
# ============================================================


@router.get("/")
async def get_rankings(
    format: str = Query("T20"),
    category: str = Query("batting", description="batting, bowling, allrounder"),
    limit: int = Query(25, ge=1, le=100),
    source: str = Query("platform", description="platform or icc"),
    db: Session = Depends(get_db),
):
    """
    Get rankings - supports both platform and ICC sources.

    Use 'source=platform' for platform-computed rankings (default).
    Use 'source=icc' for official ICC rankings.
    """
    if source == "icc":
        # Redirect to ICC endpoint
        return await get_icc_rankings(
            format=format,
            category=category,
        )
    else:
        return await get_platform_rankings(
            format=format,
            category=category,
            limit=limit,
            db=db,
        )
