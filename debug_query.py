import sys
sys.path.insert(0, '.')
from Layer_2_Agentic.logic.function_library import func_extract_product_number, func_query_database
import json

# Test product
product_code = '1101-14-06-30'
params = {'product_code': product_code}

# Step 1: Extract product number to see what it returns
success1, result1 = func_extract_product_number(params)
print('=== EXTRACT PRODUCT NUMBER OUTPUT ===')
print(f'Success: {success1}')
print(json.dumps(result1, indent=2, ensure_ascii=False))

if success1:
    extracted_code = result1.get('product_code')
    print(f'\nExtracted code for query: "{extracted_code}"')
    
    # Step 2: Check what query is built
    query_params = {'filters': extracted_code}
    print(f'\nQuery params: {query_params}')
    
    success2, result2 = func_query_database(query_params)
    print('\n=== QUERY DATABASE OUTPUT ===')
    print(f'Success: {success2}')
    print(f'Count: {result2.get("count")}')
    print(f'Query type: {result2.get("query_type")}')
    
    items = result2.get('items', [])
    print(f'\nReturned items ({len(items)}):')
    for i, item in enumerate(items[:5]):  # Show first 5
        print(f'  {i+1}. {item.get("product_code")}')
    if len(items) > 5:
        print(f'  ... and {len(items) - 5} more')
