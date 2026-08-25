"""
Pydantic Schemas
================

Request/response models for the REST API.
Used for validation, serialization, and OpenAPI documentation.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID


# ============================================================
# Player Schemas
# ============================================================

class PlayerSummary(BaseModel):
    id: UUID
    name: str
    role: Optional[str]
    country: Optional[str]
    team_name: Optional[str]
    form_score: Optional[float]
    batting_average: Optional[float]
    strike_rate: Optional[float]
    career_runs: Optional[int]
    career_wickets: Optional[int]


class PlayerBattingCareer(BaseModel):
    matches: int
    innings: int
    runs: int
    average: float
    strike_rate: float
    fours: int
    sixes: int
    fifties: int
    hundreds: int
    highest_score: int
    balls_faced: int
    not_outs: int
    boundary_pct: float
    dot_ball_pct: float


class PlayerBowlingCareer(BaseModel):
    matches: int
    innings: int
    wickets: int
    economy: float
    bowling_average: float
    strike_rate: float
    best_bowling: Optional[str]
    overs: float
    runs_conceded: int
    maidens: int


class PhaseStats(BaseModel):
    runs: int
    strike_rate: float
    balls: Optional[int] = None
    wickets: Optional[int] = None
    economy: Optional[float] = None


class PlayerFormComponent(BaseModel):
    score: float
    weight: float
    description: str


class PlayerFormScore(BaseModel):
    player_id: UUID
    form_score: float
    components: dict[str, PlayerFormComponent]


class PlayerProfile(BaseModel):
    id: UUID
    name: str
    full_name: Optional[str]
    role: Optional[str]
    country: Optional[str]
    team_name: Optional[str]
    batting_style: Optional[str]
    bowling_style: Optional[str]
    bowling_type: Optional[str]
    form_score: Optional[float]
    batting_rating: Optional[float]
    consistency: Optional[float]
    career_batting: Optional[PlayerBattingCareer]
    career_bowling: Optional[PlayerBowlingCareer]


class PlayerMatchup(BaseModel):
    opponent_id: UUID
    opponent_name: str
    total_balls: int
    total_runs: int
    wickets: int
    strike_rate: float
    average: Optional[float]
    dot_balls: int
    boundaries: int
    sixes: int


# ============================================================
# Team Schemas
# ============================================================

class TeamSummary(BaseModel):
    id: UUID
    name: str
    short_name: str
    country: Optional[str]
    overall_strength: Optional[float]
    batting_strength: Optional[float]
    bowling_strength: Optional[float]
    win_rate: Optional[float]
    matches: Optional[int]


class TeamAnalytics(BaseModel):
    team_id: UUID
    format: str
    performance: dict
    bowling: dict
    situational: dict


# ============================================================
# Venue Schemas
# ============================================================

class VenueSummary(BaseModel):
    id: UUID
    name: str
    city: Optional[str]
    country: Optional[str]
    total_matches: Optional[int]


class VenueAnalytics(BaseModel):
    venue_id: UUID
    format: str
    matches: int
    avg_first_innings_score: Optional[float]
    avg_second_innings_score: Optional[float]
    chasing_win_pct: Optional[float]
    defending_win_pct: Optional[float]
    avg_powerplay_runs: Optional[float]
    avg_middle_runs: Optional[float]
    avg_death_runs: Optional[float]
    pace_wickets_pct: Optional[float]
    spin_wickets_pct: Optional[float]
    boundary_frequency: Optional[float]


# ============================================================
# Match Schemas
# ============================================================

class MatchSummary(BaseModel):
    id: UUID
    format: str
    date: date
    venue: Optional[str]
    team_a: str
    team_b: str
    result: Optional[str]
    win_margin: Optional[int]
    win_type: Optional[str]


class MatchDetail(BaseModel):
    id: UUID
    format: str
    date: date
    venue: Optional[str]
    team_a: str
    team_b: str
    result: Optional[str]
    win_margin: Optional[int]
    win_type: Optional[str]
    toss_winner: Optional[str]
    toss_decision: Optional[str]
    player_of_match: Optional[str]


# ============================================================
# Matchup Schemas
# ============================================================

class HeadToHeadMatchup(BaseModel):
    batter_id: UUID
    batter_name: str
    bowler_id: UUID
    bowler_name: str
    format: str
    total_balls: int
    total_runs: int
    wickets: int
    strike_rate: float
    average: Optional[float]
    dot_balls: int
    boundaries: int
    sixes: int


# ============================================================
# News Schemas
# ============================================================

class NewsArticleSummary(BaseModel):
    id: UUID
    title: str
    source: Optional[str]
    url: str
    publication_date: Optional[datetime]
    description: Optional[str]
    category: Optional[str]


# ============================================================
# Pagination
# ============================================================

class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class PaginatedPlayers(PaginatedResponse):
    players: List[PlayerSummary]


class PaginatedTeams(PaginatedResponse):
    teams: List[TeamSummary]


class PaginatedMatches(PaginatedResponse):
    matches: List[MatchSummary]


class PaginatedNews(PaginatedResponse):
    articles: List[NewsArticleSummary]
