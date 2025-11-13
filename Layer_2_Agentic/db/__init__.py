"""
Database Infrastructure Module

This module provides database connection management and schema initialization
for the agentic reasoning system.

Main Components:
- connection.py: Database connection context managers
- schema_manager.py: Schema initialization and validation
- agentic_schema.sql: SQL schema definition

Usage:
    from Layer_2_Agentic.db import init_db, get_agentic_connection
    
    # Initialize database
    init_db(drop_and_recreate=True)
    
    # Use connection
    with get_agentic_connection() as conn:
        cursor = conn.cursor()
        # ... execute queries
"""

from .connection import (
    get_agentic_connection,
    get_output_connection,
    get_temp_connection,
)
from .schema_manager import init_db, get_schema_info

__all__ = [
    'get_agentic_connection',
    'get_output_connection', 
    'get_temp_connection',
    'init_db',
    'get_schema_info',
]
