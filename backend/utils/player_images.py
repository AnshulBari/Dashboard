"""Resolve player portraits through the official Cricsheet identity register.

The application stores Cricsheet player names but the historical database predates
the ``cricsheet_id`` column.  The register's name variants let us recover a stable
ESPNcricinfo identifier without fuzzy matching or guessing identities.
"""

from __future__ import annotations

import csv
import json
import logging
import re
import unicodedata
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

LOGGER = logging.getLogger(__name__)
REGISTER_DIR = Path(__file__).resolve().parents[2] / "data" / "reference" / "cricsheet-register"
ESPN_HEADSHOT_BASE = "https://a.espncdn.com/i/headshots/cricket/players/full"
PLAYER_IMAGE_MAP = REGISTER_DIR / "player-image-map.json"


def _normalize_name(value: str | None) -> str:
    if not value:
        return ""
    ascii_value = "".join(
        character
        for character in unicodedata.normalize("NFKD", value.replace("’", "'"))
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


@lru_cache(maxsize=1)
def _image_id_by_name() -> dict[str, str]:
    people_path = REGISTER_DIR / "people.csv"
    aliases_path = REGISTER_DIR / "names.csv"
    if not people_path.exists() or not aliases_path.exists():
        LOGGER.warning("Cricsheet register not found at %s", REGISTER_DIR)
        return {}

    identifier_to_image_id: dict[str, str] = {}
    candidates: defaultdict[str, set[str]] = defaultdict(set)

    with people_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            image_id = next(
                (row.get(column, "").strip() for column in ("key_cricinfo", "key_cricinfo_2", "key_cricinfo_3") if row.get(column, "").strip()),
                "",
            )
            identifier = row.get("identifier", "").strip()
            if not identifier or not image_id:
                continue
            identifier_to_image_id[identifier] = image_id
            for column in ("name", "unique_name"):
                normalized = _normalize_name(row.get(column))
                if normalized:
                    candidates[normalized].add(image_id)

    with aliases_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            image_id = identifier_to_image_id.get(row.get("identifier", "").strip())
            normalized = _normalize_name(row.get("name"))
            if image_id and normalized:
                candidates[normalized].add(image_id)

    # Ambiguous aliases are deliberately omitted. A missing portrait is better
    # than displaying a different player who happens to share the same name.
    return {
        normalized: next(iter(image_ids))
        for normalized, image_ids in candidates.items()
        if len(image_ids) == 1
    }


@lru_cache(maxsize=1)
def _image_id_by_player_id() -> dict[str, str]:
    if not PLAYER_IMAGE_MAP.exists():
        return {}
    try:
        payload = json.loads(PLAYER_IMAGE_MAP.read_text(encoding="utf-8"))
        players = payload.get("players", {})
        return {str(key): str(value) for key, value in players.items() if key and value}
    except (OSError, ValueError, TypeError):
        LOGGER.exception("Unable to read player image map at %s", PLAYER_IMAGE_MAP)
        return {}


def get_player_image_id(
    name: str | None,
    full_name: str | None = None,
    player_id: str | None = None,
) -> str | None:
    """Return a safely resolved ESPNcricinfo player ID, if one exists."""
    if player_id and (image_id := _image_id_by_player_id().get(str(player_id))):
        return image_id
    image_ids = _image_id_by_name()
    for candidate in (full_name, name):
        image_id = image_ids.get(_normalize_name(candidate))
        if image_id:
            return image_id
    return None


def get_player_image_url(
    name: str | None,
    full_name: str | None = None,
    player_id: str | None = None,
) -> str | None:
    """Return an ESPN player headshot URL for a register-backed identity."""
    image_id = get_player_image_id(name, full_name, player_id)
    return f"{ESPN_HEADSHOT_BASE}/{image_id}.png" if image_id else None
