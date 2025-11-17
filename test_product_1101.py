#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from Layer_2_Agentic.logic.function_library import func_extract_product_number, func_query_database, func_extract_attributes
import json

# Test product
product_code = '1101-14-06-30'
params = {'product_code': product_code}

# Step 1: Extract product number
success1, result1 = func_extract_product_number(params)
print('=== STEP 1: Extract Product Number ===')
print(f'Success: {success1}')
print(json.dumps(result1, indent=2, ensure_ascii=False)[:800])

if success1:
    # Step 2: Query Database
    query_params = {'filters': result1.get('product_code')}
    success2, result2 = func_query_database(query_params)
    print('\n=== STEP 2: Query Database ===')
    print(f'Success: {success2}')
    print(f'Count: {result2.get("count")}')
    
    if success2:
        items = result2.get('items', [])
        if items:
            print(f'First item configuration_name: {items[0].get("configuration_name")}')
            print(f'First item keys: {list(items[0].keys())}')
            
            # Step 3: Extract Attributes
            extract_params = {'items': items}
            success3, result3 = func_extract_attributes(extract_params)
            print('\n=== STEP 3: Extract Attributes ===')
            print(f'Success: {success3}')
            
            if success3:
                extracted_data = result3.get('extracted_data', [])
                print(f'Extracted {len(extracted_data)} items')
                print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
