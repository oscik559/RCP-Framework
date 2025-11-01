# agentic_reasoning/config/debug_config.py
"""
Centralized debug configuration and logging system for the agentic reasoning system.

Provides fine-grained control over debug output with categorized messages, verbosity
levels, and Unicode-safe printing for cross-platform compatibility. Designed for
development, testing, and production debugging of the multi-agent workflow system.

Key Features:
- Five debug levels from silent to verbose output
- Categorized debug messages (workflow, function, strategy, etc.)
- Environment variable configuration (DEBUG_LEVEL)
- Unicode-safe printing for Windows console compatibility
- Color-coded output with emoji icons for visual clarity
- Performance-friendly conditional printing
- Global debug instance for convenient access

Debug Levels:
- 0 (SILENT): No debug output - production mode
- 1 (MINIMAL): Only major workflow steps and errors
- 2 (NORMAL): Standard progress indicators (default)
- 3 (DETAILED): Function parameters, outputs, and execution details
- 4 (VERBOSE): All debug information including data merging and validation

Message Categories:
- workflow: High-level workflow progression and state changes
- goal: Goal definition, validation, and completion tracking
- strategy: Strategy selection, planning, and execution status
- function: Function execution, parameters, and results
- params: Parameter resolution and template processing
- outputs: Function outputs and data merging operations
- merge: Data merging logic and output combination
- debug: General debugging information and diagnostics
- completion: Workflow completion and termination handling
- validation: Input/output validation and error checking
- system: System-level operations and performance metrics

Usage Patterns:
- debug.print_workflow("Node transition: Goal → Strategy")
- debug.print_function(f"Executing {func_name} with {params}")
- debug.print_strategy("Selected strategy: Enhanced lookup")
- if debug.level >= 3: debug.print_detailed("Verbose information")

Configuration:
- Environment variable: DEBUG_LEVEL=2
- Programmatic: set_debug_level(3)
- Config file: debug.enabled = True, debug.level = 2
"""



import os
import sys
from typing import Dict, Set


def safe_print(message: str):
    """
    Print message with Unicode handling for cross-platform compatibility.
    
    Handles Windows console encoding issues by falling back to ASCII
    representation when Unicode characters cannot be displayed.
    
    Args:
        message: Text to print (may contain Unicode characters)
    """
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback for Windows console encoding issues
        print(message.encode("ascii", "replace").decode("ascii"))


class DebugConfig:
    """
    Centralized debug configuration with different verbosity levels.

    Debug Levels:
    - 0: SILENT - No debug output
    - 1: MINIMAL - Only major workflow steps
    - 2: NORMAL - Standard progress indicators (default)
    - 3: DETAILED - Include function parameters and outputs
    - 4: VERBOSE - All debug information including merging details
    """

    def __init__(self):
        # Get debug level from environment or default to 2
        self.level = int(os.getenv("DEBUG_LEVEL", "2"))
        self._last_function = None  # Track function changes for spacing

        # Define what gets printed at each level
        self.enabled_categories: Dict[int, Set[str]] = {
            0: set(),  # SILENT
            1: {"workflow", "goal", "strategy", "completion", "system"},  # MINIMAL
            2: {
                "workflow",
                "goal",
                "strategy",
                "function",
                "completion",
                "system",
            },  # NORMAL
            3: {
                "workflow",
                "goal",
                "strategy",
                "function",
                "params",
                "outputs",
                "completion",
                "validation",
                "system",
            },  # DETAILED
            4: {
                "workflow",
                "goal",
                "strategy",
                "function",
                "params",
                "outputs",
                "merge",
                "debug",
                "completion",
                "validation",
                "system",
            },  # VERBOSE
        }

    def should_print(self, category: str) -> bool:
        """Check if debug output should be printed for given category."""
        return category in self.enabled_categories.get(self.level, set())

    def print_workflow(self, message: str, icon: str = "🔧"):
        """Print workflow-level messages."""
        if self.should_print("workflow"):
            safe_print(f"{icon} {message}")

    def print_goal(self, message: str, icon: str = "🎯"):
        """Print goal-related messages."""
        if self.should_print("goal"):
            safe_print(f"{icon} {message}")

    def print_strategy(self, message: str, icon: str = "📊"):
        """Print strategy-related messages."""
        if self.should_print("strategy"):
            safe_print(f"{icon} {message}")

    def print_function(self, message: str, icon: str = "🚀"):
        """Print function execution messages with automatic spacing."""
        if self.should_print("function"):
            # Extract function name for spacing logic
            current_function = None
            if "Starting:" in message:
                # Extract function name after "Starting: "
                try:
                    current_function = message.split("Starting: ")[1].strip()
                except IndexError:
                    pass
            elif "[func_" in message:
                try:
                    start = message.index("[func_")
                    end = message.index("]", start)
                    current_function = message[start+1:end]
                except ValueError:
                    pass

            # Add prominent separator when starting a new function
            if ("Starting:" in message and
                current_function and
                self._last_function != current_function):
                safe_print("")
                safe_print("─" * 60)
                safe_print(f"🔹 EXECUTING: {current_function}")
                safe_print("─" * 60)
                self._last_function = current_function

            # Add spacing for other function messages
            elif (current_function and
                  self._last_function and
                  current_function != self._last_function and
                  not message.startswith("Starting:")):
                safe_print("")  # Add blank line between different functions

            safe_print(f"{icon} {message}")

            # Update last function for next comparison
            if current_function and "[func_" in message:
                self._last_function = current_function

    def print_params(self, message: str, icon: str = "📝"):
        """Print parameter resolution messages."""
        if self.should_print("params"):
            safe_print(f"{icon} {message}")

    def print_outputs(self, message: str, icon: str = "💾"):
        """Print output messages."""
        if self.should_print("outputs"):
            safe_print(f"{icon} {message}")

    def print_merge(self, message: str, icon: str = "🔄"):
        """Print merge operation messages."""
        if self.should_print("merge"):
            safe_print(f"{icon} {message}")

    def print_debug(self, message: str, icon: str = "🔧"):
        """Print detailed debug messages."""
        if self.should_print("debug"):
            safe_print(f"{icon} [DEBUG] {message}")

    def print_completion(self, message: str, icon: str = "✅"):
        """Print completion messages."""
        if self.should_print("completion"):
            safe_print(f"{icon} {message}")

    def print_validation(self, message: str, icon: str = "🔍"):
        """Print validation messages."""
        if self.should_print("validation"):
            safe_print(f"{icon} {message}")

    def print_system(self, message: str, icon: str = "⚙️"):
        """Print system messages (diagrams, setup, etc.)."""
        if self.should_print("system"):
            safe_print(f"{icon} {message}")

    def print_error(self, message: str, icon: str = "❌"):
        """Print error messages (always shown regardless of level)."""
        safe_print(f"{icon} {message}")

    def print_warning(self, message: str, icon: str = "🔸"):
        """Print warning messages (always shown regardless of level)."""
        safe_print(f"{icon} {message}")


# Global debug instance
debug = DebugConfig()


def set_debug_level(level: int):
    """Set the debug level programmatically."""
    debug.level = level
    debug._last_function = None  # Reset function tracking


def get_debug_level() -> int:
    """Get current debug level."""
    return debug.level


