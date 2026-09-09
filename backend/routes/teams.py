"""
Team API Routes
===============

Endpoints for team intelligence data.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.utils.database import get_db
from backend.utils.validation import (
    TEAM_SORT_COLUMNS,
    full_member_clause,
    format_scope_clause,
    validate_sort_column,
    validate_sort_order,
    validate_uuid,
)

router = APIRouter()


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return dict(row._mapping)


@router.get("/")
async def list_teams(
    format: Optional[str] = Query(None),
    sort_by: str = Query("overall_strength", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    full_members_only: bool = Query(False, description="Restrict to the 12 ICC Full Members"),
    recent_only: bool = Query(False, description="Use results from the recent-performance window"),
    db: Session = Depends(get_db),
):
    """List all teams with strength ratings."""
    target_format, performance_filter, params = format_scope_clause("format", format)
    sort_column = validate_sort_column(sort_by, TEAM_SORT_COLUMNS, "overall_strength")
    order = validate_sort_order(sort_order)

    team_where = "t.is_active = true"
    if full_members_only is True:
        member_filter, member_params = full_member_clause("t.canonical_name")
        team_where += f" AND {member_filter}"
        params.update(member_params)

    total = db.execute(
        text(f"SELECT COUNT(*) FROM teams t WHERE {team_where}"), params
    ).scalar() or 0

    if recent_only is True:
        _, recent_format_filter, recent_params = format_scope_clause("m.format", format)
        params.update(recent_params)
        params["recent_cutoff"] = (date.today() - timedelta(days=548)).isoformat()
        match_member_filter = ""
        if full_members_only is True:
            match_members, match_member_params = full_member_clause(
                "ta.canonical_name", "tb.canonical_name"
            )
            match_member_filter = f" AND {match_members}"
            params.update(match_member_params)

        rows = db.execute(
            text(f"""
                WITH eligible_matches AS (
                    SELECT m.id, m.team_a_id, m.team_b_id, m.winner_id, m.result_type
                    FROM matches m
                    JOIN teams ta ON ta.id = m.team_a_id
                    JOIN teams tb ON tb.id = m.team_b_id
                    WHERE {recent_format_filter}
                      AND m.match_date >= :recent_cutoff{match_member_filter}
                ), team_matches AS (
                    SELECT id, team_a_id AS team_id, winner_id, result_type FROM eligible_matches
                    UNION ALL
                    SELECT id, team_b_id AS team_id, winner_id, result_type FROM eligible_matches
                ), tp AS (
                    SELECT team_id, COUNT(*) AS matches,
                           SUM(CASE WHEN winner_id = team_id THEN 1 ELSE 0 END) AS wins,
                           SUM(CASE WHEN winner_id IS NOT NULL AND winner_id != team_id
                                     AND result_type = 'win' THEN 1 ELSE 0 END) AS losses,
                           ROUND(100.0 * SUM(CASE WHEN winner_id = team_id THEN 1 ELSE 0 END)
                                 / NULLIF(COUNT(*), 0), 2) AS win_rate
                    FROM team_matches GROUP BY team_id
                )
                SELECT t.id, t.canonical_name AS name, t.short_name, t.country,
                       tp.matches, tp.wins, tp.losses, tp.win_rate,
                       NULL AS batting_strength_score, NULL AS bowling_strength_score,
                       tp.win_rate AS overall_strength_score,
                       NULL AS avg_first_innings_score, NULL AS avg_second_innings_score,
                       NULL AS avg_economy, NULL AS chasing_win_pct, NULL AS defending_win_pct
                FROM teams t
                LEFT JOIN tp ON t.id = tp.team_id
                WHERE {team_where}
                ORDER BY tp.win_rate DESC, tp.matches DESC, t.canonical_name
                LIMIT :limit OFFSET :offset
            """),
            {**params, "limit": limit, "offset": offset},
        ).fetchall()

        teams = []
        for row in rows:
            item = _row_to_dict(row)
            item["id"] = str(item["id"])
            teams.append(item)
        return {
            "teams": teams, "total": total, "limit": limit,
            "offset": offset, "format": target_format,
        }

    rows = db.execute(
        text(f"""
            WITH tp AS (
                SELECT team_id, SUM(matches) AS matches, SUM(wins) AS wins,
                    SUM(losses) AS losses,
                    ROUND(100.0 * SUM(wins) / NULLIF(SUM(matches), 0), 2) AS win_rate,
                    ROUND(SUM(avg_first_innings_score * matches) / NULLIF(SUM(matches), 0), 2) AS avg_first_innings_score,
                    ROUND(SUM(avg_second_innings_score * matches) / NULLIF(SUM(matches), 0), 2) AS avg_second_innings_score,
                    ROUND(SUM(avg_economy * matches) / NULLIF(SUM(matches), 0), 2) AS avg_economy,
                    ROUND(SUM(chasing_win_pct * matches) / NULLIF(SUM(matches), 0), 2) AS chasing_win_pct,
                    ROUND(SUM(defending_win_pct * matches) / NULLIF(SUM(matches), 0), 2) AS defending_win_pct,
                    ROUND(SUM(batting_strength_score * matches) / NULLIF(SUM(matches), 0), 2) AS batting_strength_score,
                    ROUND(SUM(bowling_strength_score * matches) / NULLIF(SUM(matches), 0), 2) AS bowling_strength_score,
                    ROUND(SUM(overall_strength_score * matches) / NULLIF(SUM(matches), 0), 2) AS overall_strength_score
                FROM team_performance
                WHERE {performance_filter} AND period = 'career'
                GROUP BY team_id
            )
            SELECT
                t.id, t.canonical_name AS name, t.short_name, t.country,
                tp.matches, tp.wins, tp.losses, tp.win_rate,
                tp.batting_strength_score, tp.bowling_strength_score, tp.overall_strength_score,
                tp.avg_first_innings_score, tp.avg_second_innings_score,
                tp.avg_economy, tp.chasing_win_pct, tp.defending_win_pct
            FROM teams t
            LEFT JOIN tp ON t.id = tp.team_id
            WHERE {team_where}
            ORDER BY {sort_column} {order} NULLS LAST
            LIMIT :limit OFFSET :offset
        """.format(sort_column=sort_column, order=order)),
        {**params, "limit": limit, "offset": offset}
    ).fetchall()

    teams = []
    for row in rows:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        teams.append(d)

    return {"teams": teams, "total": total, "limit": limit, "offset": offset, "format": target_format}


@router.get("/{team_id}")
async def get_team(team_id: str, format: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get detailed team information and analytics."""
    validate_uuid(team_id, "team_id")
    target_format, performance_filter, params = format_scope_clause("format", format)
    params["tid"] = team_id
    row = db.execute(
        text(f"""
            WITH tp AS (
                SELECT team_id, SUM(matches) AS matches, SUM(wins) AS wins, SUM(losses) AS losses,
                    ROUND(100.0 * SUM(wins) / NULLIF(SUM(matches), 0), 2) AS win_rate,
                    ROUND(SUM(batting_strength_score * matches) / NULLIF(SUM(matches), 0), 2) AS batting_strength_score,
                    ROUND(SUM(bowling_strength_score * matches) / NULLIF(SUM(matches), 0), 2) AS bowling_strength_score,
                    ROUND(SUM(overall_strength_score * matches) / NULLIF(SUM(matches), 0), 2) AS overall_strength_score
                FROM team_performance WHERE {performance_filter} AND period = 'career' GROUP BY team_id
            )
            SELECT
                t.id, t.canonical_name AS name, t.short_name, t.country,
                tp.matches, tp.wins, tp.losses, tp.win_rate,
                tp.batting_strength_score, tp.bowling_strength_score, tp.overall_strength_score
            FROM teams t
            LEFT JOIN tp ON t.id = tp.team_id
            WHERE t.id = :tid
        """),
        params
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Team not found")

    d = _row_to_dict(row)
    d["id"] = str(d["id"])
    d["format"] = target_format
    return d


@router.get("/{team_id}/analytics")
async def get_team_analytics(
    team_id: str,
    format: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get comprehensive team analytics."""
    validate_uuid(team_id, "team_id")
    target_format, performance_filter, params = format_scope_clause("format", format)
    target_period = period or "career"
    params.update({"tid": team_id, "period": target_period})

    row = db.execute(
        text(f"""
            SELECT team_id, :scope AS format, :period AS period,
                SUM(matches) AS matches, SUM(wins) AS wins, SUM(losses) AS losses,
                ROUND(100.0 * SUM(wins) / NULLIF(SUM(matches), 0), 2) AS win_rate,
                ROUND(SUM(avg_first_innings_score * matches) / NULLIF(SUM(matches), 0), 2) AS avg_first_innings_score,
                ROUND(SUM(avg_second_innings_score * matches) / NULLIF(SUM(matches), 0), 2) AS avg_second_innings_score,
                ROUND(SUM(avg_powerplay_score * matches) / NULLIF(SUM(matches), 0), 2) AS avg_powerplay_score,
                ROUND(SUM(avg_middle_overs_score * matches) / NULLIF(SUM(matches), 0), 2) AS avg_middle_overs_score,
                ROUND(SUM(avg_death_overs_score * matches) / NULLIF(SUM(matches), 0), 2) AS avg_death_overs_score,
                ROUND(SUM(avg_total_score * matches) / NULLIF(SUM(matches), 0), 2) AS avg_total_score,
                ROUND(SUM(avg_economy * matches) / NULLIF(SUM(matches), 0), 2) AS avg_economy,
                ROUND(SUM(chasing_win_pct * matches) / NULLIF(SUM(matches), 0), 2) AS chasing_win_pct,
                ROUND(SUM(defending_win_pct * matches) / NULLIF(SUM(matches), 0), 2) AS defending_win_pct,
                ROUND(SUM(batting_strength_score * matches) / NULLIF(SUM(matches), 0), 2) AS batting_strength_score,
                ROUND(SUM(bowling_strength_score * matches) / NULLIF(SUM(matches), 0), 2) AS bowling_strength_score,
                ROUND(SUM(overall_strength_score * matches) / NULLIF(SUM(matches), 0), 2) AS overall_strength_score
            FROM team_performance
            WHERE team_id = :tid AND {performance_filter} AND period = :period
            GROUP BY team_id
        """),
        {**params, "scope": target_format}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Team analytics not found")

    return _row_to_dict(row)
