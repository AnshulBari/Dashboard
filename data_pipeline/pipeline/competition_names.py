"""Canonical names for competitions whose source labels changed over time."""

from __future__ import annotations


COMPETITION_NAME_ALIASES = {
    "icc world cup": "ICC Cricket World Cup",
    "world cup": "ICC Cricket World Cup",
}


def canonical_competition_name(name: str | None) -> str:
    """Return a stable competition name for ingestion and lookup."""
    value = " ".join(str(name or "").strip().split())
    return COMPETITION_NAME_ALIASES.get(value.casefold(), value)
