"""
Database Writer
===============

Writes Spark DataFrame output to PostgreSQL.

This module bridges the gap between the PySpark pipeline and the application
database. It uses SQLAlchemy for table management and psycopg2 for efficient
bulk inserts via COPY.

Why not JDBC directly?
- JDBC requires the PostgreSQL JDBC driver JAR on the classpath
- COPY is faster for bulk inserts than individual INSERT statements
- SQLAlchemy handles schema creation and type mapping
- We want fine-grained control over error handling and retries
"""

import os
import logging
from typing import Optional

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///data/cricket_intelligence.db"
)


class DatabaseWriter:
    """
    Writes analytical results to the PostgreSQL database.
    
    Uses pandas + psycopg2 COPY for bulk inserts.
    Handles schema creation, upserts, and data type mapping.
    """
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or DATABASE_URL
        self.engine = create_engine(self.database_url, echo=False)
        self._conn = None
    
    def _get_connection(self):
        """Get a raw psycopg2 connection for COPY operations."""
        if self._conn is None or self._conn.closed:
            # Extract connection params from the URL
            url = self.database_url
            if url.startswith("sqlite"):
                logger.warning("SQLite detected — using SQLAlchemy engine instead of COPY")
                return None
            self._conn = psycopg2.connect(url)
        return self._conn
    
    def close(self):
        """Close the database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
    
    def ensure_schema(self):
        """
        Create all tables if they don't exist.
        
        Reads and executes the schema.sql file.
        """
        schema_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "database", "schema.sql"
        )
        if not os.path.exists(schema_path):
            logger.warning(f"Schema file not found: {schema_path}")
            return
        
        logger.info("Ensuring database schema exists...")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        
        with self.engine.connect() as conn:
            # Split by semicolons and execute each statement
            # (Skip empty statements)
            for statement in schema_sql.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        conn.execute(text(statement))
                    except Exception as e:
                        # Ignore "already exists" errors
                        if "already exists" not in str(e).lower():
                            logger.warning(f"Schema statement warning: {e}")
            conn.commit()
        
        logger.info("Schema ensured successfully")
    
    def write_dataframe(
        self,
        df,
        table_name: str,
        if_exists: str = "append",
        batch_size: int = 1000,
        truncate: bool = False,
    ):
        """
        Write a Spark DataFrame to a PostgreSQL table.
        
        Converts to pandas first, then uses SQLAlchemy for the insert.
        This is the simplest approach; for very large datasets, use
        the COPY method below.
        
        Args:
            df: PySpark DataFrame (or pandas DataFrame)
            table_name: Target table name
            if_exists: 'append', 'replace', or 'fail'
            batch_size: Rows per batch for progress logging
            truncate: If True, truncate the table before writing
        """
        # Convert Spark DataFrame to pandas if needed
        if hasattr(df, 'toPandas'):
            logger.info(f"Converting Spark DataFrame to pandas for table '{table_name}'...")
            pdf = df.toPandas()
        else:
            pdf = df
        
        if pdf.empty:
            logger.warning(f"Empty DataFrame for table '{table_name}', skipping")
            return 0
        
        row_count = len(pdf)
        logger.info(f"Writing {row_count} rows to '{table_name}'...")
        
        # Handle UUID columns — convert to strings for compatibility
        for col in pdf.columns:
            if pdf[col].dtype == object:
                # Check if values look like UUIDs
                sample = pdf[col].dropna().head(1)
                if len(sample) > 0:
                    val = str(sample.iloc[0])
                    if len(val) == 36 and val.count("-") == 4:
                        # Likely a UUID — keep as string, PostgreSQL will handle it
                        pass
        
        # Truncate if requested
        if truncate:
            with self.engine.connect() as conn:
                conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
                conn.commit()
            logger.info(f"  Truncated table '{table_name}'")
        
        # Write using pandas to_sql
        try:
            pdf.to_sql(
                name=table_name,
                con=self.engine,
                if_exists=if_exists,
                index=False,
                chunksize=batch_size,
                method="multi",
            )
            logger.info(f"  Successfully wrote {row_count} rows to '{table_name}'")
            return row_count
        except Exception as e:
            logger.error(f"  Failed to write to '{table_name}': {e}")
            raise
    
    def write_dataframe_copy(
        self,
        df,
        table_name: str,
        truncate: bool = True,
    ):
        """
        Write a Spark DataFrame to PostgreSQL using COPY for maximum speed.
        
        This is significantly faster than individual INSERT statements
        for large datasets (10K+ rows).
        
        Falls back to write_dataframe if COPY is not available (e.g., SQLite).
        """
        conn = self._get_connection()
        if conn is None:
            return self.write_dataframe(df, table_name, truncate=truncate)
        
        # Convert to pandas
        if hasattr(df, 'toPandas'):
            pdf = df.toPandas()
        else:
            pdf = df
        
        if pdf.empty:
            logger.warning(f"Empty DataFrame for table '{table_name}', skipping")
            return 0
        
        row_count = len(pdf)
        logger.info(f"COPY writing {row_count} rows to '{table_name}'...")
        
        # Replace NaN with None
        pdf = pdf.where(pd.notnull(pdf), None)
        
        cursor = conn.cursor()
        
        try:
            if truncate:
                cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE")
            
            # Get column names
            columns = list(pdf.columns)
            cols_str = ", ".join(columns)
            
            # Convert DataFrame to list of tuples
            values = [tuple(row) for row in pdf.itertuples(index=False, name=None)]
            
            # Use execute_values for bulk insert (faster than individual INSERTs)
            insert_query = f"""
                INSERT INTO {table_name} ({cols_str})
                VALUES %s
                ON CONFLICT DO NOTHING
            """
            
            execute_values(cursor, insert_query, values, page_size=1000)
            conn.commit()
            
            logger.info(f"  COPY wrote {row_count} rows to '{table_name}'")
            return row_count
            
        except Exception as e:
            conn.rollback()
            logger.error(f"  COPY failed for '{table_name}': {e}")
            # Fall back to pandas method
            logger.info(f"  Falling back to pandas write for '{table_name}'")
            return self.write_dataframe(df, table_name, truncate=truncate)
        finally:
            cursor.close()
    
    def write_all_results(self, aggregations: dict, analytics: dict):
        """
        Write all pipeline results to the database.
        
        Maps Spark DataFrame names to PostgreSQL table names.
        """
        # Mapping from pipeline output names to database table names
        table_mapping = {
            "player_batting_innings": None,  # Not stored directly
            "player_bowling_innings": None,  # Not stored directly
            "career_batting": "player_batting_stats",
            "career_bowling": "player_bowling_stats",
            "batting_by_phase": None,  # Computed in real-time
            "batting_by_situation": None,  # Computed in real-time
            "consistency": None,  # Part of player_form
            "team_performance": "team_performance",
            "team_bowling": None,  # Part of team_performance
            "team_strength": "team_performance",
            "venue_stats": "venue_stats",
            "matchups": "batter_bowler_matchups",
        }
        
        analytics_mapping = {
            "form_scores": "player_form",
        }
        
        total_rows = 0
        
        # Write aggregation results
        for name, df in aggregations.items():
            table_name = table_mapping.get(name)
            if table_name:
                try:
                    count = self.write_dataframe_copy(df, table_name, truncate=True)
                    total_rows += count
                except Exception as e:
                    logger.error(f"Failed to write {name} to {table_name}: {e}")
            else:
                logger.info(f"  Skipping {name} (not stored in DB)")
        
        # Write analytics results
        for name, df in analytics.items():
            table_name = analytics_mapping.get(name)
            if table_name:
                try:
                    count = self.write_dataframe_copy(df, table_name, truncate=True)
                    total_rows += count
                except Exception as e:
                    logger.error(f"Failed to write {name} to {table_name}: {e}")
            else:
                logger.info(f"  Skipping {name} (not stored in DB)")
        
        logger.info(f"Total rows written to database: {total_rows}")
        return total_rows
    
    def get_table_counts(self) -> dict:
        """Get row counts for all analytical tables."""
        tables = [
            "teams", "players", "venues", "matches", "innings", "deliveries",
            "player_batting_stats", "player_bowling_stats", "player_form",
            "team_performance", "venue_stats", "batter_bowler_matchups",
            "rankings", "news_articles",
        ]
        
        counts = {}
        with self.engine.connect() as conn:
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    counts[table] = result.scalar()
                except Exception:
                    counts[table] = -1  # Table doesn't exist
        
        return counts
