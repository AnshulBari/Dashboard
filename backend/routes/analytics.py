"""
Analytics API Routes
====================

Endpoints for comprehensive analytical queries.
All queries use the existing serving tables (no deliveries dependency).
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.utils.database import get_db
from backend.services import analytics
from backend.utils.validation import validate_format, validate_uuid

router = APIRouter()


# ============================================================
# PLAYER ANALYTICS
# ============================================================


@router.get("/players/{player_id}/career")
async def player_career(player_id: str, db: Session = Depends(get_db)):
    """Get career statistics across all formats."""
    validate_uuid(player_id, "player_id")
    # Check player exists
    exists = db.execute(text("SELECT 1 FROM players WHERE id = :pid"), {"pid": player_id}).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Player not found")
    conn = db.get_bind().connect()
    try:
        result = analytics.player_career(conn, player_id)
    finally:
        conn.close()
    return result


@router.get("/players/{player_id}/by-year")
async def player_by_year(
    player_id: str,
    format: str = Query("T20"),
    batting: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Get player statistics grouped by year."""
    validate_uuid(player_id, "player_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.player_by_year(conn, player_id, fmt, batting)
    finally:
        conn.close()
    return {"player_id": player_id, "format": fmt, "by_year": result}


@router.get("/players/{player_id}/by-competition")
async def player_by_competition(
    player_id: str,
    format: str = Query("T20"),
    batting: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Get player statistics grouped by competition."""
    validate_uuid(player_id, "player_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.player_by_competition(conn, player_id, fmt, batting)
    finally:
        conn.close()
    return {"player_id": player_id, "format": fmt, "by_competition": result}


@router.get("/players/{player_id}/by-season")
async def player_by_season(
    player_id: str,
    format: str = Query("T20"),
    batting: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Get player statistics grouped by season."""
    validate_uuid(player_id, "player_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.player_by_season(conn, player_id, fmt, batting)
    finally:
        conn.close()
    return {"player_id": player_id, "format": fmt, "by_season": result}


@router.get("/players/{player_id}/vs-opponent")
async def player_vs_opponent(
    player_id: str,
    format: str = Query("T20"),
    batting: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Get player statistics vs each opponent."""
    validate_uuid(player_id, "player_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.player_vs_opponent(conn, player_id, fmt, batting)
    finally:
        conn.close()
    return {"player_id": player_id, "format": fmt, "vs_opponent": result}


@router.get("/players/{player_id}/at-venue")
async def player_at_venue(
    player_id: str,
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Get player statistics at each venue."""
    validate_uuid(player_id, "player_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.player_at_venue(conn, player_id, fmt)
    finally:
        conn.close()
    return {"player_id": player_id, "format": fmt, "at_venue": result}


@router.get("/players/{player_id}/history")
async def player_match_history(
    player_id: str,
    format: str = Query("T20"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get recent match history for a player."""
    validate_uuid(player_id, "player_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.player_match_history(conn, player_id, fmt, limit)
    finally:
        conn.close()
    return {"player_id": player_id, "format": fmt, "matches": result}


@router.get("/players/{player_id}/progression")
async def player_career_progression(
    player_id: str,
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Get cumulative career progression by year."""
    validate_uuid(player_id, "player_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.player_career_progression(conn, player_id, fmt)
    finally:
        conn.close()
    return {"player_id": player_id, "format": fmt, "progression": result}


# ============================================================
# TEAM ANALYTICS
# ============================================================


@router.get("/teams/{team_id}/by-format")
async def team_by_format(team_id: str, db: Session = Depends(get_db)):
    """Get team performance by format."""
    validate_uuid(team_id, "team_id")
    conn = db.get_bind().connect()
    try:
        result = analytics.team_by_format(conn, team_id)
    finally:
        conn.close()
    return {"team_id": team_id, "by_format": result}


@router.get("/teams/{team_id}/by-year")
async def team_by_year(
    team_id: str,
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Get team statistics by year."""
    validate_uuid(team_id, "team_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.team_by_year(conn, team_id, fmt)
    finally:
        conn.close()
    return {"team_id": team_id, "format": fmt, "by_year": result}


@router.get("/teams/{team_id}/vs-team/{opponent_id}")
async def team_vs_team(
    team_id: str,
    opponent_id: str,
    format: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get head-to-head record between two teams."""
    validate_uuid(team_id, "team_id")
    validate_uuid(opponent_id, "opponent_id")
    fmt = validate_format(format) if format else None
    conn = db.get_bind().connect()
    try:
        result = analytics.team_vs_team(conn, team_id, opponent_id, fmt)
    finally:
        conn.close()
    return result


@router.get("/teams/{team_id}/at-venue")
async def team_at_venue(
    team_id: str,
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Get team statistics at each venue."""
    validate_uuid(team_id, "team_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.team_at_venue(conn, team_id, fmt)
    finally:
        conn.close()
    return {"team_id": team_id, "format": fmt, "at_venue": result}


@router.get("/teams/{team_id}/by-competition")
async def team_by_competition(team_id: str, db: Session = Depends(get_db)):
    """Get team performance by competition."""
    validate_uuid(team_id, "team_id")
    conn = db.get_bind().connect()
    try:
        result = analytics.team_by_competition(conn, team_id)
    finally:
        conn.close()
    return {"team_id": team_id, "by_competition": result}


@router.get("/teams/{team_id}/history")
async def team_match_history(
    team_id: str,
    format: str = Query("T20"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get recent match history for a team."""
    validate_uuid(team_id, "team_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.team_match_history(conn, team_id, fmt, limit)
    finally:
        conn.close()
    return {"team_id": team_id, "format": fmt, "matches": result}


@router.get("/teams/{team_id}/trend")
async def team_trend(
    team_id: str,
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Get team win-rate trend by year."""
    validate_uuid(team_id, "team_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.team_year_trend(conn, team_id, fmt)
    finally:
        conn.close()
    return {"team_id": team_id, "format": fmt, "trend": result}


# ============================================================
# COMPETITION ANALYTICS
# ============================================================


@router.get("/competitions/{competition_id}/summary")
async def competition_summary(competition_id: str, db: Session = Depends(get_db)):
    """Get competition summary with seasons."""
    validate_uuid(competition_id, "competition_id")
    conn = db.get_bind().connect()
    try:
        result = analytics.competition_summary(conn, competition_id)
    finally:
        conn.close()
    if not result:
        raise HTTPException(status_code=404, detail="Competition not found")
    return result


@router.get("/seasons/{season_id}/matches")
async def season_matches(
    season_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get matches in a specific season."""
    validate_uuid(season_id, "season_id")
    conn = db.get_bind().connect()
    try:
        result = analytics.competition_season_matches(conn, season_id, limit, offset)
    finally:
        conn.close()
    return result


# ============================================================
# VENUE ANALYTICS
# ============================================================


@router.get("/venues/{venue_id}/by-format")
async def venue_by_format(venue_id: str, db: Session = Depends(get_db)):
    """Get venue statistics by format."""
    validate_uuid(venue_id, "venue_id")
    conn = db.get_bind().connect()
    try:
        result = analytics.venue_by_format(conn, venue_id)
    finally:
        conn.close()
    return {"venue_id": venue_id, "by_format": result}


@router.get("/venues/{venue_id}/teams")
async def venue_teams(
    venue_id: str,
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Get team performance at a venue."""
    validate_uuid(venue_id, "venue_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.venue_team_performance(conn, venue_id, fmt)
    finally:
        conn.close()
    return {"venue_id": venue_id, "format": fmt, "teams": result}


@router.get("/venues/{venue_id}/players")
async def venue_players(
    venue_id: str,
    format: str = Query("T20"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get top player performances at a venue."""
    validate_uuid(venue_id, "venue_id")
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        result = analytics.venue_player_performance(conn, venue_id, fmt, limit)
    finally:
        conn.close()
    return {"venue_id": venue_id, "format": fmt, "players": result}


# ============================================================
# MATCH ANALYTICS
# ============================================================


@router.get("/matches/{match_id}/detail")
async def match_detail(match_id: str, db: Session = Depends(get_db)):
    """Get complete match detail with scorecards."""
    validate_uuid(match_id, "match_id")
    conn = db.get_bind().connect()
    try:
        result = analytics.match_detail(conn, match_id)
    finally:
        conn.close()
    if not result:
        raise HTTPException(status_code=404, detail="Match not found")
    return result


# ============================================================
# DATA COMPLETENESS
# ============================================================


@router.get("/data-completeness")
async def data_completeness(db: Session = Depends(get_db)):
    """Measure data coverage across key dimensions."""
    conn = db.get_bind().connect()
    try:
        result = analytics.data_completeness(conn)
    finally:
        conn.close()
    return result


# ============================================================
# QUERY PROFILING
# ============================================================


@router.get("/profile/{query_name}")
async def profile_query(
    query_name: str,
    player_id: Optional[str] = Query(None),
    team_id: Optional[str] = Query(None),
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Profile an analytical query for performance measurement."""
    VALID_QUERIES = {"player_career", "player_by_year", "team_by_format", "team_by_year"}
    if query_name not in VALID_QUERIES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown query: {query_name}. Available: {sorted(VALID_QUERIES)}",
        )
    fmt = validate_format(format)
    conn = db.get_bind().connect()
    try:
        query_map = {
            "player_career": lambda: analytics.profile_query(
                conn, analytics.player_career, player_id
            ),
            "player_by_year": lambda: analytics.profile_query(
                conn, analytics.player_by_year, player_id, fmt
            ),
            "team_by_format": lambda: analytics.profile_query(
                conn, analytics.team_by_format, team_id
            ),
            "team_by_year": lambda: analytics.profile_query(
                conn, analytics.team_by_year, team_id, fmt
            ),
        }
        return query_map[query_name]()
    finally:
        conn.close()
