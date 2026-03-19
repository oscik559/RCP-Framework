"""
Database Manager for Agentic Reasoning System

Provides a clean, typed interface for all database operations used by workflow nodes.
Encapsulates SQL logic and provides high-level methods for:
- Session and goal management
- Strategy execution tracking  
- Function execution logging
- Template library access
- Performance metrics collection

Uses dataclasses for type safety and context managers for resource cleanup.
Thread-safe for concurrent access patterns.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any, Set
import sqlite3
import threading
import logging

from ..db.connection import get_agentic_connection

logger = logging.getLogger("DATABASE_MANAGER")


@dataclass
class GoalInfo:
    """
    Information about a goal in the system.
    
    Represents a high-level objective parsed from user query.
    Goals contain one or more strategies for completion.
    """
    goal_id: int                    # Unique goal identifier
    session_id: int                 # Session this goal belongs to
    description: str                # Human-readable goal description
    success: Optional[bool]         # None=pending, True=success, False=failed


@dataclass
class StrategyInfo:
    """
    Information about a strategy execution.
    
    Strategies are specific approaches to achieving a goal,
    containing a sequence of functions to execute.
    """
    strategy_id: int                # Unique strategy identifier
    goal_id: int                    # Parent goal ID
    name: str                       # Strategy name from StrategyLibrary
    success: Optional[bool]         # None=pending, True=success, False=failed
    plan_steps: Optional[str] = None # Comma-separated function sequence


@dataclass
class FunctionInfo:
    """
    Information about a function execution.
    
    Functions are atomic operations that perform specific tasks
    like table search, data filtering, or analysis.
    """

    function_id: int
    strategy_id: int
    strategy_name: str
    function_name: str
    success: Optional[bool]  # None=pending, True=success, False=failed
    failed_text: Optional[str] = None


@dataclass
class FunctionOutput:
    """Function output information."""

    output_name: str
    output_value: str
    output_type: str


@dataclass
class StrategyTemplate:
    """Strategy template information."""

    strategy_name: str
    strategy_type: str
    plan_steps: str


@dataclass
class FunctionParameter:
    """Function parameter information."""

    parameter_name: str
    parameter_value: str
    parameter_type: str


class DatabaseManager:
    """
    Manages all database operations for the workflow system.

    Provides clean, typed interfaces for:
    - Goal management (create, find, cleanup)
    - Strategy management (create, find tried strategies)
    - Function management (create, update, track outputs)
    - Output collection and validation
    
    Thread-safe for concurrent parallel execution.
    """
    
    # Class-level lock for database write operations
    _db_lock = threading.RLock()

    # ── Goal Management ──────────────────────────────────────────

    def find_unfinished_goal(self, session_id: int) -> Optional[GoalInfo]:
        """Find an existing unfinished goal for the session."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT GoalID, SessionID, GoalDescription, GoalSuccess
                   FROM GoalInSession
                   WHERE SessionID=? AND GoalSuccess IS NULL
                   LIMIT 1""",
                (session_id,),
            )
            row = cur.fetchone()
            if row:
                return GoalInfo(
                    goal_id=row[0],
                    session_id=row[1],
                    description=row[2],
                    success=row[3],
                )
            return None

    def count_successful_strategies(self, goal_id: int) -> int:
        """Count the number of successful strategies for a goal."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT COUNT(*) FROM StrategyInSession
                   WHERE GoalID=? AND StrategySuccess=1""",
                (goal_id,),
            )
            return cur.fetchone()[0]

    def cleanup_failed_goal(self, goal_id: int) -> None:
        """Clean up a failed goal and all its related data."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()

            # Clean up in proper order to maintain referential integrity
            cur.execute(
                """DELETE FROM FunctionOutputInSession
                   WHERE FunctionID IN (
                       SELECT fis.FunctionID FROM FunctionInSession fis
                       JOIN StrategyInSession sis ON fis.StrategyID = sis.StrategyID
                       WHERE sis.GoalID = ?
                   )""",
                (goal_id,),
            )

            cur.execute(
                """DELETE FROM FunctionParametersInSession
                   WHERE FunctionID IN (
                       SELECT fis.FunctionID FROM FunctionInSession fis
                       JOIN StrategyInSession sis ON fis.StrategyID = sis.StrategyID
                       WHERE sis.GoalID = ?
                   )""",
                (goal_id,),
            )

            cur.execute(
                """DELETE FROM FunctionInSession
                   WHERE StrategyID IN (
                       SELECT StrategyID FROM StrategyInSession WHERE GoalID=?
                   )""",
                (goal_id,),
            )

            cur.execute("DELETE FROM StrategyInSession WHERE GoalID=?", (goal_id,))
            cur.execute("DELETE FROM GoalInSession WHERE GoalID=?", (goal_id,))

            conn.commit()

    def clear_session_data(self, session_id) -> None:
        """
        Clear all data for a specific session.
        
        This ensures that each new session starts with a clean slate and doesn't
        accumulate data from previous sessions. Cleans up all related tables
        in proper order to maintain referential integrity.
        
        Args:
            session_id: The session ID to clear data for (int or str)
        """
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            
            # Convert to string for consistency with UUID-based session IDs
            session_id = str(session_id)
            
            # Clean up in proper order to maintain referential integrity
            # First, delete function outputs and parameters
            cur.execute(
                """DELETE FROM FunctionOutputInSession
                   WHERE FunctionID IN (
                       SELECT fis.FunctionID FROM FunctionInSession fis
                       JOIN StrategyInSession sis ON fis.StrategyID = sis.StrategyID
                       JOIN GoalInSession gis ON sis.GoalID = gis.GoalID
                       WHERE gis.SessionID = ?
                   )""",
                (session_id,),
            )
            
            cur.execute(
                """DELETE FROM FunctionParametersInSession
                   WHERE FunctionID IN (
                       SELECT fis.FunctionID FROM FunctionInSession fis
                       JOIN StrategyInSession sis ON fis.StrategyID = sis.StrategyID
                       JOIN GoalInSession gis ON sis.GoalID = gis.GoalID
                       WHERE gis.SessionID = ?
                   )""",
                (session_id,),
            )
            
            # Then delete functions
            cur.execute(
                """DELETE FROM FunctionInSession
                   WHERE StrategyID IN (
                       SELECT sis.StrategyID FROM StrategyInSession sis
                       JOIN GoalInSession gis ON sis.GoalID = gis.GoalID
                       WHERE gis.SessionID = ?
                   )""",
                (session_id,),
            )
            
            # Then delete strategies
            cur.execute(
                """DELETE FROM StrategyInSession
                   WHERE GoalID IN (
                       SELECT GoalID FROM GoalInSession WHERE SessionID = ?
                   )""",
                (session_id,),
            )
            
            # Finally delete goals
            cur.execute("DELETE FROM GoalInSession WHERE SessionID = ?", (session_id,))
            
            conn.commit()
            logger.info(f"✅ Cleared all data for session {session_id}")

    def clear_strategy_and_function_data(self, session_id) -> None:
        """
        Clear only strategy and function data for a session, keeping goals.
        
        This allows each goal attempt to start fresh with new strategies and functions,
        while preserving the goal history.
        
        Args:
            session_id: The session ID (int or str)
        """
        session_id = str(session_id)
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            
            # Delete function outputs and parameters first
            cur.execute(
                """DELETE FROM FunctionOutputInSession
                   WHERE FunctionID IN (
                       SELECT fis.FunctionID FROM FunctionInSession fis
                       JOIN StrategyInSession sis ON fis.StrategyID = sis.StrategyID
                       JOIN GoalInSession gis ON sis.GoalID = gis.GoalID
                       WHERE gis.SessionID = ?
                   )""",
                (session_id,),
            )
            
            cur.execute(
                """DELETE FROM FunctionParametersInSession
                   WHERE FunctionID IN (
                       SELECT fis.FunctionID FROM FunctionInSession fis
                       JOIN StrategyInSession sis ON fis.StrategyID = sis.StrategyID
                       JOIN GoalInSession gis ON sis.GoalID = gis.GoalID
                       WHERE gis.SessionID = ?
                   )""",
                (session_id,),
            )
            
            # Delete functions
            cur.execute(
                """DELETE FROM FunctionInSession
                   WHERE StrategyID IN (
                       SELECT sis.StrategyID FROM StrategyInSession sis
                       JOIN GoalInSession gis ON sis.GoalID = gis.GoalID
                       WHERE gis.SessionID = ?
                   )""",
                (session_id,),
            )
            
            # Delete strategies (but keep goals)
            cur.execute(
                """DELETE FROM StrategyInSession
                   WHERE GoalID IN (
                       SELECT GoalID FROM GoalInSession WHERE SessionID = ?
                   )""",
                (session_id,),
            )
            
            conn.commit()
            logger.info(f"✅ Cleared strategy and function data for session {session_id}")

    def clear_all_sessions(self) -> None:
        """
        Clear ALL session data from the database.
        
        This is used on startup to ensure a completely clean slate
        for all queries.
        """
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            
            # Delete in proper referential integrity order
            cur.execute("DELETE FROM FunctionOutputInSession")
            cur.execute("DELETE FROM FunctionParametersInSession")
            cur.execute("DELETE FROM FunctionInSession")
            cur.execute("DELETE FROM StrategyInSession")
            cur.execute("DELETE FROM GoalInSession")
            
            conn.commit()
            logger.info("✅ Cleared ALL session data from database")

    def create_goal(
        self,
        session_id: int,
        description: str,
        name: str = "MainGoal",
        target: Optional[str] = None,
    ) -> int:
        """Create a new goal and return its ID."""
        if target is None:
            # Extract first 4 words as target
            target = " ".join(description.split()[:4])

        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO GoalInSession (SessionID, GoalName, GoalTarget, GoalDescription, GoalSuccess)
                   VALUES (?, ?, ?, ?, NULL)""",
                (session_id, name, target, description),
            )
            goal_id = cur.lastrowid
            conn.commit()
            if goal_id is None:
                raise RuntimeError("Failed to create goal: lastrowid is None")
            return goal_id

    def update_goal_status(self, goal_id: int, success: bool) -> None:
        """Update goal completion status."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            success_value = 1 if success else 0
            cur.execute(
                """UPDATE GoalInSession
                   SET GoalSuccess=?
                   WHERE GoalID=?""",
                (success_value, goal_id),
            )
            conn.commit()

    # ── Strategy Management ──────────────────────────────────────

    def get_tried_strategies(self, goal_id: int) -> List[str]:
        """Get list of strategy names already tried for a goal."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT DISTINCT StrategyName FROM StrategyInSession
                   WHERE GoalID=?""",
                (goal_id,),
            )
            return [row[0] for row in cur.fetchall()]

    def get_untried_strategies(
        self, goal_id: int, goal_description: str
    ) -> List[StrategyTemplate]:
        """Get strategies that haven't been tried yet for this goal."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()

            # Get tried strategies
            tried = set(self.get_tried_strategies(goal_id))

            # Get all strategies from StrategyLibrary
            cur.execute(
                """SELECT StrategyName, StrategyTarget, PlanSteps
                   FROM StrategyLibrary"""
            )

            all_strategies = []
            for row in cur.fetchall():
                strategy_name = row[0]
                if strategy_name not in tried:
                    all_strategies.append(
                        StrategyTemplate(
                            strategy_name=strategy_name,
                            strategy_type=row[1],  # StrategyTarget field used as type
                            plan_steps=row[2],
                        )
                    )

            return all_strategies

    def create_strategy(self, goal_id: int, strategy_name: str, plan_steps: str) -> int:
        """Create a new strategy execution and return its ID."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()

            # Get strategy details from library
            cur.execute(
                """SELECT StrategyTarget, StrategyDescription FROM StrategyLibrary
                   WHERE StrategyName=?""",
                (strategy_name,),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"Strategy '{strategy_name}' not found in library")

            strategy_target, strategy_description = row[0], row[1]
            plan_funcs = [x.strip() for x in plan_steps.split(",") if x.strip()]

            cur.execute(
                """INSERT INTO StrategyInSession
                   (GoalID, StrategyName, StrategyTarget, StrategyDescription, PlanSteps, StrategySuccess, StrategyValidation)
                   VALUES (?, ?, ?, ?, ?, NULL, ?)""",
                (
                    goal_id,
                    strategy_name,
                    strategy_target,
                    strategy_description,
                    plan_steps,
                    f"0/{len(plan_funcs)} functions complete.",
                ),
            )
            strategy_id = cur.lastrowid
            conn.commit()
            if strategy_id is None:
                raise RuntimeError("Failed to create strategy: lastrowid is None")
            return strategy_id

    def get_current_strategy(self, goal_id: int) -> Optional[StrategyInfo]:
        """Get the most recent strategy for a goal that is not yet complete."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT StrategyID, GoalID, StrategyName, StrategySuccess, PlanSteps
                   FROM StrategyInSession
                   WHERE GoalID=? AND StrategySuccess IS NULL
                   ORDER BY StrategyID DESC
                   LIMIT 1""",
                (goal_id,),
            )
            row = cur.fetchone()
            if row:
                return StrategyInfo(
                    strategy_id=row[0],
                    goal_id=row[1],
                    name=row[2],
                    success=None if row[3] is None else bool(row[3]),
                    plan_steps=row[4],
                )
            return None

    # ── Function Management ──────────────────────────────────────

    def create_function(
        self, strategy_id: int, strategy_name: str, function_name: str
    ) -> int:
        """Create a new function execution and return its ID."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO FunctionInSession (StrategyID, StrategyName, FunctionName, FunctionSuccess)
                   VALUES (?, ?, ?, NULL)""",
                (strategy_id, strategy_name, function_name),
            )
            function_id = cur.lastrowid
            conn.commit()
            if function_id is None:
                raise RuntimeError("Failed to create function: lastrowid is None")
            return function_id

    def update_function_status(
        self, function_id: int, success: bool, failed_text: Optional[str] = None
    ) -> None:
        """Update function execution status."""
        with self._db_lock:
            with get_agentic_connection() as conn:
                cur = conn.cursor()
                success_value = 1 if success else 0
                cur.execute(
                    """UPDATE FunctionInSession
                       SET FunctionSuccess=?, failedtext=?
                       WHERE FunctionID=?""",
                    (success_value, failed_text, function_id),
                )
                conn.commit()

    def store_function_output_v1(
        self,
        function_id: int,
        function_name: str,
        output_name: str,
        output_value: str,
        output_type: str,
        strategy_name: str = "",
    ) -> None:
        """Store function output result (v1 - deprecated, use store_function_output)."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO FunctionOutputInSession
                   (FunctionID, FunctionName, StrategyName, OutputName, OutputValue, Type)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    function_id,
                    function_name,
                    strategy_name,
                    output_name,
                    output_value,
                    output_type,
                ),
            )
            conn.commit()

    def store_function_parameter(
        self,
        function_id: int,
        function_name: str,
        param_name: str,
        param_value: str,
        param_type: str,
        strategy_name: str = "",
    ) -> None:
        """Store function input parameter."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO FunctionParametersInSession
                   (FunctionID, FunctionName, StrategyName, ParameterName, ParameterValue, Type)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    function_id,
                    function_name,
                    strategy_name,
                    param_name,
                    param_value,
                    param_type,
                ),
            )
            conn.commit()

    def get_function_parameters(self, function_name: str) -> List[FunctionParameter]:
        """Get parameter templates for a function."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT fpl.ParameterName, fpl.ParameterValue, fpl.Type
                   FROM FunctionParametersLibrary fpl
                   JOIN FunctionTemplateLibrary ftl ON fpl.FunctionTemplateID = ftl.FunctionTemplateID
                   WHERE ftl.FunctionName=?""",
                (function_name,),
            )

            results = []
            for row in cur.fetchall():
                results.append(
                    FunctionParameter(
                        parameter_name=row[0],
                        parameter_value=row[1],
                        parameter_type=row[2],
                    )
                )
            return results

    def get_next_pending_function(self, strategy_id: int) -> Optional[str]:
        """Get the next function that needs to be executed."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT FunctionName FROM FunctionInSession
                   WHERE StrategyID=? AND FunctionSuccess IS NULL
                   ORDER BY FunctionID
                   LIMIT 1""",
                (strategy_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def get_current_function_id(self, strategy_id: int) -> Optional[int]:
        """Get the ID of the current function being executed (first pending function)."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT FunctionID FROM FunctionInSession
                   WHERE StrategyID=? AND FunctionSuccess IS NULL
                   ORDER BY FunctionID
                   LIMIT 1""",
                (strategy_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def get_function_instance_parameters(self, function_id: int) -> Dict[str, str]:
        """Get parameter values for a specific function instance."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT ParameterName, ParameterValue
                   FROM FunctionParametersInSession
                   WHERE FunctionID=?""",
                (function_id,),
            )
            return {name: value for name, value in cur.fetchall()}

    def get_function_allowed_parameters(self, function_name: str) -> Set[str]:
        """Get allowed parameter names for a function from templates."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT tpl.ParameterName
                   FROM FunctionParametersLibrary tpl
                   JOIN FunctionTemplateLibrary ft ON tpl.FunctionTemplateID = ft.FunctionTemplateID
                   WHERE ft.FunctionName=?""",
                (function_name,),
            )
            return {name for (name,) in cur.fetchall()}

    def get_function_allowed_outputs(self, function_name: str) -> Set[str]:
        """Get allowed output names for a function from templates."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT OutputName FROM FunctionOutputLibrary fo
                   JOIN FunctionTemplateLibrary ft ON fo.FunctionTemplateID = ft.FunctionTemplateID
                   WHERE ft.FunctionName=?""",
                (function_name,),
            )
            return {name for (name,) in cur.fetchall()}

    def update_function_parameter(
        self, function_id: int, parameter_name: str, parameter_value: str
    ) -> None:
        """Update a function parameter value."""
        with self._db_lock:
            with get_agentic_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """UPDATE FunctionParametersInSession
                       SET ParameterValue=? WHERE FunctionID=? AND ParameterName=?""",
                    (parameter_value, function_id, parameter_name),
                )
                conn.commit()

    def get_function_actual_outputs(self, function_id: int) -> Set[str]:
        """Get actual output names produced by a function instance."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT DISTINCT OutputName
                   FROM FunctionOutputInSession
                   WHERE FunctionID=?""",
                (function_id,),
            )
            return {name for (name,) in cur.fetchall()}

    def get_function_output_details(self, function_id: int) -> List[Tuple[str, str, str]]:
        """Get actual outputs with details (name, value, type) for a function instance."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT OutputName, OutputValue, Type
                   FROM FunctionOutputInSession
                   WHERE FunctionID=?
                   ORDER BY OutputName""",
                (function_id,),
            )
            return cur.fetchall()

    def store_function_output(
        self,
        function_id: int,
        function_name: str,
        output_name: str,
        output_value: str,
        output_type: str = "string",
        strategy_name: str = "",
    ) -> None:
        """Store a function output value."""
        with self._db_lock:
            with get_agentic_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO FunctionOutputInSession
                       (FunctionID, FunctionName, StrategyName, OutputName, OutputValue, Type)
                       VALUES (?,?,?,?,?,?)""",
                    (
                        function_id,
                        function_name,
                        strategy_name,
                        output_name,
                        output_value,
                        output_type,
                    ),
                )
                conn.commit()

    def get_strategy_function_statistics(self, strategy_id: int) -> Dict[str, int]:
        """Get function execution statistics for a strategy."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT COUNT(*) as total,
                   SUM(CASE WHEN FunctionSuccess=1 THEN 1 ELSE 0 END) as succeeded,
                   SUM(CASE WHEN FunctionSuccess IS NULL THEN 1 ELSE 0 END) as pending,
                   SUM(CASE WHEN FunctionSuccess=0 THEN 1 ELSE 0 END) as failed
                   FROM FunctionInSession
                   WHERE StrategyID=?""",
                (strategy_id,),
            )
            row = cur.fetchone()
            return {
                "total": row[0],
                "succeeded": row[1],
                "pending": row[2],
                "failed": row[3],
            }

    def update_strategy_status(
        self, strategy_id: int, success: bool, validation_message: str
    ) -> None:
        """Update strategy execution status."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """UPDATE StrategyInSession
                   SET StrategySuccess=?, StrategyValidation=?
                   WHERE StrategyID=?""",
                (1 if success else 0, validation_message, strategy_id),
            )
            conn.commit()

    # ── Query and Validation ──────────────────────────────────────

    def get_function_info(self, function_id: int) -> Optional[FunctionInfo]:
        """Get function information by ID."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT FunctionID, StrategyID, StrategyName, FunctionName, FunctionSuccess, failedtext
                   FROM FunctionInSession
                   WHERE FunctionID=?""",
                (function_id,),
            )
            row = cur.fetchone()
            if row:
                return FunctionInfo(
                    function_id=row[0],
                    strategy_id=row[1],
                    strategy_name=row[2],
                    function_name=row[3],
                    success=row[4],
                    failed_text=row[5] or "",
                )
            return None

    def get_strategy_functions(self, strategy_id: int) -> List[FunctionInfo]:
        """Get all functions for a strategy."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT FunctionID, StrategyID, StrategyName, FunctionName, FunctionSuccess, failedtext
                   FROM FunctionInSession
                   WHERE StrategyID=?
                   ORDER BY FunctionID""",
                (strategy_id,),
            )

            results = []
            for row in cur.fetchall():
                results.append(
                    FunctionInfo(
                        function_id=row[0],
                        strategy_id=row[1],
                        strategy_name=row[2],
                        function_name=row[3],
                        success=None if row[4] is None else bool(row[4]),
                        failed_text=row[5],
                    )
                )
            return results

    def count_pending_functions(self, strategy_id: int) -> int:
        """Count functions that haven't been executed yet."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT COUNT(*) FROM FunctionInSession
                   WHERE StrategyID=? AND FunctionSuccess IS NULL""",
                (strategy_id,),
            )
            return cur.fetchone()[0]

    def has_failed_functions(self, strategy_id: int) -> bool:
        """Check if any functions have failed in this strategy."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT COUNT(*) FROM FunctionInSession
                   WHERE StrategyID=? AND FunctionSuccess=0""",
                (strategy_id,),
            )
            return cur.fetchone()[0] > 0

    def count_total_functions(self, strategy_id: int) -> int:
        """Count total functions in a strategy."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT COUNT(*) FROM FunctionInSession
                   WHERE StrategyID=?""",
                (strategy_id,),
            )
            return cur.fetchone()[0]

    def count_successful_functions(self, strategy_id: int) -> int:
        """Count successful functions in a strategy."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT COUNT(*) FROM FunctionInSession
                   WHERE StrategyID=? AND FunctionSuccess=1""",
                (strategy_id,),
            )
            return cur.fetchone()[0]

    # ── Output Collection ──────────────────────────────────────────

    def collect_outputs_by_goal(self, goal_id: int, output_name: str) -> List[str]:
        """Collect outputs of a specific type from all functions in a goal."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT DISTINCT fos.OutputValue
                   FROM FunctionOutputInSession fos
                   JOIN FunctionInSession fis ON fos.FunctionID = fis.FunctionID
                   JOIN StrategyInSession sis ON fis.StrategyID = sis.StrategyID
                   WHERE sis.GoalID = ? AND fos.OutputName = ?
                   ORDER BY fos.OutputValue""",
                (goal_id, output_name),
            )
            return [row[0] for row in cur.fetchall()]

    def get_all_outputs_by_goal(self, goal_id: int) -> Dict[str, List[str]]:
        """Get all outputs organized by output name for a goal."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT fos.OutputName, fos.OutputValue
                   FROM FunctionOutputInSession fos
                   JOIN FunctionInSession fis ON fos.FunctionID = fis.FunctionID
                   JOIN StrategyInSession sis ON fis.StrategyID = sis.StrategyID
                   WHERE sis.GoalID = ?
                   ORDER BY fos.OutputName, fos.OutputValue""",
                (goal_id,),
            )

            outputs = {}
            for row in cur.fetchall():
                output_name, output_value = row[0], row[1]
                if output_name not in outputs:
                    outputs[output_name] = []
                if output_value not in outputs[output_name]:
                    outputs[output_name].append(output_value)

            return outputs

    def collect_outputs_for_strategy(
        self, session_id: int, goal_id: int, output_name: str, strategy_id: int
    ) -> List[str]:
        """Collect outputs of a specific type from successful functions in a strategy."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT foi.OutputValue
                FROM FunctionOutputInSession foi
                JOIN FunctionInSession   fi ON foi.FunctionID  = fi.FunctionID
                JOIN StrategyInSession   si ON fi.StrategyID   = si.StrategyID
                JOIN GoalInSession       gi ON si.GoalID       = gi.GoalID
                WHERE gi.SessionID = ?
                AND gi.GoalID    = ?
                AND si.StrategyID = ?
                AND foi.OutputName = ?
                AND fi.FunctionSuccess = 1
                ORDER BY foi.FunctionID
            """,
                (session_id, goal_id, strategy_id, output_name),
            )
            return [row[0] for row in cur.fetchall()]

    # ── Strategy Planning Support ──────────────────────────────────

    def create_strategy_functions(
        self, strategy_id: int, strategy_name: str, plan_steps: str
    ) -> None:
        """Create function entries for a strategy based on plan steps."""
        function_names = [step.strip() for step in plan_steps.split(",")]

        for function_step in function_names:
            if function_step:  # Skip empty names
                # Handle parallel syntax: [Function1 || Function2]
                if function_step.startswith("[") and function_step.endswith("]"):
                    # Extract parallel functions from brackets
                    parallel_content = function_step[1:-1]  # Remove brackets
                    parallel_funcs = [f.strip() for f in parallel_content.split("||")]
                    # Create each function in the parallel group
                    for func_name in parallel_funcs:
                        if func_name:
                            self.create_function(strategy_id, strategy_name, func_name)
                else:
                    # Regular sequential function
                    self.create_function(strategy_id, strategy_name, function_step)

    def get_strategy_plan_steps(self, strategy_name: str) -> Optional[str]:
        """Get plan steps for a strategy from the library."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT PlanSteps FROM StrategyLibrary
                   WHERE StrategyName=?""",
                (strategy_name,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def collect_outputs(
        self, session_id: int, goal_id: int, output_name: str, strategy_id: Optional[int] = None
    ) -> List[str]:
        """
        Collect output values from previously executed functions.

        Searches for successful function outputs within the same session and goal
        that match the specified output name. This enables functions to build
        upon results from earlier functions in the workflow.

        Args:
            session_id: Current session identifier
            goal_id: Current goal identifier
            output_name: Name of the output to collect (e.g., "Keyword Output")
            strategy_id: If provided, only collect outputs from this specific strategy.
                        If None, collect from current strategy only (recommended)

        Returns:
            List of output values from successful functions
        """
        with get_agentic_connection() as conn:
            cur = conn.cursor()

            if strategy_id is not None:
                # Collect only from specified strategy
                cur.execute(
                    """
                    SELECT foi.OutputValue
                    FROM FunctionOutputInSession foi
                    JOIN FunctionInSession   fi ON foi.FunctionID  = fi.FunctionID
                    JOIN StrategyInSession   si ON fi.StrategyID   = si.StrategyID
                    JOIN GoalInSession       gi ON si.GoalID       = gi.GoalID
                    WHERE gi.SessionID = ?
                    AND gi.GoalID    = ?
                    AND si.StrategyID = ?
                    AND foi.OutputName = ?
                    AND fi.FunctionSuccess = 1
                    ORDER BY foi.FunctionID
                """,
                    (session_id, goal_id, strategy_id, output_name),
                )
            else:
                # Collect from current strategy only (get latest strategy for this goal)
                cur.execute(
                    """
                    SELECT foi.OutputValue
                    FROM FunctionOutputInSession foi
                    JOIN FunctionInSession   fi ON foi.FunctionID  = fi.FunctionID
                    JOIN StrategyInSession   si ON fi.StrategyID   = si.StrategyID
                    JOIN GoalInSession       gi ON si.GoalID       = gi.GoalID
                    WHERE gi.SessionID = ?
                    AND gi.GoalID    = ?
                    AND si.StrategyID = (
                        SELECT MAX(StrategyID)
                        FROM StrategyInSession
                        WHERE GoalID = ?
                    )
                    AND foi.OutputName = ?
                    AND fi.FunctionSuccess = 1
                    ORDER BY foi.FunctionID
                """,
                    (session_id, goal_id, goal_id, output_name),
                )

            vals = [v for (v,) in cur.fetchall()]
            return vals

    def get_available_functions(self) -> Set[str]:
        """Get all available function names from the function library."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT FunctionName FROM FunctionTemplateLibrary")
            return {name for (name,) in cur.fetchall()}

    def get_function_parameter_templates(
        self, function_name: str
    ) -> List[Tuple[str, str, str]]:
        """Get parameter templates for a function."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT tpl.ParameterName, tpl.ParameterValue, tpl.Type
                   FROM FunctionParametersLibrary tpl
                   JOIN FunctionTemplateLibrary ft ON tpl.FunctionTemplateID = ft.FunctionTemplateID
                   WHERE ft.FunctionName=?""",
                (function_name,),
            )
            return cur.fetchall()

    def get_strategy_function_ids(self, strategy_id: int) -> List[Tuple[int, str]]:
        """Get all function IDs and names for a strategy."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT FunctionID, FunctionName FROM FunctionInSession
                   WHERE StrategyID=?
                   ORDER BY FunctionID""",
                (strategy_id,),
            )
            return cur.fetchall()

    def get_goal_strategy_statistics(self, goal_id: int) -> Dict[str, int]:
        """Get strategy execution statistics for a goal."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT StrategyID, StrategySuccess, StrategyValidation
                   FROM StrategyInSession
                   WHERE GoalID=?""",
                (goal_id,),
            )
            rows = cur.fetchall()

            return {
                "total": len(rows),
                "successful": sum(1 for _, success, _ in rows if success == 1),
                "pending": sum(1 for _, success, _ in rows if success is None),
                "failed": sum(1 for _, success, _ in rows if success == 0),
            }

    def count_total_strategies(self) -> int:
        """Count total number of strategies in the library."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM StrategyLibrary")
            return cur.fetchone()[0]

    def count_goal_strategies(self, goal_id: int) -> int:
        """Count number of strategies tried for a goal."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM StrategyInSession WHERE GoalID=?", (goal_id,)
            )
            return cur.fetchone()[0]

    def get_successful_strategies(self, goal_id: int) -> List[int]:
        """Get IDs of successful strategies for a goal."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT StrategyID FROM StrategyInSession WHERE GoalID=? AND StrategySuccess=1",
                (goal_id,),
            )
            return [row[0] for row in cur.fetchall()]

    def get_strategy_outputs(self, strategy_id: int) -> List[Tuple[str, str]]:
        """Get all outputs from functions in a strategy."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT foi.OutputName, foi.OutputValue
                FROM FunctionOutputInSession foi
                JOIN FunctionInSession fi ON foi.FunctionID = fi.FunctionID
                WHERE fi.StrategyID=? AND fi.FunctionSuccess=1
                """,
                (strategy_id,),
            )
            return cur.fetchall()

    # ── Missing Methods for Complete Integration ──────────────────────

    def get_strategy_info(self, strategy_name: str) -> Optional[StrategyInfo]:
        """Get strategy information from the library."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT StrategyName, StrategyTarget, PlanSteps
                   FROM StrategyLibrary WHERE StrategyName=?""",
                (strategy_name,),
            )
            row = cur.fetchone()
            if row:
                return StrategyInfo(
                    strategy_id=0,  # Library entry, no instance ID yet
                    goal_id=0,  # Library entry, no goal ID yet
                    name=row[0],
                    success=None,  # Library entry, no execution yet
                    plan_steps=row[2],
                )
            return None

    def get_available_strategies(self) -> List[str]:
        """Get all available strategy names from the library, filtered by testing configuration."""
        from ..config.strategy_testing import get_enabled_strategies

        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT StrategyName FROM StrategyLibrary")
            all_strategies = [row[0] for row in cur.fetchall()]

            # Filter based on testing configuration
            enabled_strategies = get_enabled_strategies()
            filtered_strategies = [s for s in all_strategies if s in enabled_strategies]

            return filtered_strategies

    def get_function_output_templates(
        self, function_name: str
    ) -> List[Tuple[str, str]]:
        """Get output templates for a function (name, type)."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT tpl.OutputName, tpl.Type
                   FROM FunctionOutputLibrary tpl
                   JOIN FunctionTemplateLibrary ft ON tpl.FunctionTemplateID = ft.FunctionTemplateID
                   WHERE ft.FunctionName=?""",
                (function_name,),
            )
            return cur.fetchall()

    def update_function_validation(
        self, function_id: int, is_valid: bool, validation_msg: str
    ) -> None:
        """Update function validation status."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            # Note: This assumes there's a validation field in the database
            # If not present, this could be added to failedtext or a new field
            validation_text = (
                f"VALID: {validation_msg}" if is_valid else f"INVALID: {validation_msg}"
            )
            cur.execute(
                """UPDATE FunctionInSession
                   SET failedtext=?
                   WHERE FunctionID=?""",
                (validation_text, function_id),
            )
            conn.commit()

    def get_goal_info(self, goal_id: int) -> Optional[GoalInfo]:
        """Get goal information by ID."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT GoalID, SessionID, GoalDescription, GoalSuccess
                   FROM GoalInSession WHERE GoalID=?""",
                (goal_id,),
            )
            row = cur.fetchone()
            if row:
                return GoalInfo(
                    goal_id=row[0],
                    session_id=row[1],
                    description=row[2],
                    success=row[3],
                )
            return None

    def update_goal_validation(
        self, goal_id: int, is_satisfied: bool, confidence: float, reason: str = ""
    ) -> None:
        """Update goal validation status and confidence."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            validation_text = f"confidence={confidence:.3f}; {reason}" if reason else f"confidence={confidence:.3f}"
            cur.execute(
                """UPDATE GoalInSession
                   SET GoalSuccess=?, GoalValidation=?
                   WHERE GoalID=?""",
                (1 if is_satisfied else 0, validation_text, goal_id),
            )
            conn.commit()

    def update_strategy_validation(
        self, strategy_id: int, is_satisfied: bool, reason: str = ""
    ) -> None:
        """Update strategy validation status."""
        with get_agentic_connection() as conn:
            cur = conn.cursor()
            status_text = (
                f"SATISFIED: {reason}" if is_satisfied else f"FAILED: {reason}"
            )
            cur.execute(
                """UPDATE StrategyInSession
                   SET StrategySuccess=?, StrategyValidation=?
                   WHERE StrategyID=?""",
                (1 if is_satisfied else 0, status_text, strategy_id),
            )
            conn.commit()


