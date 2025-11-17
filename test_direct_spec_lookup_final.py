#!/usr/bin/env python3
"""Test the complete DIRECT_SPEC_LOOKUP strategy - Direct Extraction"""

from Layer_2_Agentic.logic.function_library import func_extract_product_number, func_query_database
import json

print("=" * 70)
print("STRATEGY TEST: DIRECT_SPEC_LOOKUP")
print("=" * 70)
print()

# ========== STEP 1: Extract Product Number ==========
print("STEP 1: Extract Product Number")
print("-" * 70)
query = "What is the Slang ID for the product 4221-24-08?"
print(f"Query: {query}")
print()

params_extract = {"Input": query}
success_extract, result_extract = func_extract_product_number(params_extract)
product_code = result_extract.get("Keyword Output", "").strip()

print(f"✓ Extracted: {product_code}")
print()

# ========== STEP 2: Query Database ==========
print("STEP 2: Query Database (fetch product specs)")
print("-" * 70)

params_query = {
    "query_type": "custom",
    "custom_sql": f"SELECT product_code, specifications FROM products WHERE product_code = '{product_code}' LIMIT 1",
    "database_path": "database/harvested.db"
}

success_query, result_query = func_query_database(params_query)
print(f"✓ Query success: {success_query}")

if success_query and isinstance(result_query, dict):
    results = result_query.get('results', [])
    if results:
        product_data = results[0]
        specs_json = product_data.get('specifications', '{}')
        specs = json.loads(specs_json)
        
        print(f"✓ Product Code: {product_data.get('product_code')}")
        print(f"✓ All Specifications:")
        for key, value in specs.items():
            print(f"    {key}: {value}")
        print()
        
        # ========== STEP 3: Direct Extraction ==========
        print("STEP 3: Extract Target Attribute")
        print("-" * 70)
        
        # Parse query to find what attribute is being asked for
        query_lower = query.lower()
        
        # Map common attribute names to JSON keys
        attribute_map = {
            "slang id": "Slang ID",
            "ganga": "Gänga",
            "ror": "Rör",
            "typ": "Typ",
            "artikelnr": "Artikelnr.",
        }
        
        target_attribute = None
        for query_term, spec_key in attribute_map.items():
            if query_term in query_lower:
                target_attribute = spec_key
                break
        
        if target_attribute:
            value = specs.get(target_attribute, "NOT FOUND")
            print(f"✓ Target Attribute: {target_attribute}")
            print(f"✓ Value: {value}")
            print()
            
            # ========== FINAL ANSWER ==========
            print("=" * 70)
            print("FINAL ANSWER:")
            print("=" * 70)
            print(f"The {target_attribute} for product {product_code} is: {value}")
            print()
            print("✅ STRATEGY COMPLETE!")
        else:
            print("❌ Could not determine target attribute from query")
else:
    print(f"❌ Query failed")

print()
print("=" * 70)
