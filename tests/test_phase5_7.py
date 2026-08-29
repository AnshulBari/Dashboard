"""
Phase 5.7 Tests: Analytical Dimensions & Data-Categorization Audit
==================================================================

Verifies that the database supports all analytical dimensions required
by the Cricket Intelligence dashboard.

Run: python -m pytest tests/test_phase5_7.py -v
"""

import os
import sys
import pytest
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def _get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


# ============================================================
# PLAYER-WISE ANALYTICS
# ============================================================


class TestPlayerWiseAnalytics:
    """Verify player statistics work across all formats."""

    def test_kohli_has_all_four_formats(self):
        """Virat Kohli must have batting stats in all 4 formats."""
        engine = _get_engine()
        with engine.connect() as conn:
            formats = conn.execute(
                text(
                    "SELECT DISTINCT pbs.format FROM player_batting_stats pbs "
                    "JOIN players p ON pbs.player_id = p.id "
                    "WHERE p.canonical_name = 'Virat Kohli' AND pbs.period = 'career'"
                )
            ).fetchall()
            fmt_set = {r[0] for r in formats}
        engine.dispose()
        assert "T20" in fmt_set, "Kohli missing T20 batting stats"
        assert "T20I" in fmt_set, "Kohli missing T20I batting stats"
        assert "ODI" in fmt_set, "Kohli missing ODI batting stats"
        assert "Test" in fmt_set, "Kohli missing Test batting stats"

    def test_kohli_format_totals(self):
        """Verify Kohli's approximate career totals."""
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT pbs.format, pbs.runs FROM player_batting_stats pbs "
                    "JOIN players p ON pbs.player_id = p.id "
                    "WHERE p.canonical_name = 'Virat Kohli' AND pbs.period = 'career'"
                )
            ).fetchall()
            stats = {r[0]: r[1] for r in rows}
        engine.dispose()
        assert stats.get("T20", 0) >= 9000, f"Kohli T20 runs: {stats.get('T20')}"
        assert stats.get("T20I", 0) >= 4000, f"Kohli T20I runs: {stats.get('T20I')}"
        assert stats.get("ODI", 0) >= 15000, f"Kohli ODI runs: {stats.get('ODI')}"
        assert stats.get("Test", 0) >= 8000, f"Kohli Test runs: {stats.get('Test')}"

    def test_player_form_across_formats(self):
        """Player form scores exist for all formats."""
        engine = _get_engine()
        with engine.connect() as conn:
            formats = conn.execute(
                text("SELECT DISTINCT format FROM player_form")
            ).fetchall()
            fmt_set = {r[0] for r in formats}
        engine.dispose()
        assert fmt_set == {"T20", "T20I", "ODI", "Test"}

    def test_player_has_bowling_stats(self):
        """A known bowler has bowling stats."""
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM player_bowling_stats pws "
                    "JOIN players p ON pws.player_id = p.id "
                    "WHERE p.canonical_name = 'Jasprit Bumrah' "
                    "AND pws.period = 'career'"
                )
            ).scalar()
        engine.dispose()
        assert count >= 2, f"Bumrah bowling stats: {count} formats"

    def test_player_affiliations_no_duplicates(self):
        """No duplicate (player, team, format) affiliations."""
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(
                text(
                    "SELECT COUNT(*) FROM ("
                    "  SELECT player_id, team_id, format, COUNT(*) "
                    "  FROM player_team_affiliations "
                    "  GROUP BY player_id, team_id, format HAVING COUNT(*) > 1"
                    ") sub"
                )
            ).scalar()
        engine.dispose()
        assert dups == 0, f"{dups} duplicate affiliation groups"

    def test_player_match_navigation(self):
        """A player can navigate to their matches via scorecards."""
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(DISTINCT mbs.match_id) "
                    "FROM match_batting_summary mbs "
                    "JOIN players p ON mbs.player_id = p.id "
                    "WHERE p.canonical_name = 'Virat Kohli'"
                )
            ).scalar()
        engine.dispose()
        assert count > 100, f"Kohli match count: {count}"


# ============================================================
# TEAM-WISE ANALYTICS
# ============================================================


class TestTeamWiseAnalytics:
    """Verify team statistics and head-to-head queries."""

    def test_team_performance_all_formats(self):
        """Team performance exists for all formats."""
        engine = _get_engine()
        with engine.connect() as conn:
            formats = conn.execute(
                text(
                    "SELECT DISTINCT format FROM team_performance "
                    "WHERE period = 'career'"
                )
            ).fetchall()
            fmt_set = {r[0] for r in formats}
        engine.dispose()
        assert "T20" in fmt_set
        assert "T20I" in fmt_set
        assert "ODI" in fmt_set
        assert "Test" in fmt_set

    def test_india_vs_australia_head_to_head(self):
        """India vs Australia head-to-head works."""
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT m.format, COUNT(*) as matches "
                    "FROM matches m "
                    "JOIN teams t1 ON m.team_a_id = t1.id "
                    "JOIN teams t2 ON m.team_b_id = t2.id "
                    "WHERE (t1.canonical_name = 'India' AND t2.canonical_name = 'Australia') "
                    "OR (t1.canonical_name = 'Australia' AND t2.canonical_name = 'India') "
                    "GROUP BY m.format ORDER BY m.format"
                )
            ).fetchall()
            h2h = {r[0]: r[1] for r in rows}
        engine.dispose()
        assert h2h.get("ODI", 0) > 50, f"Ind vs Aus ODI: {h2h.get('ODI')}"
        assert h2h.get("Test", 0) > 30, f"Ind vs Aus Test: {h2h.get('Test')}"
        assert h2h.get("T20I", 0) > 20, f"Ind vs Aus T20I: {h2h.get('T20I')}"

    def test_ipl_team_performance(self):
        """IPL teams have performance data."""
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM team_performance tp "
                    "JOIN teams t ON tp.team_id = t.id "
                    "WHERE tp.format = 'T20' AND tp.period = 'career' "
                    "AND t.team_type = 'franchise'"
                )
            ).scalar()
        engine.dispose()
        assert count >= 10, f"IPL team performance count: {count}"

    def test_no_orphan_teams(self):
        """No teams without a canonical name."""
        engine = _get_engine()
        with engine.connect() as conn:
            orphans = conn.execute(
                text(
                    "SELECT COUNT(*) FROM teams "
                    "WHERE canonical_name IS NULL OR canonical_name = ''"
                )
            ).scalar()
        engine.dispose()
        assert orphans == 0


# ============================================================
# COMPETITION-WISE ANALYTICS
# ============================================================


class TestCompetitionWiseAnalytics:
    """Verify competition hierarchy works."""

    def test_competitions_exist(self):
        """Competitions table has records."""
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM competitions")).scalar()
        engine.dispose()
        assert count > 0

    def test_ipl_competition_has_seasons(self):
        """IPL competition has linked seasons."""
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM seasons s "
                    "JOIN competitions c ON s.competition_id = c.id "
                    "WHERE c.name = 'Indian Premier League'"
                )
            ).scalar()
        engine.dispose()
        assert count >= 5, f"IPL seasons: {count}"

    def test_ipl_seasons_have_matches(self):
        """IPL seasons have matches linked."""
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM matches m "
                    "JOIN seasons s ON m.season_id = s.id "
                    "JOIN competitions c ON s.competition_id = c.id "
                    "WHERE c.name = 'Indian Premier League'"
                )
            ).scalar()
        engine.dispose()
        assert count == 1243, f"IPL matches via seasons: {count}"

    def test_competition_to_match_navigation(self):
        """Competition -> Season -> Match chain works."""
        engine = _get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT c.name, s.name, COUNT(m.id) "
                    "FROM competitions c "
                    "JOIN seasons s ON s.competition_id = c.id "
                    "JOIN matches m ON m.season_id = s.id "
                    "WHERE c.name = 'Indian Premier League' "
                    "AND s.name = '2024' "
                    "GROUP BY c.name, s.name"
                )
            ).fetchone()
        engine.dispose()
        assert row is not None, "IPL 2024 season not found"
        assert row[2] > 0, f"IPL 2024 matches: {row[2]}"


# ============================================================
# SEASON-WISE ANALYTICS
# ============================================================


class TestSeasonWiseAnalytics:
    """Verify season-level analytics."""

    def test_seasons_count(self):
        """Seasons table has records."""
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM seasons")).scalar()
        engine.dispose()
        assert count >= 10, f"Seasons count: {count}"

    def test_format_year_grouping(self):
        """Matches can be grouped by year for any format."""
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT EXTRACT(YEAR FROM match_date)::int as yr, COUNT(*) "
                    "FROM matches WHERE format = 'ODI' "
                    "GROUP BY yr ORDER BY yr"
                )
            ).fetchall()
        engine.dispose()
        assert len(rows) >= 10, f"ODI year groups: {len(rows)}"
        # Verify year range
        years = [r[0] for r in rows]
        assert min(years) <= 2005, f"Earliest ODI year: {min(years)}"
        assert max(years) >= 2024, f"Latest ODI year: {max(years)}"


# ============================================================
# FORMAT ISOLATION
# ============================================================


class TestFormatIsolation:
    """Verify strict format isolation."""

    def test_format_counts(self):
        """Exact format match counts."""
        engine = _get_engine()
        with engine.connect() as conn:
            counts = {}
            for fmt in ["T20", "T20I", "ODI", "Test"]:
                counts[fmt] = conn.execute(
                    text("SELECT COUNT(*) FROM matches WHERE format = :f"),
                    {"f": fmt},
                ).scalar()
        engine.dispose()
        assert counts["T20"] == 1243
        assert counts["T20I"] == 3533
        assert counts["ODI"] == 2577
        assert counts["Test"] == 897

    def test_kohli_ipl_runs(self):
        """Kohli IPL regression."""
        engine = _get_engine()
        with engine.connect() as conn:
            runs = conn.execute(
                text(
                    "SELECT pbs.runs FROM player_batting_stats pbs "
                    "JOIN players p ON pbs.player_id = p.id "
                    "WHERE p.canonical_name = 'Virat Kohli' "
                    "AND pbs.format = 'T20' AND pbs.period = 'career'"
                )
            ).scalar()
        engine.dispose()
        assert runs == 9346

    def test_no_cross_format_contamination(self):
        """Match format column only contains known values."""
        engine = _get_engine()
        with engine.connect() as conn:
            formats = conn.execute(
                text("SELECT DISTINCT format FROM matches")
            ).fetchall()
            fmt_set = {r[0] for r in formats}
        engine.dispose()
        assert fmt_set == {"T20", "T20I", "ODI", "Test"}


# ============================================================
# VENUE-WISE ANALYTICS
# ============================================================


class TestVenueWiseAnalytics:
    """Verify venue analytics."""

    def test_venue_stats_exist(self):
        """Venue stats exist for all formats."""
        engine = _get_engine()
        with engine.connect() as conn:
            formats = conn.execute(
                text("SELECT DISTINCT format FROM venue_stats")
            ).fetchall()
            fmt_set = {r[0] for r in formats}
        engine.dispose()
        assert "T20" in fmt_set
        assert "ODI" in fmt_set
        assert "Test" in fmt_set

    def test_all_matches_have_venue(self):
        """100% venue coverage."""
        engine = _get_engine()
        with engine.connect() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM matches")).scalar()
            with_venue = conn.execute(
                text("SELECT COUNT(*) FROM matches WHERE venue_id IS NOT NULL")
            ).scalar()
        engine.dispose()
        assert with_venue == total, f"Venue coverage: {with_venue}/{total}"


# ============================================================
# OPPONENT-WISE ANALYTICS
# ============================================================


class TestOpponentWiseAnalytics:
    """Verify opponent derivation through scorecard joins."""

    def test_opponent_derivation_via_innings(self):
        """Opponent is derivable from innings bowling_team."""
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(DISTINCT m.id) "
                    "FROM match_batting_summary mbs "
                    "JOIN innings i ON mbs.innings_id = i.id "
                    "JOIN matches m ON mbs.match_id = m.id "
                    "JOIN players p ON mbs.player_id = p.id "
                    "WHERE p.canonical_name = 'Virat Kohli' "
                    "AND m.format = 'ODI'"
                )
            ).scalar()
        engine.dispose()
        assert count > 200, f"Kohli ODI scorecard entries: {count}"

    def test_batter_bowler_matchups_exist(self):
        """Matchups table has data."""
        engine = _get_engine()
        with engine.connect() as conn:
            for fmt in ["T20", "T20I", "ODI", "Test"]:
                count = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM batter_bowler_matchups "
                        "WHERE format = :f"
                    ),
                    {"f": fmt},
                ).scalar()
                assert count > 0, f"Matchups for {fmt}: {count}"
        engine.dispose()


# ============================================================
# SCORECARD INTEGRITY
# ============================================================


class TestScorecardIntegrity:
    """Verify scorecard associations are correct."""

    def test_no_orphan_batting_summaries(self):
        engine = _get_engine()
        with engine.connect() as conn:
            orphans = conn.execute(
                text(
                    "SELECT COUNT(*) FROM match_batting_summary mbs "
                    "LEFT JOIN matches m ON mbs.match_id = m.id "
                    "WHERE m.id IS NULL"
                )
            ).scalar()
        engine.dispose()
        assert orphans == 0

    def test_no_orphan_bowling_summaries(self):
        engine = _get_engine()
        with engine.connect() as conn:
            orphans = conn.execute(
                text(
                    "SELECT COUNT(*) FROM match_bowling_summary mbs "
                    "LEFT JOIN matches m ON mbs.match_id = m.id "
                    "WHERE m.id IS NULL"
                )
            ).scalar()
        engine.dispose()
        assert orphans == 0

    def test_no_duplicate_batting(self):
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(
                text(
                    "SELECT COUNT(*) FROM ("
                    "  SELECT match_id, innings_id, player_id, COUNT(*) "
                    "  FROM match_batting_summary "
                    "  GROUP BY match_id, innings_id, player_id HAVING COUNT(*) > 1"
                    ") sub"
                )
            ).scalar()
        engine.dispose()
        assert dups == 0

    def test_no_duplicate_bowling(self):
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(
                text(
                    "SELECT COUNT(*) FROM ("
                    "  SELECT match_id, innings_id, player_id, COUNT(*) "
                    "  FROM match_bowling_summary "
                    "  GROUP BY match_id, innings_id, player_id HAVING COUNT(*) > 1"
                    ") sub"
                )
            ).scalar()
        engine.dispose()
        assert dups == 0

    def test_representative_match_scorecard(self):
        """A sample match has valid batting + bowling scorecard."""
        engine = _get_engine()
        with engine.connect() as conn:
            # Get a sample match
            row = conn.execute(
                text(
                    "SELECT m.id, m.format FROM matches m "
                    "WHERE m.format = 'T20' LIMIT 1"
                )
            ).fetchone()
            match_id = row[0]

            bat_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM match_batting_summary "
                    "WHERE match_id = :mid"
                ),
                {"mid": match_id},
            ).scalar()
            bowl_count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM match_bowling_summary "
                    "WHERE match_id = :mid"
                ),
                {"mid": match_id},
            ).scalar()
        engine.dispose()
        assert bat_count >= 10, f"Sample match batting rows: {bat_count}"
        assert bowl_count >= 5, f"Sample match bowling rows: {bowl_count}"


# ============================================================
# ENTITY INTEGRITY
# ============================================================


class TestEntityIntegrity:
    """Verify no duplicate canonical entities."""

    def test_no_duplicate_canonical_players(self):
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(
                text(
                    "SELECT COUNT(*) FROM ("
                    "  SELECT canonical_name, COUNT(*) FROM players "
                    "  GROUP BY canonical_name HAVING COUNT(*) > 1"
                    ") sub"
                )
            ).scalar()
        engine.dispose()
        assert dups == 0, f"{dups} duplicate canonical player names"

    def test_no_duplicate_canonical_teams(self):
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(
                text(
                    "SELECT COUNT(*) FROM ("
                    "  SELECT canonical_name, COUNT(*) FROM teams "
                    "  GROUP BY canonical_name HAVING COUNT(*) > 1"
                    ") sub"
                )
            ).scalar()
        engine.dispose()
        assert dups == 0

    def test_all_periods_are_career(self):
        """No 'all-time' period values remain (fixed in 5.7)."""
        engine = _get_engine()
        with engine.connect() as conn:
            at_bat = conn.execute(
                text(
                    "SELECT COUNT(*) FROM player_batting_stats "
                    "WHERE period = 'all-time'"
                )
            ).scalar()
            at_bowl = conn.execute(
                text(
                    "SELECT COUNT(*) FROM player_bowling_stats "
                    "WHERE period = 'all-time'"
                )
            ).scalar()
        engine.dispose()
        assert at_bat == 0, f"{at_bat} batting stats with 'all-time' period"
        assert at_bowl == 0, f"{at_bowl} bowling stats with 'all-time' period"


# ============================================================
# DATABASE SIZE
# ============================================================


class TestDatabaseSize:
    """Verify database remains within Supabase Free Plan limits."""

    def test_database_under_500mb(self):
        engine = _get_engine()
        with engine.connect() as conn:
            size = conn.execute(
                text(
                    "SELECT pg_size_pretty(pg_database_size(current_database()))"
                )
            ).scalar()
        engine.dispose()
        # Parse MB value
        mb = float(size.replace(" MB", "").replace(" kB", "").replace(" bytes", ""))
        assert mb < 500, f"Database size: {size}"
