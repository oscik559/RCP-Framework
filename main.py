#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generic Agentic Reasoning System - Main Entry Point

Primary entry point for the agentic reasoning system.
Processes user queries through the multi-agent pipeline using a
hierarchical Goal → Strategy → Function workflow.

Usage:
    python main.py

Note:
    Package should be installed with: pip install -e .
    This enables clean imports without sys.path manipulation.
"""

import sys
import os

from sympy import product

# Ensure UTF-8 encoding for Windows
if sys.platform.startswith("win"):
    os.environ["PYTHONIOENCODING"] = "utf-8"

from Layer_2_Agentic.config.constants import ANSWER_FIELDS
from Layer_2_Agentic.config.session_config import (
    get_default_session_state,
    get_workflow_config,
)
from Layer_2_Agentic.logic.state_graph import get_graph
from Layer_2_Agentic.db.templates import populate_template_libraries


def main():
    """
    Execute agentic reasoning workflow.

    Processes user query through goal -> strategy -> function pipeline.
    Returns 0 on success, 1 on error.
    """
    try:
        # =================================================================
        # DEBUG CONFIGURATION
        # =================================================================
        # Set debug level:
        #   0 = SILENT     - No debug output
        #   1 = MINIMAL    - Only major workflow steps
        #   2 = NORMAL     - Standard progress indicators (recommended)
        #   3 = DETAILED   - Include function parameters and outputs
        #   4 = VERBOSE    - All debug information including merging details
        # Can also be set via environment variable: DEBUG_LEVEL
        from Layer_2_Agentic.config import debug_config

        debug_config.set_debug_level(0)  # Change this to adjust verbosity

        # =================================================================
        # QUERY SELECTION - Configure your query here
        # =================================================================
        # Example queries (domain-specific examples should be configured per application):
        user_query = "What do you know about the product 1110-00-06?"
        
        # For testing, you can uncomment and modify these:
        # user_query = "What is the Slang ID for the product 4221-24-08?"
        # user_query = "What is the working pressure of a 4201-16-16?"
        # user_query = "What is the maximum working pressure for this hose KAPPAFLEX 1 at 100 °C?"
        # user_query = "What products are available in the Hydroscand catalog?"
        # user_query = "Find product by code 1103-03-04"
        # user_query = "Compare different hose products"
        # user_query = "What are the specifications of product family 1103?"



        # Initialize session
        init_state = get_default_session_state(query=user_query)
        workflow_config = get_workflow_config()

        # Header
        print("[🤖] Generic Agentic Reasoning System")
        print("=" * 60)
        print(f"Query: {init_state['query']}")
        print(f"Session: {init_state['sessionID']}")
        print("=" * 60)

        # Setup
        print("[SETUP] Initializing libraries...")
        populate_template_libraries()
        
        # Clear any old session data to ensure fresh start
        print(f"[SETUP] Clearing all old session data...")
        from Layer_2_Agentic.logic.database_manager import DatabaseManager
        db = DatabaseManager()
        db.clear_all_sessions()

        # Execute
        print("\n[AI] Running workflow...\n")
        from typing import Any
        graph: Any = get_graph()
        if hasattr(graph, "invoke"):
            final_state = graph.invoke(init_state, config=workflow_config)
        else:
            for method_name in ("run", "execute", "start", "process"):
                if hasattr(graph, method_name):
                    final_state = getattr(graph, method_name)(init_state, config=workflow_config)
                    break
            else:
                raise AttributeError("StateGraph object has no callable 'invoke', 'run', 'execute' or 'start' methods")

        # Results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)

        # Clean debug fields from results display
        debug_fields = {
            "parallelExecutionMode",
            "parallelBatch",
            "parallelResults",
            "parallelGroups",
        }

        for key, value in final_state.items():
            if key not in debug_fields:  # Skip debug fields
                label = ANSWER_FIELDS.get(key, key)
                print(f"{label}: {value}")

        print("\n[SUCCESS] Completed successfully!")
        return 0

    except KeyboardInterrupt:
        print("\n[WARNING] Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
