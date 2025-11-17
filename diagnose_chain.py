#!/usr/bin/env python3
"""Detailed diagnostic of function chain execution and agentic database state"""

import sqlite3
import json
import sys
from pathlib import Path

# Setup path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from Layer_2_Agentic.config.constants import ANSWER_FIELDS
from Layer_2_Agentic.config.session_config import get_default_session_state, get_workflow_config
from Layer_2_Agentic.logic.state_graph import get_graph
from Layer_2_Agentic.db.templates import populate_template_libraries
from Layer_2_Agentic.config import debug_config

print("=" * 100)
print("DIAGNOSTIC: FUNCTION CHAIN EXECUTION & AGENTIC DB STATE")
print("=" * 100)
print()

# Set debug level
debug_config.set_debug_level(0)

# Setup
query = "What is the Slang ID for the product 4221-24-08?"
init_state = get_default_session_state(query=query)
session_id = init_state['sessionID']
workflow_config = get_workflow_config()

print(f"🔍 Session ID: {session_id}")
print(f"🔍 Query: {query}")
print()

# Initialize
print("[SETUP] Initializing libraries...")
populate_template_libraries()

print(f"[SETUP] Clearing old session data...")
from Layer_2_Agentic.logic.database_manager import DatabaseManager
db = DatabaseManager()
db.clear_session_data(session_id)

# Execute workflow
print("[AI] Running workflow...\n")
graph = get_graph()
final_state = graph.invoke(init_state, config=workflow_config)

print("\n" + "=" * 100)
print("STEP 1: INSPECT FINAL STATE")
print("=" * 100)
print()

# Show key fields from final state
for key in ['query', 'sessionID', 'strategyOK', 'goalOK', 'finalAnswer']:
    if key in final_state:
        value = final_state[key]
        if isinstance(value, str) and len(value) > 200:
            print(f"  {key}: {value[:200]}...")
        else:
            print(f"  {key}: {value}")

print()
print("=" * 100)
print("STEP 2: QUERY AGENTIC DATABASE - ALL TABLES")
print("=" * 100)
print()

agentic_db = "Layer_2_Agentic/db/agentic.db"
try:
    conn = sqlite3.connect(agentic_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table_name in sorted(tables):
        print(f"\n📋 TABLE: {table_name}")
        print("-" * 100)
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"   Total rows: {count}")
        
        if count == 0:
            print(f"   (empty)")
            continue
        
        # Get columns
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Filter to session if applicable
        if 'session_id' in columns:
            cursor.execute(f"SELECT * FROM {table_name} WHERE session_id = ?", (session_id,))
            rows = cursor.fetchall()
            print(f"   Rows for this session: {len(rows)}")
        else:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 100")
            rows = cursor.fetchall()
            print(f"   Showing up to 100 rows")
        
        if rows:
            print(f"   Columns: {', '.join(columns)}")
            print()
            
            for i, row in enumerate(rows[:5]):  # Show first 5 rows
                print(f"   Row {i+1}:")
                for col in columns:
                    value = row[col]
                    if value is None:
                        print(f"      {col}: NULL")
                    elif isinstance(value, str) and len(value) > 100:
                        print(f"      {col}: {value[:100]}...")
                    else:
                        print(f"      {col}: {value}")
                print()
            
            if len(rows) > 5:
                print(f"   ... and {len(rows) - 5} more rows")
        print()
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error querying agentic database: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 100)
print("STEP 3: INSPECT HARVESTED DATABASE - PRODUCT DATA")
print("=" * 100)
print()

harvested_db = "database/harvested.db"
try:
    conn = sqlite3.connect(harvested_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get product 4221-24-08
    cursor.execute("SELECT * FROM products WHERE product_code = '4221-24-08'")
    product = cursor.fetchone()
    
    if product:
        print(f"✓ Found product: 4221-24-08")
        print()
        
        cols = [description[0] for description in cursor.description]
        for col in cols:
            value = product[col]
            if col == 'specifications' and value:
                # Pretty print JSON
                specs = json.loads(value)
                print(f"   {col}:")
                for key, val in specs.items():
                    print(f"      {key}: {val}")
            elif isinstance(value, str) and len(value) > 100:
                print(f"   {col}: {value[:100]}...")
            else:
                print(f"   {col}: {value}")
    else:
        print("❌ Product not found")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error querying harvested database: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 100)
print("STEP 4: TRACE FUNCTION INPUTS → OUTPUTS")
print("=" * 100)
print()

try:
    conn = sqlite3.connect(agentic_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all function executions for this session
    cursor.execute("""
        SELECT id, goal_id, function_name, input_params, output_result, success
        FROM function_executions
        WHERE session_id = ?
        ORDER BY id ASC
    """, (session_id,))
    
    executions = cursor.fetchall()
    
    if executions:
        print(f"Found {len(executions)} function executions:")
        print()
        
        for i, exec_row in enumerate(executions, 1):
            print(f"📍 Execution {i}: {exec_row['function_name']}")
            print(f"   Function ID: {exec_row['id']}")
            print(f"   Goal ID: {exec_row['goal_id']}")
            print(f"   Success: {exec_row['success']}")
            print()
            
            # Parse and display input params
            if exec_row['input_params']:
                try:
                    params = json.loads(exec_row['input_params'])
                    print(f"   INPUT PARAMETERS:")
                    for key, value in params.items():
                        if isinstance(value, str) and len(value) > 100:
                            print(f"      {key}: {value[:100]}...")
                        elif isinstance(value, (dict, list)):
                            print(f"      {key}: {json.dumps(value, indent=6)[:200]}...")
                        else:
                            print(f"      {key}: {value}")
                except:
                    print(f"   INPUT PARAMETERS: {exec_row['input_params'][:200]}...")
            print()
            
            # Parse and display output
            if exec_row['output_result']:
                try:
                    result = json.loads(exec_row['output_result'])
                    print(f"   OUTPUT RESULT:")
                    for key, value in result.items():
                        if isinstance(value, str) and len(value) > 100:
                            print(f"      {key}: {value[:100]}...")
                        elif isinstance(value, (dict, list)):
                            print(f"      {key}: {json.dumps(value, indent=6)[:200]}...")
                        else:
                            print(f"      {key}: {value}")
                except:
                    print(f"   OUTPUT RESULT: {exec_row['output_result'][:200]}...")
            print()
    else:
        print("❌ No function executions found for this session")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error tracing function executions: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 100)
print("DIAGNOSTIC COMPLETE")
print("=" * 100)
