"""
Rankings Service
===============

Service layer for ICC rankings integration.

Responsibilities:
- Fetch rankings from provider
- Map external entities to canonical IDs
- Cache rankings in memory
- Provide fresh/stale data indicators
- Handle provider failures gracefully
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from threading import Lock

from sqlalchemy import text

from backend.providers.base import (
    RankingsProvider,
    RankingEntry,
    TeamRankingEntry,
)

logger = logging.getLogger(__name__)


class RankingsCache:
    """
    In-memory cache for rankings data.

    Rankings don't change frequently, so we cache them with a configurable TTL.
    """

    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cached data (default: 1 hour)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: dict = {}
        self._timestamps: dict = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[dict]:
        """
        Get cached data if fresh.

        Returns:
            Cached data dict or None if stale/missing
        """
        with self._lock:
            if key not in self._cache:
                return None

            timestamp = self._timestamps.get(key, 0)
            if time.time() - timestamp > self.ttl_seconds:
                return None  # Stale

            return self._cache[key]

    def set(self, key: str, data: dict):
        """Store data in cache."""
        with self._lock:
            self._cache[key] = data
            self._timestamps[key] = time.time()

    def get_last_updated(self, key: str) -> Optional[datetime]:
        """Get when the cache was last updated for a key."""
        with self._lock:
            timestamp = self._timestamps.get(key)
            if timestamp:
                return datetime.fromtimestamp(timestamp)
            return None

    def is_stale(self, key: str) -> bool:
        """Check if cached data is stale."""
        with self._lock:
            timestamp = self._timestamps.get(key, 0)
            return time.time() - timestamp > self.ttl_seconds

    def clear(self):
        """Clear all cached data."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()


class RankingsService:
    """
    Service for managing ICC rankings.

    This service:
    1. Fetches rankings from the configured provider
    2. Maps external player/team names to canonical IDs
    3. Caches results to avoid repeated API calls
    4. Provides fresh/stale data indicators
    """

    def __init__(
        self,
        provider: RankingsProvider,
        db_engine=None,
        cache_ttl: int = 3600,
    ):
        """
        Initialize the rankings service.

        Args:
            provider: Rankings data provider
            db_engine: SQLAlchemy engine for entity mapping
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        """
        self.provider = provider
        self.db_engine = db_engine
        self.cache = RankingsCache(ttl_seconds=cache_ttl)

    def _map_player_id(self, name: str, conn) -> Optional[str]:
        """
        Map an external player name to canonical player ID.

        Uses exact canonical_name match first, then tries LIKE search.
        """
        try:
            # Try exact match first
            result = conn.execute(
                text("SELECT id FROM players WHERE canonical_name = :name LIMIT 1"),
                {"name": name}
            ).fetchone()
            if result:
                return str(result[0])

            # Try partial match
            result = conn.execute(
                text("SELECT id FROM players WHERE canonical_name LIKE :pattern LIMIT 1"),
                {"pattern": f"%{name}%"}
            ).fetchone()
            if result:
                return str(result[0])

            return None
        except Exception as e:
            logger.debug(f"Player mapping failed for '{name}': {e}")
            return None

    def _map_team_id(self, name: str, conn) -> Optional[str]:
        """
        Map an external team name to canonical team ID.

        Uses exact canonical_name match first, then tries short_name.
        """
        try:
            # Try exact match
            result = conn.execute(
                text("SELECT id FROM teams WHERE canonical_name = :name LIMIT 1"),
                {"name": name}
            ).fetchone()
            if result:
                return str(result[0])

            # Try short name
            result = conn.execute(
                text("SELECT id FROM teams WHERE short_name = :name LIMIT 1"),
                {"name": name}
            ).fetchone()
            if result:
                return str(result[0])

            # Try partial match
            result = conn.execute(
                text("SELECT id FROM teams WHERE canonical_name LIKE :pattern LIMIT 1"),
                {"pattern": f"%{name}%"}
            ).fetchone()
            if result:
                return str(result[0])

            return None
        except Exception as e:
            logger.debug(f"Team mapping failed for '{name}': {e}")
            return None

    def _map_entities(
        self,
        rankings: list[RankingEntry],
        conn,
    ) -> list[RankingEntry]:
        """Map external entities in ranking entries to canonical IDs."""
        for entry in rankings:
            if entry.name:
                entry.player_id = self._map_player_id(entry.name, conn)
        return rankings

    def _map_team_entities(
        self,
        rankings: list[TeamRankingEntry],
        conn,
    ) -> list[TeamRankingEntry]:
        """Map external entities in team ranking entries to canonical IDs."""
        for entry in rankings:
            if entry.team_name:
                entry.team_id = self._map_team_id(entry.team_name, conn)
        return rankings

    def get_player_rankings(
        self,
        format: str,
        category: str,
        force_refresh: bool = False,
    ) -> dict:
        """
        Get player rankings with caching and entity mapping.

        Args:
            format: Cricket format (Test, ODI, T20I)
            category: Ranking category (batting, bowling, allrounders)
            force_refresh: Force refresh from provider

        Returns:
            Dict with rankings data, metadata, and freshness info
        """
        cache_key = f"player_{format}_{category}"

        # Check cache first
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                cached["cached"] = True
                return cached

        # Fetch from provider
        rankings = self.provider.get_player_rankings(format, category)

        # Map entities if database is available
        if self.db_engine and rankings:
            try:
                with self.db_engine.connect() as conn:
                    rankings = self._map_entities(rankings, conn)
            except Exception as e:
                logger.error(f"Entity mapping failed: {e}")

        # Build response
        result = {
            "format": format,
            "category": category,
            "rankings": [
                {
                    "rank": r.rank,
                    "name": r.name,
                    "country": r.country,
                    "rating": r.rating,
                    "change": r.change,
                    "player_id": r.player_id,
                    "source_id": r.source_id,
                }
                for r in rankings
            ],
            "total": len(rankings),
            "source": rankings[0].source if rankings else None,
            "fetched_at": rankings[0].fetched_at.isoformat() if rankings and rankings[0].fetched_at else None,
            "cached": False,
            "stale": False,
        }

        # Cache the result
        self.cache.set(cache_key, result)

        return result

    def get_team_rankings(
        self,
        format: str,
        force_refresh: bool = False,
    ) -> dict:
        """
        Get team rankings with caching and entity mapping.

        Args:
            format: Cricket format (Test, ODI, T20I)
            force_refresh: Force refresh from provider

        Returns:
            Dict with rankings data, metadata, and freshness info
        """
        cache_key = f"team_{format}"

        # Check cache first
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                cached["cached"] = True
                return cached

        # Fetch from provider
        rankings = self.provider.get_team_rankings(format)

        # Map entities if database is available
        if self.db_engine and rankings:
            try:
                with self.db_engine.connect() as conn:
                    rankings = self._map_team_entities(rankings, conn)
            except Exception as e:
                logger.error(f"Entity mapping failed: {e}")

        # Build response
        result = {
            "format": format,
            "rankings": [
                {
                    "rank": r.rank,
                    "team_name": r.team_name,
                    "rating": r.rating,
                    "points": r.points,
                    "change": r.change,
                    "team_id": r.team_id,
                    "source_id": r.source_id,
                }
                for r in rankings
            ],
            "total": len(rankings),
            "source": rankings[0].source if rankings else None,
            "fetched_at": rankings[0].fetched_at.isoformat() if rankings and rankings[0].fetched_at else None,
            "cached": False,
            "stale": False,
        }

        # Cache the result
        self.cache.set(cache_key, result)

        return result

    def is_available(self) -> bool:
        """Check if the rankings provider is available."""
        return self.provider.is_available()
