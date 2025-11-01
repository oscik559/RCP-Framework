#!/usr/bin/env python3
"""
Query Analysis and Testing Utilities

This module provides utilities for analyzing query patterns, testing strategies,
and examining failed test results.
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def analyze_query_patterns() -> Dict:
    """Analyze patterns in query execution"""
    results = {
        "total_goals": 0,
        "successful_goals": 0,
        "success_rate": 0.0,
        "strategy_patterns": {},
        "common_failures": [],
        "performance_metrics": {},
    }

    try:
        conn = sqlite3.connect("../data/database/agentic.db")
        cursor = conn.cursor()

        # Basic success metrics
        cursor.execute("SELECT COUNT(*) FROM GoalInSession")
        results["total_goals"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM GoalInSession WHERE GoalSuccess = 1")
        results["successful_goals"] = cursor.fetchone()[0]

        if results["total_goals"] > 0:
            results["success_rate"] = (
                results["successful_goals"] / results["total_goals"]
            )

        # Strategy patterns
        cursor.execute(
            """
            SELECT s.StrategyName, COUNT(*) as usage_count,
                   SUM(CASE WHEN s.StrategySuccess = 1 THEN 1 ELSE 0 END) as success_count
            FROM StrategyInSession s
            GROUP BY s.StrategyName
            ORDER BY usage_count DESC
        """
        )

        strategy_data = cursor.fetchall()
        for strategy, usage, successes in strategy_data:
            success_rate = successes / usage if usage > 0 else 0
            results["strategy_patterns"][strategy] = {
                "usage_count": usage,
                "success_count": successes,
                "success_rate": success_rate,
            }

        # Common failure patterns
        cursor.execute(
            """
            SELECT s.StrategyName, s.StrategyFailureReason, COUNT(*) as failure_count
            FROM StrategyInSession s
            WHERE s.StrategySuccess = 0 AND s.StrategyFailureReason IS NOT NULL
            GROUP BY s.StrategyName, s.StrategyFailureReason
            ORDER BY failure_count DESC
            LIMIT 10
        """
        )

        failure_data = cursor.fetchall()
        for strategy, reason, count in failure_data:
            results["common_failures"].append(
                {"strategy": strategy, "reason": reason, "count": count}
            )

        conn.close()
        results["status"] = "success"

    except Exception as e:
        results["status"] = f"error: {e}"

    return results


def analyze_function_performance() -> Dict:
    """Analyze function execution performance"""
    results = {"function_stats": {}, "execution_times": {}, "failure_analysis": {}}

    try:
        conn = sqlite3.connect("../data/database/agentic.db")
        cursor = conn.cursor()

        # Function execution statistics
        cursor.execute(
            """
            SELECT f.FunctionName, 
                   COUNT(*) as total_executions,
                   SUM(CASE WHEN f.FunctionSuccess = 1 THEN 1 ELSE 0 END) as successful_executions,
                   AVG(CASE WHEN f.FunctionSuccess = 1 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM FunctionInSession f
            GROUP BY f.FunctionName
            ORDER BY total_executions DESC
        """
        )

        function_data = cursor.fetchall()
        for func_name, total, successful, success_rate in function_data:
            results["function_stats"][func_name] = {
                "total_executions": total,
                "successful_executions": successful,
                "success_rate": success_rate,
            }

        # Function failure analysis
        cursor.execute(
            """
            SELECT f.FunctionName, f.FunctionFailureReason, COUNT(*) as failure_count
            FROM FunctionInSession f
            WHERE f.FunctionSuccess = 0 AND f.FunctionFailureReason IS NOT NULL
            GROUP BY f.FunctionName, f.FunctionFailureReason
            ORDER BY failure_count DESC
        """
        )

        failure_data = cursor.fetchall()
        for func_name, reason, count in failure_data:
            if func_name not in results["failure_analysis"]:
                results["failure_analysis"][func_name] = []
            results["failure_analysis"][func_name].append(
                {"reason": reason, "count": count}
            )

        conn.close()
        results["status"] = "success"

    except Exception as e:
        results["status"] = f"error: {e}"

    return results


def get_failed_queries() -> List[Dict]:
    """Extract details about failed queries"""
    failed_queries = []

    try:
        conn = sqlite3.connect("../data/database/agentic.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT g.GoalID, g.GoalName, g.GoalFailureReason, g.UserQuery
            FROM GoalInSession g
            WHERE g.GoalSuccess = 0
            ORDER BY g.GoalID DESC
            LIMIT 50
        """
        )

        failures = cursor.fetchall()
        for goal_id, goal_name, failure_reason, user_query in failures:
            failed_queries.append(
                {
                    "goal_id": goal_id,
                    "goal_name": goal_name,
                    "failure_reason": failure_reason,
                    "user_query": user_query,
                }
            )

        conn.close()

    except Exception as e:
        print(f"Error retrieving failed queries: {e}")

    return failed_queries


def analyze_llm_context_usage() -> Dict:
    """Analyze LLM context and token usage patterns"""
    results = {"context_patterns": {}, "prompt_analysis": {}, "model_usage": {}}

    try:
        conn = sqlite3.connect("../data/database/agentic.db")
        cursor = conn.cursor()

        # Analyze strategy selection patterns
        cursor.execute(
            """
            SELECT s.StrategyName, s.StrategyPrompt, COUNT(*) as usage_count
            FROM StrategyInSession s
            WHERE s.StrategyPrompt IS NOT NULL
            GROUP BY s.StrategyName
            ORDER BY usage_count DESC
        """
        )

        strategy_prompts = cursor.fetchall()
        for strategy, prompt, count in strategy_prompts:
            if prompt:
                prompt_length = len(prompt)
                results["prompt_analysis"][strategy] = {
                    "usage_count": count,
                    "avg_prompt_length": prompt_length,
                }

        conn.close()
        results["status"] = "success"

    except Exception as e:
        results["status"] = f"error: {e}"

    return results


def check_test_structure() -> Dict:
    """Check the structure and organization of test files"""
    results = {"test_directories": {}, "test_files": {}, "coverage_analysis": {}}

    test_dir = Path("tests")
    if not test_dir.exists():
        results["status"] = "tests directory not found"
        return results

    # Analyze directory structure
    for item in test_dir.rglob("*"):
        if item.is_file() and item.suffix == ".py":
            relative_path = item.relative_to(test_dir)
            category = (
                str(relative_path.parent)
                if relative_path.parent != Path(".")
                else "root"
            )

            if category not in results["test_directories"]:
                results["test_directories"][category] = []

            results["test_directories"][category].append(str(relative_path.name))

            # Basic file analysis
            try:
                content = item.read_text(encoding="utf-8")
                results["test_files"][str(relative_path)] = {
                    "lines": len(content.splitlines()),
                    "size": len(content),
                    "has_main": "__main__" in content,
                    "has_tests": "def test_" in content or "class Test" in content,
                }
            except Exception as e:
                results["test_files"][str(relative_path)] = {"error": str(e)}

    results["status"] = "success"
    return results


def generate_query_report() -> str:
    """Generate a comprehensive query analysis report"""
    print("📊 SAAB Query Analysis Report")
    print("=" * 50)

    # Query patterns
    query_patterns = analyze_query_patterns()
    print(f"\n🎯 Query Success Metrics:")
    print(f"  • Total Goals: {query_patterns['total_goals']}")
    print(f"  • Successful: {query_patterns['successful_goals']}")
    print(f"  • Success Rate: {query_patterns['success_rate']:.1%}")

    # Strategy performance
    print(f"\n📋 Strategy Performance:")
    for strategy, stats in query_patterns["strategy_patterns"].items():
        print(
            f"  • {strategy}: {stats['success_rate']:.1%} ({stats['success_count']}/{stats['usage_count']})"
        )

    # Function performance
    function_perf = analyze_function_performance()
    print(f"\n⚙️ Function Performance:")
    for func_name, stats in function_perf["function_stats"].items():
        print(
            f"  • {func_name}: {stats['success_rate']:.1%} ({stats['successful_executions']}/{stats['total_executions']})"
        )

    # Common failures
    if query_patterns["common_failures"]:
        print(f"\n❌ Common Failure Patterns:")
        for failure in query_patterns["common_failures"][:5]:
            print(
                f"  • {failure['strategy']}: {failure['reason']} ({failure['count']} times)"
            )

    # Failed queries
    failed_queries = get_failed_queries()
    if failed_queries:
        print(f"\n🔍 Recent Failed Queries:")
        for query in failed_queries[:3]:
            print(f"  • Goal {query['goal_id']}: {query['user_query'][:60]}...")
            if query["failure_reason"]:
                print(f"    Reason: {query['failure_reason']}")

    return "Report generated successfully"


def main():
    """Main function for command-line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="SAAB Query Analysis Tool")
    parser.add_argument(
        "--patterns", action="store_true", help="Analyze query patterns"
    )
    parser.add_argument(
        "--functions", action="store_true", help="Analyze function performance"
    )
    parser.add_argument("--failures", action="store_true", help="Show failed queries")
    parser.add_argument("--report", action="store_true", help="Generate full report")
    parser.add_argument("--tests", action="store_true", help="Check test structure")

    args = parser.parse_args()

    if args.report or not any(
        [args.patterns, args.functions, args.failures, args.tests]
    ):
        generate_query_report()
    else:
        if args.patterns:
            patterns = analyze_query_patterns()
            print("Query Patterns:", json.dumps(patterns, indent=2))

        if args.functions:
            functions = analyze_function_performance()
            print("Function Performance:", json.dumps(functions, indent=2))

        if args.failures:
            failures = get_failed_queries()
            print("Failed Queries:", json.dumps(failures, indent=2))

        if args.tests:
            test_structure = check_test_structure()
            print("Test Structure:", json.dumps(test_structure, indent=2))


if __name__ == "__main__":
    main()


