"""Focused offline regressions for backend correctness fixes."""

import asyncio
from datetime import date

import pandas as pd
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models import entities  # noqa: F401
from backend.providers.cricketdata import CricketDataProvider, MockCricketDataProvider
from backend.services.live import LiveService
from backend.utils.database import Base
from backend.utils.player_images import get_player_image_url
from backend.utils.stat_invariants import sanitize_stat_record
from data_pipeline.pipeline.analytics import (
    compute_matchups,
    compute_player_batting_stats,
    compute_player_bowling_stats,
    compute_player_form_scores,
    compute_team_performance,
)
from data_pipeline.pipeline.reader import flatten_match, normalize_result_type
from data_pipeline.pipeline.player_identity import normalize_player_names
from data_pipeline.pipeline.scorecards import compute_scorecard_from_json
from data_pipeline.pipeline.impact import compute_impact_scores_from_aggregates


def test_player_image_resolver_uses_register_identity_and_rejects_unknown_names():
    assert get_player_image_url("JE Root") == (
        "https://a.espncdn.com/i/headshots/cricket/players/full/303669.png"
    )
    assert get_player_image_url("Joe Root") == (
        "https://a.espncdn.com/i/headshots/cricket/players/full/303669.png"
    )
    assert get_player_image_url("Definitely Not A Registered Cricketer") is None


def test_serving_guard_repairs_impossible_stat_relationships():
    record = sanitize_stat_record({
        "innings": 4,
        "not_outs": -2,
        "runs": 100,
        "batting_average": -50,
        "strike_rate": -10,
        "total_balls": 6,
        "dot_balls": 8,
        "boundaries": -1,
        "total_wickets": 9,
        "boundary_pct": 120,
    })

    assert record["not_outs"] == 0
    assert record["batting_average"] == 25.0
    assert record["strike_rate"] == 0
    assert record["dot_balls"] == 6
    assert record["boundaries"] == 0
    assert record["total_wickets"] == 6
    assert record["boundary_pct"] == 100


def test_impact_rebuild_does_not_preserve_prior_only_aliases():
    prior = pd.DataFrame([{
        "player_id": "stale-alias", "format": "Test", "form_score": 99.0,
    }])
    batting = pd.DataFrame([{
        "player_id": "canonical", "format": "Test", "period": "career",
        "matches": 1, "innings": 1, "runs": 50, "balls_faced": 100,
        "batting_average": 50.0, "strike_rate": 50.0,
    }])

    result = compute_impact_scores_from_aggregates(
        prior, batting, pd.DataFrame(), pd.DataFrame()
    )

    assert result[["player_id", "format"]].to_dict("records") == [
        {"player_id": "canonical", "format": "Test"}
    ]


def _delivery_rows() -> pd.DataFrame:
    common = {
        "match_id": "m1",
        "match_date": "2025-01-01",
        "format": "T20",
        "innings_number": 1,
        "over_number": 0,
        "batter": "Batter",
        "bowler": "Bowler",
        "batting_team": "Batters",
        "bowling_team": "Bowlers",
        "venue": "Ground",
        "winner": "Batters",
        "result_type": "win",
        "dismissed_player": "",
        "wicket_type": "",
        "is_wicket": False,
    }
    events = [
        # Wides are neither balls faced nor legal balls.
        dict(ball_in_over=1, runs_batter=0, runs_extras=2, runs_total=2,
             extra_type="wide", extras_wides=2, extras_noballs=0),
        # No-balls are faced by the batter but are not legal balls.
        dict(ball_in_over=2, runs_batter=4, runs_extras=1, runs_total=5,
             extra_type="noball", extras_wides=0, extras_noballs=1),
        # Byes and leg-byes are legal but are not charged to the bowler.
        dict(ball_in_over=3, runs_batter=0, runs_extras=3, runs_total=3,
             extra_type="bye", extras_wides=0, extras_noballs=0),
        dict(ball_in_over=4, runs_batter=0, runs_extras=2, runs_total=2,
             extra_type="legbye", extras_wides=0, extras_noballs=0),
        # Run-outs do not belong in the bowler's wicket tally.
        dict(ball_in_over=5, runs_batter=0, runs_extras=0, runs_total=0,
             extra_type=None, extras_wides=0, extras_noballs=0,
             is_wicket=True, wicket_type="run out", dismissed_player="Non-striker"),
        dict(ball_in_over=6, runs_batter=0, runs_extras=0, runs_total=0,
             extra_type=None, extras_wides=0, extras_noballs=0,
             is_wicket=True, wicket_type="bowled", dismissed_player="Batter"),
    ]
    return pd.DataFrame([{**common, **event} for event in events])


def test_pandas_cricket_scoring_rules():
    deliveries = _delivery_rows()

    batting = compute_player_batting_stats(deliveries).iloc[0]
    assert batting["runs"] == 4
    assert batting["balls_faced"] == 5
    assert batting["dot_balls"] == 2
    assert batting["not_outs"] == 0
    assert batting["highest_score"] == 4

    bowling = compute_player_bowling_stats(deliveries).iloc[0]
    assert bowling["balls_bowled"] == 4
    assert bowling["runs_conceded"] == 7
    assert bowling["wickets"] == 1
    assert bowling["dot_balls"] == 2
    assert bowling["economy"] == 10.5

    matchup = compute_matchups(deliveries, min_balls=1).iloc[0]
    assert matchup["total_balls"] == 5
    assert matchup["total_wickets"] == 1


def test_non_striker_run_out_counts_as_the_dismissed_players_out():
    rows = [
        {
            **_delivery_rows().iloc[1].to_dict(),
            "batter": "Striker",
            "non_striker": "Runner",
            "ball_in_over": 1,
            "runs_batter": 1,
            "runs_total": 1,
            "is_wicket": True,
            "wicket_type": "run out",
            "dismissed_player": "Runner",
        },
        {
            **_delivery_rows().iloc[1].to_dict(),
            "ball_in_over": 2,
            "batter": "Runner",
            "non_striker": "Striker",
            "runs_batter": 2,
            "runs_total": 2,
            "is_wicket": False,
            "wicket_type": "",
            "dismissed_player": "",
        },
    ]
    stats = compute_player_batting_stats(pd.DataFrame(rows)).set_index("player_name")

    assert stats.loc["Runner", "innings"] == 1
    assert stats.loc["Runner", "not_outs"] == 0
    assert stats.loc["Striker", "not_outs"] == 1


def test_json_scorecard_attributes_non_striker_run_out():
    batting, _ = compute_scorecard_from_json({
        "innings": [{"overs": [{"over": 0, "deliveries": [
            {
                "batter": "Runner", "non_striker": "Striker", "bowler": "Bowler",
                "runs": {"batter": 1, "extras": 0, "total": 1},
            },
            {
                "batter": "Striker", "non_striker": "Runner", "bowler": "Bowler",
                "runs": {"batter": 0, "extras": 0, "total": 0},
                "wickets": [{"kind": "run out", "player_out": "Runner"}],
            },
        ]}]}],
    })

    assert batting[(0, "Runner")]["is_not_out"] is False
    assert batting[(0, "Striker")]["is_not_out"] is True


def test_all_run_fours_are_not_counted_as_boundaries():
    row = _delivery_rows().iloc[[0]].copy()
    row["extra_type"] = None
    row["extras_wides"] = 0
    row["runs_batter"] = 4
    row["runs_extras"] = 0
    row["runs_total"] = 4
    row["non_boundary"] = True

    assert compute_player_batting_stats(row).iloc[0]["fours"] == 0
    assert compute_player_bowling_stats(row).iloc[0]["boundaries_conceded"] == 0
    assert compute_matchups(row, min_balls=1).iloc[0]["boundaries"] == 0

    batting, _ = compute_scorecard_from_json({
        "innings": [{"overs": [{"over": 0, "deliveries": [{
            "batter": "Batter", "bowler": "Bowler", "non_striker": "Partner",
            "runs": {"batter": 4, "extras": 0, "total": 4, "non_boundary": True},
        }]}]}],
    })
    assert batting[(0, "Batter")]["fours"] == 0


def test_cricsheet_outcomes_are_normalized_from_result_field():
    assert normalize_result_type({"winner": "India"}) == "win"
    assert normalize_result_type({"result": "tie", "eliminator": "India"}) == "tie"
    assert normalize_result_type({"result": "draw"}) == "draw"
    assert normalize_result_type({"result": "no result"}) == "no_result"

    rows = flatten_match({
        "info": {
            "dates": ["2025-01-01"],
            "match_type": "T20",
            "teams": ["A", "B"],
            "outcome": {"result": "no result"},
        },
        "innings": [{
            "team": "A",
            "overs": [{"over": 0, "deliveries": [{
                "batter": "Batter", "bowler": "Bowler", "non_striker": "Partner",
                "runs": {"batter": 0, "extras": 0, "total": 0},
            }]}],
        }],
    }, "match.json")
    assert rows[0]["result_type"] == "no_result"


def test_player_aliases_are_canonicalized_in_every_source_column():
    frame = pd.DataFrame({
        "batter": ["V Kohli"],
        "bowler": ["RG Sharma"],
        "non_striker": ["JE Root"],
        "player_of_match": ["V Kohli"],
        "team_a_players": ["V Kohli,RG Sharma"],
    })
    normalized = normalize_player_names(frame).iloc[0]
    assert normalized["batter"] == "Virat Kohli"
    assert normalized["bowler"] == "Rohit Sharma"
    assert normalized["non_striker"] == "Joe Root"
    assert normalized["player_of_match"] == "Virat Kohli"
    assert normalized["team_a_players"] == "Virat Kohli,Rohit Sharma"


def test_validation_keeps_long_test_innings_but_rejects_impossible_t20_overs():
    from data_pipeline.pipeline.run import CricketPipeline

    base = _delivery_rows().iloc[0].to_dict()
    long_test = {**base, "format": "Test", "over_number": 125}
    invalid_t20 = {**base, "match_id": "m2", "format": "T20", "over_number": 125}
    pipeline = CricketPipeline(database_url="sqlite:///:memory:")
    validated = pipeline.validate(pd.DataFrame([long_test, invalid_t20]))
    assert validated["match_id"].tolist() == ["m1"]
    pipeline.db.close()


def test_player_impact_records_the_latest_real_appearance_date():
    base = _delivery_rows().iloc[1].to_dict()
    rows = [
        {**base, "match_id": f"m{index}", "match_date": match_date}
        for index, match_date in enumerate(
            ("2025-01-01", "2025-06-01", "2026-02-14"), start=1
        )
    ]
    impact = compute_player_form_scores(pd.DataFrame(rows)).iloc[0]
    assert str(impact["last_match_date"]) == "2026-02-14"
    assert 0 <= impact["form_score"] <= 100  # Legacy storage column.


def test_ties_are_not_losses_and_chase_defence_rates_are_independent():
    base = {
        "format": "T20", "venue": "Ground", "over_number": 0,
        "ball_in_over": 1, "runs_batter": 1, "runs_extras": 0,
        "runs_total": 1, "extra_type": None, "is_wicket": False,
        "wicket_type": "", "dismissed_player": "",
    }
    rows = [
        {**base, "match_id": "win", "innings_number": 1, "batting_team": "A",
         "bowling_team": "B", "winner": "B", "result_type": "win"},
        {**base, "match_id": "win", "innings_number": 2, "batting_team": "B",
         "bowling_team": "A", "winner": "B", "result_type": "win"},
        {**base, "match_id": "tie", "innings_number": 1, "batting_team": "A",
         "bowling_team": "B", "winner": "", "result_type": "tie"},
        {**base, "match_id": "tie", "innings_number": 2, "batting_team": "B",
         "bowling_team": "A", "winner": "", "result_type": "tie"},
    ]
    result = compute_team_performance(pd.DataFrame(rows)).set_index("team_name")
    assert result.loc["A", "losses"] == 1
    assert result.loc["A", "ties"] == 1
    assert result.loc["B", "losses"] == 0
    assert result.loc["B", "ties"] == 1
    assert result.loc["A", "defending_win_pct"] == 0
    assert result.loc["B", "chasing_win_pct"] == 100


def test_json_scorecard_uses_legal_balls_and_bowler_charged_runs():
    deliveries = []
    for row in _delivery_rows().to_dict("records"):
        extras = {}
        if row["extra_type"] == "wide":
            extras["wides"] = row["runs_extras"]
        elif row["extra_type"] == "noball":
            extras["noballs"] = row["runs_extras"]
        elif row["extra_type"] == "bye":
            extras["byes"] = row["runs_extras"]
        elif row["extra_type"] == "legbye":
            extras["legbyes"] = row["runs_extras"]
        delivery = {
            "batter": row["batter"],
            "bowler": row["bowler"],
            "non_striker": "Non-striker",
            "runs": {
                "batter": row["runs_batter"],
                "extras": row["runs_extras"],
                "total": row["runs_total"],
            },
        }
        if extras:
            delivery["extras"] = extras
        if row["is_wicket"]:
            delivery["wickets"] = [{
                "kind": row["wicket_type"],
                "player_out": row["dismissed_player"],
            }]
        deliveries.append(delivery)

    batting, bowling = compute_scorecard_from_json({
        "innings": [{"team": "Batters", "overs": [{"over": 0, "deliveries": deliveries}]}]
    })
    assert batting[(0, "Batter")]["balls"] == 5
    assert bowling[(0, "Bowler")]["balls"] == 4
    assert bowling[(0, "Bowler")]["runs"] == 7
    assert bowling[(0, "Bowler")]["wickets"] == 1
    assert bowling[(0, "Bowler")]["wides"] == 2


def test_json_scorecard_calculates_completed_maiden_overs():
    deliveries = [{
        "batter": "Batter", "bowler": "Bowler", "non_striker": "Partner",
        "runs": {"batter": 0, "extras": 0, "total": 0},
    } for _ in range(6)]
    _, bowling = compute_scorecard_from_json({
        "info": {"balls_per_over": 6},
        "innings": [{"overs": [{"over": 0, "deliveries": deliveries}]}],
    })
    assert bowling[(0, "Bowler")]["maidens"] == 1


def test_live_response_preserves_old_key_and_exposes_client_data_key():
    result = LiveService(MockCricketDataProvider()).get_live_matches()
    assert result["data"] == result["matches"]
    assert result["total"] == len(result["data"])


def test_provider_parses_current_cricketdata_shape_and_scorecard_endpoint():
    provider = CricketDataProvider(api_key="test")
    calls = []

    def fake_request(endpoint, params=None):
        calls.append((endpoint, params))
        return {
            "data": {
                "id": "match-1",
                "teams": ["India", "Australia"],
                "matchType": "odi",
                "matchStarted": True,
                "matchEnded": False,
                "status": "India are batting",
                "score": [
                    {"r": 250, "w": 8, "o": 50, "inning": "Australia Inning 1"},
                    {"r": 125, "w": 2, "o": 24.1, "inning": "India Inning 1"},
                ],
            }
        }

    provider._make_request = fake_request
    matches = provider.get_live_matches()
    assert matches[0].match_id == "match-1"
    assert matches[0].team_a == "India"
    assert matches[0].score_team_a == "125/2 (24.1 ov)"
    assert matches[0].score_team_b == "250/8 (50 ov)"

    detail = provider.get_match_detail("match-1")
    assert calls[-1] == ("match_scorecard", {"id": "match-1"})
    assert detail.batting_team == "India"
    assert detail.current_score == "125/2 (24.1 ov)"


def test_models_create_cleanly_on_sqlite():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    tables = set(inspect(engine).get_table_names())
    assert {"teams", "players", "matches", "match_batting_summary", "match_bowling_summary"} <= tables


def test_scorecard_replacement_rolls_back_if_generation_fails():
    from backend.models.entities import (
        Competition,
        Innings,
        Match,
        MatchBattingSummary,
        Player,
        Team,
        Venue,
    )
    from data_pipeline.pipeline.scorecards import ScorecardGenerator

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    batting_team = Team(canonical_name="Batters", short_name="BAT")
    bowling_team = Team(canonical_name="Bowlers", short_name="BWL")
    player = Player(canonical_name="Batter")
    venue = Venue(name="Ground")
    competition = Competition(name="Cup", format="T20")
    db.add_all([batting_team, bowling_team, player, venue, competition])
    db.flush()
    match = Match(
        external_id="m1", competition_id=competition.id, venue_id=venue.id,
        match_date=date(2025, 1, 1), format="T20", team_a_id=batting_team.id,
        team_b_id=bowling_team.id,
    )
    db.add(match)
    db.flush()
    innings = Innings(
        match_id=match.id, innings_number=1, batting_team_id=batting_team.id,
        bowling_team_id=bowling_team.id,
    )
    db.add(innings)
    db.flush()
    db.add(MatchBattingSummary(
        match_id=match.id, innings_id=innings.id, player_id=player.id,
        batting_team_id=batting_team.id, runs=99, balls=50,
    ))
    db.commit()

    generator = ScorecardGenerator(engine)
    generator._get_innings_id = lambda *_: (_ for _ in ()).throw(RuntimeError("boom"))
    result = generator.generate_from_json_data({
        "match_id": "m1",
        "innings": [{"overs": [{"over": 0, "deliveries": [{
            "batter": "Batter", "bowler": "Bowler", "runs": {"batter": 1, "total": 1}
        }]}]}],
    })
    assert result["status"] == "FAILED"
    preserved = db.query(MatchBattingSummary).filter_by(match_id=match.id).one()
    assert preserved.runs == 99
    db.close()


class _Result:
    def __init__(self, scalar_value=0, rows=()):
        self.scalar_value = scalar_value
        self.rows = rows

    def scalar(self):
        return self.scalar_value

    def fetchall(self):
        return list(self.rows)


class _RecordingDB:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        return _Result(scalar_value=3)


def test_player_sorting_uses_public_career_wickets_alias():
    from backend.routes.players import list_players

    db = _RecordingDB()
    asyncio.run(list_players(
        format="T20", role=None, country=None, sort_by="career_wickets",
        sort_order="desc", limit=10, offset=0, db=db,
    ))
    assert "ORDER BY pws.wickets DESC" in db.calls[-1][0]


def test_player_search_includes_registered_source_aliases():
    from backend.routes.players import list_players

    db = _RecordingDB()
    asyncio.run(list_players(
        format=None, role=None, country=None, search="V Kohli",
        sort_by="impact_score", sort_order="desc", limit=10, offset=0, db=db,
    ))
    sql = "\n".join(statement for statement, _ in db.calls)
    assert "player_name_mappings" in sql
    assert any(params.get("search") == "%v kohli%" for _, params in db.calls)


def test_recent_full_member_leaderboard_uses_windowed_stats():
    from backend.routes.players import list_players
    from backend.utils.validation import FULL_MEMBER_TEAMS

    db = _RecordingDB()
    asyncio.run(list_players(
        format=None, role=None, country=None, search=None,
        sort_by="career_runs", sort_order="desc", limit=10, offset=0,
        full_members_only=True, recent_only=True, db=db,
    ))
    sql = "\n".join(statement for statement, _ in db.calls)
    assert "player_recent_stats" in sql
    assert "MAX(last_match_date) >= :recent_cutoff" in sql
    params = db.calls[-1][1]
    assert {params[f"full_member_{index}"] for index in range(12)} == set(FULL_MEMBER_TEAMS)


def test_player_profile_uses_national_team_and_latest_active_franchise():
    from backend.routes.players import _player_display_team
    from setup import _create_sqlite_schema

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    raw = engine.raw_connection()
    _create_sqlite_schema(raw)
    raw.executescript("""
        INSERT INTO teams (id, canonical_name, short_name, country) VALUES
          ('india', 'India', 'IND', 'India'),
          ('csk', 'Chennai Super Kings', 'CSK', 'India'),
          ('rps', 'Rising Pune Supergiants', 'RPS', 'India');
        INSERT INTO players (id, canonical_name, team_id, is_active)
          VALUES ('dhoni', 'MS Dhoni', 'rps', 1);
        INSERT INTO player_team_affiliations (id, player_id, team_id, format, is_current) VALUES
          ('a1', 'dhoni', 'india', 'T20I', 1),
          ('a2', 'dhoni', 'india', 'Test', 1),
          ('a3', 'dhoni', 'csk', 'T20', 1),
          ('a4', 'dhoni', 'rps', 'T20', 1);
        INSERT INTO matches (id, external_id, match_date, format) VALUES
          ('old', 'old', '2017-05-01', 'T20'),
          ('new', 'new', '2024-05-01', 'T20');
        INSERT INTO innings (id, match_id, innings_number, batting_team_id, bowling_team_id) VALUES
          ('i1', 'old', 1, 'rps', 'csk'),
          ('i2', 'new', 1, 'csk', 'rps');
        INSERT INTO deliveries
          (id, innings_id, match_id, over_number, ball_in_over, striker_id) VALUES
          ('d1', 'i1', 'old', 0, 1, 'dhoni'),
          ('d2', 'i2', 'new', 0, 1, 'dhoni');
    """)
    raw.commit()
    raw.close()
    db = sessionmaker(bind=engine)()

    assert _player_display_team(db, "dhoni", "International", "Rising Pune Supergiants") == "India"
    assert _player_display_team(db, "dhoni", "T20", "Rising Pune Supergiants") == "Chennai Super Kings"
    db.close()


def test_core_list_filters_and_totals_work_on_sqlite():
    """Exercise the raw SQL routes against the supported local dialect."""
    from backend.models.entities import (
        Competition,
        Match,
        Team,
        TeamPerformance,
        Venue,
        VenueStats,
    )
    from backend.routes.matches import list_matches
    from backend.routes.teams import list_teams
    from backend.routes.venues import list_venues

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    india = Team(canonical_name="India", short_name="IND", country="India")
    australia = Team(canonical_name="Australia", short_name="AUS", country="Australia")
    venue = Venue(name="Test Ground", city="Mumbai", country="India")
    competition = Competition(name="Test Cup", short_name="TC", format="T20")
    db.add_all([india, australia, venue, competition])
    db.flush()
    db.add(TeamPerformance(
        team_id=india.id, format="T20", period="career", matches=1,
        wins=1, losses=0, overall_strength_score=90,
    ))
    db.add(VenueStats(venue_id=venue.id, format="T20", total_matches=1))
    db.add(Match(
        external_id="match-1", competition_id=competition.id, venue_id=venue.id,
        match_date=date(2025, 1, 1), format="T20", team_a_id=india.id,
        team_b_id=australia.id, winner_id=india.id, win_margin=5,
        win_type="runs", result_type="win",
    ))
    db.commit()

    teams = asyncio.run(list_teams(
        format="T20", sort_by="wins", sort_order="desc", limit=1, offset=0, db=db,
    ))
    assert teams["total"] == 2
    assert teams["teams"][0]["name"] == "India"

    venues = asyncio.run(list_venues(
        format="T20", country="India", limit=10, offset=0, db=db,
    ))
    assert venues["total"] == 1
    assert venues["venues"][0]["name"] == "Test Ground"

    matches = asyncio.run(list_matches(
        format="T20", competition=None, season=None, team=str(india.id),
        venue="Test Ground", limit=10, offset=0, db=db,
    ))
    assert matches["total"] == 1
    assert matches["matches"][0]["result"] == "India won by 5 runs"
    db.close()


def test_year_and_bowling_opponent_analytics_work_on_sqlite():
    from backend.models.entities import (
        Competition,
        Innings,
        Match,
        MatchBowlingSummary,
        Player,
        Team,
        Venue,
    )
    from backend.services.analytics import player_by_year, player_vs_opponent, team_by_year

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    batting_team = Team(canonical_name="India", short_name="IND")
    bowling_team = Team(canonical_name="Australia", short_name="AUS")
    bowler = Player(canonical_name="Bowler", team_id=bowling_team.id)
    venue = Venue(name="Ground")
    competition = Competition(name="Cup", format="T20")
    db.add_all([batting_team, bowling_team, bowler, venue, competition])
    db.flush()
    match = Match(
        external_id="year-match", competition_id=competition.id, venue_id=venue.id,
        match_date=date(2025, 2, 1), format="T20", team_a_id=batting_team.id,
        team_b_id=bowling_team.id, winner_id=bowling_team.id, result_type="win",
    )
    db.add(match)
    db.flush()
    innings = Innings(
        match_id=match.id, innings_number=1, batting_team_id=batting_team.id,
        bowling_team_id=bowling_team.id,
    )
    db.add(innings)
    db.flush()
    db.add(MatchBowlingSummary(
        match_id=match.id, innings_id=innings.id, player_id=bowler.id,
        bowling_team_id=bowling_team.id, balls_bowled=24, runs_conceded=20,
        wickets=2,
    ))
    db.commit()

    with engine.connect() as conn:
        # SQLAlchemy's portable Uuid type stores UUIDs without hyphens in an
        # in-memory SQLite schema; the pipeline's local schema stores strings.
        bowler_key = bowler.id.hex
        team_key = bowling_team.id.hex
        yearly = player_by_year(conn, bowler_key, "T20", batting=False)
        assert yearly[0]["year"] == 2025
        assert yearly[0]["wickets"] == 2
        assert team_by_year(conn, team_key, "T20")[0]["year"] == 2025
        opponents = player_vs_opponent(conn, bowler_key, "T20", batting=False)
        assert opponents[0]["opponent"] == "India"

    db.close()
