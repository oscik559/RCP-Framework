#!/usr/bin/env python3
"""
Consolidated Database Check Utilities

This module consolidates various database checking utilities into a single,
comprehensive tool for system validation and debugging.
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def check_database_schema(db_path: str) -> Dict:
    """Check database schema and structure"""
    results = {"database": db_path, "tables": [], "status": "unknown"}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        for (table_name,) in tables:
            # Get table info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]

            table_info = {
                "name": table_name,
                "columns": [{"name": col[1], "type": col[2]} for col in columns],
                "row_count": row_count,
            }
            results["tables"].append(table_info)

        results["status"] = "success"
        conn.close()

    except Exception as e:
        results["status"] = f"error: {e}"

    return results


def check_workflow_data() -> Dict:
    """Check workflow execution data"""
    results = {
        "goals": 0,
        "strategies": 0,
        "functions": 0,
        "latest_execution": None,
        "status": "unknown",
    }

    try:
        conn = sqlite3.connect("../database/agentic.db")
        cursor = conn.cursor()

        # Count records
        cursor.execute("SELECT COUNT(*) FROM GoalInSession")
        results["goals"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM StrategyInSession")
        results["strategies"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM FunctionInSession")
        results["functions"] = cursor.fetchone()[0]

        # Get latest execution info
        cursor.execute(
            """
            SELECT GoalID, GoalSuccess, GoalName 
            FROM GoalInSession 
            ORDER BY GoalID DESC 
            LIMIT 1
        """
        )
        latest = cursor.fetchone()
        if latest:
            results["latest_execution"] = {
                "goal_id": latest[0],
                "success": latest[1],
                "name": latest[2],
            }

        results["status"] = "success"
        conn.close()

    except Exception as e:
        results["status"] = f"error: {e}"

    return results


def check_extracted_data() -> Dict:
    """Check extracted PDF data"""
    results = {"documents": 0, "tables": 0, "images": 0, "status": "unknown"}

    try:
        conn = sqlite3.connect("../database/harvested.db")
        cursor = conn.cursor()

        # Count extracted data
        cursor.execute("SELECT COUNT(DISTINCT filename) FROM extracted_tables")
        results["documents"] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM extracted_tables WHERE tablecontent IS NOT NULL"
        )
        results["tables"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM saved_images")
        results["images"] = cursor.fetchone()[0]

        results["status"] = "success"
        conn.close()

    except Exception as e:
        results["status"] = f"error: {e}"

    return results


def check_temp_database() -> Dict:
    """Check temporary database status"""
    results = {"exists": False, "tables": 0, "records": 0, "status": "unknown"}

    temp_db_path = "../database/temp.db"

    try:
        if Path(temp_db_path).exists():
            results["exists"] = True
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()

            # Get table count
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            results["tables"] = cursor.fetchone()[0]

            # Get total records (if temp_records table exists)
            try:
                cursor.execute("SELECT COUNT(*) FROM temp_records")
                results["records"] = cursor.fetchone()[0]
            except:
                pass

            conn.close()

        results["status"] = "success"

    except Exception as e:
        results["status"] = f"error: {e}"

    return results


def check_system_health() -> Dict:
    """Comprehensive system health check"""
    print("🔍 SAAB System Health Check")
    print("=" * 50)

    # Check databases
    print("\n📊 Database Status:")

    # Agentic database
    agentic_results = check_database_schema("../database/agentic.db")
    workflow_data = check_workflow_data()
    print(f"  ✅ Agentic DB: {len(agentic_results['tables'])} tables")
    print(f"     • Goals: {workflow_data['goals']}")
    print(f"     • Strategies: {workflow_data['strategies']}")
    print(f"     • Functions: {workflow_data['functions']}")

    # Harvested database
    harvested_results = check_database_schema("../database/harvested.db")
    extracted_data = check_extracted_data()
    print(f"  ✅ Harvested DB: {len(harvested_results['tables'])} tables")
    print(f"     • Documents: {extracted_data['documents']}")
    print(f"     • Tables: {extracted_data['tables']}")
    print(f"     • Images: {extracted_data['images']}")

    # Temporary database
    temp_data = check_temp_database()
    temp_status = "exists" if temp_data["exists"] else "clean"
    print(f"  ✅ Temp DB: {temp_status}")
    if temp_data["exists"]:
        print(f"     • Tables: {temp_data['tables']}")
        print(f"     • Records: {temp_data['records']}")

    # Check latest execution
    if workflow_data["latest_execution"]:
        latest = workflow_data["latest_execution"]
        success_icon = "✅" if latest["success"] else "❌"
        print(f"\n🎯 Latest Execution:")
        print(f"  {success_icon} Goal {latest['goal_id']}: {latest['name']}")
        print(f"     Success: {latest['success']}")

    return {
        "agentic": agentic_results,
        "harvested": harvested_results,
        "temp": temp_data,
        "workflow": workflow_data,
        "extracted": extracted_data,
    }


def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="SAAB System Database Checker")
    parser.add_argument("--schema", help="Check specific database schema")
    parser.add_argument("--workflow", action="store_true", help="Check workflow data")
    parser.add_argument("--extracted", action="store_true", help="Check extracted data")
    parser.add_argument("--temp", action="store_true", help="Check temp database")
    parser.add_argument("--all", action="store_true", help="Run all checks")

    args = parser.parse_args()

    if args.all or not any([args.schema, args.workflow, args.extracted, args.temp]):
        check_system_health()
    else:
        if args.schema:
            results = check_database_schema(args.schema)
            print(f"Schema for {args.schema}:")
            for table in results["tables"]:
                print(f"  📋 {table['name']}: {table['row_count']} rows")

        if args.workflow:
            results = check_workflow_data()
            print(f"Workflow Data: {results}")

        if args.extracted:
            results = check_extracted_data()
            print(f"Extracted Data: {results}")

        if args.temp:
            results = check_temp_database()
            print(f"Temp Database: {results}")


if __name__ == "__main__":
    main()


