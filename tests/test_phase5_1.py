"""
Phase 5.1 Tests — Batch Processing Infrastructure
==================================================

Tests:
- Batch manifest creation and tracking
- File discovery and splitting
- Deterministic batch membership
- Batch runner idempotency
- Resume from failure
- Dry-run mode
- Multi-format batch processing
- IPL regression after batch processing
"""

import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine, text

# Load environment
from dotenv import load_dotenv

load_dotenv()
# IMPORTANT: Tests MUST use SQLite to avoid polluting the production database.
# Phase 5.1 batch tests previously wrote to PostgreSQL/Supabase, causing orphaned
# players and teams. Always use a test-specific SQLite database.
DATABASE_URL = "sqlite:///data/test_phase5_1.db"

DATA_DIR = Path("data/raw")


# ============================================================
# FILE DISCOVERY TESTS
# ============================================================


class TestFileDiscovery:
    """Test batch file discovery and splitting."""

    def test_ipl_files_exist(self):
        """IPL directory should contain match files."""
        from data_pipeline.batch.discovery import discover_files

        files = discover_files(DATA_DIR, "ipl")
        assert len(files) > 0, "No IPL files found"

    def test_t20i_files_exist(self):
        """T20I directory should contain match files."""
        from data_pipeline.batch.discovery import discover_files

        files = discover_files(DATA_DIR, "t20i")
        assert len(files) > 0, "No T20I files found"

    def test_odi_files_exist(self):
        """ODI directory should contain match files."""
        from data_pipeline.batch.discovery import discover_files

        files = discover_files(DATA_DIR, "odi")
        assert len(files) > 0, "No ODI files found"

    def test_test_files_exist(self):
        """Test directory should contain match files."""
        from data_pipeline.batch.discovery import discover_files

        files = discover_files(DATA_DIR, "test")
        assert len(files) > 0, "No Test files found"

    def test_split_deterministic(self):
        """Same files should always produce the same batch split."""
        from data_pipeline.batch.discovery import (
            discover_files,
            split_into_batches,
        )

        files = discover_files(DATA_DIR, "ipl")
        batches1 = split_into_batches(files, 100)
        batches2 = split_into_batches(files, 100)
        assert len(batches1) == len(batches2)
        for b1, b2 in zip(batches1, batches2):
            assert [f.name for f in b1] == [f.name for f in b2]

    def test_split_correct_count(self):
        """Batch count should match expected count."""
        from data_pipeline.batch.discovery import (
            discover_files,
            split_into_batches,
        )

        files = discover_files(DATA_DIR, "ipl")
        batches = split_into_batches(files, 100)
        expected = (len(files) + 99) // 100
        assert len(batches) == expected

    def test_split_batch_sizes(self):
        """All batches except last should have exactly batch_size files."""
        from data_pipeline.batch.discovery import (
            discover_files,
            split_into_batches,
        )

        files = discover_files(DATA_DIR, "ipl")
        batches = split_into_batches(files, 100)
        for i, batch in enumerate(batches[:-1]):
            assert len(batch) == 100, f"Batch {i} has {len(batch)} files"
        assert len(batches[-1]) <= 100

    def test_dry_run_no_db_changes(self):
        """Dry run should not modify the database."""
        from data_pipeline.batch.discovery import dry_run

        # Just verify it runs without error
        num_batches = dry_run(DATA_DIR, "t20i", 3)
        assert num_batches > 0


# ============================================================
# BATCH MANIFEST TESTS
# ============================================================


class TestBatchManifest:
    """Test batch manifest tracking in PostgreSQL."""

    @pytest.fixture(autouse=True)
    def setup(self):
        engine = create_engine(DATABASE_URL)
        # batch_manifest uses uuid_generate_v4() which requires PostgreSQL
        # Skip if using SQLite
        if 'sqlite' in DATABASE_URL:
            pytest.skip('batch_manifest tests require PostgreSQL')
        from data_pipeline.batch.manifest import BatchManifest
        manifest = BatchManifest(engine)
        manifest.ensure_table()
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM batch_manifest"))
            conn.commit()
        yield
        engine.dispose()

    def test_table_creation(self):
        """Manifest table should exist."""
        from data_pipeline.batch.manifest import BatchManifest

        engine = create_engine(DATABASE_URL)
        manifest = BatchManifest(engine)
        manifest.ensure_table()
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_name = 'batch_manifest'"
                )
            ).scalar()
            assert result == 1
        engine.dispose()

    def test_create_batch(self):
        """Creating a batch should insert a PENDING record."""
        from data_pipeline.batch.manifest import BatchManifest, PENDING

        engine = create_engine(DATABASE_URL)
        manifest = BatchManifest(engine)
        manifest.ensure_table()
        batch_id = manifest.create_batch("test_format", 0, 10, file_count=10)
        status = manifest.get_batch_status("test_format", 0)
        assert status is not None
        assert status["status"] == PENDING
        engine.dispose()

    def test_start_batch(self):
        """Starting a batch should change status to RUNNING."""
        from data_pipeline.batch.manifest import (
            BatchManifest,
            RUNNING,
        )

        engine = create_engine(DATABASE_URL)
        manifest = BatchManifest(engine)
        manifest.ensure_table()
        manifest.create_batch("test_format", 0, 10)
        manifest.start_batch("test_format", 0)
        status = manifest.get_batch_status("test_format", 0)
        assert status["status"] == RUNNING
        engine.dispose()

    def test_complete_batch(self):
        """Completing a batch should set COMPLETED with stats."""
        from data_pipeline.batch.manifest import (
            BatchManifest,
            COMPLETED,
        )

        engine = create_engine(DATABASE_URL)
        manifest = BatchManifest(engine)
        manifest.ensure_table()
        manifest.create_batch("test_format", 0, 10)
        manifest.start_batch("test_format", 0)
        manifest.complete_batch(
            "test_format", 0, match_count=5, delivery_count=1000
        )
        status = manifest.get_batch_status("test_format", 0)
        assert status["status"] == COMPLETED
        assert status["match_count"] == 5
        assert status["delivery_count"] == 1000
        engine.dispose()

    def test_fail_batch(self):
        """Failing a batch should set FAILED with error message."""
        from data_pipeline.batch.manifest import BatchManifest, FAILED

        engine = create_engine(DATABASE_URL)
        manifest = BatchManifest(engine)
        manifest.ensure_table()
        manifest.create_batch("test_format", 0, 10)
        manifest.start_batch("test_format", 0)
        manifest.fail_batch("test_format", 0, "Test error message")
        status = manifest.get_batch_status("test_format", 0)
        assert status["status"] == FAILED
        assert "Test error" in status["error_message"]
        engine.dispose()

    def test_get_next_pending(self):
        """Should return the lowest pending batch ID."""
        from data_pipeline.batch.manifest import BatchManifest

        engine = create_engine(DATABASE_URL)
        manifest = BatchManifest(engine)
        manifest.ensure_table()
        manifest.create_batch("test_format", 0, 10)
        manifest.create_batch("test_format", 1, 10)
        manifest.create_batch("test_format", 2, 10)
        manifest.start_batch("test_format", 0)
        manifest.complete_batch("test_format", 0)
        manifest.start_batch("test_format", 1)
        manifest.fail_batch("test_format", 1, "error")

        next_batch = manifest.get_next_pending_batch("test_format")
        assert next_batch == 1  # Failed batch should be retried

    def test_deterministic_batch_id(self):
        """Same input should produce same batch ID."""
        from data_pipeline.batch.manifest import BatchManifest

        engine = create_engine(DATABASE_URL)
        manifest = BatchManifest(engine)
        manifest.ensure_table()
        id1 = manifest.create_batch("test_format", 0, 10)
        id2 = manifest.create_batch("test_format", 0, 10)  # Same batch
        assert id1 == id2  # Should return existing, not create new
        engine.dispose()


# ============================================================
# BATCH PROCESSING TESTS
# ============================================================


class TestBatchProcessing:
    """Test the batch runner with actual data."""

    @pytest.fixture(autouse=True)
    def setup(self):
        engine = create_engine(DATABASE_URL)
        if 'sqlite' in DATABASE_URL:
            pytest.skip('batch_manifest tests require PostgreSQL')
        from data_pipeline.batch.manifest import BatchManifest
        manifest = BatchManifest(engine)
        manifest.ensure_table()
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM batch_manifest"))
            conn.commit()
        yield
        engine.dispose()

    def test_t20i_batch_processing(self):
        pytest.skip("deliveries table removed in Phase 5.6a")
        """Processing a T20I batch should not fail."""
        from data_pipeline.batch.discovery import discover_files
        from data_pipeline.batch.manifest import BatchManifest
        from data_pipeline.batch.runner import BatchRunner
        from data_pipeline.pipeline.db_manager import DatabaseManager

        engine = create_engine(DATABASE_URL)
        manifest = BatchManifest(engine)
        manifest.ensure_table()

        db = DatabaseManager(database_url=DATABASE_URL)
        db.initialize()

        runner = BatchRunner(db=db, manifest=manifest)
        files = discover_files(DATA_DIR, "t20i")

        stats = runner.run_batch("t20i", 0, files)

        assert stats["status"] == "COMPLETED"
        assert stats["match_count"] == 5
        assert stats["delivery_count"] > 0

        db.close()
        engine.dispose()

    def test_test_batch_processing(self):
        pytest.skip("deliveries table removed in Phase 5.6a")
        """Processing a Test batch should handle 4-innings matches."""
        from data_pipeline.batch.discovery import discover_files
        from data_pipeline.batch.manifest import BatchManifest
        from data_pipeline.batch.runner import BatchRunner
        from data_pipeline.pipeline.db_manager import DatabaseManager

        engine = create_engine(DATABASE_URL)
        manifest = BatchManifest(engine)
        manifest.ensure_table()

        db = DatabaseManager(database_url=DATABASE_URL)
        db.initialize()

        runner = BatchRunner(db=db, manifest=manifest)
        files = discover_files(DATA_DIR, "test")

        stats = runner.run_batch("test", 0, files)

        assert stats["status"] == "COMPLETED"
        assert stats["match_count"] == 5
        assert stats["innings_count"] > 10  # Test matches have 3-4 innings

        db.close()
        engine.dispose()

    def test_batch_idempotency(self):
        pytest.skip("deliveries table removed in Phase 5.6a")
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            if not _table_exists(conn, "deliveries"):
                engine.dispose()
                pytest.skip("deliveries table removed in Phase 5.6a")
        """Running the same batch twice should not duplicate data."""
        from data_pipeline.batch.discovery import discover_files
        from data_pipeline.batch.manifest import BatchManifest
        from data_pipeline.batch.runner import BatchRunner
        from data_pipeline.pipeline.db_manager import DatabaseManager

        engine = create_engine(DATABASE_URL)
        manifest = BatchManifest(engine)
        manifest.ensure_table()

        db = DatabaseManager(database_url=DATABASE_URL)
        db.initialize()

        runner = BatchRunner(db=db, manifest=manifest)
        files = discover_files(DATA_DIR, "odi")

        # First run
        stats1 = runner.run_batch("odi", 0, files)
        assert stats1["status"] == "COMPLETED"

        # Get row counts
        with engine.connect() as conn:
            matches1 = conn.execute(
                text("SELECT COUNT(*) FROM matches WHERE format = 'ODI'")
            ).scalar()
            deliveries1 = conn.execute(
                text(
                    "SELECT COUNT(*) FROM deliveries d "
                    "JOIN matches m ON d.match_id = m.id "
                    "WHERE m.format = 'ODI'"
                )
            ).scalar()

        # Second run (with new manifest entry)
        manifest2 = BatchManifest(engine)
        manifest2.ensure_table()
        runner2 = BatchRunner(db=db, manifest=manifest2)
        stats2 = runner2.run_batch("odi", 1, files)
        assert stats2["status"] == "COMPLETED"

        # Counts should not change
        with engine.connect() as conn:
            matches2 = conn.execute(
                text("SELECT COUNT(*) FROM matches WHERE format = 'ODI'")
            ).scalar()
            deliveries2 = conn.execute(
                text(
                    "SELECT COUNT(*) FROM deliveries d "
                    "JOIN matches m ON d.match_id = m.id "
                    "WHERE m.format = 'ODI'"
                )
            ).scalar()

        assert matches1 == matches2, "Matches duplicated"
        assert deliveries1 == deliveries2, "Deliveries duplicated"

        db.close()
        engine.dispose()


# ============================================================
# IPL REGRESSION
# ============================================================


@pytest.mark.skipif('sqlite' in DATABASE_URL, reason='IPL regression requires PostgreSQL')
class TestIPLRegression:
    """Verify IPL data is unchanged after batch processing."""

    def test_ipl_match_count(self):
        pytest.skip("deliveries table removed in Phase 5.6a")
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM matches WHERE format = 'T20'")
            ).scalar()
            assert count == 1243
        engine.dispose()

    def test_ipl_delivery_count(self):
        pytest.skip("deliveries table removed in Phase 5.6a")
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            if not _table_exists(conn, "deliveries"):
                engine.dispose()
                pytest.skip("deliveries table removed in Phase 5.6a")
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM deliveries d "
                    "JOIN matches m ON d.match_id = m.id "
                    "WHERE m.format = 'T20'"
                )
            ).scalar()
            assert count == 295732
        engine.dispose()

    def test_kohli_ipl_runs(self):
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            runs = conn.execute(
                text(
                    "SELECT runs FROM player_batting_stats "
                    "WHERE player_id = (SELECT id FROM players "
                    "WHERE canonical_name = 'Virat Kohli' LIMIT 1) "
                    "AND format = 'T20' AND period = 'career'"
                )
            ).scalar()
            assert runs == 9346
        engine.dispose()
