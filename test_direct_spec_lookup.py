#!/usr/bin/env python3
"""Test the complete DIRECT_SPEC_LOOKUP strategy"""

from Layer_2_Agentic.logic.function_library import func_extract_product_number, func_query_database, func_analyze_data
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
        
        # Extract the Slang ID
        slang_id = specs.get("Slang ID", "NOT FOUND")
        print(f"✓ TARGET ATTRIBUTE - Slang ID: {slang_id}")
        print()
        
        # ========== STEP 3: Analyze with LLM ==========
        print("STEP 3: LLM Synthesis (final answer)")
        print("-" * 70)
        
        # Prepare context for LLM
        specs_text = json.dumps(specs, indent=2)
        params_analyze = {
            "Input": query,
            "Assembled Data": specs_text,
            "Question": query,
        }
        
        success_analyze, result_analyze = func_analyze_data(params_analyze)
        print(f"✓ Analysis success: {success_analyze}")
        
        if success_analyze and isinstance(result_analyze, dict):
            answer = result_analyze.get("Analysis Result", result_analyze.get("result", str(result_analyze)))
            print()
            print("=" * 70)
            print("FINAL ANSWER:")
            print("=" * 70)
            print(answer)
            print()
            print("✅ STRATEGY COMPLETE!")
        else:
            print(f"❌ LLM Analysis failed: {result_analyze}")
else:
    print(f"❌ Query failed")
