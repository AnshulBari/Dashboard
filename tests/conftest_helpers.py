"""Shared test helpers for Phase 5.6a+ (deliveries table removal)."""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    if not DATABASE_URL:
        return False
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = :name AND table_schema = 'public'"
            ), {"name": table_name})
            exists = result.scalar() > 0
        engine.dispose()
        return exists
    except Exception:
        return False


def deliveries_exist() -> bool:
    """Check if the deliveries table exists (removed in Phase 5.6a)."""
    return table_exists("deliveries")
