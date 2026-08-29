"""
Base Provider Classes
====================

Abstract base classes and data models for external cricket data providers.

Design principles:
- Provider-agnostic interfaces
- Clear separation of concerns
- Easy to swap implementations
- Graceful failure handling
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


# ============================================================
# Enums
# ============================================================

class RankingFormat(str, Enum):
    TEST = "Test"
    ODI = "ODI"
    T20I = "T20I"


class RankingCategory(str, Enum):
    BATTING = "batting"
    BOWLING = "bowling"
    ALLROUNDERS = "allrounders"
    TEAMS = "teams"


class MatchStatus(str, Enum):
    LIVE = "live"
    COMPLETED = "completed"
    UPCOMING = "upcoming"
    SCHEDULED = "scheduled"
    UNKNOWN = "unknown"


# ============================================================
# Data Models
# ============================================================

@dataclass
class RankingEntry:
    """A single player ranking entry."""
    rank: int
    name: str
    country: Optional[str] = None
    rating: Optional[int] = None
    change: Optional[int] = None  # Movement from previous ranking
    player_id: Optional[str] = None  # Mapped canonical player ID
    source_id: Optional[str] = None  # External provider's ID
    format: Optional[str] = None
    category: Optional[str] = None
    ranking_date: Optional[str] = None
    fetched_at: Optional[datetime] = None
    source: Optional[str] = None


@dataclass
class TeamRankingEntry:
    """A single team ranking entry."""
    rank: int
    team_name: str
    team_id: Optional[str] = None  # Mapped canonical team ID
    rating: Optional[int] = None
    points: Optional[int] = None
    change: Optional[int] = None
    source_id: Optional[str] = None
    format: Optional[str] = None
    ranking_date: Optional[str] = None
    fetched_at: Optional[datetime] = None
    source: Optional[str] = None


@dataclass
class LiveMatch:
    """Summary of a live/upcoming/completed match."""
    match_id: str
    external_id: Optional[str] = None
    team_a: Optional[str] = None
    team_b: Optional[str] = None
    team_a_id: Optional[str] = None  # Mapped canonical team ID
    team_b_id: Optional[str] = None
    format: Optional[str] = None
    competition: Optional[str] = None
    venue: Optional[str] = None
    status: Optional[str] = None  # live, completed, upcoming
    start_time: Optional[str] = None
    score_team_a: Optional[str] = None
    score_team_b: Optional[str] = None
    result: Optional[str] = None
    fetched_at: Optional[datetime] = None
    source: Optional[str] = None


@dataclass
class LiveMatchDetail:
    """Detailed live match state."""
    match_id: str
    external_id: Optional[str] = None
    team_a: Optional[str] = None
    team_b: Optional[str] = None
    team_a_id: Optional[str] = None
    team_b_id: Optional[str] = None
    format: Optional[str] = None
    competition: Optional[str] = None
    venue: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None

    # Current innings
    batting_team: Optional[str] = None
    bowling_team: Optional[str] = None
    current_score: Optional[str] = None
    current_wickets: Optional[int] = None
    current_overs: Optional[float] = None
    run_rate: Optional[float] = None
    target: Optional[int] = None
    required_run_rate: Optional[float] = None

    # Current players
    striker: Optional[str] = None
    striker_id: Optional[str] = None
    non_striker: Optional[str] = None
    non_striker_id: Optional[str] = None
    current_bowler: Optional[str] = None
    current_bowler_id: Optional[str] = None

    # Additional info
    toss_winner: Optional[str] = None
    toss_decision: Optional[str] = None
    start_time: Optional[str] = None
    last_updated: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    source: Optional[str] = None
    cached: bool = False
    stale: bool = False


# ============================================================
# Abstract Provider Classes
# ============================================================

class RankingsProvider(ABC):
    """Abstract base class for ranking data providers."""

    @abstractmethod
    def get_player_rankings(
        self,
        format: str,
        category: str,
    ) -> list[RankingEntry]:
        """
        Get player rankings for a given format and category.

        Args:
            format: Cricket format (Test, ODI, T20I)
            category: Ranking category (batting, bowling, allrounders)

        Returns:
            List of RankingEntry objects
        """
        pass

    @abstractmethod
    def get_team_rankings(
        self,
        format: str,
    ) -> list[TeamRankingEntry]:
        """
        Get team rankings for a given format.

        Args:
            format: Cricket format (Test, ODI, T20I)

        Returns:
            List of TeamRankingEntry objects
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and reachable."""
        pass


class LiveDataProvider(ABC):
    """Abstract base class for live cricket data providers."""

    @abstractmethod
    def get_live_matches(self) -> list[LiveMatch]:
        """
        Get list of current live/upcoming matches.

        Returns:
            List of LiveMatch objects
        """
        pass

    @abstractmethod
    def get_match_detail(
        self,
        match_id: str,
    ) -> Optional[LiveMatchDetail]:
        """
        Get detailed live match state.

        Args:
            match_id: Match identifier (provider-specific)

        Returns:
            LiveMatchDetail or None if not found
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and reachable."""
        pass
