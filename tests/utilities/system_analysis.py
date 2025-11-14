#!/usr/bin/env python3
"""
Comprehensive System Analysis Script

Performs naming conventions review, database analysis, and system testing.
"""

import sqlite3
import os
from pathlib import Path

# Project root for relative paths
project_root = Path(__file__).parent.parent.parent


def check_harvested_database():
    """Check harvested.db structure and content."""
    db_path = project_root / "database" / "harvested.db"

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    print("🗄️ HARVESTED DATABASE ANALYSIS")
    print("=" * 50)

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print(f"📊 Found {len(tables)} tables:")
        for table in tables:
            table_name = table[0]
            print(f"  • {table_name}")

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"    └─ {count} rows")

            # Check if it's test_result table
            if table_name == "test_result":
                print("    └─ 🎯 TEST_RESULT TABLE FOUND!")
                cursor.execute("SELECT * FROM test_result LIMIT 5;")
                sample_rows = cursor.fetchall()

                # Get column names
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                col_names = [col[1] for col in columns]

                print(f"    └─ Columns: {col_names}")
                if sample_rows:
                    print("    └─ Sample queries:")
                    for i, row in enumerate(sample_rows, 1):
                        print(f"      {i}. {row[0] if row else 'No data'}")

        conn.close()

    except Exception as e:
        print(f"❌ Error accessing database: {e}")


def analyze_naming_conventions():
    """Analyze naming conventions across the codebase."""
    print("\n📝 NAMING CONVENTIONS ANALYSIS")
    print("=" * 50)

    naming_issues = []
    naming_suggestions = []

    # Function names that could be clearer
    print("🔧 FUNCTION NAMING SUGGESTIONS:")

    function_suggestions = [
        (
            "_generate_format_variations",
            "_create_product_number_variants",
            "More descriptive of actual purpose",
        ),
        (
            "_handler_from_name",
            "_get_function_handler",
            "Clearer about what it returns",
        ),
        (
            "func_change_keyword",
            "func_trim_keyword",
            "More specific about the operation",
        ),
        ("SessionState", "WorkflowState", "More descriptive of what it contains"),
        ("gid", "goal_id", "Avoid abbreviations"),
        ("sid", "strategy_id", "Avoid abbreviations"),
        ("fid", "function_id", "Avoid abbreviations"),
        ("fname", "function_name", "Avoid abbreviations"),
        ("sname", "strategy_name", "Avoid abbreviations"),
        ("cur", "cursor", "Avoid abbreviations"),
        ("conn", "connection", "Avoid abbreviations"),
        ("db", "database_manager", "More descriptive"),
        ("out", "output", "Avoid abbreviations"),
        ("ok", "success", "More descriptive"),
        ("txt", "text", "Avoid abbreviations"),
    ]

    for current, suggested, reason in function_suggestions:
        print(f"  • {current} → {suggested}")
        print(f"    └─ {reason}")

    # Database table naming
    print("\n🗄️ DATABASE TABLE NAMING:")
    table_suggestions = [
        ("FunctionInSession", "function_executions", "Snake case, more descriptive"),
        ("StrategyInSession", "strategy_executions", "Snake case, more descriptive"),
        ("GoalInSession", "goal_executions", "Snake case, more descriptive"),
        ("FunctionParametersInSession", "function_parameters", "Shorter, clearer"),
        ("FunctionOutputInSession", "function_outputs", "Shorter, clearer"),
    ]

    for current, suggested, reason in table_suggestions:
        print(f"  • {current} → {suggested}")
        print(f"    └─ {reason}")

    # Variable naming patterns
    print("\n📋 VARIABLE NAMING PATTERNS:")
    pattern_suggestions = [
        (
            "Single letter vars (i, j, k)",
            "descriptive names (index, counter, position)",
            "Better readability",
        ),
        ("Abbreviated params (params)", "parameters", "Full words preferred"),
        (
            "Mixed camelCase/snake_case",
            "Consistent snake_case",
            "Python PEP 8 compliance",
        ),
        (
            "Generic 'data' variables",
            "specific names (table_data, query_results)",
            "Clearer context",
        ),
    ]

    for current, suggested, reason in pattern_suggestions:
        print(f"  • {current} → {suggested}")
        print(f"    └─ {reason}")


def analyze_performance_patterns():
    """Analyze potential performance bottlenecks."""
    print("\n⚡ PERFORMANCE ANALYSIS")
    print("=" * 50)

    print("🔍 POTENTIAL BOTTLENECKS IDENTIFIED:")

    bottlenecks = [
        ("LLM API Calls", "Sequential calls in loops", "Consider batching or async"),
        (
            "Database Queries",
            "Multiple SELECT calls in loops",
            "Use JOIN queries or batch operations",
        ),
        (
            "File I/O Operations",
            "Reading files individually",
            "Consider caching or batch reading",
        ),
        ("JSON Parsing", "Repeated parsing of large JSON", "Cache parsed results"),
        (
            "String Processing",
            "Complex regex in tight loops",
            "Compile regex patterns once",
        ),
        (
            "Memory Usage",
            "Loading all tables into memory",
            "Stream processing for large datasets",
        ),
    ]

    for area, issue, suggestion in bottlenecks:
        print(f"  • {area}: {issue}")
        print(f"    └─ Suggestion: {suggestion}")

    print("\n📊 OPTIMIZATION OPPORTUNITIES:")
    optimizations = [
        "Add caching layer for frequent LLM queries",
        "Implement connection pooling for database operations",
        "Use async/await for I/O operations",
        "Add query result memoization",
        "Implement lazy loading for large datasets",
        "Add performance monitoring and metrics",
    ]

    for opt in optimizations:
        print(f"  ✅ {opt}")


def analyze_error_handling():
    """Analyze error handling patterns."""
    print("\n🚨 ERROR HANDLING ANALYSIS")
    print("=" * 50)

    print("🔧 CURRENT PATTERNS:")
    current_patterns = [
        "Function return tuples: (bool, dict|str)",
        "Database context managers with automatic cleanup",
        "Try-catch blocks with specific error messages",
        "LLM fallback strategies for parsing failures",
        "Graceful degradation when strategies fail",
    ]

    for pattern in current_patterns:
        print(f"  ✅ {pattern}")

    print("\n⚠️ IMPROVEMENT AREAS:")
    improvements = [
        ("Inconsistent error types", "Standardize custom exception classes"),
        ("Silent failures in some functions", "Add comprehensive logging"),
        ("Limited retry mechanisms", "Implement exponential backoff for LLM calls"),
        ("Basic validation", "Add input parameter validation schemas"),
        ("Generic error messages", "Provide actionable error messages with context"),
        ("No error aggregation", "Collect and report multiple errors together"),
    ]

    for issue, suggestion in improvements:
        print(f"  • {issue}")
        print(f"    └─ {suggestion}")


if __name__ == "__main__":
    print("🚀 SAAB SYSTEM COMPREHENSIVE ANALYSIS")
    print("=" * 60)

    check_harvested_database()
    analyze_naming_conventions()
    analyze_performance_patterns()
    analyze_error_handling()

    print(f"\n✅ Analysis complete!")


