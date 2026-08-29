"""
CricketData.org Provider
========================

Implementation of ranking and live data providers using CricketData.org API.

CricketData.org (formerly CricAPI) offers:
- Free tier: 100 API hits per day
- Live scores
- Player statistics
- Match schedules
- Team rankings

API Base URL: https://api.cricdata.org
Documentation: https://cricketdata.org/how-to-use-cricket-data-api.aspx

Note: This provider requires an API key from https://cricketdata.org
"""

import os
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import httpx

from backend.providers.base import (
    RankingsProvider,
    LiveDataProvider,
    RankingEntry,
    TeamRankingEntry,
    LiveMatch,
    LiveMatchDetail,
    MatchStatus,
)

logger = logging.getLogger(__name__)


class CricketDataProvider(RankingsProvider, LiveDataProvider):
    """
    CricketData.org API provider.

    Provides both ranking data and live match data from CricketData.org.
    Requires an API key set in environment variable CRICKETDATA_API_KEY.
    """

    BASE_URL = "https://api.cricdata.org"

    # Mapping from our format names to API format names
    FORMAT_MAP = {
        "Test": "Test",
        "ODI": "ODI",
        "T20I": "T20",
    }

    # Mapping from our category names to API category names
    CATEGORY_MAP = {
        "batting": "batting",
        "bowling": "bowling",
        "allrounders": "allrounders",
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the provider.

        Args:
            api_key: CricketData.org API key. If not provided,
                     reads from CRICKETDATA_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("CRICKETDATA_API_KEY")
        self._last_request_time = 0
        self._min_request_interval = 1.0  # Minimum 1 second between requests

    def _get_headers(self) -> dict:
        """Get HTTP headers for API requests."""
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    def _throttle(self):
        """Simple request throttling to avoid rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """
        Make an API request with error handling.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Response JSON or None on failure
        """
        if not self.api_key:
            logger.warning("CricketData.org API key not configured")
            return None

        self._throttle()

        url = f"{self.BASE_URL}{endpoint}"
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    url,
                    headers=self._get_headers(),
                    params=params or {},
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.error(f"CricketData.org API timeout: {endpoint}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"CricketData.org API error {e.response.status_code}: {endpoint}")
            return None
        except Exception as e:
            logger.error(f"CricketData.org API request failed: {e}")
            return None

    # ============================================================
    # RankingsProvider Implementation
    # ============================================================

    def get_player_rankings(
        self,
        format: str,
        category: str,
    ) -> list[RankingEntry]:
        """
        Get player rankings from CricketData.org.

        Args:
            format: Cricket format (Test, ODI, T20I)
            category: Ranking category (batting, bowling, allrounders)

        Returns:
            List of RankingEntry objects
        """
        api_format = self.FORMAT_MAP.get(format)
        api_category = self.CATEGORY_MAP.get(category)

        if not api_format or not api_category:
            logger.warning(f"Invalid format/category: {format}/{category}")
            return []

        # CricketData.org rankings endpoint
        # Note: The exact endpoint structure may vary; this is based on
        # common cricket API patterns
        endpoint = "/v1/rankings/batting" if category == "batting" else \
                   "/v1/rankings/bowling" if category == "bowling" else \
                   "/v1/rankings/allrounders"

        params = {"format": api_format}
        data = self._make_request(endpoint, params)

        if not data:
            return []

        rankings = []
        fetched_at = datetime.utcnow()

        # Parse response - adapt to actual API response structure
        # The exact structure depends on CricketData.org's API format
        players = data.get("rankings", data.get("data", []))
        if isinstance(players, list):
            for i, player in enumerate(players[:100], 1):
                entry = RankingEntry(
                    rank=player.get("rank", i),
                    name=player.get("name", player.get("player", "")),
                    country=player.get("country", player.get("team", "")),
                    rating=player.get("rating", player.get("points")),
                    change=player.get("change", player.get("movement")),
                    source_id=str(player.get("id", "")),
                    format=format,
                    category=category,
                    fetched_at=fetched_at,
                    source="cricketdata.org",
                )
                rankings.append(entry)

        logger.info(f"Fetched {len(rankings)} {format} {category} rankings")
        return rankings

    def get_team_rankings(
        self,
        format: str,
    ) -> list[TeamRankingEntry]:
        """
        Get team rankings from CricketData.org.

        Args:
            format: Cricket format (Test, ODI, T20I)

        Returns:
            List of TeamRankingEntry objects
        """
        api_format = self.FORMAT_MAP.get(format)
        if not api_format:
            logger.warning(f"Invalid format: {format}")
            return []

        endpoint = "/v1/rankings/teams"
        params = {"format": api_format}
        data = self._make_request(endpoint, params)

        if not data:
            return []

        rankings = []
        fetched_at = datetime.utcnow()

        teams = data.get("rankings", data.get("data", []))
        if isinstance(teams, list):
            for i, team in enumerate(teams[:20], 1):
                entry = TeamRankingEntry(
                    rank=team.get("rank", i),
                    team_name=team.get("name", team.get("team", "")),
                    rating=team.get("rating", team.get("points")),
                    points=team.get("points"),
                    change=team.get("change", team.get("movement")),
                    source_id=str(team.get("id", "")),
                    format=format,
                    fetched_at=fetched_at,
                    source="cricketdata.org",
                )
                rankings.append(entry)

        logger.info(f"Fetched {len(rankings)} {format} team rankings")
        return rankings

    # ============================================================
    # LiveDataProvider Implementation
    # ============================================================

    def get_live_matches(self) -> list[LiveMatch]:
        """
        Get current live/upcoming matches from CricketData.org.

        Returns:
            List of LiveMatch objects
        """
        endpoint = "/v1/matches/current"
        data = self._make_request(endpoint)

        if not data:
            return []

        matches = []
        fetched_at = datetime.utcnow()

        match_list = data.get("matches", data.get("data", []))
        if isinstance(match_list, list):
            for match in match_list:
                status_str = match.get("status", match.get("matchStatus", "")).lower()
                if "live" in status_str or "in progress" in status_str:
                    status = MatchStatus.LIVE.value
                elif "complete" in status_str or "result" in status_str:
                    status = MatchStatus.COMPLETED.value
                elif "upcoming" in status_str or "schedule" in status_str:
                    status = MatchStatus.UPCOMING.value
                else:
                    status = MatchStatus.UNKNOWN.value

                teams = match.get("teams", [])
                team_a = teams[0] if len(teams) > 0 else match.get("team1", "")
                team_b = teams[1] if len(teams) > 1 else match.get("team2", "")

                live_match = LiveMatch(
                    match_id=str(match.get("id", match.get("matchId", ""))),
                    external_id=str(match.get("id", "")),
                    team_a=team_a if isinstance(team_a, str) else team_a.get("name", ""),
                    team_b=team_b if isinstance(team_b, str) else team_b.get("name", ""),
                    format=match.get("format", match.get("matchFormat", "")),
                    competition=match.get("series", match.get("tournament", "")),
                    venue=match.get("venue", ""),
                    status=status,
                    start_time=match.get("startDate", match.get("date", "")),
                    score_team_a=match.get("team1Score", ""),
                    score_team_b=match.get("team2Score", ""),
                    result=match.get("result", ""),
                    fetched_at=fetched_at,
                    source="cricketdata.org",
                )
                matches.append(live_match)

        logger.info(f"Fetched {len(matches)} matches from CricketData.org")
        return matches

    def get_match_detail(
        self,
        match_id: str,
    ) -> Optional[LiveMatchDetail]:
        """
        Get detailed live match state from CricketData.org.

        Args:
            match_id: Match identifier

        Returns:
            LiveMatchDetail or None if not found
        """
        endpoint = f"/v1/matches/{match_id}/scorecard"
        data = self._make_request(endpoint)

        if not data:
            return None

        match = data.get("match", data)
        fetched_at = datetime.utcnow()

        teams = match.get("teams", [])
        team_a = teams[0] if len(teams) > 0 else match.get("team1", "")
        team_b = teams[1] if len(teams) > 1 else match.get("team2", "")

        # Extract current innings info
        innings = match.get("innings", [])
        current_innings = innings[-1] if innings else {}

        status_str = match.get("status", match.get("matchStatus", "")).lower()
        if "live" in status_str or "in progress" in status_str:
            status = MatchStatus.LIVE.value
        elif "complete" in status_str:
            status = MatchStatus.COMPLETED.value
        else:
            status = MatchStatus.UPCOMING.value

        detail = LiveMatchDetail(
            match_id=match_id,
            external_id=str(match.get("id", "")),
            team_a=team_a if isinstance(team_a, str) else team_a.get("name", ""),
            team_b=team_b if isinstance(team_b, str) else team_b.get("name", ""),
            format=match.get("format", ""),
            competition=match.get("series", ""),
            venue=match.get("venue", ""),
            status=status,
            result=match.get("result", ""),
            batting_team=current_innings.get("battingTeam", ""),
            bowling_team=current_innings.get("bowlingTeam", ""),
            current_score=current_innings.get("score", ""),
            current_wickets=current_innings.get("wickets"),
            current_overs=current_innings.get("overs"),
            run_rate=current_innings.get("runRate"),
            target=match.get("target"),
            required_run_rate=current_innings.get("requiredRunRate"),
            toss_winner=match.get("tossWinner", ""),
            toss_decision=match.get("tossDecision", ""),
            start_time=match.get("startDate", ""),
            last_updated=fetched_at,
            fetched_at=fetched_at,
            source="cricketdata.org",
        )

        return detail

    def is_available(self) -> bool:
        """Check if CricketData.org provider is configured."""
        return self.api_key is not None


class MockCricketDataProvider(RankingsProvider, LiveDataProvider):
    """
    Mock provider for testing.

    Returns predefined data without making external API calls.
    """

    def __init__(self):
        """Initialize with mock data."""
        self._available = True

    def get_player_rankings(
        self,
        format: str,
        category: str,
    ) -> list[RankingEntry]:
        """Return mock player rankings."""
        mock_data = {
            ("Test", "batting"): [
                RankingEntry(rank=1, name="Joe Root", country="England", rating=900, format="Test", category="batting", source="mock"),
                RankingEntry(rank=2, name="Kane Williamson", country="New Zealand", rating=880, format="Test", category="batting", source="mock"),
                RankingEntry(rank=3, name="Steve Smith", country="Australia", rating=870, format="Test", category="batting", source="mock"),
                RankingEntry(rank=4, name="Marnus Labuschagne", country="Australia", rating=860, format="Test", category="batting", source="mock"),
                RankingEntry(rank=5, name="Virat Kohli", country="India", rating=850, format="Test", category="batting", source="mock"),
            ],
            ("ODI", "batting"): [
                RankingEntry(rank=1, name="Shubman Gill", country="India", rating=850, format="ODI", category="batting", source="mock"),
                RankingEntry(rank=2, name="Babar Azam", country="Pakistan", rating=840, format="ODI", category="batting", source="mock"),
                RankingEntry(rank=3, name="Virat Kohli", country="India", rating=830, format="ODI", category="batting", source="mock"),
                RankingEntry(rank=4, name="Rohit Sharma", country="India", rating=820, format="ODI", category="batting", source="mock"),
                RankingEntry(rank=5, name="Heinrich Klaasen", country="South Africa", rating=810, format="ODI", category="batting", source="mock"),
            ],
            ("T20I", "batting"): [
                RankingEntry(rank=1, name="Suryakumar Yadav", country="India", rating=900, format="T20I", category="batting", source="mock"),
                RankingEntry(rank=2, name="Travis Head", country="Australia", rating=850, format="T20I", category="batting", source="mock"),
                RankingEntry(rank=3, name="Phil Salt", country="England", rating=830, format="T20I", category="batting", source="mock"),
                RankingEntry(rank=4, name="Aaron Finch", country="Australia", rating=810, format="T20I", category="batting", source="mock"),
                RankingEntry(rank=5, name="Jos Buttler", country="England", rating=800, format="T20I", category="batting", source="mock"),
            ],
        }
        return mock_data.get((format, category), [])

    def get_team_rankings(
        self,
        format: str,
    ) -> list[TeamRankingEntry]:
        """Return mock team rankings."""
        mock_data = {
            "Test": [
                TeamRankingEntry(rank=1, team_name="India", rating=121, format="Test", source="mock"),
                TeamRankingEntry(rank=2, team_name="Australia", rating=116, format="Test", source="mock"),
                TeamRankingEntry(rank=3, team_name="England", rating=114, format="Test", source="mock"),
                TeamRankingEntry(rank=4, team_name="South Africa", rating=106, format="Test", source="mock"),
                TeamRankingEntry(rank=5, team_name="New Zealand", rating=100, format="Test", source="mock"),
            ],
            "ODI": [
                TeamRankingEntry(rank=1, team_name="India", rating=119, format="ODI", source="mock"),
                TeamRankingEntry(rank=2, team_name="Australia", rating=116, format="ODI", source="mock"),
                TeamRankingEntry(rank=3, team_name="South Africa", rating=112, format="ODI", source="mock"),
                TeamRankingEntry(rank=4, team_name="England", rating=111, format="ODI", source="mock"),
                TeamRankingEntry(rank=5, team_name="Pakistan", rating=105, format="ODI", source="mock"),
            ],
            "T20I": [
                TeamRankingEntry(rank=1, team_name="India", rating=264, format="T20I", source="mock"),
                TeamRankingEntry(rank=2, team_name="England", rating=261, format="T20I", source="mock"),
                TeamRankingEntry(rank=3, team_name="Australia", rating=256, format="T20I", source="mock"),
                TeamRankingEntry(rank=4, team_name="South Africa", rating=252, format="T20I", source="mock"),
                TeamRankingEntry(rank=5, team_name="West Indies", rating=247, format="T20I", source="mock"),
            ],
        }
        return mock_data.get(format, [])

    def get_live_matches(self) -> list[LiveMatch]:
        """Return mock live matches."""
        return [
            LiveMatch(
                match_id="mock-001",
                team_a="India",
                team_b="Australia",
                format="ODI",
                competition="Border-Gavaskar Trophy",
                venue="Melbourne Cricket Ground",
                status=MatchStatus.LIVE.value,
                score_team_a="245/6 (45.2 overs)",
                score_team_b="",
                source="mock",
            ),
        ]

    def get_match_detail(
        self,
        match_id: str,
    ) -> Optional[LiveMatchDetail]:
        """Return mock match detail."""
        if match_id != "mock-001":
            return None

        return LiveMatchDetail(
            match_id=match_id,
            team_a="India",
            team_b="Australia",
            format="ODI",
            competition="Border-Gavaskar Trophy",
            venue="Melbourne Cricket Ground",
            status=MatchStatus.LIVE.value,
            batting_team="India",
            bowling_team="Australia",
            current_score="245/6",
            current_wickets=6,
            current_overs=45.2,
            run_rate=5.41,
            target=280,
            required_run_rate=6.25,
            striker="Virat Kohli",
            non_striker="KL Rahul",
            current_bowler="Pat Cummins",
            source="mock",
        )

    def is_available(self) -> bool:
        """Mock provider is always available."""
        return self._available
