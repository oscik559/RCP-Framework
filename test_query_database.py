#!/usr/bin/env python3
"""Test func_query_database to fetch product specs for 4221-24-08"""

from Layer_2_Agentic.logic.function_library import func_query_database
import json

product_code = "4221-24-08"

print("=" * 70)
print("TEST: func_query_database")
print("=" * 70)
print(f"Product Code: {product_code}")
print()

# Build query to fetch product by code
params = {
    "query_type": "custom",
    "custom_sql": f"SELECT product_code, specifications, family_id FROM products WHERE product_code = '{product_code}' LIMIT 1",
    "database_path": "database/harvested.db"
}

print(f"SQL: {params['custom_sql']}")
print()

# Run the function
success, result = func_query_database(params)

print(f"✓ Success: {success}")
print(f"✓ Result Type: {type(result)}")
print()

if success and isinstance(result, dict):
    print(f"✓ Count: {result.get('count', 0)}")
    print(f"✓ Fields: {result.get('fields', [])}")
    print()
    
    # Show results
    results = result.get('results', [])
    if results:
        print(f"✅ Found {len(results)} product(s)")
        for idx, product in enumerate(results):
            print()
            print(f"  Product {idx + 1}:")
            print(f"    - Product Code: {product.get('product_code')}")
            print(f"    - Family ID: {product.get('family_id')}")
            
            # Parse specifications JSON
            specs_json = product.get('specifications', '{}')
            try:
                specs = json.loads(specs_json)
                print(f"    - Specifications (parsed JSON):")
                for key, value in specs.items():
                    print(f"        {key}: {value}")
            except json.JSONDecodeError:
                print(f"    - Specifications (raw): {specs_json[:100]}...")
    else:
        print(f"❌ No product found with code {product_code}")
else:
    print(f"❌ Query failed: {result}")
