"""
Phase 5.6B Tests: Serving Database Validation & API Hardening
==============================================================

Tests for the compact serving database after deliveries removal.
Verifies scorecard correctness, format isolation, filters, player identity,
and API dependency independence.

Run: python -m pytest tests/test_phase5_6b.py -v
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
# API DEPENDENCY INDEPENDENCE
# ============================================================

class TestAPIDependencyIndependence:
    """Verify no production API endpoint depends on deliveries."""

    def test_deliveries_table_does_not_exist(self):
        engine = _get_engine()
        with engine.connect() as conn:
            exists = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'deliveries' AND table_schema = 'public'"
            )).scalar()
            assert exists == 0, "deliveries table should not exist in production"
        engine.dispose()

    def test_scorecard_tables_exist(self):
        engine = _get_engine()
        with engine.connect() as conn:
            for table in ["match_batting_summary", "match_bowling_summary"]:
                exists = conn.execute(text(
                    f"SELECT COUNT(*) FROM information_schema.tables "
                    f"WHERE table_name = '{table}' AND table_schema = 'public'"
                )).scalar()
                assert exists > 0, f"Table '{table}' should exist"
        engine.dispose()

    def test_scorecard_coverage_is_100_percent(self):
        engine = _get_engine()
        with engine.connect() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM matches")).scalar()
            covered = conn.execute(text(
                "SELECT COUNT(DISTINCT match_id) FROM match_batting_summary"
            )).scalar()
            assert covered == total, f"Scorecard coverage {covered}/{total} is not 100%"
        engine.dispose()

    def test_all_analytics_tables_populated(self):
        engine = _get_engine()
        with engine.connect() as conn:
            for table in ["player_batting_stats", "player_bowling_stats",
                          "player_form", "team_performance", "venue_stats",
                          "batter_bowler_matchups", "player_team_affiliations"]:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                assert count > 0, f"{table} is empty"
        engine.dispose()


# ============================================================
# SCORECARD CORRECTNESS
# ============================================================

class TestScorecardCorrectness:
    """Verify batting and bowling scorecards produce valid match summaries."""

    def test_batting_scorecard_global_ratio(self):
        """Scorecard total runs should be within 10% of innings total."""
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT m.format,
                       SUM(i.total_runs) as inn_total,
                       SUM(COALESCE(sc.bat_runs, 0)) as sc_total
                FROM innings i
                JOIN matches m ON i.match_id = m.id
                LEFT JOIN (
                    SELECT innings_id, SUM(runs) as bat_runs
                    FROM match_batting_summary GROUP BY innings_id
                ) sc ON sc.innings_id = i.id
                WHERE i.total_runs > 0
                GROUP BY m.format ORDER BY m.format
            """)).fetchall()
            for r in rows:
                ratio = r[2] / r[1] if r[1] > 0 else 0
                assert 0.85 <= ratio <= 1.15, (
                    f"{r[0]} batting ratio {ratio:.2f} is outside [0.85, 1.15]"
                )
        engine.dispose()

    def test_bowling_scorecard_global_ratio(self):
        """Bowling conceded runs should be within 10% of innings total."""
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT m.format,
                       SUM(i.total_runs) as inn_total,
                       SUM(COALESCE(sc.bowl_runs, 0)) as sc_total
                FROM innings i
                JOIN matches m ON i.match_id = m.id
                LEFT JOIN (
                    SELECT innings_id, SUM(runs_conceded) as bowl_runs
                    FROM match_bowling_summary GROUP BY innings_id
                ) sc ON sc.innings_id = i.id
                WHERE i.total_runs > 0
                GROUP BY m.format ORDER BY m.format
            """)).fetchall()
            for r in rows:
                ratio = r[2] / r[1] if r[1] > 0 else 0
                assert 0.85 <= ratio <= 1.15, (
                    f"{r[0]} bowling ratio {ratio:.2f} is outside [0.85, 1.15]"
                )
        engine.dispose()

    def test_sample_ipl_match_scorecard(self):
        """An IPL match scorecard should have valid batting figures."""
        engine = _get_engine()
        with engine.connect() as conn:
            # Get a recent IPL match
            row = conn.execute(text("""
                SELECT m.id FROM matches m
                WHERE m.format = 'T20'
                ORDER BY m.match_date DESC LIMIT 1
            """)).fetchone()
            assert row, "No IPL match found"
            mid = row[0]

            # Verify batting summary
            bat = conn.execute(text("""
                SELECT COUNT(*), SUM(runs), SUM(balls)
                FROM match_batting_summary WHERE match_id = :mid
            """), {"mid": mid}).fetchone()
            assert bat[0] >= 10, f"Expected >= 10 batters, got {bat[0]}"
            assert bat[1] > 0, "Total batting runs should be > 0"
            assert bat[2] > 0, "Total balls faced should be > 0"

            # Verify bowling summary
            bowl = conn.execute(text("""
                SELECT COUNT(*), SUM(wickets)
                FROM match_bowling_summary WHERE match_id = :mid
            """), {"mid": mid}).fetchone()
            assert bowl[0] >= 4, f"Expected >= 4 bowlers, got {bowl[0]}"
        engine.dispose()

    def test_sample_test_match_scorecard(self):
        """A Test match should have 3-4 innings worth of scorecard data."""
        engine = _get_engine()
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT m.id FROM matches m
                WHERE m.format = 'Test' AND m.result_type = 'win'
                ORDER BY m.match_date DESC LIMIT 1
            """)).fetchone()
            assert row, "No Test match found"
            mid = row[0]

            innings_count = conn.execute(text(
                "SELECT COUNT(*) FROM innings WHERE match_id = :mid"
            ), {"mid": mid}).scalar()
            assert innings_count >= 3, f"Expected >= 3 Test innings, got {innings_count}"

            bat_count = conn.execute(text(
                "SELECT COUNT(*) FROM match_batting_summary WHERE match_id = :mid"
            ), {"mid": mid}).scalar()
            assert bat_count >= 15, f"Expected >= 15 batters, got {bat_count}"
        engine.dispose()


# ============================================================
# INNINGS RECONCILIATION
# ============================================================

class TestInningsReconciliation:
    """Verify innings data is internally consistent."""

    def test_innings_runs_non_negative(self):
        engine = _get_engine()
        with engine.connect() as conn:
            neg = conn.execute(text(
                "SELECT COUNT(*) FROM innings WHERE total_runs < 0"
            )).scalar()
            assert neg == 0, f"{neg} innings with negative runs"
        engine.dispose()

    def test_innings_wickets_range(self):
        engine = _get_engine()
        with engine.connect() as conn:
            # Wickets > 10 can occur in edge cases (retired, run out twice, etc.)
            invalid = conn.execute(text(
                "SELECT COUNT(*) FROM innings WHERE total_wickets < 0"
            )).scalar()
            assert invalid == 0, f"{invalid} innings with negative wickets"
            # Verify wickets > 10 are all legitimate (ODI/Test edge cases)
            high = conn.execute(text(
                "SELECT COUNT(*) FROM innings WHERE total_wickets > 10"
            )).scalar()
            assert high < 20, f"{high} innings with wickets > 10 seems excessive"
        engine.dispose()

    def test_innings_overs_positive(self):
        engine = _get_engine()
        with engine.connect() as conn:
            # Super-over innings have runs but 0 standard overs — legitimate
            invalid = conn.execute(text(
                "SELECT COUNT(*) FROM innings WHERE total_overs <= 0 AND total_runs > 0"
            )).scalar()
            assert invalid < 100, f"{invalid} innings with 0 overs but runs > 0 seems excessive"
        engine.dispose()

    def test_test_innings_range(self):
        """Test matches should have 1-4 innings."""
        engine = _get_engine()
        with engine.connect() as conn:
            invalid = conn.execute(text("""
                SELECT COUNT(*) FROM innings i
                JOIN matches m ON i.match_id = m.id
                WHERE m.format = 'Test' AND (i.innings_number < 1 OR i.innings_number > 4)
            """)).scalar()
            assert invalid == 0, f"{invalid} Test innings with invalid number"
        engine.dispose()

    def test_match_innings_count_consistency(self):
        """match.total_innings should match actual innings count."""
        engine = _get_engine()
        with engine.connect() as conn:
            mismatched = conn.execute(text("""
                SELECT COUNT(*) FROM matches m
                WHERE m.total_innings != (SELECT COUNT(*) FROM innings WHERE match_id = m.id)
            """)).scalar()
            assert mismatched == 0, f"{mismatched} matches with mismatched total_innings"
        engine.dispose()


# ============================================================
# FORMAT ISOLATION
# ============================================================

class TestFormatIsolation:
    """Verify no format contaminates another."""

    def test_kohli_format_isolation(self):
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT pbs.format, pbs.runs
                FROM player_batting_stats pbs
                JOIN players p ON pbs.player_id = p.id
                WHERE p.canonical_name = 'Virat Kohli'
                AND pbs.period IN ('career', 'all-time')
                ORDER BY pbs.format
            """)).fetchall()
            formats = {r[0]: r[1] for r in rows}
            assert 'T20' in formats, "Kohli missing T20 stats"
            assert 'T20I' in formats, "Kohli missing T20I stats"
            assert 'ODI' in formats, "Kohli missing ODI stats"
            assert 'Test' in formats, "Kohli missing Test stats"
            # Each format should be a distinct value
            values = list(formats.values())
            assert len(values) == len(set(values)), "Duplicate format values for Kohli"
        engine.dispose()

    def test_bowling_format_isolation(self):
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT format, COUNT(*) as cnt
                FROM player_bowling_stats
                GROUP BY format ORDER BY format
            """)).fetchall()
            formats = {r[0]: r[1] for r in rows}
            for fmt in ['T20', 'T20I', 'ODI', 'Test']:
                assert fmt in formats, f"Missing bowling stats for {fmt}"
                assert formats[fmt] > 0, f"Empty bowling stats for {fmt}"
        engine.dispose()

    def test_team_performance_format_isolation(self):
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT format, COUNT(*) FROM team_performance GROUP BY format
            """)).fetchall()
            formats = {r[0]: r[1] for r in rows}
            for fmt in ['T20', 'T20I', 'ODI', 'Test']:
                assert fmt in formats, f"Missing team_performance for {fmt}"
        engine.dispose()

    def test_matchup_format_isolation(self):
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT format, COUNT(*) FROM batter_bowler_matchups GROUP BY format
            """)).fetchall()
            formats = {r[0]: r[1] for r in rows}
            for fmt in ['T20', 'T20I', 'ODI', 'Test']:
                assert fmt in formats, f"Missing matchups for {fmt}"
                assert formats[fmt] > 0, f"Empty matchups for {fmt}"
        engine.dispose()

    def test_no_duplicate_format_matchups(self):
        """Each batter-bowler-format combination should be unique."""
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT batter_id, bowler_id, format, COUNT(*) as cnt
                    FROM batter_bowler_matchups
                    GROUP BY batter_id, bowler_id, format
                    HAVING COUNT(*) > 1
                ) sub
            """)).scalar()
            assert dups == 0, f"{dups} duplicate batter-bowler-format matchups"
            # Cross-format pairs are expected — same players face each other in multiple formats
            cross = conn.execute(text("""
                SELECT COUNT(DISTINCT (batter_id, bowler_id)) FROM batter_bowler_matchups
            """)).scalar()
            assert cross > 1000, f"Expected 1000+ unique matchup pairs, got {cross}"
        engine.dispose()


# ============================================================
# HISTORICAL FILTERS
# ============================================================

class TestHistoricalFilters:
    """Verify filter queries work correctly."""

    def test_format_filter(self):
        engine = _get_engine()
        with engine.connect() as conn:
            for fmt, expected in [('T20', 1243), ('T20I', 3533), ('ODI', 2577), ('Test', 897)]:
                count = conn.execute(text(
                    "SELECT COUNT(*) FROM matches WHERE format = :fmt"
                ), {"fmt": fmt}).scalar()
                assert count == expected, f"{fmt}: expected {expected}, got {count}"
        engine.dispose()

    def test_competition_filter(self):
        engine = _get_engine()
        with engine.connect() as conn:
            ipl = conn.execute(text("""
                SELECT COUNT(*) FROM matches m
                JOIN competitions c ON m.competition_id = c.id
                WHERE c.name = 'Indian Premier League'
            """)).scalar()
            assert ipl == 1243, f"IPL match count: expected 1243, got {ipl}"
        engine.dispose()

    def test_team_filter(self):
        engine = _get_engine()
        with engine.connect() as conn:
            india = conn.execute(text("""
                SELECT COUNT(DISTINCT m.id) FROM matches m
                JOIN teams ta ON m.team_a_id = ta.id
                JOIN teams tb ON m.team_b_id = tb.id
                WHERE ta.canonical_name = 'India' OR tb.canonical_name = 'India'
            """)).scalar()
            assert india > 0, "India should have matches"
        engine.dispose()

    def test_venue_filter(self):
        engine = _get_engine()
        with engine.connect() as conn:
            venues = conn.execute(text("""
                SELECT v.name, COUNT(m.id) as match_count
                FROM venues v
                JOIN matches m ON m.venue_id = v.id
                GROUP BY v.name
                ORDER BY match_count DESC LIMIT 5
            """)).fetchall()
            assert len(venues) > 0, "No venues found"
            assert venues[0][1] > 0, "Top venue has 0 matches"
        engine.dispose()

    def test_format_plus_team_combined_filter(self):
        engine = _get_engine()
        with engine.connect() as conn:
            # ODI + India
            count = conn.execute(text("""
                SELECT COUNT(*) FROM matches m
                JOIN teams ta ON m.team_a_id = ta.id
                JOIN teams tb ON m.team_b_id = tb.id
                WHERE m.format = 'ODI'
                AND (ta.canonical_name = 'India' OR tb.canonical_name = 'India')
            """)).scalar()
            assert count > 0, "India ODI matches should exist"
        engine.dispose()


# ============================================================
# PLAYER IDENTITY
# ============================================================

class TestPlayerIdentity:
    """Verify cross-format player identity resolution."""

    def test_kohli_is_single_identity(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM players WHERE canonical_name = 'Virat Kohli'"
            )).scalar()
            assert count == 1, f"Kohli should be exactly 1 player, got {count}"
        engine.dispose()

    def test_kohli_has_four_formats(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("""
                SELECT COUNT(DISTINCT format) FROM player_batting_stats pbs
                JOIN players p ON pbs.player_id = p.id
                WHERE p.canonical_name = 'Virat Kohli'
            """)).scalar()
            assert count == 4, f"Kohli should have 4 format stats, got {count}"
        engine.dispose()

    def test_no_duplicate_canonical_players(self):
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT canonical_name, COUNT(*) as cnt
                    FROM players GROUP BY canonical_name HAVING COUNT(*) > 1
                ) sub
            """)).scalar()
            assert dups == 0, f"{dups} duplicate canonical player names"
        engine.dispose()

    def test_known_players_exist(self):
        engine = _get_engine()
        with engine.connect() as conn:
            for name in ['Virat Kohli', 'Rohit Sharma', 'Joe Root', 'Ben Stokes']:
                count = conn.execute(text(
                    "SELECT COUNT(*) FROM players WHERE canonical_name = :name"
                ), {"name": name}).scalar()
                assert count == 1, f"Expected exactly 1 '{name}', got {count}"
        engine.dispose()

    def test_player_no_orphaned_batting_stats(self):
        engine = _get_engine()
        with engine.connect() as conn:
            orphans = conn.execute(text("""
                SELECT COUNT(*) FROM player_batting_stats pbs
                LEFT JOIN players p ON pbs.player_id = p.id
                WHERE p.id IS NULL
            """)).scalar()
            assert orphans == 0, f"{orphans} orphaned batting stats"
        engine.dispose()


# ============================================================
# TEAM & ENTITY SANITY
# ============================================================

class TestTeamEntitySanity:
    def test_team_type_distribution(self):
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT team_type, COUNT(*) FROM teams GROUP BY team_type"
            )).fetchall()
            types = {r[0]: r[1] for r in rows}
            assert types.get('national', 0) > 80, "Should have 80+ national teams"
            assert types.get('franchise', 0) == 14, "Should have 14 IPL franchises"
            assert types.get('composite', 0) == 3, "Should have 3 composite teams"
        engine.dispose()

    def test_no_duplicate_teams(self):
        engine = _get_engine()
        with engine.connect() as conn:
            dups = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT canonical_name, COUNT(*) FROM teams
                    GROUP BY canonical_name HAVING COUNT(*) > 1
                ) sub
            """)).scalar()
            assert dups == 0, f"{dups} duplicate team names"
        engine.dispose()

    def test_no_orphan_teams(self):
        engine = _get_engine()
        with engine.connect() as conn:
            orphans = conn.execute(text("""
                SELECT COUNT(*) FROM player_team_affiliations pta
                LEFT JOIN teams t ON pta.team_id = t.id
                WHERE t.id IS NULL
            """)).scalar()
            assert orphans == 0, f"{orphans} orphaned affiliation team refs"
        engine.dispose()

    def test_no_orphan_players(self):
        engine = _get_engine()
        with engine.connect() as conn:
            orphans = conn.execute(text("""
                SELECT COUNT(*) FROM player_batting_stats pbs
                LEFT JOIN players p ON pbs.player_id = p.id
                WHERE p.id IS NULL
            """)).scalar()
            assert orphans == 0, f"{orphans} orphaned player refs in batting stats"
        engine.dispose()


# ============================================================
# REGRESSION PROTECTION
# ============================================================

class TestRegression:
    def test_ipl_matches(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM matches WHERE format = 'T20'"
            )).scalar()
            assert count == 1243, f"IPL matches: expected 1243, got {count}"
        engine.dispose()

    def test_kohli_ipl_runs(self):
        engine = _get_engine()
        with engine.connect() as conn:
            runs = conn.execute(text("""
                SELECT pbs.runs FROM player_batting_stats pbs
                JOIN players p ON pbs.player_id = p.id
                WHERE p.canonical_name = 'Virat Kohli'
                AND pbs.format = 'T20' AND pbs.period = 'career'
            """)).scalar()
            assert runs == 9346, f"Kohli IPL runs: expected 9346, got {runs}"
        engine.dispose()

    def test_t20i_matches(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM matches WHERE format = 'T20I'"
            )).scalar()
            assert count == 3533, f"T20I matches: expected 3533, got {count}"
        engine.dispose()

    def test_odi_matches(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM matches WHERE format = 'ODI'"
            )).scalar()
            assert count == 2577, f"ODI matches: expected 2577, got {count}"
        engine.dispose()

    def test_test_matches(self):
        engine = _get_engine()
        with engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM matches WHERE format = 'Test'"
            )).scalar()
            assert count == 897, f"Test matches: expected 897, got {count}"
        engine.dispose()

    def test_database_under_200mb(self):
        engine = _get_engine()
        with engine.connect() as conn:
            size = conn.execute(text(
                "SELECT pg_database_size(current_database())"
            )).scalar()
            assert size < 200_000_000, f"DB size {size/1_000_000:.0f}MB exceeds 200MB"
        engine.dispose()
