"""Official ICC men's rankings provider.

The ICC rankings pages load their tables from the public Sportz Interactive
JSON feed.  This adapter consumes that same feed and falls back to a bundled
snapshot when the upstream service is temporarily unavailable.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from backend.providers.base import RankingEntry, RankingsProvider, TeamRankingEntry

logger = logging.getLogger(__name__)


class ICCRankingsProvider(RankingsProvider):
    """Read the same official ranking feed used by icc-cricket.com."""

    BASE_URL = "https://assets-icc.sportz.io/cricket/v1/ranking"
    DEFAULT_CLIENT_ID = "tPZJbRgIub3Vua93/DWtyQ=="
    FORMAT_MAP = {"Test": "test", "ODI": "odi", "T20I": "t20"}
    CATEGORY_MAP = {
        "batting": "bat",
        "bowling": "bowl",
        "allrounder": "allrounder",
        "allrounders": "allrounder",
        "teams": "team",
    }

    def __init__(
        self,
        client_id: Optional[str] = None,
        snapshot_path: Optional[Path] = None,
        timeout_seconds: float = 12.0,
    ) -> None:
        self.client_id = client_id or os.getenv(
            "ICC_RANKINGS_CLIENT_ID", self.DEFAULT_CLIENT_ID
        )
        self.snapshot_path = snapshot_path or (
            Path(__file__).resolve().parents[1] / "data" / "icc_rankings_snapshot.json"
        )
        self.timeout_seconds = timeout_seconds
        self._last_source = "icc-official"

    @staticmethod
    def _parse_int(value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(str(value).replace(",", "").strip())
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_change(value: Any) -> int:
        text = str(value or "").strip()
        match = re.search(r"([+-]\d+)", text)
        return int(match.group(1)) if match else 0

    @staticmethod
    def _source_id(value: Any) -> Optional[str]:
        return str(value) if value not in (None, "") else None

    @classmethod
    def _resolved_rank(cls, raw_rank: Any, previous_rank: int) -> int:
        rank = cls._parse_int(raw_rank)
        return rank if rank is not None else previous_rank

    def _request(self, format: str, category: str) -> dict:
        format_key = self.FORMAT_MAP.get(format)
        category_key = self.CATEGORY_MAP.get(category)
        if not format_key or not category_key:
            return {}

        params = {
            "client_id": self.client_id,
            "comp_type": format_key,
            "lang": "en",
            "feed_format": "json",
            "type": category_key,
        }
        headers = {
            "Accept": "application/json",
            "User-Agent": "Crease/1.0 (+https://www.icc-cricket.com/rankings)",
        }
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = client.get(self.BASE_URL, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()

        data = payload.get("data") or {}
        ranking = data.get("bat-rank") or {}
        if not isinstance(ranking.get("rank"), list):
            raise ValueError("ICC ranking feed returned an unexpected payload")
        self._last_source = "icc-official"
        return ranking

    def _snapshot(self, format: str, category: str) -> dict:
        try:
            payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            ranking = payload["rankings"][format][category]
            self._last_source = "icc-official-snapshot"
            return ranking
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("ICC ranking snapshot unavailable: %s", exc)
            return {}

    def _load(self, format: str, category: str) -> dict:
        try:
            return self._request(format, category)
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            logger.warning(
                "Official ICC ranking request failed for %s/%s; using snapshot: %s",
                format,
                category,
                exc,
            )
            return self._snapshot(format, category)

    def get_player_rankings(self, format: str, category: str) -> list[RankingEntry]:
        normalized_category = (
            "allrounder" if category == "allrounders" else category
        )
        ranking = self._load(format, normalized_category)
        rows = ranking.get("entries", ranking.get("rank", []))
        fetched_at = datetime.now(timezone.utc)
        output: list[RankingEntry] = []
        previous_rank = 0

        for raw in rows:
            rank = self._resolved_rank(raw.get("no", raw.get("rank")), previous_rank)
            if rank <= 0:
                continue
            previous_rank = rank
            output.append(
                RankingEntry(
                    rank=rank,
                    name=str(raw.get("Player-name", raw.get("name", ""))).strip(),
                    country=raw.get("Country_name", raw.get("country")),
                    rating=self._parse_int(raw.get("Points", raw.get("rating"))),
                    change=self._parse_change(raw.get("change")),
                    source_id=self._source_id(raw.get("Player_id", raw.get("source_id"))),
                    format=format,
                    category=normalized_category,
                    ranking_date=ranking.get("rank_date") or raw.get("rankdate"),
                    fetched_at=fetched_at,
                    source=self._last_source,
                    career_best=raw.get("careerbest", raw.get("career_best")),
                )
            )
        return output

    def get_team_rankings(self, format: str) -> list[TeamRankingEntry]:
        ranking = self._load(format, "teams")
        rows = ranking.get("entries", ranking.get("rank", []))
        fetched_at = datetime.now(timezone.utc)
        output: list[TeamRankingEntry] = []
        previous_rank = 0

        for raw in rows:
            rank = self._resolved_rank(raw.get("no", raw.get("rank")), previous_rank)
            if rank <= 0:
                continue
            previous_rank = rank
            output.append(
                TeamRankingEntry(
                    rank=rank,
                    team_name=str(
                        raw.get("team_name", raw.get("team", raw.get("Country", "")))
                    ).strip(),
                    rating=self._parse_int(raw.get("Rating", raw.get("rating"))),
                    points=self._parse_int(raw.get("Points", raw.get("points"))),
                    matches=self._parse_int(raw.get("Matches", raw.get("matches"))),
                    change=self._parse_change(raw.get("change")),
                    source_id=self._source_id(raw.get("team_id", raw.get("source_id"))),
                    format=format,
                    ranking_date=ranking.get("rank_date") or raw.get("rankdate"),
                    fetched_at=fetched_at,
                    source=self._last_source,
                )
            )
        return output

    def is_available(self) -> bool:
        # The public ICC feed needs no private credential.  The bundled snapshot
        # also keeps this provider available during transient network failures.
        return bool(self.client_id or self.snapshot_path.exists())
