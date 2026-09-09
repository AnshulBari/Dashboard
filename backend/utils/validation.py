"""
Input Validation Utilities
==========================

Shared validation functions for API endpoint parameters.
"""

from fastapi import HTTPException

# Allowed format values
VALID_FORMATS = {"T20", "T20I", "ODI", "Test"}
INTERNATIONAL_FORMATS = ("T20I", "ODI", "Test")
DEFAULT_FORMAT_SCOPE = "International"
FULL_MEMBER_TEAMS = (
    "Afghanistan", "Australia", "Bangladesh", "England", "India", "Ireland",
    "New Zealand", "Pakistan", "South Africa", "Sri Lanka", "West Indies", "Zimbabwe",
)

# Allowed sort columns (whitelisted to prevent SQL injection)
PLAYER_SORT_COLUMNS = {
    "impact_score": "pf.impact_score",
    "name": "p.canonical_name",
    "runs": "pbs.runs",
    "wickets": "pws.wickets",
    "batting_average": "pbs.batting_average",
    "strike_rate": "pbs.strike_rate",
    # Public response names retained as aliases for API clients.
    "career_runs": "pbs.runs",
    "career_wickets": "pws.wickets",
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


def validate_format_scope(fmt: str | None) -> str:
    """Validate a single format or the aggregate international scope."""
    if fmt is None or fmt.strip().lower() in {"international", "intl"}:
        return DEFAULT_FORMAT_SCOPE
    return validate_format(fmt)


def format_scope_clause(column: str, fmt: str | None) -> tuple[str, str, dict]:
    """Return a safe SQL predicate and parameters for a format selection.

    The default deliberately excludes domestic T20 competitions such as the IPL.
    ``column`` is supplied only by route code, never by an API caller.
    """
    scope = validate_format_scope(fmt)
    if scope == DEFAULT_FORMAT_SCOPE:
        return scope, f"{column} IN (:fmt_t20i, :fmt_odi, :fmt_test)", {
            "fmt_t20i": "T20I",
            "fmt_odi": "ODI",
            "fmt_test": "Test",
        }
    return scope, f"{column} = :fmt", {"fmt": scope}


def full_member_clause(*columns: str) -> tuple[str, dict]:
    """Return a parameterized predicate restricting team-name columns."""
    placeholders = ", ".join(f":full_member_{index}" for index in range(len(FULL_MEMBER_TEAMS)))
    params = {
        f"full_member_{index}": team
        for index, team in enumerate(FULL_MEMBER_TEAMS)
    }
    return " AND ".join(f"{column} IN ({placeholders})" for column in columns), params


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
