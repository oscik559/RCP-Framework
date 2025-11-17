#!/usr/bin/env python3
"""
Trace the latest execution by re-running main.py with debug output
and analyzing the function call sequence
"""

import subprocess
import sys

print("=" * 80)
print("EXECUTING: main.py with DIRECT_SPEC_LOOKUP strategy")
print("=" * 80)
print()

# Run main.py and capture output
result = subprocess.run(
    [sys.executable, "main.py"],
    capture_output=True,
    text=True,
    encoding='utf-8'
)

output = result.stdout

# Parse the output to extract function trace
lines = output.split('\n')

print("\n" + "=" * 80)
print("FUNCTION EXECUTION TRACE")
print("=" * 80)

# Find all function execution details
in_function_section = False
function_num = 0
current_section = []

for line in lines:
    if "FUNCTION EXECUTION DETAILS" in line:
        if current_section:
            # Print previous function
            print_function_trace(current_section, function_num)
            function_num += 1
        in_function_section = True
        current_section = [line]
    elif in_function_section:
        if line.startswith("=" * 20):
            print_function_trace(current_section, function_num)
            function_num += 1
            in_function_section = False
            current_section = []
        else:
            current_section.append(line)

def print_function_trace(lines, num):
    """Extract and print function details"""
    if not lines:
        return
    
    content = '\n'.join(lines)
    
    # Extract function name
    if "📋 Function:" in content:
        for line in lines:
            if "📋 Function:" in line:
                func_name = line.split(":", 1)[1].strip()
                print(f"\n[Function {num}] {func_name}")
                break
    
    # Extract input parameters
    if "📥 INPUT PARAMETERS" in content:
        print("\n  INPUT PARAMETERS:")
        in_inputs = False
        for line in lines:
            if "INPUT PARAMETERS" in line:
                in_inputs = True
            elif in_inputs and line.startswith("   •"):
                print(f"    {line}")
            elif in_inputs and line.startswith("---"):
                break
    
    # Extract outputs
    if "📤 OUTPUT:" in content:
        print("\n  OUTPUTS:")
        in_outputs = False
        for line in lines:
            if "OUTPUT:" in line:
                in_outputs = True
            elif in_outputs and line.startswith("   •"):
                print(f"    {line}")
            elif in_outputs and line.startswith("---"):
                break

print_function_trace(current_section, function_num)

# Extract final answer
print("\n" + "=" * 80)
print("FINAL RESULT")
print("=" * 80)

in_results = False
for i, line in enumerate(lines):
    if "RESULTS" in line and "========" in lines[i-1]:
        in_results = True
    elif in_results:
        if "SUCCESS" in line or "FAILED" in line:
            break
        if line.strip():
            print(line)

print("\n" + "=" * 80)
