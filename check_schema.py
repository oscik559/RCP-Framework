#!/usr/bin/env python3
"""Check database schema"""

import sqlite3

conn = sqlite3.connect("database/agentic.db")
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    print(f"\n  {table[0]}")
    
    # Get schema for each table
    cursor.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()
    print("    Columns:")
    for col in columns:
        print(f"      {col[1]} ({col[2]})")

conn.close()
