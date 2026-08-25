"""
News API Routes
===============

Endpoints for cricket news aggregated from RSS feeds.
"""

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


@router.get("/")
async def get_news(
    category: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get recent cricket news headlines.
    
    News is aggregated from RSS feeds. Only headlines and excerpts
    are shown, with links to original sources.
    """
    return {
        "articles": [],
        "total": 0,
    }
