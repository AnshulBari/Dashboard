"""
Venue API Routes
================

Endpoints for venue intelligence data.
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


@router.get("/")
async def list_venues(
    format: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    full_members_only: bool = Query(False, description="Restrict to venues recently used by ICC Full Members"),
    recent_only: bool = Query(False, description="Restrict to the recent-performance window"),
    db: Session = Depends(get_db),
):
    """List all venues with key statistics."""
    target_format, stats_filter, params = format_scope_clause("format", format)
    where_clauses = []
    if country:
        where_clauses.append("v.country = :country")
    params.update({"limit": limit, "offset": offset})
    if country:
        params["country"] = country

    if full_members_only is True:
        _, match_filter, match_params = format_scope_clause("m.format", format)
        member_filter, member_params = full_member_clause("ta.canonical_name", "tb.canonical_name")
        recent_filter = ""
        if recent_only is True:
            from datetime import date, timedelta
            recent_filter = "AND m.match_date >= :recent_cutoff"
            params["recent_cutoff"] = (date.today() - timedelta(days=548)).isoformat()
        where_clauses.append(f"""EXISTS (
            SELECT 1 FROM matches m
            JOIN teams ta ON ta.id = m.team_a_id
            JOIN teams tb ON tb.id = m.team_b_id
            WHERE m.venue_id = v.id AND {match_filter}
              AND {member_filter} {recent_filter}
        )""")
        params.update(match_params)
        params.update(member_params)

    recent_total_expression = "vs.total_matches"
    latest_match_expression = "NULL"
    if recent_only is True:
        _, recent_match_filter, recent_match_params = format_scope_clause("rm.format", format)
        recent_member_filter = ""
        if full_members_only is True:
            recent_members, recent_member_params = full_member_clause(
                "rta.canonical_name", "rtb.canonical_name"
            )
            recent_member_filter = f" AND {recent_members}"
            params.update(recent_member_params)
        from datetime import date, timedelta
        params["recent_cutoff"] = (date.today() - timedelta(days=548)).isoformat()
        params.update(recent_match_params)
        recent_activity = f"""
            SELECT COUNT(*) FROM matches rm
            JOIN teams rta ON rta.id = rm.team_a_id
            JOIN teams rtb ON rtb.id = rm.team_b_id
            WHERE rm.venue_id = v.id AND {recent_match_filter}
              AND rm.match_date >= :recent_cutoff{recent_member_filter}
        """
        where_clauses.append(f"({recent_activity}) > 0")
        recent_total_expression = f"({recent_activity})"
        latest_match_expression = f"""(
            SELECT MAX(rm.match_date) FROM matches rm
            JOIN teams rta ON rta.id = rm.team_a_id
            JOIN teams rtb ON rtb.id = rm.team_b_id
            WHERE rm.venue_id = v.id AND {recent_match_filter}
              AND rm.match_date >= :recent_cutoff{recent_member_filter}
        )"""

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    total = db.execute(
        text(f"SELECT COUNT(*) FROM venues v {where}"), params
    ).scalar() or 0

    rows = db.execute(
        text(f"""
            WITH vs AS (
                SELECT venue_id, SUM(total_matches) AS total_matches,
                    ROUND(SUM(avg_first_innings_score * total_matches) / NULLIF(SUM(total_matches), 0), 2) AS avg_first_innings_score,
                    ROUND(SUM(avg_second_innings_score * total_matches) / NULLIF(SUM(total_matches), 0), 2) AS avg_second_innings_score,
                    SUM(chasing_wins) AS chasing_wins, SUM(defending_wins) AS defending_wins,
                    ROUND(100.0 * SUM(chasing_wins) / NULLIF(SUM(chasing_wins) + SUM(defending_wins), 0), 2) AS chasing_win_pct,
                    ROUND(SUM(pace_wickets_pct * total_matches) / NULLIF(SUM(total_matches), 0), 2) AS pace_wickets_pct
                FROM venue_stats WHERE {stats_filter} GROUP BY venue_id
            )
            SELECT
                v.id, v.name, v.city, v.country, v.capacity,
                {recent_total_expression} AS total_matches,
                {latest_match_expression} AS last_match_date,
                vs.avg_first_innings_score, vs.avg_second_innings_score,
                vs.chasing_win_pct, vs.pace_wickets_pct
            FROM venues v
            LEFT JOIN vs ON v.id = vs.venue_id
            {where}
            ORDER BY last_match_date DESC NULLS LAST, total_matches DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """),
        params
    ).fetchall()

    venues = []
    for row in rows:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        venues.append(d)

    return {"venues": venues, "total": total, "limit": limit, "offset": offset, "format": target_format}


@router.get("/{venue_id}/analytics")
async def get_venue_analytics(
    venue_id: str,
    format: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get comprehensive venue analytics."""
    validate_uuid(venue_id, "venue_id")
    target_format, stats_filter, params = format_scope_clause("vs.format", format)
    params["vid"] = venue_id

    row = db.execute(
        text(f"""
            SELECT vs.venue_id, :scope AS format,
                SUM(vs.total_matches) AS total_matches,
                ROUND(SUM(vs.avg_first_innings_score * vs.total_matches) / NULLIF(SUM(vs.total_matches), 0), 2) AS avg_first_innings_score,
                ROUND(SUM(vs.avg_second_innings_score * vs.total_matches) / NULLIF(SUM(vs.total_matches), 0), 2) AS avg_second_innings_score,
                MAX(vs.highest_total) AS highest_total, MIN(vs.lowest_total) AS lowest_total,
                SUM(vs.chasing_wins) AS chasing_wins, SUM(vs.defending_wins) AS defending_wins,
                ROUND(100.0 * SUM(vs.chasing_wins) / NULLIF(SUM(vs.chasing_wins) + SUM(vs.defending_wins), 0), 2) AS chasing_win_pct,
                ROUND(100.0 * SUM(vs.defending_wins) / NULLIF(SUM(vs.chasing_wins) + SUM(vs.defending_wins), 0), 2) AS defending_win_pct,
                ROUND(SUM(vs.pace_wickets_pct * vs.total_matches) / NULLIF(SUM(vs.total_matches), 0), 2) AS pace_wickets_pct,
                ROUND(SUM(vs.spin_wickets_pct * vs.total_matches) / NULLIF(SUM(vs.total_matches), 0), 2) AS spin_wickets_pct,
                ROUND(SUM(vs.avg_powerplay_runs * vs.total_matches) / NULLIF(SUM(vs.total_matches), 0), 2) AS avg_powerplay_runs,
                ROUND(SUM(vs.avg_middle_overs_runs * vs.total_matches) / NULLIF(SUM(vs.total_matches), 0), 2) AS avg_middle_overs_runs,
                ROUND(SUM(vs.avg_death_overs_runs * vs.total_matches) / NULLIF(SUM(vs.total_matches), 0), 2) AS avg_death_overs_runs,
                ROUND(SUM(vs.avg_fours_per_match * vs.total_matches) / NULLIF(SUM(vs.total_matches), 0), 2) AS avg_fours_per_match,
                ROUND(SUM(vs.avg_sixes_per_match * vs.total_matches) / NULLIF(SUM(vs.total_matches), 0), 2) AS avg_sixes_per_match,
                ROUND(SUM(vs.boundary_frequency * vs.total_matches) / NULLIF(SUM(vs.total_matches), 0), 2) AS boundary_frequency,
                ROUND(SUM(vs.toss_bat_first_win_pct * vs.total_matches) / NULLIF(SUM(vs.total_matches), 0), 2) AS toss_bat_first_win_pct,
                ROUND(SUM(vs.toss_field_first_win_pct * vs.total_matches) / NULLIF(SUM(vs.total_matches), 0), 2) AS toss_field_first_win_pct,
                v.name, v.city, v.country
            FROM venue_stats vs
            JOIN venues v ON vs.venue_id = v.id
            WHERE vs.venue_id = :vid AND {stats_filter}
            GROUP BY vs.venue_id, v.name, v.city, v.country
        """),
        {**params, "scope": target_format}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Venue analytics not found")

    return _row_to_dict(row)
