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
from datetime import datetime, timezone
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


def _as_bool(value) -> bool:
    """Normalize provider booleans that may arrive as bools or strings."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _team_names(match: dict) -> tuple[Optional[str], Optional[str]]:
    """Read both the current API `teams` shape and its legacy fields."""
    teams = match.get("teams")
    if isinstance(teams, list):
        cleaned = [str(team) for team in teams if team]
        if len(cleaned) >= 2:
            return cleaned[0], cleaned[1]
    return match.get("team-1"), match.get("team-2")


def _score_text(score: dict) -> Optional[str]:
    if not isinstance(score, dict):
        return None
    runs = score.get("r")
    if runs is None:
        return None
    wickets = score.get("w")
    overs = score.get("o")
    value = str(runs)
    if wickets is not None:
        value += f"/{wickets}"
    if overs is not None:
        value += f" ({overs} ov)"
    return value


def _scores_by_team(match: dict, team_a: Optional[str], team_b: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Map the current score-array response to the two participating teams."""
    scores = match.get("score", [])
    if isinstance(scores, dict):
        return _score_text(scores), _score_text(match.get("score-2", {}))
    if not isinstance(scores, list):
        return None, None

    mapped = {team_a: [], team_b: []}
    unassigned = []
    for score in scores:
        if not isinstance(score, dict):
            continue
        rendered = _score_text(score)
        if rendered is None:
            continue
        innings_name = str(score.get("inning", "")).lower()
        assigned = False
        for team in (team_a, team_b):
            if team and str(team).lower() in innings_name:
                mapped[team].append(rendered)
                assigned = True
                break
        if not assigned:
            unassigned.append(rendered)

    if not mapped.get(team_a) and unassigned:
        mapped[team_a] = [unassigned.pop(0)]
    if not mapped.get(team_b) and unassigned:
        mapped[team_b] = [unassigned.pop(0)]
    return " & ".join(mapped.get(team_a, [])) or None, " & ".join(mapped.get(team_b, [])) or None


class CricketDataProvider(RankingsProvider, LiveDataProvider):
    """
    CricketData.org API provider.

    Provides both ranking data and live match data from CricketData.org.
    Requires an API key set in environment variable CRICKETDATA_API_KEY.
    
    Actual API base URL: https://api.cricapi.com/v1/
    Documentation: https://cricketdata.org/how-to-use-cricket-data-api.aspx
    """

    BASE_URL = "https://api.cricapi.com/v1"

    # Mapping from our format names to API format names
    FORMAT_MAP = {
        "Test": "Test",
        "ODI": "ODI",
        "T20I": "T20",
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
            endpoint: API endpoint path (e.g., 'cricket', 'matches', 'matchScorecard')
            params: Query parameters

        Returns:
            Response JSON or None on failure
        """
        if not self.api_key:
            logger.warning("CricketData.org API key not configured")
            return None

        self._throttle()

        # CricAPI passes apikey as query parameter
        request_params = {"apikey": self.api_key}
        if params:
            request_params.update(params)

        url = f"{self.BASE_URL}/{endpoint}"
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(
                    url,
                    headers=self._get_headers(),
                    params=request_params,
                )
                response.raise_for_status()
                data = response.json()
                
                # Check for API-level errors
                if "error" in data:
                    logger.warning(f"CricketData.org API error: {data['error']}")
                    return None
                
                return data
        except httpx.TimeoutException:
            logger.error(f"CricketData.org API timeout: {endpoint}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"CricketData.org API HTTP error {e.response.status_code}: {endpoint}")
            return None
        except Exception as e:
            logger.error(f"CricketData.org API request failed: {type(e).__name__}: {endpoint}")
            return None

    # ============================================================
    # RankingsProvider Implementation
    # ============================================================
    # Note: CricketData.org does not provide a dedicated rankings endpoint.
    # Rankings are derived from player statistics, not available via free tier.
    # We return empty list and document this limitation.

    def get_player_rankings(
        self,
        format: str,
        category: str,
    ) -> list[RankingEntry]:
        """
        Get player rankings from CricketData.org.
        
        NOTE: CricketData.org free tier does not provide ICC rankings.
        This method returns empty list. For ICC rankings, a different
        provider or manual data source would be needed.

        Args:
            format: Cricket format (Test, ODI, T20I)
            category: Ranking category (batting, bowling, allrounders)

        Returns:
            List of RankingEntry objects (currently empty)
        """
        # CricketData.org does not expose ICC rankings via free tier API
        logger.info(f"ICC rankings not available via CricketData.org free tier: {format}/{category}")
        return []

    def get_team_rankings(
        self,
        format: str,
    ) -> list[TeamRankingEntry]:
        """
        Get team rankings from CricketData.org.
        
        NOTE: CricketData.org free tier does not provide team rankings.
        This method returns empty list.

        Args:
            format: Cricket format (Test, ODI, T20I)

        Returns:
            List of TeamRankingEntry objects (currently empty)
        """
        # CricketData.org does not expose team rankings via free tier API
        logger.info(f"Team rankings not available via CricketData.org free tier: {format}")
        return []

    # ============================================================
    # LiveDataProvider Implementation
    # ============================================================

    def get_live_matches(self) -> list[LiveMatch]:
        """
        Get current live/upcoming matches from CricketData.org.
        
        Uses the 'currentMatches' endpoint (actual CricAPI endpoint).
        
        Returns:
            List of LiveMatch objects
        """
        # Actual CricAPI endpoint: /v1/currentMatches
        data = self._make_request("currentMatches")

        if not data:
            return []

        matches = []
        fetched_at = datetime.now(timezone.utc)

        # CricAPI response structure: {"data": [{...}, ...]}
        match_list = data.get("data", data.get("matches", []))
        if isinstance(match_list, dict) and match_list.get("id"):
            match_list = [match_list]
        if not isinstance(match_list, list):
            logger.warning(f"Unexpected response format: {type(match_list)}")
            return []

        for match in match_list:
            try:
                # Normalize status
                if _as_bool(match.get("matchEnded", False)):
                    status = MatchStatus.COMPLETED.value
                elif _as_bool(match.get("matchStarted", False)):
                    status = MatchStatus.LIVE.value
                else:
                    status = MatchStatus.UPCOMING.value

                # Extract team names
                team_a, team_b = _team_names(match)
                
                # Skip if no team names
                if not team_a and not team_b:
                    continue

                score_team_a, score_team_b = _scores_by_team(match, team_a, team_b)
                match_id = str(match.get("id", match.get("unique_id", "")))
                live_match = LiveMatch(
                    match_id=match_id,
                    external_id=match_id,
                    team_a=str(team_a) if team_a else None,
                    team_b=str(team_b) if team_b else None,
                    format=match.get("matchType", match.get("type", "")),
                    competition=match.get("seriesName", match.get("series", match.get("series_id", ""))),
                    venue=match.get("venue", ""),
                    status=status,
                    start_time=match.get("dateTimeGMT", match.get("date", "")),
                    score_team_a=score_team_a,
                    score_team_b=score_team_b,
                    result=match.get("status", match.get("result", "")),
                    fetched_at=fetched_at,
                    source="cricketdata.org",
                )
                matches.append(live_match)
            except Exception as e:
                logger.warning(f"Failed to parse match: {e}")
                continue

        logger.info(f"Fetched {len(matches)} matches from CricketData.org")
        return matches

    def get_match_detail(
        self,
        match_id: str,
    ) -> Optional[LiveMatchDetail]:
        """
        Get detailed live match state from CricketData.org.
        
        Uses the current 'match_scorecard' endpoint.

        Args:
            match_id: Match unique_id from CricAPI

        Returns:
            LiveMatchDetail or None if not found
        """
        data = self._make_request("match_scorecard", {"id": match_id})

        if not data:
            return None

        # CricAPI response: the match data is at the top level
        match = data.get("data", data)
        fetched_at = datetime.now(timezone.utc)

        # Extract team names
        team_a, team_b = _team_names(match)

        # Determine status
        match_started = _as_bool(match.get("matchStarted", False))
        match_ended = _as_bool(match.get("matchEnded", False))
        
        if match_ended:
            status = MatchStatus.COMPLETED.value
        elif match_started:
            status = MatchStatus.LIVE.value
        else:
            status = MatchStatus.UPCOMING.value

        # Extract innings info if available
        score_value = match.get("score", {})
        score_rows = score_value if isinstance(score_value, list) else [score_value]
        score_rows = [row for row in score_rows if isinstance(row, dict)]
        score_data = score_rows[-1] if score_rows else {}
        inning_name = str(score_data.get("inning", ""))
        batting_team = next(
            (team for team in (team_a, team_b) if team and str(team).lower() in inning_name.lower()),
            None,
        )
        bowling_team = team_b if batting_team == team_a else team_a if batting_team == team_b else None
        
        detail = LiveMatchDetail(
            match_id=match_id,
            external_id=str(match.get("id", match.get("unique_id", match_id))),
            team_a=str(team_a) if team_a else None,
            team_b=str(team_b) if team_b else None,
            format=match.get("matchType", match.get("type", "")),
            competition=match.get("seriesName", match.get("series", match.get("series_id", ""))),
            venue=match.get("venue", ""),
            status=status,
            result=match.get("status", match.get("result", "")),
            batting_team=batting_team,
            bowling_team=bowling_team,
            current_score=_score_text(score_data),
            current_wickets=score_data.get("w"),
            current_overs=score_data.get("o"),
            run_rate=score_data.get("rr"),
            target=match.get("target", {}).get("runs") if isinstance(match.get("target"), dict) else None,
            required_run_rate=None,  # Not directly available
            toss_winner=match.get("tossWinner", match.get("toss_winner_team", "")),
            toss_decision=match.get("tossChoice", match.get("toss_winner_elected", "")),
            start_time=match.get("dateTimeGMT", ""),
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
