#!/usr/bin/env python3
"""
Comprehensive System Testing and Analysis

1. Tests parallel strategy with real queries from test_results
2. Documents state graph flow
3. Performs performance analysis
4. Reviews error handling patterns
"""

import sqlite3
import sys
import time
import json
import subprocess
from pathlib import Path

# Get actual project root (go up from tests/utilities/ to project root)
project_root = Path(__file__).parent.parent.parent

from agentic_reasoning.config.config_loader import CONFIG


def get_test_queries_from_db(limit=5):
    """Get successful test queries from harvested.db."""
    db_path = project_root / "data" / "database" / "harvested.db"

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get successful queries with different categories
        cursor.execute(
            """
            SELECT test_query, category, execution_time_seconds 
            FROM test_results 
            WHERE status = 'SUCCESS' 
            AND test_query IS NOT NULL
            ORDER BY execution_time_seconds ASC
            LIMIT ?
        """,
            (limit,),
        )

        queries = cursor.fetchall()
        conn.close()

        print(f"📊 Found {len(queries)} successful test queries:")
        test_queries = []
        for i, (query, category, exec_time) in enumerate(queries, 1):
            print(f"  {i}. [{category}] {query[:60]}... ({exec_time:.1f}s)")
            test_queries.append(query)

        return test_queries

    except Exception as e:
        print(f"❌ Error getting test queries: {e}")
        return []


def configure_parallel_only():
    """Configure system to test only parallel strategy."""
    config_path = project_root / "agentic_reasoning" / "config" / "strategy_testing.py"

    # Read current config
    with open(config_path, "r") as f:
        content = f.read()

    # Update for parallel-only testing
    new_content = content.replace(
        'TESTING_MODE = "ALL_ENABLED"', 'TESTING_MODE = "SINGLE_STRATEGY"'
    ).replace(
        '"Parallel multi-source search": False,',
        '"Parallel multi-source search": True,',
    )

    # Ensure other strategies are disabled
    lines = new_content.split("\n")
    updated_lines = []
    for line in lines:
        if (
            ": True," in line
            and "Parallel multi-source search" not in line
            and "STRATEGY_TEST_CONFIG" not in line
        ):
            # Disable other strategies
            updated_lines.append(line.replace(": True,", ": False,"))
        else:
            updated_lines.append(line)

    with open(config_path, "w") as f:
        f.write("\n".join(updated_lines))

    print("✅ Configured for parallel strategy testing")


def restore_config():
    """Restore normal configuration."""
    config_path = project_root / "agentic_reasoning" / "config" / "strategy_testing.py"

    with open(config_path, "r") as f:
        content = f.read()

    new_content = content.replace(
        'TESTING_MODE = "SINGLE_STRATEGY"', 'TESTING_MODE = "ALL_ENABLED"'
    )

    with open(config_path, "w") as f:
        f.write(new_content)

    print("✅ Restored normal configuration")


def test_parallel_strategy(test_queries):
    """Test parallel strategy with real queries."""
    print("\n🚀 PARALLEL STRATEGY TESTING")
    print("=" * 50)

    results = []

    for i, query in enumerate(test_queries[:3], 1):  # Test first 3 queries
        print(f"\n📝 Test {i}: {query[:50]}...")

        # Update main.py with test query
        main_path = project_root / "main.py"

        with open(main_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace the query
        updated_content = content
        lines = content.split("\n")
        for j, line in enumerate(lines):
            if "user_query = " in line and ("shell size" in line or "torque" in line):
                lines[j] = f'    user_query = "{query}"'
                break

        with open(main_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # Run test
        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, "main.py"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=90,
            )

            end_time = time.time()
            execution_time = end_time - start_time

            # Analyze output
            success = "✅ Completed successfully!" in result.stdout
            parallel_used = "Parallel multi-source search" in result.stdout
            function_count = result.stdout.count("🚀 Starting:")

            print(f"  ⏱️  Time: {execution_time:.2f}s")
            print(f"  🎯 Success: {success}")
            print(f"  📊 Used Parallel: {parallel_used}")
            print(f"  🔧 Functions executed: {function_count}")

            results.append(
                {
                    "query": query[:50],
                    "success": success,
                    "parallel_used": parallel_used,
                    "execution_time": execution_time,
                    "function_count": function_count,
                }
            )

        except subprocess.TimeoutExpired:
            print(f"  ⏰ Timeout after 90s")
            results.append(
                {
                    "query": query[:50],
                    "success": False,
                    "parallel_used": False,
                    "execution_time": 90,
                    "timeout": True,
                }
            )
        except Exception as e:
            print(f"  ❌ Error: {e}")

    return results


def document_state_graph_flow():
    """Document the LangGraph workflow."""
    print("\n📋 STATE GRAPH FLOW DOCUMENTATION")
    print("=" * 50)

    workflow_nodes = [
        (
            "node_goal_define",
            "Goal Definition",
            "Creates/reuses goal instance, extracts key terms with LLM",
        ),
        (
            "node_strategy_plan",
            "Strategy Selection",
            "Selects strategy from library using LLM, creates function instances",
        ),
        (
            "node_function_execute",
            "Function Execution",
            "Central dispatcher for sequential/parallel function execution",
        ),
        (
            "node_function_validate",
            "Function Validation",
            "Validates function outputs against expected schemas",
        ),
        (
            "node_strategy_validate",
            "Strategy Validation",
            "Tracks strategy completion, implements tri-condition routing",
        ),
        (
            "node_goal_validate",
            "Goal Validation",
            "LLM judge determines if goal is satisfied",
        ),
        ("node_done", "Completion", "Terminal node for successful workflows"),
    ]

    print("🔄 WORKFLOW NODES:")
    for node_name, display_name, description in workflow_nodes:
        print(f"  • {display_name} ({node_name})")
        print(f"    └─ {description}")

    print("\n🎯 ROUTING LOGIC:")
    routing_rules = [
        ("GoalDefine → StrategyPlan", "Always routes to strategy selection"),
        ("StrategyPlan → FunctionExecute", "Routes to function execution"),
        ("FunctionExecute → FunctionValidate", "Validates function outputs"),
        ("FunctionValidate → StrategyValidate", "Checks strategy progress"),
        ("StrategyValidate → FunctionExecute", "If more functions pending"),
        ("StrategyValidate → GoalValidate", "If strategy completed successfully"),
        ("StrategyValidate → StrategyPlan", "If strategy failed, try new strategy"),
        ("GoalValidate → Done", "If goal satisfied"),
        ("GoalValidate → StrategyPlan", "If goal not satisfied, try new strategy"),
    ]

    for route, condition in routing_rules:
        print(f"  • {route}")
        print(f"    └─ {condition}")

    print("\n⚡ TRI-CONDITION ROUTING:")
    tri_conditions = [
        (
            "strategySatisfied=True + strategyAborted=False",
            "All functions succeeded → GoalValidate",
        ),
        (
            "strategySatisfied=True + strategyAborted=True",
            "Some functions failed → StrategyPlan (new strategy)",
        ),
        (
            "strategySatisfied=False + strategyAborted=False",
            "Functions pending → FunctionExecute",
        ),
    ]

    for condition, action in tri_conditions:
        print(f"  • {condition}")
        print(f"    └─ {action}")


def analyze_performance_bottlenecks():
    """Analyze system performance patterns."""
    print("\n⚡ PERFORMANCE BOTTLENECK ANALYSIS")
    print("=" * 50)

    # Read some key files to analyze
    key_files = [
        ("workflow_nodes.py", "Core workflow execution"),
        ("function_library.py", "Function implementations"),
        ("database_manager.py", "Database operations"),
    ]

    bottlenecks_found = []

    for filename, description in key_files:
        file_path = project_root / "agentic_reasoning" / "logic" / filename
        if file_path.exists():
            with open(file_path, "r") as f:
                content = f.read()

            # Look for performance anti-patterns
            line_count = len(content.split("\n"))

            # Count database queries
            db_queries = content.count("cur.execute(") + content.count(
                "cursor.execute("
            )

            # Count LLM calls
            llm_calls = (
                content.count(".invoke(")
                + content.count("get_basic_llm()")
                + content.count("get_reasoning_llm()")
            )

            # Count loops with DB operations
            loop_db_pattern = 0
            lines = content.split("\n")
            in_loop = False
            for line in lines:
                if "for " in line or "while " in line:
                    in_loop = True
                elif in_loop and ("execute(" in line or ".invoke(" in line):
                    loop_db_pattern += 1
                elif line.strip() == "" or not line.startswith(" "):
                    in_loop = False

            print(f"📊 {filename} ({description}):")
            print(f"  • Lines of code: {line_count}")
            print(f"  • Database queries: {db_queries}")
            print(f"  • LLM calls: {llm_calls}")
            print(f"  • Loop+DB/LLM patterns: {loop_db_pattern}")

            if loop_db_pattern > 3:
                bottlenecks_found.append(
                    f"{filename}: {loop_db_pattern} potential loop bottlenecks"
                )
            if llm_calls > 10:
                bottlenecks_found.append(
                    f"{filename}: {llm_calls} LLM calls (consider batching)"
                )

    print(f"\n🚨 BOTTLENECKS IDENTIFIED:")
    if bottlenecks_found:
        for bottleneck in bottlenecks_found:
            print(f"  ⚠️ {bottleneck}")
    else:
        print("  ✅ No major bottlenecks detected")

    print(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
    recommendations = [
        "Cache LLM responses for repeated queries",
        "Use database connection pooling",
        "Implement async execution for I/O operations",
        "Add query result memoization",
        "Batch database operations where possible",
        "Profile actual execution to identify hotspots",
    ]

    for rec in recommendations:
        print(f"  ✅ {rec}")


def analyze_error_handling():
    """Analyze error handling patterns."""
    print("\n🚨 ERROR HANDLING PATTERN ANALYSIS")
    print("=" * 50)

    # Analyze error patterns in key files
    error_patterns = {
        "try_catch_blocks": 0,
        "function_return_tuples": 0,
        "context_managers": 0,
        "custom_exceptions": 0,
        "error_logging": 0,
    }

    key_files = ["workflow_nodes.py", "function_library.py", "database_manager.py"]

    for filename in key_files:
        file_path = project_root / "agentic_reasoning" / "logic" / filename
        if file_path.exists():
            with open(file_path, "r") as f:
                content = f.read()

            # Count error handling patterns
            error_patterns["try_catch_blocks"] += content.count("try:")
            error_patterns["function_return_tuples"] += content.count("return (")
            error_patterns["context_managers"] += content.count("with ")
            error_patterns["custom_exceptions"] += content.count(
                "Exception("
            ) + content.count("RuntimeError(")
            error_patterns["error_logging"] += content.count(
                "debug.print_error"
            ) + content.count("logger.error")

    print("📊 ERROR HANDLING PATTERNS:")
    for pattern, count in error_patterns.items():
        print(f"  • {pattern.replace('_', ' ').title()}: {count}")

    print("\n✅ CURRENT STRENGTHS:")
    strengths = [
        "Function return tuples for consistent error signaling",
        "Database context managers for resource cleanup",
        "Try-catch blocks for exception handling",
        "Debug system for error visibility",
    ]

    for strength in strengths:
        print(f"  ✅ {strength}")

    print("\n⚠️ IMPROVEMENT OPPORTUNITIES:")
    improvements = [
        "Add custom exception classes for different error types",
        "Implement retry mechanisms for transient failures",
        "Add input validation schemas",
        "Enhance error context and actionable messages",
        "Add error aggregation and reporting",
        "Implement circuit breaker patterns for external services",
    ]

    for improvement in improvements:
        print(f"  💡 {improvement}")


def main():
    """Main comprehensive analysis."""
    print("🚀 COMPREHENSIVE SYSTEM ANALYSIS & TESTING")
    print("=" * 70)

    # Step 1: Get test queries
    print("📂 Step 1: Loading test queries from harvested.db...")
    test_queries = get_test_queries_from_db(5)

    if not test_queries:
        print("❌ No test queries available")
        test_queries = [
            "What is the shell size for connector C0000268-11105?",
            "Find the torque specification for RPT2354313/350",
            "What is the cable entry diameter for C0001686-61701?",
        ]
        print("🔄 Using default test queries")

    # Step 2: Test parallel strategy
    print("\n⚙️ Step 2: Configuring and testing parallel strategy...")
    configure_parallel_only()

    try:
        results = test_parallel_strategy(test_queries)

        # Analyze parallel test results
        print(f"\n📊 PARALLEL STRATEGY RESULTS:")
        successful = sum(1 for r in results if r.get("success", False))
        parallel_used = sum(1 for r in results if r.get("parallel_used", False))
        avg_time = (
            sum(r.get("execution_time", 0) for r in results) / len(results)
            if results
            else 0
        )

        print(
            f"  • Success rate: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)"
        )
        print(f"  • Used parallel strategy: {parallel_used}/{len(results)}")
        print(f"  • Average execution time: {avg_time:.2f}s")

    finally:
        restore_config()

    # Step 3: Document workflow
    document_state_graph_flow()

    # Step 4: Performance analysis
    analyze_performance_bottlenecks()

    # Step 5: Error handling analysis
    analyze_error_handling()

    print("\n✅ COMPREHENSIVE ANALYSIS COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    main()


