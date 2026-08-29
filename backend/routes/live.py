"""
Live Match API Routes
=====================

Endpoints for live match data from external cricket APIs.

Supports 30-second refresh architecture:
- Backend caches live data with short TTL
- Frontend polls every ~30 seconds
- Provider is called only when cache is stale

Note: Live data is fetched from legitimate cricket APIs.
The historical analytics continue working independently of live data availability.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from backend.utils.database import engine
from backend.services.live import LiveService
from backend.providers.cricketdata import CricketDataProvider

router = APIRouter()

# Initialize live service with provider
_live_provider = CricketDataProvider()
_live_service = LiveService(
    provider=_live_provider,
    db_engine=engine,
    cache_ttl=30,  # 30-second cache for live data
)


@router.get("/")
async def get_live_matches(
    refresh: bool = Query(False, description="Force refresh from provider"),
):
    """
    Get currently live/upcoming matches.

    Returns current score, run rates, win probability, etc.

    Architecture:
    - Data is cached for 30 seconds
    - Use refresh=true to force a provider call
    - Response includes 'cached' and 'stale' indicators
    """
    result = _live_service.get_live_matches(force_refresh=refresh)
    result["provider_available"] = _live_service.is_available()
    return result


@router.get("/{match_id}")
async def get_live_match_state(
    match_id: str,
    refresh: bool = Query(False, description="Force refresh from provider"),
):
    """
    Get detailed live match state.

    Includes:
    - Current score, wickets, overs
    - Current batters and bowler
    - Required run rate, current run rate
    - Projected score
    - Match status
    - Last updated timestamp

    Architecture:
    - Data is cached for 30 seconds
    - Use refresh=true to force a provider call
    """
    result = _live_service.get_match_detail(match_id, force_refresh=refresh)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Match '{match_id}' not found or no live data available",
        )

    result["provider_available"] = _live_service.is_available()
    return result


# Keep backward compatibility with old endpoint
@router.get("/{match_id}/state")
async def get_live_match_state_legacy(
    match_id: str,
    refresh: bool = Query(False),
):
    """Legacy endpoint - redirects to new format."""
    return await get_live_match_state(match_id, refresh)
