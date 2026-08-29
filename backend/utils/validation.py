"""
Input Validation Utilities
==========================

Shared validation functions for API endpoint parameters.
"""

from fastapi import HTTPException

# Allowed format values
VALID_FORMATS = {"T20", "T20I", "ODI", "Test"}

# Allowed sort columns (whitelisted to prevent SQL injection)
PLAYER_SORT_COLUMNS = {
    "form_score": "pf.form_score",
    "name": "p.canonical_name",
    "runs": "pbs.runs",
    "wickets": "pws.wickets",
    "batting_average": "pbs.batting_average",
}

TEAM_SORT_COLUMNS = {
    "overall_strength": "tp.overall_strength_score",
    "matches": "tp.matches",
    "wins": "tp.wins",
    "win_rate": "tp.win_rate",
}

# Allowed categories for rankings
VALID_RANKING_CATEGORIES = {"batting", "bowling", "allrounder"}


def validate_format(fmt: str) -> str:
    """Validate and return a format string. Raises 400 if invalid."""
    if fmt not in VALID_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format '{fmt}'. Must be one of: {', '.join(sorted(VALID_FORMATS))}",
        )
    return fmt


def validate_uuid(value: str, field_name: str = "ID") -> str:
    """Validate that a string is a valid UUID. Raises 400 if not."""
    try:
        from uuid import UUID
        UUID(value)
        return value
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name} format: '{value}'",
        )


def validate_sort_column(value: str, allowed: dict, default: str) -> str:
    """Validate sort column against a whitelist. Returns the SQL column expression."""
    return allowed.get(value, allowed.get(default))


def validate_sort_order(value: str) -> str:
    """Validate sort order. Returns 'ASC' or 'DESC'."""
    if value.lower() in ("asc", "desc"):
        return value.upper()
    return "DESC"


def validate_page_params(page: int, page_size: int) -> tuple[int, int]:
    """Validate and normalize page parameters. Returns (offset, limit)."""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 25
    if page_size > 200:
        page_size = 200
    offset = (page - 1) * page_size
    return offset, page_size
