"""Build a compact player-ID to ESPN headshot-ID map from local Cricsheet data.

This uses the registry embedded in each match, including the team context, to
disambiguate shared names. Run from the repository root after refreshing match
data or the Cricsheet Register snapshot.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER_DIR = ROOT / "data" / "reference" / "cricsheet-register"
DATABASE = ROOT / "data" / "cricket_intelligence.db"
OUTPUT = REGISTER_DIR / "player-image-map.json"
RAW_DIRS = tuple(ROOT / "data" / "raw" / name for name in ("ipl", "odi", "t20i", "test"))

# The synthetic recent-match fixtures use expanded display names but intentionally
# contain an empty registry. These team-scoped IDs are the matching entries in the
# downloaded Cricsheet Register and keep the fixture layer reproducible.
FIXTURE_ESPN_IDS = {
    ("shahnawaz dahani", ""): "1217276",
    ("brad evans", ""): "696127",
    ("brandon king", "west indies"): "670035",
    ("dilshan madushanka", "sri lanka"): "793007",
    ("dunith wellalage", ""): "1152427",
    ("innocent kaia", "zimbabwe"): "465327",
    ("jimmy neesham", "new zealand"): "355269",
    ("joylord gumbi", "zimbabwe"): "596376",
    ("kedar jadhav", "india"): "290716",
    ("litton das", "bangladesh"): "536936",
    ("maheesh theekshana", "sri lanka"): "1138316",
    ("matheesha pathirana", "sri lanka"): "1194795",
    ("matt henry", "new zealand"): "506612",
    ("ravichandran ashwin", "india"): "26421",
    ("rovman powell", "west indies"): "820351",
    ("salman agha", "pakistan"): "623977",
    ("shimron hetmyer", "west indies"): "670025",
    ("tadiwanashe marumani", "zimbabwe"): "946507",
    ("chris rogers", "australia"): "7388",
    ("todd murphy", "australia"): "1193685",
    ("yashasvi jaiswal", "india"): "1151278",
}


def normalize(value: str | None) -> str:
    if not value:
        return ""
    ascii_value = "".join(
        char
        for char in unicodedata.normalize("NFKD", value.replace("’", "'"))
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def load_register() -> tuple[dict[str, str], dict[str, set[str]]]:
    cricsheet_to_espn: dict[str, str] = {}
    register_names: defaultdict[str, set[str]] = defaultdict(set)
    with (REGISTER_DIR / "people.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            image_id = next(
                (row.get(column, "").strip() for column in ("key_cricinfo", "key_cricinfo_2", "key_cricinfo_3") if row.get(column, "").strip()),
                "",
            )
            identifier = row.get("identifier", "").strip()
            if not identifier or not image_id:
                continue
            cricsheet_to_espn[identifier] = image_id
            for column in ("name", "unique_name"):
                if normalized := normalize(row.get(column)):
                    register_names[normalized].add(image_id)
    with (REGISTER_DIR / "names.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            image_id = cricsheet_to_espn.get(row.get("identifier", "").strip())
            if image_id and (normalized := normalize(row.get("name"))):
                register_names[normalized].add(image_id)
    return cricsheet_to_espn, register_names


def load_raw_identities() -> tuple[dict[tuple[str, str], set[str]], dict[str, set[str]], int]:
    by_name_team: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    by_name: defaultdict[str, set[str]] = defaultdict(set)
    files_read = 0
    for raw_dir in RAW_DIRS:
        for path in raw_dir.rglob("*.json"):
            try:
                info = json.loads(path.read_text(encoding="utf-8")).get("info", {})
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            files_read += 1
            registry = info.get("registry", {}).get("people", {})
            if not isinstance(registry, dict):
                continue
            for team, names in info.get("players", {}).items():
                for name in names:
                    identifier = registry.get(name)
                    if identifier:
                        by_name_team[(normalize(name), normalize(team))].add(identifier)
                        by_name[normalize(name)].add(identifier)
            for name, identifier in registry.items():
                if identifier:
                    by_name[normalize(name)].add(identifier)
    return by_name_team, by_name, files_read


def main() -> None:
    cricsheet_to_espn, register_names = load_register()
    by_name_team, by_name, files_read = load_raw_identities()

    connection = sqlite3.connect(DATABASE)
    players = connection.execute(
        """
        SELECT p.id, p.canonical_name, p.full_name, t.canonical_name
        FROM players p LEFT JOIN teams t ON p.team_id = t.id
        WHERE p.is_active = 1
        """
    ).fetchall()
    variants: defaultdict[str, list[str]] = defaultdict(list)
    for player_id, name in connection.execute("SELECT player_id, name_variant FROM player_name_mappings"):
        variants[str(player_id)].append(name)
    connection.close()

    result: dict[str, str] = {}
    fixture_matches = raw_team_matches = raw_alias_matches = register_matches = 0
    for player_id, canonical_name, full_name, team_name in players:
        player_id = str(player_id)
        names = [*variants[player_id], full_name, canonical_name]

        fixture_image_id = (
            FIXTURE_ESPN_IDS.get((normalize(canonical_name), normalize(team_name)))
            or FIXTURE_ESPN_IDS.get((normalize(canonical_name), ""))
        )
        if fixture_image_id:
            result[player_id] = fixture_image_id
            fixture_matches += 1
            continue

        team_ids: set[str] = set()
        for name in names:
            team_ids.update(by_name_team.get((normalize(name), normalize(team_name)), set()))
        image_ids = {cricsheet_to_espn[value] for value in team_ids if value in cricsheet_to_espn}
        if len(image_ids) == 1:
            result[player_id] = next(iter(image_ids))
            raw_team_matches += 1
            continue

        unique_alias_ids: set[str] = set()
        for name in names:
            raw_ids = by_name.get(normalize(name), set())
            resolved = {cricsheet_to_espn[value] for value in raw_ids if value in cricsheet_to_espn}
            if len(resolved) == 1:
                unique_alias_ids.update(resolved)
        if len(unique_alias_ids) == 1:
            result[player_id] = next(iter(unique_alias_ids))
            raw_alias_matches += 1
            continue

        register_ids: set[str] = set()
        for name in names:
            resolved = register_names.get(normalize(name), set())
            if len(resolved) == 1:
                register_ids.update(resolved)
        if len(register_ids) == 1:
            result[player_id] = next(iter(register_ids))
            register_matches += 1

    payload = {
        "source": "Cricsheet Register and embedded match registries",
        "generated": "2026-09-08",
        "players": dict(sorted(result.items())),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "match_files_read": files_read,
        "active_players": len(players),
        "mapped_players": len(result),
        "coverage_pct": round(100 * len(result) / len(players), 2),
        "fixture_display_name_matches": fixture_matches,
        "team_context_matches": raw_team_matches,
        "raw_alias_matches": raw_alias_matches,
        "register_name_matches": register_matches,
        "output": str(OUTPUT),
    }, indent=2))


if __name__ == "__main__":
    main()
