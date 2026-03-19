"""
Custom exception classes for the workflow system.

This module defines standard exception types for consistent error handling
across all workflow components.
"""

from typing import Any, Dict, List, Optional


class WorkflowError(Exception):
    """Base exception for all workflow errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}


class StrategyError(WorkflowError):
    """Raised when strategy selection or creation fails."""
    pass


class FunctionError(WorkflowError):
    """Raised when function execution fails."""
    
    def __init__(
        self,
        message: str,
        function_name: Optional[str] = None,
        function_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, context)
        self.function_name = function_name
        self.function_id = function_id


class DatabaseError(WorkflowError):
    """Raised when database operations fail."""
    pass


class ParameterError(WorkflowError):
    """Raised when parameter resolution fails."""
    
    def __init__(self, message: str, parameter_name: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, context)
        self.parameter_name = parameter_name


class ValidationError(WorkflowError):
    """Raised when input validation fails."""
    pass


class HandlerNotFoundError(FunctionError):
    """Raised when a function handler cannot be found."""
    pass


class ParallelExecutionError(WorkflowError):
    """Raised when parallel execution fails."""
    
    def __init__(self, message: str, failed_functions: Optional[List[Any]] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, context)
        self.failed_functions = failed_functions or []


