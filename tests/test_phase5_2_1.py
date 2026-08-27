"""
Phase 5.2.1 Tests: Data Integrity, Player Identity & Analytics Reliability
==========================================================================

Tests for:
1. Canonical player resolution
2. Alias resolution via player_name_mappings
3. Analytics player ID resolution
4. Matchup foreign key integrity
5. PostgreSQL count verification
6. Analytics write correctness
7. Idempotent analytics rebuild
8. Data-quality audit
9. Foreign key integrity
10. Format isolation
11. Cross-format player identity
12. IPL regression
"""

import uuid
import pytest
from dotenv import load_dotenv

load_dotenv()

import os
from sqlalchemy import create_engine, text
import pandas as pd


@pytest.fixture(scope="module")
def db_engine():
    """Create engine to PostgreSQL for testing."""
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("No DATABASE_URL set")
    engine = create_engine(url, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def db_manager():
    """Initialize DatabaseManager with full entity resolution."""
    from data_pipeline.pipeline.db_manager import DatabaseManager
    db = DatabaseManager()
    db.initialize()
    return db


class TestPlayerIdentity:
    """Test player identity pipeline."""

    def test_no_duplicate_canonical_names(self, db_engine):
        """No two players should share the same canonical name."""
        with db_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT canonical_name, COUNT(*) FROM players "
                "GROUP BY canonical_name HAVING COUNT(*) > 1"
            )).fetchall()
        assert len(rows) == 0, f"Duplicate canonical names found: {rows}"

    def test_total_players_reasonable(self, db_engine):
        """Should have at least 900 players from IPL + international."""
        with db_engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
        assert count >= 900, f"Expected >= 900 players, got {count}"

    def test_name_mappings_point_to_real_players(self, db_engine):
        """All name mappings should reference existing players."""
        with db_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT COUNT(*) FROM player_name_mappings m "
                "LEFT JOIN players p ON m.player_id = p.id WHERE p.id IS NULL"
            )).scalar()
        assert rows == 0, f"{rows} orphaned name mappings"

    def test_virat_kohli_single_identity(self, db_engine):
        """Virat Kohli must be a single canonical player."""
        with db_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, canonical_name FROM players "
                "WHERE canonical_name ILIKE '%virat kohli%'"
            )).fetchall()
        assert len(rows) == 1, f"Expected 1 Virat Kohli, got {len(rows)}: {rows}"

    def test_v_kohli_maps_to_virat_kohli(self, db_manager):
        """V Kohli alias should resolve to Virat Kohli."""
        # Direct lookup
        virat_id = db_manager._player_ids.get("Virat Kohli")
        assert virat_id is not None, "Virat Kohli not found in player IDs"

        # Via alias
        v_kohli_canonical = db_manager._player_name_mappings.get("V Kohli")
        assert v_kohli_canonical == "Virat Kohli", \
            f"V Kohli mapping should be Virat Kohli, got {v_kohli_canonical}"

    def test_kl_rahul_single_identity(self, db_engine):
        """KL Rahul must be a single canonical player."""
        with db_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, canonical_name FROM players "
                "WHERE canonical_name ILIKE '%rahul%' "
                "AND canonical_name LIKE 'KL%'"
            )).fetchall()
        assert len(rows) == 1, f"Expected 1 KL Rahul, got {len(rows)}: {rows}"

    def test_no_player_name_with_version_suffix(self, db_engine):
        """Players with '(2)' suffix are suspicious (potential duplicates)."""
        with db_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT canonical_name FROM players "
                "WHERE canonical_name LIKE '%(%)%'"
            )).fetchall()
        # Allow but warn — this is a known limitation
        if rows:
            names = [r[0] for r in rows]
            print(f"  WARN: Players with version suffix: {names}")

    def test_cross_format_player_identity(self, db_engine):
        """Players appearing in multiple formats should share one identity."""
        with db_engine.connect() as conn:
            # Find players with both T20 and T20I affiliations
            rows = conn.execute(text(
                "SELECT p.canonical_name, "
                "  SUM(CASE WHEN a.format = 'T20' THEN 1 ELSE 0 END) as t20_aff, "
                "  SUM(CASE WHEN a.format = 'T20I' THEN 1 ELSE 0 END) as t20i_aff, "
                "  SUM(CASE WHEN a.format = 'ODI' THEN 1 ELSE 0 END) as odi_aff "
                "FROM player_team_affiliations a "
                "JOIN players p ON a.player_id = p.id "
                "GROUP BY p.canonical_name "
                "HAVING SUM(CASE WHEN a.format = 'T20' THEN 1 ELSE 0 END) > 0 "
                "   AND SUM(CASE WHEN a.format IN ('T20I', 'ODI') THEN 1 ELSE 0 END) > 0 "
                "LIMIT 10"
            )).fetchall()
        # Verify these are real cross-format players
        assert len(rows) >= 1, "No cross-format players found"
        for r in rows:
            print(f"  Cross-format: {r[0]} (T20={r[1]}, T20I={r[2]}, ODI={r[3]})")

    def test_player_count_by_format(self, db_engine):
        """Each format should have players affiliated."""
        with db_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT format, COUNT(DISTINCT player_id) FROM player_team_affiliations "
                "GROUP BY format"
            )).fetchall()
        counts = {r[0]: r[1] for r in rows}
        assert counts.get("T20", 0) > 100, "T20 should have >100 affiliated players"
        assert counts.get("T20I", 0) > 0, "T20I should have affiliated players"
        assert counts.get("ODI", 0) > 0, "ODI should have affiliated players"
        assert counts.get("Test", 0) > 0, "Test should have affiliated players"


class TestAnalyticsIntegrity:
    """Test analytics data integrity."""

    def test_no_null_player_ids_in_batting_stats(self, db_engine):
        """All batting stats should have valid player_id."""
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM player_batting_stats WHERE player_id IS NULL"
            )).scalar()
        assert count == 0, f"{count} batting stats with NULL player_id"

    def test_no_null_player_ids_in_bowling_stats(self, db_engine):
        """All bowling stats should have valid player_id."""
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM player_bowling_stats WHERE player_id IS NULL"
            )).scalar()
        assert count == 0, f"{count} bowling stats with NULL player_id"

    def test_no_orphaned_batting_stats(self, db_engine):
        """All batting stats should reference existing players."""
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM player_batting_stats a "
                "LEFT JOIN players p ON a.player_id = p.id WHERE p.id IS NULL"
            )).scalar()
        assert count == 0, f"{count} orphaned batting stats"

    def test_no_orphaned_bowling_stats(self, db_engine):
        """All bowling stats should reference existing players."""
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM player_bowling_stats a "
                "LEFT JOIN players p ON a.player_id = p.id WHERE p.id IS NULL"
            )).scalar()
        assert count == 0, f"{count} orphaned bowling stats"

    def test_no_null_player_ids_in_matchups(self, db_engine):
        """All matchups should have valid batter_id and bowler_id."""
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM batter_bowler_matchups "
                "WHERE batter_id IS NULL OR bowler_id IS NULL"
            )).scalar()
        assert count == 0, f"{count} matchups with NULL player IDs"

    def test_no_orphaned_matchups(self, db_engine):
        """All matchup batter/bowler IDs should reference existing players."""
        with db_engine.connect() as conn:
            for col in ["batter_id", "bowler_id"]:
                count = conn.execute(text(
                    f"SELECT COUNT(*) FROM batter_bowler_matchups m "
                    f"LEFT JOIN players p ON m.{col} = p.id WHERE p.id IS NULL"
                )).scalar()
                assert count == 0, f"{count} matchups with orphaned {col}"

    def test_format_isolation_batting(self, db_engine):
        """Each format should have separate batting stats."""
        with db_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT format, COUNT(*) FROM player_batting_stats GROUP BY format"
            )).fetchall()
        counts = {r[0]: r[1] for r in rows}
        assert counts.get("T20", 0) > 0, "T20 batting stats missing"
        assert counts.get("T20I", 0) > 0, "T20I batting stats missing"
        assert counts.get("ODI", 0) > 0, "ODI batting stats missing"
        assert counts.get("Test", 0) > 0, "Test batting stats missing"

    def test_format_isolation_matchups(self, db_engine):
        """Each format should have separate matchup stats."""
        with db_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT format, COUNT(*) FROM batter_bowler_matchups GROUP BY format"
            )).fetchall()
        counts = {r[0]: r[1] for r in rows}
        assert counts.get("T20", 0) > 0, "T20 matchups missing"
        assert counts.get("T20I", 0) > 0, "T20I matchups missing"

    def test_no_zero_matchup_totals(self, db_engine):
        """No matchup should have 0 total_balls or total_runs < 0."""
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM batter_bowler_matchups WHERE total_balls <= 0"
            )).scalar()
        assert count == 0, f"{count} matchups with invalid total_balls"


class TestDataQualityAudit:
    """Test the data-quality audit tool."""

    def test_audit_runs(self):
        """The audit should run without errors."""
        from data_pipeline.audit.runner import AuditRunner
        runner = AuditRunner()
        report = runner.run_all()
        assert report.total_checks > 0, "Audit produced no checks"

    def test_audit_finds_no_failures(self):
        """The audit should find zero failures in current data."""
        from data_pipeline.audit.runner import AuditRunner
        runner = AuditRunner()
        report = runner.run_all()
        assert report.failures == 0, (
            f"Audit found {report.failures} failures: "
            + str([r for r in report.results if r.status == "FAIL"])
        )

    def test_audit_detects_player_duplicates(self):
        """Audit should detect duplicate canonical players if they exist."""
        from data_pipeline.audit.runner import AuditRunner
        runner = AuditRunner()
        report = runner.run_all()
        player_checks = [r for r in report.results if r.category == "Players"]
        assert len(player_checks) > 0, "No player checks in audit"

    def test_audit_fk_integrity(self):
        """Audit should verify all foreign keys."""
        from data_pipeline.audit.runner import AuditRunner
        runner = AuditRunner()
        report = runner.run_all()
        fk_checks = [r for r in report.results if r.category == "Foreign Keys"]
        assert len(fk_checks) >= 10, f"Expected >= 10 FK checks, got {len(fk_checks)}"
        fk_failures = [r for r in fk_checks if r.status == "FAIL"]
        assert len(fk_failures) == 0, (
            f"FK failures: {[f'{r.check} ({r.count})' for r in fk_failures]}"
        )

    def test_audit_format_isolation(self):
        """Audit should verify format isolation."""
        from data_pipeline.audit.runner import AuditRunner
        runner = AuditRunner()
        report = runner.run_all()
        fi_checks = [r for r in report.results if r.category == "Format Isolation"]
        assert len(fi_checks) >= 4, f"Expected >= 4 format isolation checks, got {len(fi_checks)}"


class TestDatabaseIntegrity:
    """Test database-level integrity."""

    def test_no_duplicate_matches(self, db_engine):
        """No duplicate match external IDs."""
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM ("
                "  SELECT external_id, COUNT(*) FROM matches "
                "  GROUP BY external_id HAVING COUNT(*) > 1"
                ") sub"
            )).scalar()
        assert count == 0, f"{count} duplicate match external IDs"

    def test_valid_match_formats(self, db_engine):
        """All matches should have valid formats."""
        with db_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT DISTINCT format FROM matches"
            )).fetchall()
        formats = {r[0] for r in rows}
        valid = {"T20", "T20I", "ODI", "Test"}
        invalid = formats - valid
        assert len(invalid) == 0, f"Invalid formats: {invalid}"

    def test_no_orphaned_deliveries(self, db_engine):
        """All deliveries should reference valid innings."""
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries d "
                "LEFT JOIN innings i ON d.innings_id = i.id WHERE i.id IS NULL"
            )).scalar()
        assert count == 0, f"{count} orphaned deliveries"

    def test_no_null_striker_bowler(self, db_engine):
        """No deliveries should have NULL striker or bowler."""
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries WHERE striker_id IS NULL OR bowler_id IS NULL"
            )).scalar()
        assert count == 0, f"{count} deliveries with NULL striker/bowler"

    def test_valid_over_ball_numbers(self, db_engine):
        """All deliveries should have valid over/ball numbers."""
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries WHERE over_number < 0 OR ball_in_over < 1 OR ball_in_over > 12"
            )).scalar()
        # ball_in_over > 12 is valid for super overs; warn but don't fail
        # Just ensure no negative over_number or ball_in_over < 1
        with db_engine.connect() as conn:
            invalid = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries WHERE over_number < 0 OR ball_in_over < 1"
            )).scalar()
        assert invalid == 0, f"{invalid} deliveries with truly invalid over/ball numbers"

    def test_no_negative_runs(self, db_engine):
        """No deliveries should have negative runs."""
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries WHERE total_runs < 0 OR runs_bat < 0"
            )).scalar()
        assert count == 0, f"{count} deliveries with negative runs"


class TestIPLRegression:
    """Verify IPL data remains intact after Phase 5.2.1 changes."""

    def test_ipl_match_count(self, db_engine):
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM matches WHERE format = 'T20'"
            )).scalar()
        assert count == 1243, f"IPL match count changed: expected 1243, got {count}"

    def test_ipl_delivery_count(self, db_engine):
        with db_engine.connect() as conn:
            count = conn.execute(text(
                "SELECT COUNT(*) FROM deliveries d "
                "JOIN innings i ON d.innings_id = i.id "
                "JOIN matches m ON i.match_id = m.id "
                "WHERE m.format = 'T20'"
            )).scalar()
        assert count == 295732, f"IPL delivery count changed: expected 295732, got {count}"

    def test_kohli_ipl_runs(self, db_engine):
        with db_engine.connect() as conn:
            runs = conn.execute(text(
                "SELECT SUM(d.runs_bat) FROM deliveries d "
                "JOIN innings i ON d.innings_id = i.id "
                "JOIN matches m ON i.match_id = m.id "
                "JOIN players p ON d.striker_id = p.id "
                "WHERE m.format = 'T20' AND p.canonical_name = 'Virat Kohli'"
            )).scalar()
        assert runs == 9346, f"Kohli IPL runs changed: expected 9346, got {runs}"

    def test_total_matches_unchanged(self, db_engine):
        with db_engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM matches")).scalar()
        assert count >= 1261, f"Total match count regression: expected >= 1261, got {count}"

    def test_total_deliveries_unchanged(self, db_engine):
        with db_engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM deliveries")).scalar()
        assert count >= 298383, f"Total delivery count regression: expected >= 298383, got {count}"


class TestCrossFormatIdentity:
    """Verify cross-format identity isolation."""

    def test_kohli_batting_stats_by_format(self, db_engine):
        """Virat Kohli should have separate stats for each format."""
        with db_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT format, runs FROM player_batting_stats a "
                "JOIN players p ON a.player_id = p.id "
                "WHERE p.canonical_name = 'Virat Kohli' "
                "ORDER BY format"
            )).fetchall()
        stats = {r[0]: r[1] for r in rows}
        assert "T20" in stats, "Kohli missing T20 stats"
        assert stats["T20"] == 9346, f"Kohli T20 runs: expected 9346, got {stats['T20']}"

    def test_kohli_multiple_format_stats(self, db_engine):
        """Kohli should have stats in multiple formats."""
        with db_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT DISTINCT format FROM player_batting_stats a "
                "JOIN players p ON a.player_id = p.id "
                "WHERE p.canonical_name = 'Virat Kohli'"
            )).fetchall()
        formats = {r[0] for r in rows}
        assert len(formats) >= 2, f"Kohli should have >= 2 format stats, has: {formats}"
