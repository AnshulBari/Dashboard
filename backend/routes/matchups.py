"""
Matchup API Routes
==================

Endpoints for batter-bowler matchup analytics.
"""

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


@router.get("/{batter_id}/{bowler_id}")
async def get_matchup(
    batter_id: str,
    bowler_id: str,
    format: Optional[str] = Query(None),
):
    """Get head-to-head matchup between a specific batter and bowler."""
    return {
        "batter_id": batter_id,
        "bowler_id": bowler_id,
        "format": format or "T20I",
        "total_balls": 45,
        "total_runs": 68,
        "wickets": 3,
        "strike_rate": 151.11,
        "average": 22.67,
        "dot_balls": 15,
        "boundaries": 8,
        "sixes": 4,
    }
