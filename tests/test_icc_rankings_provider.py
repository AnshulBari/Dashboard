import httpx

from backend.providers.icc_rankings import ICCRankingsProvider


def _provider_with_snapshot(monkeypatch):
    snapshot = {
        "batting": {
            "rank_date": "2026-09-08",
            "entries": [
                {
                    "no": "1",
                    "change": "(+2)",
                    "Player-name": "Example Batter",
                    "Player_id": "100",
                    "Country_name": "India",
                    "Points": "850",
                    "careerbest": "900 v Australia",
                },
                {
                    "no": "=",
                    "change": "(-1)",
                    "Player-name": "Tied Batter",
                    "Player_id": "101",
                    "Country_name": "England",
                    "Points": "850",
                },
            ],
        },
        "teams": {
            "rank_date": "2026-09-10",
            "entries": [
                {
                    "no": "1",
                    "team_name": "Australia",
                    "team_id": "1",
                    "Rating": "126",
                    "Matches": "27",
                    "Points": "3,411",
                    "change": "( - )",
                }
            ],
        },
    }
    provider = ICCRankingsProvider()

    def fail_request(*_args, **_kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(provider, "_request", fail_request)
    monkeypatch.setattr(provider, "_snapshot", lambda _format, category: (
        setattr(provider, "_last_source", "icc-official-snapshot") or snapshot[category]
    ))
    return provider


def test_official_player_snapshot_preserves_ratings_and_ties(monkeypatch):
    provider = _provider_with_snapshot(monkeypatch)
    rows = provider.get_player_rankings("Test", "batting")

    assert [row.rank for row in rows] == [1, 1]
    assert rows[0].rating == 850
    assert rows[0].change == 2
    assert rows[0].career_best == "900 v Australia"
    assert rows[0].ranking_date == "2026-09-08"
    assert rows[0].source == "icc-official-snapshot"


def test_official_team_snapshot_keeps_icc_matches_points_and_rating(monkeypatch):
    provider = _provider_with_snapshot(monkeypatch)
    row = provider.get_team_rankings("Test")[0]

    assert row.team_name == "Australia"
    assert row.rating == 126
    assert row.matches == 27
    assert row.points == 3411
    assert row.ranking_date == "2026-09-10"
