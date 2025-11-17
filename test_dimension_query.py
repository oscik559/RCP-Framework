#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from Layer_2_Agentic.logic.function_library import func_extract_product_number, func_query_database, func_extract_attributes
import json

user_query = 'What is the dimension of this 1101-14-06-30 product?'
print(f'Query: {user_query}')
print('='*80)

# Step 1: Extract Product Number
params1 = {'Input': user_query}
success1, result1 = func_extract_product_number(params1)
keyword = result1.get('Keyword Output', '').strip()
print(f'\n✓ STEP 1 - Extract Product Number')
print(f'  Extracted: "{keyword}"')

# Step 2: Query Database
params2 = {'filters': keyword}
success2, result2 = func_query_database(params2)
items = result2.get('items', []) if isinstance(result2, dict) else []
print(f'\n✓ STEP 2 - Query Database')
print(f'  Found: {len(items)} items')
for item in items:
    print(f'    - {item.get("product_code")}')

# Step 3: Extract Attributes
if items:
    params3 = {'items': items}
    success3, result3 = func_extract_attributes(params3)
    extracted = result3.get('extracted_data', []) if isinstance(result3, dict) else []
    print(f'\n✓ STEP 3 - Extract Attributes')
    print(f'  Extracted: {len(extracted)} items')
    print()
    print('='*80)
    print('FULL EXTRACTED DATA OUTPUT:')
    print('='*80)
    print(json.dumps(extracted, indent=2, ensure_ascii=False))
