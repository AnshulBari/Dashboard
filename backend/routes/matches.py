"""
Match API Routes
================

Endpoints for match data.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.utils.database import get_db
from backend.utils.validation import format_scope_clause, full_member_clause, validate_uuid

router = APIRouter()


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return dict(row._mapping)


def _attach_innings_scores(db: Session, matches: list[dict]) -> None:
    """Attach compact, correctly ordered team scorelines to match-list rows."""
    if not matches:
        return

    match_params = {
        f"score_match_{index}": str(match["id"]).replace("-", "")
        for index, match in enumerate(matches)
    }
    placeholders = ", ".join(f":{key}" for key in match_params)
    rows = db.execute(
        text(f"""
            SELECT REPLACE(CAST(i.match_id AS TEXT), '-', '') AS match_key,
                   t.canonical_name AS batting_team,
                   i.innings_number, i.total_runs, i.total_wickets
            FROM innings i
            JOIN teams t ON t.id = i.batting_team_id
            WHERE REPLACE(CAST(i.match_id AS TEXT), '-', '') IN ({placeholders})
            ORDER BY i.match_id, i.innings_number
        """),
        match_params,
    ).fetchall()

    scorelines: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        score = _row_to_dict(row)
        runs = score.get("total_runs")
        wickets = score.get("total_wickets")
        if runs is None:
            continue
        innings_score = str(runs) if wickets is None or wickets >= 10 else f"{runs}/{wickets}"
        scorelines.setdefault((score["match_key"], score["batting_team"]), []).append(innings_score)

    for match in matches:
        match_key = str(match["id"]).replace("-", "")
        match["score_team_a"] = " & ".join(scorelines.get((match_key, match.get("team_a")), [])) or None
        match["score_team_b"] = " & ".join(scorelines.get((match_key, match.get("team_b")), [])) or None


@router.get("/")
async def list_matches(
    format: Optional[str] = Query(None),
    competition: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    venue: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    full_members_only: bool = Query(False, description="Restrict to matches between ICC Full Members"),
    recent_only: bool = Query(False, description="Restrict to the recent-performance window"),
    completed_only: bool = Query(False, description="Restrict to completed matches up to today"),
    db: Session = Depends(get_db),
):
    """List matches with filtering options."""
    target_format, format_filter, params = format_scope_clause("m.format", format)

    where_clauses = [format_filter]
    params.update({"limit": limit, "offset": offset})

    if full_members_only is True:
        member_filter, member_params = full_member_clause("ta.canonical_name", "tb.canonical_name")
        where_clauses.append(member_filter)
        params.update(member_params)

    if recent_only is True:
        from datetime import date, timedelta
        where_clauses.append("m.match_date >= :recent_cutoff")
        params["recent_cutoff"] = (date.today() - timedelta(days=548)).isoformat()

    if completed_only is True:
        from datetime import date
        where_clauses.append("m.match_date <= :completed_through")
        where_clauses.append("COALESCE(m.is_live, false) = false")
        where_clauses.append("m.result_type IN ('win', 'draw', 'tie', 'no_result', 'abandoned')")
        params["completed_through"] = date.today().isoformat()

    if competition:
        where_clauses.append("c.name = :comp")
        params["comp"] = competition

    if season:
        where_clauses.append("s.name = :season")
        params["season"] = season

    if team:
        where_clauses.append(
            "(REPLACE(CAST(m.team_a_id AS TEXT), '-', '') = REPLACE(:team, '-', '') "
            "OR REPLACE(CAST(m.team_b_id AS TEXT), '-', '') = REPLACE(:team, '-', '') "
            "OR ta.canonical_name = :team OR tb.canonical_name = :team)"
        )
        params["team"] = team

    if venue:
        where_clauses.append(
            "(REPLACE(CAST(m.venue_id AS TEXT), '-', '') = REPLACE(:venue, '-', '') "
            "OR v.name = :venue)"
        )
        params["venue"] = venue

    where_sql = " AND ".join(where_clauses)

    rows = db.execute(
        text(f"""
            SELECT
                m.id, m.match_date, m.format, m.win_margin, m.win_type,
                m.result_type,
                ta.canonical_name AS team_a,
                tb.canonical_name AS team_b,
                tw.canonical_name AS winner,
                v.name AS venue,
                m.toss_decision,
                c.name AS competition_name,
                s.name AS season_name
            FROM matches m
            LEFT JOIN teams ta ON m.team_a_id = ta.id
            LEFT JOIN teams tb ON m.team_b_id = tb.id
            LEFT JOIN teams tw ON m.winner_id = tw.id
            LEFT JOIN venues v ON m.venue_id = v.id
            LEFT JOIN competitions c ON m.competition_id = c.id
            LEFT JOIN seasons s ON m.season_id = s.id
            WHERE {where_sql}
            ORDER BY m.match_date DESC
            LIMIT :limit OFFSET :offset
        """),
        params
    ).fetchall()

    matches = []
    for row in rows:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        # Build result string
        result_type = d.get("result_type", "win")
        if result_type == "draw":
            d["result"] = "Draw"
        elif result_type == "tie":
            d["result"] = "Tie"
        elif result_type == "no_result":
            d["result"] = "No result"
        elif result_type == "abandoned":
            d["result"] = "Abandoned"
        elif d.get("winner"):
            margin_str = (
                f" by {d['win_margin']} {d['win_type']}"
                if d.get("win_margin") is not None and d.get("win_type")
                else ""
            )
            d["result"] = f"{d['winner']} won{margin_str}"
        else:
            d["result"] = "No result"
        matches.append(d)

    _attach_innings_scores(db, matches)

    # Count total
    count_sql = f"""
        SELECT COUNT(*) FROM matches m
        LEFT JOIN teams ta ON m.team_a_id = ta.id
        LEFT JOIN teams tb ON m.team_b_id = tb.id
        LEFT JOIN venues v ON m.venue_id = v.id
        LEFT JOIN competitions c ON m.competition_id = c.id
        LEFT JOIN seasons s ON m.season_id = s.id
        WHERE {where_sql}
    """
    count_params = {k: v for k, v in params.items() if k not in {"limit", "offset"}}
    total = db.execute(text(count_sql), count_params).scalar() or 0

    return {
        "matches": matches,
        "total": total,
        "format": target_format,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{match_id}")
async def get_match(match_id: str, db: Session = Depends(get_db)):
    """Get detailed match information."""
    validate_uuid(match_id, "match_id")
    row = db.execute(
        text("""
            SELECT
                m.id, m.match_date, m.format, m.win_margin, m.win_type,
                m.toss_decision, m.result_type,
                ta.canonical_name AS team_a,
                tb.canonical_name AS team_b,
                tw.canonical_name AS winner,
                v.name AS venue,
                c.name AS competition_name,
                s.name AS season_name
            FROM matches m
            LEFT JOIN teams ta ON m.team_a_id = ta.id
            LEFT JOIN teams tb ON m.team_b_id = tb.id
            LEFT JOIN teams tw ON m.winner_id = tw.id
            LEFT JOIN venues v ON m.venue_id = v.id
            LEFT JOIN competitions c ON m.competition_id = c.id
            LEFT JOIN seasons s ON m.season_id = s.id
            WHERE m.id = :mid
        """),
        {"mid": match_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Match not found")

    d = _row_to_dict(row)
    d["id"] = str(d["id"])
    if d.get("result_type") == "draw":
        d["result"] = "Draw"
    elif d.get("result_type") == "tie":
        d["result"] = "Tie"
    elif d.get("result_type") in {"no_result", "abandoned"}:
        d["result"] = "No result" if d["result_type"] == "no_result" else "Abandoned"
    elif d.get("winner"):
        margin = (
            f" by {d['win_margin']} {d['win_type']}"
            if d.get("win_margin") is not None and d.get("win_type")
            else ""
        )
        d["result"] = f"{d['winner']} won{margin}"
    else:
        d["result"] = "No result"

    return d
