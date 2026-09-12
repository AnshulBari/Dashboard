"""Refresh the bundled ICC men's rankings snapshot.

Run on (or after) Wednesday, when ICC publishes its weekly men's rankings:

    python scripts/sync_icc_rankings.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.providers.icc_rankings import ICCRankingsProvider  # noqa: E402


FORMATS = ("Test", "ODI", "T20I")
CATEGORIES = ("batting", "bowling", "allrounder", "teams")


def main() -> int:
    provider = ICCRankingsProvider(timeout_seconds=30.0)
    rankings: dict[str, dict[str, dict]] = {}

    for format_name in FORMATS:
        rankings[format_name] = {}
        for category in CATEGORIES:
            ranking = provider._request(format_name, category)
            rankings[format_name][category] = {
                "rank_date": ranking.get("rank_date"),
                "last_updated": ranking.get("last_updated"),
                "entries": ranking.get("rank", []),
            }
            print(
                f"{format_name}/{category}: "
                f"{len(rankings[format_name][category]['entries'])} rows "
                f"({ranking.get('rank_date')})"
            )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "ICC official rankings",
        "source_url": "https://www.icc-cricket.com/rankings",
        "rankings": rankings,
    }
    provider.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    provider.snapshot_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {provider.snapshot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

