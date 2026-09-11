"""
Player API Routes
=================

Endpoints for player intelligence data.
Queries the database for precomputed analytical results.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from datetime import date, timedelta
import math
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.utils.database import get_db
from backend.utils.player_images import get_player_image_url
from backend.utils.stat_invariants import safe_not_outs_sql, sanitize_stat_record
from backend.utils.validation import (
    PLAYER_SORT_COLUMNS,
    full_member_clause,
    format_scope_clause,
    validate_sort_column,
    validate_sort_order,
    validate_uuid,
)

router = APIRouter()


def _row_to_dict(row) -> dict:
    """Convert a SQLAlchemy Row to a dict."""
    if row is None:
        return None
    return sanitize_stat_record(dict(row._mapping))


SAFE_NOT_OUTS_SQL = safe_not_outs_sql()


def _percentile_scores(rows: list[dict], key: str, valid, invert: bool = False) -> dict[str, float]:
    """Return tie-aware percentile ranks keyed by player ID."""
    eligible = [row for row in rows if valid(row) and row.get(key) is not None]
    values = sorted(float(row[key]) for row in eligible)
    if not values:
        return {}
    scores = {}
    for row in eligible:
        value = float(row[key])
        first = values.index(value) + 1
        last = len(values) - values[::-1].index(value)
        rank = (first + last) / 2
        percentile = rank / len(values) * 100.0
        scores[str(row["id"])] = 100.0 - percentile + (100.0 / len(values)) if invert else percentile
    return scores


def _season_impact_scores(rows: list[dict]) -> None:
    """Calculate role-aware impact entirely within one competition edition."""
    bat_valid = lambda row: int(row.get("batting_innings") or 0) >= 3
    bowl_valid = lambda row: int(row.get("bowling_innings") or 0) >= 3 and int(row.get("balls_bowled") or 0) > 0
    bat_average = _percentile_scores(rows, "batting_average", bat_valid)
    bat_strike = _percentile_scores(rows, "strike_rate", bat_valid)
    bat_volume_rows = [{**row, "run_volume": math.log1p(int(row.get("career_runs") or 0))} for row in rows]
    bat_volume = _percentile_scores(bat_volume_rows, "run_volume", bat_valid)
    wicket_rate_rows = [{
        **row,
        "wickets_per_innings": (
            int(row.get("career_wickets") or 0) / int(row.get("bowling_innings") or 1)
        ),
        "wicket_volume": math.log1p(int(row.get("career_wickets") or 0)),
    } for row in rows]
    wicket_rate = _percentile_scores(wicket_rate_rows, "wickets_per_innings", bowl_valid)
    bowl_economy = _percentile_scores(rows, "economy", bowl_valid, invert=True)
    wicket_volume = _percentile_scores(wicket_rate_rows, "wicket_volume", bowl_valid)

    for row in rows:
        player_id = str(row["id"])
        batting = None
        if player_id in bat_average:
            raw = bat_average[player_id] * .45 + bat_strike[player_id] * .25 + bat_volume[player_id] * .30
            innings = int(row.get("batting_innings") or 0)
            batting = 50 + (raw - 50) * innings / (innings + 8)
        bowling = None
        if player_id in wicket_rate:
            raw = wicket_rate[player_id] * .45 + bowl_economy[player_id] * .25 + wicket_volume[player_id] * .30
            innings = int(row.get("bowling_innings") or 0)
            bowling = 50 + (raw - 50) * innings / (innings + 8)
        if batting is not None and bowling is not None:
            impact = max(batting, bowling) * .75 + min(batting, bowling) * .25
        else:
            impact = batting if batting is not None else bowling
        row["impact_score"] = round(max(0.0, min(100.0, impact)), 2) if impact is not None else None


def _competition_season_players(
    db: Session, competition: str, season: str | None, sort_by: str,
    sort_order: str, limit: int, offset: int,
) -> dict:
    competition_value = "Indian Premier League" if competition.strip().casefold() == "ipl" else competition.strip()
    params = {"competition": competition_value}
    season_filter = ""
    if season and season.strip().casefold() != "latest":
        params["season"] = season.strip()
        season_filter = "AND (CAST(s.id AS TEXT) = :season OR s.name = :season)"
    selected = db.execute(text(f"""
        SELECT s.id, s.name, s.start_date, s.end_date,
               c.id AS competition_id, c.name AS competition_name,
               COUNT(m.id) AS matches, MAX(m.match_date) AS last_match_date
        FROM seasons s
        JOIN competitions c ON c.id = s.competition_id
        LEFT JOIN matches m ON m.season_id = s.id
        WHERE (LOWER(c.name) = LOWER(:competition) OR CAST(c.id AS TEXT) = :competition)
          {season_filter}
        GROUP BY s.id, s.name, s.start_date, s.end_date, c.id, c.name
        HAVING COUNT(m.id) > 0
        ORDER BY MAX(m.match_date) DESC, s.end_date DESC, s.start_date DESC, s.name DESC
        LIMIT 1
    """), params).fetchone()
    if not selected:
        raise HTTPException(status_code=404, detail="Competition season not found")

    rows = db.execute(text("""
        WITH appearances AS (
            SELECT b.player_id, b.batting_team_id AS team_id, b.match_id, m.match_date
            FROM match_batting_summary b JOIN matches m ON m.id = b.match_id
            WHERE m.season_id = :season_id
            UNION
            SELECT b.player_id, b.bowling_team_id AS team_id, b.match_id, m.match_date
            FROM match_bowling_summary b JOIN matches m ON m.id = b.match_id
            WHERE m.season_id = :season_id
        ), team_activity AS (
            SELECT player_id, team_id, COUNT(DISTINCT match_id) AS matches,
                   MAX(match_date) AS last_match_date
            FROM appearances GROUP BY player_id, team_id
        ), ranked_team AS (
            SELECT player_id, team_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY player_id
                       ORDER BY matches DESC, last_match_date DESC, team_id
                   ) AS team_rank
            FROM team_activity
        )
        SELECT p.id, p.canonical_name AS name, p.full_name, p.role, p.country,
               t.canonical_name AS team_name,
               sp.matches, sp.batting_innings, sp.bowling_innings,
               sp.runs AS career_runs, sp.wickets AS career_wickets,
               ROUND(1.0 * sp.runs / NULLIF(sp.batting_innings - sp.not_outs, 0), 2) AS batting_average,
               ROUND(100.0 * sp.runs / NULLIF(sp.balls_faced, 0), 2) AS strike_rate,
               ROUND(6.0 * sp.runs_conceded / NULLIF(sp.balls_bowled, 0), 2) AS economy,
               sp.balls_bowled
        FROM season_player_stats sp
        JOIN players p ON p.id = sp.player_id
        LEFT JOIN ranked_team rt ON rt.player_id = sp.player_id AND rt.team_rank = 1
        LEFT JOIN teams t ON t.id = rt.team_id
        WHERE sp.season_id = :season_id
          AND (sp.batting_innings > 0 OR sp.bowling_innings > 0)
    """), {"season_id": str(selected.id)}).fetchall()
    players = [sanitize_stat_record(dict(row._mapping)) for row in rows]
    for player in players:
        player["id"] = str(player["id"])
    _season_impact_scores(players)

    sort_keys = {
        "impact_score": "impact_score", "name": "name", "runs": "career_runs",
        "career_runs": "career_runs", "wickets": "career_wickets",
        "career_wickets": "career_wickets", "batting_average": "batting_average",
        "strike_rate": "strike_rate",
    }
    sort_key = sort_keys.get(sort_by, "impact_score")
    descending = validate_sort_order(sort_order) == "DESC"
    players.sort(
        key=lambda row: (row.get(sort_key) is not None, row.get(sort_key) or 0),
        reverse=descending,
    )
    total = len(players)
    players = players[offset:offset + limit]
    for player in players:
        player["image_url"] = get_player_image_url(
            player.get("name"), player.get("full_name"), player["id"]
        )
        for internal in ("matches", "batting_innings", "bowling_innings", "economy", "balls_bowled"):
            player.pop(internal, None)

    season_data = dict(selected._mapping)
    for key in ("id", "competition_id"):
        season_data[key] = str(season_data[key])
    return {
        "players": players, "total": total, "limit": limit, "offset": offset,
        "format": "T20", "competition": {
            "id": season_data.pop("competition_id"),
            "name": season_data.pop("competition_name"),
        }, "season": season_data,
    }


def _player_display_team(db: Session, player_id: str, scope: str, fallback: str | None) -> str | None:
    """Choose a national team for international views and a franchise for T20.

    ``players.team_id`` is only a canonical fallback: historical ingestion can
    encounter a short-lived franchise first. Affiliations and match activity
    provide the format-aware answer shown on the profile.
    """
    if scope == "T20":
        row = db.execute(
            text("""
                WITH appearances AS (
                    SELECT i.batting_team_id AS team_id, d.match_id
                    FROM deliveries d
                    JOIN innings i ON i.id = d.innings_id
                    WHERE d.striker_id = :pid OR d.non_striker_id = :pid
                       OR d.dismissed_player_id = :pid
                    UNION
                    SELECT i.bowling_team_id AS team_id, d.match_id
                    FROM deliveries d
                    JOIN innings i ON i.id = d.innings_id
                    WHERE d.bowler_id = :pid OR d.fielder_id = :pid
                ),
                activity AS (
                    SELECT a.team_id, COUNT(DISTINCT a.match_id) AS match_count,
                           MAX(m.match_date) AS last_match
                    FROM appearances a
                    JOIN matches m ON m.id = a.match_id
                    WHERE m.format = 'T20'
                    GROUP BY a.team_id
                )
                SELECT t.canonical_name
                FROM player_team_affiliations pta
                JOIN teams t ON t.id = pta.team_id
                LEFT JOIN activity ON activity.team_id = pta.team_id
                WHERE pta.player_id = :pid AND pta.format = 'T20'
                ORDER BY CASE WHEN activity.last_match IS NULL THEN 1 ELSE 0 END,
                         activity.last_match DESC, activity.match_count DESC,
                         t.canonical_name
                LIMIT 1
            """),
            {"pid": player_id},
        ).fetchone()
    else:
        row = db.execute(
            text("""
                SELECT t.canonical_name,
                       COUNT(DISTINCT pta.format) AS format_count,
                       SUM(CASE WHEN pta.format = :scope THEN 1 ELSE 0 END) AS exact_scope
                FROM player_team_affiliations pta
                JOIN teams t ON t.id = pta.team_id
                WHERE pta.player_id = :pid
                  AND pta.format IN ('T20I', 'ODI', 'Test')
                GROUP BY t.id, t.canonical_name
                ORDER BY exact_scope DESC, format_count DESC, t.canonical_name
                LIMIT 1
            """),
            {"pid": player_id, "scope": scope},
        ).fetchone()

    return row[0] if row else fallback


@router.get("/")
async def list_players(
    format: Optional[str] = Query(None, description="Filter by format (T20I, ODI, Test)"),
    role: Optional[str] = Query(None, description="Filter by role"),
    country: Optional[str] = Query(None, description="Filter by country"),
    search: Optional[str] = Query(
        None,
        min_length=1,
        max_length=100,
        description="Search canonical or full player name",
    ),
    sort_by: str = Query("impact_score", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    full_members_only: bool = Query(False, description="Restrict to the 12 ICC Full Members"),
    recent_only: bool = Query(False, description="Require activity during the recent-performance window"),
    competition: Optional[str] = Query(None, description="Competition name or ID"),
    season: Optional[str] = Query(None, description="Season name, ID, or latest"),
    db: Session = Depends(get_db),
):
    """
    List players with optional filtering and sorting.

    Returns player summary including Impact Score and batting/bowling stats.
    """
    if isinstance(competition, str) and competition.strip():
        return _competition_season_players(
            db, competition, season if isinstance(season, str) else None,
            sort_by, sort_order, limit, offset,
        )

    target_format, batting_filter, params = format_scope_clause("format", format)
    _, bowling_filter, bowling_params = format_scope_clause("format", format)
    _, form_filter, form_params = format_scope_clause("format", format)
    params.update(bowling_params)
    params.update(form_params)

    recent_activity_having = ""
    if recent_only is True:
        params["recent_cutoff"] = (date.today() - timedelta(days=548)).isoformat()
        # Eligibility is recent, but the displayed International Impact Score
        # must use the same complete format scope as the player profile.
        recent_activity_having = " HAVING MAX(last_match_date) >= :recent_cutoff"

    weighted_impact = (
        "SUM(form_score * COALESCE(NULLIF(recent_innings_count, 0), 1)) / "
        "NULLIF(SUM(COALESCE(NULLIF(recent_innings_count, 0), 1)), 0)"
    )
    impact_score_expression = f"ROUND({weighted_impact}, 2)"

    if recent_only is True:
        batting_summary = f"""
            SELECT player_id, SUM(matches) AS matches,
                   SUM(batting_innings) AS innings, SUM(runs) AS runs,
                   SUM(balls_faced) AS balls_faced, 0 AS not_outs,
                   ROUND(1.0 * SUM(runs) / NULLIF(SUM(batting_innings), 0), 2) AS batting_average,
                   ROUND(100.0 * SUM(runs) / NULLIF(SUM(balls_faced), 0), 2) AS strike_rate
            FROM player_recent_stats WHERE {batting_filter} GROUP BY player_id
        """
        bowling_summary = f"""
            SELECT player_id, SUM(matches) AS matches,
                   SUM(bowling_innings) AS innings, SUM(wickets) AS wickets,
                   SUM(balls_bowled) AS balls_bowled, SUM(runs_conceded) AS runs_conceded,
                   ROUND(1.0 * SUM(runs_conceded) / NULLIF(SUM(wickets), 0), 2) AS bowling_average,
                   ROUND(1.0 * SUM(balls_bowled) / NULLIF(SUM(wickets), 0), 2) AS strike_rate,
                   ROUND(6.0 * SUM(runs_conceded) / NULLIF(SUM(balls_bowled), 0), 2) AS economy
            FROM player_recent_stats WHERE {bowling_filter} GROUP BY player_id
        """
    else:
        batting_summary = f"""
            SELECT player_id, SUM(matches) AS matches, SUM(innings) AS innings,
                   SUM(runs) AS runs, SUM(balls_faced) AS balls_faced,
                   {SAFE_NOT_OUTS_SQL} AS not_outs,
                   ROUND(1.0 * SUM(runs) / NULLIF(SUM(innings) - ({SAFE_NOT_OUTS_SQL}), 0), 2) AS batting_average,
                   ROUND(100.0 * SUM(runs) / NULLIF(SUM(balls_faced), 0), 2) AS strike_rate
            FROM player_batting_stats
            WHERE {batting_filter} AND period = 'career' GROUP BY player_id
        """
        bowling_summary = f"""
            SELECT player_id, SUM(matches) AS matches, SUM(innings) AS innings,
                   SUM(wickets) AS wickets, SUM(balls_bowled) AS balls_bowled,
                   SUM(runs_conceded) AS runs_conceded,
                   ROUND(1.0 * SUM(runs_conceded) / NULLIF(SUM(wickets), 0), 2) AS bowling_average,
                   ROUND(1.0 * SUM(balls_bowled) / NULLIF(SUM(wickets), 0), 2) AS strike_rate,
                   ROUND(6.0 * SUM(runs_conceded) / NULLIF(SUM(balls_bowled), 0), 2) AS economy
            FROM player_bowling_stats
            WHERE {bowling_filter} AND period = 'career' GROUP BY player_id
        """

    # Build query with either recent-window or career summaries.
    query = text(f"""
        WITH pbs AS ({batting_summary}),
        pws AS ({bowling_summary}),
        pf AS (
            SELECT player_id,
                   {impact_score_expression} AS impact_score
                   , MAX(last_match_date) AS last_match_date
                   , SUM(COALESCE(recent_innings_count, 0)) AS recent_innings_count
            FROM player_form
            WHERE {form_filter}
            GROUP BY player_id{recent_activity_having}
        )
        SELECT
            p.id,
            p.canonical_name AS name,
            p.full_name,
            p.role,
            p.country,
            t.canonical_name AS team_name,
            pf.impact_score,
            pbs.batting_average,
            pbs.strike_rate,
            pbs.runs AS career_runs,
            pws.wickets AS career_wickets
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        LEFT JOIN pf ON p.id = pf.player_id
        LEFT JOIN pbs ON p.id = pbs.player_id
        LEFT JOIN pws ON p.id = pws.player_id
        WHERE p.is_active = true
          AND (pbs.player_id IS NOT NULL OR pws.player_id IS NOT NULL)
    """)

    if full_members_only is True:
        member_filter, member_params = full_member_clause("t.canonical_name")
        query = text(str(query) + f" AND {member_filter}")
        params.update(member_params)

    if recent_only is True:
        query = text(
            str(query)
            + " AND pf.recent_innings_count >= 3"
        )

    if role:
        query = text(str(query) + " AND p.role = :role")
        params["role"] = role

    if country:
        query = text(str(query) + " AND p.country = :country")
        params["country"] = country

    search_term = search.strip().lower() if isinstance(search, str) else ""
    if search_term:
        query = text(
            str(query)
            + """ AND (
                LOWER(p.canonical_name) LIKE :search
                OR LOWER(COALESCE(p.full_name, '')) LIKE :search
                OR EXISTS (
                    SELECT 1
                    FROM player_name_mappings pnm
                    WHERE pnm.player_id = p.id
                      AND LOWER(pnm.name_variant) LIKE :search
                )
            )"""
        )
        params["search"] = f"%{search_term}%"

    # Count total
    count_query = text(f"SELECT COUNT(*) FROM ({str(query)}) sub")
    total = db.execute(count_query, params).scalar() or 0

    # Sort (whitelisted columns only)
    sort_column = validate_sort_column(sort_by, PLAYER_SORT_COLUMNS, "impact_score")
    order = validate_sort_order(sort_order)
    query = text(str(query) + f" ORDER BY {sort_column} {order} NULLS LAST")
    query = text(str(query) + " LIMIT :limit OFFSET :offset")
    params["limit"] = limit
    params["offset"] = offset

    rows = db.execute(query, params).fetchall()

    players = []
    for row in rows:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        d["image_url"] = get_player_image_url(d.get("name"), d.get("full_name"), d.get("id"))
        players.append(d)

    return {
        "players": players,
        "total": total,
        "format": target_format,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{player_id}")
async def get_player(player_id: str, format: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """
    Get detailed player information.
    """
    validate_uuid(player_id, "player_id")

    target_format, batting_filter, params = format_scope_clause("format", format)
    _, bowling_filter, bowling_params = format_scope_clause("format", format)
    _, form_filter, form_params = format_scope_clause("format", format)
    params.update(bowling_params)
    params.update(form_params)
    params["pid"] = player_id

    row = db.execute(
        text(f"""
            WITH pbs AS (
                SELECT player_id,
                    SUM(matches) AS matches, SUM(innings) AS innings, {SAFE_NOT_OUTS_SQL} AS not_outs,
                    SUM(runs) AS runs, MAX(highest_score) AS highest_score,
                    ROUND(1.0 * SUM(runs) / NULLIF(SUM(innings) - ({SAFE_NOT_OUTS_SQL}), 0), 2) AS batting_average,
                    ROUND(100.0 * SUM(runs) / NULLIF(SUM(balls_faced), 0), 2) AS strike_rate,
                    SUM(balls_faced) AS balls_faced, SUM(fours) AS fours, SUM(sixes) AS sixes,
                    SUM(fifties) AS fifties, SUM(hundreds) AS hundreds,
                    ROUND(100.0 * (SUM(fours) * 4 + SUM(sixes) * 6) / NULLIF(SUM(runs), 0), 2) AS boundary_pct,
                    ROUND(SUM(dot_ball_pct * balls_faced) / NULLIF(SUM(balls_faced), 0), 2) AS dot_ball_pct,
                    SUM(powerplay_runs) AS powerplay_runs,
                    ROUND(SUM(powerplay_strike_rate * powerplay_runs) / NULLIF(SUM(powerplay_runs), 0), 2) AS powerplay_strike_rate,
                    SUM(middle_runs) AS middle_runs,
                    ROUND(SUM(middle_strike_rate * middle_runs) / NULLIF(SUM(middle_runs), 0), 2) AS middle_strike_rate,
                    SUM(death_runs) AS death_runs,
                    ROUND(SUM(death_strike_rate * death_runs) / NULLIF(SUM(death_runs), 0), 2) AS death_strike_rate
                FROM player_batting_stats
                WHERE {batting_filter} AND period = 'career'
                GROUP BY player_id
            ),
            pf AS (
                SELECT player_id,
                    ROUND(SUM(form_score * COALESCE(NULLIF(recent_innings_count, 0), 1)) /
                          NULLIF(SUM(COALESCE(NULLIF(recent_innings_count, 0), 1)), 0), 2) AS impact_score
                FROM player_form WHERE {form_filter} GROUP BY player_id
            )
            SELECT
                p.id, p.canonical_name AS name, p.full_name, p.role, p.country,
                p.batting_style, p.bowling_style, p.bowling_type,
                t.canonical_name AS team_name,
                pf.impact_score,
                pbs.matches, pbs.innings, pbs.runs, pbs.batting_average, pbs.strike_rate,
                pbs.highest_score, pbs.fours, pbs.sixes, pbs.fifties, pbs.hundreds,
                pbs.balls_faced, pbs.not_outs, pbs.boundary_pct, pbs.dot_ball_pct,
                pbs.powerplay_runs, pbs.powerplay_strike_rate,
                pbs.middle_runs, pbs.middle_strike_rate,
                pbs.death_runs, pbs.death_strike_rate
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN pf ON p.id = pf.player_id
            LEFT JOIN pbs ON p.id = pbs.player_id
            WHERE p.id = :pid
        """),
        params
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Player not found")

    d = _row_to_dict(row)
    d["id"] = str(d["id"])
    d["format"] = target_format
    d["team_name"] = _player_display_team(db, player_id, target_format, d.get("team_name"))
    d["image_url"] = get_player_image_url(d.get("name"), d.get("full_name"), d.get("id"))

    # Get bowling stats if applicable
    bowling = db.execute(
        text(f"""
            SELECT SUM(matches) AS matches, SUM(innings) AS innings,
                   ROUND(SUM(balls_bowled) / 6.0, 1) AS overs,
                   SUM(balls_bowled) AS balls_bowled, SUM(wickets) AS wickets,
                   SUM(runs_conceded) AS runs_conceded,
                   ROUND(1.0 * SUM(runs_conceded) / NULLIF(SUM(wickets), 0), 2) AS bowling_average,
                   ROUND(1.0 * SUM(balls_bowled) / NULLIF(SUM(wickets), 0), 2) AS strike_rate,
                   ROUND(6.0 * SUM(runs_conceded) / NULLIF(SUM(balls_bowled), 0), 2) AS economy,
                   ROUND(SUM(dot_ball_pct * balls_bowled) / NULLIF(SUM(balls_bowled), 0), 2) AS dot_ball_pct
            FROM player_bowling_stats
            WHERE player_id = :pid AND {bowling_filter} AND period = 'career'
            GROUP BY player_id
        """),
        params
    ).fetchone()

    if bowling:
        d["bowling"] = _row_to_dict(bowling)

    return d


@router.get("/{player_id}/impact")
async def get_player_impact(player_id: str, format: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get the unified Impact Score with its explainable component breakdown."""
    validate_uuid(player_id, "player_id")
    target_format, form_filter, params = format_scope_clause("format", format)
    params["pid"] = player_id

    row = db.execute(
        text(f"""
            SELECT
                player_id,
                ROUND(SUM(form_score * COALESCE(NULLIF(recent_innings_count, 0), 1)) /
                      NULLIF(SUM(COALESCE(NULLIF(recent_innings_count, 0), 1)), 0), 2) AS impact_score,
                ROUND(AVG(recent_performance_component), 2) AS recent_form_component,
                ROUND(AVG(consistency_component), 2) AS consistency_component,
                ROUND(AVG(opposition_strength_component), 2) AS opposition_quality_component,
                ROUND(AVG(venue_performance_component), 2) AS performance_impact_component,
                ROUND(AVG(match_situation_component), 2) AS pressure_impact_component,
                ROUND(AVG(efficiency_component), 2) AS efficiency_component,
                SUM(recent_innings_count) AS recent_innings_count
            FROM player_form
            WHERE player_id = :pid AND {form_filter}
            GROUP BY player_id
        """),
        params
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Impact data not found")

    d = _row_to_dict(row)
    d["player_id"] = str(d["player_id"])

    return {
        "player_id": d["player_id"],
        "impact_score": d["impact_score"],
        "components": {
            "performance_impact": {"score": d["performance_impact_component"], "weight": 0.35,
                                   "description": "Sustained role-aware batting and bowling contribution"},
            "recent_form": {"score": d["recent_form_component"], "weight": 0.30,
                            "description": "Recent batting and bowling output with sample confidence"},
            "pressure_impact": {"score": d["pressure_impact_component"], "weight": 0.15,
                                "description": "Contribution in demanding match situations"},
            "opposition_quality": {"score": d["opposition_quality_component"], "weight": 0.10,
                                   "description": "Quality of opposition faced"},
            "consistency": {"score": d["consistency_component"], "weight": 0.05,
                            "description": "Reliability across innings"},
            "efficiency": {"score": d["efficiency_component"], "weight": 0.05,
                           "description": "Format-relative scoring or bowling efficiency"},
        },
        "recent_innings_count": d["recent_innings_count"],
    }


@router.get("/{player_id}/batting")
async def get_player_batting(
    player_id: str,
    format: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get detailed batting statistics for a player."""
    validate_uuid(player_id, "player_id")
    target_format, batting_filter, params = format_scope_clause("format", format)
    target_period = period or "career"
    params.update({"pid": player_id, "period": target_period})

    row = db.execute(
        text(f"""
            SELECT player_id, :scope AS format, :period AS period,
                   SUM(matches) AS matches, SUM(innings) AS innings, {SAFE_NOT_OUTS_SQL} AS not_outs,
                   SUM(runs) AS runs, MAX(highest_score) AS highest_score,
                   ROUND(1.0 * SUM(runs) / NULLIF(SUM(innings) - ({SAFE_NOT_OUTS_SQL}), 0), 2) AS batting_average,
                   ROUND(100.0 * SUM(runs) / NULLIF(SUM(balls_faced), 0), 2) AS strike_rate,
                   SUM(balls_faced) AS balls_faced, SUM(fours) AS fours, SUM(sixes) AS sixes,
                   ROUND(100.0 * (SUM(fours) * 4 + SUM(sixes) * 6) / NULLIF(SUM(runs), 0), 2) AS boundary_pct,
                   ROUND(SUM(dot_ball_pct * balls_faced) / NULLIF(SUM(balls_faced), 0), 2) AS dot_ball_pct,
                   SUM(fifties) AS fifties, SUM(hundreds) AS hundreds,
                   ROUND(AVG(consistency_score), 2) AS consistency_score,
                   SUM(powerplay_runs) AS powerplay_runs,
                   ROUND(SUM(powerplay_strike_rate * powerplay_runs) / NULLIF(SUM(powerplay_runs), 0), 2) AS powerplay_strike_rate,
                   SUM(middle_runs) AS middle_runs,
                   ROUND(SUM(middle_strike_rate * middle_runs) / NULLIF(SUM(middle_runs), 0), 2) AS middle_strike_rate,
                   SUM(death_runs) AS death_runs,
                   ROUND(SUM(death_strike_rate * death_runs) / NULLIF(SUM(death_runs), 0), 2) AS death_strike_rate,
                   SUM(chasing_runs) AS chasing_runs,
                   ROUND(SUM(chasing_strike_rate * chasing_runs) / NULLIF(SUM(chasing_runs), 0), 2) AS chasing_strike_rate,
                   SUM(first_innings_runs) AS first_innings_runs,
                   ROUND(SUM(first_innings_strike_rate * first_innings_runs) / NULLIF(SUM(first_innings_runs), 0), 2) AS first_innings_strike_rate
            FROM player_batting_stats
            WHERE player_id = :pid AND {batting_filter} AND period = :period
            GROUP BY player_id
        """),
        {**params, "scope": target_format}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Batting stats not found")

    return _row_to_dict(row)


@router.get("/{player_id}/bowling")
async def get_player_bowling(
    player_id: str,
    format: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get detailed bowling statistics for a player."""
    validate_uuid(player_id, "player_id")
    target_format, bowling_filter, params = format_scope_clause("format", format)
    target_period = period or "career"
    params.update({"pid": player_id, "period": target_period})

    row = db.execute(
        text(f"""
            SELECT player_id, :scope AS format, :period AS period,
                   SUM(matches) AS matches, SUM(innings) AS innings,
                   ROUND(SUM(balls_bowled) / 6.0, 1) AS overs,
                   SUM(balls_bowled) AS balls_bowled,
                   SUM(wickets) AS wickets, SUM(runs_conceded) AS runs_conceded,
                   ROUND(1.0 * SUM(runs_conceded) / NULLIF(SUM(wickets), 0), 2) AS bowling_average,
                   ROUND(1.0 * SUM(balls_bowled) / NULLIF(SUM(wickets), 0), 2) AS strike_rate,
                   ROUND(6.0 * SUM(runs_conceded) / NULLIF(SUM(balls_bowled), 0), 2) AS economy,
                   ROUND(SUM(dot_ball_pct * balls_bowled) / NULLIF(SUM(balls_bowled), 0), 2) AS dot_ball_pct,
                   ROUND(SUM(boundary_conceded_pct * balls_bowled) / NULLIF(SUM(balls_bowled), 0), 2) AS boundary_conceded_pct,
                   SUM(powerplay_overs) AS powerplay_overs, SUM(powerplay_wickets) AS powerplay_wickets,
                   ROUND(AVG(powerplay_economy), 2) AS powerplay_economy,
                   SUM(middle_overs) AS middle_overs, SUM(middle_wickets) AS middle_wickets,
                   ROUND(AVG(middle_economy), 2) AS middle_economy,
                   SUM(death_overs) AS death_overs, SUM(death_wickets) AS death_wickets,
                   ROUND(AVG(death_economy), 2) AS death_economy
            FROM player_bowling_stats
            WHERE player_id = :pid AND {bowling_filter} AND period = :period
            GROUP BY player_id
        """),
        {**params, "scope": target_format}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Bowling stats not found")

    return _row_to_dict(row)


@router.get("/{player_id}/matchups")
async def get_player_matchups(
    player_id: str,
    type: str = Query("batting", description="Matchup type: batting or bowling"),
    format: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get player matchup data against specific opponents."""
    validate_uuid(player_id, "player_id")
    target_format, matchup_filter, params = format_scope_clause("bbm.format", format)
    params["pid"] = player_id

    if type not in {"batting", "bowling"}:
        raise HTTPException(
            status_code=400, detail="Invalid matchup type. Must be batting or bowling"
        )

    if type == "batting":
        rows = db.execute(
            text(f"""
                SELECT
                    bbm.bowler_id AS opponent_id,
                    p.canonical_name AS opponent_name,
                    SUM(bbm.total_balls) AS total_balls, SUM(bbm.total_runs) AS total_runs,
                    SUM(bbm.total_wickets) AS total_wickets,
                    ROUND(100.0 * SUM(bbm.total_runs) / NULLIF(SUM(bbm.total_balls), 0), 2) AS strike_rate,
                    ROUND(1.0 * SUM(bbm.total_runs) / NULLIF(SUM(bbm.total_wickets), 0), 2) AS batting_average,
                    SUM(bbm.dot_balls) AS dot_balls, SUM(bbm.boundaries) AS boundaries,
                    SUM(bbm.sixes) AS sixes
                FROM batter_bowler_matchups bbm
                JOIN players p ON bbm.bowler_id = p.id
                WHERE bbm.batter_id = :pid AND {matchup_filter}
                GROUP BY bbm.bowler_id, p.canonical_name
                ORDER BY total_runs DESC
                LIMIT 20
            """),
            params
        ).fetchall()
    else:
        rows = db.execute(
            text(f"""
                SELECT
                    bbm.batter_id AS opponent_id,
                    p.canonical_name AS opponent_name,
                    SUM(bbm.total_balls) AS total_balls, SUM(bbm.total_runs) AS total_runs,
                    SUM(bbm.total_wickets) AS total_wickets,
                    ROUND(100.0 * SUM(bbm.total_runs) / NULLIF(SUM(bbm.total_balls), 0), 2) AS strike_rate,
                    ROUND(1.0 * SUM(bbm.total_runs) / NULLIF(SUM(bbm.total_wickets), 0), 2) AS batting_average,
                    SUM(bbm.dot_balls) AS dot_balls, SUM(bbm.boundaries) AS boundaries,
                    SUM(bbm.sixes) AS sixes
                FROM batter_bowler_matchups bbm
                JOIN players p ON bbm.batter_id = p.id
                WHERE bbm.bowler_id = :pid AND {matchup_filter}
                GROUP BY bbm.batter_id, p.canonical_name
                ORDER BY total_wickets DESC
                LIMIT 20
            """),
            params
        ).fetchall()

    return {
        "player_id": player_id,
        "type": type,
        "format": target_format,
        "matchups": [{k: str(v) if k == "opponent_id" else v for k, v in _row_to_dict(r).items()} for r in rows],
    }


@router.get("/{player_id}/affiliations")
async def get_player_affiliations(player_id: str, db: Session = Depends(get_db)):
    """Get team affiliations for a player across formats and competitions."""
    validate_uuid(player_id, "player_id")

    rows = db.execute(
        text("""
            SELECT
                pta.id, pta.format, pta.season, pta.is_current,
                t.canonical_name AS team_name, t.short_name AS team_short,
                c.name AS competition_name,
                pta.start_date, pta.end_date
            FROM player_team_affiliations pta
            JOIN teams t ON pta.team_id = t.id
            LEFT JOIN competitions c ON pta.competition_id = c.id
            WHERE pta.player_id = :pid
            ORDER BY pta.is_current DESC, t.canonical_name
        """),
        {"pid": player_id}
    ).fetchall()

    affiliations = []
    for row in rows:
        d = _row_to_dict(row)
        d["id"] = str(d["id"])
        affiliations.append(d)

    return {
        "player_id": player_id,
        "affiliations": affiliations,
        "total": len(affiliations),
    }
