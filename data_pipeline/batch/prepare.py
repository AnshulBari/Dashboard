"""
Historical Dataset Preparation
==============================

Extracts Cricsheet ZIP files and prepares JSON match files for batch ingestion.

Handles:
- ZIP extraction to per-format directories
- Gender filtering (men's only by default)
- Format remapping (Cricsheet 'T20' + team_type='international' -> 'T20I')
- Match ID assignment from filename
- Malformed file detection and quarantine

Does NOT:
- Ingest into PostgreSQL
- Modify the original ZIP
- Load entire dataset into memory

Usage:
    python -m data_pipeline.batch.prepare --format t20i
    python -m data_pipeline.batch.prepare --format odi
    python -m data_pipeline.batch.prepare --format test
    python -m data_pipeline.batch.prepare --format all
"""

import json
import logging
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ZIP file locations
ZIP_PATHS = {
    "t20i": "data/raw/t20i/t20s_json.zip",
    "odi": "data/raw/odi/odis_json.zip",
    "test": "data/raw/test/tests_json.zip",
}


def extract_and_prepare(
    format_type: str,
    data_dir: str = "data/raw",
    gender: str = "male",
    dry_run: bool = False,
) -> dict:
    """
    Extract a Cricsheet ZIP and prepare JSON files for ingestion.

    Args:
        format_type: 't20i', 'odi', 'test'
        data_dir: Root data directory
        gender: Filter by gender ('male', 'female', or 'all')
        dry_run: If True, report statistics without writing files

    Returns:
        dict with extraction statistics
    """
    data_dir = Path(data_dir)
    fmt_dir = data_dir / format_type
    zip_path = data_dir / format_type / _zip_filename(format_type)

    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP not found: {zip_path}")

    stats = {
        "format": format_type,
        "zip_path": str(zip_path),
        "total_files": 0,
        "json_files": 0,
        "extracted": 0,
        "filtered_out": 0,
        "format_remapped": 0,
        "malformed": 0,
        "errors": [],
    }

    with zipfile.ZipFile(zip_path, "r") as z:
        all_files = z.namelist()
        json_files = [f for f in all_files if f.endswith(".json")]
        stats["total_files"] = len(all_files)
        stats["json_files"] = len(json_files)

        if dry_run:
            # Just report statistics
            _report_zip_stats(z, json_files, format_type, gender)
            return stats

        # Create output directory
        fmt_dir.mkdir(parents=True, exist_ok=True)

        extracted = 0
        filtered = 0
        remapped = 0
        malformed = 0

        for fname in json_files:
            try:
                data = json.loads(z.read(fname))
                info = data.get("info", {})

                # Gender filter
                file_gender = info.get("gender", "")
                if gender != "all" and file_gender != gender:
                    filtered += 1
                    continue

                # Format remapping
                match_type = info.get("match_type", "")
                team_type = info.get("team_type", "")
                original_match_type = match_type

                if format_type == "t20i" and match_type == "T20" and team_type == "international":
                    match_type = "T20I"
                    remapped += 1

                # Assign match ID from filename
                match_id = Path(fname).stem
                data["match_id"] = match_id

                # Store original match_type for reference
                if "meta" not in data:
                    data["meta"] = {}
                data["meta"]["original_match_type"] = original_match_type
                data["meta"]["prepared_format"] = match_type

                # Write prepared file
                out_path = fmt_dir / fname
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, separators=(",", ":"))

                extracted += 1

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                malformed += 1
                stats["errors"].append(f"{fname}: {e}")
                if malformed <= 5:
                    logger.warning(f"  Malformed file: {fname}: {e}")

        stats["extracted"] = extracted
        stats["filtered_out"] = filtered
        stats["format_remapped"] = remapped
        stats["malformed"] = malformed

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"Extraction Complete: {format_type.upper()}")
    logger.info(f"{'='*60}")
    logger.info(f"ZIP files:        {stats['total_files']}")
    logger.info(f"JSON files:       {stats['json_files']}")
    logger.info(f"Extracted:        {stats['extracted']}")
    logger.info(f"Filtered out:     {stats['filtered_out']} ({gender} filter)")
    logger.info(f"Format remapped:  {stats['format_remapped']} (T20 -> T20I)")
    logger.info(f"Malformed:        {stats['malformed']}")
    logger.info(f"Output directory: {fmt_dir}")
    logger.info(f"{'='*60}")

    return stats


def _zip_filename(format_type: str) -> str:
    """Get expected ZIP filename for a format."""
    names = {
        "t20i": "t20s_json.zip",
        "odi": "odis_json.zip",
        "test": "tests_json.zip",
    }
    return names.get(format_type, f"{format_type}_json.zip")


def _report_zip_stats(
    z: zipfile.ZipFile, json_files: list, format_type: str, gender: str
):
    """Report ZIP statistics without extracting."""
    genders = {}
    match_types = {}
    team_types = {}
    dates = []
    errors = 0
    male_count = 0
    remappable = 0

    sample_size = min(500, len(json_files))

    for fname in json_files[:sample_size]:
        try:
            data = json.loads(z.read(fname))
            info = data.get("info", {})

            g = info.get("gender", "unknown")
            genders[g] = genders.get(g, 0) + 1

            mt = info.get("match_type", "unknown")
            match_types[mt] = match_types.get(mt, 0) + 1

            tt = info.get("team_type", "unknown")
            team_types[tt] = team_types.get(tt, 0) + 1

            d = info.get("dates", [""])[0]
            if d:
                dates.append(d)

            if g == "male":
                male_count += 1
                if mt == "T20" and tt == "international":
                    remappable += 1

        except Exception:
            errors += 1

    print(f"\n{'='*60}")
    print(f"ZIP Analysis: {format_type.upper()}")
    print(f"{'='*60}")
    print(f"Total JSON files:  {len(json_files)}")
    print(f"Sampled:           {sample_size}")
    print(f"\nGender distribution (sampled):")
    for g, c in sorted(genders.items()):
        pct = c / sample_size * 100
        print(f"  {g}: {c} ({pct:.0f}%)")
    print(f"\nMatch types (sampled):")
    for mt, c in sorted(match_types.items()):
        print(f"  {mt}: {c}")
    print(f"\nTeam types (sampled):")
    for tt, c in sorted(team_types.items()):
        print(f"  {tt}: {c}")
    if dates:
        print(f"\nDate range: {min(dates)} to {max(dates)}")
    if errors:
        print(f"\nParse errors: {errors}")

    # Estimate male matches
    if genders:
        male_pct = genders.get("male", 0) / sample_size
        estimated_male = int(len(json_files) * male_pct)
        print(f"\nEstimated male matches: ~{estimated_male} of {len(json_files)}")
        if format_type == "t20i":
            print(f"  (T20I format remapping needed for {remappable} sampled male matches)")

    print(f"{'='*60}")


def validate_extraction(format_type: str, data_dir: str = "data/raw") -> dict:
    """
    Validate extracted JSON files are compatible with the batch runner.

    Returns validation report.
    """
    data_dir = Path(data_dir)
    fmt_dir = data_dir / format_type

    if not fmt_dir.exists():
        return {"status": "ERROR", "message": f"Directory not found: {fmt_dir}"}

    json_files = sorted(fmt_dir.glob("*.json"))
    if not json_files:
        return {"status": "ERROR", "message": f"No JSON files in {fmt_dir}"}

    report = {
        "status": "OK",
        "format": format_type,
        "total_files": len(json_files),
        "valid": 0,
        "invalid": 0,
        "issues": [],
        "sample_formats": {},
        "missing_match_id": 0,
        "missing_innings": 0,
    }

    for fp in json_files[:100]:  # Validate sample
        try:
            with open(fp, "r") as f:
                data = json.load(f)

            # Check required fields
            if "match_id" not in data:
                report["missing_match_id"] += 1
            if "innings" not in data or not data["innings"]:
                report["missing_innings"] += 1
                continue

            info = data.get("info", {})
            fmt = info.get("match_type", "unknown")
            report["sample_formats"][fmt] = report["sample_formats"].get(fmt, 0) + 1

            # Check innings structure
            for innings in data["innings"]:
                if "team" not in innings:
                    report["issues"].append(f"{fp.name}: innings missing 'team'")
                if "overs" not in innings:
                    report["issues"].append(f"{fp.name}: innings missing 'overs'")

            report["valid"] += 1

        except Exception as e:
            report["invalid"] += 1
            report["issues"].append(f"{fp.name}: {e}")

    if report["invalid"] > 0:
        report["status"] = "WARN"

    return report


def list_prepared_files(format_type: str, data_dir: str = "data/raw") -> list:
    """List all prepared JSON files for a format."""
    data_dir = Path(data_dir)
    fmt_dir = data_dir / format_type
    if not fmt_dir.exists():
        return []
    return sorted(fmt_dir.glob("*.json"))


def cleanup_prepared(format_type: str, data_dir: str = "data/raw"):
    """Remove extracted JSON files (keep ZIP)."""
    data_dir = Path(data_dir)
    fmt_dir = data_dir / format_type
    if not fmt_dir.exists():
        return

    json_files = list(fmt_dir.glob("*.json"))
    for fp in json_files:
        fp.unlink()
    logger.info(f"Cleaned up {len(json_files)} files from {fmt_dir}")


# ============================================================
# CLI
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Prepare Cricsheet ZIP for batch ingestion"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["t20i", "odi", "test", "all"],
        required=True,
        help="Format to prepare"
    )
    parser.add_argument(
        "--data-dir", default="data/raw",
        help="Root data directory (default: data/raw)"
    )
    parser.add_argument(
        "--gender", choices=["male", "female", "all"],
        default="male",
        help="Gender filter (default: male)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report statistics without extracting"
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Validate already-extracted files"
    )
    parser.add_argument(
        "--cleanup", action="store_true",
        help="Remove extracted files (keep ZIPs)"
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    formats = ["t20i", "odi", "test"] if args.format == "all" else [args.format]

    for fmt in formats:
        if args.cleanup:
            cleanup_prepared(fmt, args.data_dir)
        elif args.validate:
            report = validate_extraction(fmt, args.data_dir)
            print(json.dumps(report, indent=2))
        else:
            stats = extract_and_prepare(
                fmt, data_dir=args.data_dir,
                gender=args.gender, dry_run=args.dry_run,
            )


if __name__ == "__main__":
    main()
