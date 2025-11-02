"""
Unit tests for database schema and connections.
"""

import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from agentic_reasoning.db.connection import (
    get_agentic_connection,
    get_output_connection,
    get_temp_connection,
)
from agentic_reasoning.db.schema_manager import init_db


class TestDatabaseSchema(unittest.TestCase):
    """Test database schema initialization and structure."""

    def setUp(self):
        """Set up test database."""
        self.test_db_fd, self.test_db_path = tempfile.mkstemp()
        os.close(self.test_db_fd)

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    @patch("agentic_reasoning.db.schema_manager.get_agentic_connection")
    def test_schema_initialization(self, mock_connection):
        """Test database schema initialization."""
        # Create in-memory database for testing
        conn = sqlite3.connect(":memory:")
        mock_connection.return_value.__enter__.return_value = conn

        # Initialize schema
        init_db(drop_and_recreate=True)

        # Check that required tables exist
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """
        )
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = [
            "GoalInSession",
            "StrategyInSession",
            "FunctionInSession",
            "FunctionTemplateLibrary",
            "FunctionOutputLibrary",
            "FunctionParametersLibrary",
            "FunctionOutputInSession",
            "FunctionParametersInSession",
            "StrategyLibrary",
        ]

        for table in expected_tables:
            self.assertIn(table, tables, f"Table {table} should exist")

    def test_tri_state_schema(self):
        """Test that success fields use tri-state INTEGER instead of BOOLEAN."""
        conn = sqlite3.connect(":memory:")

        with patch("agentic_reasoning.db.schema_manager.get_agentic_connection") as mock_conn:
            mock_conn.return_value.__enter__.return_value = conn
            init_db(drop_and_recreate=True)

        cursor = conn.cursor()

        # Check GoalInSession schema
        cursor.execute("PRAGMA table_info(GoalInSession)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        self.assertEqual(
            columns["GoalSuccess"],
            "INTEGER",
            "GoalSuccess should be INTEGER for tri-state",
        )

        # Check StrategyInSession schema
        cursor.execute("PRAGMA table_info(StrategyInSession)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        self.assertEqual(
            columns["StrategySuccess"],
            "INTEGER",
            "StrategySuccess should be INTEGER for tri-state",
        )

        # Check FunctionInSession schema
        cursor.execute("PRAGMA table_info(FunctionInSession)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        self.assertEqual(
            columns["FunctionSuccess"],
            "INTEGER",
            "FunctionSuccess should be INTEGER for tri-state",
        )


class TestDatabaseConnections(unittest.TestCase):
    """Test database connection management."""

    def test_agentic_connection_context_manager(self):
        """Test agentic database connection context manager."""
        with get_agentic_connection() as conn:
            self.assertIsNotNone(conn)
            self.assertIsInstance(conn, sqlite3.Connection)

    def test_output_connection_context_manager(self):
        """Test output database connection context manager."""
        with get_output_connection() as conn:
            self.assertIsNotNone(conn)
            self.assertIsInstance(conn, sqlite3.Connection)

    def test_temp_connection_context_manager(self):
        """Test temporary database connection context manager."""
        with get_temp_connection() as conn:
            self.assertIsNotNone(conn)
            self.assertIsInstance(conn, sqlite3.Connection)


if __name__ == "__main__":
    unittest.main()


