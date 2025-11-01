"""
Strategy Performance Comparison Test
=====================================
Compares Enhanced lookup vs Parallel enhanced lookup strategies
for speed, performance, and result quality.
"""

import time
import traceback
import json
import csv
from datetime import datetime
from typing import Dict, List, Tuple, Any
from tabulate import tabulate

import sys
import os

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agentic_reasoning.logic.state_graph import get_graph
from agentic_reasoning.logic.types import SessionState
from agentic_reasoning.db.connection import get_agentic_connection
from agentic_reasoning.config.debug_config import debug


class StrategyComparator:
    """Compare different strategies on the same query"""

    def __init__(self):
        self.workflow = get_graph()
        # self.test_query = "What locator and crimptool is used for RPT2354313/350?"
        self.test_query = "What specifications apply to C0000658-13630?"

        self.strategies_to_test = [
            "Simple lookup",
            "Enhanced lookup",
            "Parallel enhanced lookup",
        ]
        self.original_config = None

    def backup_strategy_config(self):
        """Backup current strategy testing configuration"""
        try:
            from agentic_reasoning.config import strategy_testing

            self.original_config = {
                "STRATEGY_TEST_CONFIG": strategy_testing.STRATEGY_TEST_CONFIG.copy(),
                "TESTING_MODE": strategy_testing.TESTING_MODE,
            }
            print("📋 Backed up original strategy configuration")
        except Exception as e:
            print(f"⚠️  Warning: Could not backup strategy config: {e}")

    def restore_strategy_config(self):
        """Restore original strategy testing configuration"""
        try:
            if self.original_config:
                from agentic_reasoning.config import strategy_testing

                strategy_testing.STRATEGY_TEST_CONFIG = self.original_config[
                    "STRATEGY_TEST_CONFIG"
                ]
                strategy_testing.TESTING_MODE = self.original_config["TESTING_MODE"]
                print("🔄 Restored original strategy configuration")
        except Exception as e:
            print(f"⚠️  Warning: Could not restore strategy config: {e}")

    def configure_single_strategy(self, strategy_name: str):
        """Configure testing to use only one specific strategy"""
        try:
            from agentic_reasoning.config import strategy_testing

            # Set all strategies to False, then enable only the target strategy
            for key in strategy_testing.STRATEGY_TEST_CONFIG:
                strategy_testing.STRATEGY_TEST_CONFIG[key] = False

            # Enable only the target strategy
            if strategy_name in strategy_testing.STRATEGY_TEST_CONFIG:
                strategy_testing.STRATEGY_TEST_CONFIG[strategy_name] = True
                strategy_testing.TESTING_MODE = "SINGLE_STRATEGY"
                print(f"🎯 Configured to use only: {strategy_name}")
                return True
            else:
                print(f"❌ Strategy '{strategy_name}' not found in configuration")
                return False

        except Exception as e:
            print(f"❌ Error configuring strategy: {e}")
            return False

    def run_single_strategy_test(self, strategy_name: str) -> Dict[str, Any]:
        """Run test with a specific strategy"""
        print(f"\n🧪 Testing Strategy: {strategy_name}")
        print("=" * 50)

        # Configure system to use only this strategy
        if not self.configure_single_strategy(strategy_name):
            return {
                "strategy": strategy_name,
                "success": False,
                "error": f"Failed to configure strategy: {strategy_name}",
            }

        # Generate unique session ID
        import uuid

        session_id = int(str(uuid.uuid4().int)[:15])

        # Initialize session state
        init_state: SessionState = {
            "sessionID": session_id,
            "query": self.test_query,
            "currentGoalID": None,
            "currentStrategyID": None,
            "currentFunctionID": None,
            "strategySatisfied": False,
            "goalSatisfied": False,
            "workflowComplete": False,
            "outputs": {},
            "errors": [],
        }

        # Track performance metrics
        start_time = time.time()
        memory_before = self._get_memory_usage()

        result = {
            "strategy": strategy_name,
            "session_id": session_id,
            "success": False,
            "execution_time": 0.0,
            "memory_delta": 0,
            "answer": None,
            "confidence": 0.0,
            "goal_satisfied": False,
            "functions_executed": [],
            "function_count": 0,
            "error": None,
        }

        try:
            # Execute workflow
            print(f"⚡ Executing workflow with query: {self.test_query}")
            workflow_result = self.workflow.invoke(init_state)

            # Calculate performance metrics
            end_time = time.time()
            memory_after = self._get_memory_usage()

            functions_executed = self._get_executed_functions(session_id)

            # Extract answer and confidence
            answer = workflow_result.get("finalAnswer") or workflow_result.get(
                "outputs", {}
            ).get("Answer", "No answer")
            confidence = self._extract_confidence(workflow_result)

            result.update(
                {
                    "success": True,
                    "execution_time": end_time - start_time,
                    "memory_delta": memory_after - memory_before,
                    "answer": answer,
                    "confidence": confidence,
                    "goal_satisfied": workflow_result.get("goalSatisfied", False),
                    "functions_executed": functions_executed,
                    "function_count": len(functions_executed),
                }
            )

            print(f"✅ Strategy completed successfully")
            print(f"⏱️  Execution time: {result['execution_time']:.2f} seconds")
            print(f"🧠 Memory usage: {result['memory_delta']:+d} MB")
            print(f"🎯 Goal satisfied: {result['goal_satisfied']}")
            print(f"📊 Confidence: {result['confidence']:.1%}")

        except Exception as e:
            end_time = time.time()
            result.update(
                {
                    "execution_time": end_time - start_time,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            )
            print(f"❌ Strategy failed: {e}")

        return result

    def _get_memory_usage(self) -> int:
        """Get current memory usage in MB"""
        try:
            import psutil

            process = psutil.Process()
            memory_bytes = process.memory_info().rss
            memory_mb = memory_bytes // (1024 * 1024)  # Convert to MB
            return memory_mb
        except ImportError:
            print("⚠️  Warning: psutil not available, memory tracking disabled")
            return 0
        except Exception as e:
            print(f"⚠️  Warning: Memory tracking failed: {e}")
            return 0

    def _extract_confidence(self, workflow_result: Dict) -> float:
        """Extract confidence score from workflow result"""
        try:
            # Check judgeConfidence (the correct location)
            confidence = workflow_result.get("judgeConfidence")

            # If not there, check outputs
            if confidence is None:
                outputs = workflow_result.get("outputs", {})
                confidence = outputs.get("Confidence") or outputs.get("confidence")

            # If still None, return 0
            if confidence is None:
                return 0.0

            # Convert string percentages to float
            if isinstance(confidence, str):
                confidence = confidence.strip()
                if "%" in confidence:
                    confidence = float(confidence.replace("%", "")) / 100
                else:
                    confidence = float(confidence)

            # Ensure it's between 0 and 1
            return max(0.0, min(1.0, float(confidence)))

        except Exception as e:
            return 0.0

    def _get_executed_functions(self, session_id: int) -> List[str]:
        """Get list of functions executed in this session"""
        try:
            with get_agentic_connection() as conn:
                cursor = conn.cursor()
                # Query using the correct schema - FunctionInSession has FunctionName directly
                cursor.execute(
                    """
                    SELECT FunctionName
                    FROM FunctionInSession fis
                    WHERE fis.StrategyID IN (
                        SELECT StrategyID FROM StrategyInSession
                        WHERE GoalID IN (
                            SELECT GoalID FROM GoalInSession WHERE SessionID = ?
                        )
                    )
                    ORDER BY fis.FunctionID
                """,
                    (session_id,),
                )

                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"⚠️  Error getting executed functions: {e}")
            return []

    def run_comparison(self) -> Dict[str, Any]:
        """Run comparison between strategies"""
        print("🚀 Starting Strategy Comparison Test")
        print("=" * 60)
        print(f"📋 Test Query: {self.test_query}")
        print(f"🎯 Strategies: {', '.join(self.strategies_to_test)}")
        print("=" * 60)

        # Backup original configuration
        self.backup_strategy_config()

        results = []

        try:
            for strategy in self.strategies_to_test:
                result = self.run_single_strategy_test(strategy)
                results.append(result)

                # Brief pause between tests
                time.sleep(1)

        finally:
            # Always restore original configuration
            self.restore_strategy_config()

        # Generate comparison report
        return self._generate_comparison_report(results)

    def _generate_comparison_report(self, results: List[Dict]) -> Dict[str, Any]:
        """Generate detailed comparison report with table format"""
        print("\n📊 STRATEGY COMPARISON REPORT")
        print("=" * 60)

        # Generate comparison table
        self._print_comparison_table(results)

        # Performance comparison
        successful_results = [r for r in results if r["success"]]

        if len(successful_results) >= 2:
            fastest = min(successful_results, key=lambda x: x["execution_time"])
            slowest = max(successful_results, key=lambda x: x["execution_time"])

            print(
                f"\n🏆 FASTEST: {fastest['strategy']} ({fastest['execution_time']:.2f}s)"
            )
            print(
                f"🐌 SLOWEST: {slowest['strategy']} ({slowest['execution_time']:.2f}s)"
            )

            speed_improvement = (
                (slowest["execution_time"] - fastest["execution_time"])
                / slowest["execution_time"]
                * 100
            )
            print(f"⚡ Speed improvement: {speed_improvement:.1f}%")

        # Summary statistics
        summary = {
            "test_query": self.test_query,
            "strategies_tested": len(results),
            "successful_runs": len(successful_results),
            "total_execution_time": sum(r["execution_time"] for r in results),
            "average_confidence": (
                sum(r["confidence"] for r in successful_results)
                / len(successful_results)
                if successful_results
                else 0
            ),
            "results": results,
        }

        print(f"\n📈 SUMMARY:")
        print(f"   Total strategies tested: {summary['strategies_tested']}")
        print(f"   Successful runs: {summary['successful_runs']}")
        print(f"   Average confidence: {summary['average_confidence']:.1%}")
        print(f"   Total execution time: {summary['total_execution_time']:.2f}s")

        return summary

    def _print_comparison_table(self, results: List[Dict]):
        """Print comparison results in table format"""
        print("\n📋 STRATEGY COMPARISON TABLE")
        print("-" * 80)

        # Prepare table data
        headers = [
            "Strategy",
            "Success",
            "Time (s)",
            "Memory (MB)",
            "Confidence",
            "Goal Met",
            "Functions",
            "Answer Preview",
        ]

        table_data = []
        for result in results:
            answer_preview = (
                result.get("answer", "")[:40] + "..."
                if len(result.get("answer", "")) > 40
                else result.get("answer", "N/A")
            )

            row = [
                result["strategy"],
                "✅" if result["success"] else "❌",
                f"{result['execution_time']:.2f}",
                f"{result['memory_delta']:+d}" if result["memory_delta"] != 0 else "0",
                f"{result['confidence']:.0%}",
                "✅" if result["goal_satisfied"] else "❌",
                result["function_count"],
                answer_preview,
            ]
            table_data.append(row)

        # Print table using tabulate
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        # Print detailed function execution table
        if any(result["functions_executed"] for result in results):
            self._print_function_execution_table(results)

    def _print_function_execution_table(self, results: List[Dict]):
        """Print detailed function execution comparison"""
        print("\n🔧 FUNCTION EXECUTION COMPARISON")
        print("-" * 80)

        # Get all unique functions
        all_functions = set()
        for result in results:
            all_functions.update(result["functions_executed"])

        all_functions = sorted(all_functions)

        if not all_functions:
            print("No function execution data available")
            return

        # Create function execution matrix
        headers = ["Function"] + [result["strategy"] for result in results]
        table_data = []

        for func in all_functions:
            row = [func]
            for result in results:
                if func in result["functions_executed"]:
                    # Get the position/order of this function
                    try:
                        pos = result["functions_executed"].index(func) + 1
                        row.append(f"#{pos}")
                    except ValueError:
                        row.append("✅")
                else:
                    row.append("❌")
            table_data.append(row)

        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def export_to_csv(self, results: List[Dict], filename: str):
        """Export results to CSV format"""
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "strategy",
                "success",
                "execution_time",
                "memory_delta",
                "confidence",
                "goal_satisfied",
                "function_count",
                "answer",
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for result in results:
                row = {
                    "strategy": result["strategy"],
                    "success": result["success"],
                    "execution_time": result["execution_time"],
                    "memory_delta": result["memory_delta"],
                    "confidence": result["confidence"],
                    "goal_satisfied": result["goal_satisfied"],
                    "function_count": result["function_count"],
                    "answer": result.get("answer", ""),
                }
                writer.writerow(row)

        print(f"� CSV exported to: {filename}")

    def export_to_markdown(self, results: List[Dict], filename: str):
        """Export results to Markdown table format"""
        with open(filename, "w", encoding="utf-8") as md_file:
            md_file.write(f"# Strategy Comparison Results\n\n")
            md_file.write(f"**Query:** {self.test_query}\n\n")
            md_file.write(
                f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )

            # Main comparison table
            headers = [
                "Strategy",
                "Success",
                "Time (s)",
                "Memory (MB)",
                "Confidence",
                "Goal Met",
                "Functions",
                "Answer",
            ]

            table_data = []
            for result in results:
                row = [
                    result["strategy"],
                    "✅" if result["success"] else "❌",
                    f"{result['execution_time']:.2f}",
                    (
                        f"{result['memory_delta']:+d}"
                        if result["memory_delta"] != 0
                        else "0"
                    ),
                    f"{result['confidence']:.0%}",
                    "✅" if result["goal_satisfied"] else "❌",
                    result["function_count"],
                    result.get("answer", "N/A"),
                ]
                table_data.append(row)

            md_file.write(tabulate(table_data, headers=headers, tablefmt="pipe"))
            md_file.write("\n\n")

            # Function execution details
            if any(result["functions_executed"] for result in results):
                md_file.write("## Function Execution Details\n\n")
                for result in results:
                    md_file.write(f"### {result['strategy']}\n\n")
                    if result["functions_executed"]:
                        for i, func in enumerate(result["functions_executed"], 1):
                            md_file.write(f"{i}. {func}\n")
                    else:
                        md_file.write("No functions executed\n")
                    md_file.write("\n")

        print(f"📝 Markdown exported to: {filename}")


def main():
    """Run the strategy comparison test"""
    try:
        comparator = StrategyComparator()
        results = comparator.run_comparison()

        # Export results in multiple formats
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"tests/strategy_comparison_{timestamp}"

        # JSON export (original)
        json_file = f"{base_filename}.json"
        with open(json_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 JSON results exported to: {json_file}")

        # CSV export
        csv_file = f"{base_filename}.csv"
        comparator.export_to_csv(results["results"], csv_file)

        # Markdown export
        md_file = f"{base_filename}.md"
        comparator.export_to_markdown(results["results"], md_file)

    except Exception as e:
        print(f"❌ Test failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
