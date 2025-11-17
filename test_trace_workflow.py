#!/usr/bin/env python3
"""
Comprehensive workflow trace: Inspect all agentic database tables
to understand data flow through the DIRECT_SPEC_LOOKUP strategy
"""

import sqlite3
import json
from pathlib import Path

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_subsection(title):
    print(f"\n{title}")
    print("-" * 80)

def format_json(data):
    """Pretty print JSON data"""
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except:
            return data
    return json.dumps(data, indent=2, ensure_ascii=False)

def query_agentic_db(query):
    """Execute query on agentic.db"""
    conn = sqlite3.connect("Layer_2_Agentic/db/agentic.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

# ============================================================================
# PART 1: STRATEGY DEFINITION
# ============================================================================
print_section("PART 1: DIRECT_SPEC_LOOKUP STRATEGY DEFINITION")

strategies = query_agentic_db("""
    SELECT StrategyID, StrategyName, StrategyTarget, StrategyDescription, PlanSteps
    FROM StrategyLibrary
    WHERE StrategyName = 'DIRECT SPECIFICATION LOOKUP'
""")

for strat in strategies:
    print(f"\nStrategy ID: {strat['StrategyID']}")
    print(f"Name: {strat['StrategyName']}")
    print(f"Target: {strat['StrategyTarget']}")
    print(f"Description: {strat['StrategyDescription']}")
    print(f"\nPlan Steps:")
    steps = [s.strip() for s in strat['PlanSteps'].split(',')]
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")

# ============================================================================
# PART 2: FUNCTION TEMPLATES
# ============================================================================
print_section("PART 2: FUNCTION TEMPLATES (from templates.py)")

function_names = [
    "Extract Product Number",
    "Query Database",
    "Extract Attributes",
    "Analyze With LLM"
]

for fname in function_names:
    functions = query_agentic_db(f"""
        SELECT FunctionTemplateID, FunctionName, StrategyType, FunctionDescription
        FROM FunctionTemplateLibrary
        WHERE FunctionName = '{fname}'
    """)
    
    if functions:
        func = functions[0]
        print_subsection(f"Function: {fname}")
        print(f"ID: {func['FunctionTemplateID']}")
        print(f"Type: {func['StrategyType']}")
        print(f"Description: {func['FunctionDescription']}")

# ============================================================================
# PART 3: FUNCTION PARAMETERS (Inputs)
# ============================================================================
print_section("PART 3: FUNCTION PARAMETER DEFINITIONS (Expected Inputs)")

for fname in function_names:
    functions = query_agentic_db(f"""
        SELECT FunctionTemplateID
        FROM FunctionTemplateLibrary
        WHERE FunctionName = '{fname}'
    """)
    
    if functions:
        func_id = functions[0]['FunctionTemplateID']
        params = query_agentic_db(f"""
            SELECT ParameterName, ParameterValue, Type
            FROM FunctionParametersLibrary
            WHERE FunctionTemplateID = {func_id}
            ORDER BY rowid
        """)
        
        print_subsection(f"{fname} - Input Parameters")
        if params:
            for param in params:
                print(f"  • {param['ParameterName']:<30} = '{param['ParameterValue']:<20}' ({param['Type']})")
        else:
            print("  (No parameters defined)")

# ============================================================================
# PART 4: FUNCTION OUTPUTS (Expected Outputs)
# ============================================================================
print_section("PART 4: FUNCTION OUTPUT DEFINITIONS (Expected Outputs)")

for fname in function_names:
    functions = query_agentic_db(f"""
        SELECT FunctionTemplateID
        FROM FunctionTemplateLibrary
        WHERE FunctionName = '{fname}'
    """)
    
    if functions:
        func_id = functions[0]['FunctionTemplateID']
        outputs = query_agentic_db(f"""
            SELECT OutputName, OutputValue, Type
            FROM FunctionOutputLibrary
            WHERE FunctionTemplateID = {func_id}
            ORDER BY rowid
        """)
        
        print_subsection(f"{fname} - Output Fields")
        if outputs:
            for output in outputs:
                print(f"  • {output['OutputName']:<30} = '{output['OutputValue']:<20}' ({output['Type']})")
        else:
            print("  (No outputs defined)")

# ============================================================================
# PART 5: SESSION EXECUTION DATA
# ============================================================================
print_section("PART 5: SESSION EXECUTION DATA (Latest Session)")

# Get latest session
sessions = query_agentic_db("""
    SELECT DISTINCT SessionID
    FROM GoalInSession
    ORDER BY SessionID DESC
    LIMIT 1
""")

if sessions:
    session_id = sessions[0]['SessionID']
    print(f"\nLatest Session ID: {session_id}")
    
    # ---- Goals ----
    print_subsection("Goals in Session")
    goals = query_agentic_db(f"""
        SELECT GoalID, GoalText, GoalType
        FROM GoalInSession
        WHERE SessionID = {session_id}
    """)
    for goal in goals:
        print(f"  Goal {goal['GoalID']}: {goal['GoalText']} (Type: {goal['GoalType']})")
    
    # ---- Strategy ----
    print_subsection("Strategy Selected")
    strategies_used = query_agentic_db(f"""
        SELECT StrategyID, StrategyName, Status
        FROM StrategyInSession
        WHERE SessionID = {session_id}
    """)
    for strat in strategies_used:
        print(f"  Strategy {strat['StrategyID']}: {strat['StrategyName']} (Status: {strat['Status']})")
    
    # ---- Functions Executed ----
    print_subsection("Functions Executed (In Order)")
    functions_executed = query_agentic_db(f"""
        SELECT 
            FunctionID,
            FunctionName,
            Status,
            ExecutionOrder
        FROM FunctionInSession
        WHERE SessionID = {session_id}
        ORDER BY ExecutionOrder ASC
    """)
    
    for func in functions_executed:
        print(f"\n  [{func['ExecutionOrder']}] {func['FunctionName']} (ID: {func['FunctionID']}, Status: {func['Status']})")
        
        # Get parameters for this function execution
        func_params = query_agentic_db(f"""
            SELECT ParameterName, ParameterValue
            FROM FunctionParametersInSession
            WHERE FunctionID = {func['FunctionID']} AND SessionID = {session_id}
            ORDER BY rowid
        """)
        
        if func_params:
            print(f"      Inputs:")
            for param in func_params:
                value_display = param['ParameterValue']
                if len(value_display) > 100:
                    value_display = value_display[:100] + "..."
                print(f"        • {param['ParameterName']:<25} = {value_display}")
        
        # Get outputs for this function execution
        func_outputs = query_agentic_db(f"""
            SELECT OutputName, OutputValue
            FROM FunctionOutputInSession
            WHERE FunctionID = {func['FunctionID']} AND SessionID = {session_id}
            ORDER BY rowid
        """)
        
        if func_outputs:
            print(f"      Outputs:")
            for output in func_outputs:
                value_display = output['OutputValue']
                if len(value_display) > 100:
                    value_display = value_display[:100] + "..."
                print(f"        • {output['OutputName']:<25} = {value_display}")

# ============================================================================
# PART 6: DATA FLOW VALIDATION
# ============================================================================
print_section("PART 6: DATA FLOW VALIDATION")

if sessions and functions_executed:
    session_id = sessions[0]['SessionID']
    
    print("\nValidating output → input connections:")
    
    # Build function sequence
    for i in range(len(functions_executed) - 1):
        current_func = functions_executed[i]
        next_func = functions_executed[i + 1]
        
        print(f"\n  {current_func['FunctionName']} → {next_func['FunctionName']}")
        
        # Get outputs from current function
        current_outputs = query_agentic_db(f"""
            SELECT OutputName, OutputValue
            FROM FunctionOutputInSession
            WHERE FunctionID = {current_func['FunctionID']} AND SessionID = {session_id}
        """)
        
        # Get inputs to next function
        next_inputs = query_agentic_db(f"""
            SELECT ParameterName, ParameterValue
            FROM FunctionParametersInSession
            WHERE FunctionID = {next_func['FunctionID']} AND SessionID = {session_id}
        """)
        
        # Look for matching fields
        output_names = {out['OutputName'] for out in current_outputs}
        input_names = {inp['ParameterName'] for inp in next_inputs}
        
        # Check for common naming patterns
        matches = output_names & input_names
        if matches:
            print(f"    ✓ Direct field match: {matches}")
        else:
            print(f"    ⚠ No direct field match")
            print(f"      Available outputs: {output_names}")
            print(f"      Expected inputs: {input_names}")

print("\n" + "=" * 80)
print("  END OF TRACE")
print("=" * 80 + "\n")
