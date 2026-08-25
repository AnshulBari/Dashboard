"""
Database Connection Management
==============================

Manages SQLAlchemy connection pool and session lifecycle.

Uses environment variables:
- DATABASE_URL: PostgreSQL connection string
  Default: sqlite:///data/cricket_intelligence.db (local dev)
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///data/cricket_intelligence.db"
)

IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    **({} if IS_SQLITE else {
        "pool_size": 5,
        "max_overflow": 10,
    }),
    echo=False,
)

# Enable WAL mode for SQLite (better concurrency)
if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def close_db():
    """Dispose of the connection pool."""
    engine.dispose()


def get_db():
    """
    Dependency for FastAPI route handlers.
    Yields a database session and ensures proper cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
