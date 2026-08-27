"""
Batch CLI — Command-Line Interface for Batch Processing
========================================================

Provides CLI entry point for batch processing:

    python -m data_pipeline.batch --format odi --batch-size 250
    python -m data_pipeline.batch --format odi --resume
    python -m data_pipeline.batch --format odi --batch-id 3 --resume
    python -m data_pipeline.batch --format ipl --batch-size 500 --dry-run
    python -m data_pipeline.batch --status odi

Features:
- Format-specific batch processing
- Configurable batch size
- Checkpoint/resume from failed batches
- Dry-run mode (no database writes)
- Status reporting
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine

from data_pipeline.batch.discovery import (
    discover_files,
    get_batch_files,
    split_into_batches,
    dry_run,
)
from data_pipeline.batch.manifest import BatchManifest
from data_pipeline.batch.runner import BatchRunner
from data_pipeline.pipeline.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from environment."""
    from dotenv import load_dotenv
    load_dotenv()
    return os.environ.get(
        "DATABASE_URL",
        "sqlite:///data/cricket_intelligence.db",
    )


def run_batch_command(args):
    """Execute batch processing."""
    database_url = args.database_url or get_database_url()
    engine = create_engine(database_url)

    # Initialize components
    manifest = BatchManifest(engine)
    manifest.ensure_table()

    db = DatabaseManager(database_url=database_url)
    db.initialize()

    runner = BatchRunner(db=db, manifest=manifest)

    try:
        if args.dry_run:
            # Dry run: show batch boundaries without processing
            num_batches = dry_run(args.data_dir, args.format, args.batch_size)
            return

        if args.status:
            # Show batch status
            manifest.print_summary(args.format)
            return

        if args.resume:
            # Resume from next pending/failed batch
            batch_id = manifest.get_next_pending_batch(args.format)
            if batch_id is None:
                print(f"No pending/failed batches for {args.format}")
                # Check if all completed
                all_batches = manifest.get_all_batches(args.format)
                if all_batches:
                    print("All batches are COMPLETED")
                else:
                    print("No batches found. Run without --resume first.")
                return

            file_paths = get_batch_files(
                args.data_dir, args.format, batch_id, args.batch_size
            )
            print(
                f"Resuming batch {batch_id} "
                f"({len(file_paths)} files)..."
            )
            stats = runner.run_batch(args.format, batch_id, file_paths)

        elif args.batch_id is not None:
            # Process specific batch
            file_paths = get_batch_files(
                args.data_dir, args.format, args.batch_id, args.batch_size
            )
            print(
                f"Processing batch {args.batch_id} "
                f"({len(file_paths)} files)..."
            )
            stats = runner.run_batch(
                args.format, args.batch_id, file_paths
            )

        else:
            # Process all unprocessed batches
            all_files = discover_files(args.data_dir, args.format)
            batches = split_into_batches(all_files, args.batch_size)

            total_matches = 0
            total_deliveries = 0
            total_duration = 0
            completed = 0
            failed = 0

            for batch_id, batch_files in enumerate(batches):
                # Skip completed batches
                batch_status = manifest.get_batch_status(args.format, batch_id)
                if batch_status and batch_status["status"] == "COMPLETED":
                    logger.info(
                        f"Skipping completed batch {batch_id}"
                    )
                    completed += 1
                    continue

                print(
                    f"\nProcessing batch {batch_id + 1}/{len(batches)} "
                    f"({len(batch_files)} files)..."
                )

                stats = runner.run_batch(
                    args.format, batch_id, batch_files
                )

                if stats["status"] == "COMPLETED":
                    completed += 1
                    total_matches += stats["match_count"]
                    total_deliveries += stats["delivery_count"]
                    total_duration += stats["duration_seconds"]
                else:
                    failed += 1
                    # Stop on failure to allow investigation
                    print(f"\nBatch {batch_id} FAILED. Stopping.")
                    print("Fix the issue and run with --resume to continue.")
                    break

            # Final summary
            print(f"\n{'='*60}")
            print(f"BATCH PROCESSING COMPLETE: {args.format.upper()}")
            print(f"{'='*60}")
            print(f"Batches processed: {completed}")
            print(f"Batches failed:    {failed}")
            print(f"Total matches:     {total_matches}")
            print(f"Total deliveries:  {total_deliveries}")
            print(f"Total duration:    {total_duration:.1f}s")
            print(f"{'='*60}")

            # Show manifest summary
            manifest.print_summary(args.format)

    finally:
        db.close()
        engine.dispose()


def status_command(args):
    """Show batch status."""
    database_url = args.database_url or get_database_url()
    engine = create_engine(database_url)

    try:
        manifest = BatchManifest(engine)
        manifest.ensure_table()

        for fmt in args.formats:
            manifest.print_summary(fmt)
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Cricket Intelligence Platform — Batch Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all T20I matches in batches of 250
  python -m data_pipeline.batch --format t20i --batch-size 250

  # Process IPL in batches of 500
  python -m data_pipeline.batch --format ipl --batch-size 500

  # Resume from first failed/pending batch
  python -m data_pipeline.batch --format odi --resume

  # Process specific batch
  python -m data_pipeline.batch --format test --batch-id 3 --batch-size 100

  # Dry run (show batch boundaries without writing)
  python -m data_pipeline.batch --format odi --batch-size 250 --dry-run

  # Show batch status
  python -m data_pipeline.batch --status --formats odi t20i test
        """,
    )

    # Main arguments
    parser.add_argument(
        "--format", "-f",
        choices=["ipl", "t20i", "odi", "test"],
        help="Cricket format to process",
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=250,
        help="Number of files per batch (default: 250)",
    )
    parser.add_argument(
        "--batch-id",
        type=int,
        default=None,
        help="Process a specific batch (0-indexed)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from first pending/failed batch",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show batch boundaries without processing",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/raw",
        help="Root data directory (default: data/raw)",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Override DATABASE_URL",
    )

    # Status command
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show batch manifest status",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["ipl", "t20i", "odi", "test"],
        help="Formats to show status for (with --status)",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.status:
        status_command(args)
    elif args.format:
        run_batch_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
