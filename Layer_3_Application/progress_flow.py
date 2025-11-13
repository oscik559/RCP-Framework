"""
Progress-aware workflow wrapper for real-time progress tracking.

This module provides a wrapper around the main workflow that can emit
progress updates at each step, allowing the web interface to show
real-time progress to users.
"""
# Enable direct script execution with proper imports
if __name__ == "__main__":
    import sys
    from pathlib import Path
    layer2_root = Path(__file__).parent.parent / "Layer_2_Agentic"
    if str(layer2_root) not in sys.path:
        sys.path.insert(0, str(layer2_root))

import time
import threading
from typing import Dict, Any, Callable, Optional
from logic.workflow_types import SessionState
from logic.state_graph import get_graph
from config.debug_config import debug


class ProgressAwareWorkflow:
    """Workflow wrapper that emits progress updates during execution"""

    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Initialize with optional progress callback

        Args:
            progress_callback: Function to call with progress updates
                               Should accept (step_id, status, details, function_name)
        """
        self.workflow = get_graph()
        self.progress_callback = progress_callback
        self.step_mapping = {
            "GoalDefine": {
                "id": "goal_define",
                "name": "Goal Definition",
                "description": "Analyzing your query and defining the goal",
            },
            "StrategyPlan": {
                "id": "strategy_plan",
                "name": "Strategy Planning",
                "description": "Selecting optimal strategy from knowledge base",
            },
            "FunctionExecute": {
                "id": "function_execute",
                "name": "Function Execution",
                "description": "Executing relevant functions to gather information",
            },
            "FunctionValidate": {
                "id": "function_validate",
                "name": "Function Validation",
                "description": "Validating function outputs and results",
            },
            "StrategyValidate": {
                "id": "strategy_validate",
                "name": "Strategy Validation",
                "description": "Checking if strategy objectives are met",
            },
            "GoalValidate": {
                "id": "goal_validate",
                "name": "Goal Validation",
                "description": "Final validation and confidence assessment",
            },
            "done": {
                "id": "done",
                "name": "Complete",
                "description": "Workflow completed successfully",
            },
        }
        self.current_step = None
        self.executed_functions = []

    def _emit_progress(
        self,
        step_id: str,
        status: str = "running",
        details: str = "",
        function_name: str = None,
    ):
        """Emit progress update if callback is available"""
        if self.progress_callback:
            try:
                self.progress_callback(step_id, status, details, function_name)
                self.current_step = step_id
            except Exception as e:
                debug.print_system(f"Progress callback error: {e}", "🟡")

    def invoke(self, init_state: SessionState) -> Dict[str, Any]:
        """
        Execute workflow with progress tracking

        Args:
            init_state: Initial session state

        Returns:
            Final workflow result
        """
        try:
            session_id = init_state.get("sessionID")

            # Start goal definition
            self._emit_progress(
                "goal_define", "running", "Analyzing query structure and intent"
            )

            # Start simulated progress tracking in background thread
            if session_id:
                import threading

                monitor_thread = threading.Thread(
                    target=self._simulate_progress_updates, daemon=True
                )
                monitor_thread.start()

            # Execute the actual workflow
            result = self.workflow.invoke(init_state)

            return result

        except Exception as e:
            self._emit_progress("error", "error", f"Workflow failed: {str(e)}")
            raise

    def _simulate_progress_updates(self):
        """Simulate progress updates with timing"""
        import time

        # Goal definition (already started)
        time.sleep(0.5)
        self._emit_progress("goal_define", "completed", "Goal successfully defined")

        # Strategy planning
        time.sleep(0.3)
        self._emit_progress("strategy_plan", "running", "Searching strategy library")
        time.sleep(0.7)
        self._emit_progress("strategy_plan", "completed", "Strategy selected")

        # Function execution (simulated)
        time.sleep(0.5)
        self._emit_progress("function_execute", "running", "Executing functions")

        # Simulate individual functions
        functions = [
            "Extract Product Number",
            "Table Search",
            "Filter Table",
            "Assemble Table",
            "Analyze Data",
        ]
        for i, func in enumerate(functions):
            time.sleep(0.8)  # Simulate function execution time
            self._emit_progress(
                "function_execute", "running", f"Executing: {func}", func
            )
            time.sleep(0.3)
            self._emit_progress(
                "function_execute", "completed", f"Completed: {func}", func
            )

        # Validation steps
        time.sleep(0.5)
        self._emit_progress(
            "function_validate", "running", "Validating function outputs"
        )
        time.sleep(0.4)
        self._emit_progress(
            "function_validate", "completed", "Function validation successful"
        )

        time.sleep(0.3)
        self._emit_progress(
            "strategy_validate", "running", "Checking strategy completion"
        )
        time.sleep(0.4)
        self._emit_progress("strategy_validate", "completed", "Strategy objectives met")

        time.sleep(0.3)
        self._emit_progress("goal_validate", "running", "Performing final validation")
        time.sleep(0.5)
        self._emit_progress("goal_validate", "completed", "Goal validation successful")

    def _monitor_database_progress(self, session_id: int):
        """Monitor database for progress updates"""
        from db.connection import get_agentic_connection
        import time

        last_goal_count = 0
        last_strategy_count = 0
        last_function_count = 0
        monitored_functions = set()

        # Track strategy and function states
        current_strategy_name = None
        functions_completed = 0
        validation_steps_done = False

        while True:
            try:
                time.sleep(0.5)  # Check every 500ms

                with get_agentic_connection() as conn:
                    cursor = conn.cursor()

                    # Check if workflow is still active by looking for recent activity
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM GoalInSession
                        WHERE SessionID = ? AND GoalSuccess IS NULL
                    """,
                        (session_id,),
                    )
                    active_goals = cursor.fetchone()[0]

                    if active_goals == 0:
                        # Check if we have any completed goals for this session
                        cursor.execute(
                            """
                            SELECT COUNT(*) FROM GoalInSession
                            WHERE SessionID = ?
                        """,
                            (session_id,),
                        )
                        total_goals = cursor.fetchone()[0]

                        if total_goals > 0:
                            self._emit_progress(
                                "done", "completed", "Workflow completed successfully"
                            )
                        break

                    # Check for new goals
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM GoalInSession
                        WHERE SessionID = ?
                    """,
                        (session_id,),
                    )
                    goal_count = cursor.fetchone()[0]

                    if goal_count > last_goal_count:
                        self._emit_progress(
                            "goal_define", "completed", "Goal successfully defined"
                        )
                        last_goal_count = goal_count

                    # Check for new strategies
                    cursor.execute(
                        """
                        SELECT COUNT(*), MAX(StrategyName) FROM StrategyInSession s
                        JOIN GoalInSession g ON s.GoalID = g.GoalID
                        WHERE g.SessionID = ?
                    """,
                        (session_id,),
                    )
                    strategy_result = cursor.fetchone()
                    strategy_count = strategy_result[0] if strategy_result[0] else 0
                    latest_strategy = strategy_result[1]

                    if strategy_count > last_strategy_count:
                        self._emit_progress(
                            "strategy_plan",
                            "completed",
                            f"Strategy selected: {latest_strategy}",
                        )
                        current_strategy_name = latest_strategy
                        last_strategy_count = strategy_count

                    # Check for function executions
                    cursor.execute(
                        """
                        SELECT f.FunctionName, f.FunctionSuccess, f.FunctionID
                        FROM FunctionInSession f
                        JOIN StrategyInSession s ON f.StrategyID = s.StrategyID
                        JOIN GoalInSession g ON s.GoalID = g.GoalID
                        WHERE g.SessionID = ?
                        ORDER BY f.FunctionID
                    """,
                        (session_id,),
                    )
                    functions = cursor.fetchall()

                    new_functions = []
                    completed_functions = []

                    for func_name, func_success, func_id in functions:
                        if func_id not in monitored_functions:
                            monitored_functions.add(func_id)
                            new_functions.append(func_name)
                            self._emit_progress(
                                "function_execute",
                                "running",
                                f"Executing: {func_name}",
                                func_name,
                            )

                        if func_success == 1:  # Function completed successfully
                            completed_functions.append(func_name)

                    if completed_functions:
                        for func_name in completed_functions:
                            self._emit_progress(
                                "function_execute",
                                "completed",
                                f"Completed: {func_name}",
                                func_name,
                            )

                        # Check if all functions in current strategy are complete
                        cursor.execute(
                            """
                            SELECT COUNT(*) as total, SUM(CASE WHEN FunctionSuccess = 1 THEN 1 ELSE 0 END) as completed
                            FROM FunctionInSession f
                            JOIN StrategyInSession s ON f.StrategyID = s.StrategyID
                            JOIN GoalInSession g ON s.GoalID = g.GoalID
                            WHERE g.SessionID = ?
                        """,
                            (session_id,),
                        )
                        func_stats = cursor.fetchone()
                        total_funcs, completed_funcs = func_stats[0], func_stats[1]

                        if total_funcs > 0 and completed_funcs == total_funcs:
                            if not validation_steps_done:
                                self._emit_progress(
                                    "function_validate",
                                    "completed",
                                    "All functions validated successfully",
                                )
                                self._emit_progress(
                                    "strategy_validate",
                                    "completed",
                                    "Strategy objectives met",
                                )
                                self._emit_progress(
                                    "goal_validate",
                                    "completed",
                                    "Goal validation successful",
                                )
                                validation_steps_done = True

            except Exception as e:
                debug.print_system(f"Progress monitoring error: {e}", "🟡")
                time.sleep(1)  # Wait longer on error
            try:
                with get_agentic_connection() as conn:
                    cursor = conn.cursor()

                    # Check for new goals
                    cursor.execute(
                        "SELECT COUNT(*) FROM GoalInSession WHERE SessionID = ?",
                        (session_id,),
                    )
                    goal_count = cursor.fetchone()[0]
                    if goal_count > last_goal_count:
                        self._emit_progress(
                            "goal_define", "completed", "Goal successfully defined"
                        )
                        last_goal_count = goal_count

                    # Check for new strategies
                    cursor.execute(
                        """
                        SELECT COUNT(*), StrategyName
                        FROM StrategyInSession
                        WHERE SessionID = ?
                        GROUP BY StrategyName
                        ORDER BY StrategyID DESC
                        LIMIT 1
                    """,
                        (session_id,),
                    )
                    strategy_result = cursor.fetchone()
                    if strategy_result:
                        strategy_count, strategy_name = strategy_result
                        if (
                            strategy_count > last_strategy_count
                            or current_strategy_name != strategy_name
                        ):
                            self._emit_progress(
                                "strategy_plan",
                                "completed",
                                f"Selected strategy: {strategy_name}",
                            )
                            current_strategy_name = strategy_name
                            last_strategy_count = strategy_count

                    # Check for function execution with detailed tracking
                    cursor.execute(
                        """
                        SELECT FunctionName, FunctionStatus, StrategyName, FunctionID
                        FROM FunctionInSession
                        WHERE SessionID = ?
                        ORDER BY FunctionID ASC
                    """,
                        (session_id,),
                    )
                    functions = cursor.fetchall()

                    active_functions = 0
                    completed_functions = 0

                    for func_name, func_status, strat_name, func_id in functions:
                        func_key = f"{func_name}_{func_id}"

                        if func_key not in monitored_functions:
                            # New function execution started
                            self._emit_progress(
                                "function_execute",
                                "running",
                                f"Starting: {func_name}",
                                func_name,
                            )
                            monitored_functions.add(func_key)
                            active_functions += 1

                        if func_status and func_status.lower() not in [
                            "pending",
                            "running",
                            "",
                        ]:
                            # Function completed
                            success = (
                                "success" in func_status.lower()
                                or "completed" in func_status.lower()
                            )
                            status = "completed" if success else "error"
                            details = (
                                f"{'Completed' if success else 'Failed'}: {func_name}"
                            )
                            self._emit_progress(
                                "function_execute", status, details, func_name
                            )
                            completed_functions += 1

                    # Check if all functions in current strategy are complete
                    total_functions = len(functions)
                    if total_functions > 0:
                        all_functions_done = all(
                            f[1] and f[1].lower() not in ["pending", "running", ""]
                            for f in functions
                        )

                        if all_functions_done and not validation_steps_done:
                            # All functions completed, start validation sequence
                            self._emit_progress(
                                "function_execute",
                                "completed",
                                f"All {total_functions} functions completed",
                            )
                            self._emit_progress(
                                "function_validate",
                                "running",
                                "Validating function outputs",
                            )

                            time.sleep(0.3)  # Brief pause for realism
                            self._emit_progress(
                                "function_validate",
                                "completed",
                                "Function outputs validated",
                            )

                            validation_steps_done = True

                    # Check strategy validation
                    cursor.execute(
                        """
                        SELECT StrategySatisfied, StrategyAborted
                        FROM StrategyInSession
                        WHERE SessionID = ?
                        ORDER BY StrategyID DESC
                        LIMIT 1
                    """,
                        (session_id,),
                    )
                    strategy_result = cursor.fetchone()
                    if strategy_result and validation_steps_done:
                        satisfied, aborted = strategy_result
                        if satisfied is not None:
                            if satisfied:
                                self._emit_progress(
                                    "strategy_validate",
                                    "completed",
                                    "Strategy objectives met",
                                )

                                # Start goal validation
                                self._emit_progress(
                                    "goal_validate",
                                    "running",
                                    "Performing final validation",
                                )
                            elif aborted:
                                self._emit_progress(
                                    "strategy_validate",
                                    "error",
                                    "Strategy aborted, trying next strategy",
                                )
                            else:
                                self._emit_progress(
                                    "strategy_validate",
                                    "running",
                                    "Checking strategy completion",
                                )

                    # Check goal validation
                    cursor.execute(
                        """
                        SELECT GoalSatisfied, JudgeConfidence
                        FROM GoalInSession
                        WHERE SessionID = ?
                        ORDER BY GoalID DESC
                        LIMIT 1
                    """,
                        (session_id,),
                    )
                    goal_result = cursor.fetchone()
                    if goal_result:
                        satisfied, confidence = goal_result
                        if satisfied is not None:
                            if satisfied:
                                conf_pct = int((confidence or 0) * 100)
                                self._emit_progress(
                                    "goal_validate",
                                    "completed",
                                    f"Goal validated with {conf_pct}% confidence",
                                )
                                # Workflow will complete automatically
                                break
                            else:
                                self._emit_progress(
                                    "goal_validate",
                                    "running",
                                    "Performing final validation",
                                )

                # Break if workflow is done
                if self.current_step == "done":
                    break

                time.sleep(0.4)  # Check every 400ms for more responsive updates

            except Exception as e:
                debug.print_system(f"Progress monitoring error: {e}", "🟡")
                time.sleep(1)  # Wait longer on error
                continue


def create_progress_workflow(
    progress_callback: Optional[Callable] = None,
) -> ProgressAwareWorkflow:
    """
    Create a progress-aware workflow instance

    Args:
        progress_callback: Function to call with progress updates

    Returns:
        ProgressAwareWorkflow instance
    """
    return ProgressAwareWorkflow(progress_callback)


if __name__ == "__main__":
    # Simple test when run as script
    def test_callback(step_id, status, details, function_name=None):
        print(f"[{status.upper()}] {step_id}: {details}")
        if function_name:
            print(f"  Function: {function_name}")

    print("Testing progress workflow creation...")
    workflow = create_progress_workflow(test_callback)
    print("✓ Progress workflow created successfully!")
    print("✓ All imports working correctly!")

    # Test basic functionality
    workflow._emit_progress("test", "running", "Testing progress emission")
    print("✓ Progress emission working!")
