"""Edge-cache policy for public Crease API responses.

The browser always revalidates while Vercel's CDN keeps a shared copy.  This
keeps historical cricket data close to visitors without making live data look
fresher than it is.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class EdgeCachePolicy:
    name: str
    max_age: int
    stale_while_revalidate: int
    stale_if_error: int

    @property
    def cdn_cache_control(self) -> str:
        return (
            f"public, s-maxage={self.max_age}, "
            f"stale-while-revalidate={self.stale_while_revalidate}, "
            f"stale-if-error={self.stale_if_error}"
        )


# Live responses stay at the edge for only a few seconds.  Once expired, the
# stale response can be served briefly while a new score is fetched.
LIVE = EdgeCachePolicy(
    name="live",
    max_age=10,
    stale_while_revalidate=15,
    stale_if_error=60,
)

# Dashboard and rolling/recent data may be ten minutes old, with background
# refreshes preventing a visitor from blocking on database aggregation.
RECENT = EdgeCachePolicy(
    name="recent",
    max_age=10 * 60,
    stale_while_revalidate=60 * 60,
    stale_if_error=6 * 60 * 60,
)

# Career and historical analytics change only when a data refresh is shipped.
HISTORICAL = EdgeCachePolicy(
    name="historical",
    max_age=3 * 60 * 60,
    stale_while_revalidate=6 * 60 * 60,
    stale_if_error=24 * 60 * 60,
)

# ICC publishes rankings weekly, so a twelve-hour edge lifetime is comfortably
# inside the requested 6-24 hour window.
ICC_RANKINGS = EdgeCachePolicy(
    name="icc-rankings",
    max_age=12 * 60 * 60,
    stale_while_revalidate=24 * 60 * 60,
    stale_if_error=48 * 60 * 60,
)


HISTORICAL_PREFIXES = (
    "/api/players",
    "/api/teams",
    "/api/venues",
    "/api/matches",
    "/api/matchups",
    "/api/analytics",
    "/api/competitions",
    "/api/rankings",
)


def _matches_prefix(path: str, prefix: str) -> bool:
    normalized = path.rstrip("/") or "/"
    return normalized == prefix or normalized.startswith(f"{prefix}/")


def _is_true(value: str | None) -> bool:
    return bool(value and value.casefold() in {"1", "true", "yes", "on"})


def edge_cache_policy(
    path: str,
    query_params: Mapping[str, str],
) -> EdgeCachePolicy | None:
    """Return the shared-cache policy for a public GET request."""
    if _matches_prefix(path, "/api/live"):
        if _is_true(query_params.get("refresh")):
            return None
        return LIVE

    if _matches_prefix(path, "/api/rankings/icc"):
        return ICC_RANKINGS

    if _matches_prefix(path, "/api/dashboard") or _matches_prefix(path, "/api/news"):
        return RECENT

    # The dashboard uses list endpoints with these flags, so classify them as
    # recent even though the same routes also serve long-lived career data.
    if (
        _is_true(query_params.get("recent_only"))
        or _is_true(query_params.get("completed_only"))
        or query_params.get("season", "").casefold() == "latest"
    ):
        if any(_matches_prefix(path, prefix) for prefix in HISTORICAL_PREFIXES):
            return RECENT

    if any(_matches_prefix(path, prefix) for prefix in HISTORICAL_PREFIXES):
        return HISTORICAL

    # Health checks, documentation and future private endpoints are uncached
    # unless they are explicitly added above.
    return None
