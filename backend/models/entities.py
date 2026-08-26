"""
SQLAlchemy ORM Models
====================

Defines database models matching the PostgreSQL schema.
These are used by the backend to query precomputed analytical data.

Updated for Phase 1: Universal Cricket Data Model
- Added seasons, format_config tables
- Added result_type, day_number, event_match_number to Match
- Added declared, all_out, follow_on to Innings
- Added team_type to Team
- Added competition_type to Competition
"""

import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Date, DateTime,
    ForeignKey, Text, JSON, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from backend.utils.database import Base


class Team(Base):
    __tablename__ = "teams"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name = Column(String(100), nullable=False, unique=True)
    short_name = Column(String(20), nullable=False)
    country = Column(String(100))
    team_type = Column(String(50), default="franchise")  # 'national', 'franchise', 'domestic'
    icc_id = Column(String(50))
    aliases = Column(ARRAY(Text))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Player(Base):
    __tablename__ = "players"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name = Column(String(200), nullable=False)
    full_name = Column(String(300))
    country = Column(String(100))
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))  # DEPRECATED: use affiliations
    date_of_birth = Column(Date)
    role = Column(String(50))
    batting_style = Column(String(50))
    bowling_style = Column(String(50))
    bowling_type = Column(String(30))
    icc_id = Column(String(50))
    cricsheet_id = Column(String(50))
    aliases = Column(ARRAY(Text))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    affiliations = relationship("PlayerTeamAffiliation", back_populates="player")


class Venue(Base):
    __tablename__ = "venues"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    city = Column(String(100))
    country = Column(String(100))
    capacity = Column(Integer)
    aliases = Column(ARRAY(Text))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Competition(Base):
    __tablename__ = "competitions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    short_name = Column(String(50))
    format = Column(String(20), nullable=False)
    competition_type = Column(String(50), default="league")  # 'league', 'tournament', 'bilateral', 'test_series'
    governing_body = Column(String(100))
    season = Column(String(20))
    aliases = Column(ARRAY(Text))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Season(Base):
    """Represents a specific season/edition of a competition."""
    __tablename__ = "seasons"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False)
    name = Column(String(50), nullable=False)  # '2024', '2023-24', '2023'
    start_date = Column(Date)
    end_date = Column(Date)
    aliases = Column(ARRAY(Text))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("competition_id", "name"),
    )


class FormatConfig(Base):
    """Format-specific configuration for analytics."""
    __tablename__ = "format_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    format = Column(String(20), nullable=False, unique=True)
    standard_overs = Column(Integer)
    powerplay_end = Column(Integer)  # Last over of powerplay (0-indexed)
    middle_end = Column(Integer)  # Last over of middle phase (0-indexed)
    max_innings = Column(Integer, default=2)
    is_multi_day = Column(Boolean, default=False)
    is_first_class = Column(Boolean, default=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Match(Base):
    __tablename__ = "matches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(100), unique=True)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"))
    season_id = Column(UUID(as_uuid=True), ForeignKey("seasons.id"))
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"))
    match_date = Column(Date, nullable=False)
    format = Column(String(20), nullable=False)

    team_a_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    team_b_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))

    toss_winner_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    toss_decision = Column(String(20))

    winner_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    win_margin = Column(Integer)
    win_type = Column(String(30))
    result_type = Column(String(30), default="win")  # 'win', 'tie', 'draw', 'no_result', 'abandoned'

    player_of_match_id = Column(UUID(as_uuid=True), ForeignKey("players.id"))

    total_innings = Column(Integer)
    total_deliveries = Column(Integer)

    day_number = Column(Integer)  # For multi-day matches
    event_match_number = Column(Integer)  # Match number within event/series

    is_live = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Innings(Base):
    __tablename__ = "innings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    innings_number = Column(Integer, nullable=False)
    batting_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    bowling_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)

    total_runs = Column(Integer, default=0)
    total_wickets = Column(Integer, default=0)
    total_overs = Column(Float, default=0)

    extras_wides = Column(Integer, default=0)
    extras_noballs = Column(Integer, default=0)
    extras_byes = Column(Integer, default=0)
    extras_legbyes = Column(Integer, default=0)
    extras_penalty = Column(Integer, default=0)
    total_extras = Column(Integer, default=0)
    run_rate = Column(Float)

    declared = Column(Boolean, default=False)
    all_out = Column(Boolean, default=False)
    follow_on = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("match_id", "innings_number"),
    )


class PlayerBattingStats(Base):
    __tablename__ = "player_batting_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), nullable=False)
    period = Column(String(20), nullable=False)
    
    matches = Column(Integer, default=0)
    innings = Column(Integer, default=0)
    not_outs = Column(Integer, default=0)
    runs = Column(Integer, default=0)
    highest_score = Column(Integer)
    batting_average = Column(Float)
    strike_rate = Column(Float)
    balls_faced = Column(Integer, default=0)
    
    fours = Column(Integer, default=0)
    sixes = Column(Integer, default=0)
    boundary_pct = Column(Float)
    dot_ball_pct = Column(Float)
    
    fifties = Column(Integer, default=0)
    hundreds = Column(Integer, default=0)
    
    powerplay_runs = Column(Integer, default=0)
    powerplay_strike_rate = Column(Float)
    middle_runs = Column(Integer, default=0)
    middle_strike_rate = Column(Float)
    death_runs = Column(Integer, default=0)
    death_strike_rate = Column(Float)
    
    chasing_runs = Column(Integer, default=0)
    chasing_strike_rate = Column(Float)
    first_innings_runs = Column(Integer, default=0)
    first_innings_strike_rate = Column(Float)
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("player_id", "format", "period"),
        Index("idx_pbs_player", "player_id"),
        Index("idx_pbs_format_period", "format", "period"),
    )


class PlayerBowlingStats(Base):
    __tablename__ = "player_bowling_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), nullable=False)
    period = Column(String(20), nullable=False)
    
    matches = Column(Integer, default=0)
    innings = Column(Integer, default=0)
    overs = Column(Float, default=0)
    balls_bowled = Column(Integer, default=0)
    maidens = Column(Integer, default=0)
    wickets = Column(Integer, default=0)
    runs_conceded = Column(Integer, default=0)
    bowling_average = Column(Float)
    strike_rate = Column(Float)
    economy = Column(Float)
    best_bowling = Column(String(20))
    
    four_wickets = Column(Integer, default=0)
    five_wickets = Column(Integer, default=0)
    
    dot_ball_pct = Column(Float)
    boundary_conceded_pct = Column(Float)
    
    powerplay_overs = Column(Float, default=0)
    powerplay_wickets = Column(Integer, default=0)
    powerplay_economy = Column(Float)
    middle_overs = Column(Float, default=0)
    middle_wickets = Column(Integer, default=0)
    middle_economy = Column(Float)
    death_overs = Column(Float, default=0)
    death_wickets = Column(Integer, default=0)
    death_economy = Column(Float)
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("player_id", "format", "period"),
        Index("idx_pws_player", "player_id"),
        Index("idx_pws_format_period", "format", "period"),
    )


class PlayerForm(Base):
    __tablename__ = "player_form"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), nullable=False)
    
    form_score = Column(Float, nullable=False)
    recent_performance_component = Column(Float)
    consistency_component = Column(Float)
    opposition_strength_component = Column(Float)
    venue_performance_component = Column(Float)
    match_situation_component = Column(Float)
    efficiency_component = Column(Float)
    
    recent_innings_count = Column(Integer)
    last_calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("player_id", "format"),
    )


class TeamPerformance(Base):
    __tablename__ = "team_performance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), nullable=False)
    period = Column(String(20), nullable=False)
    
    matches = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)
    no_results = Column(Integer, default=0)
    win_rate = Column(Float)
    
    avg_first_innings_score = Column(Float)
    avg_second_innings_score = Column(Float)
    avg_powerplay_score = Column(Float)
    avg_middle_overs_score = Column(Float)
    avg_death_overs_score = Column(Float)
    avg_total_score = Column(Float)
    
    chasing_win_pct = Column(Float)
    defending_win_pct = Column(Float)
    
    batting_strength_score = Column(Float)
    bowling_strength_score = Column(Float)
    overall_strength_score = Column(Float)
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("team_id", "format", "period"),
        Index("idx_tp_team", "team_id"),
        Index("idx_tp_format_period", "format", "period"),
    )


class VenueStats(Base):
    __tablename__ = "venue_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), nullable=False)
    
    total_matches = Column(Integer, default=0)
    avg_first_innings_score = Column(Float)
    avg_second_innings_score = Column(Float)
    highest_total = Column(Integer)
    lowest_total = Column(Integer)
    
    chasing_win_pct = Column(Float)
    chasing_wins = Column(Integer, default=0)
    defending_wins = Column(Integer, default=0)
    defending_win_pct = Column(Float)
    
    pace_wickets_pct = Column(Float)
    spin_wickets_pct = Column(Float)
    
    avg_powerplay_runs = Column(Float)
    avg_middle_overs_runs = Column(Float)
    avg_death_overs_runs = Column(Float)
    
    avg_fours_per_match = Column(Float)
    avg_sixes_per_match = Column(Float)
    boundary_frequency = Column(Float)
    
    toss_bat_first_win_pct = Column(Float)
    toss_field_first_win_pct = Column(Float)
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("venue_id", "format"),
        Index("idx_vs_venue", "venue_id"),
    )


class BatterBowlerMatchup(Base):
    __tablename__ = "batter_bowler_matchups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batter_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    bowler_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20), nullable=False)
    
    total_balls = Column(Integer, default=0)
    total_runs = Column(Integer, default=0)
    total_wickets = Column(Integer, default=0)
    strike_rate = Column(Float)
    batting_average = Column(Float)
    dot_balls = Column(Integer, default=0)
    boundaries = Column(Integer, default=0)
    sixes = Column(Integer, default=0)
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("batter_id", "bowler_id", "format"),
    )


class PlayerTeamAffiliation(Base):
    """Links players to teams with format/competition context.
    
    A player can have multiple affiliations:
    - India (T20I)
    - India (ODI)
    - Royal Challengers Bangalore (T20, IPL)
    """
    __tablename__ = "player_team_affiliations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(20))  # 'T20', 'T20I', 'ODI', 'Test', NULL = general
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"))
    season = Column(String(50))
    start_date = Column(Date)
    end_date = Column(Date)
    is_current = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    player = relationship("Player", back_populates="affiliations")
    
    __table_args__ = (
        UniqueConstraint("player_id", "team_id", "format", "competition_id"),
        Index("idx_pta_player", "player_id"),
        Index("idx_pta_team", "team_id"),
        Index("idx_pta_format", "format"),
    )


class PlayerNameMapping(Base):
    """Maps source-specific player names to canonical player identities.
    
    Used to resolve Cricsheet abbreviated names (e.g. 'V Kohli') to
    canonical player identities (e.g. 'Virat Kohli').
    """
    __tablename__ = "player_name_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(50), nullable=False)  # 'cricsheet', 'icc', 'manual'
    source_id = Column(String(100))
    name_variant = Column(String(300), nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("source", "name_variant"),
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    source = Column(String(100))
    url = Column(String(1000), nullable=False)
    publication_date = Column(DateTime)
    description = Column(Text)
    category = Column(String(50))
    image_url = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_news_date", "publication_date"),
    )
