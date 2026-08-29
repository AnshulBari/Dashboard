"""
Phase 5.8 Tests: Analytical Query Layer Validation
====================================================

Tests all analytical dimensions against the production database.
Verifies format isolation, data correctness, and query performance.

Run: python -m pytest tests/test_phase5_8.py -v
"""

import os
import sys
import time
import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Shared engine for all tests
_engine = create_engine(
    DATABASE_URL, pool_pre_ping=True,
    pool_size=10, max_overflow=20, pool_timeout=60,
)


def _q(sql, params=None):
    """Execute a query and return list of dicts."""
    with _engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).fetchall()
        return [dict(r._mapping) for r in rows]


def _scalar(sql, params=None):
    """Execute a query and return scalar."""
    with _engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar()


# Known entities
KOHLI = _scalar("SELECT id FROM players WHERE canonical_name = 'Virat Kohli'")
INDIA = _scalar("SELECT id FROM teams WHERE canonical_name = 'India'")
AUSTRALIA = _scalar("SELECT id FROM teams WHERE canonical_name = 'Australia'")
IPL_COMP = _scalar("SELECT id FROM competitions WHERE name = 'Indian Premier League'")


# ============================================================
# PLAYER ANALYTICS
# ============================================================


class TestPlayerCareer:
    def test_kohli_career_has_all_formats(self):
        from backend.services.analytics import player_career
        with _engine.connect() as conn:
            result = player_career(conn, KOHLI)
        assert "T20" in result["batting"]
        assert "T20I" in result["batting"]
        assert "ODI" in result["batting"]
        assert "Test" in result["batting"]

    def test_kohli_odi_runs(self):
        from backend.services.analytics import player_career
        with _engine.connect() as conn:
            result = player_career(conn, KOHLI)
        assert result["batting"]["ODI"]["runs"] >= 15000

    def test_kohli_test_runs(self):
        from backend.services.analytics import player_career
        with _engine.connect() as conn:
            result = player_career(conn, KOHLI)
        assert result["batting"]["Test"]["runs"] >= 8000

    def test_kohli_form_scores(self):
        from backend.services.analytics import player_career
        with _engine.connect() as conn:
            result = player_career(conn, KOHLI)
        assert len(result["form"]) >= 3


class TestPlayerByYear:
    def test_kohli_odi_by_year(self):
        from backend.services.analytics import player_by_year
        with _engine.connect() as conn:
            result = player_by_year(conn, KOHLI, "ODI")
        assert len(result) >= 10
        assert all("year" in r and "runs" in r for r in result)

    def test_kohli_year_range(self):
        from backend.services.analytics import player_by_year
        with _engine.connect() as conn:
            result = player_by_year(conn, KOHLI, "ODI")
        years = [r["year"] for r in result]
        assert min(years) <= 2010
        assert max(years) >= 2024

    def test_kohli_ipl_by_year(self):
        from backend.services.analytics import player_by_year
        with _engine.connect() as conn:
            result = player_by_year(conn, KOHLI, "T20")
        assert len(result) >= 10


class TestPlayerByCompetition:
    def test_kohli_by_competition(self):
        from backend.services.analytics import player_by_competition
        with _engine.connect() as conn:
            result = player_by_competition(conn, KOHLI, "T20")
        competitions = [r["competition"] for r in result]
        assert "Indian Premier League" in competitions

    def test_kohli_ipl_stats(self):
        from backend.services.analytics import player_by_competition
        with _engine.connect() as conn:
            result = player_by_competition(conn, KOHLI, "T20")
        ipl = [r for r in result if r["competition"] == "Indian Premier League"]
        assert len(ipl) == 1
        assert ipl[0]["runs"] >= 7000


class TestPlayerBySeason:
    def test_kohli_by_season(self):
        from backend.services.analytics import player_by_season
        with _engine.connect() as conn:
            result = player_by_season(conn, KOHLI, "T20")
        assert len(result) >= 5


class TestPlayerVsOpponent:
    def test_kohli_vs_australia_od(self):
        from backend.services.analytics import player_vs_opponent
        with _engine.connect() as conn:
            result = player_vs_opponent(conn, KOHLI, "ODI")
        aus = [r for r in result if r["opponent"] == "Australia"]
        assert len(aus) == 1
        assert aus[0]["matches"] >= 30

    def test_kohli_vs_australia_test(self):
        from backend.services.analytics import player_vs_opponent
        with _engine.connect() as conn:
            result = player_vs_opponent(conn, KOHLI, "Test")
        aus = [r for r in result if r["opponent"] == "Australia"]
        assert len(aus) == 1
        assert aus[0]["matches"] >= 10


class TestPlayerAtVenue:
    def test_kohli_at_venue(self):
        from backend.services.analytics import player_at_venue
        with _engine.connect() as conn:
            result = player_at_venue(conn, KOHLI, "ODI")
        assert len(result) >= 10


class TestPlayerMatchHistory:
    def test_kohli_recent_matches(self):
        from backend.services.analytics import player_match_history
        with _engine.connect() as conn:
            result = player_match_history(conn, KOHLI, "ODI", limit=10)
        assert len(result) <= 10
        assert all("match_id" in r and "runs" in r for r in result)


# ============================================================
# TEAM ANALYTICS
# ============================================================


class TestTeamByFormat:
    def test_india_has_all_formats(self):
        from backend.services.analytics import team_by_format
        with _engine.connect() as conn:
            result = team_by_format(conn, INDIA)
        formats = [r["format"] for r in result]
        assert "ODI" in formats
        assert "Test" in formats


class TestTeamByYear:
    def test_india_by_year(self):
        from backend.services.analytics import team_by_year
        with _engine.connect() as conn:
            result = team_by_year(conn, INDIA, "ODI")
        assert len(result) >= 10
        assert all("year" in r and "wins" in r for r in result)


class TestTeamVsTeam:
    def test_india_vs_australia_overall(self):
        from backend.services.analytics import team_vs_team
        with _engine.connect() as conn:
            result = team_vs_team(conn, INDIA, AUSTRALIA)
        total = sum(r["matches"] for r in result["by_format"])
        assert total >= 100

    def test_india_vs_australia_od(self):
        from backend.services.analytics import team_vs_team
        with _engine.connect() as conn:
            result = team_vs_team(conn, INDIA, AUSTRALIA, "ODI")
        assert len(result["by_format"]) == 1
        assert result["by_format"][0]["format"] == "ODI"
        assert result["by_format"][0]["matches"] >= 50

    def test_india_vs_australia_test(self):
        from backend.services.analytics import team_vs_team
        with _engine.connect() as conn:
            result = team_vs_team(conn, INDIA, AUSTRALIA, "Test")
        assert result["by_format"][0]["matches"] >= 30
        assert result["by_format"][0]["draws"] >= 5


class TestTeamAtVenue:
    def test_india_at_venue(self):
        from backend.services.analytics import team_at_venue
        with _engine.connect() as conn:
            result = team_at_venue(conn, INDIA, "ODI")
        assert len(result) >= 5


class TestTeamByCompetition:
    def test_india_by_competition(self):
        from backend.services.analytics import team_by_competition
        with _engine.connect() as conn:
            result = team_by_competition(conn, INDIA)
        assert len(result) >= 1


class TestTeamMatchHistory:
    def test_india_recent_matches(self):
        from backend.services.analytics import team_match_history
        with _engine.connect() as conn:
            result = team_match_history(conn, INDIA, "ODI", limit=10)
        assert len(result) <= 10


class TestTeamTrend:
    def test_india_trend(self):
        from backend.services.analytics import team_year_trend
        with _engine.connect() as conn:
            result = team_year_trend(conn, INDIA, "ODI")
        assert len(result) >= 10
        assert all("win_rate" in r for r in result)


# ============================================================
# COMPETITION ANALYTICS
# ============================================================


class TestCompetitionSummary:
    def test_ipl_summary(self):
        from backend.services.analytics import competition_summary
        with _engine.connect() as conn:
            result = competition_summary(conn, IPL_COMP)
        assert result["name"] == "Indian Premier League"
        assert len(result["seasons"]) >= 10


class TestSeasonMatches:
    def test_ipl_season_matches(self):
        from backend.services.analytics import competition_summary, competition_season_matches
        with _engine.connect() as conn:
            summary = competition_summary(conn, IPL_COMP)
            first_season = summary["seasons"][0]
            result = competition_season_matches(conn, first_season["id"], limit=10)
        assert result["total"] >= 50
        assert len(result["matches"]) <= 10


# ============================================================
# VENUE ANALYTICS
# ============================================================


class TestVenueAnalytics:
    def test_venue_by_format(self):
        from backend.services.analytics import venue_by_format
        vid = _scalar(
            "SELECT venue_id FROM matches GROUP BY venue_id ORDER BY COUNT(*) DESC LIMIT 1"
        )
        with _engine.connect() as conn:
            result = venue_by_format(conn, vid)
        assert len(result) >= 1

    def test_venue_team_performance(self):
        from backend.services.analytics import venue_team_performance
        vid = _scalar(
            "SELECT venue_id FROM matches GROUP BY venue_id ORDER BY COUNT(*) DESC LIMIT 1"
        )
        with _engine.connect() as conn:
            result = venue_team_performance(conn, vid, "ODI")
        assert len(result) >= 1


# ============================================================
# MATCH ANALYTICS
# ============================================================


class TestMatchDetail:
    def test_match_detail_has_scorecard(self):
        from backend.services.analytics import match_detail
        mid = _scalar("SELECT id FROM matches WHERE format = 'ODI' LIMIT 1")
        with _engine.connect() as conn:
            result = match_detail(conn, mid)
        assert result["id"] == str(mid)
        assert len(result["innings"]) >= 1
        assert len(result["batting"]) >= 10
        assert len(result["bowling"]) >= 5

    def test_test_match_multi_innings(self):
        from backend.services.analytics import match_detail
        mid = _scalar("SELECT id FROM matches WHERE format = 'Test' LIMIT 1")
        with _engine.connect() as conn:
            result = match_detail(conn, mid)
        assert len(result["innings"]) >= 2

    def test_match_has_format(self):
        from backend.services.analytics import match_detail
        mid = _scalar("SELECT id FROM matches LIMIT 1")
        with _engine.connect() as conn:
            result = match_detail(conn, mid)
        assert result["format"] in ["T20", "T20I", "ODI", "Test"]


# ============================================================
# DATA COMPLETENESS
# ============================================================


class TestDataCompleteness:
    def test_completeness_report(self):
        from backend.services.analytics import data_completeness
        with _engine.connect() as conn:
            result = data_completeness(conn)
        assert result["total_matches"] == 8250
        assert result["venue_coverage"]["with_venue"] == 8250
        assert result["competition_coverage"]["with_competition"] >= 1500


# ============================================================
# FORMAT ISOLATION
# ============================================================


class TestFormatIsolation:
    def test_kohli_format_isolation(self):
        from backend.services.analytics import player_career
        with _engine.connect() as conn:
            result = player_career(conn, KOHLI)
        t20 = result["batting"]["T20"]["runs"]
        odi = result["batting"]["ODI"]["runs"]
        test = result["batting"]["Test"]["runs"]
        assert t20 != odi
        assert t20 != test
        assert odi != test

    def test_odi_query_no_t20(self):
        from backend.services.analytics import player_vs_opponent
        with _engine.connect() as conn:
            result = player_vs_opponent(conn, KOHLI, "ODI")
        opponents = [r["opponent"] for r in result]
        assert "Royal Challengers Bangalore" not in opponents

    def test_format_counts(self):
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='T20'") == 1243
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='T20I'") == 3533
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='ODI'") == 2577
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='Test'") == 897


# ============================================================
# REGRESSION
# ============================================================


class TestRegression:
    def test_ipl_match_count(self):
        assert _scalar("SELECT COUNT(*) FROM matches WHERE format='T20'") == 1243

    def test_kohli_ipl_runs(self):
        runs = _scalar(
            "SELECT pbs.runs FROM player_batting_stats pbs "
            "JOIN players p ON pbs.player_id = p.id "
            "WHERE p.canonical_name = 'Virat Kohli' "
            "AND pbs.format = 'T20' AND pbs.period = 'career'"
        )
        assert runs == 9346

    def test_total_matches(self):
        assert _scalar("SELECT COUNT(*) FROM matches") == 8250


# ============================================================
# PERFORMANCE
# ============================================================


class TestPerformance:
    def test_player_career_speed(self):
        from backend.services.analytics import player_career
        with _engine.connect() as conn:
            start = time.time()
            player_career(conn, KOHLI)
            elapsed = (time.time() - start) * 1000
        assert elapsed < 1000, f"Player career query took {elapsed:.0f}ms"

    def test_team_vs_team_speed(self):
        from backend.services.analytics import team_vs_team
        with _engine.connect() as conn:
            start = time.time()
            team_vs_team(conn, INDIA, AUSTRALIA)
            elapsed = (time.time() - start) * 1000
        assert elapsed < 1000, f"Team vs team query took {elapsed:.0f}ms"

    def test_match_detail_speed(self):
        from backend.services.analytics import match_detail
        mid = _scalar("SELECT id FROM matches WHERE format = 'ODI' LIMIT 1")
        with _engine.connect() as conn:
            start = time.time()
            match_detail(conn, mid)
            elapsed = (time.time() - start) * 1000
        assert elapsed < 1000, f"Match detail query took {elapsed:.0f}ms"


# ============================================================
# DATABASE SIZE
# ============================================================


class TestDatabaseSize:
    def test_under_500mb(self):
        size = _scalar(
            "SELECT pg_size_pretty(pg_database_size(current_database()))"
        )
        mb = float(size.replace(" MB", ""))
        assert mb < 500, f"Database size: {size}"


# ============================================================
# NO DELIVERIES DEPENDENCY
# ============================================================


class TestNoDeliveriesDependency:
    def test_deliveries_table_absent(self):
        exists = _scalar(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'deliveries' AND table_schema = 'public'"
        )
        assert exists == 0, "deliveries table should not exist"
