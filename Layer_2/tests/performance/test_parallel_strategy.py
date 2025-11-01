#!/usr/bin/env python3
"""
Parallel Strategy Testing Script

Tests the parallel strategy with different queries and analyzes performance.
"""

import sqlite3
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agentic_reasoning.config.strategy_testing import STRATEGY_TEST_CONFIG, TESTING_MODE


def get_successful_test_queries(limit=10):
    """Get successful queries from harvested.db test_results table."""
    db_path = project_root / "data" / "database" / "harvested.db"

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return []

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get table info first
        cursor.execute("PRAGMA table_info(test_results);")
        columns = cursor.fetchall()
        print("📊 test_results table columns:")
        for col in columns:
            print(f"  • {col[1]} ({col[2]})")

        # Get sample successful queries
        cursor.execute("SELECT * FROM test_results LIMIT ?;", (limit,))
        rows = cursor.fetchall()

        conn.close()

        if rows:
            print(f"\n✅ Found {len(rows)} test queries")
            queries = []
            for i, row in enumerate(rows, 1):
                query_text = str(row[0]) if row else f"Query {i}"
                queries.append(query_text)
                print(f"  {i}. {query_text[:80]}...")

            return queries
        else:
            print("❌ No test queries found")
            return []

    except Exception as e:
        print(f"❌ Error accessing test_results: {e}")
        return []


def configure_parallel_strategy_only():
    """Configure system to test only parallel strategy."""
    config_path = project_root / "project_saab" / "config" / "strategy_testing.py"

    print("🔧 Configuring system for parallel strategy testing...")

    # Read current config
    with open(config_path, "r") as f:
        content = f.read()

    # Update for parallel testing
    new_content = content.replace(
        'TESTING_MODE = "ALL_ENABLED"', 'TESTING_MODE = "SINGLE_STRATEGY"'
    )

    # Enable only parallel strategy
    lines = new_content.split("\n")
    in_config_block = False
    updated_lines = []

    for line in lines:
        if "STRATEGY_TEST_CONFIG = {" in line:
            in_config_block = True
            updated_lines.append(line)
        elif in_config_block and "}" in line and "STRATEGY_TEST_CONFIG" not in line:
            in_config_block = False
            updated_lines.append(line)
        elif in_config_block:
            if '"Parallel multi-source search"' in line:
                updated_lines.append('    "Parallel multi-source search": True,')
            elif '": True,' in line or '": False,' in line:
                # Disable all other strategies
                strategy_name = line.split('"')[1]
                updated_lines.append(f'    "{strategy_name}": False,')
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    # Write updated config
    with open(config_path, "w") as f:
        f.write("\n".join(updated_lines))

    print("✅ Configured for parallel strategy testing")


def restore_normal_config():
    """Restore normal configuration."""
    config_path = project_root / "project_saab" / "config" / "strategy_testing.py"

    with open(config_path, "r") as f:
        content = f.read()

    # Restore to normal mode
    new_content = content.replace(
        'TESTING_MODE = "SINGLE_STRATEGY"', 'TESTING_MODE = "ALL_ENABLED"'
    )

    with open(config_path, "w") as f:
        f.write(new_content)

    print("✅ Restored normal configuration")


def test_parallel_strategy_performance(queries):
    """Test parallel strategy with different queries and measure performance."""
    print("\n🚀 TESTING PARALLEL STRATEGY PERFORMANCE")
    print("=" * 60)

    results = []

    for i, query in enumerate(queries[:5], 1):  # Test first 5 queries
        print(f"\n📝 Test {i}: {query[:60]}...")

        # Modify main.py to use this query temporarily
        main_path = project_root / "main.py"

        # Read main.py
        with open(main_path, "r", encoding="utf-8") as f:
            main_content = f.read()

        # Find and replace the query line
        lines = main_content.split("\n")
        updated_lines = []

        for line in lines:
            if "user_query = " in line and "what is the shell size" in line:
                updated_lines.append(f'    user_query = "{query}"')
            else:
                updated_lines.append(line)

        # Write updated main.py
        with open(main_path, "w", encoding="utf-8") as f:
            f.write("\n".join(updated_lines))

        # Run the test and measure time
        start_time = time.time()

        try:
            import subprocess

            result = subprocess.run(
                [sys.executable, "main.py"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
            )

            end_time = time.time()
            execution_time = end_time - start_time

            # Analyze output
            success = "✅ Completed successfully!" in result.stdout
            strategy_used = "Parallel multi-source search" in result.stdout
            function_count = result.stdout.count("🚀 Starting:")

            result_data = {
                "query": query[:60],
                "success": success,
                "strategy_used": strategy_used,
                "execution_time": execution_time,
                "function_count": function_count,
                "output_length": len(result.stdout),
            }

            results.append(result_data)

            print(f"  ⏱️  Time: {execution_time:.2f}s")
            print(f"  🎯 Success: {success}")
            print(f"  📊 Strategy: {'Parallel' if strategy_used else 'Other'}")
            print(f"  🔧 Functions: {function_count}")

            if not success:
                print(f"  ❌ Error output: {result.stderr[:200]}...")

        except subprocess.TimeoutExpired:
            print(f"  ⏰ Test {i} timed out after 2 minutes")
            results.append(
                {
                    "query": query[:60],
                    "success": False,
                    "strategy_used": False,
                    "execution_time": 120,
                    "function_count": 0,
                    "timeout": True,
                }
            )

        except Exception as e:
            print(f"  ❌ Test {i} failed: {e}")
            results.append(
                {
                    "query": query[:60],
                    "success": False,
                    "strategy_used": False,
                    "execution_time": 0,
                    "function_count": 0,
                    "error": str(e),
                }
            )

    return results


def analyze_test_results(results):
    """Analyze and report test results."""
    print("\n📊 PARALLEL STRATEGY TEST RESULTS")
    print("=" * 60)

    if not results:
        print("❌ No results to analyze")
        return

    successful_tests = [r for r in results if r.get("success", False)]
    parallel_tests = [r for r in results if r.get("strategy_used", False)]

    print(f"📈 SUMMARY:")
    print(f"  • Total Tests: {len(results)}")
    print(
        f"  • Successful: {len(successful_tests)} ({len(successful_tests)/len(results)*100:.1f}%)"
    )
    print(
        f"  • Used Parallel Strategy: {len(parallel_tests)} ({len(parallel_tests)/len(results)*100:.1f}%)"
    )

    if successful_tests:
        avg_time = sum(r["execution_time"] for r in successful_tests) / len(
            successful_tests
        )
        avg_functions = sum(r["function_count"] for r in successful_tests) / len(
            successful_tests
        )

        print(f"  • Average Execution Time: {avg_time:.2f}s")
        print(f"  • Average Function Count: {avg_functions:.1f}")

    print("\n📋 DETAILED RESULTS:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get("success") else "❌"
        strategy = "📈" if result.get("strategy_used") else "📊"
        time_str = f"{result.get('execution_time', 0):.1f}s"

        print(f"  {i}. {status} {strategy} {time_str} - {result['query']}")

        if "timeout" in result:
            print(f"     ⏰ Timed out")
        elif "error" in result:
            print(f"     ❌ Error: {result['error']}")


def main():
    """Main testing function."""
    print("🧪 PARALLEL STRATEGY COMPREHENSIVE TESTING")
    print("=" * 70)

    # Step 1: Get test queries from database
    print("📂 Step 1: Loading test queries from harvested.db...")
    queries = get_successful_test_queries(10)

    if not queries:
        print("❌ No queries available for testing")
        return

    # Step 2: Configure for parallel testing
    print("\n⚙️ Step 2: Configuring system for parallel strategy testing...")
    configure_parallel_strategy_only()

    try:
        # Step 3: Run performance tests
        print("\n🚀 Step 3: Running parallel strategy performance tests...")
        results = test_parallel_strategy_performance(queries)

        # Step 4: Analyze results
        print("\n📊 Step 4: Analyzing test results...")
        analyze_test_results(results)

    finally:
        # Step 5: Restore configuration
        print("\n🔄 Step 5: Restoring normal configuration...")
        restore_normal_config()

    print("\n✅ Parallel strategy testing complete!")


if __name__ == "__main__":
    main()


