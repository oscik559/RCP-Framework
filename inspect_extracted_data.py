#!/usr/bin/env python3
"""
Extract the full extracted_data output from the last function execution
"""

import sqlite3
import json

# Get the latest session and extract the full output from Extract Attributes
conn = sqlite3.connect("database/agentic.db")
cursor = conn.cursor()

# Get latest session
cursor.execute("SELECT SessionID FROM GoalInSession ORDER BY SessionID DESC LIMIT 1")
session_id = cursor.fetchone()[0]

# Get Extract Attributes function (Function ID 3)
cursor.execute("""
    SELECT FunctionOutputID, FunctionID, OutputName, OutputValue
    FROM FunctionOutputInSession
    WHERE FunctionName = 'Extract Attributes'
    ORDER BY FunctionOutputID DESC
    LIMIT 1
""")

result = cursor.fetchone()
if result:
    output_id, func_id, output_name, output_value = result
    
    print(f"Function: Extract Attributes (ID: {func_id})")
    print(f"Output Field: {output_name}")
    print()
    
    if output_name == "extracted_data":
        try:
            data = json.loads(output_value)
            print("Extracted Data (formatted):")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print("Raw output (parse error):")
            print(output_value[:2000])
else:
    print("No Extract Attributes output found")

conn.close()
