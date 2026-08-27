"""
Batch Discovery — File Discovery & Splitting
=============================================

Discovers raw match files for a format and splits them into batches.

The splitting is deterministic: the same input files always produce
the same batch membership, enabling checkpoint/resume.

Design:
- Files are sorted alphabetically (consistent across runs)
- Batches are contiguous slices of the sorted file list
- Batch N contains files [N*batch_size, (N+1)*batch_size)
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Map format strings to data directories
FORMAT_DIRECTORIES = {
    "ipl": "ipl",
    "t20i": "t20i",
    "odi": "odi",
    "test": "test",
}


def discover_files(
    data_dir: str | Path,
    format_type: str,
) -> list[Path]:
    """
    Discover all raw match files for a format.

    Args:
        data_dir: Root data directory (e.g., 'data/raw')
        format_type: Format string ('ipl', 't20i', 'odi', 'test')

    Returns:
        Sorted list of JSON file paths

    Raises:
        FileNotFoundError: If directory doesn't exist or no files found
    """
    data_dir = Path(data_dir)
    sub_dir = FORMAT_DIRECTORIES.get(format_type.lower(), format_type.lower())
    format_dir = data_dir / sub_dir

    if not format_dir.exists():
        raise FileNotFoundError(f"Format directory not found: {format_dir}")

    # Discover JSON files (non-recursive, sorted)
    json_files = sorted(format_dir.glob("*.json"))

    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {format_dir}")

    logger.info(f"Discovered {len(json_files)} files in {format_dir}")
    return json_files


def split_into_batches(
    files: list[Path],
    batch_size: int,
) -> list[list[Path]]:
    """
    Split a sorted file list into deterministic batches.

    Args:
        files: Sorted list of file paths
        batch_size: Maximum files per batch

    Returns:
        List of batches, each batch is a list of file paths

    Raises:
        ValueError: If batch_size < 1
    """
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got {batch_size}")

    batches = []
    for i in range(0, len(files), batch_size):
        batch = files[i : i + batch_size]
        batches.append(batch)

    logger.info(
        f"Split {len(files)} files into {len(batches)} batches "
        f"(batch_size={batch_size})"
    )
    return batches


def get_batch_files(
    data_dir: str | Path,
    format_type: str,
    batch_id: int,
    batch_size: int,
) -> list[Path]:
    """
    Get the files for a specific batch.

    This re-derives batch membership from the same deterministic
    splitting logic used during batch creation.

    Args:
        data_dir: Root data directory
        format_type: Format string
        batch_id: Batch number (0-indexed)
        batch_size: Maximum files per batch

    Returns:
        List of file paths for this batch

    Raises:
        IndexError: If batch_id is out of range
    """
    all_files = discover_files(data_dir, format_type)
    batches = split_into_batches(all_files, batch_size)

    if batch_id >= len(batches):
        raise IndexError(
            f"Batch {batch_id} does not exist. "
            f"Total batches: {len(batches)} (for {len(all_files)} files, "
            f"batch_size={batch_size})"
        )

    return batches[batch_id]


def compute_file_hash(files: list[Path]) -> str:
    """
    Compute a deterministic hash of a file list.

    Useful for verifying batch membership hasn't changed.
    """
    names = [f.name for f in sorted(files)]
    content = "|".join(names)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def dry_run(
    data_dir: str | Path,
    format_type: str,
    batch_size: int,
):
    """
    Print batch boundaries without modifying the database.

    Args:
        data_dir: Root data directory
        format_type: Format string
        batch_size: Maximum files per batch
    """
    all_files = discover_files(data_dir, format_type)
    batches = split_into_batches(all_files, batch_size)

    print(f"\n{'='*60}")
    print(f"Dry Run: {format_type.upper()}")
    print(f"{'='*60}")
    print(f"Total files: {len(all_files)}")
    print(f"Batch size:  {batch_size}")
    print(f"Total batches: {len(batches)}")
    print(f"\n{'Batch':>6} {'Files':>8} {'First File':<30} {'Last File':<30}")
    print(f"{'-'*80}")

    for i, batch in enumerate(batches):
        first = batch[0].name
        last = batch[-1].name
        print(f"{i:>6} {len(batch):>8} {first:<30} {last:<30}")

    print(f"{'='*60}")
    return len(batches)
