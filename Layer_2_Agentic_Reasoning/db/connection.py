# /db/connection.py
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from Layer_2_Agentic_Reasoning.config.config_loader import CONFIG

logger = logging.getLogger("CONNECTION")


# ─── Database Connection Context Manager ──────────────────────────────


@contextmanager
def get_output_connection():
    """Context-managed connection to the harvested data database."""
    with get_db_connection(CONFIG["harvested_db"]) as conn:
        yield conn


@contextmanager
def get_agentic_connection():
    """Context-managed connection to the agentic database."""
    with get_db_connection(CONFIG["agentic_db"]) as conn:
        yield conn


@contextmanager
def get_temp_connection():
    """Context-managed connection to the temporary database."""
    with get_db_connection(CONFIG["temp_db"]) as conn:
        yield conn


@contextmanager
def get_db_connection(db):
    """
    Context manager for SQLite database connections with proper configuration.

    Args:
        db: Path to the SQLite database file

    Yields:
        sqlite3.Connection: Configured database connection with Row factory and foreign keys enabled
    """
    db_path = Path(db)
    db_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent folders exist
    logger.debug(f"Connecting to database: {db_path}")
    
    try:
        # Enhanced connection with timeout and optimizations
        conn = sqlite3.connect(
            db, 
            check_same_thread=False,
            timeout=30.0,  # 30 second timeout for busy database
            isolation_level=None  # Enable autocommit mode for better performance
        )
        
        # Set Row factory for easier column access
        conn.row_factory = sqlite3.Row
        
        # Enable foreign keys and performance optimizations
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA synchronous = NORMAL")  # Better performance than FULL
        conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
        conn.execute("PRAGMA temp_store = memory")  # Store temporary tables in memory
        conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for better concurrency
        
        logger.debug(f"Database connection established with optimizations: {db_path}")
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error for {db_path}: {e}")
        raise
    finally:
        try:
            conn.close()
            logger.debug("Database connection closed.")
        except Exception as e:
            logger.warning(f"Error closing database connection: {e}")


# ─── Database Initialization (sanity check)──────────────────────────────────────────
if __name__ == "__main__":
    with get_output_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()
        table_names = [row["name"] for row in rows]
        logger.info(f"Tables in database: {table_names}")


