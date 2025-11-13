"""
Core type definitions for the agentic reasoning system.

Defines TypedDict structures for state management and data flow throughout
the multi-agent LLM workflow. These types ensure consistency across all
workflow nodes and provide clear interfaces for state transitions.
"""

from typing_extensions import TypedDict
from typing import Dict, List, Any


class SessionState(TypedDict):
    """
    Main state object that flows through the LangGraph workflow.

    Tracks execution progress from Goal → Strategy → Function hierarchy.
    All workflow nodes receive and modify this state object.

    State Flow:
    1. Goal definition and validation
    2. Strategy selection and planning
    3. Function execution (sequential or parallel)
    4. Result validation and output generation
    """
    # Core session data
    query: str                              # Original user query
    sessionID: int                          # Unique session identifier

    # Current execution context
    currentGoalID: int | None               # Active goal ID from GoalLibrary
    currentStrategyID: int | None           # Active strategy ID from StrategyLibrary
    currentFunctionID: int | None           # Active function ID from FunctionLibrary

    # Completion tracking
    strategySatisfied: bool                 # Current strategy completed successfully
    goalSatisfied: bool                     # Current goal completed successfully
    strategyAborted: bool                   # Strategy failed and should be abandoned
    workflowComplete: bool                  # Entire workflow finished (success or failure)

    # Final results
    judgeConfidence: float | None           # LLM confidence score (0.0-1.0)
    finalAnswer: str | None                 # Generated answer text

    # Parallel execution support
    parallelExecutionMode: bool             # Current strategy uses parallel functions
    parallelBatch: List[int] | None         # Function IDs to execute concurrently
    parallelResults: Dict[int, Any] | None  # Results from parallel function execution
    parallelGroups: (
        List[List[str]] | None
    )  # Groups of functions that should run in parallel


