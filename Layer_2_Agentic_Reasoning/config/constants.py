# Layer_2_Agentic_Reasoning/config/constants.py
"""
System-wide constants and default values for the agentic reasoning system.

Defines GENERIC constants used across the application for system limits,
user interface elements, and status codes. Provides centralized configuration
to ensure consistency and easy maintenance.

Categories:
- System performance limits and timeouts
- LLM configuration defaults
- User interface display constants with emoji icons
- Error codes and status values

Design Principles:
- Centralized constant management
- Clear naming conventions with descriptive prefixes
- Type hints and documentation for all constants
- Environment-agnostic default values
- User-friendly display formatting with icons
- GENERIC ONLY - domain-specific constants belong in domain_config.py

Note:
    Domain-specific constants (like table names) have been moved to
    domain_config.py for better separation of concerns. This file now
    contains only generic system-wide constants.
"""

# ═══════════════════════════════════════════════════════════════════════
# SYSTEM PERFORMANCE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

# LLM configuration defaults
DEFAULT_LLM_TEMPERATURE: float = 0.1           # Low temperature for consistent technical responses
DEFAULT_LLM_TIMEOUT: int = 30                  # Seconds before LLM request timeout
MAX_LLM_RETRIES: int = 3                       # Maximum retry attempts for failed LLM calls

# Function execution limits
MAX_FUNCTION_RETRIES: int = 2                  # Maximum function retry attempts
DEFAULT_FUNCTION_TIMEOUT: int = 60             # Seconds before function timeout
MAX_PARALLEL_FUNCTIONS: int = 5                # Maximum concurrent function execution

# Database operation limits
DEFAULT_DATABASE_TIMEOUT: int = 30             # Seconds before database timeout
MAX_DATABASE_CONNECTIONS: int = 10             # Connection pool size
QUERY_RESULT_LIMIT: int = 1000                 # Maximum rows returned per query

# ═══════════════════════════════════════════════════════════════════════
# USER INTERFACE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

# Session state field display labels with emoji icons for UI
ANSWER_FIELDS = {
    "query": "🔍 Query",                       # User input query
    "sessionID": "🆔 Session ID",              # Unique session identifier
    "currentGoalID": "🎯 Goal ID",             # Active goal identifier
    "currentStrategyID": "🧠 Strategy ID",     # Current strategy identifier
    "currentFunctionID": "🧩 Function ID",     # Executing function identifier
    "strategySatisfied": "📐 Strategy OK",     # Strategy completion status
    "goalSatisfied": "🏁 Goal OK",             # Goal completion status
    "strategyAborted": "🚫 Strategy Aborted",  # Strategy failure flag
    "judgeConfidence": "📊 Judge Confidence",  # LLM confidence score (0.0-1.0)
    "finalAnswer": "📦 Final Answer",          # Generated response text
}

# ═══════════════════════════════════════════════════════════════════════
# STATUS AND ERROR CODES
# ═══════════════════════════════════════════════════════════════════════

# Workflow completion status codes
STATUS_SUCCESS = "success"                     # Workflow completed successfully
STATUS_PARTIAL = "partial"                     # Partial completion with warnings
STATUS_FAILED = "failed"                       # Workflow failed completely
STATUS_TIMEOUT = "timeout"                     # Workflow exceeded time limits

# Strategy execution status codes
STRATEGY_PENDING = "pending"                   # Strategy not yet executed
STRATEGY_EXECUTING = "executing"               # Strategy currently running
STRATEGY_COMPLETED = "completed"               # Strategy finished successfully
STRATEGY_ABORTED = "aborted"                   # Strategy failed and abandoned

# Function execution status codes
FUNCTION_SUCCESS = "success"                   # Function executed successfully
FUNCTION_FAILED = "failed"                     # Function execution failed
FUNCTION_TIMEOUT = "timeout"                   # Function exceeded time limit
FUNCTION_SKIPPED = "skipped"                   # Function skipped due to conditions


