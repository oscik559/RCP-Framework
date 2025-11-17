#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from Layer_2_Agentic.logic.function_library import (
    func_extract_product_number, func_query_database, func_extract_attributes, func_analyze_with_llm
)
import json

# Test with full question like in main.py
user_query = "What is the Slang ID for the product 1101-14-06-30?"
print(f"Query: {user_query}\n")

# Step 1: Extract product number from question
params1 = {"Input": user_query}
success1, result1 = func_extract_product_number(params1)
print('=== STEP 1: Extract Product Number ===')
print(f'Success: {success1}')
if isinstance(result1, dict):
    print(f'Output: {result1.get("Keyword Output")}')
else:
    print(f'Output: {result1}')
    sys.exit(1)

if success1:
    # Step 2: Query Database
    keyword_output = result1.get("Keyword Output", "").strip()
    query_params = {"filters": keyword_output}
    success2, result2 = func_query_database(query_params)
    print('\n=== STEP 2: Query Database ===')
    print(f'Success: {success2}')
    
    if isinstance(result2, dict):
        print(f'Count: {result2.get("count")}')
        
        if success2:
            items = result2.get('items', [])
            print(f'Items found: {len(items)}')
            if items:
                # Show the items
                for i, item in enumerate(items):
                    print(f'\n  Item {i+1}:')
                    print(f'    - Code: {item.get("product_code")}')
                    print(f'    - Family: {item.get("family_name", "N/A")}')
                
                # Step 3: Extract Attributes
                extract_params = {"items": items}
                success3, result3 = func_extract_attributes(extract_params)
                print('\n=== STEP 3: Extract Attributes ===')
                print(f'Success: {success3}')
                
                if isinstance(result3, dict) and success3:
                    extracted_data = result3.get('extracted_data', [])
                    print(f'Extracted: {len(extracted_data)} items')
                    
                    # Show structured output
                    for i, item in enumerate(extracted_data):
                        print(f'\nExtracted Item {i+1}:')
                        print(f'  Product: {item.get("product_code")}')
                        print(f'  Specs: {item.get("specifications")}')
                        print(f'  Config: {item.get("configuration_name")}')
                        print(f'  Family: {item.get("family_code")} - {item.get("family_name")}')
                        print(f'  Category: {item.get("category_name")} ({item.get("chapter")})')
    else:
        print(f'Error: {result2}')
