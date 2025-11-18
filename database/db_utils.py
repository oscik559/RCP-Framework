#!/usr/bin/env python3
"""
Database Utilities

Shared functions for database initialization and management across all Layer_1 scripts.
"""

import sqlite3
from pathlib import Path
import sys


class DatabaseManager:
    """Manages database initialization and connection."""
    
    def __init__(self, db_path="database/harvested.db"):
        """Initialize database manager."""
        self.db_path = Path(db_path)
        # Schema is now in the same directory as db_utils.py
        self.schema_path = Path(__file__).parent / "harvested_schema.sql"
        
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def init_database(self):
        """
        Initialize database with full schema if not already done.
        
        Returns:
            bool: True if successful, False if failed
        """
        try:
            # Check if database needs initialization
            if not self._is_database_initialized():
                print(f"[SETUP] Initializing database: {self.db_path}")
                self._load_schema()
                print("[OK] Database initialized successfully")
            else:
                print(f"[OK] Database already initialized: {self.db_path}")
            
            return True
            
        except Exception as e:
            print(f"[FAIL] Database initialization failed: {e}")
            return False
    
    def _is_database_initialized(self):
        """Check if database has all required tables."""
        if not self.db_path.exists():
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for all major tables
            required_tables = [
                'page_regions',
                'categories', 
                'product_families', 
                'products',
                'product_knowledge'
            ]
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ({})
            """.format(','.join('?' * len(required_tables))), required_tables)
            
            existing_tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            # All required tables must exist
            return len(existing_tables) == len(required_tables)
            
        except Exception:
            return False
    
    def _load_schema(self):
        """Load schema from harvested_schema.sql file."""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        
        # Read schema file
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Execute schema
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Execute the entire schema (SQLite can handle multiple statements)
            cursor.executescript(schema_sql)
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to execute schema: {e}")
        
        finally:
            conn.close()
    
    def get_connection(self):
        """
        Get database connection, ensuring database is initialized first.
        
        Returns:
            sqlite3.Connection: Database connection
        """
        if not self.init_database():
            raise Exception("Database initialization failed")
        
        return sqlite3.connect(self.db_path)
    
    def verify_connection(self):
        """Verify database connection and print status."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get table information
            required_tables = ['page_regions', 'categories', 'product_families', 'products', 'product_knowledge']
            table_info = []
            
            for table_name in required_tables:
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name = ?
                """, (table_name,))
                exists = cursor.fetchone() is not None
                
                if exists:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                else:
                    count = 0
                
                table_info.append((table_name, exists, count))
            
            print(f"\n[DATA] Database Status: {self.db_path}")
            print("=" * 50)
            
            for table_name, exists, count in table_info:
                status = "[OK] EXISTS" if exists else "[MISSING]"
                
                if exists:
                    print(f"{table_name:15} {status:10} ({count:,} rows)")
                else:
                    print(f"{table_name:15} {status}")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"[FAIL] Database verification failed: {e}")
            return False


# Convenience function for quick initialization
def init_database(db_path="database/harvested.db"):
    """
    Quick database initialization function.
    
    Args:
        db_path: Path to database file
        
    Returns:
        bool: True if successful
    """
    db_manager = DatabaseManager(db_path)
    return db_manager.init_database()


# Convenience function for getting connection
def get_db_connection(db_path="database/harvested.db"):
    """
    Get database connection with auto-initialization.
    
    Args:
        db_path: Path to database file
        
    Returns:
        sqlite3.Connection: Database connection
    """
    db_manager = DatabaseManager(db_path)
    return db_manager.get_connection()


if __name__ == "__main__":
    """Command-line interface for database management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database management utilities")
    parser.add_argument("--init", action="store_true", help="Initialize database")
    parser.add_argument("--verify", action="store_true", help="Verify database status")
    parser.add_argument("--db-path", default="database/harvested.db", help="Database path")
    
    args = parser.parse_args()
    
    db_manager = DatabaseManager(args.db_path)
    
    if args.init:
        if db_manager.init_database():
            sys.exit(0)
        else:
            sys.exit(1)
    
    elif args.verify:
        if db_manager.verify_connection():
            sys.exit(0)
        else:
            sys.exit(1)
    
    else:
        # Default: verify status
        db_manager.verify_connection()