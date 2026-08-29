"""
Analytics API Routes
====================

Endpoints for comprehensive analytical queries.
All queries use the existing serving tables (no deliveries dependency).
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session

from backend.utils.database import get_db
from backend.services import analytics

router = APIRouter()


# ============================================================
# PLAYER ANALYTICS
# ============================================================


@router.get("/players/{player_id}/career")
async def player_career(player_id: str, db: Session = Depends(get_db)):
    """Get career statistics across all formats."""
    result = analytics.player_career(db.get_bind().connect(), player_id)
    return result


@router.get("/players/{player_id}/by-year")
async def player_by_year(
    player_id: str,
    format: str = Query("T20"),
    batting: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Get player statistics grouped by year."""
    result = analytics.player_by_year(
        db.get_bind().connect(), player_id, format, batting
    )
    return {"player_id": player_id, "format": format, "by_year": result}


@router.get("/players/{player_id}/by-competition")
async def player_by_competition(
    player_id: str,
    format: str = Query("T20"),
    batting: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Get player statistics grouped by competition."""
    result = analytics.player_by_competition(
        db.get_bind().connect(), player_id, format, batting
    )
    return {"player_id": player_id, "format": format, "by_competition": result}


@router.get("/players/{player_id}/by-season")
async def player_by_season(
    player_id: str,
    format: str = Query("T20"),
    batting: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Get player statistics grouped by season."""
    result = analytics.player_by_season(
        db.get_bind().connect(), player_id, format, batting
    )
    return {"player_id": player_id, "format": format, "by_season": result}


@router.get("/players/{player_id}/vs-opponent")
async def player_vs_opponent(
    player_id: str,
    format: str = Query("T20"),
    batting: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Get player statistics vs each opponent."""
    result = analytics.player_vs_opponent(
        db.get_bind().connect(), player_id, format, batting
    )
    return {"player_id": player_id, "format": format, "vs_opponent": result}


@router.get("/players/{player_id}/at-venue")
async def player_at_venue(
    player_id: str,
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Get player statistics at each venue."""
    result = analytics.player_at_venue(
        db.get_bind().connect(), player_id, format
    )
    return {"player_id": player_id, "format": format, "at_venue": result}


@router.get("/players/{player_id}/history")
async def player_match_history(
    player_id: str,
    format: str = Query("T20"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get recent match history for a player."""
    result = analytics.player_match_history(
        db.get_bind().connect(), player_id, format, limit
    )
    return {"player_id": player_id, "format": format, "matches": result}


@router.get("/players/{player_id}/progression")
async def player_career_progression(
    player_id: str,
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Get cumulative career progression by year."""
    result = analytics.player_career_progression(
        db.get_bind().connect(), player_id, format
    )
    return {"player_id": player_id, "format": format, "progression": result}


# ============================================================
# TEAM ANALYTICS
# ============================================================


@router.get("/teams/{team_id}/by-format")
async def team_by_format(team_id: str, db: Session = Depends(get_db)):
    """Get team performance by format."""
    result = analytics.team_by_format(db.get_bind().connect(), team_id)
    return {"team_id": team_id, "by_format": result}


@router.get("/teams/{team_id}/by-year")
async def team_by_year(
    team_id: str,
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Get team statistics by year."""
    result = analytics.team_by_year(
        db.get_bind().connect(), team_id, format
    )
    return {"team_id": team_id, "format": format, "by_year": result}


@router.get("/teams/{team_id}/vs-team/{opponent_id}")
async def team_vs_team(
    team_id: str,
    opponent_id: str,
    format: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get head-to-head record between two teams."""
    result = analytics.team_vs_team(
        db.get_bind().connect(), team_id, opponent_id, format
    )
    return result


@router.get("/teams/{team_id}/at-venue")
async def team_at_venue(
    team_id: str,
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Get team statistics at each venue."""
    result = analytics.team_at_venue(
        db.get_bind().connect(), team_id, format
    )
    return {"team_id": team_id, "format": format, "at_venue": result}


@router.get("/teams/{team_id}/by-competition")
async def team_by_competition(team_id: str, db: Session = Depends(get_db)):
    """Get team performance by competition."""
    result = analytics.team_by_competition(
        db.get_bind().connect(), team_id
    )
    return {"team_id": team_id, "by_competition": result}


@router.get("/teams/{team_id}/history")
async def team_match_history(
    team_id: str,
    format: str = Query("T20"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get recent match history for a team."""
    result = analytics.team_match_history(
        db.get_bind().connect(), team_id, format, limit
    )
    return {"team_id": team_id, "format": format, "matches": result}


@router.get("/teams/{team_id}/trend")
async def team_trend(
    team_id: str,
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Get team win-rate trend by year."""
    result = analytics.team_year_trend(
        db.get_bind().connect(), team_id, format
    )
    return {"team_id": team_id, "format": format, "trend": result}


# ============================================================
# COMPETITION ANALYTICS
# ============================================================


@router.get("/competitions/{competition_id}/summary")
async def competition_summary(competition_id: str, db: Session = Depends(get_db)):
    """Get competition summary with seasons."""
    result = analytics.competition_summary(
        db.get_bind().connect(), competition_id
    )
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
    result = analytics.competition_season_matches(
        db.get_bind().connect(), season_id, limit, offset
    )
    return result


# ============================================================
# VENUE ANALYTICS
# ============================================================


@router.get("/venues/{venue_id}/by-format")
async def venue_by_format(venue_id: str, db: Session = Depends(get_db)):
    """Get venue statistics by format."""
    result = analytics.venue_by_format(db.get_bind().connect(), venue_id)
    return {"venue_id": venue_id, "by_format": result}


@router.get("/venues/{venue_id}/teams")
async def venue_teams(
    venue_id: str,
    format: str = Query("T20"),
    db: Session = Depends(get_db),
):
    """Get team performance at a venue."""
    result = analytics.venue_team_performance(
        db.get_bind().connect(), venue_id, format
    )
    return {"venue_id": venue_id, "format": format, "teams": result}


@router.get("/venues/{venue_id}/players")
async def venue_players(
    venue_id: str,
    format: str = Query("T20"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get top player performances at a venue."""
    result = analytics.venue_player_performance(
        db.get_bind().connect(), venue_id, format, limit
    )
    return {"venue_id": venue_id, "format": format, "players": result}


# ============================================================
# MATCH ANALYTICS
# ============================================================


@router.get("/matches/{match_id}/detail")
async def match_detail(match_id: str, db: Session = Depends(get_db)):
    """Get complete match detail with scorecards."""
    result = analytics.match_detail(db.get_bind().connect(), match_id)
    if not result:
        raise HTTPException(status_code=404, detail="Match not found")
    return result


# ============================================================
# DATA COMPLETENESS
# ============================================================


@router.get("/data-completeness")
async def data_completeness(db: Session = Depends(get_db)):
    """Measure data coverage across key dimensions."""
    result = analytics.data_completeness(db.get_bind().connect())
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
    conn = db.get_bind().connect()
    query_map = {
        "player_career": lambda: analytics.profile_query(
            conn, analytics.player_career, player_id
        ),
        "player_by_year": lambda: analytics.profile_query(
            conn, analytics.player_by_year, player_id, format
        ),
        "team_by_format": lambda: analytics.profile_query(
            conn, analytics.team_by_format, team_id
        ),
        "team_by_year": lambda: analytics.profile_query(
            conn, analytics.team_by_year, team_id, format
        ),
    }
    if query_name not in query_map:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown query: {query_name}. Available: {list(query_map.keys())}",
        )
    return query_map[query_name]()
