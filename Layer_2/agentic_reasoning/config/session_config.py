# agentic_reasoning/config/session_config.py
"""
Session management and workflow configuration for the agentic reasoning system.

Provides utilities for initializing session state, generating unique identifiers,
and configuring workflow execution parameters. Ensures consistent session
management across all workflow nodes and components.

Key Functions:
- Session state initialization with sensible defaults
- Unique session ID generation for tracking and debugging
- Workflow configuration for execution parameters and limits
- Session cleanup and resource management utilities

Session State Management:
- Tracks current execution context (goal, strategy, function)
- Maintains completion flags and error states
- Supports parallel execution state tracking
- Provides session lifecycle management

Workflow Configuration:
- Execution timeouts and retry limits
- Debug mode and logging configuration
- Resource limits and performance settings
- Error handling and recovery parameters

Design Principles:
- Immutable default configurations with override support
- Unique session tracking for debugging and monitoring
- Resource-conscious default limits and timeouts
- Environment-aware configuration loading
"""


import uuid
from typing import Any, Dict, Optional


def get_default_session_state(
    query: Optional[str] = None, session_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Initialize session state with default values and optional overrides.

    Creates a new session state dictionary with all required fields initialized
    to safe default values. Supports override of key fields for testing or
    specific use cases.

    Args:
        query: User query string. If None, no default query is set
        session_id: Session identifier. If None, generates timestamp-based ID

    Returns:
        Dictionary containing complete SessionState with default values:
        - All execution IDs set to None (will be populated during workflow)
        - Completion flags set to False
        - Empty parallel execution state
        - Unique session identifier for tracking
    """

    return {
        "query": query,
        "sessionID": session_id or generate_session_id(),
        "currentGoalID": None,
        "currentStrategyID": None,
        "currentFunctionID": None,
        "strategySatisfied": False,
        "goalSatisfied": False,
        "strategyAborted": False,  # New flag for tri-condition routing
        "workflowComplete": False,  # Flag for graceful termination when all strategies fail
        "judgeConfidence": None,
        "finalAnswer": None,
        # Parallel execution support
        "parallelExecutionMode": False,
        "parallelBatch": None,
        "parallelResults": None,
        "parallelGroups": None,
    }


def generate_session_id() -> int:
    """
    Generate a unique session ID.

    Returns:
        Unique integer session identifier
    """
    # For now, use simple timestamp-based ID

    import time

    return int(time.time() * 1000) % 1000000  # Last 6 digits of timestamp


def get_workflow_config() -> Dict[str, Any]:
    """
    Get workflow execution configuration.

    Returns:
        Dictionary containing workflow settings
    """
    return {
        "recursion_limit": 1000000,  # Increased for complex strategies while preventing infinite loops
        "debug_mode": False,
        "enable_logging": True,
        "timeout_seconds": 300,
    }


