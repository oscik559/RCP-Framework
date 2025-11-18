#!/usr/bin/env python3
"""
Simple test script to verify the CONTEXTUAL PRODUCT SEARCH strategy with real queries.
"""

import sys
import os

if sys.platform.startswith("win"):
    os.environ["PYTHONIOENCODING"] = "utf-8"

from Layer_2_Agentic.config.constants import ANSWER_FIELDS
from Layer_2_Agentic.config.session_config import (
    get_default_session_state,
    get_workflow_config,
)
from Layer_2_Agentic.logic.state_graph import get_graph
from Layer_2_Agentic.logic.templates import populate_template_libraries
from Layer_2_Agentic.config import debug_config


def test_strategy(query: str):
    """Test the strategy with a single query."""
    try:
        debug_config.set_debug_level(2)  # NORMAL debug level
        
        # Initialize session
        init_state = get_default_session_state(query=query)
        workflow_config = get_workflow_config()

        # Header
        print("[AI] Testing CONTEXTUAL PRODUCT SEARCH Strategy")
        print("=" * 70)
        print("Query: " + query)
        print("Session: " + str(init_state.get('sessionID', 'unknown')))
        print("=" * 70)

        # Setup
        print("[SETUP] Initializing libraries...")
        populate_template_libraries()
        
        print("[SETUP] Clearing old session data...")
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
                raise AttributeError("StateGraph object has no callable invoke/run/execute/start methods")

        # Results
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)

        debug_fields = {
            "parallelExecutionMode",
            "parallelBatch",
            "parallelResults",
            "parallelGroups",
        }

        for key, value in final_state.items():
            if key not in debug_fields:
                label = ANSWER_FIELDS.get(key, key)
                print(label + ": " + str(value))

        print("\n[SUCCESS] Completed successfully!")
        return True

    except Exception as e:
        print("\n[ERROR] Error: " + str(e))
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Test queries from the question database
    test_queries = [
        # High-confidence semantic search queries
        "What hoses can be used for boiling water?",
        "Which hydraulic hoses are rated for more than 300 bar working pressure?",
        "Which products are approved for food use?",
        
        # Mid-confidence queries
        "What hoses can be used for chemicals?",
        
        # Product lookup
        "What is the maximum temperature for hose 1071-00-16?",
    ]
    
    print("\n" + "[TEST]" * 10)
    print("STRATEGY TESTING - CONTEXTUAL PRODUCT SEARCH")
    print("[TEST]" * 10 + "\n")
    
    results = []
    for i, query in enumerate(test_queries[:2], 1):  # Test first 2 queries
        print("\n" + "=" * 70)
        print("TEST " + str(i) + "/" + str(min(2, len(test_queries))))
        print("=" * 70 + "\n")
        
        success = test_strategy(query)
        results.append((query, success))
        
        print("\n" + "-" * 70)
        print("Press Enter to continue to next query...")
        try:
            input()
        except:
            pass
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    for query, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(status + " - " + query)
    
    print("\nPassed: " + str(sum(1 for _, s in results if s)) + "/" + str(len(results)))
