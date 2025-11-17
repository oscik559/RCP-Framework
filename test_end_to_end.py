#!/usr/bin/env python3
"""End-to-end test: Query through the full Layer 2 system"""

import sys
import os
from pathlib import Path

# Setup path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from Layer_2_Agentic.config.domain_config import initialize_domain_config
from Layer_2_Agentic.orchestration.workflow_state import WorkflowSystem

print("=" * 70)
print("END-TO-END SYSTEM TEST")
print("=" * 70)
print()

# ========== Initialize System ==========
print("STEP 1: Initialize Domain Configuration")
print("-" * 70)

try:
    config = initialize_domain_config(debug_level=2)
    print("✓ Domain configuration initialized")
    print(f"  - Tables: {list(config['tables'].keys())}")
    print(f"  - Functions: {len(config['functions'])} functions available")
    print()
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# ========== Initialize Workflow System ==========
print("STEP 2: Initialize Workflow System")
print("-" * 70)

try:
    workflow_system = WorkflowSystem(config, session_id="test_session")
    print("✓ Workflow system initialized")
    print(f"  - Session ID: test_session")
    print()
except Exception as e:
    print(f"❌ Workflow initialization failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# ========== Process Query ==========
print("STEP 3: Process Query Through System")
print("-" * 70)

query = "What is the Slang ID for the product 4221-24-08?"
print(f"Query: {query}")
print()

try:
    # Process the query through the workflow
    result = workflow_system.process_query(query)
    
    print("✓ Query processed")
    print()
    print("RESULT:")
    print("-" * 70)
    print(result)
    print()
    print("=" * 70)
    print("✅ END-TO-END TEST COMPLETE!")
    print("=" * 70)
    
except Exception as e:
    print(f"❌ Query processing failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
