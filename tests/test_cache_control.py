from backend.utils.cache_control import (
    HISTORICAL,
    ICC_RANKINGS,
    LIVE,
    RECENT,
    edge_cache_policy,
)


def test_live_data_uses_short_edge_cache() -> None:
    assert edge_cache_policy("/api/live/", {}) == LIVE
    assert LIVE.max_age == 10
    assert LIVE.stale_while_revalidate == 15
    assert edge_cache_policy("/api/live/", {"refresh": "true"}) is None


def test_dashboard_and_recent_lists_use_ten_minute_cache() -> None:
    assert edge_cache_policy("/api/dashboard/summary", {}) == RECENT
    assert edge_cache_policy("/api/matches/", {"recent_only": "true"}) == RECENT
    assert edge_cache_policy("/api/players/", {"season": "latest"}) == RECENT
    assert RECENT.max_age == 600


def test_historical_statistics_use_three_hour_cache() -> None:
    assert edge_cache_policy("/api/players/player-id", {"format": "Test"}) == HISTORICAL
    assert edge_cache_policy("/api/teams/team-id/analytics", {}) == HISTORICAL
    assert edge_cache_policy("/api/venues/venue-id/analytics", {}) == HISTORICAL
    assert HISTORICAL.max_age == 10_800


def test_icc_rankings_use_twelve_hour_cache() -> None:
    assert edge_cache_policy("/api/rankings/icc", {"format": "Test"}) == ICC_RANKINGS
    assert ICC_RANKINGS.max_age == 43_200


def test_operational_and_unknown_routes_are_not_cached() -> None:
    assert edge_cache_policy("/api/health", {}) is None
    assert edge_cache_policy("/docs", {}) is None
    assert edge_cache_policy("/api/private", {}) is None


def test_cdn_header_enables_background_refresh_and_error_fallback() -> None:
    assert RECENT.cdn_cache_control == (
        "public, s-maxage=600, stale-while-revalidate=3600, stale-if-error=21600"
    )
