"""Search and dashboard analytics for competition editions."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.utils.player_images import get_player_image_url


COMPETITION_ALIASES = {
    "cwc": "icc cricket world cup",
    "odi world cup": "icc cricket world cup",
    "cricket world cup": "icc cricket world cup",
    "icc cricket world cup": "icc cricket world cup",
    "t20wc": "icc men s t20 world cup",
    "t20 wc": "icc men s t20 world cup",
    "t20 world cup": "icc men s t20 world cup",
    "men s t20 world cup": "icc men s t20 world cup",
    "wt20": "icc men s t20 world cup",
    "champions trophy": "icc champions trophy",
    "icc champions trophy": "icc champions trophy",
    "ipl": "indian premier league",
    "indian premier league": "indian premier league",
    "ashes": "the ashes",
    "the ashes": "the ashes",
    "bgt": "border gavaskar trophy",
    "border gavaskar trophy": "border gavaskar trophy",
    "wtc": "icc world test championship",
    "world test championship": "icc world test championship",
}

ACRONYM_STOP_WORDS = {"icc", "the", "men", "mens", "women", "womens", "of"}


def normalize_search_text(value: str | None) -> str:
    """Normalize punctuation, accents, and joined aliases such as ``CWC23``."""
    ascii_value = "".join(
        character
        for character in unicodedata.normalize("NFKD", str(value or ""))
        if not unicodedata.combining(character)
    ).casefold()
    # Split joined aliases such as CWC23, while preserving format tokens such
    # as T20 and T10 whose leading letter is part of the name.
    ascii_value = re.sub(r"([a-z]{2,})(\d+)", r"\1 \2", ascii_value)
    ascii_value = re.sub(r"(\d+)([a-z]{2,})", r"\1 \2", ascii_value)
    return re.sub(r"[^a-z0-9]+", " ", ascii_value).strip()


def _query_terms(query: str) -> tuple[str, str | None]:
    normalized = normalize_search_text(query)
    tokens = normalized.split()
    season = None
    text_tokens: list[str] = []
    for token in tokens:
        if re.fullmatch(r"(?:19|20)\d{2}", token):
            season = token
        elif re.fullmatch(r"\d{2}", token):
            value = int(token)
            season = str(2000 + value if value <= 50 else 1900 + value)
        else:
            text_tokens.append(token)
    return " ".join(text_tokens), season


def _acronym(name: str) -> str:
    tokens = [token for token in normalize_search_text(name).split() if token not in ACRONYM_STOP_WORDS]
    return "".join(token[0] for token in tokens)


def _season_sort_value(value: str | None) -> int:
    years = re.findall(r"(?:19|20)\d{2}", str(value or ""))
    return max(map(int, years), default=0)


def rank_competition_candidates(rows: list[dict[str, Any]], query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Rank competition-season rows while keeping player-like searches out."""
    search_text, requested_season = _query_terms(query)
    if not search_text:
        return []
    alias_target = COMPETITION_ALIASES.get(search_text)
    search_tokens = set(search_text.split())
    compact_search = search_text.replace(" ", "")
    ranked: list[tuple[int, int, int, dict[str, Any]]] = []

    for row in rows:
        if int(row.get("match_count") or 0) <= 0:
            continue
        season_name = str(row.get("season_name") or "")
        if requested_season and requested_season not in season_name:
            continue

        name = normalize_search_text(row.get("name"))
        short_name = normalize_search_text(row.get("short_name"))
        name_tokens = set(name.split())
        score = 0
        if alias_target and name == alias_target:
            score = 120
        elif search_text in {name, short_name}:
            score = 110
        elif compact_search and compact_search in {_acronym(name), short_name.replace(" ", "")}:
            score = 95
        elif len(search_text) >= 4 and search_text in name:
            score = 80
        elif len(search_tokens) >= 2 and search_tokens.issubset(name_tokens):
            score = 70

        if score:
            if requested_season:
                score += 25
            ranked.append((score, _season_sort_value(season_name), int(row["match_count"]), row))

    ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    seen: set[tuple[str, str]] = set()
    results = []
    for score, _, _, row in ranked:
        key = (str(row["id"]), str(row["season_id"]))
        if key in seen:
            continue
        seen.add(key)
        item = dict(row)
        for field in ("id", "season_id"):
            item[field] = str(item[field])
        item["score"] = score
        results.append(item)
        if len(results) >= limit:
            break
    return results


def search_competitions(db: Session, query: str, limit: int = 5) -> list[dict[str, Any]]:
    rows = db.execute(text("""
        SELECT c.id, c.name, c.short_name, c.format,
               s.id AS season_id, s.name AS season_name,
               s.start_date, s.end_date,
               COUNT(m.id) AS match_count,
               MIN(m.match_date) AS first_match_date,
               MAX(m.match_date) AS last_match_date
        FROM competitions c
        JOIN seasons s ON s.competition_id = c.id
        LEFT JOIN matches m ON m.season_id = s.id
        GROUP BY c.id, c.name, c.short_name, c.format,
                 s.id, s.name, s.start_date, s.end_date
    """)).fetchall()
    return rank_competition_candidates([dict(row._mapping) for row in rows], query, limit)


def _result_text(match: dict[str, Any]) -> str:
    result_type = match.get("result_type")
    if result_type == "draw":
        return "Draw"
    if result_type == "tie":
        return "Tie"
    if result_type == "abandoned":
        return "Abandoned"
    if result_type == "no_result":
        return "No result"
    if match.get("winner"):
        margin = f" by {match['win_margin']} {match['win_type']}" if match.get("win_margin") is not None and match.get("win_type") else ""
        return f"{match['winner']} won{margin}"
    return "No result"


def _attach_scores(db: Session, matches: list[dict[str, Any]]) -> None:
    if not matches:
        return
    values = {
        f"match_{index}": str(match["id"]).replace("-", "")
        for index, match in enumerate(matches)
    }
    placeholders = ", ".join(f":{key}" for key in values)
    rows = db.execute(text(f"""
        SELECT REPLACE(CAST(i.match_id AS TEXT), '-', '') AS match_key,
               t.canonical_name AS batting_team, i.innings_number,
               i.total_runs, i.total_wickets
        FROM innings i JOIN teams t ON t.id = i.batting_team_id
        WHERE REPLACE(CAST(i.match_id AS TEXT), '-', '') IN ({placeholders})
        ORDER BY i.match_id, i.innings_number
    """), values).fetchall()
    scorelines: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        item = dict(row._mapping)
        wickets = item.get("total_wickets")
        score = str(item["total_runs"]) if wickets is None or wickets >= 10 else f"{item['total_runs']}/{wickets}"
        scorelines.setdefault((item["match_key"], item["batting_team"]), []).append(score)
    for match in matches:
        key = str(match["id"]).replace("-", "")
        match["score_team_a"] = " & ".join(scorelines.get((key, match.get("team_a")), [])) or None
        match["score_team_b"] = " & ".join(scorelines.get((key, match.get("team_b")), [])) or None


def tournament_dashboard(db: Session, competition_id: str, season_id: str | None = None) -> dict[str, Any] | None:
    competition = db.execute(text("""
        SELECT id, name, short_name, format, governing_body, season
        FROM competitions WHERE id = :competition_id
    """), {"competition_id": competition_id}).fetchone()
    if not competition:
        return None

    seasons = db.execute(text("""
        SELECT s.id, s.name, s.start_date, s.end_date,
               COUNT(m.id) AS matches,
               MIN(m.match_date) AS first_match_date,
               MAX(m.match_date) AS last_match_date
        FROM seasons s
        LEFT JOIN matches m ON m.season_id = s.id
        WHERE s.competition_id = :competition_id
        GROUP BY s.id, s.name, s.start_date, s.end_date
        ORDER BY MAX(m.match_date) DESC, s.name DESC
    """), {"competition_id": competition_id}).fetchall()
    season_rows = [dict(row._mapping) for row in seasons]
    if not season_rows:
        return None
    selected = next((row for row in season_rows if str(row["id"]) == str(season_id)), None) if season_id else None
    if season_id and selected is None:
        return None
    selected = selected or next((row for row in season_rows if int(row.get("matches") or 0) > 0), season_rows[0])
    sid = str(selected["id"])
    params = {"season_id": sid}

    overview = db.execute(text("""
        WITH season_matches AS (
            SELECT id, team_a_id, team_b_id, venue_id, winner_id
            FROM matches WHERE season_id = :season_id
        ), participants AS (
            SELECT team_a_id AS team_id FROM season_matches
            UNION SELECT team_b_id AS team_id FROM season_matches
        )
        SELECT
            (SELECT COUNT(*) FROM season_matches) AS matches,
            (SELECT COUNT(*) FROM participants WHERE team_id IS NOT NULL) AS teams,
            (SELECT COUNT(DISTINCT venue_id) FROM season_matches WHERE venue_id IS NOT NULL) AS venues,
            COALESCE(SUM(i.total_runs), 0) AS runs,
            COALESCE(SUM(i.total_wickets), 0) AS wickets,
            MAX(i.total_runs) AS highest_total,
            ROUND(AVG(CASE WHEN i.innings_number = 1 THEN i.total_runs END), 2) AS avg_first_innings
        FROM innings i
        JOIN season_matches sm ON sm.id = i.match_id
    """), params).fetchone()

    champion = db.execute(text("""
        SELECT t.id, t.canonical_name AS name
        FROM matches m JOIN teams t ON t.id = m.winner_id
        WHERE m.season_id = :season_id AND m.winner_id IS NOT NULL
        ORDER BY m.match_date DESC, m.event_match_number DESC
        LIMIT 1
    """), params).fetchone()

    teams = db.execute(text("""
        WITH appearances AS (
            SELECT team_a_id AS team_id, winner_id, result_type FROM matches WHERE season_id = :season_id
            UNION ALL
            SELECT team_b_id AS team_id, winner_id, result_type FROM matches WHERE season_id = :season_id
        )
        SELECT t.id, t.canonical_name AS name, t.short_name, t.country,
               COUNT(*) AS matches,
               SUM(CASE WHEN a.winner_id = a.team_id THEN 1 ELSE 0 END) AS wins,
               SUM(CASE WHEN a.result_type = 'win' AND a.winner_id <> a.team_id THEN 1 ELSE 0 END) AS losses,
               SUM(CASE WHEN a.result_type = 'tie' THEN 1 ELSE 0 END) AS ties,
               SUM(CASE WHEN a.result_type IN ('no_result', 'abandoned') THEN 1 ELSE 0 END) AS no_results,
               ROUND(100.0 * SUM(CASE WHEN a.winner_id = a.team_id THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) AS win_rate
        FROM appearances a JOIN teams t ON t.id = a.team_id
        GROUP BY t.id, t.canonical_name, t.short_name, t.country
        ORDER BY wins DESC, win_rate DESC, matches DESC, name
    """), params).fetchall()

    top_batters = db.execute(text("""
        SELECT p.id, p.canonical_name AS name, p.full_name,
               COALESCE(NULLIF(p.country, ''), t.canonical_name) AS country,
               s.matches, s.batting_innings AS innings, s.not_outs, s.runs,
               s.balls_faced, s.fours, s.sixes, s.highest_score,
               s.fifties, s.hundreds,
               ROUND(1.0 * s.runs / NULLIF(s.batting_innings - s.not_outs, 0), 2) AS average,
               ROUND(100.0 * s.runs / NULLIF(s.balls_faced, 0), 2) AS strike_rate
        FROM season_player_stats s JOIN players p ON p.id = s.player_id
        LEFT JOIN teams t ON t.id = p.team_id
        WHERE s.season_id = :season_id AND s.batting_innings > 0
        ORDER BY s.runs DESC, average DESC LIMIT 10
    """), params).fetchall()

    top_bowlers = db.execute(text("""
        SELECT p.id, p.canonical_name AS name, p.full_name,
               COALESCE(NULLIF(p.country, ''), t.canonical_name) AS country,
               s.matches, s.bowling_innings AS innings, s.wickets,
               s.balls_bowled, s.runs_conceded, s.maidens,
               s.best_wickets, s.best_runs,
               ROUND(1.0 * s.runs_conceded / NULLIF(s.wickets, 0), 2) AS average,
               ROUND(6.0 * s.runs_conceded / NULLIF(s.balls_bowled, 0), 2) AS economy
        FROM season_player_stats s JOIN players p ON p.id = s.player_id
        LEFT JOIN teams t ON t.id = p.team_id
        WHERE s.season_id = :season_id AND s.bowling_innings > 0
        ORDER BY s.wickets DESC, average ASC LIMIT 10
    """), params).fetchall()

    matches = db.execute(text("""
        SELECT m.id, m.match_date, m.format, m.result_type, m.win_margin, m.win_type,
               ta.canonical_name AS team_a, tb.canonical_name AS team_b,
               tw.canonical_name AS winner, v.name AS venue,
               c.name AS competition_name, s.name AS season_name
        FROM matches m
        LEFT JOIN teams ta ON ta.id = m.team_a_id
        LEFT JOIN teams tb ON tb.id = m.team_b_id
        LEFT JOIN teams tw ON tw.id = m.winner_id
        LEFT JOIN venues v ON v.id = m.venue_id
        JOIN competitions c ON c.id = m.competition_id
        JOIN seasons s ON s.id = m.season_id
        WHERE m.season_id = :season_id
        ORDER BY m.match_date DESC, m.event_match_number DESC
        LIMIT 100
    """), params).fetchall()

    venues = db.execute(text("""
        SELECT v.id, v.name, v.city, v.country, COUNT(DISTINCT m.id) AS matches,
               ROUND(AVG(CASE WHEN i.innings_number = 1 THEN i.total_runs END), 1) AS avg_first_innings,
               MAX(i.total_runs) AS highest_total
        FROM matches m JOIN venues v ON v.id = m.venue_id
        LEFT JOIN innings i ON i.match_id = m.id
        WHERE m.season_id = :season_id
        GROUP BY v.id, v.name, v.city, v.country
        ORDER BY matches DESC, avg_first_innings DESC
    """), params).fetchall()

    def player_rows(source):
        result = []
        for row in source:
            item = dict(row._mapping)
            item["id"] = str(item["id"])
            item["image_url"] = get_player_image_url(item.get("name"), item.get("full_name"), item["id"])
            result.append(item)
        return result

    match_rows = []
    for row in matches:
        item = dict(row._mapping)
        item["id"] = str(item["id"])
        item["result"] = _result_text(item)
        match_rows.append(item)
    _attach_scores(db, match_rows)

    competition_data = dict(competition._mapping)
    competition_data["id"] = str(competition_data["id"])
    selected["id"] = sid
    for row in season_rows:
        row["id"] = str(row["id"])

    return {
        "competition": competition_data,
        "season": selected,
        "seasons": season_rows,
        "overview": dict(overview._mapping) if overview else {},
        "champion": ({**dict(champion._mapping), "id": str(champion.id)} if champion else None),
        "teams": [{**dict(row._mapping), "id": str(row.id)} for row in teams],
        "top_batters": player_rows(top_batters),
        "top_bowlers": player_rows(top_bowlers),
        "matches": match_rows,
        "venues": [{**dict(row._mapping), "id": str(row.id)} for row in venues],
        "generated_through": date.today().isoformat(),
    }
