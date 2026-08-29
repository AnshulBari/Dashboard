"""
Live Data Service
================

Service layer for live cricket match data.

Responsibilities:
- Fetch live match data from provider
- Cache with short TTL for 30-second refresh
- Map external entities to canonical IDs
- Handle provider failures gracefully
- Normalize response format
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from threading import Lock

from sqlalchemy import text

from backend.providers.base import (
    LiveDataProvider,
    LiveMatch,
    LiveMatchDetail,
)

logger = logging.getLogger(__name__)


class LiveCache:
    """
    Short-lived in-memory cache for live data.

    Designed for ~30-second refresh intervals.
    """

    def __init__(self, ttl_seconds: int = 30):
        """
        Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cached data (default: 30 seconds)
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

    def is_stale(self, key: str) -> bool:
        """Check if cached data is stale."""
        with self._lock:
            timestamp = self._timestamps.get(key, 0)
            return time.time() - timestamp > self.ttl_seconds

    def get_age_seconds(self, key: str) -> float:
        """Get age of cached data in seconds."""
        with self._lock:
            timestamp = self._timestamps.get(key, 0)
            return time.time() - timestamp

    def clear(self):
        """Clear all cached data."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()


class LiveService:
    """
    Service for managing live cricket match data.

    This service:
    1. Fetches live data from the configured provider
    2. Caches results with short TTL for 30-second refresh
    3. Maps external entities to canonical IDs
    4. Provides normalized API responses
    5. Handles provider failures gracefully
    """

    def __init__(
        self,
        provider: LiveDataProvider,
        db_engine=None,
        cache_ttl: int = 30,
    ):
        """
        Initialize the live data service.

        Args:
            provider: Live data provider
            db_engine: SQLAlchemy engine for entity mapping
            cache_ttl: Cache time-to-live in seconds (default: 30)
        """
        self.provider = provider
        self.db_engine = db_engine
        self.cache = LiveCache(ttl_seconds=cache_ttl)

    def _map_team_id(self, name: str, conn) -> Optional[str]:
        """Map an external team name to canonical team ID."""
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

    def _map_player_id(self, name: str, conn) -> Optional[str]:
        """Map an external player name to canonical player ID."""
        try:
            result = conn.execute(
                text("SELECT id FROM players WHERE canonical_name = :name LIMIT 1"),
                {"name": name}
            ).fetchone()
            if result:
                return str(result[0])

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

    def _map_match_entities(
        self,
        match: LiveMatch,
        conn,
    ) -> LiveMatch:
        """Map external entities in a match to canonical IDs."""
        if match.team_a:
            match.team_a_id = self._map_team_id(match.team_a, conn)
        if match.team_b:
            match.team_b_id = self._map_team_id(match.team_b, conn)
        return match

    def _map_detail_entities(
        self,
        detail: LiveMatchDetail,
        conn,
    ) -> LiveMatchDetail:
        """Map external entities in match detail to canonical IDs."""
        if detail.team_a:
            detail.team_a_id = self._map_team_id(detail.team_a, conn)
        if detail.team_b:
            detail.team_b_id = self._map_team_id(detail.team_b, conn)
        if detail.striker:
            detail.striker_id = self._map_player_id(detail.striker, conn)
        if detail.non_striker:
            detail.non_striker_id = self._map_player_id(detail.non_striker, conn)
        if detail.current_bowler:
            detail.current_bowler_id = self._map_player_id(detail.current_bowler, conn)
        return detail

    def _match_to_dict(self, match: LiveMatch) -> dict:
        """Convert LiveMatch to dict for API response."""
        return {
            "match_id": match.match_id,
            "external_id": match.external_id,
            "team_a": match.team_a,
            "team_b": match.team_b,
            "team_a_id": match.team_a_id,
            "team_b_id": match.team_b_id,
            "format": match.format,
            "competition": match.competition,
            "venue": match.venue,
            "status": match.status,
            "start_time": match.start_time,
            "score_team_a": match.score_team_a,
            "score_team_b": match.score_team_b,
            "result": match.result,
        }

    def _detail_to_dict(self, detail: LiveMatchDetail) -> dict:
        """Convert LiveMatchDetail to dict for API response."""
        return {
            "match_id": detail.match_id,
            "external_id": detail.external_id,
            "team_a": detail.team_a,
            "team_b": detail.team_b,
            "team_a_id": detail.team_a_id,
            "team_b_id": detail.team_b_id,
            "format": detail.format,
            "competition": detail.competition,
            "venue": detail.venue,
            "status": detail.status,
            "result": detail.result,
            "innings": {
                "batting_team": detail.batting_team,
                "bowling_team": detail.bowling_team,
                "score": detail.current_score,
                "wickets": detail.current_wickets,
                "overs": detail.current_overs,
                "run_rate": detail.run_rate,
                "target": detail.target,
                "required_run_rate": detail.required_run_rate,
            },
            "players": {
                "striker": detail.striker,
                "striker_id": detail.striker_id,
                "non_striker": detail.non_striker,
                "non_striker_id": detail.non_striker_id,
                "bowler": detail.current_bowler,
                "bowler_id": detail.current_bowler_id,
            },
            "toss": {
                "winner": detail.toss_winner,
                "decision": detail.toss_decision,
            },
            "start_time": detail.start_time,
            "last_updated": detail.last_updated.isoformat() if detail.last_updated else None,
        }

    def get_live_matches(self, force_refresh: bool = False) -> dict:
        """
        Get current live/upcoming matches.

        Args:
            force_refresh: Force refresh from provider

        Returns:
            Dict with matches data and metadata
        """
        cache_key = "live_matches"

        # Check cache first
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                cached["cached"] = True
                cached["stale"] = False
                return cached

        # Fetch from provider
        matches = self.provider.get_live_matches()

        # Map entities if database is available
        if self.db_engine and matches:
            try:
                with self.db_engine.connect() as conn:
                    matches = [self._map_match_entities(m, conn) for m in matches]
            except Exception as e:
                logger.error(f"Entity mapping failed: {e}")

        # Build response
        result = {
            "matches": [self._match_to_dict(m) for m in matches],
            "total": len(matches),
            "source": matches[0].source if matches else None,
            "fetched_at": matches[0].fetched_at.isoformat() if matches and matches[0].fetched_at else None,
            "cached": False,
            "stale": False,
        }

        # Cache the result
        self.cache.set(cache_key, result)

        return result

    def get_match_detail(
        self,
        match_id: str,
        force_refresh: bool = False,
    ) -> Optional[dict]:
        """
        Get detailed live match state.

        Args:
            match_id: Match identifier
            force_refresh: Force refresh from provider

        Returns:
            Dict with match detail or None if not found
        """
        cache_key = f"match_{match_id}"

        # Check cache first
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached:
                cached["cached"] = True
                cached["stale"] = False
                return cached

        # Fetch from provider
        detail = self.provider.get_match_detail(match_id)

        if not detail:
            return None

        # Map entities if database is available
        if self.db_engine:
            try:
                with self.db_engine.connect() as conn:
                    detail = self._map_detail_entities(detail, conn)
            except Exception as e:
                logger.error(f"Entity mapping failed: {e}")

        # Build response
        result = self._detail_to_dict(detail)
        result["source"] = detail.source
        result["fetched_at"] = detail.fetched_at.isoformat() if detail.fetched_at else None
        result["cached"] = False
        result["stale"] = False

        # Cache the result
        self.cache.set(cache_key, result)

        return result

    def is_available(self) -> bool:
        """Check if the live data provider is available."""
        return self.provider.is_available()
