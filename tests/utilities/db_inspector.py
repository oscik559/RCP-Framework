"""
Database inspection utility for understanding harvested.db and agentic.db structure.

Provides comprehensive tools for:
- Database schema inspection
- Row count and data distribution analysis
- Sample data extraction
- Coverage analysis for test questions
- Data quality checks

Usage:
    python tests/utilities/db_inspector.py --db harvested --analyze-coverage
    python tests/utilities/db_inspector.py --db agentic --schema
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    row_count: int
    columns: List[str]
    sample_rows: List[Dict[str, Any]]


class DatabaseInspector:
    """Inspect and analyze SQLite databases."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        self.conn = None

    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        return self

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self.connect()

    def __exit__(self, *args):
        self.close()

    def get_tables(self) -> List[str]:
        """Get all table names."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall()]

    def get_table_info(self, table_name: str) -> TableInfo:
        """Get detailed information about a table."""
        cursor = self.conn.cursor()

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]

        # Get columns
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]

        # Get sample rows (limit 5)
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
        sample_rows = [dict(row) for row in cursor.fetchall()]

        return TableInfo(
            name=table_name,
            row_count=row_count,
            columns=columns,
            sample_rows=sample_rows,
        )

    def print_schema(self):
        """Print database schema overview."""
        print("\n" + "=" * 80)
        print(f"DATABASE: {self.db_path.name}")
        print("=" * 80)

        tables = self.get_tables()
        print(f"\nTables ({len(tables)}):\n")

        for table in tables:
            info = self.get_table_info(table)
            print(f"  📋 {table}")
            print(f"     Rows: {info.row_count:,}")
            print(f"     Columns: {', '.join(info.columns)}")
            print()

    def print_table_details(self, table_name: str):
        """Print detailed information about a specific table."""
        info = self.get_table_info(table_name)

        print("\n" + "=" * 80)
        print(f"TABLE: {info.name}")
        print("=" * 80)
        print(f"\nRow Count: {info.row_count:,}")
        print(f"\nColumns ({len(info.columns)}):")
        for col in info.columns:
            print(f"  - {col}")

        if info.sample_rows:
            print(f"\nSample Rows (showing first {len(info.sample_rows)}):")
            print()
            for i, row in enumerate(info.sample_rows, 1):
                print(f"  Row {i}:")
                for key, value in row.items():
                    # Truncate long JSON strings
                    display_value = str(value)
                    if len(display_value) > 100:
                        display_value = display_value[:97] + "..."
                    print(f"    {key}: {display_value}")
                print()

    def analyze_coverage(self) -> Dict[str, Any]:
        """Analyze data coverage for test questions."""
        cursor = self.conn.cursor()

        analysis = {
            "database": str(self.db_path.name),
            "tables": {},
        }

        # Categories analysis
        try:
            cursor.execute("SELECT COUNT(*) FROM categories")
            categories_count = cursor.fetchone()[0]
            cursor.execute("SELECT DISTINCT chapter FROM categories")
            chapters = [row[0] for row in cursor.fetchall()]
            analysis["tables"]["categories"] = {
                "count": categories_count,
                "chapters": chapters,
            }
        except Exception as e:
            analysis["tables"]["categories"] = {"error": str(e)}

        # Product families analysis
        try:
            cursor.execute("SELECT COUNT(*) FROM product_families")
            families_count = cursor.fetchone()[0]
            cursor.execute("SELECT DISTINCT category_id FROM product_families")
            categories_with_families = len(cursor.fetchall())
            analysis["tables"]["product_families"] = {
                "count": families_count,
                "categories_with_families": categories_with_families,
            }
        except Exception as e:
            analysis["tables"]["product_families"] = {"error": str(e)}

        # Products analysis
        try:
            cursor.execute("SELECT COUNT(*) FROM products")
            products_count = cursor.fetchone()[0]
            cursor.execute("SELECT DISTINCT configuration_type FROM products")
            config_types = [row[0] for row in cursor.fetchall()]
            cursor.execute(
                "SELECT COUNT(*) FROM products WHERE specifications IS NOT NULL"
            )
            with_specs = cursor.fetchone()[0]

            analysis["tables"]["products"] = {
                "count": products_count,
                "with_specifications": with_specs,
                "configuration_types": config_types,
            }
        except Exception as e:
            analysis["tables"]["products"] = {"error": str(e)}

        # Product knowledge analysis
        try:
            cursor.execute("SELECT COUNT(*) FROM product_knowledge")
            knowledge_count = cursor.fetchone()[0]
            cursor.execute("SELECT DISTINCT knowledge_type FROM product_knowledge")
            knowledge_types = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT DISTINCT category FROM product_knowledge")
            knowledge_categories = [row[0] for row in cursor.fetchall()]

            analysis["tables"]["product_knowledge"] = {
                "count": knowledge_count,
                "types": knowledge_types,
                "categories": knowledge_categories,
            }
        except Exception as e:
            analysis["tables"]["product_knowledge"] = {"error": str(e)}

        return analysis

    def get_products_by_family(self, family_name: str) -> List[Dict[str, Any]]:
        """Get all products in a family."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT p.* FROM products p
            JOIN product_families pf ON p.family_id = pf.id
            WHERE pf.name LIKE ?
        """,
            (f"%{family_name}%",),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_products_by_code(self, code_pattern: str) -> List[Dict[str, Any]]:
        """Get products matching a code pattern."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM products WHERE product_code LIKE ?", (f"%{code_pattern}%",)
        )
        return [dict(row) for row in cursor.fetchall()]

    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search product knowledge base."""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """
                SELECT * FROM product_knowledge_fts
                WHERE product_knowledge_fts MATCH ?
                LIMIT ?
            """,
                (query, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"⚠️  FTS search failed: {e}")
            # Fallback to simple LIKE search
            cursor.execute(
                """
                SELECT * FROM product_knowledge
                WHERE content LIKE ? OR section_title LIKE ?
                LIMIT ?
            """,
                (f"%{query}%", f"%{query}%", limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def export_summary(self) -> str:
        """Export summary as formatted string."""
        analysis = self.analyze_coverage()
        tables = self.get_tables()

        output = []
        output.append("=" * 80)
        output.append(f"DATABASE SUMMARY: {analysis['database']}")
        output.append("=" * 80)
        output.append(f"\nTotal Tables: {len(tables)}\n")

        for table_name, table_info in analysis["tables"].items():
            output.append(f"📋 {table_name}:")
            for key, value in table_info.items():
                output.append(f"   {key}: {value}")
            output.append("")

        return "\n".join(output)


def main():
    """CLI interface for database inspection."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python db_inspector.py --db [harvested|agentic] [--schema|--table TABLE|--coverage]")
        sys.exit(1)

    db_choice = "harvested"
    action = "schema"

    if "--db" in sys.argv:
        idx = sys.argv.index("--db")
        if idx + 1 < len(sys.argv):
            db_choice = sys.argv[idx + 1]

    if "--schema" in sys.argv:
        action = "schema"
    elif "--table" in sys.argv:
        action = "table"
        idx = sys.argv.index("--table")
        if idx + 1 < len(sys.argv):
            table_name = sys.argv[idx + 1]
    elif "--coverage" in sys.argv:
        action = "coverage"

    # Find database
    db_paths = {
        "harvested": "database/harvested.db",
        "agentic": "Layer_2_Agentic/db/agentic.db",
    }

    db_path = db_paths.get(db_choice)
    if not db_path:
        print(f"❌ Unknown database: {db_choice}")
        sys.exit(1)

    with DatabaseInspector(db_path) as inspector:
        if action == "schema":
            inspector.print_schema()
        elif action == "table" and "table_name" in locals():
            inspector.print_table_details(table_name)
        elif action == "coverage":
            print(inspector.export_summary())


if __name__ == "__main__":
    main()
