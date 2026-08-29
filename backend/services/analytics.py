"""
Cricket Analytics Query Layer
==============================

Provides reusable SQL aggregation functions for all analytical dimensions.
All queries operate on the existing serving tables (no deliveries dependency).

Dimensions supported:
- Player: career, format, year, competition, season, opponent, venue
- Team: overall, format, year, competition, season, head-to-head, venue
- Competition: summary, seasons, matches, top performers
- Venue: overall, format, team/player performance
- Match: metadata, scorecards, navigation
- Time-series: player/team statistics by year
"""

import time
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _query(conn, sql: str, params: dict = None) -> list[dict]:
    """Execute a query and return list of dicts."""
    rows = conn.execute(text(sql), params or {}).fetchall()
    return [dict(r._mapping) for r in rows]


def _scalar(conn, sql: str, params: dict = None):
    """Execute a query and return scalar result."""
    return conn.execute(text(sql), params or {}).scalar()


# ============================================================
# PLAYER ANALYTICS
# ============================================================


def player_career(conn, player_id: str) -> dict:
    """Get career statistics across all formats for a player."""
    batting = _query(
        conn,
        """SELECT format, matches, innings, not_outs, runs, highest_score,
                  batting_average, strike_rate, balls_faced, fours, sixes,
                  fifties, hundreds
           FROM player_batting_stats
           WHERE player_id = :pid AND period = 'career'
           ORDER BY format""",
        {"pid": player_id},
    )
    bowling = _query(
        conn,
        """SELECT format, matches, innings, overs, wickets, runs_conceded,
                  bowling_average, economy, strike_rate, best_bowling,
                  four_wickets, five_wickets
           FROM player_bowling_stats
           WHERE player_id = :pid AND period = 'career'
           ORDER BY format""",
        {"pid": player_id},
    )
    form = _query(
        conn,
        """SELECT format, form_score, recent_innings_count
           FROM player_form WHERE player_id = :pid ORDER BY format""",
        {"pid": player_id},
    )
    return {
        "player_id": player_id,
        "batting": {r["format"]: r for r in batting},
        "bowling": {r["format"]: r for r in bowling},
        "form": {r["format"]: r for r in form},
    }


def player_by_year(
    conn, player_id: str, fmt: str, batting: bool = True
) -> list[dict]:
    """Get player statistics grouped by year for a format."""
    table = "match_batting_summary" if batting else "match_bowling_summary"
    if batting:
        agg = """EXTRACT(YEAR FROM m.match_date)::int as year,
                 SUM(mbs.runs) as runs, SUM(mbs.balls) as balls,
                 SUM(mbs.fours) as fours, SUM(mbs.sixes) as sixes,
                 COUNT(DISTINCT mbs.match_id) as matches,
                 COUNT(*) as innings"""
    else:
        agg = """EXTRACT(YEAR FROM m.match_date)::int as year,
                 SUM(mbs.runs_conceded) as runs_conceded,
                 SUM(mbs.wickets) as wickets,
                 SUM(mbs.balls_bowled) as balls_bowled,
                 COUNT(DISTINCT mbs.match_id) as matches,
                 COUNT(*) as innings"""
    return _query(
        conn,
        f"""SELECT {agg}
            FROM {table} mbs
            JOIN matches m ON mbs.match_id = m.id
            JOIN players p ON mbs.player_id = p.id
            WHERE p.id = :pid AND m.format = :fmt
            GROUP BY year ORDER BY year""",
        {"pid": player_id, "fmt": fmt},
    )


def player_by_competition(
    conn, player_id: str, fmt: str, batting: bool = True
) -> list[dict]:
    """Get player statistics grouped by competition for a format."""
    table = "match_batting_summary" if batting else "match_bowling_summary"
    if batting:
        agg = """COALESCE(c.name, 'Unknown') as competition,
                 SUM(mbs.runs) as runs, SUM(mbs.balls) as balls,
                 SUM(mbs.fours) as fours, SUM(mbs.sixes) as sixes,
                 COUNT(DISTINCT mbs.match_id) as matches,
                 COUNT(*) as innings"""
    else:
        agg = """COALESCE(c.name, 'Unknown') as competition,
                 SUM(mbs.runs_conceded) as runs_conceded,
                 SUM(mbs.wickets) as wickets,
                 COUNT(DISTINCT mbs.match_id) as matches,
                 COUNT(*) as innings"""
    return _query(
        conn,
        f"""SELECT {agg}
            FROM {table} mbs
            JOIN matches m ON mbs.match_id = m.id
            JOIN players p ON mbs.player_id = p.id
            LEFT JOIN competitions c ON m.competition_id = c.id
            WHERE p.id = :pid AND m.format = :fmt
            GROUP BY c.name ORDER BY matches DESC""",
        {"pid": player_id, "fmt": fmt},
    )


def player_by_season(
    conn, player_id: str, fmt: str, batting: bool = True
) -> list[dict]:
    """Get player statistics grouped by season for a format."""
    table = "match_batting_summary" if batting else "match_bowling_summary"
    if batting:
        agg = """COALESCE(s.name, 'Unknown') as season,
                 SUM(mbs.runs) as runs, SUM(mbs.balls) as balls,
                 COUNT(DISTINCT mbs.match_id) as matches,
                 COUNT(*) as innings"""
    else:
        agg = """COALESCE(s.name, 'Unknown') as season,
                 SUM(mbs.runs_conceded) as runs_conceded,
                 SUM(mbs.wickets) as wickets,
                 COUNT(DISTINCT mbs.match_id) as matches,
                 COUNT(*) as innings"""
    return _query(
        conn,
        f"""SELECT {agg}
            FROM {table} mbs
            JOIN matches m ON mbs.match_id = m.id
            JOIN players p ON mbs.player_id = p.id
            LEFT JOIN seasons s ON m.season_id = s.id
            WHERE p.id = :pid AND m.format = :fmt
            GROUP BY s.name ORDER BY matches DESC""",
        {"pid": player_id, "fmt": fmt},
    )


def player_vs_opponent(
    conn, player_id: str, fmt: str, batting: bool = True
) -> list[dict]:
    """Get player statistics vs each opponent team for a format."""
    table = "match_batting_summary" if batting else "match_bowling_summary"
    if batting:
        agg = """opp.canonical_name as opponent,
                 SUM(mbs.runs) as runs, SUM(mbs.balls) as balls,
                 SUM(mbs.fours) as fours, SUM(mbs.sixes) as sixes,
                 COUNT(DISTINCT mbs.match_id) as matches,
                 COUNT(*) as innings"""
    else:
        agg = """opp.canonical_name as opponent,
                 SUM(mbs.runs_conceded) as runs_conceded,
                 SUM(mbs.wickets) as wickets,
                 COUNT(DISTINCT mbs.match_id) as matches,
                 COUNT(*) as innings"""
    return _query(
        conn,
        f"""SELECT {agg}
            FROM {table} mbs
            JOIN innings i ON mbs.innings_id = i.id
            JOIN matches m ON mbs.match_id = m.id
            JOIN players p ON mbs.player_id = p.id
            JOIN teams opp ON i.bowling_team_id = opp.id
            WHERE p.id = :pid AND m.format = :fmt
            GROUP BY opp.canonical_name ORDER BY matches DESC""",
        {"pid": player_id, "fmt": fmt},
    )


def player_at_venue(conn, player_id: str, fmt: str) -> list[dict]:
    """Get player statistics at each venue for a format."""
    return _query(
        conn,
        """SELECT v.name as venue, v.city,
                  SUM(mbs.runs) as runs, SUM(mbs.balls) as balls,
                  SUM(mbs.fours) as fours, SUM(mbs.sixes) as sixes,
                  COUNT(DISTINCT mbs.match_id) as matches,
                  COUNT(*) as innings
           FROM match_batting_summary mbs
           JOIN matches m ON mbs.match_id = m.id
           JOIN players p ON mbs.player_id = p.id
           JOIN venues v ON m.venue_id = v.id
           WHERE p.id = :pid AND m.format = :fmt
           GROUP BY v.name, v.city ORDER BY matches DESC""",
        {"pid": player_id, "fmt": fmt},
    )


def player_match_history(conn, player_id: str, fmt: str, limit: int = 20) -> list[dict]:
    """Get recent match history for a player in a format."""
    return _query(
        conn,
        """SELECT m.id as match_id, m.match_date, m.format,
                  ta.canonical_name as team_a, tb.canonical_name as team_b,
                  tw.canonical_name as winner, v.name as venue,
                  c.name as competition, s.name as season,
                  mbs.runs, mbs.balls, mbs.fours, mbs.sixes,
                  mbs.strike_rate, mbs.is_not_out, mbs.dismissal_type
           FROM match_batting_summary mbs
           JOIN matches m ON mbs.match_id = m.id
           JOIN players p ON mbs.player_id = p.id
           LEFT JOIN teams ta ON m.team_a_id = ta.id
           LEFT JOIN teams tb ON m.team_b_id = tb.id
           LEFT JOIN teams tw ON m.winner_id = tw.id
           LEFT JOIN venues v ON m.venue_id = v.id
           LEFT JOIN competitions c ON m.competition_id = c.id
           LEFT JOIN seasons s ON m.season_id = s.id
           WHERE p.id = :pid AND m.format = :fmt
           ORDER BY m.match_date DESC
           LIMIT :limit""",
        {"pid": player_id, "fmt": fmt, "limit": limit},
    )


# ============================================================
# TEAM ANALYTICS
# ============================================================


def team_by_format(conn, team_id: str) -> list[dict]:
    """Get team performance broken down by format."""
    return _query(
        conn,
        """SELECT format, matches, wins, losses, ties, no_results, win_rate,
                  avg_first_innings_score, avg_second_innings_score,
                  batting_strength_score, bowling_strength_score
           FROM team_performance
           WHERE team_id = :tid AND period = 'career'
           ORDER BY matches DESC""",
        {"tid": team_id},
    )


def team_by_year(conn, team_id: str, fmt: str) -> list[dict]:
    """Get team statistics grouped by year for a format."""
    return _query(
        conn,
        """SELECT EXTRACT(YEAR FROM m.match_date)::int as year,
                  COUNT(*) as matches,
                  SUM(CASE WHEN m.winner_id = :tid THEN 1 ELSE 0 END) as wins,
                  SUM(CASE WHEN m.result_type = 'draw' THEN 1 ELSE 0 END) as draws,
                  SUM(CASE WHEN m.result_type = 'tie' THEN 1 ELSE 0 END) as ties,
                  SUM(CASE WHEN m.result_type IN ('no_result','abandoned') THEN 1 ELSE 0 END) as no_results
           FROM matches m
           WHERE (m.team_a_id = :tid OR m.team_b_id = :tid) AND m.format = :fmt
           GROUP BY year ORDER BY year""",
        {"tid": team_id, "fmt": fmt},
    )


def team_vs_team(
    conn, team_a_id: str, team_b_id: str, fmt: Optional[str] = None
) -> dict:
    """Get head-to-head record between two teams."""
    base = """(m.team_a_id = :a AND m.team_b_id = :b)
               OR (m.team_a_id = :b AND m.team_b_id = :a)"""

    if fmt:
        where_clause = f"({base}) AND m.format = :fmt"
        params = {"a": team_a_id, "b": team_b_id, "fmt": fmt}
    else:
        where_clause = base
        params = {"a": team_a_id, "b": team_b_id}

    overall = _query(
        conn,
        f"""SELECT m.format,
                    COUNT(*) as matches,
                    SUM(CASE WHEN m.winner_id = :a THEN 1 ELSE 0 END) as team_a_wins,
                    SUM(CASE WHEN m.winner_id = :b THEN 1 ELSE 0 END) as team_b_wins,
                    SUM(CASE WHEN m.result_type = 'draw' THEN 1 ELSE 0 END) as draws,
                    SUM(CASE WHEN m.result_type = 'tie' THEN 1 ELSE 0 END) as ties,
                    SUM(CASE WHEN m.result_type IN ('no_result','abandoned') THEN 1 ELSE 0 END) as no_results
             FROM matches m WHERE {where_clause}
             GROUP BY m.format ORDER BY m.format""",
        params,
    )
    return {"team_a_id": team_a_id, "team_b_id": team_b_id, "by_format": overall}


def team_at_venue(conn, team_id: str, fmt: str) -> list[dict]:
    """Get team statistics at each venue."""
    return _query(
        conn,
        """SELECT v.name as venue, v.city,
                  COUNT(*) as matches,
                  SUM(CASE WHEN m.winner_id = :tid THEN 1 ELSE 0 END) as wins,
                  SUM(CASE WHEN m.result_type = 'draw' THEN 1 ELSE 0 END) as draws
           FROM matches m
           JOIN venues v ON m.venue_id = v.id
           WHERE (m.team_a_id = :tid OR m.team_b_id = :tid) AND m.format = :fmt
           GROUP BY v.name, v.city ORDER BY matches DESC""",
        {"tid": team_id, "fmt": fmt},
    )


def team_by_competition(conn, team_id: str) -> list[dict]:
    """Get team performance by competition."""
    return _query(
        conn,
        """SELECT COALESCE(c.name, 'Unknown') as competition, m.format,
                  COUNT(*) as matches,
                  SUM(CASE WHEN m.winner_id = :tid THEN 1 ELSE 0 END) as wins,
                  SUM(CASE WHEN m.result_type = 'draw' THEN 1 ELSE 0 END) as draws
           FROM matches m
           LEFT JOIN competitions c ON m.competition_id = c.id
           WHERE m.team_a_id = :tid OR m.team_b_id = :tid
           GROUP BY c.name, m.format ORDER BY c.name, m.format""",
        {"tid": team_id},
    )


def team_match_history(conn, team_id: str, fmt: str, limit: int = 20) -> list[dict]:
    """Get recent match history for a team in a format."""
    return _query(
        conn,
        """SELECT m.id as match_id, m.match_date,
                  ta.canonical_name as team_a, tb.canonical_name as team_b,
                  tw.canonical_name as winner, v.name as venue,
                  c.name as competition, s.name as season,
                  m.win_margin, m.win_type, m.result_type
           FROM matches m
           LEFT JOIN teams ta ON m.team_a_id = ta.id
           LEFT JOIN teams tb ON m.team_b_id = tb.id
           LEFT JOIN teams tw ON m.winner_id = tw.id
           LEFT JOIN venues v ON m.venue_id = v.id
           LEFT JOIN competitions c ON m.competition_id = c.id
           LEFT JOIN seasons s ON m.season_id = s.id
           WHERE (m.team_a_id = :tid OR m.team_b_id = :tid) AND m.format = :fmt
           ORDER BY m.match_date DESC LIMIT :limit""",
        {"tid": team_id, "fmt": fmt, "limit": limit},
    )


# ============================================================
# COMPETITION ANALYTICS
# ============================================================


def competition_summary(conn, competition_id: str) -> dict:
    """Get competition summary with seasons and match counts."""
    comp = _query(
        conn,
        """SELECT id, name, short_name, format, competition_type, governing_body
           FROM competitions WHERE id = :cid""",
        {"cid": competition_id},
    )
    if not comp:
        return {}
    seasons = _query(
        conn,
        """SELECT s.id, s.name, s.start_date, s.end_date,
                  COUNT(m.id) as matches
           FROM seasons s
           LEFT JOIN matches m ON m.season_id = s.id
           WHERE s.competition_id = :cid
           GROUP BY s.id, s.name, s.start_date, s.end_date
           ORDER BY s.name DESC""",
        {"cid": competition_id},
    )
    return {**comp[0], "seasons": seasons}


def competition_season_matches(
    conn, season_id: str, limit: int = 50, offset: int = 0
) -> dict:
    """Get matches in a specific season."""
    matches = _query(
        conn,
        """SELECT m.id, m.match_date, m.format,
                  ta.canonical_name as team_a, tb.canonical_name as team_b,
                  tw.canonical_name as winner, v.name as venue,
                  m.win_margin, m.win_type, m.result_type
           FROM matches m
           LEFT JOIN teams ta ON m.team_a_id = ta.id
           LEFT JOIN teams tb ON m.team_b_id = tb.id
           LEFT JOIN teams tw ON m.winner_id = tw.id
           LEFT JOIN venues v ON m.venue_id = v.id
           WHERE m.season_id = :sid
           ORDER BY m.match_date
           LIMIT :limit OFFSET :offset""",
        {"sid": season_id, "limit": limit, "offset": offset},
    )
    total = _scalar(
        conn,
        "SELECT COUNT(*) FROM matches WHERE season_id = :sid",
        {"sid": season_id},
    )
    return {"matches": matches, "total": total}


# ============================================================
# VENUE ANALYTICS
# ============================================================


def venue_by_format(conn, venue_id: str) -> list[dict]:
    """Get venue statistics by format."""
    return _query(
        conn,
        """SELECT format, total_matches, avg_first_innings_score,
                  avg_second_innings_score, highest_total, lowest_total,
                  chasing_win_pct, pace_wickets_pct, spin_wickets_pct
           FROM venue_stats
           WHERE venue_id = :vid ORDER BY total_matches DESC""",
        {"vid": venue_id},
    )


def venue_team_performance(conn, venue_id: str, fmt: str) -> list[dict]:
    """Get team performance at a venue."""
    return _query(
        conn,
        """SELECT t.canonical_name as team,
                  COUNT(*) as matches,
                  SUM(CASE WHEN m.winner_id = t.id THEN 1 ELSE 0 END) as wins
           FROM matches m
           JOIN venues v ON m.venue_id = v.id
           JOIN teams t ON (m.team_a_id = t.id OR m.team_b_id = t.id)
           WHERE m.venue_id = :vid AND m.format = :fmt
           GROUP BY t.canonical_name ORDER BY wins DESC""",
        {"vid": venue_id, "fmt": fmt},
    )


def venue_player_performance(conn, venue_id: str, fmt: str, limit: int = 20) -> list[dict]:
    """Get top player performances at a venue."""
    return _query(
        conn,
        """SELECT p.canonical_name as player,
                  SUM(mbs.runs) as total_runs,
                  COUNT(DISTINCT mbs.match_id) as matches,
                  COUNT(*) as innings
           FROM match_batting_summary mbs
           JOIN matches m ON mbs.match_id = m.id
           JOIN players p ON mbs.player_id = p.id
           WHERE m.venue_id = :vid AND m.format = :fmt
           GROUP BY p.canonical_name
           ORDER BY total_runs DESC LIMIT :limit""",
        {"vid": venue_id, "fmt": fmt, "limit": limit},
    )


# ============================================================
# MATCH ANALYTICS
# ============================================================


def match_detail(conn, match_id: str) -> dict:
    """Get complete match detail with scorecards."""
    match = _query(
        conn,
        """SELECT m.id, m.match_date, m.format, m.win_margin, m.win_type,
                  m.result_type, m.toss_decision, m.total_innings,
                  ta.canonical_name as team_a, tb.canonical_name as team_b,
                  tw.canonical_name as winner, v.name as venue, v.city,
                  c.name as competition, s.name as season
           FROM matches m
           LEFT JOIN teams ta ON m.team_a_id = ta.id
           LEFT JOIN teams tb ON m.team_b_id = tb.id
           LEFT JOIN teams tw ON m.winner_id = tw.id
           LEFT JOIN venues v ON m.venue_id = v.id
           LEFT JOIN competitions c ON m.competition_id = c.id
           LEFT JOIN seasons s ON m.season_id = s.id
           WHERE m.id = :mid""",
        {"mid": match_id},
    )
    if not match:
        return {}

    innings = _query(
        conn,
        """SELECT i.id, i.innings_number,
                  bt.canonical_name as batting_team,
                  bw.canonical_name as bowling_team,
                  i.total_runs, i.total_wickets, i.total_overs,
                  i.declared, i.all_out, i.follow_on
           FROM innings i
           JOIN teams bt ON i.batting_team_id = bt.id
           JOIN teams bw ON i.bowling_team_id = bw.id
           WHERE i.match_id = :mid
           ORDER BY i.innings_number""",
        {"mid": match_id},
    )

    batting = _query(
        conn,
        """SELECT mbs.innings_id, i.innings_number,
                  p.canonical_name as player,
                  bt.canonical_name as team,
                  mbs.runs, mbs.balls, mbs.fours, mbs.sixes,
                  mbs.strike_rate, mbs.is_not_out, mbs.dismissal_type
           FROM match_batting_summary mbs
           JOIN innings i ON mbs.innings_id = i.id
           JOIN players p ON mbs.player_id = p.id
           JOIN teams bt ON mbs.batting_team_id = bt.id
           WHERE mbs.match_id = :mid
           ORDER BY i.innings_number, mbs.runs DESC""",
        {"mid": match_id},
    )

    bowling = _query(
        conn,
        """SELECT mbs.innings_id, i.innings_number,
                  p.canonical_name as player,
                  bw.canonical_name as team,
                  mbs.overs, mbs.balls_bowled, mbs.runs_conceded,
                  mbs.wickets, mbs.economy, mbs.wides, mbs.noballs
           FROM match_bowling_summary mbs
           JOIN innings i ON mbs.innings_id = i.id
           JOIN players p ON mbs.player_id = p.id
           JOIN teams bw ON mbs.bowling_team_id = bw.id
           WHERE mbs.match_id = :mid
           ORDER BY i.innings_number, mbs.wickets DESC""",
        {"mid": match_id},
    )

    result = match[0]
    result["id"] = str(result["id"])
    result["innings"] = innings
    result["batting"] = batting
    result["bowling"] = bowling
    return result


# ============================================================
# TIME-SERIES
# ============================================================


def player_career_progression(conn, player_id: str, fmt: str) -> list[dict]:
    """Get cumulative career progression by year."""
    yearly = player_by_year(conn, player_id, fmt, batting=True)
    cumulative = []
    runs_total = 0
    matches_total = 0
    for row in yearly:
        runs_total += row["runs"]
        matches_total += row["matches"]
        cumulative.append({
            "year": row["year"],
            "year_runs": row["runs"],
            "year_matches": row["matches"],
            "cumulative_runs": runs_total,
            "cumulative_matches": matches_total,
        })
    return cumulative


def team_year_trend(conn, team_id: str, fmt: str) -> list[dict]:
    """Get team win-rate trend by year."""
    yearly = team_by_year(conn, team_id, fmt)
    return [
        {
            "year": r["year"],
            "matches": r["matches"],
            "wins": r["wins"],
            "win_rate": round(r["wins"] / r["matches"] * 100, 1)
            if r["matches"] > 0
            else 0,
        }
        for r in yearly
    ]


# ============================================================
# DATA COMPLETENESS
# ============================================================


def data_completeness(conn) -> dict:
    """Measure coverage of key dimensions."""
    total = _scalar(conn, "SELECT COUNT(*) FROM matches")
    return {
        "total_matches": total,
        "competition_coverage": {
            "with_competition": _scalar(
                conn,
                "SELECT COUNT(*) FROM matches WHERE competition_id IS NOT NULL",
            ),
            "without_competition": _scalar(
                conn,
                "SELECT COUNT(*) FROM matches WHERE competition_id IS NULL",
            ),
        },
        "season_coverage": {
            "with_season": _scalar(
                conn, "SELECT COUNT(*) FROM matches WHERE season_id IS NOT NULL"
            ),
        },
        "venue_coverage": {
            "with_venue": _scalar(
                conn, "SELECT COUNT(*) FROM matches WHERE venue_id IS NOT NULL"
            ),
        },
        "by_format": {
            fmt: _scalar(
                conn,
                "SELECT COUNT(*) FROM matches WHERE format = :f",
                {"f": fmt},
            )
            for fmt in ["T20", "T20I", "ODI", "Test"]
        },
    }


# ============================================================
# PERFORMANCE PROFILING
# ============================================================


def profile_query(conn, func, *args, **kwargs) -> dict:
    """Profile a query function and return timing + result."""
    start = time.time()
    result = func(conn, *args, **kwargs)
    elapsed = round((time.time() - start) * 1000, 1)
    return {"result": result, "query_time_ms": elapsed}
