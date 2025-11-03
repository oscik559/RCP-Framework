# workflow_nodes.py
"""
LangGraph workflow node implementations for the agentic reasoning system.

Orchestrates the multi-step Goal → Strategy → Function workflow with LLM-powered
decision making, parallel execution support, and robust error handling.

Workflow Architecture:
1. Goal Definition: Parse user query into structured objective
2. Strategy Planning: Select optimal approach from template library
3. Function Execution: Execute business logic (sequential/parallel)
4. Validation: Validate outputs and assess completion
5. Goal Validation: Final LLM judgment and confidence scoring

Node Functions:
- node_goal_define: Single goal per session with LLM-assisted parsing
- node_strategy_plan: Strategy selection with parallel execution support
- node_function_execute: Function dispatch with sequential/parallel modes
- node_function_validate: Output validation against expected schemas
- node_strategy_validate: Tri-state routing (abort/success/continue)
- node_goal_validate: LLM judge for goal completion assessment
- node_done: Terminal workflow completion

Key Features:
- Parallel function execution with batching and result aggregation
- LLM-powered decision making with fallback mechanisms
- Comprehensive error handling with immediate abort logic
- Database-driven execution tracking and state persistence
- Modular design with helper functions for common operations

Dependencies:
- Database: SQLite with context managers for session management
- LLM: Ollama models (basic/reasoning tiers) with structured prompts
- Function Library: 15+ business logic functions with standardized interface
- Templates: Dynamic strategy and function definitions from database

Usage:
Designed for LangGraph workflow engine with SessionState coordination
between nodes for multi-agent reasoning and execution.
"""


import concurrent.futures
import json
import logging
import re
import sqlite3
from typing import Any, Dict, List, Optional

from config.debug_config import debug
from config.prompt_loader import get_prompt_loader
from logic.function_library import FUNCTION_MAP
from logic.llm_helpers import get_basic_llm, get_reasoning_llm
from logic.database_manager import DatabaseManager
from logic.workflow_helpers import (
    collect_outputs,
    handler_from_name,
    infer_sql_type,
    merge_values,
    parse_json_response,
    safe_json_parse,
)
from logic.types import SessionState
from logic.exceptions import (
    WorkflowError,
    StrategyError,
    FunctionError,
    DatabaseError,
    ParameterError,
    ValidationError,
    HandlerNotFoundError,
    ParallelExecutionError,
)

logger = logging.getLogger("NODES")

# Global database manager instance to avoid scattered imports
db = DatabaseManager()

# Note: Helper functions like infer_sql_type, collect_outputs, merge_values,
# handler_from_name are imported from workflow_helpers to avoid duplication


# ── Goal Definition Helper ────────────────────────────────────────
def _create_goal_with_llm_definition(db, session_id: int, query: str) -> int:
    """
    Create a goal with LLM-assisted definition for better validation.

    Args:
        db: DatabaseManager instance
        session_id: Current session ID
        query: User query string

    Returns:
        Goal ID of the created goal
    """
    from config.prompt_loader import get_prompt_loader
    from logic.llm_helpers import get_basic_llm

    import json
    import re

    # Get LLM to define the goal
    prompt_loader = get_prompt_loader()
    prompt = prompt_loader.format_prompt("goal_definition", query=query)

    try:
        from logic.llm_helpers import invoke_llm_with_retry
        
        llm = get_basic_llm()
        response = invoke_llm_with_retry(
            llm,
            [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ],
            max_retries=3,
            base_delay=1.0
        ).content
        debug.print_goal(f"Goal definition response: {response}")

        # Parse the JSON response robustly
        goal_definition = parse_json_response(response)
        if not goal_definition:
            # Fallback: try the old parsing method
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response.strip()
            try:
                goal_definition = json.loads(json_str)
            except json.JSONDecodeError as e:
                # Final fallback: create basic goal definition
                goal_definition = {
                    "goal_description": f"To answer the question: {query.rstrip('?.!')}",
                    "goal_target": " ".join(query.split()[:4]),
                }

        # Create goal with enhanced description
        goal_desc = goal_definition.get(
            "goal_description", f"To answer the question: {query.rstrip('?.!')}"
        )
        target = " ".join(query.split()[:4])  # First 4 words as target

        # Store the full goal definition as additional metadata
        goal_metadata = {
            "expected_content_types": goal_definition.get("expected_content_types", []),
            "key_terms": goal_definition.get("key_terms", []),
            "success_indicators": goal_definition.get("success_indicators", []),
        }

        goal_id = db.create_goal(session_id, goal_desc, "MainGoal", target)

        # Store goal definition metadata (you may need to add this to database schema)
        # For now, we'll just store it in the description for simplicity
        debug.print_goal(f"Goal: '{goal_desc}'")
        debug.print_goal(
            f"Expected content: {goal_definition.get('expected_content_types', [])}"
        )
        debug.print_goal(f"Key terms: {goal_definition.get('key_terms', [])}")

        return goal_id

    except Exception as e:
        debug.print_error(f"Goal definition failed: {e}")
        # Fallback to simple goal creation
        goal_desc = f"To answer the question: {query.rstrip('?.!')}"
        target = " ".join(query.split()[:4])
        goal_id = db.create_goal(session_id, goal_desc, "MainGoal", target)
        debug.print_goal(f"Goal (fallback): '{goal_desc}'")
        return goal_id


# ── Output Collection Helper ───────────────────────────────────────
# Using workflow_helpers.collect_outputs - removed duplicate function


# ── Value Merging Helper ───────────────────────────────────────────
# Using workflow_helpers.merge_values - removed duplicate function


# ── helper: resolve function handler by name ─────────────────────────
# Using workflow_helpers.handler_from_name - removed duplicate function


# ── Goal Definition Node ──────────────────────────────────────────
def node_goal_define(session_state: SessionState) -> SessionState:
    """
    Define or reuse a goal instance for the current session.

    This node ensures there is exactly one active goal per session. It handles:
    - Reusing existing unfinished goals for the same query
    - Cleaning up failed goals when a different query is provided
    - Creating new goals when needed

    Args:
        state: Current session state containing sessionID and query

    Returns:
        Updated state with currentGoalID set

    Business Logic:
    - One goal per session maximum
    - Failed goals are cleaned up if query changes
    - Successful strategies preserve the goal for reuse
    """
    sess = session_state["sessionID"]
    query = session_state["query"].strip()

    # Step 1: Check for existing unfinished goals
    existing_goal = db.find_unfinished_goal(sess)

    if existing_goal:
        # Check if this goal has any successful strategies
        successful_strategies = db.count_successful_strategies(existing_goal.goal_id)

        # If no successful strategies and we have a new query, start fresh
        if successful_strategies == 0:
            new_desc = f"To answer the question: {query.rstrip('?.!')}"

            # If it's a different question, clean up and start fresh
            if existing_goal.description != new_desc:
                debug.print_workflow("Removing failed goal for different query")
                db.cleanup_failed_goal(existing_goal.goal_id)
                # Create new goal with LLM-assisted definition
                goal_id = _create_goal_with_llm_definition(db, sess, query)
            else:
                # Same question, reuse the existing goal
                session_state["currentGoalID"] = existing_goal.goal_id
                return session_state
        else:
            # Has successful strategies, reuse the goal
            session_state["currentGoalID"] = existing_goal.goal_id
            return session_state
    else:
        # Step 2: Create a new goal instance with LLM assistance
        goal_id = _create_goal_with_llm_definition(db, sess, query)

    # Store the new goal ID in state for subsequent nodes
    session_state["currentGoalID"] = goal_id

    return session_state


# ── Strategy Definition Node ───────────────────────────────────────


def node_strategy_plan(session_state: SessionState) -> SessionState:
    """
    Select and instantiate an appropriate strategy from the library.

    Uses LLM to choose the best strategy based on query analysis and available
    templates. Handles parallel execution markers and workflow termination
    when all strategies are exhausted.

    Key Responsibilities:
    - LLM-powered strategy selection from StrategyLibrary
    - Parallel execution plan parsing ([Func1 || Func2] syntax)
    - Function instance creation and parameter template setup
    - Workflow termination detection when no strategies remain
    """
    import json
    import re

    gid, query = session_state["currentGoalID"], session_state["query"]

    # Check for existing incomplete strategy
    current_strategy = db.get_current_strategy(gid)
    debug.print_debug(f"Current strategy: {current_strategy}")

    if current_strategy and current_strategy.success is None:
        # Get next pending function
        next_function_id = db.get_current_function_id(current_strategy.strategy_id)
        debug.print_debug(f"Next function ID: {next_function_id}")

        if next_function_id:
            session_state.update(
                currentStrategyID=current_strategy.strategy_id,
                currentFunctionID=next_function_id,
                strategySatisfied=False,
                strategyAborted=False,  # Reset abort flag
            )
            return session_state

    # ─── LLM Strategy Selection ─────────────────────────
    from config.prompt_loader import get_prompt_loader

    prompt_loader = get_prompt_loader()

    # Gather required template parameters
    goal_info = db.get_goal_info(gid)
    goal_desc = goal_info.description if goal_info else query

    # Get tried strategies (already executed)
    tried_strategies = db.get_tried_strategies(gid)
    tried_readable = (
        "\n".join([f"- {s}" for s in tried_strategies])
        if tried_strategies
        else "- None"
    )

    # Get available strategies (filter out already tried ones)
    all_strategies = db.get_available_strategies()

    # Show testing configuration on first strategy selection
    if not tried_strategies:
        from config.strategy_testing import print_testing_status

        print_testing_status()

    available_strategies = [s for s in all_strategies if s not in tried_strategies]

    # Check if we have any untried strategies left
    if not available_strategies:
        # All strategies exhausted - check if we have any successful strategies to use
        debug.print_strategy(
            f"All available strategies exhausted for goal {gid}. Tried: {tried_strategies}",
            "❌",
        )

        # Check if we have successful strategies with outputs to accept
        successful_strategies = db.get_successful_strategies(gid)
        if successful_strategies:
            # Accept the best available result from successful strategies
            debug.print_goal(
                "Accepting best available result from successful strategies"
            )
            session_state["goalSatisfied"] = True
            session_state["strategySatisfied"] = True
            session_state["judgeConfidence"] = (
                0.6  # Medium confidence for fallback acceptance
            )
            session_state["workflowComplete"] = True

            # Set a fallback final answer from the first successful strategy
            for strategy_id in successful_strategies:
                strategy_outputs = db.get_strategy_outputs(strategy_id)
                if strategy_outputs:
                    # Look for the best analysis result first
                    # Priority order: Analysis, Analyze Output, Answer, then any other outputs
                    analysis_result = None
                    
                    # First pass: Look for Analysis (from func_analyze_with_llm)
                    for name, value in strategy_outputs:
                        if name == "Analysis":
                            analysis_result = value
                            break
                    
                    # Second pass: Look for legacy Analyze Output or Answer
                    if not analysis_result:
                        for name, value in strategy_outputs:
                            if name in ("Analyze Output", "Answer", "answer"):
                                analysis_result = value
                                break
                    
                    # Third pass: If still no analysis, filter out intermediate data outputs
                    if not analysis_result:
                        # Exclude raw data outputs (assembled data, extracted data, results lists)
                        filtered_outputs = []
                        for name, value in strategy_outputs:
                            # Skip raw data outputs
                            if name.lower() in ("results", "assembled data", "extracted_data", "items", "records"):
                                continue
                            # Skip outputs that look like raw JSON lists
                            if isinstance(value, str) and value.strip().startswith('[{"'):
                                continue
                            filtered_outputs.append((name, value))
                        
                        if filtered_outputs:
                            # Use the first meaningful output
                            analysis_result = filtered_outputs[0][1]

                    if analysis_result:
                        session_state["finalAnswer"] = analysis_result
                    else:
                        # Last resort: combine all outputs
                        output_text = "; ".join(
                            [f"{name}: {value}" for name, value in strategy_outputs]
                        )
                        session_state["finalAnswer"] = (
                            f"Best available result: {output_text[:500]}..."
                        )
                    break

            return session_state
        else:
            # No successful strategies at all - true failure
            db.update_goal_status(gid, False)
            session_state["goalSatisfied"] = False
            session_state["strategySatisfied"] = False
            session_state["judgeConfidence"] = 0.0
            session_state["workflowComplete"] = True

            error_msg = f"Error: All strategies failed execution for goal {gid}. Tried: {tried_strategies}"
            debug.print_error(error_msg)
            session_state["finalAnswer"] = "No strategies succeeded in execution"

            return session_state

    lib_block = "\n".join([f"- {s}" for s in available_strategies])

    prompt = prompt_loader.format_prompt(
        "strategy_selection",
        query=query,
        goal_desc=goal_desc,
        tried_readable=tried_readable,
        lib_block=lib_block,
    )

    # Import retry helper
    from logic.llm_helpers import invoke_llm_with_retry
    
    # Use retry logic for LLM invocation
    try:
        llm_raw = invoke_llm_with_retry(
            get_basic_llm(),
            [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ],
            max_retries=3,
            base_delay=2.0
        )
    except Exception as e:
        error_msg = f"LLM strategy selection failed after retries: {str(e)}"
        debug.print_error(error_msg)
        raise StrategyError(error_msg, {"exception": str(e), "query": query})

    if hasattr(llm_raw, "content"):
        llm_resp = llm_raw.content.strip()
    else:
        llm_resp = str(llm_raw).strip()

    # Parse JSON response robustly
    strategy_resp = parse_json_response(llm_resp)

    if not strategy_resp:
        raise StrategyError(
            f"Strategy selection failed - LLM returned invalid JSON: {llm_resp}",
            {"llm_response": llm_resp, "query": query},
        )

    sname = strategy_resp.get(
        "strategy_name", strategy_resp.get("StrategyName", "")
    ).strip()
    if not sname:
        raise StrategyError(
            f"Strategy selection failed - missing strategy_name: {strategy_resp}",
            {"strategy_response": strategy_resp, "query": query},
        )

    # Get strategy details from database
    strategy_info = db.get_strategy_info(sname)
    if not strategy_info:
        available_strategies = db.get_available_strategies()
        raise StrategyError(
            f"Strategy '{sname}' not found. Available: {available_strategies}",
            {"requested_strategy": sname, "available_strategies": available_strategies},
        )

    plan_steps = strategy_info.plan_steps
    plan_funcs = [step.strip() for step in plan_steps.split(",")]
    debug.print_strategy(f"Strategy {sname} with functions: {plan_funcs}")

    # Parse parallel syntax: [Function1 || Function2 || Function3]
    parallel_groups = []
    sequential_funcs = []

    for func_step in plan_funcs:
        if func_step.startswith("[") and func_step.endswith("]"):
            # This is a parallel group
            parallel_content = func_step[1:-1]  # Remove brackets
            parallel_funcs = [f.strip() for f in parallel_content.split("||")]
            parallel_groups.append(parallel_funcs)
            debug.print_strategy(f"Found parallel group: {parallel_funcs}")
        else:
            # Regular sequential function
            sequential_funcs.append(func_step)

    # Validate all functions exist (including those in parallel groups)
    all_funcs = sequential_funcs.copy()
    for group in parallel_groups:
        all_funcs.extend(group)

    available_functions = db.get_available_functions()
    unknown = [f for f in all_funcs if f not in available_functions]
    if unknown:
        raise RuntimeError(f"Unknown functions in plan: {unknown}")

    # Create strategy and function instances using DatabaseManager
    sid = db.create_strategy(gid, sname, plan_steps)
    debug.print_debug(f"Created strategy {sid}")

    debug.print_debug(
        f"About to create functions for strategy {sid} with plan: {plan_steps}"
    )
    db.create_strategy_functions(sid, sname, plan_steps)
    debug.print_debug(f"Created functions for strategy {sid}")

    # If we have parallel groups, store them for later but start in sequential mode
    if parallel_groups:
        debug.print_strategy(
            f"Strategy contains {len(parallel_groups)} parallel groups"
        )
        # Store parallel groups information for later use
        session_state["parallelGroups"] = parallel_groups
        session_state["parallelExecutionMode"] = False  # Start sequential
        session_state["parallelBatch"] = None

        # Start with the first sequential function (before any parallel group)
        first_fid = db.get_current_function_id(sid)
        session_state["currentFunctionID"] = first_fid
        debug.print_debug(f"First function ID (before parallel): {first_fid}")
    else:
        # Regular sequential execution
        session_state["parallelExecutionMode"] = False
        session_state["parallelBatch"] = None
        session_state["parallelGroups"] = None

        # Get first function ID
        first_fid = db.get_current_function_id(sid)
        session_state["currentFunctionID"] = first_fid
        debug.print_debug(f"First function ID: {first_fid}")

        if first_fid is None:
            raise RuntimeError(f"No functions were created for strategy {sid}")

    # Copy parameter templates using DatabaseManager
    function_ids = db.get_strategy_function_ids(sid)
    for function_id, fname in function_ids:
        # Get parameter templates for this function
        param_templates = db.get_function_parameter_templates(fname)
        for pname, pval, ptype in param_templates:
            db.store_function_parameter(
                function_id, fname, pname, pval, ptype or "string", sname
            )

    session_state.update(
        currentStrategyID=sid,
        currentFunctionID=first_fid,
        strategySatisfied=False,
        strategyAborted=False,  # Reset abort flag for new strategy
    )
    return session_state


# ── Function Execution Node ────────────────────────────────────────


def node_function_execute(session_state: SessionState) -> SessionState:
    """
    Central function execution dispatcher for sequential and parallel execution.

    Core execution node that handles both execution modes based on strategy
    configuration. Manages function lifecycle, parameter resolution, and
    result aggregation with comprehensive error handling.

    Execution Flow:
    1. Detect execution mode from strategy configuration
    2. Resolve function parameters from templates and prior outputs
    3. Execute functions via handler dispatch (sequential/parallel)
    4. Update database with execution results and timing
    5. Aggregate outputs and update session state

    Parallel Support:
    - Detects [Func1 || Func2] patterns in strategy plans
    - Concurrent execution with ThreadPoolExecutor
    - Result aggregation and error handling across parallel functions

    Error Handling:
    - Function-level error capture and logging
    - Strategy abortion on critical function failures
    - Graceful degradation for non-critical function errors
    """
    debug.print_debug(
        f"\\node_function_execute called with state: currentFunctionID={session_state.get('currentFunctionID')}, sessionID={session_state.get('sessionID')}"
    )

    # Guard clause: Don't execute if strategy is already aborted
    if session_state.get("strategyAborted", False):
        debug.print_warning("Strategy already aborted, skipping execution")
        return session_state

    # Determine execution mode and dispatch
    if session_state.get("parallelExecutionMode", False) and session_state.get(
        "parallelBatch"
    ):
        debug.print_function("Executing functions in parallel mode")
        return _execute_parallel_functions(session_state)
    else:
        debug.print_function("Executing function in sequential mode")
        return _execute_sequential_function(session_state)


def _execute_parallel_functions(session_state: SessionState) -> SessionState:
    """
    Execute multiple functions in parallel for improved performance.

    This function implements concurrent function execution for strategies that use
    the parallel format: [Function1 || Function2 || Function3]
    """
    # Reuse existing parallel execution logic
    return node_parallel_execute(session_state)


def _execute_sequential_function(session_state: SessionState) -> SessionState:
    """
    Execute a single function in sequential mode.

    This is the original node_function_execute logic for single function execution.
    """
    debug.print_debug(
        f"\node_function_execute called with state: currentFunctionID={session_state.get('currentFunctionID')}, sessionID={session_state.get('sessionID')}"
    )

    # Guard clause: Don't execute if strategy is already aborted
    # This prevents unnecessary work when a strategy has already failed
    if session_state.get("strategyAborted", False):
        debug.print_warning("Strategy already aborted, skipping execution")
        return session_state

    function_id, sess, gid = (
        session_state["currentFunctionID"],
        session_state["sessionID"],
        session_state["currentGoalID"],
    )
    query = session_state["query"]

    # Step 1: Get function information
    func_info = db.get_function_info(function_id)
    if not func_info:
        raise FunctionError(
            f"Function {function_id} not found",
            function_id=function_id,
            context={"session_id": sess, "goal_id": gid},
        )

    fn, current_strategy_id, strategy_name = (
        func_info.function_name,
        func_info.strategy_id,
        func_info.strategy_name,
    )
    debug.print_function(f"Starting: {fn}")

    # Step 2: Build function parameters just-in-time
    # Parameters are filled from templates and merged with outputs from prior functions
    param_dict = {}
    func_params = db.get_function_parameters(fn)

    for param in func_params:
        pname, pval, ptype = (
            param.parameter_name,
            param.parameter_value,
            param.parameter_type,
        )
        if pval == "Input":
            # Use user query directly
            final_val = query
            debug.print_params(f"{pname} ← User query")
        elif pval == "":
            # Merge outputs from prior functions in this strategy
            values = collect_outputs(sess, gid, pname, current_strategy_id)
            final_val = merge_values(pname, values)

            # Special case: If this is the "Input" parameter and no prior outputs exist,
            # use the user query (for first function in strategy)
            if pname == "Input" and not values:
                final_val = query
                debug.print_params(f"{pname} ← User query (first function)")
            elif not values:
                # Warning: Parameter has no value from previous functions
                debug.print_warning(f"{pname} ← No prior outputs found, using empty string")
                final_val = ""
            else:
                debug.print_params(f"{pname} ← {len(values)} merged outputs")
        else:
            # Use template value as-is
            final_val = pval
            debug.print_params(f"{pname} ← template: '{pval}'")

        param_dict[pname] = final_val

    # Step 2.5: Store the actual resolved parameter values in the database
    import json as json_module
    for pname, pval in param_dict.items():
        # Use JSON serialization for lists/dicts to preserve structure
        if isinstance(pval, (list, dict)):
            param_str = json_module.dumps(pval)
        else:
            param_str = str(pval)
        db.update_function_parameter(function_id, pname, param_str)

    # Step 3: Execute function with resolved parameters
    debug.print_function(f"Execute {fn} with {len(param_dict)} parameters")
    # Print detailed input parameters for inspection
    print(f"\n{'='*80}")
    print(f"🔍 FUNCTION EXECUTION DETAILS")
    print(f"{'='*80}")
    print(f"📋 Function: {fn}")
    print(f"🆔 Function ID: {function_id}")
    print(f"📥 INPUT PARAMETERS ({len(param_dict)}):")
    for pname, pval in param_dict.items():
        val_preview = str(pval)[:200] if pval else "None"
        print(f"   • {pname}: {val_preview}")
    print(f"{'-'*80}")
    
    # Note: Parameter details available in debug logs if needed
    try:
        handler = handler_from_name(fn)
        success, result = handler(param_dict)
        
        # Print detailed output for inspection
        print(f"📤 OUTPUT:")
        print(f"   ✓ Success: {success}")
        if success and isinstance(result, dict):
            for out_name, out_val in result.items():
                val_preview = str(out_val)[:300] if out_val else "None"
                print(f"   • {out_name}: {val_preview}")
        else:
            result_preview = str(result)[:300] if result else "None"
            print(f"   • Result: {result_preview}")
        print(f"{'='*80}\n")
        
        debug.print_function(f"{fn} → Success: {success}")
    except ValueError as e:
        debug.print_error(f"{fn} → Handler not found: {e}")
        success, result = False, f"Function handler not found: {str(e)}"
        raise HandlerNotFoundError(
            f"Function handler not found for '{fn}': {str(e)}",
            function_name=fn,
            function_id=function_id,
            context={"parameters": list(param_dict.keys())},
        )
    except Exception as e:
        debug.print_error(f"{fn} → Exception: {e}")
        success, result = False, f"Exception during execution: {str(e)}"
        raise FunctionError(
            f"Exception during execution of '{fn}': {str(e)}",
            function_name=fn,
            function_id=function_id,
            context={"parameters": param_dict, "exception_type": type(e).__name__},
        )

    # Step 4: Update function status
    db.update_function_status(
        function_id, success, str(result) if not success else "Completed successfully"
    )

    # Step 5: Handle function outputs if successful
    if success:
        # Get expected outputs from function library
        output_templates = db.get_function_output_templates(fn)

        if isinstance(result, dict):
            # Store each output with type inference
            for out_name, out_val in result.items():
                if out_name in [template[0] for template in output_templates]:
                    # Use JSON serialization for lists/dicts to preserve structure
                    if isinstance(out_val, (list, dict)):
                        val_str = json_module.dumps(out_val)
                    else:
                        val_str = str(out_val)
                    sql_type = infer_sql_type(val_str)
                    db.store_function_output(
                        function_id, fn, out_name, val_str, sql_type, strategy_name
                    )
                    debug.print_outputs(f"{out_name}: {val_str[:100]}...")

        # Convert key outputs to final answer format for terminal display
        if fn == "Data Analysis":
            session_state["finalAnswer"] = result.get("Analysis Result", str(result))
        elif "analysis" in result:
            session_state["finalAnswer"] = result["analysis"]
        elif "Assembled Data" in result:
            session_state["finalAnswer"] = (
                f"Data assembled: {result['Assembled Data'][:200]}..."
            )
        else:
            # Default final answer from first output
            first_output = next(iter(result.values())) if result else str(result)
            session_state["finalAnswer"] = str(first_output)[:500] + (
                "..." if len(str(first_output)) > 500 else ""
            )

    else:
        # Function failed - don't store any outputs
        debug.print_error(f"Function {fn} failed: {result}")
        session_state["finalAnswer"] = f"Function execution failed: {result}"

    # Step 6: Update state for workflow routing
    # The strategy validation node will use these flags to route appropriately
    session_state["functionSuccess"] = success

    # Only set abort flag if this is a critical failure
    # Some functions might fail but strategy can still continue with alternatives
    if not success:
        session_state["strategyAborted"] = (
            True  # Signal immediate abort to strategy validation
        )
        debug.print_function(f"Function {fn} failed, marking strategy for abort", "🚨")

    return session_state


# ── Parallel Function Execution Node ──────────────────────────────


def node_parallel_execute(session_state: SessionState) -> SessionState:
    """
    Execute multiple functions in parallel for improved performance.

    This node implements concurrent function execution for strategies that use
    the parallel format: [Function1 || Function2 || Function3]

    Key Features:
    - Concurrent execution using asyncio/threading
    - Aggregated output collection from all parallel functions
    - Proper error handling and abort logic
    - Maintains output compatibility with sequential functions

    Args:
        state: Session state with parallelBatch containing function IDs to execute

    Returns:
        Updated state with aggregated results from all parallel functions
    """
    import asyncio
    import concurrent.futures

    debug.print_debug(
        f"\\node_parallel_execute called with parallelBatch: {session_state.get('parallelBatch')}"
    )

    # Guard clause: Check if we have functions to execute in parallel
    parallel_batch = session_state.get("parallelBatch", [])
    if not parallel_batch:
        debug.print_warning("No parallel batch found, skipping parallel execution")
        return session_state

    # Guard clause: Don't execute if strategy is already aborted
    if session_state.get("strategyAborted", False):
        debug.print_warning("Strategy already aborted, skipping parallel execution")
        return session_state

    db = DatabaseManager()
    query = session_state["query"]
    sess = session_state["sessionID"]
    gid = session_state["currentGoalID"]

    def execute_single_function(function_id):
        """Execute a single function - to be run in parallel."""
        try:
            # Get function information
            func_info = db.get_function_info(function_id)
            if not func_info:
                return function_id, False, f"Function {function_id} not found"

            fn = func_info.function_name
            current_strategy_id = func_info.strategy_id
            strategy_name = func_info.strategy_name
            debug.print_function(f"[Parallel] Starting: {fn}")

            # Build function parameters (similar to regular execution)
            param_dict = {}
            func_params = db.get_function_parameters(fn)

            for param in func_params:
                pname, pval, ptype = (
                    param.parameter_name,
                    param.parameter_value,
                    param.parameter_type,
                )
                if pval == "Input":
                    final_val = query
                elif pval == "":
                    values = collect_outputs(sess, gid, pname, current_strategy_id)
                    final_val = merge_values(pname, values)
                    if pname == "Input" and not values:
                        final_val = query
                else:
                    final_val = pval
                param_dict[pname] = final_val

            # Store resolved parameters
            for pname, pval in param_dict.items():
                db.update_function_parameter(function_id, pname, str(pval))

            # Execute the function
            try:
                handler = handler_from_name(fn)
                success, result = handler(param_dict)
                debug.print_function(f"[Parallel] {fn} → Success: {success}")
            except ValueError as e:
                debug.print_error(f"[Parallel] {fn} → Handler not found: {e}")
                success, result = False, f"Function handler not found: {str(e)}"
            except Exception as e:
                debug.print_error(f"[Parallel] {fn} → Exception: {e}")
                success, result = False, f"Exception during execution: {str(e)}"
            debug.print_function(f"[Parallel] {fn} → Success: {success}")

            # Update function status
            db.update_function_status(
                function_id,
                success,
                str(result) if not success else "Completed successfully",
            )

            # Store outputs if successful
            if success and isinstance(result, dict):
                output_templates = db.get_function_output_templates(fn)
                for out_name, out_val in result.items():
                    if out_name in [template[0] for template in output_templates]:
                        val_str = str(out_val)
                        sql_type = infer_sql_type(val_str)
                        db.store_function_output(
                            function_id, fn, out_name, val_str, sql_type, strategy_name
                        )

            return function_id, success, result

        except Exception as e:
            debug.print_error(f"[Parallel] Function {function_id} exception: {e}")
            db.update_function_status(function_id, False, f"Exception: {str(e)}")
            return function_id, False, f"Exception during execution: {str(e)}"

    # Execute all functions in parallel using ThreadPoolExecutor
    debug.print_function(
        f"[Parallel] Executing {len(parallel_batch)} functions concurrently"
    )

    parallel_results = {}
    failed_functions = []
    successful_outputs = {}

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=len(parallel_batch)
    ) as executor:
        # Submit all functions for parallel execution
        future_to_fid = {
            executor.submit(execute_single_function, function_id): function_id
            for function_id in parallel_batch
        }

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_fid):
            function_id = future_to_fid[future]
            try:
                fid_result, success, result = future.result()
                parallel_results[fid_result] = (success, result)

                if success:
                    if isinstance(result, dict):
                        successful_outputs.update(result)
                    debug.print_function(
                        f"[Parallel] Function {fid_result} completed successfully"
                    )
                else:
                    failed_functions.append(fid_result)
                    debug.print_error(
                        f"[Parallel] Function {fid_result} failed: {result}"
                    )

            except Exception as e:
                debug.print_error(
                    f"[Parallel] Function {function_id} generated an exception: {e}"
                )
                failed_functions.append(function_id)
                parallel_results[function_id] = (False, str(e))

    # Store aggregated results in state
    session_state["parallelResults"] = parallel_results

    # Determine overall success - require all functions to succeed
    overall_success = len(failed_functions) == 0
    session_state["functionSuccess"] = overall_success

    # Create aggregated final answer from successful outputs
    if overall_success and successful_outputs:
        # Try to create a meaningful final answer from parallel outputs
        if "Analyze Output" in successful_outputs:
            session_state["finalAnswer"] = successful_outputs["Analyze Output"]
        elif "Table Output" in successful_outputs:
            session_state["finalAnswer"] = (
                f"Data gathered: {str(successful_outputs['Table Output'])[:200]}..."
            )
        else:
            # Combine all outputs
            combined_output = "; ".join(
                [f"{k}: {str(v)[:100]}" for k, v in successful_outputs.items()]
            )
            session_state["finalAnswer"] = (
                f"Parallel execution results: {combined_output}"
            )
    else:
        session_state["finalAnswer"] = (
            f"Parallel execution failed: {len(failed_functions)} of {len(parallel_batch)} functions failed"
        )

    # Set abort flag if any critical function failed
    if failed_functions:
        session_state["strategyAborted"] = True
        debug.print_function(
            f"[Parallel] {len(failed_functions)} functions failed, marking strategy for abort",
            "🚨",
        )

    # Clear the parallel batch since we've executed it
    session_state["parallelBatch"] = None
    session_state["parallelExecutionMode"] = False

    debug.print_function(
        f"[Parallel] Execution complete: {len(parallel_batch) - len(failed_functions)}/{len(parallel_batch)} successful"
    )

    return session_state


# ── Function Validation Node ───────────────────────────────────────


def node_function_validate(session_state: SessionState) -> SessionState:
    """
    Validate that function outputs meet the expected requirements.

    This node performs post-execution validation to ensure function outputs
    are properly formatted and contain the expected data types. It serves as
    a quality gate before proceeding to the next function in the strategy.

    Args:
        state: Session state with currentFunctionID and execution results

    Returns:
        Updated state with validation results and routing flags

    Validation Logic:
    - Checks that required outputs are present and properly formatted
    - Validates data types match expected schema from function library
    - Sets validation flags used by strategy routing logic
    - Updates database with detailed validation results
    """
    function_id = session_state["currentFunctionID"]
    success = session_state.get("functionSuccess", False)

    # Step 1: Get function info and validate it exists
    func_info = db.get_function_info(function_id)
    if not func_info:
        debug.print_error(f"Function {function_id} not found")
        session_state["functionValidated"] = False
        return session_state

    fn = func_info.function_name
    debug.print_validation(f"Validating: {fn}")

    # Step 2: Check actual function status from database rather than just session state
    # Sometimes functionSuccess flag can be incorrect due to state management issues
    db_function_info = db.get_function_info(function_id)
    actual_success = db_function_info and db_function_info.success
    
    # Use database status as authoritative source, fall back to session state
    if actual_success is not None:
        success = actual_success
        session_state["functionSuccess"] = success  # Correct the session state
        
    if not success:
        debug.print_warning(
            f"Function {fn} failed execution, skipping output validation"
        )
        session_state["functionValidated"] = False
        return session_state
    else:
        # Function actually succeeded, continue with validation
        debug.print_validation(f"Function {fn} confirmed successful, proceeding with validation")

    # Step 3: Validate outputs exist and match expected schema
    # Get expected outputs from function library templates
    expected_outputs = db.get_function_output_templates(fn)
    actual_outputs = db.get_function_output_details(function_id)

    validation_errors = []

    # Check that all required outputs are present
    expected_names = {name for name, _ in expected_outputs}
    actual_names = {name for name, _, _ in actual_outputs}

    missing_outputs = expected_names - actual_names
    if missing_outputs:
        validation_errors.append(f"Missing required outputs: {missing_outputs}")

    # Validate output types and content
    for out_name, out_value, out_type in actual_outputs:
        # Basic type validation
        if out_type == "json":
            try:
                json.loads(out_value)
            except json.JSONDecodeError:
                validation_errors.append(
                    f"Output '{out_name}' marked as JSON but not valid JSON"
                )

        # Content validation - ensure outputs have meaningful content
        if not out_value or out_value.strip() == "":
            validation_errors.append(f"Output '{out_name}' is empty")

    # Step 4: Update validation status
    is_valid = len(validation_errors) == 0
    validation_msg = "All outputs valid" if is_valid else "; ".join(validation_errors)

    # Store validation results
    db.update_function_validation(function_id, is_valid, validation_msg)

    if is_valid:
        debug.print_validation(f"{fn} outputs validated successfully", "✅")
    else:
        debug.print_validation(f"{fn} validation failed: {validation_msg}", "❌")

    # Step 5: Set state flags for workflow routing
    session_state["functionValidated"] = is_valid

    # If validation failed, mark strategy for abort
    if not is_valid:
        session_state["strategyAborted"] = True
        debug.print_validation("Validation failed, marking strategy for abort", "🚨")

    return session_state


# ── Strategy Validation Node ───────────────────────────────────────


def node_strategy_validate(session_state: SessionState) -> SessionState:
    """
    Validate strategy progress and implement tri-condition routing logic.

    This is the central coordination node that determines workflow routing based on
    function execution status. It implements intelligent immediate-abort logic to
    prevent wasted computation on failed strategies.

    Routing Conditions:
    1. ANY function failed -> IMMEDIATE ABORT (route to StrategyPlan for new strategy)
    2. ALL functions succeeded -> SUCCESS (route to GoalValidate)
    3. Functions still pending -> CONTINUE (route to FunctionExecute)

    Args:
        state: Session state with currentStrategyID and function execution status

    Returns:
        Updated state with routing flags (strategySatisfied, strategyAborted)

    Business Logic:
    - Prevents continuing with broken strategies (immediate abort on failure)
    - Efficiently routes to goal validation when strategy completes successfully
    - Manages function sequence execution for in-progress strategies
    - Updates database with detailed strategy execution status
    """
    sid = session_state["currentStrategyID"]

    # Step 1: Get comprehensive strategy function statistics
    stats = db.get_strategy_function_statistics(sid)
    total, succeeded, pending, failed = (
        stats["total"],
        stats["succeeded"],
        stats["pending"],
        stats["failed"],
    )

    print(
        f"📊 [StrategyValidate] Strategy {sid}: {succeeded}/{total} succeeded, {pending} pending, {failed} failed"
    )

    # Step 2: Find next pending function to execute (not failed ones)
    next_func_id = db.get_current_function_id(sid)

    # Step 2.5: Check if next function is part of a parallel group
    if next_func_id and session_state.get("parallelGroups"):
        parallel_groups = session_state["parallelGroups"]
        func_info = db.get_function_info(next_func_id)
        if func_info:
            func_name = func_info.function_name

            # Check if this function is the start of a parallel group
            for group in parallel_groups:
                if func_name in group:
                    debug.print_strategy(f"Reached parallel group containing: {group}")
                    # Set up parallel execution for this group
                    function_ids = db.get_strategy_function_ids(sid)
                    parallel_batch = []

                    for function_id, fname in function_ids:
                        if fname in group:
                            parallel_batch.append(function_id)

                    session_state["parallelExecutionMode"] = True
                    session_state["parallelBatch"] = parallel_batch
                    session_state["currentFunctionID"] = (
                        parallel_batch[0] if parallel_batch else None
                    )
                    debug.print_strategy(f"Set up parallel batch: {parallel_batch}")
                    break

    # Step 3: Implement tri-condition routing logic
    # This is the core of the enhanced immediate-abort workflow:

    # CONDITION 1: Any function failed -> IMMEDIATE ABORT
    # No point continuing a failed strategy - try different approach
    if failed > 0:
        outcome = f"Strategy aborted: {failed}/{total} function(s) failed - trying new strategy"
        strategy_success_flag = 0
        strategy_done = True  # Mark strategy as complete (failed)
        next_func_id = None
        session_state["strategyAborted"] = True  # Signal routing to try new strategy
        debug.print_strategy("Strategy aborted due to function failure")

    # CONDITION 2: All functions completed successfully -> SUCCESS
    # Strategy achieved its goal, move to goal validation
    elif pending == 0:
        outcome = "All functions succeeded."
        strategy_success_flag = 1
        strategy_done = True  # Mark strategy as complete (success)
        next_func_id = None
        session_state["strategyAborted"] = False  # Signal routing to validate goal
        debug.print_completion("Strategy completed successfully")

    # CONDITION 3: Functions still pending, no failures yet -> CONTINUE
    # Strategy is making progress, continue with next function in sequence
    else:
        outcome = f"{succeeded}/{total} functions complete. Continuing execution."
        strategy_success_flag = 0
        strategy_done = False  # Strategy still in progress
        session_state["strategyAborted"] = False  # Signal routing to continue execution

        # Safety check: ensure we have a valid next function to execute
        # This should never happen if our logic is correct, but prevents crashes
        if next_func_id is None:
            raise RuntimeError(
                f"Strategy {sid} reports pending functions but none found to execute"
            )

    # Step 4: Update strategy instance with progress using DatabaseManager
    db.update_strategy_status(sid, strategy_success_flag, outcome)

    # Step 5: Set workflow routing flags and update state
    # The tri-condition routing in state_graph.py will use these flags:
    # - strategySatisfied=True + strategyAborted=False -> GoalValidate
    # - strategySatisfied=True + strategyAborted=True  -> StrategyPlan
    # - strategySatisfied=False                        -> FunctionExecute
    session_state["strategySatisfied"] = strategy_done
    if strategy_done:
        if session_state.get("strategyAborted", False):
            debug.print_strategy("Strategy failed, trying new strategy", "🚨")
        else:
            debug.print_strategy("Strategy completed, validating goal", "✅")
    else:
        # Continue with next function in strategy
        session_state["currentFunctionID"] = next_func_id
        # Get function name for better logging
        if next_func_id:
            func_info = db.get_function_info(next_func_id)
            func_name = func_info.function_name if func_info else f"ID-{next_func_id}"
            debug.print_workflow(
                f"Executing next function: {func_name} (ID: {next_func_id})", "➡"
            )
        else:
            debug.print_workflow("No function ID found", "➡")
    return session_state


# ── Goal Validation Node ──────────────────────────────────────────
def node_goal_validate(session_state: SessionState) -> SessionState:
    """
    Validate whether the goal has been satisfied using LLM judge.

    This node performs the final goal validation by:
    1. Collecting all outputs from successful strategies
    2. Using LLM judge to evaluate goal satisfaction
    3. Setting final confidence scores and completion status

    Args:
        state: Session state with currentGoalID set

    Returns:
        Updated state with goalSatisfied flag and confidence score
    """
    import re

    gid = session_state["currentGoalID"]
    query = session_state["query"]

    # Step 1: Get strategy execution status using DatabaseManager
    strategy_stats = db.get_goal_strategy_statistics(gid)

    # Step 2: Wait for all strategies to complete
    if strategy_stats["pending"] > 0:
        session_state["goalSatisfied"] = False
        session_state["judgeConfidence"] = (
            0.0  # No confidence when strategies incomplete
        )
        return session_state

    # Step 3: Check if we should continue trying more strategies
    if strategy_stats["successful"] == 0:
        # No successful strategies yet - check if more are available
        total_strategies = db.count_total_strategies()
        used_strategies = db.count_goal_strategies(gid)

        if used_strategies >= total_strategies:
            # No more strategies to try - goal failed
            session_state["goalSatisfied"] = False
            session_state["judgeConfidence"] = 0.0
            debug.print_error(
                f"All {total_strategies} strategies exhausted, goal failed"
            )
            return session_state
        else:
            # More strategies available - continue trying
            session_state["goalSatisfied"] = False
            session_state["judgeConfidence"] = 0.0
            debug.print_goal(
                f"{used_strategies}/{total_strategies} strategies tried, continuing"
            )
            return session_state

    # Step 4: Enhanced Strategy Stopping Logic
    # At this point we have at least one successful strategy - evaluate if we should stop
    debug.print_goal(
        f"{strategy_stats['successful']} successful strategies, validating goal"
    )

    # Collect only the primary analysis output from each successful strategy.
    # Goal validation should validate the strategy's final analysis output
    # (for example, 'Analyze Output' / 'Analysis Result' / 'analysis')
    primary_outputs = []
    successful_strategies = db.get_successful_strategies(gid)

    for strategy_id in successful_strategies:
        strategy_outputs = db.get_strategy_outputs(strategy_id)
        # strategy_outputs is a list of (name, value) pairs
        chosen = None
        # Prefer explicit analysis keys
        for name, value in strategy_outputs:
            lname = name.lower() if isinstance(name, str) else ""
            if lname in (
                "analyze output",
                "analysis result",
                "analysis",
                "final answer",
            ):
                if value and str(value).strip():
                    chosen = (name, value)
                    break
        # Fallback to first non-empty output
        if not chosen:
            for name, value in strategy_outputs:
                if value and str(value).strip():
                    chosen = (name, value)
                    break
        if chosen:
            primary_outputs.append(chosen)

    # Step 4a: Quick content analysis for strategy stopping
    if primary_outputs:
        output_text = "\n".join([f"{name}: {value}" for name, value in primary_outputs])

        # Enhanced stopping criteria: Check if we have a substantive answer
        has_specific_answer = False
        output_lower = output_text.lower()

        # General content quality checks
        has_technical_content = False

        # Check for meaningful technical content (non-specific patterns)
        content_indicators = len(
            [word for word in output_lower.split() if len(word) > 3]
        )
        has_numbers_or_codes = bool(re.search(r"[0-9-/]+", output_text))
        has_technical_terms = bool(
            re.search(r"[A-Z]{2,}|#\d+|specification|tool|connector|size", output_text)
        )

        # Evaluate content quality
        if content_indicators > 10 and (has_numbers_or_codes or has_technical_terms):
            # Check if it's a negative answer
            if not (
                ("not" in output_lower or "unable" in output_lower)
                and ("find" in output_lower or "specified" in output_lower)
            ):
                has_specific_answer = True

        # If we have a substantive answer from the first strategy, consider stopping
        # unless the user explicitly wants comprehensive analysis
        total_strategies = db.count_total_strategies()
        used_strategies = db.count_goal_strategies(gid)

        if (
            has_specific_answer
            and used_strategies == 1
            and "all" not in query.lower()
            and "compare" not in query.lower()
        ):
            debug.print_goal(
                "First strategy provided substantive answer - proceeding to validation"
            )
            # Continue to LLM validation but with lower threshold for stopping

    # Step 4b: Goal validation with LLM judge
    # Rebuild primary_outputs (ensure we use the same selection logic)
    primary_outputs = []
    successful_strategies = db.get_successful_strategies(gid)

    for strategy_id in successful_strategies:
        strategy_outputs = db.get_strategy_outputs(strategy_id)
        chosen = None
        for name, value in strategy_outputs:
            lname = name.lower() if isinstance(name, str) else ""
            if lname in (
                "analyze output",
                "analysis result",
                "analysis",
                "final answer",
            ):
                if value and str(value).strip():
                    chosen = (name, value)
                    break
        if not chosen:
            for name, value in strategy_outputs:
                if value and str(value).strip():
                    chosen = (name, value)
                    break
        if chosen:
            primary_outputs.append(chosen)

    # Use LLM judge to validate goal satisfaction using primary analysis outputs
    if primary_outputs:
        # Log which primary outputs were selected for validation (name and truncated value)
        try:
            selected_preview = [
                f"{name}: {str(value)[:200]}" for name, value in primary_outputs
            ]
            debug.print_validation(
                f"Primary outputs selected for goal validation: {selected_preview}",
                "🔎",
            )
        except Exception:
            debug.print_validation(
                "Primary outputs selected for goal validation: [unavailable]", "🔎"
            )

        # Combine primary outputs for LLM evaluation
        output_text = "\n".join([f"{name}: {value}" for name, value in primary_outputs])

        # Get goal definition for enhanced validation
        goal_info = db.get_goal_info(gid)
        goal_definition = ""
        if goal_info and hasattr(goal_info, "description"):
            # Try to extract goal definition if stored (simple fallback for now)
            goal_definition = f"Goal: {goal_info.description}"
        else:
            goal_definition = "General technical query validation"

        # LLM judge prompt
        prompt_loader = get_prompt_loader()
        prompt = prompt_loader.format_prompt(
            "goal_validation",
            query=query,
            goal_definition=goal_definition,
            full_evidence=output_text,
        )

        from logic.llm_helpers import invoke_llm_with_retry
        
        llm = get_reasoning_llm()
        response = invoke_llm_with_retry(
            llm,
            [
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ],
            max_retries=3,
            base_delay=2.0
        )

        # Parse confidence and satisfaction from JSON response
        try:
            import json
            import re

            # Clean the response content to extract JSON
            response_text = response.content.strip()
            debug.print_validation(f"LLM Response: {response_text[:200]}...", "🔍")
            debug.print_validation(
                f"Response length: {len(response_text)}, type: {type(response_text)}",
                "🔍",
            )

            # Check for empty response
            if not response_text:
                debug.print_validation(
                    "Empty LLM response, using fallback confidence", "🔸"
                )
                confidence = 0.1  # Low confidence for empty response
                satisfied = False
            else:
                # Initialize with fallback values
                confidence = 0.1
                satisfied = False

                # Method 1: Extract JSON from markdown code blocks
                json_match = re.search(
                    r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL
                )
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                        confidence = float(result.get("confidence", 0.0))
                        satisfied = confidence >= 0.5
                        debug.print_validation(
                            f"Markdown JSON parse - confidence: {confidence}", "�"
                        )
                    except Exception as e:
                        debug.print_validation(
                            f"Failed to parse markdown JSON: {e}", "🔸"
                        )

                # Method 2: Direct JSON parsing if no markdown blocks found
                if confidence == 0.1:  # Still at fallback value
                    try:
                        # Try to find JSON object in response
                        json_start = response_text.find("{")
                        json_end = response_text.rfind("}") + 1

                        if json_start >= 0 and json_end > json_start:
                            json_text = response_text[json_start:json_end]

                            # Simplified and safer JSON cleaning approach
                            import re

                            debug.print_validation(
                                f"Original JSON: {repr(json_text)}", "🔧"
                            )

                            # Since we only need confidence value, use direct extraction
                            # This avoids all the complex quote-handling issues

                            # Step 1: Extract confidence value using regex (safest approach)
                            confidence_match = re.search(
                                r'"?confidence"?\s*:\s*([0-9]*\.?[0-9]+)',
                                json_text.lower(),
                            )

                            if confidence_match:
                                conf_value = confidence_match.group(1)
                                # Construct clean JSON with just confidence
                                json_text = f'{{"confidence": {conf_value}}}'
                                debug.print_validation(
                                    f"Extracted and cleaned JSON: {json_text}", "🔧"
                                )
                            else:
                                # Try alternative patterns for malformed JSON
                                conf_match_alt = re.search(
                                    r"confidence[:\s]*([0-9]*\.?[0-9]+)",
                                    json_text.lower(),
                                )
                                if conf_match_alt:
                                    conf_value = conf_match_alt.group(1)
                                    json_text = f'{{"confidence": {conf_value}}}'
                                    debug.print_validation(
                                        f"Alternative extraction: {json_text}", "🔧"
                                    )
                                else:
                                    # No confidence found, use fallback
                                    json_text = '{"confidence": 0.1}'
                                    debug.print_validation(
                                        "No confidence found, using fallback", "🔧"
                                    )

                            result = json.loads(json_text)
                            confidence = float(result.get("confidence", 0.0))
                            satisfied = confidence >= 0.5
                            debug.print_validation(
                                f"Direct JSON parse - confidence: {confidence}", "📊"
                            )
                    except json.JSONDecodeError as je:
                        debug.print_validation(f"JSON decode error: {je}", "🔸")
                        debug.print_validation(
                            f"Error position: line {je.lineno}, column {je.colno}", "🔸"
                        )
                        debug.print_validation(f"Error message: {je.msg}", "🔸")
                        debug.print_validation(
                            f"Problematic JSON (full): {repr(json_text)}", "🔧"
                        )
                        debug.print_validation(
                            f"Problematic JSON (first 300 chars): {json_text[:300]}...",
                            "🔧",
                        )

                        # Show the specific problematic area around the error
                        if hasattr(je, "pos") and je.pos is not None:
                            start_pos = max(0, je.pos - 50)
                            end_pos = min(len(json_text), je.pos + 50)
                            debug.print_validation(
                                f"JSON around error position {je.pos}: {repr(json_text[start_pos:end_pos])}",
                                "🔧",
                            )

                        # Try multiple fallback approaches for severely malformed JSON
                        confidence_extracted = False

                        # Fallback 1: Extract confidence value from malformed JSON
                        try:
                            conf_match = re.search(
                                r'"confidence":\s*([0-9.]+)', json_text
                            )
                            if conf_match:
                                confidence = float(conf_match.group(1))
                                satisfied = confidence >= 0.5
                                confidence_extracted = True
                                debug.print_validation(
                                    f"Extracted confidence from malformed JSON: {confidence}",
                                    "📊",
                                )
                        except Exception:
                            pass

                        # Fallback 2: Try to construct minimal valid JSON
                        if not confidence_extracted:
                            try:
                                # Extract confidence value
                                conf_match = re.search(
                                    r'"confidence":\s*([0-9.]+)', response_text
                                )
                                conf_val = conf_match.group(1) if conf_match else "0.1"

                                # Extract satisfied value if present
                                sat_match = re.search(
                                    r'"satisfied":\s*(true|false)',
                                    response_text.lower(),
                                )
                                sat_val = sat_match.group(1) if sat_match else "false"

                                # Construct minimal valid JSON
                                minimal_json = f'{{"confidence": {conf_val}, "satisfied": {sat_val}}}'
                                result = json.loads(minimal_json)
                                confidence = float(result.get("confidence", 0.0))
                                satisfied = result.get("satisfied", False)
                                debug.print_validation(
                                    f"Reconstructed JSON - confidence: {confidence}",
                                    "📊",
                                )
                            except Exception as e2:
                                debug.print_validation(
                                    f"JSON reconstruction failed: {e2}", "🔸"
                                )

                        # Fallback 3: Try extracting from original response text
                        if confidence == 0.1:
                            try:
                                conf_match = re.search(
                                    r'"confidence":\s*([0-9.]+)', response_text
                                )
                                if conf_match:
                                    confidence = float(conf_match.group(1))
                                    satisfied = confidence >= 0.5
                                    debug.print_validation(
                                        f"Extracted confidence from original response: {confidence}",
                                        "📊",
                                    )
                            except Exception:
                                pass
                    except Exception as e:
                        debug.print_validation(f"Direct JSON parsing failed: {e}", "🔸")

                # Method 3: Regex extraction of confidence value
                if confidence == 0.1:  # Still at fallback value
                    try:
                        conf_match = re.search(
                            r'"confidence":\s*([0-9.]+)', response_text
                        )
                        if conf_match:
                            confidence = float(conf_match.group(1))
                            satisfied = confidence >= 0.5
                            debug.print_validation(
                                f"Regex confidence extraction: {confidence}", "📊"
                            )
                    except Exception as e:
                        debug.print_validation(f"Regex extraction failed: {e}", "🔸")

                # Method 4: Fallback to content analysis
                if confidence == 0.1:  # Still at fallback value
                    # Analyze response content for positive indicators
                    positive_indicators = [
                        "yes",
                        "satisfied",
                        "complete",
                        "success",
                        "found",
                    ]
                    negative_indicators = [
                        "no",
                        "unsatisfied",
                        "incomplete",
                        "failed",
                        "not found",
                    ]

                    response_lower = response_text.lower()
                    positive_count = sum(
                        1
                        for indicator in positive_indicators
                        if indicator in response_lower
                    )
                    negative_count = sum(
                        1
                        for indicator in negative_indicators
                        if indicator in response_lower
                    )

                    if positive_count > negative_count:
                        confidence = 0.6
                        satisfied = True
                        debug.print_validation(
                            f"Content analysis: positive ({positive_count} vs {negative_count})",
                            "📊",
                        )
                    else:
                        confidence = 0.2
                        satisfied = False
                        debug.print_validation(
                            f"Content analysis: negative ({positive_count} vs {negative_count})",
                            "📊",
                        )

        except Exception as overall_error:
            # Ultimate fallback for any parsing errors
            debug.print_validation(
                f"Goal validation completely failed: {overall_error}", "❌"
            )
            confidence = 0.1
            satisfied = False

        # ── Enhanced Strategy Stopping Logic ──────────────────────────────────
        # Determine if we should continue with more strategies based on:
        # 1. Confidence level
        # 2. Technical content quality
        # 3. Available strategies
        # 4. Query complexity indicators

        used_strategies = db.count_goal_strategies(gid)
        total_strategies = db.count_total_strategies()
        has_more_strategies = used_strategies < total_strategies

        # Get primary outputs again for content quality analysis
        primary_outputs = []
        successful_strategies = db.get_successful_strategies(gid)
        for strategy_id in successful_strategies:
            strategy_outputs = db.get_strategy_outputs(strategy_id)
            chosen = None
            for name, value in strategy_outputs:
                lname = name.lower() if isinstance(name, str) else ""
                if lname in (
                    "analyze output",
                    "analysis result",
                    "analysis",
                    "final answer",
                ):
                    if value and str(value).strip():
                        chosen = (name, value)
                        break
            if not chosen:
                for name, value in strategy_outputs:
                    if value and str(value).strip():
                        chosen = (name, value)
                        break
            if chosen:
                primary_outputs.append(chosen)

        output_text = "\n".join([f"{name}: {value}" for name, value in primary_outputs])
        output_lower = output_text.lower()

        # General content quality assessment
        content_length = len(output_text.strip())
        word_count = len([word for word in output_lower.split() if len(word) > 2])
        has_technical_patterns = bool(
            re.search(r"[A-Z]{2,}|#\d+|\d+[A-Za-z]+|[a-z]+\d+", output_text)
        )
        has_measurements = bool(
            re.search(r"\d+\.?\d*\s*(mm|awg|v|a|ohm|mhz|khz)", output_lower)
        )

        # General content quality indicators
        has_substantive_content = (
            content_length > 50
            and word_count > 8
            and (has_technical_patterns or has_measurements)
        )

        # Check for negative/incomplete answers
        has_negative_answer = (
            "not" in output_lower
            or "unable" in output_lower
            or "cannot" in output_lower
        ) and (
            "find" in output_lower
            or "specified" in output_lower
            or "determined" in output_lower
        )

        # Determine satisfaction with enhanced strategy stopping criteria
        if confidence >= 0.8:
            # Very high confidence - always satisfied
            satisfied = True
            debug.print_validation(
                f"Very high confidence: {confidence} - stopping strategies", "✅"
            )

        elif confidence >= 0.4 and has_substantive_content and not has_negative_answer:
            # Medium confidence with substantive content - be more lenient
            if used_strategies >= 1:
                satisfied = True
                debug.print_validation(
                    f"Medium confidence + substantive content: {confidence} - stopping strategies",
                    "✅",
                )
            else:
                satisfied = False

        elif confidence >= 0.3 and has_substantive_content and not has_more_strategies:
            # Lower confidence but substantive content and no more strategies available
            satisfied = True
            debug.print_validation(
                f"Lower confidence but exhausted strategies with substantive content: {confidence}",
                "✅",
            )

        elif has_negative_answer and has_more_strategies and used_strategies == 1:
            # First strategy gave negative answer - try enhanced lookup
            satisfied = False
            debug.print_validation(
                f"Negative answer from first strategy - trying more: {confidence}", "🔄"
            )

        elif not has_more_strategies:
            # No more strategies available - must accept result
            satisfied = True
            debug.print_validation(
                f"No more strategies available - accepting: {confidence}", "✅"
            )

        else:
            # Default: unsatisfied if confidence is low and more strategies available
            satisfied = (
                confidence >= 0.5
            )  # Lowered from 0.7 to 0.5 for better success rate
            if not satisfied and has_more_strategies:
                debug.print_validation(
                    f"Low confidence, trying more strategies: {confidence}", "🔄"
                )

        session_state["goalSatisfied"] = satisfied
        session_state["judgeConfidence"] = confidence

        if satisfied:
            debug.print_validation(f"Goal satisfied with confidence {confidence}", "✅")
        else:
            debug.print_validation(
                f"Goal not satisfied (confidence {confidence})", "🤔"
            )
    else:
        # No outputs to validate
        session_state["goalSatisfied"] = False
        session_state["judgeConfidence"] = 0.0
        debug.print_validation("No outputs to validate", "❌")

    return session_state


# ── Terminal Node - Workflow Completion ──────────────────────────────────────
def node_done(session_state: SessionState) -> SessionState:
    """
    Terminal node - End of workflow execution.

    This is the final node in the LangGraph workflow, reached after goal validation
    is complete. It serves as the official termination point for successful workflows
    where all goals have been satisfied or validation has been completed.

    Args:
        state: Current session state containing complete workflow context and results

    Returns:
        SessionState: Unmodified state dict - workflow is complete

    Business Logic:
        - Confirms successful completion of the multi-agent workflow
        - Serves as terminal node for LangGraph execution engine
        - No state modifications needed - all work is done
        - System is ready for potential future sessions

    Note:
        This node is reached only when goal validation indicates success.
        Failed validations typically don't route here, ending at goal_validate instead.
    """
    debug.print_completion("All work completed successfully", "🎉")
    return session_state
