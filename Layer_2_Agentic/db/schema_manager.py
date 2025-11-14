"""
Database Schema Manager for Agentic Reasoning System

This module provides Python utilities for initializing and managing the agentic
database schema. The actual schema definition is in agentic_schema.sql.

Database Structure:
==================
    Goal → Strategy → Function → Parameters/Outputs

Core Tables:
-----------
- GoalInSession: Top-level user queries and objectives
- StrategyInSession: Reasoning strategies selected for each goal
- FunctionInSession: Individual function executions within strategies
- FunctionOutputInSession: Results produced by function executions
- FunctionParametersInSession: Input parameters for function executions

Template Libraries:
------------------
- StrategyLibrary: Reusable strategy templates and plans
- FunctionTemplateLibrary: Available function definitions
- FunctionOutputLibrary: Expected outputs for each function template
- FunctionParametersLibrary: Required parameters for each function template

Key Features:
============
- Foreign key constraints maintain referential integrity
- Automatic table dropping with system table protection
- Supports LangGraph-based agentic workflows
- Tracks complete execution history and state
- Template-based function and strategy definitions

Usage:
======
    from Layer_2_Agentic.db.schema_manager import init_db

    # Initialize database with fresh schema
    init_db(drop_and_recreate=True)

    # Initialize schema without dropping existing data
    init_db(drop_and_recreate=False)
"""

import logging
import sqlite3
from pathlib import Path

from Layer_2_Agentic.db.connection import get_agentic_connection

logger = logging.getLogger("SCHEMA_MANAGER")


def get_schema_sql() -> str:
    """
    Load the SQL schema from the agentic_schema.sql file.
    
    Returns:
        str: Complete SQL schema as string
        
    Raises:
        FileNotFoundError: If schema file doesn't exist
    """
    schema_file = Path(__file__).parent / "agentic_schema.sql"
    
    if not schema_file.exists():
        raise FileNotFoundError(
            f"Schema file not found: {schema_file}\n"
            f"Expected location: {schema_file.absolute()}"
        )
    
    with open(schema_file, 'r', encoding='utf-8') as f:
        return f.read()


def init_db(drop_and_recreate: bool = True):
    """
    Initialize the agentic database schema with all required tables.

    This function creates a complete database schema for the agentic reasoning
    system, including workflow tracking tables and template libraries. The schema
    is loaded from agentic_schema.sql.

    Args:
        drop_and_recreate (bool): If True, drops all existing user tables
                                before creating new schema. If False, only
                                creates missing tables. Default: True.

    Database Schema Overview:
    ========================

    Workflow Hierarchy:
    ------------------
    GoalInSession (User queries)
    ├── StrategyInSession (Reasoning approaches)
        ├── FunctionInSession (Individual function calls)
            ├── FunctionParametersInSession (Input parameters)
            └── FunctionOutputInSession (Results/outputs)

    Template Libraries:
    ------------------
    StrategyLibrary (Available strategies)
    FunctionTemplateLibrary (Available functions)
    ├── FunctionParametersLibrary (Required parameters)
    └── FunctionOutputLibrary (Expected outputs)

    Table Relationships:
    ===================
    - All InSession tables track actual workflow execution
    - All Library tables provide reusable templates
    - Foreign keys ensure referential integrity
    - Supports complex multi-step reasoning chains

    Safety Features:
    ===============
    - System tables (sqlite_*) are protected from deletion
    - Foreign key constraints are temporarily disabled during drops
    - Complete transaction rollback on errors
    - Proper PRAGMA foreign_keys management

    Raises:
        sqlite3.Error: If database operations fail
        sqlite3.OperationalError: If foreign key constraints are violated
        FileNotFoundError: If agentic_schema.sql is missing

    Example:
        >>> init_db(drop_and_recreate=True)  # Fresh database
        >>> init_db(drop_and_recreate=False) # Preserve existing data
    """
    with get_agentic_connection() as conn:
        cur = conn.cursor()

        if drop_and_recreate:
            logger.info("Dropping all existing user tables...")
            cur.execute("PRAGMA foreign_keys = OFF")

            # Get all table names from the database (excluding system tables)
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = [row[0] for row in cur.fetchall()]

            # Drop all user tables
            for table in tables:
                cur.execute(f"DROP TABLE IF EXISTS {table}")
                logger.debug(f"  Dropped table: {table}")

            cur.execute("PRAGMA foreign_keys = ON")

        # Load and execute schema from SQL file
        logger.info("Loading schema from agentic_schema.sql...")
        schema_sql = get_schema_sql()
        
        cur.executescript(schema_sql)
        conn.commit()
        
        # Validate schema creation
        logger.info("Validating schema...")
        _validate_schema(cur)
        
        logger.info("✅ agentic.db initialized successfully.")


def _validate_schema(cursor):
    """
    Validate that all required tables and indexes were created successfully.
    
    Args:
        cursor: Database cursor for validation queries
        
    Raises:
        sqlite3.Error: If schema validation fails
    """
    # Check that required tables exist
    cursor.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = [
        "FunctionInSession",
        "FunctionOutputInSession", 
        "FunctionOutputLibrary",
        "FunctionParametersInSession",
        "FunctionParametersLibrary",
        "FunctionTemplateLibrary",
        "GoalInSession",
        "StrategyInSession",
        "StrategyLibrary",
    ]
    
    missing_tables = set(expected_tables) - set(tables)
    if missing_tables:
        raise sqlite3.Error(f"Missing required tables: {missing_tables}")
    
    logger.info(f"  ✅ All {len(expected_tables)} required tables created")
    
    # Check that required indexes exist
    cursor.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='index' AND name LIKE 'idx_%'
        ORDER BY name
        """
    )
    indexes = [row[0] for row in cursor.fetchall()]
    
    expected_indexes = [
        "idx_strategy_goal",
        "idx_function_strategy", 
        "idx_function_output_function",
        "idx_function_params_function",
        "idx_strategy_success",
        "idx_function_success",
        "idx_goal_success",
    ]
    
    missing_indexes = set(expected_indexes) - set(indexes)
    if missing_indexes:
        logger.warning(f"  ⚠️  Missing recommended indexes: {missing_indexes}")
    else:
        logger.info(f"  ✅ All {len(expected_indexes)} recommended indexes created")
    
    # Validate foreign key constraints
    cursor.execute("PRAGMA foreign_key_check")
    fk_violations = cursor.fetchall()
    if fk_violations:
        raise sqlite3.Error(f"Foreign key constraint violations: {fk_violations}")
    
    logger.info(f"  ✅ Schema validation passed")


def get_schema_info() -> dict:
    """
    Get information about the current database schema.
    
    Returns:
        dict: Schema information including tables, indexes, and statistics
        
    Example:
        >>> info = get_schema_info()
        >>> print(info['tables'])
        ['GoalInSession', 'StrategyInSession', ...]
    """
    with get_agentic_connection() as conn:
        cur = conn.cursor()
        
        # Get tables
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        tables = [row[0] for row in cur.fetchall()]
        
        # Get indexes
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name"
        )
        indexes = [row[0] for row in cur.fetchall()]
        
        # Get row counts for each table
        table_counts = {}
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            table_counts[table] = cur.fetchone()[0]
        
        return {
            'tables': tables,
            'table_count': len(tables),
            'indexes': indexes,
            'index_count': len(indexes),
            'row_counts': table_counts,
            'total_rows': sum(table_counts.values())
        }


if __name__ == "__main__":
    # Initialize database and show info
    init_db(drop_and_recreate=True)
    
    info = get_schema_info()
    print("\n" + "="*60)
    print("AGENTIC DATABASE SCHEMA INFO")
    print("="*60)
    print(f"Tables: {info['table_count']}")
    for table in info['tables']:
        print(f"  - {table}: {info['row_counts'][table]} rows")
    print(f"\nIndexes: {info['index_count']}")
    for idx in info['indexes']:
        print(f"  - {idx}")
    print("="*60)
