#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generic Agentic Reasoning System - Main Entry Point

Primary entry point for the agentic reasoning system.
Processes user queries through the multi-agent pipeline using a
hierarchical Goal → Strategy → Function workflow.

Usage:
    python main.py
"""

import sys
import os

# Add Layer_2-Agentic to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Layer_2-Agentic'))

# Ensure UTF-8 encoding for Windows
if sys.platform.startswith("win"):
    os.environ["PYTHONIOENCODING"] = "utf-8"

from config.constants import ANSWER_FIELDS
from config.session_config import (
    get_default_session_state,
    get_workflow_config,
)
from logic.state_graph import get_graph
from logic.templates import populate_template_libraries


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
        from config.debug_config import set_debug_level

        set_debug_level(0)  # Change this to adjust verbosity

        # =================================================================
        # QUERY SELECTION - Configure your query here
        # =================================================================
        # Example queries (domain-specific examples should be configured per application):
        user_query = "What products are available in the Hydroscand catalog?"
        
        # For testing, you can uncomment and modify these:
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

        # Execute
        print("\n[AI] Running workflow...\n")
        final_state = get_graph().invoke(init_state, config=workflow_config)

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
