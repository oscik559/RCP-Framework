#!/usr/bin/env python3
"""Test func_extract_product_number"""

from Layer_2_Agentic.logic.function_library import func_extract_product_number

# Test query from STRATEGY_PROPOSAL
query = "What is the Slang ID for the product 4221-24-08?"
params = {"Input": query}

print("=" * 70)
print("TEST: func_extract_product_number")
print("=" * 70)
print(f"Query: {query}")
print()

# Run the function
success, result = func_extract_product_number(params)

print(f"✓ Success: {success}")
print(f"✓ Result Type: {type(result)}")
print(f"✓ Result: {result}")
print()

# Extract the product code
product_code = result.get("Keyword Output", "NONE") if isinstance(result, dict) else str(result)
print(f"✓ Extracted Product Code: {product_code}")
print()

# Verify it matches expected
expected = "4221-24-08"
if expected in product_code:
    print(f"✅ PASS: Product code correctly extracted!")
else:
    print(f"❌ FAIL: Expected '{expected}', got '{product_code}'")
