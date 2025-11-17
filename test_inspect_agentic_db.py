#!/usr/bin/env python3
"""
Deep inspection of agentic database after last execution
Shows what was actually stored in the workflow tables
"""

import sqlite3
import json
from pathlib import Path

def print_section(title):
    print("\n" + "=" * 90)
    print(f"  {title}")
    print("=" * 90)

def print_subsection(title):
    print(f"\n{title}")
    print("-" * 90)

def query_db(db_path, sql):
    """Execute query on database"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        conn.close()
        return [dict(row) for row in results]
    except Exception as e:
        print(f"❌ Error querying {db_path}: {e}")
        return []

def truncate_value(val, max_len=80):
    """Truncate long values for display"""
    val_str = str(val)
    if len(val_str) > max_len:
        return val_str[:max_len-3] + "..."
    return val_str

agentic_db = "database/agentic.db"

# Check if database exists
if not Path(agentic_db).exists():
    print(f"❌ Database not found: {agentic_db}")
    print("Run main.py first to generate execution data")
    exit(1)

print_section("AGENTIC DATABASE INSPECTION - WORKFLOW EXECUTION TRACE")

# Get latest session
sessions = query_db(agentic_db, """
    SELECT DISTINCT SessionID FROM GoalInSession 
    ORDER BY SessionID DESC LIMIT 1
""")

if not sessions:
    print("❌ No sessions found in database")
    exit(1)

session_id = sessions[0]['SessionID']
print(f"\nLatest Session ID: {session_id}")

# 1. Goals
print_subsection("1. GOALS IN SESSION")
goals = query_db(agentic_db, f"""
    SELECT GoalID, GoalName, GoalTarget, GoalSuccess
    FROM GoalInSession
    WHERE SessionID = {session_id}
""")
for goal in goals:
    print(f"Goal {goal['GoalID']}: {goal['GoalName']}")
    print(f"  Target: {goal['GoalTarget']}, Success: {goal['GoalSuccess']}")

# 2. Strategies
print_subsection("2. STRATEGIES SELECTED")
strategies = query_db(agentic_db, f"""
    SELECT StrategyID, StrategyName, StrategySuccess
    FROM StrategyInSession
    WHERE GoalID IN (SELECT GoalID FROM GoalInSession WHERE SessionID = {session_id})
""")
for strat in strategies:
    print(f"Strategy {strat['StrategyID']}: {strat['StrategyName']}")
    print(f"  Success: {strat['StrategySuccess']}")

# 3. Functions
print_subsection("3. FUNCTIONS EXECUTED (IN SEQUENCE)")

# Get all strategy IDs for this session
strategy_ids = query_db(agentic_db, f"""
    SELECT StrategyID FROM StrategyInSession
    WHERE GoalID IN (SELECT GoalID FROM GoalInSession WHERE SessionID = {session_id})
""")

strategy_id_list = [s['StrategyID'] for s in strategy_ids]

if strategy_id_list:
    functions = query_db(agentic_db, f"""
        SELECT FunctionID, FunctionName, FunctionSuccess, rowid as ExecutionOrder
        FROM FunctionInSession
        WHERE StrategyID IN ({','.join(map(str, strategy_id_list))})
        ORDER BY rowid ASC
    """)
    
    for func in functions:
        print(f"\n[Step {func['ExecutionOrder']}] Function ID {func['FunctionID']}: {func['FunctionName']}")
        print(f"  Success: {func['FunctionSuccess']}")
    
    # Get parameters for this function
    print_subsection(f"  └─ INPUT PARAMETERS")
    params = query_db(agentic_db, f"""
        SELECT ParameterName, ParameterValue
        FROM FunctionParametersInSession
        WHERE FunctionID = {func['FunctionID']}
        ORDER BY FunctionParameterID ASC
    """)
    
    if params:
        for param in params:
            value = truncate_value(param['ParameterValue'])
            print(f"      • {param['ParameterName']:<30} = {value}")
    else:
        print(f"      (No parameters stored)")
    
    # Get outputs for this function
    print_subsection(f"  └─ OUTPUT VALUES")
    outputs = query_db(agentic_db, f"""
        SELECT OutputName, OutputValue
        FROM FunctionOutputInSession
        WHERE FunctionID = {func['FunctionID']}
        ORDER BY FunctionOutputID ASC
    """)
    
    if outputs:
        for output in outputs:
            value = truncate_value(output['OutputValue'])
            print(f"      • {output['OutputName']:<30} = {value}")
    else:
        print(f"      (No outputs stored)")

# 4. Data flow validation
print_subsection("4. DATA FLOW VALIDATION (Output → Input)")

functions_ordered = sorted(functions, key=lambda x: x['ExecutionOrder'])
for i in range(len(functions_ordered) - 1):
    current = functions_ordered[i]
    next_func = functions_ordered[i + 1]
    
    print(f"\n  Connection: {current['FunctionName']} → {next_func['FunctionName']}")
    
    # Get current function outputs
    outputs = query_db(agentic_db, f"""
        SELECT OutputName, OutputValue
        FROM FunctionOutputInSession
        WHERE FunctionID = {current['FunctionID']}
    """)
    
    # Get next function inputs
    inputs = query_db(agentic_db, f"""
        SELECT ParameterName, ParameterValue
        FROM FunctionParametersInSession
        WHERE FunctionID = {next_func['FunctionID']}
    """)
    
    output_names = {o['OutputName'] for o in outputs}
    input_names = {i['ParameterName'] for i in inputs}
    
    # Check for overlaps
    shared = output_names & input_names
    if shared:
        print(f"    ✓ Found {len(shared)} matching output→input field(s): {shared}")
    else:
        print(f"    ℹ No direct field name match")
        print(f"      Outputs available: {output_names}")
        print(f"      Inputs expected:   {input_names}")

# 5. Final answer
print_subsection("5. FINAL WORKFLOW RESULTS")
results = query_db(agentic_db, f"""
    SELECT * FROM StrategyInSession
    WHERE SessionID = {session_id}
    LIMIT 1
""")

if results:
    result = results[0]
    print(f"Strategy Success: {result.get('StrategySuccess', 'N/A')}")
    print(f"Strategy Name: {result.get('StrategyName', 'N/A')}")
else:
    print("(No results found)")

print("\n" + "=" * 90)
print("  END OF TRACE")
print("=" * 90 + "\n")
