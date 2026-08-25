"""
SQLAlchemy ORM Models
====================

Defines database models matching the PostgreSQL schema.
These are used by the backend to query precomputed analytical data.
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
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
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
    governing_body = Column(String(100))
    season = Column(String(20))
    aliases = Column(ARRAY(Text))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Match(Base):
    __tablename__ = "matches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(100), unique=True)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"))
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
    player_of_match_id = Column(UUID(as_uuid=True), ForeignKey("players.id"))
    total_innings = Column(Integer)
    total_deliveries = Column(Integer)
    is_live = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlayerBattingStats(Base):
    __tablename__ = "player_batting_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False)
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
    chasing_average = Column(Float)
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
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False)
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
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("player_id", "format", "period"),
    )


class PlayerForm(Base):
    __tablename__ = "player_form"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False)
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
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
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
    
    batting_strength_score = Column(Float)
    bowling_strength_score = Column(Float)
    overall_strength_score = Column(Float)
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("team_id", "format", "period"),
    )


class VenueStats(Base):
    __tablename__ = "venue_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False)
    format = Column(String(20), nullable=False)
    
    total_matches = Column(Integer, default=0)
    avg_first_innings_score = Column(Float)
    avg_second_innings_score = Column(Float)
    highest_total = Column(Integer)
    lowest_total = Column(Integer)
    
    chasing_win_pct = Column(Float)
    defending_win_pct = Column(Float)
    
    pace_wickets_pct = Column(Float)
    spin_wickets_pct = Column(Float)
    
    avg_powerplay_runs = Column(Float)
    avg_middle_overs_runs = Column(Float)
    avg_death_overs_runs = Column(Float)
    
    avg_fours_per_match = Column(Float)
    avg_sixes_per_match = Column(Float)
    boundary_frequency = Column(Float)
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("venue_id", "format"),
    )


class BatterBowlerMatchup(Base):
    __tablename__ = "batter_bowler_matchups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batter_id = Column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False)
    bowler_id = Column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False)
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
