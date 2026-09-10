"""Remove reconstructed validation matches from the serving database.

The historical corpus is made up of numeric Cricsheet match identifiers.
During early format validation, 18 descriptive fixture files were generated in
the production raw-data directories and were subsequently ingested.  Those
matches are useful test inputs, but they must not contribute to public career,
team, venue, or match totals.

Fixtures now live under ``data/raw/fixtures``.  This command removes their
known database rows and reconciles aggregates that can be computed from the
official match and innings tables.  It is a dry run unless ``--apply`` is used.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "cricket_intelligence.db"

RECONSTRUCTED_IDS = {
    "471345_od_final_2023",
    "471346_ind_vs_eng_2023",
    "471347_wc_final_2019",
    "471348_afg_vs_zim_2023",
    "471349_ct_final_2017",
    "471350_sl_vs_sa_2023",
    "471351_ban_vs_wi_2022",
    "471352_asia_cup_2023",
    "t20i_asia_cup2022_ind_vs_pak",
    "t20i_bilateral_aus_vs_sa_2023",
    "t20i_wc2022_final_eng_vs_pak",
    "t20i_wc2024_final_ind_vs_aus",
    "t20i_wc2024_sf_ind_vs_eng",
    "test_match_8wickets",
    "test_match_declaration",
    "test_match_draw",
    "test_match_innings_victory",
    "test_match_normal",
}


def _reconcile_team_performance(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        WITH appearances AS (
            SELECT team_a_id AS team_id, format, winner_id, result_type
            FROM matches WHERE team_a_id IS NOT NULL
            UNION ALL
            SELECT team_b_id AS team_id, format, winner_id, result_type
            FROM matches WHERE team_b_id IS NOT NULL
        ), records AS (
            SELECT team_id, format,
                   COUNT(*) AS matches,
                   SUM(CASE WHEN winner_id = team_id THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN result_type = 'win' AND winner_id <> team_id THEN 1 ELSE 0 END) AS losses,
                   SUM(CASE WHEN result_type = 'tie' THEN 1 ELSE 0 END) AS ties,
                   SUM(CASE WHEN result_type IN ('draw', 'no_result') THEN 1 ELSE 0 END) AS no_results
            FROM appearances GROUP BY team_id, format
        ), batting AS (
            SELECT i.batting_team_id AS team_id, m.format,
                   AVG(CASE WHEN i.innings_number = 1 THEN i.total_runs END) AS first_avg,
                   AVG(CASE WHEN i.innings_number = 2 THEN i.total_runs END) AS second_avg,
                   AVG(i.total_runs) AS total_avg
            FROM innings i JOIN matches m ON m.id = i.match_id
            WHERE i.batting_team_id IS NOT NULL
            GROUP BY i.batting_team_id, m.format
        ), bowling AS (
            SELECT i.bowling_team_id AS team_id, m.format,
                   AVG(i.total_runs) AS conceded_avg,
                   AVG(i.total_wickets) AS wickets_avg
            FROM innings i JOIN matches m ON m.id = i.match_id
            WHERE i.bowling_team_id IS NOT NULL
            GROUP BY i.bowling_team_id, m.format
        )
        SELECT r.team_id, r.format, r.matches, r.wins, r.losses, r.ties, r.no_results,
               b.first_avg, b.second_avg, b.total_avg, w.conceded_avg, w.wickets_avg
        FROM records r
        LEFT JOIN batting b ON b.team_id = r.team_id AND b.format = r.format
        LEFT JOIN bowling w ON w.team_id = r.team_id AND w.format = r.format
        """
    ).fetchall()

    now = datetime.now(timezone.utc).isoformat()
    for row in rows:
        (team_id, match_format, matches, wins, losses, ties, no_results,
         first_avg, second_avg, total_avg, conceded_avg, wickets_avg) = row
        win_rate = round(100.0 * wins / matches, 2) if matches else 0.0
        existing = conn.execute(
            """SELECT batting_strength_score, bowling_strength_score
               FROM team_performance
               WHERE team_id = ? AND format = ? AND period = 'career'""",
            (team_id, match_format),
        ).fetchone()
        batting_strength = existing[0] if existing else None
        bowling_strength = existing[1] if existing else None
        components = [value for value in (batting_strength, bowling_strength) if value is not None]
        if len(components) == 2:
            overall = round(0.35 * batting_strength + 0.35 * bowling_strength + 0.30 * win_rate, 2)
        elif components:
            overall = round(0.70 * components[0] + 0.30 * win_rate, 2)
        else:
            overall = win_rate

        conn.execute(
            """INSERT INTO team_performance
               (id, team_id, format, period, matches, wins, losses, win_rate,
                avg_first_innings_score, avg_second_innings_score,
                batting_strength_score, bowling_strength_score,
                overall_strength_score, ties, no_results, avg_total_score,
                avg_runs_conceded_per_innings, avg_wickets_per_innings,
                calculated_at)
               VALUES (lower(hex(randomblob(16))), ?, ?, 'career', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(team_id, format, period) DO UPDATE SET
                 matches=excluded.matches, wins=excluded.wins,
                 losses=excluded.losses, win_rate=excluded.win_rate,
                 avg_first_innings_score=excluded.avg_first_innings_score,
                 avg_second_innings_score=excluded.avg_second_innings_score,
                 overall_strength_score=excluded.overall_strength_score,
                 ties=excluded.ties, no_results=excluded.no_results,
                 avg_total_score=excluded.avg_total_score,
                 avg_runs_conceded_per_innings=excluded.avg_runs_conceded_per_innings,
                 avg_wickets_per_innings=excluded.avg_wickets_per_innings,
                 calculated_at=excluded.calculated_at""",
            (
                team_id, match_format, matches, wins, losses, win_rate,
                first_avg, second_avg, batting_strength, bowling_strength,
                overall, ties, no_results, total_avg, conceded_avg,
                wickets_avg, now,
            ),
        )

    conn.execute(
        """DELETE FROM team_performance
           WHERE period = 'career' AND NOT EXISTS (
             SELECT 1 FROM matches m
             WHERE m.format = team_performance.format
               AND (m.team_a_id = team_performance.team_id
                    OR m.team_b_id = team_performance.team_id)
           )"""
    )


def _reconcile_venue_stats(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        WITH venue_matches AS (
            SELECT venue_id, format,
                   COUNT(*) AS total_matches,
                   SUM(CASE WHEN win_type = 'wickets' THEN 1 ELSE 0 END) AS chasing_wins,
                   SUM(CASE WHEN win_type = 'runs' THEN 1 ELSE 0 END) AS defending_wins,
                   SUM(CASE WHEN toss_decision = 'bat' AND toss_winner_id = winner_id THEN 1 ELSE 0 END) AS toss_bat_wins,
                   SUM(CASE WHEN toss_decision = 'field' AND toss_winner_id = winner_id THEN 1 ELSE 0 END) AS toss_field_wins,
                   SUM(CASE WHEN toss_decision = 'bat' THEN 1 ELSE 0 END) AS toss_bat_matches,
                   SUM(CASE WHEN toss_decision = 'field' THEN 1 ELSE 0 END) AS toss_field_matches
            FROM matches WHERE venue_id IS NOT NULL GROUP BY venue_id, format
        ), innings_stats AS (
            SELECT m.venue_id, m.format,
                   AVG(CASE WHEN i.innings_number = 1 THEN i.total_runs END) AS first_avg,
                   AVG(CASE WHEN i.innings_number = 2 THEN i.total_runs END) AS second_avg,
                   MAX(i.total_runs) AS highest_total,
                   MIN(CASE WHEN i.total_runs > 0 THEN i.total_runs END) AS lowest_total
            FROM matches m JOIN innings i ON i.match_id = m.id
            WHERE m.venue_id IS NOT NULL GROUP BY m.venue_id, m.format
        )
        SELECT v.venue_id, v.format, v.total_matches, i.first_avg, i.second_avg,
               i.highest_total, i.lowest_total, v.chasing_wins, v.defending_wins,
               v.toss_bat_wins, v.toss_field_wins, v.toss_bat_matches, v.toss_field_matches
        FROM venue_matches v
        LEFT JOIN innings_stats i ON i.venue_id = v.venue_id AND i.format = v.format
        """
    ).fetchall()

    now = datetime.now(timezone.utc).isoformat()
    for row in rows:
        (venue_id, match_format, total, first_avg, second_avg, highest, lowest,
         chasing, defending, toss_bat_wins, toss_field_wins,
         toss_bat_matches, toss_field_matches) = row
        decided = chasing + defending
        chasing_pct = round(100.0 * chasing / decided, 2) if decided else None
        defending_pct = round(100.0 * defending / decided, 2) if decided else None
        toss_bat_pct = round(100.0 * toss_bat_wins / toss_bat_matches, 2) if toss_bat_matches else None
        toss_field_pct = round(100.0 * toss_field_wins / toss_field_matches, 2) if toss_field_matches else None
        conn.execute(
            """INSERT INTO venue_stats
               (id, venue_id, format, total_matches, avg_first_innings_score,
                avg_second_innings_score, highest_total, lowest_total,
                chasing_wins, defending_wins, chasing_win_pct,
                defending_win_pct, toss_bat_first_win_pct,
                toss_field_first_win_pct, calculated_at)
               VALUES (lower(hex(randomblob(16))), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(venue_id, format) DO UPDATE SET
                 total_matches=excluded.total_matches,
                 avg_first_innings_score=excluded.avg_first_innings_score,
                 avg_second_innings_score=excluded.avg_second_innings_score,
                 highest_total=excluded.highest_total,
                 lowest_total=excluded.lowest_total,
                 chasing_wins=excluded.chasing_wins,
                 defending_wins=excluded.defending_wins,
                 chasing_win_pct=excluded.chasing_win_pct,
                 defending_win_pct=excluded.defending_win_pct,
                 toss_bat_first_win_pct=excluded.toss_bat_first_win_pct,
                 toss_field_first_win_pct=excluded.toss_field_first_win_pct,
                 calculated_at=excluded.calculated_at""",
            (
                venue_id, match_format, total, first_avg, second_avg, highest,
                lowest, chasing, defending, chasing_pct, defending_pct,
                toss_bat_pct, toss_field_pct, now,
            ),
        )

    conn.execute(
        """DELETE FROM venue_stats
           WHERE NOT EXISTS (
             SELECT 1 FROM matches m
             WHERE m.venue_id = venue_stats.venue_id
               AND m.format = venue_stats.format
           )"""
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    database = args.database.resolve()
    with sqlite3.connect(database) as conn:
        placeholders = ",".join("?" for _ in RECONSTRUCTED_IDS)
        rows = conn.execute(
            f"""SELECT id, external_id, format FROM matches
                WHERE external_id IN ({placeholders}) ORDER BY format, external_id""",
            tuple(sorted(RECONSTRUCTED_IDS)),
        ).fetchall()
        print(f"Found {len(rows)} reconstructed matches")
        for _, external_id, match_format in rows:
            print(f"  {match_format}: {external_id}")

        if not args.apply:
            print("Dry run only; pass --apply to purge and reconcile aggregates.")
            return

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = database.with_name(f"{database.stem}.pre-fixture-purge-{timestamp}{database.suffix}")
    shutil.copy2(database, backup)

    with sqlite3.connect(database) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        match_ids = [row[0] for row in rows]
        if match_ids:
            match_placeholders = ",".join("?" for _ in match_ids)
            for table in ("match_batting_summary", "match_bowling_summary", "deliveries", "innings"):
                conn.execute(
                    f"DELETE FROM {table} WHERE match_id IN ({match_placeholders})",
                    match_ids,
                )
            conn.execute(
                f"DELETE FROM matches WHERE id IN ({match_placeholders})",
                match_ids,
            )
        _reconcile_team_performance(conn)
        _reconcile_venue_stats(conn)
        conn.commit()

        counts = dict(conn.execute("SELECT format, COUNT(*) FROM matches GROUP BY format"))
        remaining = conn.execute(
            f"SELECT COUNT(*) FROM matches WHERE external_id IN ({placeholders})",
            tuple(sorted(RECONSTRUCTED_IDS)),
        ).fetchone()[0]

    print(f"Backup: {backup}")
    print(f"Purged: {len(rows)}; remaining reconstructed rows: {remaining}")
    print("Official match counts: " + ", ".join(f"{key}={value:,}" for key, value in sorted(counts.items())))


if __name__ == "__main__":
    main()
