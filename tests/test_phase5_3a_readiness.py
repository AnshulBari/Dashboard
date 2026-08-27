"""
Phase 5.3A Tests: Historical Dataset Preparation & Ingestion Readiness
=====================================================================

Tests for:
1. ZIP file existence and integrity
2. Extraction and format remapping
3. Batch runner compatibility
4. Gender filtering
5. Match ID assignment
6. .gitignore verification
7. Reader compatibility
"""

import json
import os
import zipfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path("data/raw")


class TestZipIntegrity:
    """Verify downloaded ZIPs are valid."""

    def test_t20i_zip_exists(self):
        assert (DATA_DIR / "t20i" / "t20s_json.zip").exists()

    def test_odi_zip_exists(self):
        assert (DATA_DIR / "odi" / "odis_json.zip").exists()

    def test_test_zip_exists(self):
        assert (DATA_DIR / "test" / "tests_json.zip").exists()

    def test_t20i_zip_valid(self):
        zf = DATA_DIR / "t20i" / "t20s_json.zip"
        with zipfile.ZipFile(zf, "r") as z:
            json_files = [f for f in z.namelist() if f.endswith(".json")]
            assert len(json_files) > 1000, f"Expected >1000 T20I files, got {len(json_files)}"

    def test_t20i_zip_contains_mens_matches(self):
        """ZIP should contain male T20I matches."""
        zf = DATA_DIR / "t20i" / "t20s_json.zip"
        with zipfile.ZipFile(zf, "r") as z:
            json_files = [f for f in z.namelist() if f.endswith(".json")]
            # Sample to check gender
            males = 0
            for fname in json_files[:100]:
                data = json.loads(z.read(fname))
                if data.get("info", {}).get("gender") == "male":
                    males += 1
            assert males > 10, f"Expected male matches in ZIP, found {males}/100"


class TestExtraction:
    """Verify extraction and format remapping."""

    @pytest.fixture(scope="class")
    def extracted_t20i(self):
        """Extract T20I and return stats."""
        from data_pipeline.batch.prepare import extract_and_prepare
        stats = extract_and_prepare("t20i", gender="male")
        return stats

    def test_extraction_count(self, extracted_t20i):
        assert extracted_t20i["extracted"] > 1000, \
            f"Expected >1000 extracted, got {extracted_t20i['extracted']}"

    def test_no_malformed_files(self, extracted_t20i):
        assert extracted_t20i["malformed"] == 0, \
            f"Found {extracted_t20i['malformed']} malformed files"

    def test_gender_filtered(self, extracted_t20i):
        assert extracted_t20i["filtered_out"] > 0, \
            "Should have filtered out women's matches"

    def test_format_remapped(self, extracted_t20i):
        assert extracted_t20i["format_remapped"] > 0, \
            "Should have remapped T20 -> T20I"

    def test_remapped_files_correct(self):
        """Verify extracted files have correct format in meta."""
        files = sorted(Path("data/raw/t20i").glob("*.json"))[:10]
        for fp in files:
            with open(fp) as f:
                data = json.load(f)
            info = data.get("info", {})
            meta = data.get("meta", {})
            if info.get("team_type") == "international":
                assert meta.get("prepared_format") == "T20I", \
                    f"{fp.name}: expected prepared_format=T20I"

    def test_match_id_assigned(self):
        """Extracted files should have match_id from filename."""
        files = sorted(Path("data/raw/t20i").glob("*.json"))[:5]
        for fp in files:
            with open(fp) as f:
                data = json.load(f)
            assert data.get("match_id") == fp.stem, \
                f"{fp.name}: match_id should be {fp.stem}"


class TestBatchCompatibility:
    """Verify batch runner can process extracted files."""

    def test_discover_files_finds_extracted(self):
        from data_pipeline.batch.discovery import discover_files
        files = discover_files(DATA_DIR, "t20i")
        assert len(files) > 1000, f"Expected >1000 files, got {len(files)}"

    def test_batch_runner_reads_files(self):
        """Batch runner can read and flatten extracted files."""
        from data_pipeline.batch.runner import BatchRunner
        from pathlib import Path

        # Create a minimal runner to test reading only
        class FakeDB:
            _player_ids = {}
            _player_name_mappings = {}
            _team_ids = {}
            _venue_ids = {}
            _competition_ids = {}
            _match_ids = {}
            _innings_ids = {}

        runner = BatchRunner.__new__(BatchRunner)
        runner.db = FakeDB()

        files = sorted(Path("data/raw/t20i").glob("*.json"))[:3]
        df = runner._read_batch_files(files)

        assert len(df) > 0, "Should read deliveries from files"
        assert df["match_id"].nunique() == 3, "Should have 3 matches"
        assert all(df["format"] == "T20I"), f"Format should be T20I, got {df['format'].unique()}"

    def test_dry_run_works(self):
        """Batch dry run should complete without errors."""
        from data_pipeline.batch.discovery import dry_run
        num_batches = dry_run(DATA_DIR, "t20i", 250)
        assert num_batches > 10, f"Expected >10 batches, got {num_batches}"


class TestGitignore:
    """Verify .gitignore excludes large data files."""

    def test_raw_dir_excluded(self):
        gitignore = Path(".gitignore").read_text()
        assert "data/raw/*" in gitignore, "data/raw/* should be in .gitignore"

    def test_git_status_clean(self):
        """git status should show no untracked large files."""
        import subprocess
        result = subprocess.run(
            ["git", "status", "data/raw/"],
            capture_output=True, text=True, cwd=str(Path.cwd())
        )
        assert "nothing to commit" in result.stdout or "Untracked" not in result.stdout, \
            f"Untracked files in data/raw/: {result.stdout[:200]}"


class TestProductionSafety:
    """Verify tests don't pollute production database."""

    def test_phase5_1_uses_sqlite(self):
        """Phase 5.1 tests should use SQLite, not PostgreSQL."""
        test_file = Path("tests/test_phase5_1.py").read_text()
        assert "sqlite:///" in test_file, "Phase 5.1 tests should use SQLite"
        # Should NOT use production DATABASE_URL for test writes
        assert 'DATABASE_URL = "sqlite:///data/test_phase5_1.db"' in test_file, \
            "Phase 5.1 tests should use test-specific SQLite"
