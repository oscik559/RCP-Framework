"""
LangGraph workflow definition for the agentic reasoning system.

Defines the state graph that orchestrates the Goal → Strategy → Function
hierarchy. Handles routing logic, parallel execution, and workflow termination.

Workflow Flow:
1. GoalDefine: Parse user query into structured goal
2. StrategyPlan: Select appropriate strategy from library
3. FunctionExecute: Execute functions (sequential or parallel)
4. FunctionValidate: Validate function outputs
5. StrategyValidate: Check strategy completion
6. GoalValidate: Final goal validation and answer generation
7. Done: Workflow termination

Features:
- Automatic Mermaid diagram generation for visualization
- Support for parallel function execution with batching
- Robust error handling and fallback routing
- Three-state strategy validation (success, continue, abort)
"""

from typing import Any, Dict, List
import subprocess
from pathlib import Path

from langgraph.graph import END, StateGraph

from agentic_reasoning.config.debug_config import debug
from agentic_reasoning.logic.types import SessionState
from agentic_reasoning.logic.workflow_nodes import (
    node_done,
    node_function_execute,
    node_function_validate,
    node_goal_define,
    node_goal_validate,
    node_strategy_plan,
    node_strategy_validate,
)

# Configuration
DEBUG = False
# Mermaid CLI path (configure based on your system)
# Windows: MMDC_PATH = "C:\\Users\\<username>\\AppData\\Roaming\\npm\\mmdc.cmd"
# macOS/Linux: MMDC_PATH = "mmdc" (if installed globally)
MMDC_PATH = "mmdc"  # Update this path based on your installation
PNG_CONFIG = {"width": 1200, "height": 800, "timeout": 30}
# Graph files now stored in root docs/ folder (moved from Layer_2/docs/)
DIAGRAM_FILES = {"mermaid": "../docs/graph.mmd", "png": "../docs/graph.png"}


def _get_next_strategy_node(state: SessionState) -> str:
    """
    Determine next node based on strategy completion state.

    Implements three-way routing logic:
    - ABORT: Strategy failed, try new strategy
    - SUCCESS: Strategy completed, validate goal
    - CONTINUE: Execute next function(s)

    Args:
        state: Current session state with strategy status

    Returns:
        Next node name for workflow routing
    """
    if state["strategySatisfied"] and state.get("strategyAborted", False):
        return "StrategyPlan"  # ABORT: Strategy failed, try new strategy
    elif state["strategySatisfied"]:
        return "GoalValidate"  # SUCCESS: Strategy completed, validate goal
    else:
        return "FunctionExecute"  # CONTINUE: Execute next function(s)


def _get_next_from_strategy_plan(state: SessionState) -> str:
    """
    Determine next node from strategy planning.

    Handles workflow termination when all strategies are exhausted
    or continues with function execution for new strategy.

    Args:
        state: Current session state with workflow status

    Returns:
        Next node name ("done" for termination or "FunctionExecute")
    """
    if state.get("workflowComplete", False):
        return "done"  # TERMINATE: All strategies exhausted, workflow complete
    else:
        return "FunctionExecute"  # CONTINUE: New strategy selected, execute functions


def _save_mermaid_diagram(compiled_graph) -> None:
    """Save Mermaid diagram to file."""
    try:
        mermaid_code = compiled_graph.get_graph().draw_mermaid()
        Path(DIAGRAM_FILES["mermaid"]).write_text(mermaid_code)
        debug.print_system("Mermaid diagram saved to: graph.mmd", "✅")
        if DEBUG:
            print(mermaid_code)
    except Exception as e:
        debug.print_system(f"Failed to render Mermaid diagram: {e}", "🟡")


def _generate_png_diagram() -> None:
    """Generate PNG from Mermaid diagram."""
    try:
        result = subprocess.run(
            [
                MMDC_PATH,
                "-i",
                DIAGRAM_FILES["mermaid"],
                "-o",
                DIAGRAM_FILES["png"],
                "-w",
                str(PNG_CONFIG["width"]),
                "-H",
                str(PNG_CONFIG["height"]),
            ],
            capture_output=True,
            text=True,
            timeout=PNG_CONFIG["timeout"],
        )

        if result.returncode == 0:
            debug.print_system("PNG diagram auto-generated: check ../docs/graph.png", "✅")
        else:
            debug.print_system(f"PNG generation failed: {result.stderr}", "🟡")
    except Exception as e:
        debug.print_system(f"PNG generation error: {e}", "🟡")
        debug.print_system("Install with: npm install -g @mermaid-js/mermaid-cli")


def build_graph() -> StateGraph:
    """Build LangGraph workflow with tri-condition routing system."""
    builder = StateGraph(state_schema=SessionState)

    # Register workflow nodes
    nodes = {
        "GoalDefine": node_goal_define,
        "StrategyPlan": node_strategy_plan,
        "FunctionExecute": node_function_execute,  # Central function executor (handles both sequential and parallel)
        "FunctionValidate": node_function_validate,
        "StrategyValidate": node_strategy_validate,
        "GoalValidate": node_goal_validate,
        "done": node_done,
    }

    for name, node in nodes.items():
        builder.add_node(name, node)

    # Set entry point
    builder.set_entry_point("GoalDefine")

    # Linear workflow edges
    workflow_edges = [
        ("GoalDefine", "StrategyPlan"),
        (
            "FunctionExecute",
            "FunctionValidate",
        ),  # FunctionExecute handles both sequential and parallel
        ("FunctionValidate", "StrategyValidate"),
    ]

    for source, target in workflow_edges:
        builder.add_edge(source, target)

    # Conditional routing
    builder.add_conditional_edges(
        "StrategyValidate",
        _get_next_strategy_node,
        {
            "GoalValidate": "GoalValidate",
            "StrategyPlan": "StrategyPlan",
            "FunctionExecute": "FunctionExecute",  # Single entry point for function execution
        },
    )

    builder.add_conditional_edges(
        "StrategyPlan",
        _get_next_from_strategy_plan,
        {
            "done": "done",  # All strategies exhausted
            "FunctionExecute": "FunctionExecute",  # Continue with new strategy
        },
    )

    builder.add_conditional_edges(
        "GoalValidate",
        lambda s: s["goalSatisfied"],
        {True: "done", False: "StrategyPlan"},  # Goal satisfied: True→done, False→retry
    )

    builder.add_edge("done", END)

    # Compile and generate diagrams
    compiled = builder.compile(debug=DEBUG)
    if compiled.config is None:
        compiled.config = {}
    compiled.config["recursion_limit"] = 1000000
    # _save_mermaid_diagram(compiled)
    # _generate_png_diagram()

    return compiled


compiled_graph = build_graph()


def get_graph() -> StateGraph:
    """Returns the compiled state graph for the workflow system."""
    return compiled_graph


