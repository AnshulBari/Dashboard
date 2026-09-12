"""
Rankings API Routes
===================

Endpoints for player and team rankings.

Supports two ranking sources:
1. Platform rankings - computed from historical analytics
2. Official ICC rankings - from the feed used by icc-cricket.com
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.utils.database import get_db, engine
from backend.utils.stat_invariants import safe_not_outs_sql, sanitize_stat_record
from backend.utils.validation import format_scope_clause, validate_format, VALID_FORMATS
from backend.services.rankings import RankingsService
from backend.providers.icc_rankings import ICCRankingsProvider

router = APIRouter()

# Initialize rankings service with provider
_rankings_provider = ICCRankingsProvider()
_rankings_service = RankingsService(
    provider=_rankings_provider,
    db_engine=engine,
    cache_ttl=21600,  # Recheck during the day so Wednesday updates arrive promptly.
)


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return sanitize_stat_record(dict(row._mapping))


SAFE_NOT_OUTS_SQL = safe_not_outs_sql()


# ============================================================
# Platform Rankings (existing)
# ============================================================


@router.get("/platform")
async def get_platform_rankings(
    format: str = Query("International"),
    category: str = Query("batting", description="batting, bowling, allrounder"),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get platform-computed rankings from historical analytics.

    These are derived from the platform's own statistical analysis.
    """
    target_format, batting_filter, params = format_scope_clause("format", format)
    _, bowling_filter, bowling_params = format_scope_clause("format", format)
    _, form_filter, form_params = format_scope_clause("format", format)
    params.update(bowling_params)
    params.update(form_params)
    params["limit"] = limit
    if category not in {"batting", "bowling", "allrounder"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid category. Must be one of: batting, bowling, allrounder",
        )

    if category == "batting":
        rows = db.execute(
            text(f"""
                WITH pbs AS (
                    SELECT player_id, SUM(runs) AS runs, SUM(innings) AS innings,
                        SUM(fifties) AS fifties, SUM(hundreds) AS hundreds,
                        ROUND(1.0 * SUM(runs) / NULLIF(SUM(innings) - ({SAFE_NOT_OUTS_SQL}), 0), 2) AS batting_average,
                        ROUND(100.0 * SUM(runs) / NULLIF(SUM(balls_faced), 0), 2) AS strike_rate
                    FROM player_batting_stats WHERE {batting_filter} AND period = 'career' GROUP BY player_id
                ),
                pf AS (
                    SELECT player_id,
                        ROUND(SUM(form_score * COALESCE(NULLIF(recent_innings_count, 0), 1)) /
                              NULLIF(SUM(COALESCE(NULLIF(recent_innings_count, 0), 1)), 0), 2) AS impact_score
                    FROM player_form WHERE {form_filter} GROUP BY player_id
                )
                SELECT
                    p.id, p.canonical_name AS name, p.country,
                    t.short_name AS team,
                    pbs.runs, pbs.batting_average, pbs.strike_rate,
                    pbs.innings, pbs.fifties, pbs.hundreds,
                    pf.impact_score,
                    ROUND(
                        COALESCE(pbs.batting_average, 0) * 0.4 +
                        COALESCE(pbs.strike_rate, 0) * 0.3 +
                        COALESCE(pf.impact_score, 50) * 0.3
                    , 2) AS rating
                FROM players p
                LEFT JOIN teams t ON p.team_id = t.id
                LEFT JOIN pbs ON p.id = pbs.player_id
                LEFT JOIN pf ON p.id = pf.player_id
                WHERE p.role IN ('batsman', 'allrounder', 'wicketkeeper')
                    AND p.is_active = true
                    AND pbs.innings >= 5
                ORDER BY rating DESC NULLS LAST
                LIMIT :limit
            """),
            params
        ).fetchall()

    elif category == "bowling":
        rows = db.execute(
            text(f"""
                WITH pws AS (
                    SELECT player_id, SUM(wickets) AS wickets, SUM(innings) AS innings,
                        ROUND(6.0 * SUM(runs_conceded) / NULLIF(SUM(balls_bowled), 0), 2) AS economy,
                        ROUND(1.0 * SUM(runs_conceded) / NULLIF(SUM(wickets), 0), 2) AS bowling_average,
                        ROUND(1.0 * SUM(balls_bowled) / NULLIF(SUM(wickets), 0), 2) AS strike_rate
                    FROM player_bowling_stats WHERE {bowling_filter} AND period = 'career' GROUP BY player_id
                ),
                pf AS (
                    SELECT player_id,
                        ROUND(SUM(form_score * COALESCE(NULLIF(recent_innings_count, 0), 1)) /
                              NULLIF(SUM(COALESCE(NULLIF(recent_innings_count, 0), 1)), 0), 2) AS impact_score
                    FROM player_form WHERE {form_filter} GROUP BY player_id
                )
                SELECT
                    p.id, p.canonical_name AS name, p.country,
                    t.short_name AS team,
                    pws.wickets, pws.economy, pws.bowling_average, pws.strike_rate,
                    pws.innings, pf.impact_score,
                    ROUND(
                        COALESCE(pws.wickets, 0) * 0.3 +
                        (10 - CASE WHEN COALESCE(pws.economy, 15) < 10 THEN COALESCE(pws.economy, 15) ELSE 10 END) * 10 * 0.25 +
                        COALESCE(30 - CASE WHEN COALESCE(pws.bowling_average, 60) < 30 THEN COALESCE(pws.bowling_average, 60) ELSE 30 END, 0) * 0.15 +
                        COALESCE(pf.impact_score, 50) * 0.3
                    , 2) AS rating
                FROM players p
                LEFT JOIN teams t ON p.team_id = t.id
                LEFT JOIN pws ON p.id = pws.player_id
                LEFT JOIN pf ON p.id = pf.player_id
                WHERE p.role IN ('bowler', 'allrounder')
                    AND p.is_active = true
                    AND pws.innings >= 5
                ORDER BY rating DESC NULLS LAST
                LIMIT :limit
            """),
            params
        ).fetchall()

    else:  # allrounder
        rows = db.execute(
            text(f"""
                WITH pbs AS (
                    SELECT player_id, SUM(runs) AS runs,
                        ROUND(1.0 * SUM(runs) / NULLIF(SUM(innings) - ({SAFE_NOT_OUTS_SQL}), 0), 2) AS batting_average,
                        ROUND(100.0 * SUM(runs) / NULLIF(SUM(balls_faced), 0), 2) AS strike_rate
                    FROM player_batting_stats WHERE {batting_filter} AND period = 'career' GROUP BY player_id
                ),
                pws AS (
                    SELECT player_id, SUM(wickets) AS wickets,
                        ROUND(6.0 * SUM(runs_conceded) / NULLIF(SUM(balls_bowled), 0), 2) AS economy
                    FROM player_bowling_stats WHERE {bowling_filter} AND period = 'career' GROUP BY player_id
                ),
                pf AS (
                    SELECT player_id,
                        ROUND(SUM(form_score * COALESCE(NULLIF(recent_innings_count, 0), 1)) /
                              NULLIF(SUM(COALESCE(NULLIF(recent_innings_count, 0), 1)), 0), 2) AS impact_score
                    FROM player_form WHERE {form_filter} GROUP BY player_id
                )
                SELECT
                    p.id, p.canonical_name AS name, p.country,
                    t.short_name AS team,
                    pbs.runs, pbs.batting_average, pbs.strike_rate,
                    pws.wickets, pws.economy,
                    pf.impact_score,
                    ROUND(
                        COALESCE(pbs.batting_average, 0) * 0.25 +
                        COALESCE(pbs.strike_rate, 0) * 0.15 +
                        COALESCE(pws.wickets, 0) * 0.3 +
                        COALESCE(pf.impact_score, 50) * 0.3
                    , 2) AS rating
                FROM players p
                LEFT JOIN teams t ON p.team_id = t.id
                LEFT JOIN pbs ON p.id = pbs.player_id
                LEFT JOIN pws ON p.id = pws.player_id
                LEFT JOIN pf ON p.id = pf.player_id
                WHERE p.role = 'allrounder'
                    AND p.is_active = true
                ORDER BY rating DESC NULLS LAST
                LIMIT :limit
            """),
            params
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

    Rankings are sourced from the official ICC website feed and mapped to
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
        if category not in ("batting", "bowling", "allrounder", "allrounders"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category '{category}'. Must be one of: batting, bowling, allrounders, teams",
            )
        result = _rankings_service.get_player_rankings(
            format=fmt,
            category="allrounders" if category == "allrounder" else category,
            force_refresh=refresh,
        )

    result["official_url"] = "https://www.icc-cricket.com/rankings"
    result["update_schedule"] = "Wednesday"
    result["provider_available"] = _rankings_service.is_available()

    return result


# ============================================================
# Backward Compatibility
# ============================================================


@router.get("/")
async def get_rankings(
    format: str = Query("International"),
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
    if source not in {"platform", "icc"}:
        raise HTTPException(
            status_code=400, detail="Invalid source. Must be platform or icc"
        )
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
