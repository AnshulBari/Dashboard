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
    In-memory cache for rankings data with request coalescing.

    Rankings don't change frequently, so we cache them with a configurable TTL.
    Includes single-flight protection to prevent duplicate provider calls.
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
        self._in_flight: dict = {}  # key -> Future for request coalescing
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

            # Return a copy to prevent mutation of cached data
            return dict(self._cache[key])

    def get_stale(self, key: str) -> Optional[dict]:
        """
        Get last known data even if stale.

        Returns:
            Last known cached data or None if never fetched
        """
        with self._lock:
            if key not in self._cache:
                return None
            # Return a copy to prevent mutation
            return dict(self._cache[key])

    def set(self, key: str, data: dict):
        """Store data in cache."""
        with self._lock:
            self._cache[key] = data
            self._timestamps[key] = time.time()
            # Clear in-flight marker
            self._in_flight.pop(key, None)

    def get_or_set_inflight(self, key: str) -> bool:
        """
        Check if request is already in flight, or mark it as in-flight.
        
        Returns:
            True if request was already in flight (caller should wait),
            False if this caller should proceed with the fetch.
        """
        with self._lock:
            if key in self._in_flight:
                return True  # Already fetching
            self._in_flight[key] = True
            return False

    def clear_inflight(self, key: str):
        """Clear in-flight marker for a key."""
        with self._lock:
            self._in_flight.pop(key, None)

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
            self._in_flight.clear()


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
        
        Uses safe mapping strategy:
        1. Exact canonical_name match (preferred)
        2. Unambiguous partial match (only if exactly 1 result)
        3. Returns None for ambiguous or no matches

        Args:
            name: External player name to map
            conn: Database connection

        Returns:
            Canonical player ID or None if unmapped/ambiguous
        """
        try:
            # Try exact match first (most reliable)
            result = conn.execute(
                text("SELECT id FROM players WHERE canonical_name = :name LIMIT 2"),
                {"name": name}
            ).fetchall()
            
            if len(result) == 1:
                return str(result[0][0])
            elif len(result) > 1:
                logger.warning(f"Ambiguous player mapping for '{name}': {len(result)} matches")
                return None  # Ambiguous - don't guess

            # Try case-insensitive exact match
            result = conn.execute(
                text("SELECT id FROM players WHERE LOWER(canonical_name) = LOWER(:name) LIMIT 2"),
                {"name": name}
            ).fetchall()
            
            if len(result) == 1:
                return str(result[0][0])
            elif len(result) > 1:
                logger.warning(f"Ambiguous player mapping (case-insensitive) for '{name}': {len(result)} matches")
                return None

            # Try partial match - ONLY if exactly 1 result (unambiguous)
            result = conn.execute(
                text("SELECT id FROM players WHERE canonical_name LIKE :pattern LIMIT 3"),
                {"pattern": f"%{name}%"}
            ).fetchall()
            
            if len(result) == 1:
                logger.debug(f"Partial player match for '{name}'")
                return str(result[0][0])
            elif len(result) > 1:
                logger.warning(f"Ambiguous partial player mapping for '{name}': {len(result)} matches - returning None")
                return None

            return None
        except Exception as e:
            logger.debug(f"Player mapping failed for '{name}': {e}")
            return None

    def _map_team_id(self, name: str, conn) -> Optional[str]:
        """
        Map an external team name to canonical team ID.
        
        Uses safe mapping strategy:
        1. Exact canonical_name match (preferred)
        2. Exact short_name match
        3. Unambiguous partial match (only if exactly 1 result)
        4. Returns None for ambiguous or no matches

        Args:
            name: External team name to map
            conn: Database connection

        Returns:
            Canonical team ID or None if unmapped/ambiguous
        """
        try:
            # Try exact canonical_name match first
            result = conn.execute(
                text("SELECT id FROM teams WHERE canonical_name = :name LIMIT 2"),
                {"name": name}
            ).fetchall()
            
            if len(result) == 1:
                return str(result[0][0])
            elif len(result) > 1:
                logger.warning(f"Ambiguous team mapping for '{name}': {len(result)} matches")
                return None

            # Try exact short_name match
            result = conn.execute(
                text("SELECT id FROM teams WHERE short_name = :name LIMIT 2"),
                {"name": name}
            ).fetchall()
            
            if len(result) == 1:
                return str(result[0][0])
            elif len(result) > 1:
                logger.warning(f"Ambiguous team mapping (short_name) for '{name}': {len(result)} matches")
                return None

            # Try case-insensitive match
            result = conn.execute(
                text("SELECT id FROM teams WHERE LOWER(canonical_name) = LOWER(:name) LIMIT 2"),
                {"name": name}
            ).fetchall()
            
            if len(result) == 1:
                return str(result[0][0])
            elif len(result) > 1:
                logger.warning(f"Ambiguous team mapping (case-insensitive) for '{name}': {len(result)} matches")
                return None

            # Try partial match - ONLY if exactly 1 result (unambiguous)
            result = conn.execute(
                text("SELECT id FROM teams WHERE canonical_name LIKE :pattern LIMIT 3"),
                {"pattern": f"%{name}%"}
            ).fetchall()
            
            if len(result) == 1:
                logger.debug(f"Partial team match for '{name}'")
                return str(result[0][0])
            elif len(result) > 1:
                logger.warning(f"Ambiguous partial team mapping for '{name}': {len(result)} matches - returning None")
                return None

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
        
        Uses request coalescing to prevent multiple concurrent provider calls.

        Args:
            format: Cricket format (Test, ODI, T20I)
            category: Ranking category (batting, bowling, allrounders)
            force_refresh: Force refresh from provider

        Returns:
            Dict with rankings data, metadata, and freshness info
        """
        cache_key = f"player_{format}_{category}"

        # Check cache first (return copy to prevent mutation)
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                cached["cached"] = True
                cached["stale"] = False
                return cached

        # Request coalescing: if another thread is already fetching, wait and return cached
        if self.cache.get_or_set_inflight(cache_key):
            # Another request is in flight, return stale data or wait
            stale = self.cache.get_stale(cache_key)
            if stale:
                stale["cached"] = True
                stale["stale"] = True
                return stale
            # No stale data available, wait briefly then retry
            time.sleep(0.1)
            cached = self.cache.get(cache_key)
            if cached:
                cached["cached"] = True
                cached["stale"] = False
                return cached

        try:
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
        except Exception as e:
            # On failure, return stale data if available
            self.cache.clear_inflight(cache_key)
            stale = self.cache.get_stale(cache_key)
            if stale:
                logger.warning(f"Provider failed, returning stale data: {e}")
                stale["cached"] = True
                stale["stale"] = True
                return stale
            raise

    def get_team_rankings(
        self,
        format: str,
        force_refresh: bool = False,
    ) -> dict:
        """
        Get team rankings with caching and entity mapping.
        
        Uses request coalescing to prevent multiple concurrent provider calls.

        Args:
            format: Cricket format (Test, ODI, T20I)
            force_refresh: Force refresh from provider

        Returns:
            Dict with rankings data, metadata, and freshness info
        """
        cache_key = f"team_{format}"

        # Check cache first (return copy to prevent mutation)
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                cached["cached"] = True
                cached["stale"] = False
                return cached

        # Request coalescing
        if self.cache.get_or_set_inflight(cache_key):
            stale = self.cache.get_stale(cache_key)
            if stale:
                stale["cached"] = True
                stale["stale"] = True
                return stale
            time.sleep(0.1)
            cached = self.cache.get(cache_key)
            if cached:
                cached["cached"] = True
                cached["stale"] = False
                return cached

        try:
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
        except Exception as e:
            self.cache.clear_inflight(cache_key)
            stale = self.cache.get_stale(cache_key)
            if stale:
                logger.warning(f"Provider failed, returning stale data: {e}")
                stale["cached"] = True
                stale["stale"] = True
                return stale
            raise

    def is_available(self) -> bool:
        """Check if the rankings provider is available."""
        return self.provider.is_available()
