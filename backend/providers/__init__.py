"""
External Data Providers
======================

Provider abstraction layer for external cricket data sources.

This module provides a clean separation between:
- Historical data (Cricsheet, offline)
- Official rankings (ICC source)
- Live match data (third-party provider)

Each provider follows a common interface so the source can be
swapped without changing the service layer.
"""

from backend.providers.base import (
    RankingsProvider,
    LiveDataProvider,
    RankingEntry,
    TeamRankingEntry,
    LiveMatch,
    LiveMatchDetail,
)
from backend.providers.cricketdata import CricketDataProvider

__all__ = [
    "RankingsProvider",
    "LiveDataProvider",
    "RankingEntry",
    "TeamRankingEntry",
    "LiveMatch",
    "LiveMatchDetail",
    "CricketDataProvider",
]
